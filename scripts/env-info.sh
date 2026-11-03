#!/usr/bin/env bash
# Registra las condiciones de ejecución: hardware, versiones, límites, datos, caché y versión del código.
cd "$(dirname "$0")/.."
P=scripts/psql.sh
echo "=== Fecha ==="; date -Iseconds
echo; echo "=== Código ==="
echo "commit: $(git rev-parse --short HEAD 2>/dev/null) $(git describe --tags --always 2>/dev/null)"
git diff --quiet 2>/dev/null && echo "árbol: limpio" || echo "árbol: CON CAMBIOS SIN COMMIT"
echo "migraciones: $(ls db/migrations | tr '\n' ' ')"
echo; echo "=== Hardware / SO ==="
uname -srm
if [ -r /proc/cpuinfo ]; then
  grep -m1 'model name' /proc/cpuinfo; echo "núcleos lógicos: $(nproc)"
  free -m | sed -n '1,2p'
elif command -v sysctl >/dev/null; then
  sysctl -n machdep.cpu.brand_string 2>/dev/null; sysctl -n hw.ncpu hw.memsize 2>/dev/null
fi
echo; echo "=== Versiones ==="
echo "node: $(node -v 2>/dev/null)"; k6 version 2>/dev/null | head -1
docker --version 2>/dev/null
$P -tAc "select version()" 2>/dev/null
echo; echo "=== Límites de contenedores ==="
if docker compose ps --status running 2>/dev/null | grep -q reservas; then
  for c in reservas-api reservas-db; do
    docker inspect -f '{{.Name}} cpus={{.HostConfig.NanoCpus}} mem={{.HostConfig.Memory}}' "$c" 2>/dev/null \
      | awk '{split($2,a,"=");split($3,b,"="); printf "%s CPU=%.2f RAM=%d MiB\n",$1,a[2]/1e9,b[2]/1048576}'
  done
else
  echo "(sin Docker: procesos locales sin límite)"
fi
echo "PG_POOL_MAX=${PG_POOL_MAX:-10 (por defecto)}"
echo; echo "=== Datos ==="
$P -tA -F' | ' -c "select 'resources',count(*) from resources union all select 'customers',count(*) from customers
  union all select 'reservations',count(*) from reservations
  union all select 'reservas 2028 (creadas por pruebas)',count(*) from reservations where start_at >= '2028-01-01T06:00:00Z'" 2>/dev/null
echo "tamaño BD: $($P -tAc "select pg_size_pretty(pg_database_size(current_database()))" 2>/dev/null)"
echo "índices:"; $P -tAc "select '  '||indexname||': '||indexdef from pg_indexes where schemaname='public' order by tablename, indexname" 2>/dev/null
echo; echo "=== PostgreSQL / caché ==="
$P -tA -F' = ' -c "select name, setting||coalesce(unit,'') from pg_settings where name in ('shared_buffers','work_mem','max_connections','effective_cache_size','random_page_cost') order by 1" 2>/dev/null
$P -tAc "select 'cache hit ratio acumulado: '||round(100.0*blks_hit/nullif(blks_hit+blks_read,0),2)||' % (desde '||coalesce(stats_reset::text,'arranque')||')' from pg_stat_database where datname=current_database()" 2>/dev/null
$P -tAc "select 'postgres iniciado: '||pg_postmaster_start_time()" 2>/dev/null
