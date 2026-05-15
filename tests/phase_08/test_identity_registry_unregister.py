"""RR-1 A — IdentityRegistry.unregister(uid) present + idempotent.

Step-0 audit found `unregister` already present in halvim_mindsos
(Phase 02 surface). This test pins the contract so future Phase 06
refactors don't drop it.
"""

from __future__ import annotations

from mindsos_core.models.identity import IdentityRegistry


def test_unregister_exists_as_public_method() -> None:
    r = IdentityRegistry()
    assert hasattr(r, "unregister")
    assert callable(r.unregister)


def test_unregister_removes_registered_id() -> None:
    r = IdentityRegistry()
    r.register("id-1")
    assert "id-1" in r
    r.unregister("id-1")
    assert "id-1" not in r


def test_unregister_is_idempotent_on_already_removed() -> None:
    """Idempotent — calling on absent id is a no-op (Phase 02 contract).

    The current halvim implementation uses ``self._ids.discard(uid)``
    which is silent. Phase 08 reconstruction relies on this idempotency
    (recover/refresh paths may unregister already-removed ids).
    """
    r = IdentityRegistry()
    # No registration, then unregister — must not raise.
    r.unregister("never-registered")
    r.unregister("never-registered")
