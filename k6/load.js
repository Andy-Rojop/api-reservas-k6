// CARGA SOSTENIDA — tasa de llegada constante a la demanda esperada (ver docs/PLAN.md).
// Modelo abierto (arrival-rate): si el servidor se vuelve lento, k6 NO baja la tasa;
// necesita más VUs y, si llega a maxVUs, registra dropped_iterations.
import { mixedIteration, makeSummary } from './lib/common.js';

const RATE = Number(__ENV.RATE || 20);          // solicitudes/s esperadas (demanda pico definida)
const DURATION = __ENV.DURATION || '10m';

export const options = {
  discardResponseBodies: false,
  scenarios: {
    rampa: {
      executor: 'ramping-arrival-rate',
      startRate: 1, timeUnit: '1s',
      preAllocatedVUs: 20, maxVUs: 100,
      stages: [{ target: RATE, duration: '1m' }],
      tags: { phase: 'ramp' },
    },
    sostenida: {
      executor: 'constant-arrival-rate',
      rate: RATE, timeUnit: '1s', duration: DURATION,
      preAllocatedVUs: 20, maxVUs: 100,
      startTime: '1m',
      tags: { phase: 'steady' },
    },
  },
  thresholds: {
    // Umbrales de aprobación SOLO sobre la fase sostenida (la rampa es calentamiento)
    'http_req_failed{phase:steady}': ['rate<0.01'],
    'checks{phase:steady}': ['rate>0.99'],
    'http_req_duration{phase:steady,endpoint:availability}': ['p(95)<300', 'p(99)<800'],
    'http_req_duration{phase:steady,endpoint:list}': ['p(95)<500', 'p(99)<1000'],
    'http_req_duration{phase:steady,endpoint:create}': ['p(95)<500', 'p(99)<1000'],
    'dropped_iterations': [`count<${Math.ceil(RATE * 600 * 0.01)}`], // < 1 % de lo planificado
    // Límite de seguridad: abortar si el sistema colapsa durante la carga normal
    http_req_failed: [{ threshold: 'rate<0.20', abortOnFail: true, delayAbortEval: '30s' }],
  },
  tags: { test: 'load' },
};

export default function () { mixedIteration(); }

export const handleSummary = makeSummary('load');
