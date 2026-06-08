"""Phase 46 — signal-triage worker thread (ADR-0169 / D32.2=A)."""

from __future__ import annotations

import threading

from mindsos_capacity.tiers import TierEnum
from mindsos_intelligence.signal_triage import (
    SignalTriageWorker,
    passthrough_classifier,
)


def test_passthrough_classifier_reads_tier_hint():
    assert passthrough_classifier({"tier": TierEnum.CRITICAL}) is TierEnum.CRITICAL
    assert passthrough_classifier({"no": "tier"}) is TierEnum.FOREGROUND


def test_worker_is_always_on_until_stopped():
    worker = SignalTriageWorker()
    worker.start()
    assert worker.is_alive()
    worker.stop()
    assert not worker.is_alive()


def test_classification_path():
    results = []
    done = threading.Event()

    def on_classified(signal, tier):
        results.append((signal, tier))
        done.set()

    worker = SignalTriageWorker(on_classified=on_classified)
    worker.start()
    worker.submit_signal({"tier": TierEnum.CRITICAL, "id": "sig1"})
    assert done.wait(5)
    worker.stop()
    assert results[0][1] is TierEnum.CRITICAL


def test_default_tier_for_unhinted_signal():
    results = []
    done = threading.Event()

    worker = SignalTriageWorker(
        on_classified=lambda s, t: (results.append(t), done.set())
    )
    worker.start()
    worker.submit_signal({"id": "no-hint"})
    assert done.wait(5)
    worker.stop()
    assert results[0] is TierEnum.FOREGROUND
