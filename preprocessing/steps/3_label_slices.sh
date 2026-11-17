#!/usr/bin/env bash
# Step 3: label the slices.
# Juliet's manifest.xml lists every flaw line. A slice gets label 1 (vulnerable) if it contains one, otherwise 0.
source /preprocessing/lib.sh
echo "STEP 3  Label slices"
cd "$S2S"
stage contain_all python3 /preprocessing/scripts/make_contain_all.py "$W/data/juliet/manifest.xml" "$W/src" "$S2S/contain_all.txt"
stage make_label_sard "$PY27" /preprocessing/scripts/label_with_paper.py
stage check_labels python3 /preprocessing/scripts/check_labels.py "$SARD" "$W/data/juliet/manifest.xml" "$OUT"
sed 's/^/   /' "$OUT/logs/check_labels.log"
