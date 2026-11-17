#!/usr/bin/env bash
# Step 2: extract the slices.
# points_get finds the syntax-based candidates (SyVCs): library/API calls, pointer uses, array uses and arithmetic
# expressions. For each one, extract_df then collects the statements it depends on or that depend on it. That
# collection is the slice (SeVC).
source /preprocessing/lib.sh
echo "STEP 2  Extract slices"
neo4j_up; cd "$S2S"
for s in points_get extract_df; do stage "$s" "$PY27" "$s.py"; done
neo4j_down
# extract_df.py writes the focus variable as a Python list, e.g. [u'data'], while the later scripts expect just the
# name, data (see README). We also rename the files to the names make_label_sard.py looks for.
mkdir -p "$SARD"
for pair in api_slices:api pointersuse_slices:pointer arraysuse_slices:array integeroverflow_slices:expr; do
  src="$S2S/C/test_data/4/${pair%%:*}.txt"; dst="$SARD/${pair##*:}_slices.txt"
  [ -f "$src" ] && sed -E "s/\[u'([^']*)'(, u'[^']*')*\]/\1/g" "$src" > "$dst" || : > "$dst"
done
for k in api pointer array expr; do
  printf "   %-8s slices: %s\n" "$k" "$(grep -c '^------------------------------' "$SARD/${k}_slices.txt" || true)"
done
