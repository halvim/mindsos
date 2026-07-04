"""arc-viz standalone gate — fixtures only, no solver, no docker.

Proves (1) the two communication caps + comm DataStates register cleanly on a
CapacityLayer (valid bipartite topology — `install_viz_standalone` raises on any
contract violation), and (2) `ingest_solve` -> `express` produces the right
outcome + artifact for a solved task AND for the abstain ("I don't know") case.

    ./run_viz
"""

from __future__ import annotations

from mindsos_capacity.capacity_layer import CapacityLayer

from .capabilities import (
    ABSTAIN_TEXT,
    DS_ARTIFACT,
    DS_EXPRESSIBLE_RECORD,
    OUTCOME_ABSTAINED,
    OUTCOME_VERIFIED,
    _express,
    _ingest_solve,
    install_viz_standalone,
)
from .fixtures import ABSTAIN_5, SOLVED_2
from .human import render_html


def _run(fixture: dict):
    record = _ingest_solve(**fixture)[DS_EXPRESSIBLE_RECORD]
    artifact = _express(**{DS_EXPRESSIBLE_RECORD: record})[DS_ARTIFACT]
    return record, artifact


def main() -> int:
    # (1) registration = valid topology (register_capacity validates + raises).
    cl = CapacityLayer()
    install_viz_standalone(cl)
    print("  [ok] arc-viz: 2 communication caps (ingest_solve, express) + comm "
          "DataStates registered on a CapacityLayer (valid bipartite topology).")

    # (2a) solved + verified.
    rec, art = _run(SOLVED_2)
    assert rec["subject"]["id"] == "00d62c1b", rec["subject"]
    assert rec["outcome"] == OUTCOME_VERIFIED, rec["outcome"]
    assert rec["claim"] == "recolor [enclosed] yellow", rec["claim"]
    assert len(rec["decision_path"]) == 3, rec["decision_path"]
    kinds = [b["kind"] for b in art["content"]]
    for k in ("grid_pair", "rule", "grid_single", "outcome"):
        assert k in kinds, (k, kinds)
    assert art["summary"].startswith("Solved by recolor [enclosed] yellow"), art["summary"]
    print(f"  [ok] arc-viz: #2 recolor-enclosed -> outcome=verified; artifact summary "
          f"+ blocks {sorted(set(kinds))}.")

    # (2b) abstain -> the mind reports "I don't know".
    rec2, art2 = _run(ABSTAIN_5)
    assert rec2["outcome"] == OUTCOME_ABSTAINED, rec2["outcome"]
    assert rec2["claim"] == ABSTAIN_TEXT, rec2["claim"]
    assert any(b["kind"] == "note" for b in art2["content"]), art2["content"]
    assert art2["summary"].startswith(ABSTAIN_TEXT), art2["summary"]
    print(f"  [ok] arc-viz: #5 abstain -> outcome=abstained, '{ABSTAIN_TEXT}' expressed "
          f"(note block + NL summary).")

    # (3) human adapter renders the artifact blocks -> self-contained HTML.
    html_solved = render_html(art)
    assert "recolor [enclosed] yellow" in html_solved and "#FFDC00" in html_solved, "solved render"
    html_abstain = render_html(art2)
    assert "know how to solve this task" in html_abstain, "abstain render"  # apostrophe is HTML-escaped
    print("  [ok] arc-viz human adapter: renders #2 (grids + rule chip + verified pill) "
          "and #5 ('I don't know') to self-contained HTML.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
