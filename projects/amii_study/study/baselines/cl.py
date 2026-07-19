"""Continual-learning baseline arms (torch, CPU) — the real competition on
forgetting (axis A3).

Implemented directly on the shared 1-D backbone, NOT via Avalanche: the task is
multi-label incremental, which Avalanche's single-label class-incremental
scenarios/strategies (esp. iCaRL's exemplar + nearest-mean classifier) do not
fit cleanly. EWC, LwF, and Experience Replay are loss-/buffer-based and
label-agnostic, so a direct implementation is correct, auditable for the
supervision ledger, and runs on the same runner as every other arm. Definitions
follow the original papers (EWC: Kirkpatrick 2017; LwF: Li & Hoiem 2017; ER).
iCaRL is deferred — single-label-specific; adapt or justify-drop at freeze.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .cnn import N_CLASSES, _Net, _standardize


def _to_tensor(X, device):
    return torch.tensor(_standardize(X), dtype=torch.float32).unsqueeze(1).to(device)


class _BaseArm:
    def __init__(self, epochs: int = 40, lr: float = 3e-3, batch_size: int = 32,
                 device: str = "cpu", seed: int | None = None):
        if seed is not None:
            torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed or 0)
        self.net = _Net(N_CLASSES).to(device)
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.device = device

    def _train(self, Xt, Yt, extra_loss=None):
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        n = Xt.shape[0]
        self.net.train()
        for _ in range(self.epochs):
            perm = torch.randperm(n)
            for s in range(0, n, self.batch_size):
                idx = perm[s:s + self.batch_size]
                opt.zero_grad()
                loss = bce(self.net(Xt[idx]), Yt[idx])
                if extra_loss is not None:
                    loss = loss + extra_loss()
                loss.backward()
                opt.step()

    def predict_proba(self, X):
        self.net.eval()
        with torch.no_grad():
            return torch.sigmoid(self.net(_to_tensor(X, self.device))).cpu().numpy()

    def predict(self, X):
        return (self.predict_proba(X) > 0.5).astype(int)


class ReplayArm(_BaseArm):
    """Experience Replay: train on new data + a sample from a bounded reservoir
    memory of past examples."""

    def __init__(self, mem_size: int = 300, **kw):
        super().__init__(**kw)
        self.mem_size = mem_size
        self.memX = None
        self.memY = None
        self._seen = 0

    def fit(self, X, Y):
        X = np.asarray(X, dtype=np.float32)
        Y = np.asarray(Y, dtype=np.float32)
        if self.memX is not None and len(self.memX) > 0:
            k = min(len(self.memX), len(X))
            ridx = self.rng.choice(len(self.memX), k, replace=False)
            Xc = np.concatenate([X, self.memX[ridx]])
            Yc = np.concatenate([Y, self.memY[ridx]])
        else:
            Xc, Yc = X, Y
        self._train(_to_tensor(Xc, self.device),
                    torch.tensor(Yc, dtype=torch.float32).to(self.device))
        self._reservoir(X, Y)
        return self

    def _reservoir(self, X, Y):
        if self.memX is None:
            self.memX = np.empty((0,) + X.shape[1:], dtype=np.float32)
            self.memY = np.empty((0, Y.shape[1]), dtype=np.float32)
        for x, y in zip(X, Y):
            self._seen += 1
            if len(self.memX) < self.mem_size:
                self.memX = np.concatenate([self.memX, x[None]])
                self.memY = np.concatenate([self.memY, y[None]])
            else:
                j = int(self.rng.integers(0, self._seen))
                if j < self.mem_size:
                    self.memX[j] = x
                    self.memY[j] = y


class EWCArm(_BaseArm):
    """Elastic Weight Consolidation: penalize moving parameters important to
    earlier tasks, weighted by a diagonal Fisher information estimate."""

    def __init__(self, ewc_lambda: float = 50.0, **kw):
        super().__init__(**kw)
        self.ewc_lambda = ewc_lambda
        self.tasks = []  # list of (param_snapshot, fisher_diag)

    def fit(self, X, Y):
        Xt = _to_tensor(X, self.device)
        Yt = torch.tensor(np.asarray(Y, dtype=np.float32)).to(self.device)

        def penalty():
            if not self.tasks:
                return torch.zeros((), device=self.device)
            total = torch.zeros((), device=self.device)
            for star, fisher in self.tasks:
                for p, s, f in zip(self.net.parameters(), star, fisher):
                    total = total + (f * (p - s) ** 2).sum()
            return 0.5 * self.ewc_lambda * total

        self._train(Xt, Yt, extra_loss=penalty)
        self._consolidate(Xt, Yt)
        return self

    def _consolidate(self, Xt, Yt):
        self.net.eval()
        self.net.zero_grad()
        loss = nn.BCEWithLogitsLoss()(self.net(Xt), Yt)
        loss.backward()
        fisher = [(p.grad.detach() ** 2 if p.grad is not None else torch.zeros_like(p))
                  for p in self.net.parameters()]
        star = [p.detach().clone() for p in self.net.parameters()]
        self.tasks.append((star, fisher))
        self.net.zero_grad()


class LwFArm(_BaseArm):
    """Learning without Forgetting: distill the previous model's outputs on the
    new data (multi-label -> per-class sigmoid distillation)."""

    def __init__(self, alpha: float = 1.0, temperature: float = 2.0, **kw):
        super().__init__(**kw)
        self.alpha = alpha
        self.T = temperature
        self.old_net = None

    def fit(self, X, Y):
        Xt = _to_tensor(X, self.device)
        Yt = torch.tensor(np.asarray(Y, dtype=np.float32)).to(self.device)
        old_logits = None
        if self.old_net is not None:
            with torch.no_grad():
                old_logits = self.old_net(Xt)

        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        n = Xt.shape[0]
        self.net.train()
        for _ in range(self.epochs):
            perm = torch.randperm(n)
            for s in range(0, n, self.batch_size):
                idx = perm[s:s + self.batch_size]
                opt.zero_grad()
                out = self.net(Xt[idx])
                loss = bce(out, Yt[idx])
                if old_logits is not None:
                    soft = torch.sigmoid(old_logits[idx] / self.T)
                    loss = loss + self.alpha * F.binary_cross_entropy_with_logits(out / self.T, soft)
                loss.backward()
                opt.step()

        self.old_net = _Net(N_CLASSES).to(self.device)
        self.old_net.load_state_dict(self.net.state_dict())
        self.old_net.eval()
        return self
