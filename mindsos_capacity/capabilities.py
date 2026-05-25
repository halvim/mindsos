"""Capability constants used by the L3 Capacity Layer's write API.

L3 keeps its **own** copy of the capability strings it enforces rather
than importing them from :mod:`mindsos_server`. Importing anything from
``mindsos_server`` into ``mindsos_capacity`` would violate the
layer-isolation invariant (**I-S1** in the Server Layer design): no
domain layer may depend on the server module.

The parity test
``tests/phase_28/test_capabilities_parity.py::test_can_write_global_matches_server``
asserts that ``mindsos_capacity.capabilities.CAN_WRITE_GLOBAL`` equals
``mindsos_server.capabilities.CAN_WRITE_GLOBAL``. Halvim is a monorepo —
the server package is always installed in both prod + test images, so
the test does NOT use ``pytest.importorskip`` (drift caught immediately;
parallels ``tests/phase_18/test_capabilities_parity.py`` discipline).

Only one capability is enforced by L3 today: ``CAN_WRITE_GLOBAL``.
Writes to Local-scoped Capacity data (memories, capacity-state) do not
need a capability check — they are scoped to ``session.user_id`` and are
implicitly allowed. Only writes to the Global-scoped upper-layer roles
(promoted pipelines, task patterns, problem traces) are gated.

**String-value convention.** ADR-0078 §amendment-1 (Phase 28) locks the
halvim string value as UPPERCASE ``"CAN_WRITE_GLOBAL"`` (matches
``mindsos_server.capabilities`` since Phase 18 ship). The parent
non-halvim reference implementation may use a lowercase variant; halvim
deliberately diverges to preserve the parity contract that is this
ADR's whole point.
"""

from __future__ import annotations

CAN_WRITE_GLOBAL: str = "CAN_WRITE_GLOBAL"
"""Capability required to mutate the Global L3 Metagraph.

Gates Global-scoped writes such as ``promote_pipeline``,
``record_task_pattern``, ``record_problem_trace``, and any
``register_*`` call made without a session-resolved user_id (i.e.
targeting Global).
"""

__all__ = ["CAN_WRITE_GLOBAL"]
