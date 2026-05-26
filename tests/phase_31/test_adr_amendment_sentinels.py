"""Phase 31 — ADR amendment sentinels (Model C; parent ADR dir not COPYed into image).

4 ADR amendments per R5 ship-lock + R3 PB-30:

1. ADR-0073 §amendment-1 (4 clauses): per-layer registry / drop
   ``subscribes_to`` kwarg / ``ResidentSubscription`` eq=False /
   wrong-type raises ``ResidentError``.
2. ADR-0073 §Implementation (Phase 31).
3. ADR-0088 §Implementation (Phase 31) — granularity validated.
4. ADR-0071 §Implementation (Phase 31, separate footer) —
   ``build_bfs_capacity_declaration`` retires.

Each case skips in-container per Model C (the parent ``docs/decisions/adr/``
tree is NOT COPYed into the runtime image). The case still runs on the
host filesystem (sandbox / pre-impl test rig) where the parent tree IS
present, so the sentinel asserts the §amendment / §Implementation text
exists at ship.

This module emits +4 to the cumulative skip count in docker — Phase 30
baseline 45 skipped → Phase 31 target 49 skipped.
"""

from __future__ import annotations

import pathlib

import pytest


# Resolve the parent ADR dir relative to this halvim repo's parent
# directory (per Model C; halvim_mindsos has no .git of its own at the
# parent level — `..` is the /Layered Intelligence/ workspace root).
_PARENT_ADR_DIR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "docs" / "decisions" / "adr"
)


def _adr_path(num: int, slug: str) -> pathlib.Path:
    return _PARENT_ADR_DIR / f"{num:04d}-{slug}.md"


@pytest.mark.parametrize(
    "adr_num,slug,marker",
    [
        (73, "residents-descriptive", "## §amendment-1 (2026-05-25, Phase 31)"),
        (73, "residents-descriptive", "## §Implementation (2026-05-25, Phase 31)"),
        (88, "fine-grained-residents", "## §Implementation (2026-05-25, Phase 31)"),
        (71, "pipeline-finder-bfs", "## §Implementation (2026-05-25, Phase 31)"),
    ],
    ids=[
        "adr_0073_amendment_1",
        "adr_0073_implementation",
        "adr_0088_implementation",
        "adr_0071_implementation_phase_31",
    ],
)
def test_adr_amendment_sentinel(adr_num, slug, marker):
    """Sentinel: the ADR file contains the Phase 31 §amendment / §Implementation marker."""
    path = _adr_path(adr_num, slug)
    if not path.exists():
        # Model C — parent ADR dir not COPYed into docker image.
        pytest.skip(f"parent ADR file not present in this environment: {path}")
    text = path.read_text(encoding="utf-8")
    assert marker in text, f"missing {marker!r} in {path}"
