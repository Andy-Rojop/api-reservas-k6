#!/usr/bin/env bash
# Corre TODA la batería de una etiqueta sin supervisión (~60 min):
#   build → reset → EXPLAIN → regresión funcional → humo → 3× carga → 1× estrés (+ recuperación si aborta)
# Antes de cada carga/estrés se restablecen datos y caché con scripts/reset-env.sh (condiciones equivalentes).
#
#   git checkout v1-baseline && scripts/run-all.sh antes
#   git checkout v2-fix      && scripts/run-all.sh despues
#
# Variables opcionales: LOAD_REPS (3), STRESS_REPS (1). No cambiés PEAK/RATE entre antes y después.
set -uo pipefail
cd "$(dirname "$0")/.."
LABEL=${1:?uso: scripts/run-all.sh antes|despues}
LOAD_REPS=${LOAD_REPS:-3}; STRESS_REPS=${STRESS_REPS:-1}

# --- Protección: la etiqueta debe corresponder a la versión del código ---
HAS_FIX=0; [ -f db/migrations/002_indexes.sql ] && HAS_FIX=1
if [ "$LABEL" = antes ] && [ $HAS_FIX -eq 1 ]; then echo "✖ Estás en la versión corregida. Ejecutá: git checkout v1-baseline"; exit 1; fi
if [ "$LABEL" = despues ] && [ $HAS_FIX -eq 0 ]; then echo "✖ Falta la corrección. Ejecutá: git checkout v2-fix"; exit 1; fi
command -v k6 >/dev/null || { echo "✖ k6 no está instalado (ver docs/GUIA.md)"; exit 1; }
command -v docker >/dev/null || { echo "✖ Docker no está disponible (ver docs/GUIA.md)"; exit 1; }

mkdir -p "results/$LABEL"
exec > >(tee -a "results/$LABEL/run-all.log") 2>&1
echo "════ run-all $LABEL · $(date -Iseconds) · commit $(git rev-parse --short HEAD) $(git describe --tags --always)"

step() { echo; echo "──── $(date +%H:%M:%S) $*"; }

step "Construyendo e iniciando contenedores"
APP_VERSION=$(git describe --tags --always) docker compose up -d --build || exit 1
until curl -fs http://localhost:3000/health >/dev/null; do sleep 2; done

step "Restableciendo entorno"
scripts/reset-env.sh || exit 1

step "Planes de ejecución → results/$LABEL/explain.txt"
scripts/explain.sh > "results/$LABEL/explain.txt" 2>&1
grep -cE "Seq Scan" "results/$LABEL/explain.txt" | sed 's/^/  Seq Scan encontrados: /'

step "Regresión funcional → results/$LABEL/regresion.txt"
docker compose exec -T api sh -c 'API_URL=http://localhost:3000 node --test --test-concurrency=1 test/*.test.js' \
  > "results/$LABEL/regresion.txt" 2>&1
grep -E "^# (tests|pass|fail)" "results/$LABEL/regresion.txt"
grep -q "^# fail 0" "results/$LABEL/regresion.txt" || { echo "✖ Regresión funcional falló: no se mide"; exit 1; }

step "Humo"
scripts/reset-env.sh && scripts/run-test.sh smoke "$LABEL" | tail -6

for i in $(seq 1 "$LOAD_REPS"); do
  step "Carga sostenida $i/$LOAD_REPS (11 min)"
  scripts/reset-env.sh && scripts/run-test.sh load "$LABEL" | grep -E "^■|fase|steady"
done

for i in $(seq 1 "$STRESS_REPS"); do
  step "Estrés $i/$STRESS_REPS (~19 min)"
  scripts/reset-env.sh && scripts/run-test.sh stress "$LABEL" | grep -E "^■|fase|stress |recovery "
  LAST=$(ls -d results/"$LABEL"/stress-* | tail -1)
  if grep -qE "stopping test prematurely" "$LAST/k6-stdout.log"; then
    step "Estrés detenido por límite de seguridad → recuperación posterior segura (3 min)"
    grep -E "stopping test prematurely" "$LAST/k6-stdout.log" | tee "$LAST/interrupcion.txt"
    scripts/run-test.sh recovery "$LABEL" | grep -E "^■|recovery "
  fi
done

step "Fin. Resultados en results/$LABEL/"
ls -1 "results/$LABEL"
