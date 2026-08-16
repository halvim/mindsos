"""dr_screen — Screen A: the document layout over the renderer's page, and the "what arrived" panel.

68.3 item 3, designed coordination §78, critic-corrected §79, adopted §80.

**The substrate rule (the design's spine):** this module consumes the
renderer's composed TEXT PAGE — the string — and adds typography only. It
never reads graphs, the store, or the blackboard. The day a styling need
exceeds what the text carries, THE RENDERER EMITS THE MISSING TEXT (facts
stay single-sourced); this module never grows a graph reader (§79 Q1).

**The fact guard is EQUALITY, not membership (§79 Q4):** chrome-stripped,
the styled page's text nodes concatenated IN ORDER must EQUAL the renderer
page text (whitespace-normalized, entities resolved). Membership alone
would pass a layout that DROPS a line, REORDERS blocks, or DUPLICATES one —
and order is a fact channel (seeded order = member identity). See
:func:`fact_channel` / :func:`page_channel`.

**Chrome (§78.4 + §79 Q2):** every word this module may show that the
renderer did not emit lives in :data:`CHROME`. Chrome is byte-identical
across every case in a run, carries no digits, and shares no word with the
registered phrase vocabulary (pinned test-side from the declarations —
assertion-words carry no digits, so vocabulary disjointness is the closure
that matters). The tuple is review-listed at any PR hold that touches it.

**The CSS channel is guarded too (§79 Q4-6):** a stylesheet can hide a
refusal from the ROOM while every text guard passes — the §11 sin by
stylesheet. :func:`lint_stylesheet` refuses hiding declarations statically
and runs on EVERY compose, not only in tests.

**The left panel (§78.3):** renders the intake the case actually fed the
run. The framing words are chrome; every value string is the fixture's own,
verbatim (pinned test-side). It is the INPUT display, not a Record, and
does not claim otherwise. A from-root screen has no intake to show — the
intake is not store-resident — so the panel is ABSENT there rather than
invented.

**Line classification (§79 Q3):** permissive — a line this module cannot
classify styles as a plain fact line, no raise (a new renderer page form
must not be a layout-breaking change). The REFUSAL, STOP and THEREFORE
classifications are pinned per known page form test-side, red on
regression, because de-emphasising the one line the room must see is the
presentation sin in CSS form.

RULES §11 seam: the two-panel arrangement, the classes and the stylesheet
are this module's; every FACT on the screen is the renderer page's or the
intake fixture's, byte-for-byte. This file is demo code (RULES §3) and
imports the standard library ONLY.
"""

from __future__ import annotations

import html as _html
import re
from html.parser import HTMLParser
from typing import Any, List, Optional, Tuple

#: Every word this layout may display that the renderer did not emit.
CHROME: Tuple[str, ...] = ("What arrived",)

#: Hiding declarations the lint refuses. The zero-valued patterns match a
#: TRUE zero only (``0``/``0px``/``0%``), never ``0.9rem`` / ``0.5`` —
#: found by this module's own smoke run, where the naive substring
#: red-flagged the legitimate ``font-size: 0.9rem``. ``opacity`` joined by
#: critic condition §82 (the hole was live past §79's list). This list is
#: NOT exhaustive and cannot be: offscreen positioning, color-on-color and
#: their kin remain — which is exactly why the stylesheet and the CHROME
#: tuple stay review-listed at every PR hold that touches them (§79/§82).
_BANNED_CSS_PATTERNS = (
    re.compile(r"display\s*:\s*none"),
    re.compile(r"visibility\s*:\s*hidden"),
    re.compile(r"font-size\s*:\s*0(?![.\d])"),
    re.compile(r"opacity\s*:\s*0(?![.\d])"),
)


class ScreenGapError(RuntimeError):
    """The screen cannot honestly be composed — raise, never fill."""


class StylesheetHiddenError(RuntimeError):
    """The stylesheet hides content — the §11 sin by CSS (§79)."""


STYLESHEET = """
body { margin: 0; background: #f4f2ee; color: #1d1d1f;
       font-family: Georgia, 'Times New Roman', serif; }
main.screen { display: flex; gap: 2rem; padding: 2rem;
              max-width: 75rem; margin: 0 auto; align-items: flex-start; }
section#arrived { flex: 1; background: #eceae4; padding: 1.25rem 1.5rem;
                  border-radius: 4px; }
section#record { flex: 2; background: #ffffff; padding: 2rem 2.5rem;
                 border: 1px solid #d8d4cc; border-radius: 4px;
                 box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
h2.chrome { font-size: 0.9rem; letter-spacing: 0.08em;
            text-transform: uppercase; color: #6b675f; margin: 0 0 1rem; }
div.intake-block { border-top: 1px solid #d8d4cc; padding: 0.6rem 0; }
div.intake-block:first-of-type { border-top: none; }
p { margin: 0.15rem 0; line-height: 1.5; }
p.title { font-size: 1.3rem; font-weight: bold; margin-bottom: 0.2rem; }
p.date { color: #6b675f; font-size: 0.95rem; margin-bottom: 1rem; }
p.fact { }
p.verdict { padding-left: 1rem; }
p.refusal { border-left: 3px solid #8a1c1c; padding: 0.4rem 0 0.4rem 0.8rem;
            background: #faf5f3; }
p.stop { border-left: 3px solid #8a6d1c; padding: 0.4rem 0 0.4rem 0.8rem;
         background: #faf8f0; }
p.inhand { }
p.therefore { font-weight: bold; border-top: 1px solid #d8d4cc;
              padding-top: 0.8rem; margin-top: 1rem; }
div.gap { height: 0.75rem; }
@media print {
  body { background: #ffffff; }
  main.screen { display: block; padding: 0; }
  section#arrived { page-break-after: always; border-radius: 0; }
  section#record { border: none; box-shadow: none; padding: 0; }
}
"""


