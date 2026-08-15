"""dr_render — the Decision Record page, from the persisted grounding graphs and nothing else.

Plan item 7. Form is **question → answer → therefore** (plan §2.3, probe D).
The design was critic-reviewed before it was built (coordination §29–§31);
the four §30 rulings are load-bearing here:

* member↔verdict correlation is FULL verdict-value equality against the fold's
  seeded LIST (bank #7), and it is a BIJECTION (coordination §37/§39): an entry
  matching no member graph RAISES, an entry matching several graphs that do not
  render alike RAISES, and a member graph left unmatched at the end RAISES
  naming its role. The first cut matched one direction only and took the first
  candidate — so an unmatched member vanished from the page and two identical
  verdict values printed one member twice. Both were silent, and the ∀-abort
  barrier is the only reason they were unreachable; the day a member may refuse
  instead of aborting, the page must not be able to drop the refusal;
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

**The Q-form source rule (owner ruling, 2026-08-14, after critic §33's Q3
observation):** a "Q." line is EARNED by a stored question — the origin
record's ``question`` field is the only source of interrogative voice on the
page. Graphs that carry no question present the item and its outcome
(``{value} — {description}``, then ``{phrase} → {verdict}``); the renderer
never invents a question, because that is the §11 class — presentation
implying the system asked something it did not. A future capacity that wants
a Q-line earns it the ADR-0208 way: by producing an origin record.

RULES §11 seam: the PAGE is composed output by design — the layout, the "Q."
and "Therefore" framing and the sentence glue are this module's. The claim
under test is that every FACT on the page is a stored graph value, and that
every gap raises instead of rendering.

The demo's vocabulary (all-demo ruling, §31): the verdict field names this
layout knows are ``decision`` and ``claim_decision``.

**Two correlation roads (ADR-0201 am-5 consumption; coordination §71/§72):**

* MANIFEST ROAD — the fold manifest carries ``member_graph_ids`` (key
  presence means exactly: a map supplied ids). Member blocks render BY
  POSITION over that list; the value-equality bijection is DEMOTED to a
  per-position cross-check (a list entry must equal a value its named graph
  produced, or the record and the value bus are out of step — raise). The
  member-completedness predicate is the record itself: ``RunStopped``
  present ⟹ stopped, REGARDLESS of produced values — and a graph carrying
  both a ``RunStopped`` and a produced verdict-typed value RAISES as
  incoherent, never classifies (§72 Q2). A stopped or manifest-only member
  consumes NO list entry; its stop block renders in place.
* NO-MANIFEST ROAD — key absent (a fold-only plan, or a degraded/stale
  record). The shipped bijection stands here unchanged, identical-duplicates
  refusal included (N-F2's re-scope). Its raise texts name the road's own
  ambiguity: a parentless list marks a fold, or a list-valued start — this
  record cannot say. KEEP THIS: two refusals with different named items on
  this road raise via "do not render alike" — that is CORRECT for a
  degraded record, not a defect to fix (§72 Q3).

Refusals (ADR-0209 shape (a)): a verdict VALUE carrying ``refusal_reason``
is a structural marker, branch-only, never printed; the prose comes from the
origin record OF THE REFUSING VALUE (the produced origin-record dict whose
``refusal_reason`` is set), rendered in the leaf refusal's Q-form.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

NODE_MANIFEST = "RunManifest"
NODE_DSI = "DataStateInstance"
NODE_CAPACITY = "CapacityInstance"
NODE_STOPPED = "RunStopped"
PROP_DS_TYPE = "datastate_type"
PROP_STOP_DETAIL = "stopped_detail"

#: am-5 manifest key (string literal by design — G1 bans the identifiers
#: module; the spelling collision with the persistence row key is recorded in
#: the amendment).
MANIFEST_MEMBER_IDS = "member_graph_ids"

#: ADR-0209 structural refusal marker on a verdict VALUE — branch-only.
REFUSAL_MARKER = "refusal_reason"

#: Demo (claims) vocabulary — the layout's knowledge, not the graph's.
VERDICT_FIELD = "decision"
CONCLUSION_FIELD = "claim_decision"

#: IRI prefixes that must never reach the page (G6): a detail carrying one is
#: a link, not text.
_LINK_PREFIXES = ("datastate:", "capacity:", "runstopped:", "runmanifest:")

#: The banned-pattern list, ONE source for the render-time scan and the guard
#: test (critic §33 M-D: a G6 that only sees the fixtures it was written with
#: is one careless stored phrase away from printing an IRI — so the renderer
#: scans its OWN composed page and raises).
G6_BANNED = (
    "datastate:", "capacity:", "runstopped", "runmanifest",
    "requestrun:", "pipelinerun:", "step_failed", "needs_input",
    "empty_domain", "partial_domain", "refusal_reason",
    "field_absent", "value_not_coercible", "no_source_in_force",
)


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
        self.graph_id = getattr(graph, "graph_id", None)
        self.manifest_only = not graph.edges

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

    def refusing_records(self) -> List[Dict[str, Any]]:
        """Origin records OF a refusing value (§72 Q3): produced dicts that
        are origin-record-shaped (``origin_producer_kind`` present) AND carry
        a set ``refusal_reason`` — the only source of refusal prose."""
        return [
            value for value in self.origin_refusals()
            if "origin_producer_kind" in value
        ]

    def produced_values(self) -> List[Any]:
        return [node.value for node in self.produced]

    def no_route_lines(self) -> List[str]:
        """The manifest-only member's block — run-4's shape, the leaf
        no-route lines reused at member position."""
        lines = [
            f"In hand: {description}"
            for description in (self.manifest.get("declared_starts") or {}).values()
        ]
        lines.append(
            "Stopped before any step could run: no way to answer "
            "this was found."
        )
        return lines

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


def _member_block(member: "_Analysis", entry: Any) -> List[str]:
    """The lines one member contributes, for one list entry.

    Extracted so correlation can COMPARE candidates instead of taking the
    first: §30's interchangeability argument holds only where the rendered
    blocks are identical (a genuinely duplicated exposure), and the renderer
    must be able to tell that case from an ambiguous one rather than assume it.
    """
    lines = [
        f"{_fmt(start.value)} — {member.start_description(start)}"
        for start in member.parentless
        if not isinstance(start.value, list)
    ]
    lines.append(f"   {member.phrase()} → {_verdict_text(entry)}")
    return lines


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
        if MANIFEST_MEMBER_IDS in a.manifest
        or any(isinstance(a_node.value, list) for a_node in a.parentless)
    ]
    if len(folds) > 1:
        raise RendererGapError(
            "more than one terminal-shaped graph in one Episode — the v0 page "
            "renders a single attempt and will not guess which one is the "
            "Record (§31 scope)"
        )
    manifest_road = bool(folds) and MANIFEST_MEMBER_IDS in folds[0].manifest

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
    else:
        # §52 condition 1 (adopted §53): a page that cannot prove its decided
        # date STATES that, in room-safe words — a silently missing line is
        # indistinguishable from a renderer bug (G2's principle, applied to
        # the page itself). The date lives on the Episode, which is not
        # store-resident (§51.1), so the from-root page always takes this
        # branch.
        lines.append("Decided date: not available from stored evidence")
    lines.append("")

    terminal: Optional[_Analysis] = None
    if folds and manifest_road:
        fold = folds[0]
        terminal = fold
        ids = list(fold.manifest[MANIFEST_MEMBER_IDS])
        verdicts_node = next(
            (node for node in fold.parentless if isinstance(node.value, list)),
            None,
        )
        entries = list(verdicts_node.value) if verdicts_node is not None else []
        by_id = {a.graph_id: a for a in analyses if a is not fold}
        named = set(ids)
        extra = [a for a in analyses if a is not fold and a.graph_id not in named]
        if extra:
            raise RendererGapError(
                "a run graph produced a verdict that appears nowhere in the "
                "recorded list, so the page would omit it silently: "
                + ", ".join(repr(m.graph.role) for m in extra)
                + " — refusing to publish a Record that leaves a member out"
            )
        pos = 0
        verdict_types: set = set()
        stopped_members: List[_Analysis] = []
        for gid in ids:
            member = by_id.get(gid)
            if member is None:
                raise RendererGapError(
                    "the manifest names a member graph that is not in this "
                    "Episode — the record cannot show the member it promises"
                )
            if member.stopped is not None or member.manifest_only:
                stopped_members.append(member)
                block = [
                    f"{_fmt(start.value)} — {member.start_description(start)}"
                    for start in member.parentless
                    if not isinstance(start.value, list)
                ]
                if member.stopped is not None:
                    block.extend(member.stop_lines())
                else:
                    block = member.no_route_lines()
                lines.extend(block)
                lines.append("")
                continue
            if pos >= len(entries):
                raise RendererGapError(
                    "a run graph produced a verdict that appears nowhere in "
                    "the recorded list, so the page would omit it silently: "
                    + repr(member.graph.role)
                    + " — refusing to publish a Record that leaves a member out"
                )
            entry = entries[pos]
            pos += 1
            if not any(value == entry for value in member.produced_values()):
                raise RendererGapError(
                    f"list position {pos - 1} does not match any value its "
                    f"named member graph produced ({member.graph.role!r}) — "
                    "the record and the value bus are out of step"
                )
            for node in member.produced:
                if node.value == entry:
                    verdict_types.add(member.ds_type(node))
                    break
            if isinstance(entry, dict) and entry.get(REFUSAL_MARKER):
                records = member.refusing_records()
                if not records:
                    raise RendererGapError(
                        f"a refusing verdict on {member.graph.role!r} has no "
                        "origin record to speak from — refusing to render a "
                        "refusal with no stored words"
                    )
                record = records[0]
                block = [
                    f"{_fmt(start.value)} — {member.start_description(start)}"
                    for start in member.parentless
                    if not isinstance(start.value, list)
                ]
                block.append(
                    f"Q. {record.get('question')} — Nothing. "
                    f"{record.get('refusal_detail')}"
                )
                lines.extend(block)
                lines.append("")
                continue
            lines.extend(_member_block(member, entry))
            lines.append("")
        if pos != len(entries):
            raise RendererGapError(
                "the recorded list holds more verdicts than the manifest's "
                "members supplied — the record and the value bus are out of "
                "step"
            )
        for member in stopped_members:
            if member.stopped is not None and verdict_types and any(
                member.ds_type(node) in verdict_types for node in member.produced
            ):
                raise RendererGapError(
                    f"member graph {member.graph.role!r} carries both a stop "
                    "and a produced verdict — incoherent, refusing to "
                    "classify (§72 Q2)"
                )
        if fold.stopped is not None:
            lines.extend(fold.stop_lines())
        else:
            conclusions = fold.plain_produced()
            if conclusions:
                lines.append(
                    f"Therefore: {fold.phrase()} → "
                    f"{_verdict_text(conclusions[0].value)}"
                )
    elif folds:
        fold = folds[0]
        terminal = fold
        verdicts_node = next(
            node for node in fold.parentless if isinstance(node.value, list)
        )
        members = [a for a in analyses if a is not fold]
        unmatched = list(members)
        _AMBIGUITY = (
            " (no-manifest road: a parentless list marks a fold, or a "
            "list-valued start — this record cannot say)"
        )
        for entry in verdicts_node.value:
            candidates = [
                member for member in unmatched
                if any(node.value == entry for node in member.plain_produced())
            ]
            if not candidates:
                raise RendererGapError(
                    "a recorded verdict matches no run graph — the list and "
                    "the members have diverged" + _AMBIGUITY
                )
            blocks = [_member_block(c, entry) for c in candidates]
            if len({tuple(b) for b in blocks}) > 1:
                raise RendererGapError(
                    f"a recorded verdict matches {len(candidates)} run graphs "
                    "that do not render alike ("
                    + ", ".join(repr(c.graph.role) for c in candidates)
                    + ") — refusing to guess which exposure it belongs to"
                    + _AMBIGUITY
                )
            match = candidates[0]
            unmatched.remove(match)
            lines.extend(blocks[0])
            lines.append("")
        if unmatched:
            raise RendererGapError(
                "a run graph produced a verdict that appears nowhere in the "
                "recorded list, so the page would omit it silently: "
                + ", ".join(repr(m.graph.role) for m in unmatched)
                + " — refusing to publish a Record that leaves a member out"
                + _AMBIGUITY
            )
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
                f"{_fmt(start.value)} — {analysis.start_description(start)}"
            )
        refusals = analysis.origin_refusals()
        if analysis.stopped is not None:
            lines.extend(analysis.stop_lines())
        elif refusals:
            refusal = refusals[0]
            lines.append(
                f"Q. {refusal.get('question')} — Nothing. "
                f"{refusal.get('refusal_detail')}"
            )
        else:
            produced = analysis.plain_produced()
            if produced:
                lines.append(
                    f"   {analysis.phrase()} → {_verdict_text(produced[0].value)}"
                )
            elif not analysis.graph.edges:
                for description in (
                    analysis.manifest.get("declared_starts") or {}
                ).values():
                    lines.append(f"In hand: {description}")
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

    page = "\n".join(lines).rstrip() + "\n"
    low = page.lower()
    for token in G6_BANNED:
        if token in low:
            raise RendererGapError(
                f"an internal token reached the composed page: {token!r} — "
                "refusing to publish (render-time G6, §33)"
            )
    return page


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
