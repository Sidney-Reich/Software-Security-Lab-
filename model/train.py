#!/usr/bin/env python3
"""Trains SySeVR's BGRU on the Juliet train split, with the settings from the paper.

Settings: batch size 16, Adamax with learning rate 0.002, binary cross-entropy, dropout 0.2, two BiGRU layers of 256
units, 20 epochs. The shuffle seed is 2018, as in the authors' bgru.py. This script only reads the train split;
test.py takes care of the test split.

Usage: train.py VECTORS_DIR OUT_DIR [--epochs 20] [--batch 16] [--threads N] [--seed 2018]
  VECTORS_DIR  the "vectors" folder from preprocessing (we read dl_input_shuffle/train)
Writes bgru.pt (the weights), training.json (settings, time, memory) and epochs.csv (one row per epoch) to OUT_DIR.
"""
import argparse, csv, json, os, time
import numpy as np
import torch
from torch import nn
from bgru import BGRU, count_parameters
from common import batches, rss_mb, to_batch
from data import load_split


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vectors"); ap.add_argument("out")
    ap.add_argument("--epochs", type=int, default=20); ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--threads", type=int, default=0, help="CPU threads (0 = PyTorch default)")
    ap.add_argument("--seed", type=int, default=2018)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.threads:
        torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed); rng = np.random.RandomState(a.seed)
    bench = dict(threads=torch.get_num_threads(), torch=torch.__version__, cpus=os.cpu_count())

    t = time.time()
    X, y, L, _, _ = load_split(os.path.join(a.vectors, "dl_input_shuffle", "train"))
    bench["load_data_s"] = round(time.time() - t, 1)
    print("train: %d slices (%d vulnerable), words per slice max %d" % (len(y), y.sum(), L.max()), flush=True)

    model = BGRU()
    bench["parameters"] = count_parameters(model)
    opt = torch.optim.Adamax(model.parameters(), lr=0.002)
    loss_fn = nn.BCEWithLogitsLoss()               # sigmoid + binary cross-entropy in one numerically stable step
    rows = []
    t_train = time.time()
    for ep in range(1, a.epochs + 1):
        model.train(); t0 = time.time(); c0 = time.process_time(); tot, n = 0.0, 0
        for ids in batches(len(X), a.batch, rng):
            x, l = to_batch(X, L, ids)
            opt.zero_grad()
            loss = loss_fn(model(x, l), torch.from_numpy(y[ids]))
            loss.backward(); opt.step()
            tot += loss.item() * len(ids); n += len(ids)
            if (n // a.batch) % 10 == 0:
                print("\r  epoch %d: %4d/%d slices, loss %.4f" % (ep, n, len(X), tot / n), end="", flush=True)
        wall = time.time() - t0; cpu = time.process_time() - c0
        rows.append(dict(epoch=ep, train_loss=round(tot / n, 4), wall_s=round(wall, 1), cpu_pct=round(100 * cpu / wall),
                         ms_per_slice=round(1000 * wall / n, 1), peak_rss_mb=round(rss_mb())))
        print("\repoch %(epoch)2d  loss %(train_loss).4f  %(wall_s)6.1f s  (%(ms_per_slice).1f ms/slice, CPU %(cpu_pct)d%%)" % rows[-1],
              flush=True)
    bench["train_s"] = round(time.time() - t_train, 1)

    torch.save(model.state_dict(), os.path.join(a.out, "bgru.pt"))
    bench["model_file_mb"] = round(os.path.getsize(os.path.join(a.out, "bgru.pt")) / 1e6, 2)
    bench["peak_rss_mb"] = round(rss_mb())
    with open(os.path.join(a.out, "epochs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    json.dump(dict(settings=vars(a), benchmark=bench), open(os.path.join(a.out, "training.json"), "w"), indent=1)
    print("saved %s; training %.1f min" % (os.path.join(a.out, "bgru.pt"), bench["train_s"] / 60))


if __name__ == "__main__":
    main()