def lint_stylesheet(css: str) -> None:
    low = css.lower()
    for pattern in _BANNED_CSS_PATTERNS:
        if pattern.search(low):
            raise StylesheetHiddenError(
                f"the stylesheet hides content ({pattern.pattern!r}) — a "
                "hidden refusal passes every text guard while the room "
                "never sees it; refusing to compose"
            )


def classify_line(line: str) -> str:
    """Style class for one renderer line. PERMISSIVE: an unknown line is a
    plain fact line, never a raise (§79 Q3 — the fact channel is owned by
    the equality guard, not by this classifier)."""
    if line.startswith("Decision Record"):
        return "title"
    if line.startswith("Decided"):
        return "date"
    if line.startswith("Q. "):
        return "refusal"
    if line.startswith("Stopped"):
        return "stop"
    if line.startswith("In hand:"):
        return "inhand"
    if line.startswith("Therefore:"):
        return "therefore"
    if line.startswith("   "):
        return "verdict"
    return "fact"


def intake_blocks(intake: Any) -> List[List[str]]:
    """The left panel's lines: the fixture's OWN keys and values, verbatim,
    in filed order. A list yields one block per item; a dict one block; a
    scalar one line. No key is invented and no value is rephrased."""
    if isinstance(intake, list):
        blocks = []
        for item in intake:
            if isinstance(item, dict):
                blocks.append([f"{k}: {v}" for k, v in item.items()])
            else:
                blocks.append([str(item)])
        return blocks
    if isinstance(intake, dict):
        return [[f"{k}: {v}" for k, v in intake.items()]]
    return [[str(intake)]]


def _arrived_section(intake: Any) -> str:
    parts = ['<section id="arrived">', '<h2 class="chrome">What arrived</h2>']
    for block in intake_blocks(intake):
        parts.append('<div class="intake-block">')
        for line in block:
            parts.append(f'<p class="fact">{_html.escape(line)}</p>')
        parts.append("</div>")
    parts.append("</section>")
    return "\n".join(parts)


def _record_section(page_text: str) -> str:
    parts = ['<section id="record">']
    for line in page_text.splitlines():
        if not line.strip():
            parts.append('<div class="gap"></div>')
            continue
        parts.append(
            f'<p class="{classify_line(line)}">{_html.escape(line)}</p>'
        )
    parts.append("</section>")
    return "\n".join(parts)


def compose_screen(
    page_text: str,
    intake: Any = None,
    css: str = STYLESHEET,
) -> str:
    """One self-contained HTML screen: the intake panel (when an intake
    exists — a from-root render has none and shows none) beside the styled
    Record. Zero external resources: Gate 7's laptop is cold."""
    lint_stylesheet(css)
    if not page_text.strip():
        raise ScreenGapError("no renderer page to style — nothing to show")
    arrived = _arrived_section(intake) if intake is not None else ""
    record = _record_section(page_text)
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        f"<style>{css}</style>\n</head>\n<body>\n"
        f'<main class="screen">\n{arrived}\n{record}\n</main>\n'
        "</body>\n</html>\n"
    )


class _NodeCollector(HTMLParser):
    """(section_id, css_class, text) per text node, in document order.
    ``convert_charrefs`` (the default) resolves entities BEFORE comparison —
    an entity-encoded fact word cannot dodge the equality guard."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes: List[Tuple[Optional[str], Optional[str], str]] = []
        self._section: Optional[str] = None
        self._class: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section":
            self._section = a.get("id")
        self._class = a.get("class", self._class)

    def handle_endtag(self, tag):
        if tag == "section":
            self._section = None

    def handle_data(self, data):
        if data.strip():
            self.nodes.append((self._section, self._class, data))


def text_nodes(html_doc: str):
    collector = _NodeCollector()
    collector.feed(html_doc)
    return collector.nodes


def _normalize(text: str) -> str:
    return " ".join(text.split())


def page_channel(page_text: str) -> str:
    """The renderer page as one normalized fact string."""
    return _normalize(page_text)


def fact_channel(
    html_doc: str, section: str = "record", chrome: Tuple[str, ...] = CHROME,
) -> str:
    """The styled page's fact string: text nodes of ``section`` IN ORDER,
    chrome-stripped, whitespace-normalized. The guard is
    ``fact_channel(screen) == page_channel(page)`` — equality, so a dropped,
    reordered or duplicated line is red, not just an invented one (§79)."""
    kept = [
        _normalize(text)
        for (sec, _cls, text) in text_nodes(html_doc)
        if sec == section and _normalize(text) not in chrome
    ]
    return " ".join(kept)


def compare_pages(page_a: str, page_b: str) -> List[Tuple[str, str]]:
    """Line-paired differences between two renderer pages (normalized,
    blanks dropped). The §79 pin: a live page and its from-root re-render
    must differ in EXACTLY the date line — anything else is a finding."""
    a = [_normalize(l) for l in page_a.splitlines() if l.strip()]
    b = [_normalize(l) for l in page_b.splitlines() if l.strip()]
    diffs: List[Tuple[str, str]] = []
    for i in range(max(len(a), len(b))):
        la = a[i] if i < len(a) else "<absent>"
        lb = b[i] if i < len(b) else "<absent>"
        if la != lb:
            diffs.append((la, lb))
    return diffs


__all__ = [
    "CHROME", "STYLESHEET", "ScreenGapError", "StylesheetHiddenError",
    "classify_line", "compare_pages", "compose_screen", "fact_channel",
    "intake_blocks", "lint_stylesheet", "page_channel", "text_nodes",
]
