const express = require('express');
const { pool } = require('./db');
const {
  RuleError,
  MAX_PER_CUSTOMER_PER_DAY,
  localDayStart,
  isValidDateStr,
  parsePositiveInt,
  validateReservationInput,
  buildSlots,
} = require('./rules');

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '10kb' }));

const asyncH = (fn) => (req, res, next) => fn(req, res, next).catch(next);

async function getResource(id) {
  const { rows } = await pool.query(
    'SELECT id, name, type, capacity, open_hour, close_hour FROM resources WHERE id = $1',
    [id]
  );
  return rows[0] || null;
}

// ---------------------------------------------------------------- salud
app.get('/health', asyncH(async (_req, res) => {
  await pool.query('SELECT 1');
  res.json({ status: 'ok', version: process.env.APP_VERSION || 'dev' });
}));

// ---------------------------------------------------------------- recursos
app.get('/resources', asyncH(async (_req, res) => {
  const { rows } = await pool.query(
    'SELECT id, name, type, capacity, open_hour, close_hour FROM resources ORDER BY id'
  );
  res.json({ data: rows });
}));

// ---------------------------------------------------------------- disponibilidad
// GET /resources/:id/availability?date=YYYY-MM-DD
app.get('/resources/:id/availability', asyncH(async (req, res) => {
  const id = parsePositiveInt(req.params.id);
  const date = req.query.date;
  if (!id) throw new RuleError(400, 'BAD_REQUEST', 'id de recurso inválido');
  if (!isValidDateStr(date)) throw new RuleError(400, 'BAD_REQUEST', 'date debe tener formato YYYY-MM-DD');

  const resource = await getResource(id);
  if (!resource) throw new RuleError(404, 'NOT_FOUND', 'Recurso no encontrado');

  const dayStart = localDayStart(date);
  const dayEnd = new Date(dayStart.getTime() + 24 * 3_600_000);
  const { rows } = await pool.query(
    `SELECT start_at, end_at
       FROM reservations
      WHERE resource_id = $1
        AND status = 'confirmed'
        AND start_at < $3
        AND end_at   > $2
        -- Cota inferior equivalente por R1 (ninguna reserva dura más de 240 min):
        -- permite un rango acotado sobre el índice (resource_id, start_at)
        AND start_at >= $2::timestamptz - interval '240 minutes'
      ORDER BY start_at`,
    [id, dayStart, dayEnd]
  );

  const slots = buildSlots(date, resource, rows);
  res.json({
    resource_id: id,
    date,
    open_hour: resource.open_hour,
    close_hour: resource.close_hour,
    available_slots: slots.filter((s) => s.available).length,
    slots,
  });
}));

// ---------------------------------------------------------------- crear reserva
// POST /reservations {resource_id, customer_id, start_at, duration_min}
app.post('/reservations', asyncH(async (req, res) => {
  const pre = validateReservationInput(req.body, null); // validación de forma (400 / R1)
  const resource = await getResource(pre.resourceId);
  if (!resource) throw new RuleError(404, 'NOT_FOUND', 'Recurso no encontrado');
  const input = validateReservationInput(req.body, resource); // R2, R3

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const cust = await client.query('SELECT id FROM customers WHERE id = $1', [input.customerId]);
    if (cust.rowCount === 0) throw new RuleError(404, 'NOT_FOUND', 'Cliente no encontrado');

    // R5: serializa por cliente para que dos solicitudes simultáneas no rompan el límite diario
    await client.query('SELECT pg_advisory_xact_lock(1, $1)', [input.customerId]);
    const dayStart = localDayStart(input.localDate);
    const dayEnd = new Date(dayStart.getTime() + 24 * 3_600_000);
    const { rows: [{ n }] } = await client.query(
      `SELECT count(*)::int AS n
         FROM reservations
        WHERE customer_id = $1
          AND status = 'confirmed'
          AND start_at >= $2 AND start_at < $3`,
      [input.customerId, dayStart, dayEnd]
    );
    if (n >= MAX_PER_CUSTOMER_PER_DAY) {
      throw new RuleError(422, 'R5_DAILY_LIMIT', `El cliente ya tiene ${MAX_PER_CUSTOMER_PER_DAY} reservas ese día`);
    }

    const { rows: [created] } = await client.query(
      `INSERT INTO reservations (resource_id, customer_id, start_at, end_at)
       VALUES ($1, $2, $3, $4)
       RETURNING id, resource_id, customer_id, start_at, end_at, status, created_at`,
      [input.resourceId, input.customerId, input.start, input.end]
    );
    await client.query('COMMIT');
    res.status(201).json(created);
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    if (err.code === '23P01') { // exclusion_violation -> R4
      throw new RuleError(409, 'R4_OVERLAP', 'El recurso ya está reservado en ese horario');
    }
    throw err;
  } finally {
    client.release();
  }
}));

