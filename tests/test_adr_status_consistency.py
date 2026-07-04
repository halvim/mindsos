"""Gate guard: ADR status must agree across file, README, and summaries.

Wraps ``tools/check_adr_status_consistency.py`` so the existing
``pytest tests/`` gate fails loud if any ADR's status drifts between its
front-matter, its prose ``**Status:**`` line, the ADR index README, and
the per-layer summary tables. Added in the 2026-07 doc-vs-code audit to
stop the decision index from silently rotting again.
"""

import importlib.util
from pathlib import Path

_CHECKER = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "check_adr_status_consistency.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("adr_status_checker", _CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_adr_status_consistent_across_docs():
    mod = _load()
    adr_status, file_problems = mod.load_adr_statuses()
    assert adr_status, "no ADRs found — checker path or glob is wrong"
    assert not file_problems, (
        "ADR file status inconsistencies (front-matter vs prose):\n  "
        + "\n  ".join(file_problems)
    )
    index_problems = []
    for path in [mod.README, *sorted(mod.SUMMARY_DIR.glob("*.md"))]:
        if path.exists():
            index_problems += mod.check_index(path, adr_status)
    assert not index_problems, (
        "ADR index/summary status disagrees with the ADR files:\n  "
        + "\n  ".join(index_problems)
    )
