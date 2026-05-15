"""attach_xref_loader — M18 idempotent observer subscription."""

from __future__ import annotations

from mindsos_core import Metagraph
from mindsos_core.reconstruction.xref_loader import attach_xref_loader


def test_attach_xref_loader_returns_observer_handle():
    mg = Metagraph(name="m")
    handle = attach_xref_loader(mg)
    assert handle is not None
    # Handle has unsubscribe per Phase 06 P49 B.
    assert hasattr(handle, "unsubscribe")


def test_attach_xref_loader_idempotent_p49b():
    """M18 + Phase 06 P49 B precedent — re-attach returns same handle."""
    mg = Metagraph(name="m")
    h1 = attach_xref_loader(mg)
    h2 = attach_xref_loader(mg)
    assert h1 is h2


def test_attach_xref_loader_subscribes_to_after_load():
    """The helper subscribes via register_after_load_observer."""
    mg = Metagraph(name="m")
    n_observers_before = len(mg._after_load_observers)
    attach_xref_loader(mg)
    n_observers_after = len(mg._after_load_observers)
    assert n_observers_after == n_observers_before + 1


def test_attach_xref_loader_observer_no_op_without_persist_client():
    """Observer reads mg._persist_client at fire time; absent ⇒ silent no-op.

    Fresh-in-memory metagraphs (not loaded from DB) have nothing to
    load; the observer must NOT crash when fired in this state.
    """
    from mindsos_core._observers import _dispatch_after_load

    mg = Metagraph(name="m")
    attach_xref_loader(mg)
    # _persist_client is absent (None); no client to load from.
    # Manually fire the after_load dispatch — should NOT raise.
    _dispatch_after_load(mg._after_load_observers, mg)
    # mg.xrefs unchanged.
    assert mg.xrefs == {}
