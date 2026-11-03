#!/usr/bin/env node
// Verifica que las reglas de negocio se conservaron en TODA la base (correr después de cada prueba).
// Sale con código 1 si alguna regla se rompió.
const { Client } = require('pg');

const CHECKS = [
  ['R1 duración 30–240 min múltiplo de 30', `
    SELECT count(*)::int AS n FROM reservations
     WHERE extract(epoch FROM end_at - start_at)/60 NOT BETWEEN 30 AND 240
        OR (extract(epoch FROM end_at - start_at)/60)::int % 30 <> 0`],
  ['R2 dentro del horario y mismo día', `
    SELECT count(*)::int AS n FROM reservations r JOIN resources s ON s.id = r.resource_id
     WHERE (r.start_at AT TIME ZONE 'America/Guatemala')::date <> ((r.end_at - interval '1 second') AT TIME ZONE 'America/Guatemala')::date
        OR (r.start_at AT TIME ZONE 'America/Guatemala')::time < make_time(s.open_hour, 0, 0)
        OR ((r.end_at AT TIME ZONE 'America/Guatemala') - (r.start_at AT TIME ZONE 'America/Guatemala')::date)
           > make_interval(hours => s.close_hour)`],
  ['R4 sin traslapes por recurso (confirmadas)', `
    SELECT count(*)::int AS n FROM reservations a JOIN reservations b
      ON a.resource_id = b.resource_id AND a.id < b.id
     AND a.status = 'confirmed' AND b.status = 'confirmed'
     AND tstzrange(a.start_at, a.end_at, '[)') && tstzrange(b.start_at, b.end_at, '[)')`],
  ['R5 máximo 2 confirmadas por cliente por día', `
    SELECT count(*)::int AS n FROM (
      SELECT customer_id, (start_at AT TIME ZONE 'America/Guatemala')::date
        FROM reservations WHERE status = 'confirmed'
       GROUP BY 1, 2 HAVING count(*) > 2) x`],
];

(async () => {
  const client = new Client({ connectionString: process.env.DATABASE_URL || 'postgres://reservas:reservas@localhost:5432/reservas' });
  await client.connect();
  let ok = true;
  try {
    const { rows: [tot] } = await client.query(`SELECT count(*)::int AS total,
      count(*) FILTER (WHERE start_at >= '2028-01-01T06:00:00Z')::int AS creadas_por_pruebas FROM reservations`);
    console.log(`[invariantes] reservas totales=${tot.total} (creadas en 2028 por pruebas=${tot.creadas_por_pruebas})`);
    for (const [name, sql] of CHECKS) {
      const { rows: [{ n }] } = await client.query(sql);
      console.log(`  ${n === 0 ? 'OK  ' : 'FALLA'} ${name}${n ? ` → ${n} violaciones` : ''}`);
      if (n !== 0) ok = false;
    }
  } finally {
    await client.end();
  }
  console.log(ok ? '[invariantes] TODAS las reglas se conservan' : '[invariantes] HAY REGLAS ROTAS');
  process.exit(ok ? 0 : 1);
})().catch((e) => { console.error('[invariantes] ERROR:', e.message); process.exit(2); });
