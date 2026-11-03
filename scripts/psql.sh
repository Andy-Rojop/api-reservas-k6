#!/usr/bin/env bash
# Ejecuta psql contra la base de la API: dentro del contenedor si docker compose está arriba,
# o con DATABASE_URL si PostgreSQL corre fuera de Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v docker >/dev/null 2>&1 && docker compose ps --status running db 2>/dev/null | grep -q db; then
  exec docker compose exec -T db psql -U reservas -d reservas -X "$@"
else
  exec psql "${DATABASE_URL:-postgres://reservas:reservas@localhost:5432/reservas}" -X "$@"
fi
