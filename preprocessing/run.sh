#!/usr/bin/env bash
# Preprocessing: takes the Juliet 1.3 CWE-416 programs, cuts them into SySeVR slices, labels the slices,
# turns them into word vectors and splits them into a train set and a test set.
# Usage inside the image: run.sh [all | N | name1,name2]
#   all (the default) uses all 459 test cases, N takes a small sample of N test cases, or name the ones you want.
# Everything goes to $OUT (/results by default): slices/, labels/, slices_index.csv, vectors/, benchmark.csv, logs/
set -euo pipefail
SEL="${1:-all}"; export OUT="${OUT:-/results}" W="${W:-/work}"
rm -f "$OUT/benchmark.csv"            # start fresh; lib.sh writes the header line
source /preprocessing/lib.sh
# This container runs as root. If the host passed in its user id (run.sh does), give the results back to that
# user on exit, even after a failure, so they can be deleted later without sudo.
[ -n "${HOST_UID:-}" ] && trap 'chown -R "$HOST_UID:${HOST_GID:-$HOST_UID}" "$OUT"' EXIT
T0=$(date +%s)

echo "STEP 0  Get Juliet 1.3 CWE-416 and select the test cases"
[ -d "$W/data/juliet/testcases" ] || stage fetch_juliet /preprocessing/scripts/fetch_juliet.sh "$W/data"
stage select_programs python3 /preprocessing/scripts/select_programs.py "$W/data/juliet" "$W/src" "$SEL"
sed 's/^/   /' "$OUT/logs/select_programs.log"

for s in 1_build_graphs 2_extract_slices 3_label_slices 4_vectorize; do bash "/preprocessing/steps/$s.sh"; done

echo; echo "Done in $(( $(date +%s) - T0 )) s. Per-stage time, CPU and peak RAM: benchmark.csv"
echo "Neo4j server peak RAM: $(( $(cat "$OUT/logs/neo4j_peak_rss_kb" 2>/dev/null || echo 0) / 1024 )) MB"
