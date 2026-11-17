# Settings and helper functions shared by the preprocessing steps. This file is sourced, not run.
set -euo pipefail
OUT="${OUT:-/results}"; W="${W:-/work}"; PY27="${PY27:-/opt/py27/bin/python}"
S2S="$W/s2s"                                   # our copy of the paper's source2slice scripts
SARD="$S2S/C/test_data/data_source_add/sard"   # where the paper's make_label_sard.py looks for slices
mkdir -p "$OUT/logs"; BENCH="$OUT/benchmark.csv"
[ -f "$BENCH" ] || echo "stage,wall_s,user_s,sys_s,max_rss_kb,cpu_pct" > "$BENCH"

# stage NAME CMD...: runs CMD, saves its output to logs/NAME.log and adds its time, CPU and peak RAM to benchmark.csv
stage() {
  local name=$1; shift; local t0; t0=$(date +%s)
  /usr/bin/time -f "$name,%e,%U,%S,%M,%P" -a -o "$BENCH" "$@" > "$OUT/logs/$name.log" 2>&1 &
  local pid=$!
  while kill -0 "$pid" 2>/dev/null; do printf "\r   - %-20s %5ss" "$name" "$(( $(date +%s) - t0 ))"; sleep 2; done
  if ! wait "$pid"; then echo; echo "FAILED: $name (see logs/$name.log)"; tail -20 "$OUT/logs/$name.log"; exit 1; fi
  printf "\r   - %-20s %5ss\n" "$name" "$(( $(date +%s) - t0 ))"
}

# neo4j_up: starts Neo4j 2.1.5 on the Joern database. The slicing scripts query it through its REST API.
neo4j_up() {
  curl -sf http://localhost:7474/db/data/ >/dev/null && return 0
  sed -i "s#^org.neo4j.server.database.location=.*#org.neo4j.server.database.location=$W/.joernIndex#" \
      /opt/neo4j/conf/neo4j-server.properties
  # Neo4j 2.1.5 is old, and the image runs it on Java 11. After a stop it leaves data/rrd locked and the next
  # start hangs. That file only holds the web console's charts, so we just delete it before each start.
  rm -rf /opt/neo4j/data/rrd
  # Neo4j's own startup check doesn't work in a container, so start it without waiting and poll the API ourselves.
  /opt/neo4j/bin/neo4j start-no-wait > "$OUT/logs/neo4j_start.log" 2>&1
  for i in $(seq 180); do curl -sf http://localhost:7474/db/data/ >/dev/null && break; sleep 1; done
  curl -sf http://localhost:7474/db/data/ >/dev/null || { echo "Neo4j did not start"; tail -20 /opt/neo4j/data/log/console.log; exit 1; }
  # Neo4j runs as a separate process that benchmark.csv doesn't see, so we track its peak memory in the background.
  local neo; neo=$(pgrep -f org.neo4j.server | head -1)
  ( peak=$(cat "$OUT/logs/neo4j_peak_rss_kb" 2>/dev/null || echo 0)
    while kill -0 "$neo" 2>/dev/null; do r=$(awk '/VmRSS/{print $2}' /proc/$neo/status 2>/dev/null || echo 0)
      [ "${r:-0}" -gt "$peak" ] && peak=$r && echo "$peak" > "$OUT/logs/neo4j_peak_rss_kb"; sleep 1; done ) < /dev/null > /dev/null 2>&1 &
}
neo4j_down() { /opt/neo4j/bin/neo4j stop > /dev/null 2>&1 || true; }
