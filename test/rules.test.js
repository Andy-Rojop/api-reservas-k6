// Pruebas unitarias de reglas de negocio (no requieren base de datos)
const test = require('node:test');
const assert = require('node:assert');
const { validateReservationInput, buildSlots, toLocal, localDayStart } = require('../src/rules');

const resource = { id: 1, open_hour: 8, close_hour: 20 };
const now = new Date('2026-11-02T12:00:00Z');
const ok = (o) => ({ resource_id: 1, customer_id: 1, start_at: '2028-03-01T10:00:00-06:00', duration_min: 60, ...o });
const status = (fn) => { try { fn(); return 200; } catch (e) { return e.status; } };

test('acepta una reserva válida', () => {
  const r = validateReservationInput(ok(), resource, now);
  assert.equal(r.localDate, '2028-03-01');
  assert.equal(r.end.toISOString(), '2028-03-01T17:00:00.000Z');
});

test('R1 duración', () => {
  for (const d of [0, 15, 45, 270]) assert.equal(status(() => validateReservationInput(ok({ duration_min: d }), resource, now)), 422);
  assert.equal(status(() => validateReservationInput(ok({ duration_min: '60' }), resource, now)), 400);
});

test('R2 horario y alineación', () => {
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2028-03-01T07:30:00-06:00' }), resource, now)), 422);
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2028-03-01T19:30:00-06:00', duration_min: 60 }), resource, now)), 422);
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2028-03-01T10:15:00-06:00' }), resource, now)), 422);
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2028-03-01T19:30:00-06:00', duration_min: 30 }), resource, now)), 200);
});

test('R3 pasado', () => {
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2025-03-01T10:00:00-06:00' }), resource, now)), 422);
});

test('entradas mal formadas -> 400', () => {
  assert.equal(status(() => validateReservationInput(ok({ start_at: '2028-03-01T10:00:00' }), resource, now)), 400);
  assert.equal(status(() => validateReservationInput(ok({ resource_id: -1 }), resource, now)), 400);
  assert.equal(status(() => validateReservationInput(null, resource, now)), 400);
});

test('slots de 30 min y ocupación', () => {
  const slots = buildSlots('2028-03-01', resource, [
    { start_at: '2028-03-01T16:00:00Z', end_at: '2028-03-01T17:00:00Z' }, // 10:00–11:00 local
  ]);
  assert.equal(slots.length, 24);
  assert.equal(slots.filter((s) => !s.available).length, 2);
  assert.equal(toLocal(localDayStart('2028-03-01')).minutes, 0);
});
