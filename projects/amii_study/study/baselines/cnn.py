"""1-D CNN baseline arm (torch, CPU).

A small multi-label convolutional classifier over the raw waveform. Fit
across increments continuously (naive fine-tuning) it is expected to forget
earlier concepts — the intended sanity signal for the harness, and the
"per-increment deep net" baseline of the prereg.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from ..generator import ALL_CLASSES

N_CLASSES = len(ALL_CLASSES)


class _Net(nn.Module):
    def __init__(self, n_classes: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=9, stride=2, padding=4),
            nn.ReLU(),
            nn.Conv1d(16, 32, kernel_size=9, stride=2, padding=4),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(16),
            nn.Flatten(),
            nn.Linear(32 * 16, 64),
            nn.ReLU(),
            nn.Linear(64, n_classes),
        )

    def forward(self, x):
        return self.net(x)


def _standardize(X):
    """Per-waveform z-score — raw amplitudes vary with sag/swell, so
    normalizing each signal helps the conv net learn shape, not scale."""
    X = np.asarray(X, dtype=np.float32)
    mu = X.mean(axis=1, keepdims=True)
    sd = X.std(axis=1, keepdims=True) + 1e-6
    return (X - mu) / sd


class CNNArm:
    def __init__(self, n_classes: int = N_CLASSES, epochs: int = 40, lr: float = 3e-3,
                 batch_size: int = 32, device: str = "cpu"):
        self.net = _Net(n_classes).to(device)
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.device = device

    def fit(self, X, Y):
        self.net.train()
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        loss_fn = nn.BCEWithLogitsLoss()
        Xt = torch.tensor(_standardize(X), dtype=torch.float32).unsqueeze(1).to(self.device)
        Yt = torch.tensor(np.asarray(Y), dtype=torch.float32).to(self.device)
        n = Xt.shape[0]
        for _ in range(self.epochs):
            perm = torch.randperm(n)
            for s in range(0, n, self.batch_size):
                idx = perm[s:s + self.batch_size]
                opt.zero_grad()
                loss = loss_fn(self.net(Xt[idx]), Yt[idx])
                loss.backward()
                opt.step()
        return self

    def predict(self, X):
        self.net.eval()
        with torch.no_grad():
            Xt = torch.tensor(_standardize(X), dtype=torch.float32).unsqueeze(1).to(self.device)
            probs = torch.sigmoid(self.net(Xt)).cpu().numpy()
        return (probs > 0.5).astype(int)
