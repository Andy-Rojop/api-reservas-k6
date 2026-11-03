// Funciones compartidas por todos los escenarios k6.
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';
import { textSummary } from './k6-summary.js';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

// 409 (traslape R4) y 422 (límite R5) son respuestas de NEGOCIO correctas, no fallas del servidor.
http.setResponseCallback(http.expectedStatuses(200, 201, 409, 422));

export const businessRejections = new Counter('business_rejections');
export const reservationsCreated = new Counter('reservations_created');

const JSON_HEADERS = { 'Content-Type': 'application/json' };
const RESOURCES = 40;
const CUSTOMERS = 5000;

// Generador pseudoaleatorio con semilla (por VU) para que la secuencia sea reproducible.
let seed = (Number(__ENV.SEED || 42) * 1_000_003 + (__VU || 0) * 7919) >>> 0;
export function rnd() {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296;
}
const pick = (n) => 1 + Math.floor(rnd() * n);
const pad = (n) => String(n).padStart(2, '0');

function seededDate() {
  // Fechas con datos sembrados (2025-01-01 .. 2027-12-31)
  const d = new Date(Date.UTC(2025, 0, 1) + Math.floor(rnd() * 1095) * 86_400_000);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- operaciones
export function availability() {
  const id = pick(RESOURCES);
  const date = seededDate();
  const res = http.get(`${BASE_URL}/resources/${id}/availability?date=${date}`, {
    tags: { endpoint: 'availability', name: 'GET /resources/:id/availability' },
  });
  check(res, {
    'availability 200': (r) => r.status === 200,
    'availability 24 bloques': (r) => r.status === 200 && (r.json('slots') || []).length === 24,
  }, { endpoint: 'availability' });
  return res;
}

export function listReservations() {
  const v = rnd();
  let qs;
  if (v < 0.6) {
    qs = `resource_id=${pick(RESOURCES)}&page=${pick(5)}&page_size=20`;
  } else if (v < 0.9) {
    const y = 2025 + Math.floor(rnd() * 3);
    qs = `customer_id=${pick(CUSTOMERS)}&from=${y}-01-01&to=${y}-12-31&page=1&page_size=20`;
  } else {
    qs = `status=confirmed&page=${pick(50)}&page_size=50`;
  }
  const res = http.get(`${BASE_URL}/reservations?${qs}`, {
    tags: { endpoint: 'list', name: 'GET /reservations' },
  });
  check(res, {
    'list 200': (r) => r.status === 200,
    'list paginación coherente': (r) => {
      if (r.status !== 200) return false;
      const b = r.json();
      return Array.isArray(b.data) && b.data.length <= b.page_size && b.total_pages === Math.ceil(b.total / b.page_size);
    },
  }, { endpoint: 'list' });
  return res;
}

export function createReservation() {
  // 2028 está vacío en la semilla: las pruebas crean ahí.
  const day = new Date(Date.UTC(2028, 0, 1) + Math.floor(rnd() * 366) * 86_400_000).toISOString().slice(0, 10);
  const duration = [30, 60, 90, 120][Math.floor(rnd() * 4)];
  const latestStartHalfHours = (20 * 60 - duration - 8 * 60) / 30; // cabe antes de 20:00
  const startMin = 8 * 60 + Math.floor(rnd() * (latestStartHalfHours + 1)) * 30;
  const body = JSON.stringify({
    resource_id: pick(RESOURCES),
    customer_id: pick(CUSTOMERS),
    start_at: `${day}T${pad(Math.floor(startMin / 60))}:${pad(startMin % 60)}:00-06:00`,
    duration_min: duration,
  });
  const res = http.post(`${BASE_URL}/reservations`, body, {
    headers: JSON_HEADERS,
    tags: { endpoint: 'create', name: 'POST /reservations' },
  });
  check(res, {
    'create 201|409|422': (r) => [201, 409, 422].includes(r.status),
    'create 201 devuelve id': (r) => r.status !== 201 || Number(r.json('id')) > 0,
  }, { endpoint: 'create' });
  if (res.status === 201) reservationsCreated.add(1);
  if (res.status === 409 || res.status === 422) businessRejections.add(1, { endpoint: 'create', status: String(res.status) });
  return res;
}

// Mezcla de tráfico: 60 % disponibilidad, 25 % listado, 15 % creación.
export function mixedIteration() {
  const v = rnd();
  if (v < 0.60) return availability();
  if (v < 0.85) return listReservations();
  return createReservation();
}

// ---------------------------------------------------------------- resumen
export function makeSummary(name) {
  return function handleSummary(data) {
    const dir = __ENV.OUT_DIR || 'results/ultimo';
    return {
      stdout: textSummary(data, { indent: ' ', enableColors: true }),
      [`${dir}/summary.json`]: JSON.stringify(data, null, 2),
      [`${dir}/summary.txt`]: textSummary(data, { indent: ' ', enableColors: false }),
    };
  };
}
