"""SySeVR's BGRU (Li et al., IEEE TDSC 2022), ported to PyTorch from the authors' Keras code
(Implementation/model/bgru.py, build_model):

    Masking(0) -> Bidirectional(GRU 256, return_sequences) -> Dropout(0.2)
               -> Bidirectional(GRU 256)                   -> Dropout(0.2) -> Dense(1, sigmoid)

PyTorch's GRU forces two small differences, both listed in the README: the gates use the normal sigmoid instead of
Keras' hard_sigmoid, and each gate has a second bias vector (1,625,601 parameters instead of 1,622,529, +0.2%).
Masking is done with packed sequences, so the all-zero padding vectors are skipped, just as Keras' Masking layer does.
"""
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence


class BGRU(nn.Module):
    def __init__(self, vector_dim=30, units=256, layers=2, dropout=0.2):
        super().__init__()
        # With num_layers=2, PyTorch applies the dropout to the first BiGRU's output, as the Keras model does.
        self.gru = nn.GRU(vector_dim, units, num_layers=layers, dropout=dropout, bidirectional=True, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(2 * units, 1)
        self.keras_init()

    def keras_init(self):
        """Same starting weights as Keras: glorot_uniform for inputs, orthogonal for recurrent weights, zero biases."""
        for name, p in self.named_parameters():
            if "weight_ih" in name:
                for w in p.data.chunk(3, 0):
                    nn.init.xavier_uniform_(w)
            elif "weight_hh" in name:
                for w in p.data.chunk(3, 0):
                    nn.init.orthogonal_(w)
            elif "bias" in name:
                nn.init.zeros_(p)
        nn.init.xavier_uniform_(self.out.weight)

    def forward(self, x, lengths):
        """x holds the zero-padded word vectors, shape (batch, time, 30); lengths is the real number of words per slice.
        Returns one logit per slice; sigmoid(logit) is the probability that the slice is vulnerable."""
        packed = pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, h = self.gru(packed)                      # h: (layers*2, batch, units)
        last = torch.cat([h[-2], h[-1]], dim=1)      # last layer: forward ends at the last word, backward at the first
        return self.out(self.drop(last)).squeeze(1)


def count_parameters(model):
    return sum(p.numel() for p in model.parameters())