// ---------------------------------------------------------------- listado paginado
// GET /reservations?page=1&page_size=20&resource_id=&customer_id=&from=YYYY-MM-DD&to=YYYY-MM-DD&status=
app.get('/reservations', asyncH(async (req, res) => {
  const page = req.query.page === undefined ? 1 : parsePositiveInt(req.query.page);
  const pageSize = req.query.page_size === undefined ? 20 : parsePositiveInt(req.query.page_size);
  if (!page || page > 10_000) throw new RuleError(400, 'BAD_REQUEST', 'page debe estar entre 1 y 10000');
  if (!pageSize || pageSize > 100) throw new RuleError(400, 'BAD_REQUEST', 'page_size debe estar entre 1 y 100');

  const where = [];
  const params = [];
  const add = (sql, v) => { params.push(v); where.push(sql.replace('?', `$${params.length}`)); };

  if (req.query.resource_id !== undefined) {
    const v = parsePositiveInt(req.query.resource_id);
    if (!v) throw new RuleError(400, 'BAD_REQUEST', 'resource_id inválido');
    add('r.resource_id = ?', v);
  }
  if (req.query.customer_id !== undefined) {
    const v = parsePositiveInt(req.query.customer_id);
    if (!v) throw new RuleError(400, 'BAD_REQUEST', 'customer_id inválido');
    add('r.customer_id = ?', v);
  }
  if (req.query.status !== undefined) {
    if (!['confirmed', 'cancelled'].includes(req.query.status)) throw new RuleError(400, 'BAD_REQUEST', 'status inválido');
    add('r.status = ?', req.query.status);
  }
  if (req.query.from !== undefined) {
    if (!isValidDateStr(req.query.from)) throw new RuleError(400, 'BAD_REQUEST', 'from inválido');
    add('r.start_at >= ?', localDayStart(req.query.from));
  }
  if (req.query.to !== undefined) {
    if (!isValidDateStr(req.query.to)) throw new RuleError(400, 'BAD_REQUEST', 'to inválido');
    add('r.start_at < ?', new Date(localDayStart(req.query.to).getTime() + 24 * 3_600_000));
  }
  const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

  const countQ = pool.query(`SELECT count(*)::int AS total FROM reservations r ${whereSql}`, params);
  const dataQ = pool.query(
    `SELECT r.id, r.resource_id, s.name AS resource_name, r.customer_id,
            r.start_at, r.end_at, r.status, r.created_at
       FROM reservations r
       JOIN resources s ON s.id = r.resource_id
       ${whereSql}
      ORDER BY r.start_at DESC, r.id DESC
      LIMIT $${params.length + 1} OFFSET $${params.length + 2}`,
    [...params, pageSize, (page - 1) * pageSize]
  );
  const [{ rows: [{ total }] }, { rows }] = await Promise.all([countQ, dataQ]);

  res.json({
    data: rows,
    page,
    page_size: pageSize,
    total,
    total_pages: Math.ceil(total / pageSize),
  });
}));

// ---------------------------------------------------------------- errores
app.use((_req, res) => res.status(404).json({ error: 'NOT_FOUND', message: 'Ruta no encontrada' }));

// eslint-disable-next-line no-unused-vars
app.use((err, _req, res, _next) => {
  if (err instanceof RuleError) return res.status(err.status).json({ error: err.code, message: err.message });
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'BAD_REQUEST', message: 'JSON inválido' });
  console.error('[api] error no controlado:', err.code || '', err.message);
  const status = err.message && (/timeout|Connection terminated/i.test(err.message) || ['ECONNREFUSED', '57P01', '53300'].includes(err.code)) ? 503 : 500;
  return res.status(status).json({ error: status === 503 ? 'UNAVAILABLE' : 'INTERNAL', message: 'Error interno' });
});

module.exports = { app };
