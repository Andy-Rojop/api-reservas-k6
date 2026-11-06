#!/usr/bin/env bash
# Planes de ejecución reales (EXPLAIN ANALYZE BUFFERS) de las consultas de la API, con parámetros fijos.
# Correr con el sistema SIN carga, después de un reset. Uso: scripts/explain.sh > results/<etiqueta>/explain.txt
cd "$(dirname "$0")/.."
# En v2-fix la consulta de disponibilidad agrega una cota inferior (ver src/app.js); se refleja si existe la migración 002.
AVAIL_LOWER=""; ls db/migrations | grep -q 002_ && AVAIL_LOWER="AND start_at >= timestamptz '2026-05-04T06:00:00Z' - interval '240 minutes'"
run() { echo; echo "=================== $1"; scripts/psql.sh -c "EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF) $2"; }

run "LISTADO por recurso (página 3)" \
"SELECT r.id, r.resource_id, s.name, r.customer_id, r.start_at, r.end_at, r.status, r.created_at
   FROM reservations r JOIN resources s ON s.id = r.resource_id
  WHERE r.resource_id = 7 ORDER BY r.start_at DESC, r.id DESC LIMIT 20 OFFSET 40"
run "CONTEO del listado por recurso" "SELECT count(*) FROM reservations r WHERE r.resource_id = 7"
run "LISTADO por cliente en un año" \
"SELECT r.id, r.start_at FROM reservations r JOIN resources s ON s.id = r.resource_id
  WHERE r.customer_id = 1234 AND r.start_at >= '2026-01-01T06:00:00Z' AND r.start_at < '2027-01-01T06:00:00Z'
  ORDER BY r.start_at DESC, r.id DESC LIMIT 20 OFFSET 0"
run "CONTEO del listado por cliente" \
"SELECT count(*) FROM reservations r WHERE r.customer_id = 1234 AND r.start_at >= '2026-01-01T06:00:00Z' AND r.start_at < '2027-01-01T06:00:00Z'"
run "LISTADO general (página 30, 50 por página)" \
"SELECT r.id, r.start_at FROM reservations r JOIN resources s ON s.id = r.resource_id
  WHERE r.status = 'confirmed' ORDER BY r.start_at DESC, r.id DESC LIMIT 50 OFFSET 1450"
run "CONTEO del listado general" "SELECT count(*) FROM reservations r WHERE r.status = 'confirmed'"
run "R5: reservas del cliente en el día (dentro de POST /reservations)" \
"SELECT count(*) FROM reservations WHERE customer_id = 1234 AND status = 'confirmed'
   AND start_at >= '2028-03-01T06:00:00Z' AND start_at < '2028-03-02T06:00:00Z'"
run "DISPONIBILIDAD de un recurso en un día" \
"SELECT start_at, end_at FROM reservations WHERE resource_id = 7 AND status = 'confirmed'
   AND start_at < '2026-05-05T06:00:00Z' AND end_at > '2026-05-04T06:00:00Z' $AVAIL_LOWER ORDER BY start_at"
