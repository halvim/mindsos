"""PB-4 A + RPB-9 A — register_after_load_observer + single fire."""

from __future__ import annotations

from typing import List

from mindsos_core.models.identity import IdentityRegistry
from mindsos_core.models.metagraph import Metagraph


def test_register_after_load_observer_returns_handle_with_unsubscribe() -> None:
    """PB-4 A — register returns ObserverHandle; unsubscribe revokes."""
    mg = Metagraph(name="m1", identity=IdentityRegistry())

    def cb(_mg: object) -> None:
        pass

    h = mg.register_after_load_observer(cb)
    assert h is not None
    assert h.is_subscribed is True
    h.unsubscribe()
    assert h.is_subscribed is False


def test_register_after_load_observer_idempotent_unsubscribe() -> None:
    """ObserverHandle unsubscribe is idempotent (Phase 06 contract)."""
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    h = mg.register_after_load_observer(lambda _mg: None)
    h.unsubscribe()
    h.unsubscribe()
    assert h.is_subscribed is False


def test_after_load_observers_list_present_on_construction() -> None:
    """Constructor initialises `_after_load_observers` to empty list."""
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    assert hasattr(mg, "_after_load_observers")
    assert isinstance(mg._after_load_observers, list)
    assert mg._after_load_observers == []


def test_after_load_observer_fires_with_metagraph(monkeypatch) -> None:
    """Programmatic check — calling _dispatch_after_load fires the observer."""
    from mindsos_core._observers import _dispatch_after_load

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    captured: List[object] = []

    def cb(received_mg: object) -> None:
        captured.append(received_mg)

    mg.register_after_load_observer(cb)
    _dispatch_after_load(mg._after_load_observers, mg)
    assert captured == [mg]


def test_multiple_after_load_observers_fire_in_registration_order() -> None:
    """Multi-observer chain — Phase 09 XRefLoader + Phase 08 InstanceLoader."""
    from mindsos_core._observers import _dispatch_after_load

    mg = Metagraph(name="m1", identity=IdentityRegistry())
    order: List[int] = []

    mg.register_after_load_observer(lambda _mg: order.append(1))
    mg.register_after_load_observer(lambda _mg: order.append(2))
    mg.register_after_load_observer(lambda _mg: order.append(3))

    _dispatch_after_load(mg._after_load_observers, mg)
    assert order == [1, 2, 3]
