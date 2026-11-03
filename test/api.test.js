// Regresión funcional contra la API en ejecución + PostgreSQL real.
// Requiere: API arriba (API_URL, default http://localhost:3000) y base restablecida.
// Uso: npm test        (se omite si la API no responde)
const test = require('node:test');
const assert = require('node:assert');

const API = process.env.API_URL || 'http://localhost:3000';
const j = async (method, path, body) => {
  const r = await fetch(API + path, {
    method, headers: { 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined,
  });
  return { status: r.status, body: await r.json().catch(() => null) };
};

let up = false;
test.before(async () => { up = (await fetch(`${API}/health`).catch(() => null))?.ok === true; });
const t = (name, fn) => test(name, async (ctx) => { if (!up) return ctx.skip('API no disponible'); await fn(); });

// Fecha/recurso/cliente exclusivos para esta suite (diciembre 2028, recurso 40)
const RES = 40;
const day = `2028-12-${String(1 + Math.floor(Math.random() * 28)).padStart(2, '0')}`;
const cust = 4000 + Math.floor(Math.random() * 1000);

t('health', async () => { assert.equal((await j('GET', '/health')).status, 200); });

t('disponibilidad: estructura y 24 bloques', async () => {
  const r = await j('GET', `/resources/1/availability?date=2026-05-04`);
  assert.equal(r.status, 200);
  assert.equal(r.body.slots.length, 24);
  assert.ok(r.body.slots.some((s) => !s.available), 'datos sembrados ocupan bloques');
  assert.equal((await j('GET', '/resources/1/availability?date=2026-13-01')).status, 400);
  assert.equal((await j('GET', '/resources/999/availability?date=2026-05-04')).status, 404);
});

t('crear, traslape (R4) y límite diario (R5)', async () => {
  const a = await j('POST', '/reservations', { resource_id: RES, customer_id: cust, start_at: `${day}T08:00:00-06:00`, duration_min: 90 });
  assert.equal(a.status, 201, JSON.stringify(a.body));
  const overlap = await j('POST', '/reservations', { resource_id: RES, customer_id: cust - 1, start_at: `${day}T09:00:00-06:00`, duration_min: 60 });
  assert.equal(overlap.status, 409);
  const adj = await j('POST', '/reservations', { resource_id: RES, customer_id: cust, start_at: `${day}T09:30:00-06:00`, duration_min: 30 });
  assert.equal(adj.status, 201, 'bloque contiguo (fin exclusivo) es válido');
  const third = await j('POST', '/reservations', { resource_id: RES - 1, customer_id: cust, start_at: `${day}T12:00:00-06:00`, duration_min: 30 });
  assert.equal(third.status, 422);
  assert.equal(third.body.error, 'R5_DAILY_LIMIT');

  const av = await j('GET', `/resources/${RES}/availability?date=${day}`);
  assert.equal(av.body.slots.filter((s) => !s.available).length >= 4, true);
});

t('R5 bajo concurrencia: 6 solicitudes simultáneas, solo 2 éxitos', async () => {
  const c = 3000 + Math.floor(Math.random() * 900);
  const d = `2028-11-${String(1 + Math.floor(Math.random() * 28)).padStart(2, '0')}`;
  const rs = await Promise.all([1, 2, 3, 4, 5, 6].map((i) =>
    j('POST', '/reservations', { resource_id: i, customer_id: c, start_at: `${d}T14:00:00-06:00`, duration_min: 60 })));
  assert.equal(rs.filter((r) => r.status === 201).length, 2);
  assert.equal(rs.filter((r) => r.status === 422).length, 4);
});

t('validaciones 400/422', async () => {
  assert.equal((await j('POST', '/reservations', { resource_id: 1, customer_id: 1, start_at: '2028-01-05T10:00:00-06:00', duration_min: 45 })).status, 422);
  assert.equal((await j('POST', '/reservations', { resource_id: 1, customer_id: 1, start_at: '2025-01-05T10:00:00-06:00', duration_min: 60 })).status, 422);
  assert.equal((await j('POST', '/reservations', { resource_id: 1, customer_id: 1, start_at: '2028-01-05T21:00:00-06:00', duration_min: 60 })).status, 422);
  assert.equal((await j('POST', '/reservations', { resource_id: 1 })).status, 400);
  assert.equal((await j('POST', '/reservations', { resource_id: 1, customer_id: 99999, start_at: '2028-01-05T10:00:00-06:00', duration_min: 60 })).status, 404);
});

t('listado paginado: orden, límites y totales coherentes', async () => {
  const p1 = await j('GET', '/reservations?resource_id=3&page=1&page_size=50');
  assert.equal(p1.status, 200);
  assert.equal(p1.body.data.length, 50);
  assert.equal(p1.body.total_pages, Math.ceil(p1.body.total / 50));
  const p2 = await j('GET', '/reservations?resource_id=3&page=2&page_size=50');
  const ids1 = new Set(p1.body.data.map((r) => r.id));
  assert.ok(p2.body.data.every((r) => !ids1.has(r.id)), 'páginas sin duplicados');
  const all = [...p1.body.data, ...p2.body.data];
  for (let i = 1; i < all.length; i++) assert.ok(new Date(all[i - 1].start_at) >= new Date(all[i].start_at), 'orden descendente');
  assert.ok(all.every((r) => r.resource_id === 3));

  const c = await j('GET', '/reservations?customer_id=17&from=2026-01-01&to=2026-12-31&page_size=100');
  assert.equal(c.status, 200);
  assert.ok(c.body.data.every((r) => r.customer_id === 17));
  assert.equal((await j('GET', '/reservations?page_size=101')).status, 400);
  assert.equal((await j('GET', '/reservations?page=0')).status, 400);
});
