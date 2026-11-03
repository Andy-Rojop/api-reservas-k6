#!/usr/bin/env bash
# Deja el entorno en el MISMO estado inicial antes de cada medición:
#   1) datos restablecidos (semilla determinística)  2) contenedores reiniciados (caché de PostgreSQL vacía)
#   3) calentamiento con la prueba de humo (caché caliente y conexiones del pool abiertas)
# La caché de páginas del sistema operativo NO se controla; se declara en el informe.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "▶ Restableciendo datos…"
docker compose exec -T api node scripts/db-reset.js
echo "▶ Reiniciando contenedores (caché fría de PostgreSQL)…"
docker compose restart db >/dev/null
until docker compose exec -T db pg_isready -U reservas -d reservas >/dev/null 2>&1; do sleep 1; done
docker compose restart api >/dev/null
until curl -fs http://localhost:3000/health >/dev/null; do sleep 1; done
echo "▶ Calentamiento: humo de 1 min (también valida que todo funciona)…"
mkdir -p results/ultimo
k6 run -q -e OUT_DIR=results/ultimo k6/smoke.js >/dev/null 2>&1 \
  && echo "✔ Entorno listo (humo OK)" \
  || { echo "✖ El humo falló: NO ejecutar carga/estrés. Revisar: k6 run k6/smoke.js"; exit 1; }
docker compose exec -T db psql -U reservas -d reservas -qc "SELECT pg_stat_statements_reset()" >/dev/null
