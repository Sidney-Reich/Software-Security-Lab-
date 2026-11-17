#!/usr/bin/env python3
"""Runs a trained BGRU on the Juliet test split and reports the paper's metrics.

The test split is every slice from the 20% of Juliet programs that preprocessing held back from training. A slice
counts as predicted vulnerable when the model gives it a probability of 0.5 or more.

Usage: test.py MODEL_FILE VECTORS_DIR OUT_DIR [--threads N]
  MODEL_FILE   bgru.pt from train.py (or reference/training/bgru.pt)
  VECTORS_DIR  the "vectors" folder from preprocessing (we read dl_input_shuffle/test)
Writes metrics.json (metrics and inference speed) and test_predictions.csv (one row per slice) to OUT_DIR.

A note on train/test overlap: duplicates are removed before names are replaced with variable_N / func_N, so a test
slice can still end up identical, word for word, to a training slice. We count those slices, check whether their
training copies have the same label, and also report the metrics on the test slices that have no such copy.
"""
import argparse, csv, hashlib, json, os, time
import numpy as np
import torch
from bgru import BGRU
from common import predict, rss_mb, scores, to_batch
from data import load_split


def train_copies(vectors_dir, X_test):
    """For each test slice, the labels of any identical training slices (an empty set if there are none)."""
    key = lambda x: hashlib.sha1(x.tobytes()).digest()       # hash the whole padded slice: same words, same positions
    X_tr, y_tr, _, _, _ = load_split(os.path.join(vectors_dir, "dl_input_shuffle", "train"))
    seen = {}
    for x, lab in zip(X_tr, y_tr):
        seen.setdefault(key(x), set()).add(int(lab))
    return [seen.get(key(x), set()) for x in X_test]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model"); ap.add_argument("vectors"); ap.add_argument("out")
    ap.add_argument("--threads", type=int, default=0, help="CPU threads (0 = PyTorch default)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.threads:
        torch.set_num_threads(a.threads)
    bench = dict(threads=torch.get_num_threads(), torch=torch.__version__, cpus=os.cpu_count())

    model = BGRU(); model.load_state_dict(torch.load(a.model, map_location="cpu", weights_only=True)); model.eval()
    X, y, L, names, programs = load_split(os.path.join(a.vectors, "dl_input_shuffle", "test"))
    print("test: %d slices (%d vulnerable) from %d programs" % (len(y), y.sum(), len(set(programs))), flush=True)

    t = time.time(); p = predict(model, X, L)
    bench["inference_slices_per_s_batch64"] = round(len(X) / (time.time() - t), 1)
    # Also time one slice at a time, the way a code-scanning tool would run it (on the first 200 slices).
    one = [to_batch(X, L, np.array([i])) for i in range(min(200, len(X)))]
    with torch.no_grad():
        t = time.time()
        for x, l in one:
            model(x, l)
        bench["inference_ms_per_slice_batch1"] = round(1000 * (time.time() - t) / len(one), 2)
    bench["peak_rss_mb"] = round(rss_mb())

    m = scores(y, p)
    copies = train_copies(a.vectors, X)
    new = np.array([not c for c in copies], dtype=bool)
    overlap = dict(test_slices=len(y), with_identical_train_slice=int((~new).sum()),
                   same_label_in_train=sum(c == {int(l)} for c, l in zip(copies, y)),
                   other_label_in_train=sum(bool(c) and c != {int(l)} for c, l in zip(copies, y)),
                   metrics_without_them=scores(y[new], p[new]))
    with open(os.path.join(a.out, "test_predictions.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["slice", "program", "label", "probability", "predicted", "train_copy_labels"])
        for nm, pr, lab, q, c in zip(names, programs, y, p, copies):
            w.writerow([nm, pr, int(lab), round(float(q), 4), int(q >= 0.5), ";".join(map(str, sorted(c)))])
    json.dump(dict(model=a.model, test=m, train_test_overlap=overlap, benchmark=bench),
              open(os.path.join(a.out, "metrics.json"), "w"), indent=1)
    print("TEST (%d slices):  TP %d  FP %d  FN %d  TN %d" % (len(y), m["TP"], m["FP"], m["FN"], m["TN"]))
    print("  precision %.3f  recall %.3f  F1 %.3f  FPR %.3f  FNR %.3f  accuracy %.3f"
          % (m["precision"], m["recall"], m["F1"], m["FPR"], m["FNR"], m["accuracy"]))
    o, mn = overlap, overlap["metrics_without_them"]
    print("OVERLAP: %d of %d test slices have an identical train slice (%d same label, %d other label)"
          % (o["with_identical_train_slice"], len(y), o["same_label_in_train"], o["other_label_in_train"]))
    print("  without them (%d slices): TP %d  FP %d  FN %d  TN %d  F1 %.3f"
          % (int(new.sum()), mn["TP"], mn["FP"], mn["FN"], mn["TN"], mn["F1"]))


if __name__ == "__main__":
    main()
