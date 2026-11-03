// HUMO — 1 VU, ~1 min. Verifica que todo responde y que las reglas de negocio se cumplen
// antes de aplicar carga. Si falla, NO se ejecutan carga ni estrés.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, availability, listReservations, createReservation, makeSummary } from './lib/common.js';

export const options = {
  vus: 1,
  duration: __ENV.DURATION || '1m',
  thresholds: {
    checks: ['rate==1.0'],
    http_req_failed: ['rate==0'],
    'http_req_duration{endpoint:availability}': ['p(95)<300'],
    'http_req_duration{endpoint:list}': ['p(95)<500'],
    'http_req_duration{endpoint:create}': ['p(95)<500'],
  },
  tags: { test: 'smoke' },
};

const J = { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'rules', name: 'reglas' } };

export function setup() {
  const h = http.get(`${BASE_URL}/health`);
  if (h.status !== 200) throw new Error(`API no disponible en ${BASE_URL}`);
  // Reglas de negocio de punta a punta (una vez por corrida)
  const day = `2028-12-${String(1 + Math.floor(Math.random() * 28)).padStart(2, '0')}`;
  const cust = 4500 + Math.floor(Math.random() * 400);
  const post = (b) => http.post(`${BASE_URL}/reservations`, JSON.stringify(b), J);
  const a = post({ resource_id: 39, customer_id: cust, start_at: `${day}T08:00:00-06:00`, duration_min: 60 });
  const ov = post({ resource_id: 39, customer_id: cust + 1, start_at: `${day}T08:30:00-06:00`, duration_min: 60 });
  const b = post({ resource_id: 38, customer_id: cust, start_at: `${day}T10:00:00-06:00`, duration_min: 60 });
  const lim = post({ resource_id: 37, customer_id: cust, start_at: `${day}T12:00:00-06:00`, duration_min: 60 });
  const dur = post({ resource_id: 37, customer_id: cust + 2, start_at: `${day}T12:00:00-06:00`, duration_min: 45 });
  const past = post({ resource_id: 37, customer_id: cust + 2, start_at: '2025-06-02T12:00:00-06:00', duration_min: 60 });
  check(null, {
    'R4 crea primera reserva (201)': () => a.status === 201,
    'R4 traslape rechazado (409)': () => ov.status === 409,
    'R5 segunda del día permitida (201)': () => b.status === 201,
    'R5 tercera del día rechazada (422)': () => lim.status === 422,
    'R1 duración inválida (422)': () => dur.status === 422,
    'R3 pasado rechazado (422)': () => past.status === 422,
  });
}

export default function () {
  availability();
  listReservations();
  createReservation();
  sleep(1);
}

export const handleSummary = makeSummary('smoke');
