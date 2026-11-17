"""Small helpers shared by train.py and test.py: batching, prediction, metrics and memory use."""
import resource
import numpy as np
import torch


def rss_mb():
    """Peak memory use of this process, in MB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def batches(n, size, shuffle_rng=None):
    idx = np.arange(n)
    if shuffle_rng is not None:
        shuffle_rng.shuffle(idx)
    for i in range(0, n, size):
        yield idx[i:i + size]


def to_batch(X, L, ids):
    """Trims the batch to its longest slice. Anything after that is zero padding, which the model skips anyway."""
    m = int(L[ids].max())
    return torch.from_numpy(X[ids, :m]), torch.from_numpy(L[ids])


def predict(model, X, L, size=64):
    """Returns the probability that each slice is vulnerable."""
    model.eval(); out = []
    with torch.no_grad():
        for ids in batches(len(X), size):
            x, l = to_batch(X, L, ids)
            out.append(torch.sigmoid(model(x, l)).numpy())
    return np.concatenate(out) if out else np.zeros(0)


def scores(y, p, threshold=0.5):
    """The metrics the paper reports: TP, FP, FN, TN, FPR, FNR, accuracy, precision, recall and F1."""
    pred = (p >= threshold).astype(int); y = y.astype(int)
    TP = int(((pred == 1) & (y == 1)).sum()); FP = int(((pred == 1) & (y == 0)).sum())
    FN = int(((pred == 0) & (y == 1)).sum()); TN = int(((pred == 0) & (y == 0)).sum())
    div = lambda a, b: a / b if b else 0.0
    P, R = div(TP, TP + FP), div(TP, TP + FN)
    return dict(TP=TP, FP=FP, FN=FN, TN=TN, FPR=div(FP, FP + TN), FNR=div(FN, TP + FN),
                accuracy=div(TP + TN, len(y)), precision=P, recall=R, F1=div(2 * P * R, P + R))
