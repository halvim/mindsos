"""Phase 34 — fixtures for L3 write-capacity wired-path tests.

Builds on Phase 33's ``_CapAwareTestSession``; adds factory helpers for
constructing a fully-wired ``CapacityLayer(kl=...)`` with the Phase 34
write builtins installed. Per Phase 34 R1 PB-F (phase-local fixture
module pattern).

Two test modalities (R3 PB-D):

* **In-process tests** — use these fixtures to construct CapacityLayer
  + KL directly; assert on both ``InvocationResult.write_outcome`` AND
  the KL state (read-back via ``kl.metagraph_view(...)``).
* **CLI tests** — use ``CliRunner`` against ``mindsos capacity invoke``;
  assert on exit_code + stdout JSON only. The CLI's KL is constructed
  inside the handler and goes out of scope; cross-CliRunner KL
  introspection is not supported.
"""

from __future__ import annotations

from typing import FrozenSet, Optional, Tuple

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.builtins.trace import install_trace_capacities
from mindsos_knowledge import KnowledgeLayer

# Re-export Phase 33's session fixture so Phase 34 tests can import from
# one place.
from tests.phase_33._fixtures import (  # noqa: F401
    _CapAwareTestSession,
    build_session_with_caps,
    build_session_without_cap,
)


def build_writeable_capacity_layer(
    *,
    install_consolidate: bool = True,
    install_trace: bool = True,
) -> Tuple[CapacityLayer, KnowledgeLayer]:
    """Construct a CapacityLayer wired with KL + write capacity installs.

    Returns ``(layer, kl)``; tests can ``layer.invoke(...)`` AND
    introspect ``kl.metagraph_view(...)`` to assert side-effects.

    Args:
        install_consolidate: When True (default), installs the
            ``capacity:consolidate:mm`` family.
        install_trace: When True (default), installs the
            ``capacity:trace:problem`` family.
    """
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    if install_consolidate:
        install_consolidate_capacities(layer)
    if install_trace:
        install_trace_capacities(layer)
    return layer, kl


def build_admin_session(user_id: str = "admin") -> "_CapAwareTestSession":
    """Convenience: session bearing ``CAN_WRITE_GLOBAL`` (admin)."""
    return build_session_with_caps(user_id, frozenset({"CAN_WRITE_GLOBAL"}))


def build_user_session(user_id: str = "alice") -> "_CapAwareTestSession":
    """Convenience: ordinary user session (no global caps)."""
    return build_session_with_caps(user_id, frozenset())


__all__ = [
    "build_writeable_capacity_layer",
    "build_admin_session",
    "build_user_session",
    "build_session_with_caps",
    "build_session_without_cap",
]
