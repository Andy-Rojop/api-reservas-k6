// ESTRÉS PROGRESIVO + RECUPERACIÓN.
// Sube la tasa por escalones (20 %, 40 %, … 100 % de PEAK), cada uno sostenido 2 min,
// y luego baja a carga baja (RECOVERY_RATE) durante 3 min para observar recuperación.
// Límites de seguridad: aborta si los errores o la latencia superan los topes (ver PLAN.md).
// Si aborta, la fase de recuperación NO corre: ejecutar k6/recovery.js inmediatamente después.
import { mixedIteration, makeSummary } from './lib/common.js';

const PEAK = Number(__ENV.PEAK || 100);
const RECOVERY_RATE = Number(__ENV.RECOVERY_RATE || 10);
const MAX_VUS = Number(__ENV.MAX_VUS || 300);

const steps = [0.2, 0.4, 0.6, 0.8, 1.0].map((f) => Math.max(1, Math.round(PEAK * f)));
const stages = [];
for (const s of steps) {
  stages.push({ target: s, duration: '1m' });   // subida
  stages.push({ target: s, duration: '2m' });   // meseta
}
const STRESS_MIN = stages.length * 1.5;          // 15 min

export const options = {
  scenarios: {
    estres: {
      executor: 'ramping-arrival-rate',
      startRate: 1, timeUnit: '1s',
      preAllocatedVUs: 50, maxVUs: MAX_VUS,
      stages,
      gracefulStop: '30s',
      tags: { phase: 'stress' },
    },
    recuperacion: {
      executor: 'constant-arrival-rate',
      rate: RECOVERY_RATE, timeUnit: '1s', duration: '3m',
      preAllocatedVUs: 20, maxVUs: 100,
      startTime: `${STRESS_MIN * 60 + 30}s`,     // tras el gracefulStop del estrés
      tags: { phase: 'recovery' },
    },
  },
  thresholds: {
    // --- Límites de SEGURIDAD (detienen la prueba) ---
    'http_req_failed{phase:stress}': [{ threshold: 'rate<0.10', abortOnFail: true, delayAbortEval: '1m' }],
    'http_req_duration{phase:stress}': [{ threshold: 'p(95)<5000', abortOnFail: true, delayAbortEval: '1m' }],
    // --- Criterio de RECUPERACIÓN (no aborta; se evalúa) ---
    'http_req_failed{phase:recovery}': ['rate<0.01'],
    'http_req_duration{phase:recovery}': ['p(95)<300'],
    'checks{phase:recovery}': ['rate>0.99'],
    // Informativos: siempre "pasan" pero dejan la métrica por fase en summary.json
    'http_req_duration{phase:stress,endpoint:availability}': ['p(95)<100000'],
    'http_req_duration{phase:stress,endpoint:list}': ['p(95)<100000'],
    'http_req_duration{phase:stress,endpoint:create}': ['p(95)<100000'],
    'dropped_iterations{scenario:estres}': ['count>=0'],
    'dropped_iterations{scenario:recuperacion}': ['count>=0'],
    'http_reqs{phase:stress}': ['count>=0'],
    'http_reqs{phase:recovery}': ['count>=0'],
  },
  tags: { test: 'stress' },
};

export default function () { mixedIteration(); }

export const handleSummary = makeSummary('stress');
