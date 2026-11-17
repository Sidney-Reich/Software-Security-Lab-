#!/usr/bin/env bash
# Step 4: vectorize (the paper's "data_preprocess" step).
# Removes duplicate slices, replaces names with variable_N / func_N, trains word2vec (30 numbers per word), turns
# each slice into vectors, splits the programs 80/20 into train and test, and pads or cuts every slice to 500 words.
source /preprocessing/lib.sh
echo "STEP 4  Vectorize"
# The paper's mapping.py loads function.xls from the current directory, so run from a copy of data_preprocess.
rm -rf "$W/dp" "$W/vec"; cp -r /opt/sysevr/Implementation/data_preprocess "$W/dp"; cd "$W/dp"
stage vectorize "$PY27" /preprocessing/scripts/vectorize.py "$OUT/slices" "$OUT/labels" "$W/vec"
rm -rf "$OUT/vectors"; mkdir -p "$OUT/vectors"
cp -r "$W/vec/w2v_model" "$W/vec/dl_input_shuffle" "$W/vec/vectorize_stats.json" "$OUT/vectors/"
python3 - "$OUT/vectors/vectorize_stats.json" <<'PY'
import json, sys; s = json.load(open(sys.argv[1]))
print("   %d slices after removing %d exact duplicates (%d programs)" % (sum(s['corpus_slices'].values()), sum(s['duplicates'].values()), s['programs']))
print("   vocabulary: %d words; words per slice: median %d, max %d" % (s['vocabulary'], s['tokens_per_slice']['median'], s['tokens_per_slice']['max']))
print("   train: %(slices)d slices (%(vulnerable)d vulnerable)" % s['total_train'] + "; test: %(slices)d slices (%(vulnerable)d vulnerable)" % s['total_test'])
PY
