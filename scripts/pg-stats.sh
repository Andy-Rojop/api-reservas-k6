#!/usr/bin/env bash
# Consultas más costosas según pg_stat_statements (evidencia del lado de la base de datos).
cd "$(dirname "$0")/.."
scripts/psql.sh -c "
SELECT calls,
       round(total_exec_time)::bigint                AS total_ms,
       round(mean_exec_time::numeric, 2)             AS mean_ms,
       round(max_exec_time::numeric, 1)              AS max_ms,
       rows,
       shared_blks_hit + shared_blks_read            AS blocks,
       round((100.0 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 1) AS pct_tiempo,
       left(regexp_replace(query, '\s+', ' ', 'g'), 110) AS query
  FROM pg_stat_statements
 WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
 ORDER BY total_exec_time DESC
 LIMIT 12;"
