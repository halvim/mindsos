"""Trivial reference skill bundle (Phase 50 — design log S12).

Test-fixture package, deliberately NOT ``mindsos_capacity/builtins/``:
the bundle exercises the ADR-0183 install lifecycle (install /
de-install / provenance / idempotency ONLY — not "installed skill
runs"; Phase 49 PB-1a dispatch work is WSD's). Contents: 1 DataState
(``text.ref_shouted``) + 1 CapacityContext-native ``text.*`` capacity
(``text.ref_shout``) + 3 L2 content nodes (in ``manifest.toml``).
"""

from pathlib import Path

#: The bundle's manifest path, for tests + CLI exercises.
MANIFEST_PATH = Path(__file__).parent / "manifest.toml"
