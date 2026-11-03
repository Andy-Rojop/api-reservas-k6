// Reglas de negocio puras (sin base de datos), probadas en test/rules.test.js
//
// R1  Duración entre 30 y 240 minutos, en múltiplos de 30.
// R2  Inicio y fin dentro del horario del recurso, el mismo día (hora de Guatemala, UTC-6 sin horario de verano).
// R3  No se puede reservar en el pasado.
// R4  Sin traslapes por recurso (restricción EXCLUDE en PostgreSQL -> 409).
// R5  Máximo 2 reservas confirmadas por cliente por día local (transacción + advisory lock -> 422).

const TZ_OFFSET_MIN = -360; // America/Guatemala
const MAX_PER_CUSTOMER_PER_DAY = 2;

class RuleError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** Convierte un instante a {date:'YYYY-MM-DD', minutes: minutos desde medianoche} en hora local. */
function toLocal(d) {
  const local = new Date(d.getTime() + TZ_OFFSET_MIN * 60_000);
  return {
    date: local.toISOString().slice(0, 10),
    minutes: local.getUTCHours() * 60 + local.getUTCMinutes(),
    seconds: local.getUTCSeconds() + local.getUTCMilliseconds(),
  };
}

/** Inicio (UTC) del día local indicado. */
function localDayStart(dateStr) {
  return new Date(Date.parse(`${dateStr}T00:00:00Z`) - TZ_OFFSET_MIN * 60_000);
}

function isValidDateStr(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

function parsePositiveInt(v) {
  if (typeof v === 'number' && Number.isInteger(v) && v > 0) return v;
  if (typeof v === 'string' && /^\d{1,9}$/.test(v) && Number(v) > 0) return Number(v);
  return null;
}

/**
 * Valida el cuerpo de POST /reservations contra R1–R3.
 * Devuelve {resourceId, customerId, start, end, localDate}.
 */
function validateReservationInput(body, resource, now = new Date()) {
  if (!body || typeof body !== 'object') throw new RuleError(400, 'BAD_REQUEST', 'Cuerpo JSON requerido');
  const resourceId = parsePositiveInt(body.resource_id);
  const customerId = parsePositiveInt(body.customer_id);
  const duration = body.duration_min;
  if (!resourceId) throw new RuleError(400, 'BAD_REQUEST', 'resource_id inválido');
  if (!customerId) throw new RuleError(400, 'BAD_REQUEST', 'customer_id inválido');
  if (typeof body.start_at !== 'string') throw new RuleError(400, 'BAD_REQUEST', 'start_at requerido (ISO 8601 con zona)');
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(body.start_at)) throw new RuleError(400, 'BAD_REQUEST', 'start_at debe incluir zona horaria');
  const start = new Date(body.start_at);
  if (Number.isNaN(start.getTime())) throw new RuleError(400, 'BAD_REQUEST', 'start_at no es una fecha válida');
  if (!Number.isInteger(duration)) throw new RuleError(400, 'BAD_REQUEST', 'duration_min debe ser entero');

  // R1
  if (duration < 30 || duration > 240 || duration % 30 !== 0) {
    throw new RuleError(422, 'R1_DURATION', 'La duración debe estar entre 30 y 240 minutos, en múltiplos de 30');
  }
  const end = new Date(start.getTime() + duration * 60_000);

  // R2
  if (resource) {
    const ls = toLocal(start);
    const le = toLocal(new Date(end.getTime() - 1)); // fin exclusivo
    const endMinutes = ls.minutes + duration;
    if (ls.seconds !== 0 || ls.minutes % 30 !== 0) {
      throw new RuleError(422, 'R2_HOURS', 'El inicio debe estar alineado a bloques de 30 minutos');
    }
    if (ls.date !== le.date || ls.minutes < resource.open_hour * 60 || endMinutes > resource.close_hour * 60) {
      throw new RuleError(422, 'R2_HOURS', `La reserva debe estar entre ${resource.open_hour}:00 y ${resource.close_hour}:00 del mismo día`);
    }
  }

  // R3
  if (start.getTime() <= now.getTime()) {
    throw new RuleError(422, 'R3_PAST', 'No se puede reservar en el pasado');
  }

  return { resourceId, customerId, start, end, duration, localDate: toLocal(start).date };
}

/** Bloques de 30 min del día con su disponibilidad. reservations: [{start_at, end_at}] */
function buildSlots(dateStr, resource, reservations) {
  const dayStart = localDayStart(dateStr).getTime();
  const busy = reservations.map((r) => [new Date(r.start_at).getTime(), new Date(r.end_at).getTime()]);
  const slots = [];
  for (let m = resource.open_hour * 60; m < resource.close_hour * 60; m += 30) {
    const s = dayStart + m * 60_000;
    const e = s + 30 * 60_000;
    const available = !busy.some(([bs, be]) => bs < e && be > s);
    slots.push({ start: new Date(s).toISOString(), end: new Date(e).toISOString(), available });
  }
  return slots;
}

module.exports = {
  TZ_OFFSET_MIN,
  MAX_PER_CUSTOMER_PER_DAY,
  RuleError,
  toLocal,
  localDayStart,
  isValidDateStr,
  parsePositiveInt,
  validateReservationInput,
  buildSlots,
};
