"""arc-viz human adapter — render a communication artifact as a visual page.

TRANSPORT, not a capacity: a pure function over `comm.artifact` (its typed content
blocks) → a self-contained HTML page (coloured ARC grids, enclosed region
outlined, rule chip, outcome pill, NL summary). Understands the closed block kinds
from ARC_VIZ_CONTRACT_SPEC.md §3; a machine adapter would instead emit the artifact
as JSON.
"""

from __future__ import annotations

import html as _html
from typing import List, Optional

# ARC palette (0-9).
PALETTE = ["#000000", "#0074D9", "#FF4136", "#2ECC40", "#FFDC00",
           "#AAAAAA", "#F012BE", "#FF851B", "#7FDBFF", "#870C25"]

_OUTCOME_STYLE = {
    "verified": ("#137333", "#e6f4ea", "verified — matches the withheld test"),
    "solved_unverified": ("#1a56b8", "#e8f0fe", "solved"),
    "wrong": ("#a50e0e", "#fce8e6", "wrong — does not match the test"),
    "abstained": ("#5f6368", "#f1f3f4", "I don't know"),
    "inapplicable": ("#b06000", "#fef7e0", "rule set did not apply"),
}


def _esc(s) -> str:
    return _html.escape(str(s))


def _grid(cells, enclosed: Optional[List[List[int]]] = None, cell: int = 20) -> str:
    if not cells:
        return '<div class="muted">(no grid)</div>'
    enc = {(r, c) for r, c in (enclosed or [])}
    cols = len(cells[0])
    out = [f'<div class="grid" style="grid-template-columns:repeat({cols},{cell}px)">']
    for r, row in enumerate(cells):
        for c, v in enumerate(row):
            colour = PALETTE[v] if 0 <= v < len(PALETTE) else "#888"
            mark = " enc" if (r, c) in enc else ""
            out.append(f'<div class="cl{mark}" style="width:{cell}px;height:{cell}px;'
                       f'background:{colour}"></div>')
    out.append("</div>")
    return "".join(out)


def _labelled(inner: str, label: str) -> str:
    return f'<div class="col">{inner}<div class="lbl">{_esc(label)}</div></div>'


def _block_html(block: dict) -> str:
    kind = block.get("kind")
    p = block.get("payload") or {}
    if kind == "grid_pair":
        left = _labelled(_grid(p.get("in"), p.get("enclosed")),
                         p.get("label", "input") + (" · enclosed outlined" if p.get("enclosed") else ""))
        right = _labelled(_grid(p.get("out")), "output")
        return f'<div class="row">{left}<div class="arrow">&rarr;</div>{right}</div>'
    if kind == "grid_single":
        return f'<div class="row">{_labelled(_grid(p.get("grid")), p.get("label", ""))}</div>'
    if kind == "rule":
        return (f'<div class="chip"><span class="mono">{_esc(p.get("text"))}</span>'
                f'{"  &#10003; complete" if p.get("complete") else ""}</div>')
    if kind == "region":
        return f'<div class="note">enclosed region: {len(p.get("cells") or [])} cells</div>'
    if kind == "outcome":
        return ""  # rendered as the header pill
    if kind == "note":
        return f'<div class="note">{_esc(p.get("text"))}</div>'
    return ""


def render_html(artifact: dict) -> str:
    header = artifact.get("header") or {}
    outcome = header.get("outcome", "")
    subject = (header.get("subject") or {}).get("id", "?")
    producer = header.get("producer", "")
    summary = artifact.get("summary", "")
    fg, bg, label = _OUTCOME_STYLE.get(outcome, ("#5f6368", "#f1f3f4", outcome))

    blocks = "".join(_block_html(b) for b in (artifact.get("content") or []))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>arc-viz — {_esc(subject)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #fafafa;
         color: #1a1a1a; margin: 0; padding: 32px; }}
  .card {{ max-width: 760px; margin: 0 auto; background: #fff; border: 1px solid #e5e5e5;
          border-radius: 14px; padding: 28px 32px; }}
  .meta {{ font-size: 13px; color: #888; }}
  h1 {{ font-size: 20px; font-weight: 600; margin: 4px 0 2px; }}
  .summary {{ font-size: 15px; color: #333; margin: 10px 0 16px; }}
  .pill {{ display: inline-flex; align-items: center; gap: 6px; font-size: 13px;
          border-radius: 999px; padding: 5px 14px; color: {fg}; background: {bg};
          font-weight: 500; margin-bottom: 20px; }}
  .row {{ display: flex; align-items: flex-start; gap: 18px; flex-wrap: wrap; margin: 14px 0; }}
  .col {{ display: flex; flex-direction: column; align-items: center; }}
  .grid {{ display: grid; gap: 1px; background: #ddd; padding: 1px; border-radius: 4px; }}
  .cl {{ box-sizing: border-box; }}
  .cl.enc {{ outline: 2px solid #1a56b8; outline-offset: -2px; z-index: 1; }}
  .lbl {{ font-size: 12px; color: #666; margin-top: 6px; }}
  .arrow {{ align-self: center; font-size: 22px; color: #aaa; }}
  .chip {{ display: inline-flex; align-items: center; gap: 8px; background: #fff8e1;
          border: 1px solid #ffe082; border-radius: 8px; padding: 7px 14px; margin: 10px 0;
          font-size: 14px; color: #7a5900; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .note {{ font-size: 13px; color: #777; margin: 8px 0; }}
  .muted {{ color: #aaa; font-size: 13px; }}
</style></head>
<body><div class="card">
  <div class="meta">arc-viz · {_esc(producer)} · task {_esc(subject)}</div>
  <h1>How the answer is reached</h1>
  <div class="summary">{_esc(summary)}</div>
  <div class="pill">{_esc(label)}</div>
  {blocks}
</div></body></html>
"""
