"""Loads the preprocessing output (vectors/dl_input_shuffle/{train,test}/*.pkl).

Each file is what the paper's dealrawdata writes (from Python 2): [X, labels, funcs, filenames, testcases].
Every slice in X is 500 word vectors of 30 numbers, padded with zeros.
Files are read in sorted order, so every run sees the slices in the same order."""
import os, pickle
import numpy as np


def load_split(folder):
    X, y, names, programs = [], [], [], []
    for f in sorted(os.listdir(folder)):
        if not f.endswith(".pkl"):
            continue
        with open(os.path.join(folder, f), "rb") as fh:
            xs, labels, funcs, filenames, testcases = pickle.load(fh, encoding="latin1")
        X += [np.asarray(x, dtype=np.float32) for x in xs]
        y += [1 if l == 1 else 0 for l in labels]          # what the paper's multi_labels_to_two does
        names += list(filenames); programs += list(testcases)
    X = np.stack(X) if X else np.zeros((0, 500, 30), np.float32)
    lengths = (np.abs(X).sum(axis=2) > 0).sum(axis=1)       # real words per slice; Keras masks all-zero vectors
    return X, np.asarray(y, dtype=np.float32), lengths, names, programs
