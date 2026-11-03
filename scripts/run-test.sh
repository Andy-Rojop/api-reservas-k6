#!/usr/bin/env bash
# Ejecuta un escenario k6 guardando TODA la evidencia original en results/<etiqueta>/<escenario>-<fecha>/
#
#   scripts/run-test.sh smoke    antes
#   scripts/run-test.sh load     antes
#   scripts/run-test.sh stress   antes  -e PEAK=100
#   scripts/run-test.sh recovery antes      # solo si stress se detuvo por seguridad
#
# Archivos generados: env.txt, k6-stdout.log, summary.json/.txt, raw.csv.gz (cada muestra),
# resources.csv (CPU/RAM/conexiones), pg_stat_statements.txt, invariants.txt, exit_code.txt
set -uo pipefail
cd "$(dirname "$0")/.."
SCEN=${1:?escenario: smoke|load|stress|recovery}; LABEL=${2:?etiqueta: antes|despues}; shift 2
OUT="results/$LABEL/$SCEN-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

echo "▶ Condiciones → $OUT/env.txt"; scripts/env-info.sh > "$OUT/env.txt" 2>&1
scripts/psql.sh -qc "SELECT pg_stat_statements_reset()" >/dev/null 2>&1 || true
scripts/monitor.sh "$OUT/resources.csv" & MON=$!

echo "▶ k6 run k6/$SCEN.js $*"
k6 run --out "csv=$OUT/raw.csv.gz" -e OUT_DIR="$OUT" "$@" "k6/$SCEN.js" 2>&1 | tee "$OUT/k6-stdout.log"
RC=${PIPESTATUS[0]}

kill -TERM $MON 2>/dev/null; wait $MON 2>/dev/null
echo "$RC" > "$OUT/exit_code.txt"
scripts/pg-stats.sh > "$OUT/pg_stat_statements.txt" 2>&1
if docker compose ps --status running 2>/dev/null | grep -q reservas-api; then
  docker compose exec -T api node scripts/verify-invariants.js > "$OUT/invariants.txt" 2>&1
else
  DATABASE_URL=${DATABASE_URL:-postgres://reservas:reservas@localhost:5432/reservas} node scripts/verify-invariants.js > "$OUT/invariants.txt" 2>&1
fi
INV=$?

echo
echo "■ k6 código de salida: $RC  (0 = umbrales OK · 99 = umbral incumplido o abortado por seguridad)"
grep -qE "stopping test prematurely|aborted" "$OUT/k6-stdout.log" && echo "■ PRUEBA DETENIDA POR LÍMITE DE SEGURIDAD → ejecutar: scripts/run-test.sh recovery $LABEL"
[ $INV -eq 0 ] && echo "■ Reglas de negocio: conservadas" || echo "■ Reglas de negocio: ¡ROTAS! ver $OUT/invariants.txt"
echo "■ Evidencia original en $OUT"
command -v python3 >/dev/null && python3 scripts/analyze.py "$OUT" || true
