"""dr_render — the Decision Record page, from the persisted grounding graphs and nothing else.

Plan item 7. Form is **question → answer → therefore** (plan §2.3, probe D).
The design was critic-reviewed before it was built (coordination §29–§31);
the four §30 rulings are load-bearing here:

* member↔verdict correlation is FULL verdict-value equality against the fold's
  seeded LIST (bank #7); an entry matching no member graph RAISES;
* `outcome_classification='completed'` with no produced conclusion in the
  terminal graph RAISES (the Episode asserting a success the graph cannot show);
* `environment_fault` is NOT consumed (ADR-0207 §am-2: always False,
  structurally) — the our-fault/case-finding distinction is structural:
  `RunStopped` present ⟹ our stop; in-band refusal in an origin record ⟹ a
  finding about the case;
* the v0 page renders a SINGLE-ATTEMPT Episode — more than one terminal-shaped
  graph raises rather than guessing which attempt is the Record.

**G1 (import ban):** this module imports the standard library and
`mindsos_core` (the client + `load_graph`) ONLY — no blackboard, no capacity
context, no L2 snapshot, no `Pipeline`, no `chain_artifacts`. Pinned by AST in
`test_dr_render_guards.py`.

**G2 (raise, never fill):** a parentless `DataStateInstance` whose type is not
in the manifest's declared start set raises :class:`RendererGapError` — probe
D's mutation (delete a `CapacityInstance`) must never again print a derived
conclusion as a premise.

**G6 (no internal tokens):** the page carries descriptions, phrases and
values — never an IRI, never a reason token. A stop detail that IS an IRI is a
link, not text, and is suppressed.

RULES §11 seam: the PAGE is composed output by design — the layout, the "Q."
and "Therefore" framing and the sentence glue are this module's. The claim
under test is that every FACT on the page is a stored graph value, and that
every gap raises instead of rendering.

The demo's vocabulary (all-demo ruling, §31): the verdict field names this
layout knows are ``decision`` and ``claim_decision``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

NODE_MANIFEST = "RunManifest"
NODE_DSI = "DataStateInstance"
NODE_CAPACITY = "CapacityInstance"
NODE_STOPPED = "RunStopped"
PROP_DS_TYPE = "datastate_type"
PROP_STOP_DETAIL = "stopped_detail"

#: Demo (claims) vocabulary — the layout's knowledge, not the graph's.
VERDICT_FIELD = "decision"
CONCLUSION_FIELD = "claim_decision"

#: IRI prefixes that must never reach the page (G6): a detail carrying one is
#: a link, not text.
_LINK_PREFIXES = ("datastate:", "capacity:", "runstopped:", "runmanifest:")


class RendererGapError(RuntimeError):
    """The graph cannot honestly support the page — raise, never fill (G2)."""


class _Analysis:
    def __init__(self, graph: Any) -> None:
        self.graph = graph
        produced_ids = set()
        for edge in graph.edges.values():
            if edge.type_name == "PRODUCES":
                produced_ids.add(edge.target.node_id)
        self.manifest: Optional[Dict[str, Any]] = None
        self.stopped: Optional[Any] = None
        self.capacity_iris: List[str] = []
        self.parentless: List[Any] = []
        self.produced: List[Any] = []
        for node_id, node in graph.nodes.items():
            if node.type_name == NODE_MANIFEST:
                self.manifest = node.value
            elif node.type_name == NODE_STOPPED:
                self.stopped = node
            elif node.type_name == NODE_CAPACITY:
                self.capacity_iris.append((node.properties or {}).get("capacity"))
            elif node.type_name == NODE_DSI:
                if node_id in produced_ids:
                    self.produced.append(node)
                else:
                    self.parentless.append(node)
        if self.manifest is None:
            raise RendererGapError(
                f"run graph {graph.role!r} carries no manifest; nothing on it "
                "can be named"
            )

    def ds_type(self, node: Any) -> str:
        return (node.properties or {}).get(PROP_DS_TYPE, "")

    def check_declared_starts(self) -> None:
        declared = self.manifest.get("declared_starts") or {}
        for node in self.parentless:
            if self.ds_type(node) not in declared:
                raise RendererGapError(
                    "a value stands with no producer and is not a declared "
                    f"start: {self.ds_type(node)!r} in {self.graph.role!r} — "
                    "refusing to render a derived value as a premise"
                )

    def start_description(self, node: Any) -> str:
        return (self.manifest.get("declared_starts") or {})[self.ds_type(node)]

    def phrase(self) -> str:
        phrases = self.manifest.get("capacity_phrases") or {}
        for iri in self.capacity_iris:
            if iri in phrases:
                return phrases[iri]
        raise RendererGapError(
            f"no phrase for any capacity on {self.graph.role!r}; an IRI is "
            "not a sentence"
        )

    def stop_lines(self) -> List[str]:
        phrases = self.manifest.get("stop_reason_phrases") or {}
        reason = self.stopped.value
        if reason not in phrases:
            raise RendererGapError(
                f"stop reason {reason!r} has no phrase in the manifest"
            )
        detail = (self.stopped.properties or {}).get(PROP_STOP_DETAIL)
        lines = [f"Stopped: {phrases[reason]}."]
        if detail and not str(detail).startswith(_LINK_PREFIXES):
            lines.append(f"  {detail}")
        return lines

    def origin_refusals(self) -> List[Dict[str, Any]]:
        out = []
        for node in self.produced:
            value = node.value
            if isinstance(value, dict) and value.get("refusal_reason"):
                out.append(value)
        return out

    def plain_produced(self) -> List[Any]:
        """Produced DSIs that are neither origin records nor refusal carriers."""
        out = []
        for node in self.produced:
            value = node.value
            if isinstance(value, dict) and (
                "origin_producer_kind" in value or "refusal_reason" in value
            ):
                continue
            out.append(node)
        return out


def _fmt(value: Any) -> str:
    """Deterministic plain-text form of a stored value (layout's choice; the
    facts are the values). Dict fields sort by key — S-F1: iteration order is
    not a stored fact, so no layout may depend on it."""
    if isinstance(value, dict):
        return ", ".join(str(value[k]) for k in sorted(value))
    if isinstance(value, list):
        return "; ".join(_fmt(v) for v in value)
    return str(value)


def _verdict_text(value: Any) -> str:
    if isinstance(value, dict):
        if VERDICT_FIELD in value:
            return str(value[VERDICT_FIELD])
        if CONCLUSION_FIELD in value:
            return str(value[CONCLUSION_FIELD])
    return _fmt(value)


def render_from_graphs(graphs: List[Any], episode_props: Dict[str, Any]) -> str:
    """Render one Decision Record page from run graphs + the Episode's fields.

    ``graphs`` may be live or loaded — the page must not be able to tell
    (bank #4 is enforced one level up: :func:`render_record` only ever hands
    this loaded ones).
    """
    if not graphs:
        raise RendererGapError("the Episode references no run graphs at all")
    analyses = [_Analysis(g) for g in graphs]
    for analysis in analyses:
        analysis.check_declared_starts()

    folds = [
        a for a in analyses
        if any(isinstance(a_node.value, list) for a_node in a.parentless)
    ]
    if len(folds) > 1:
        raise RendererGapError(
            "more than one terminal-shaped graph in one Episode — the v0 page "
            "renders a single attempt and will not guess which one is the "
            "Record (§31 scope)"
        )

    case_label = next(
        (a.manifest.get("case_label") for a in analyses if a.manifest.get("case_label")),
        None,
    )
    consolidated_at = episode_props.get("consolidated_at") or ""
    outcome = episode_props.get("outcome_classification")

    lines: List[str] = []
    lines.append(f"Decision Record — {case_label}" if case_label else "Decision Record")
    if consolidated_at:
        lines.append(f"Decided {str(consolidated_at)[:10]}")
    lines.append("")

    terminal: Optional[_Analysis] = None
    if folds:
        fold = folds[0]
        terminal = fold
        verdicts_node = next(
            node for node in fold.parentless if isinstance(node.value, list)
        )
        members = [a for a in analyses if a is not fold]
        for entry in verdicts_node.value:
            match = None
            for member in members:
                if any(node.value == entry for node in member.plain_produced()):
                    match = member
                    break
            if match is None:
                raise RendererGapError(
                    "a recorded verdict matches no run graph — the list and "
                    "the members have diverged"
                )
            start_nodes = [
                node for node in match.parentless
                if not isinstance(node.value, list)
            ]
            for start in start_nodes:
                lines.append(
                    f"Q. {match.start_description(start)} — {_fmt(start.value)}"
                )
            lines.append(f"   {match.phrase()} → {_verdict_text(entry)}")
            lines.append("")
        if fold.stopped is not None:
            lines.extend(fold.stop_lines())
        else:
            conclusions = fold.plain_produced()
            if conclusions:
                lines.append(
                    f"Therefore: {fold.phrase()} → "
                    f"{_verdict_text(conclusions[0].value)}"
                )
    else:
        analysis = analyses[0]
        terminal = analysis
        for start in analysis.parentless:
            lines.append(
                f"Q. {analysis.start_description(start)} — {_fmt(start.value)}"
            )
        refusals = analysis.origin_refusals()
        if analysis.stopped is not None:
            lines.extend(analysis.stop_lines())
        elif refusals:
            refusal = refusals[0]
            lines.append(
                f"   {refusal.get('question')} — Nothing. "
                f"{refusal.get('refusal_detail')}"
            )
        else:
            produced = analysis.plain_produced()
            if produced:
                lines.append(
                    f"   {analysis.phrase()} → {_verdict_text(produced[0].value)}"
                )
            elif not analysis.graph.edges:
                lines.append(
                    "Stopped before any step could run: no way to answer "
                    "this was found."
                )

    if outcome == "completed" and terminal is not None:
        if terminal.stopped is not None or not terminal.plain_produced():
            raise RendererGapError(
                "the Episode says completed but the terminal graph shows no "
                "conclusion — refusing to assert a success the graph cannot "
                "show (§30 Q2)"
            )

    return "\n".join(lines).rstrip() + "\n"


def render_record(client: Any, episode_props: Dict[str, Any]) -> str:
    """Load the Episode's graphs from the STORE and render (bank #4: the page
    is built from persisted evidence, never live objects)."""
    from mindsos_core.reconstruction.graph_loader import load_graph

    root = episode_props.get("capacity_root_ref")
    if not root:
        raise RendererGapError(
            "the Episode carries no capacity_root_ref — there is no stored "
            "evidence to render"
        )
    index = load_graph(client, root)
    graph_ids = [
        node.value for node in index.nodes.values()
        if node.type_name == "CapacityRunRef"
    ]
    graphs = [load_graph(client, graph_id) for graph_id in graph_ids]
    return render_from_graphs(graphs, episode_props)


__all__ = ["RendererGapError", "render_from_graphs", "render_record"]
