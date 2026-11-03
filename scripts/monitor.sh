#!/usr/bin/env bash
# Muestrea recursos cada INTERVAL s hasta recibir SIGTERM. Uso: scripts/monitor.sh salida.csv
# Columnas: epoch, cpu_api_%, mem_api_MiB, cpu_db_%, mem_db_MiB, cpu_k6_%, pg_conexiones_activas, pg_esperando_lock
# CPU en % de UN núcleo (100 = 1 núcleo completo), medido como delta entre muestras (no promedio histórico).
# Requiere Linux o WSL2 (usa /proc para el CPU de k6 y de los procesos locales).
cd "$(dirname "$0")/.."
OUT=$1; INTERVAL=${INTERVAL:-2}
echo "epoch,cpu_api,mem_api_mib,cpu_db,mem_db_mib,cpu_k6,pg_active,pg_lock_wait" > "$OUT"
DOCKER=0
docker compose ps --status running 2>/dev/null | grep -q reservas-api && DOCKER=1
HZ=$(getconf CLK_TCK 2>/dev/null || echo 100)

ticks() { # suma utime+stime de los PIDs dados
  local t=0 p
  for p in "$@"; do
    [ -r "/proc/$p/stat" ] && t=$((t + $(awk '{print $14+$15}' "/proc/$p/stat" 2>/dev/null || echo 0)))
  done; echo $t
}
rss_mib() { local m=0 p; for p in "$@"; do m=$((m + $(awk '/VmRSS/{print $2}' "/proc/$p/status" 2>/dev/null || echo 0))); done; awk -v m=$m 'BEGIN{printf "%.1f", m/1024}'; }
to_mib() { awk '{v=$1; u=v; gsub(/[0-9.]/,"",u); gsub(/[A-Za-z]/,"",v);
        if(u=="GiB")v*=1024; else if(u=="KiB"||u=="kB")v/=1024; else if(u=="B")v/=1048576; printf "%.1f", v}'; }

declare -A prev; prev_ts=$(date +%s%N)
pids_api() { pgrep -f '^node src/server.js'; }
pids_db()  { pgrep -x postgres; }
pids_k6()  { pgrep -x k6; }
for k in api db k6; do prev[$k]=$(ticks $(pids_$k)); done

running=1; trap 'running=0' TERM INT
while [ $running -eq 1 ]; do
  sleep "$INTERVAL" & wait $!
  now=$(date +%s%N); el=$(( (now - prev_ts) / 1000000 )); prev_ts=$now   # ms
  declare -A cpu
  for k in api db k6; do
    t=$(ticks $(pids_$k)); cpu[$k]=$(awk -v d=$((t - prev[$k])) -v el=$el -v hz=$HZ 'BEGIN{ if(d<0)d=0; printf "%.1f", 100*d/hz/(el/1000)}'); prev[$k]=$t
  done
  if [ $DOCKER -eq 1 ]; then
    stats=$(docker stats --no-stream --format '{{.Name}};{{.CPUPerc}};{{.MemUsage}}' reservas-api reservas-db 2>/dev/null)
    ca=$(echo "$stats" | awk -F';' '$1=="reservas-api"{gsub("%","",$2);print $2}')
    ma=$(echo "$stats" | awk -F';' '$1=="reservas-api"{print $3}' | to_mib)
    cd_=$(echo "$stats" | awk -F';' '$1=="reservas-db"{gsub("%","",$2);print $2}')
    md=$(echo "$stats" | awk -F';' '$1=="reservas-db"{print $3}' | to_mib)
  else
    ca=${cpu[api]}; ma=$(rss_mib $(pids_api)); cd_=${cpu[db]}; md=$(rss_mib $(pids_db))
  fi
  pg=$(scripts/psql.sh -tA -F, -c "select count(*) filter (where state='active'), count(*) filter (where wait_event_type='Lock') from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid()" 2>/dev/null || echo ",")
  echo "$(date +%s),${ca:-},${ma:-},${cd_:-},${md:-},${cpu[k6]},${pg}" >> "$OUT"
done
