// RECUPERACIÓN POSTERIOR SEGURA — usar cuando stress.js se detuvo por un límite de seguridad.
// Carga baja durante 3 min; debe cumplir los mismos criterios que la fase de recuperación del estrés.
import { mixedIteration, makeSummary } from './lib/common.js';

const RATE = Number(__ENV.RECOVERY_RATE || 10);

export const options = {
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
  scenarios: {
    recuperacion: {
      executor: 'constant-arrival-rate',
      rate: RATE, timeUnit: '1s', duration: __ENV.DURATION || '3m',
      preAllocatedVUs: 20, maxVUs: 100,
      tags: { phase: 'recovery' },
    },
  },
  thresholds: {
    'http_req_failed{phase:recovery}': ['rate<0.01'],
    'http_req_duration{phase:recovery}': ['p(95)<300'],
    'checks{phase:recovery}': ['rate>0.99'],
  },
  tags: { test: 'recovery' },
};

export default function () { mixedIteration(); }

export const handleSummary = makeSummary('recovery');
