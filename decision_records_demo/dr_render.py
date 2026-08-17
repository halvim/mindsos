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

**The source line (beat 4, *the policy changed mid-claim*):** where a value
was admitted by a policy lookup, the page names the edition and the window it
was in force — see :func:`_source_lines`. A missing field the producer
declares it always supplies RAISES (it is a defect); a missing
``source_in_force_to`` renders as *onwards* (it is an open edition, and the
contract says so by leaving that field out of ``supplied_fields``).

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
``refusal_reason`` is set), rendered in the leaf refusal's Q-form. A
refusal-shaped record on a member whose verdict does NOT refuse is
DELIBERATELY ignored (§76): a reader refusal on an input the decision never
consulted is legitimate noise — a vehicle exposure needs no severity — and
record↔verdict coherence is a demand this contract chooses not to impose.
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

#: The field a refusing verdict carries its OWN words in.
#:
#: ⚠ **This replaced a renderer-composed string, on the rule coordination
#: §100/§102 settled and which is worth more than the fix:** the renderer's
#: voice may describe THE RECORD'S LIMITS — meta, case-invariant, true of
#: every Record ever rendered from a store, which is what makes *"Decided
#: date: not available from stored evidence"* chrome — and may NEVER describe
#: THE CASE'S OUTCOME. *"not possible"* is an outcome statement, so the words
#: belong to the capacity that could not decide, and this module only places
#: them.
#:
#: ⚠ **The contract that comes with it:** a refusing value rendered on the
#: LEAF road must carry this field, or the page RAISES (G2 — raise, never
#: fill). Spelled as a literal here and in the producing module because
#: ``dr_render`` may import neither (G1); the spellings are pinned equal
#: test-side, exactly as the determining field's are.
FIELD_REFUSAL_PHRASE = "refusal_phrase"

#: Origin-record keys the page reads. String literals BY NECESSITY — G1 bans
#: importing `mindsos_capacity`, where the contract defines them — so they are
#: pinned against `origin_v0`'s own constants test-side
#: (`test_the_origin_keys_the_page_reads_match_the_contract`). Without that pin
#: a rename in the contract would silently stop the source line from rendering
#: rather than fail, which is the "guard that cannot go red" shape.
FIELD_PRODUCER_KIND = "origin_producer_kind"
FIELD_SUPPLIED_FIELDS = "supplied_fields"
FIELD_ADMITTED = "admitted"
FIELD_QUESTION = "question"
FIELD_SOURCE_PHRASE = "source_identity_phrase"
FIELD_SOURCE_VERSION = "source_version"
FIELD_IN_FORCE_FROM = "source_in_force_from"
FIELD_IN_FORCE_TO = "source_in_force_to"
PRODUCER_POLICY_LOOKUP = "policy_lookup"

#: Demo (claims) vocabulary — the layout's knowledge, not the graph's.
VERDICT_FIELD = "decision"
CONCLUSION_FIELD = "claim_decision"

#: The demo-owned structural field naming WHICH INPUT decided a verdict.
#: Branch-only and NEVER printed — it holds a DataState IRI and G6 bans those
#: from the page. Same discipline as ``refusal_reason`` (ADR-0209). Spelled as
#: a literal here because G1 forbids importing the demo modules that write it;
#: the three spellings are pinned equal test-side.
FIELD_DETERMINED_BY = "determined_by"

#: The demo-owned structural field naming WHICH STORED RULE a verdict was
#: measured against (``dr_routing.MEASURED_AGAINST``). Same discipline as
#: :data:`FIELD_DETERMINED_BY`: it names a DataState, it SELECTS, and it never
#: appears on the page.
FIELD_MEASURED_AGAINST = "measured_against"

#: How an origin record's DataState type is named from its value's:
#: ``origin_v0.origin_record_iri(value_iri) == value_iri + "_origin"``, and
#: EVERY producer that exists calls it (structured ingest, policy lookup,
#: comprehension). Verified on a dump the owner ran, 2026-08-17: a lookup graph
#: carries ``datastate:drdemo.dwelling_limit`` beside
#: ``datastate:drdemo.dwelling_limit_origin``. This is the PRIMARY pairing
#: axis; same-producing-capacity is the cross-check, because one capacity emits
#: both and a name match across two producers is incoherent rather than
#: ambiguous. Pinned test-side against the contract.
ORIGIN_SUFFIX = "_origin"

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
        self.produced_by: Dict[str, Any] = {}
        for edge in graph.edges.values():
            if edge.type_name == "PRODUCES":
                produced_ids.add(edge.target.node_id)
                self.produced_by[edge.target.node_id] = (
                    edge.source.properties or {}
                ).get("capacity")
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

    def phrase_for_value(self, value: Any) -> str:
        """The phrase of the capacity that PRODUCED this value — on a
        multi-capacity member graph (readers + a decision) the verdict line
        must not wear a reader's phrase. Falls back to :meth:`phrase` (the
        first phrased capacity), which is byte-identical on every
        single-capacity graph."""
        phrases = self.manifest.get("capacity_phrases") or {}
        for node_id, node in self.graph.nodes.items():
            if node.type_name == NODE_DSI and node.value == value:
                iri = self.produced_by.get(node_id)
                if iri in phrases:
                    return phrases[iri]
        return self.phrase()

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

    def _capacity_of(self, node: Any) -> Optional[str]:
        for node_id, candidate in self.graph.nodes.items():
            if candidate is node:
                return self.produced_by.get(node_id)
        return None

    def policy_records_for(self, node: Any) -> List[Dict[str, Any]]:
        """Admitted policy-lookup origin records produced by the SAME capacity
        as ``node``.

        Same-capacity is the association, not same-graph: a member graph can
        carry several producers, and a value must never wear another
        producer's provenance.
        """
        iri = self._capacity_of(node)
        if iri is None:
            return []
        out = []
        for node_id, candidate in self.graph.nodes.items():
            if candidate.type_name != NODE_DSI:
                continue
            value = candidate.value
            if not isinstance(value, dict):
                continue
            if value.get(FIELD_PRODUCER_KIND) != PRODUCER_POLICY_LOOKUP:
                continue
            if not value.get(FIELD_ADMITTED):
                continue
            if self.produced_by.get(node_id) == iri:
                out.append(value)
        return out

    def deciding_lines(self, verdict: Any) -> List[str]:
        """:meth:`deciding_fact`, rendered."""
        fact = self.deciding_fact(verdict)
        if fact is None:
            return []
        question, answer = fact
        return [f"   Q. {question} — {_fmt(answer)}."]

    def _node_by_type(self, ds_type: str) -> Optional[Any]:
        """The PRODUCED node of this type, or None. Raises on two."""
        found = [n for n in self.produced if self.ds_type(n) == ds_type]
        if len(found) > 1:
            raise RendererGapError(
                f"two produced values share the type {ds_type!r} on "
                f"{self.graph.role!r} — the page cannot say which one was read"
            )
        return found[0] if found else None

    def deciding_fact(self, verdict: Any):
        """The one read that DECIDED this verdict, as its stored question and
        its stored answer.

        **Not every read.** A page carrying every fact a decision consulted is
        a data dump; the fact that MOVED the answer is the decision. The
        producing capacity records which input that was
        (:data:`FIELD_DETERMINED_BY`), and this method renders THAT stored
        question with THAT stored answer — inventing neither.

        **The marker is never printed.** It names a DataState; G6 bans IRIs
        from the page. It selects, it does not appear.

        **Two asymmetries, and both are deliberate.** A verdict carrying no
        marker returns nothing and is NOT punished — the policy criterion
        writes no origin record by design (ADR-0208 (c)), and a capacity that
        does not claim a determining input has not failed to supply one. A
        verdict that DECLARES one whose question or answer cannot be found
        RAISES: that is a gap, and G2 is raise, never fill.
        """
        nodes = self._deciding_nodes(verdict)
        if nodes is None:
            return None
        answer_node, record_node = nodes
        record = record_node.value
        return (record.get(FIELD_QUESTION), answer_node.value)

    def _deciding_nodes(self, verdict: Any):
        """The (answer, record) pair the DETERMINING marker names."""
        return self._marked_nodes(verdict, FIELD_DETERMINED_BY)

    def _marked_nodes(self, verdict: Any, field: str):
        """The (answer, record) node pair a structural marker names, with
        every check :meth:`deciding_fact` documents. Split out 2026-08-17
        (ship B) so the SOURCE of the deciding fact can be rendered beside it
        without re-deriving the pairing — two callers deriving the same pair
        by different routes is how a page ends up citing one record's
        authority over another record's answer.

        ⚠ **Generalised over the FIELD in step 2**, when a second marker
        appeared (:data:`FIELD_MEASURED_AGAINST`, the stored rule a verdict was
        measured against). Giving the second marker its own resolver would have
        been the smaller diff and exactly the defect the paragraph above
        describes — **the reason to share this is the reason it was extracted
        in the first place.**"""
        if not isinstance(verdict, dict):
            return None
        marker = verdict.get(field)
        if not marker:
            return None
        answer_node = self._node_by_type(marker)
        record_node = self._node_by_type(marker + ORIGIN_SUFFIX)
        if answer_node is None or record_node is None:
            missing = "its answer" if answer_node is None else "its question"
            raise RendererGapError(
                f"a decision on {self.graph.role!r} names the fact that decided "
                f"it, but {missing} is not in this run's stored evidence — "
                "refusing to publish a Record that cannot show its own reason"
            )
        answer_by = self._capacity_of(answer_node)
        record_by = self._capacity_of(record_node)
        if answer_by is None or answer_by != record_by:
            raise RendererGapError(
                f"on {self.graph.role!r} the deciding value and the question it "
                "is supposed to answer were produced by different capacities — "
                "refusing to print a question over an answer that did not come "
                "from it"
            )
        record = record_node.value
        if not isinstance(record, dict) or not record.get(FIELD_ADMITTED):
            raise RendererGapError(
                f"a decision on {self.graph.role!r} was determined by a value "
                "whose own record does not admit it — a verdict standing on a "
                "refusal is incoherent, and the page will not carry it"
            )
        return (answer_node, record_node)

    def deciding_source_lines(self, verdict: Any) -> List[str]:
        """The authority behind the fact that DECIDED, when it has one.

        **Why this exists.** :func:`_source_lines` associates a record with a
        value by SAME CAPACITY, which is right and which means beat 4's
        assessment page named no edition at all: the limit is produced by the
        policy lookup, the conclusion by the capacity that decided against
        it, and nothing joined them. A Record that prints *"350000 payable"*
        without saying which edition said 350000 shows the effect and hides
        the reason — the exact defect :func:`_source_lines` was written for,
        one hop further out.

        **It reuses the marker's own pairing**, so the authority printed is
        the authority of the answer printed directly above it, never a
        record that merely happens to be in the graph. A deciding fact whose
        record is not a policy record renders nothing: routing's readers
        cite no edition, and inventing a line for them is not this method's
        business.
        """
        nodes = self._deciding_nodes(verdict)
        if nodes is None:
            return []
        record = nodes[1].value
        if not isinstance(record, dict):
            return []
        if record.get(FIELD_PRODUCER_KIND) != PRODUCER_POLICY_LOOKUP:
            return []
        line = _source_line_from_record(record)
        return [line] if line else []

    def rule_lines(self, verdict: Any) -> List[str]:
        """The stored RULE a verdict was measured against, and its edition.

        **Why the page needs this and the deciding fact is not enough.** Step 2
        moved routing's threshold out of a Python conditional and into a dated
        policy edition — and the page said NOTHING about it. The deciding fact
        is the claimant's weeks off work, whose source is the intake record; the
        threshold reached the decision and never reached the page. **Stored is
        not shown.** Found by a probe before a guard was written.

        **Two lines, in the record's own words.** The rule's stored question
        with its stored answer, then the edition and window that stated it —
        the same ``_source_line_from_record`` beat 4's limit already uses. The
        renderer composes neither: a capacity that measured against a rule says
        which DataState held it, and everything printed comes out of that
        DataState's own record.

        **Nothing is rendered where nothing was applied.** A vehicle exposure
        routed on coverage alone and a refusal that never reached the
        comparison both carry no marker, so both get no rule line. **A page
        citing an authority it did not consult is the same defect as a renderer
        composing an outcome word** (§0.3 item 11), one hop further out.
        """
        nodes = self._marked_nodes(verdict, FIELD_MEASURED_AGAINST)
        if nodes is None:
            return []
        answer_node, record_node = nodes
        record = record_node.value
        if not isinstance(record, dict):
            return []
        out = [f"   Q. {record.get(FIELD_QUESTION)} — {_fmt(answer_node.value)}."]
        if record.get(FIELD_PRODUCER_KIND) == PRODUCER_POLICY_LOOKUP:
            line = _source_line_from_record(record)
            if line:
                out.append(line)
        return out

    def _unconsumed(self, nodes: List[Any]) -> List[Any]:
        """Of ``nodes``, those with no outgoing ``CONSUMES`` edge."""
        consumed = {
            edge.source.node_id for edge in self.graph.edges.values()
            if edge.type_name == "CONSUMES"
        }
        out = []
        for node in nodes:
            node_id = next(
                (nid for nid, c in self.graph.nodes.items() if c is node), None
            )
            if node_id not in consumed:
                out.append(node)
        return out

    def terminal_outcomes(self) -> List[Any]:
        """Unconsumed produced values INCLUDING refusal carriers.

        **A refusal is a conclusion** (ADR-0209 shape (a)): a completed run
        that refused is a Record, not a fault. ``plain_produced`` filters
        refusal carriers out because they render through a different form, so
        the completed-vs-conclusion check must not be asked in those terms.

        Found 2026-08-17, and it is the more interesting half of that day's
        conclusion fix: the §30 Q2 check had been satisfied on the refusing
        settlement leaf by the value the decision CONSUMED — a premise standing
        in for a conclusion. It passed for a reason unrelated to what it
        asserts, which is a green guard that was not checking its own claim.
        """
        candidates = [
            node for node in self.produced
            if not (isinstance(node.value, dict)
                    and "origin_producer_kind" in node.value)
        ]
        return self._unconsumed(candidates)

    def terminal_produced(self) -> List[Any]:
        """The produced values NOTHING consumed — the graph's own conclusions.

        **Why this exists, found 2026-08-17 by a fixture rather than by
        reading.** The page used to take ``plain_produced()[0]``, which is
        node-iteration order and is not a stored fact. It was unambiguous only
        because every leaf shipped until now produced exactly ONE plain value.
        The first leaf with two — a reader that admits a value plus the
        decision that consumes it — published this:

            E. Nakamura, ... — the claim as it arrived
               reading the claim as filed → sworn statement of loss, filed 9 June

        A premise, printed as the conclusion, with the verdict absent. G2
        refuses to render a derived value as a premise; this is the same error
        inverted, and nothing could see it.

        **The record answers it.** A value the run went on to use carries an
        outgoing ``CONSUMES`` edge; a conclusion does not. That is structure in
        the graph, not an accident of ordering. Two unconsumed values is
        genuine ambiguity and RAISES rather than picking one — the record
        cannot say which is the Record's conclusion, and G2 is raise, never
        fill.
        """
        out = self._unconsumed(self.plain_produced())
        if len(out) > 1:
            raise RendererGapError(
                f"{self.graph.role!r} produced more than one value that nothing "
                "consumed, so the record cannot say which one is this Record's "
                "conclusion — refusing to pick by iteration order"
            )
        return out

    def refusing_conclusions(self) -> List[Any]:
        """The refusal CARRIERS nothing consumed — a refusing leaf's own
        conclusion, the counterpart of :meth:`terminal_produced`.

        **Why a refusing leaf needs one at all.** Every answered page carries
        ``<what was being done> → <what came of it>``; a refusing leaf carried
        only the reader's Q line, so the page never named the decision that
        was ATTEMPTED. Beat 3 is where that shows — a page about a missing
        document that never says the claim cannot be settled — but it is true
        of every refusing leaf.

        **The member road is deliberately NOT changed.** There the fold's
        claim-level line already names the consequence (*"1 not yet assigned:
        D. Laurent, Bodily Injury"*), so the attempted decision is not
        hidden. A leaf has no fold, and that is the whole asymmetry.

        Two unconsumed carriers RAISE, exactly as two unconsumed plain values
        do: the record cannot say which one is this Record's conclusion, and
        picking by iteration order is the defect that rule replaced.
        """
        candidates = [
            node for node in self.produced
            if isinstance(node.value, dict)
            and node.value.get(REFUSAL_MARKER)
            and FIELD_PRODUCER_KIND not in node.value
        ]
        out = self._unconsumed(candidates)
        if len(out) > 1:
            raise RendererGapError(
                f"{self.graph.role!r} produced more than one refusing value "
                "that nothing consumed, so the record cannot say which one is "
                "this Record's conclusion — refusing to pick by iteration order"
            )
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


def _token_in(needle: str, haystack: str) -> bool:
    """True iff ``needle`` occurs in ``haystack`` as a WHOLE TOKEN.

    ⚠ **Bounded on purpose, and the reason is arithmetic.** The echo rule asks
    whether an intake value already appears in a line below it, and a bare
    ``in`` answers YES for ``"3"`` inside ``"350000"`` and for ``"50"`` inside
    ``"50000"`` — so an unrelated number containing a value's digits would
    silently delete that value from the page. A page quietly losing context is
    the failure G2 exists to refuse, and no reader would ever spot it. A match
    counts only where both edges are non-alphanumeric or the end of the text.
    """
    if not needle:
        return False
    start = haystack.find(needle)
    while start != -1:
        before = haystack[start - 1] if start else ""
        end = start + len(needle)
        after = haystack[end] if end < len(haystack) else ""
        if not before.isalnum() and not after.isalnum():
            return True
        start = haystack.find(needle, start + 1)
    return False


def _fmt_without(value: Any, drop: Any, texts: Any = ()) -> str:
    """:func:`_fmt`, minus the value the deciding fact is about to state.

    **Why, from the first live read of the page, 2026-08-17.** The intake line
    prints every field of the exposure, so the answer to the deciding question
    stood one line above the question — and Screen A's left panel prints the
    same intake a third time. What the deciding fact ADDS is *which* fact was
    decisive, not what it was; the answer half was already on screen and read
    as filler on the exposures whose coverage alone decided them.

    Narrow on purpose: only the echoed value goes. C. Mensah keeps *Bodily
    Injury* — that is context the decision needed and did not state — and loses
    only the duplicated *severe*.

    **Stated limit:** the renderer knows the deciding VALUE, never the field
    name the reader read (an origin record carries ``source_datastate``, not a
    key). So two fields carrying the identical value both drop. The page cannot
    tell them apart, and dropping one arbitrarily would be a guess.

    ⚠ **THREE DOORS since ship B, not one** (coordination §101.3, §102).
    A value is duplicated whether it is echoed from the deciding ANSWER
    (exact match, the original rule), from the text of the deciding QUESTION,
    or from the composed VERDICT sentence — the third arrived the moment a
    decision started naming its own operands, and two doors would have left
    the same number labelled once and bare once on one page. Text matches are
    WHOLE-TOKEN (:func:`_token_in`); a bare substring test would delete
    ``"3"`` because some unrelated total contains ``350000``.
    """
    if not isinstance(value, dict):
        return _fmt(value)
    kept = {
        k: v for k, v in value.items()
        if v != drop
        and not any(_token_in(str(v), text) for text in texts if text)
    }
    return _fmt(kept) if kept else _fmt(value)


def _source_lines(analysis: "_Analysis", node: Any) -> List[str]:
    """The authority behind an admitted value: which edition, in force when.

    Beat 4 of the demo script — *the policy changed mid-claim* — is two
    Records naming different versions, so a page that prints only the number
    (350,000 vs 375,000) shows the effect and hides the reason.

    **Two absences, and the contract tells them apart.** ``supplied_fields``
    names what this producer ALWAYS populates when it admits; a field missing
    from that set is a DEFECT and raises (G2). ``source_in_force_to`` is
    deliberately NOT in the set — an open-ended edition legitimately has no
    end — so its absence renders as *onwards* rather than raising or
    vanishing.

    **Narrowed to `policy_lookup` on purpose.** Every reader produces an
    origin record; a general provenance line for all of them is a bigger
    design that would rewrite every page in the demo. This renders the one
    beat 4 needs and leaves the rest untouched.
    """
    lines: List[str] = []
    for record in analysis.policy_records_for(node):
        line = _source_line_from_record(record)
        if line:
            lines.append(line)
    return lines


def _source_line_from_record(record: Dict[str, Any]) -> Optional[str]:
    """One admitted policy record -> its Source line, or ``None``.

    Extracted 2026-08-17 (ship B) so :meth:`_Analysis.deciding_source_lines`
    renders the SAME sentence from the SAME fields; a second formatter would
    drift from this one on the first edition that has no end date.
    """
    missing = sorted(
        field for field in (record.get(FIELD_SUPPLIED_FIELDS) or ())
        if record.get(field) in (None, "")
    )
    if missing:
        raise RendererGapError(
            "a source record admits a value but is missing the field(s) "
            f"its own producer declares it always supplies: {missing!r} — "
            "refusing to name an authority the stored evidence cannot pin"
        )
    phrase = record.get(FIELD_SOURCE_PHRASE)
    version = record.get(FIELD_SOURCE_VERSION)
    if not phrase or not version:
        return None
    ends = record.get(FIELD_IN_FORCE_TO)
    window = f"in force from {record.get(FIELD_IN_FORCE_FROM)}"
    window += f" to {ends}" if ends not in (None, "") else " onwards"
    return f"   Source: {phrase}, version {version}, {window}."


def _member_block(member: "_Analysis", entry: Any) -> List[str]:
    """The lines one member contributes, for one list entry.

    Extracted so correlation can COMPARE candidates instead of taking the
    first: §30's interchangeability argument holds only where the rendered
    blocks are identical (a genuinely duplicated exposure), and the renderer
    must be able to tell that case from an ambiguous one rather than assume it.
    """
    fact = member.deciding_fact(entry)
    echoed = fact[1] if fact else None
    # The same three doors as the leaf road. Nothing on the routing pages
    # matches today; applying it to one road only is the one-member-domain
    # shape this lane has paid for five times.
    texts = [str(fact[0])] if fact else []
    texts.append(_verdict_text(entry))
    lines = [
        f"{_fmt_without(start.value, echoed, texts)} — "
        f"{member.start_description(start)}"
        for start in member.parentless
        if not isinstance(start.value, list)
    ]
    lines.extend(member.deciding_lines(entry))
    # The rule comes AFTER the fact it measured and BEFORE the verdict: the
    # room reads the claimant's fact, then what it was tested against, then
    # where the exposure went.
    lines.extend(member.rule_lines(entry))
    lines.append(f"   {member.phrase_for_value(entry)} → {_verdict_text(entry)}")
    produced = next((n for n in member.produced if n.value == entry), None)
    if produced is not None:
        lines.extend(_source_lines(member, produced))
    for line in member.deciding_source_lines(entry):
        if line not in lines:
            lines.append(line)
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
            conclusions = fold.terminal_produced()
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
            conclusions = fold.terminal_produced()
            if conclusions:
                lines.append(
                    f"Therefore: {fold.phrase()} → "
                    f"{_verdict_text(conclusions[0].value)}"
                )
    else:
        analysis = analyses[0]
        terminal = analysis
        # Only where a conclusion is what this page will show. A stopped or
        # refusing leaf takes a different branch below, and asking
        # terminal_produced() there would put a new raise on paths this ship
        # has no business touching.
        _leaf_echo = None
        _leaf_texts: List[str] = []
        if analysis.stopped is None and not analysis.origin_refusals():
            _leaf_produced = analysis.terminal_produced()
            if _leaf_produced:
                _leaf_fact = analysis.deciding_fact(_leaf_produced[0].value)
                _leaf_echo = _leaf_fact[1] if _leaf_fact else None
                if _leaf_fact:
                    _leaf_texts.append(str(_leaf_fact[0]))
                _leaf_texts.append(_verdict_text(_leaf_produced[0].value))
        for start in analysis.parentless:
            lines.append(
                f"{_fmt_without(start.value, _leaf_echo, _leaf_texts)} — "
                f"{analysis.start_description(start)}"
            )
        refusals = analysis.origin_refusals()
        records = analysis.refusing_records()
        if analysis.stopped is not None:
            lines.extend(analysis.stop_lines())
        elif refusals:
            if not records:
                # The member road has always raised here; the leaf road did
                # not, because before a refusal-capable LEAF verdict existed
                # the only refusing value on a leaf WAS its origin record.
                # It is reachable now (beat 3), and the unguarded form
                # printed the structural marker's absent fields — a page
                # reading "Q. None — Nothing. None".
                raise RendererGapError(
                    f"a refusing value on {analysis.graph.role!r} has no "
                    "origin record to speak from — refusing to render a "
                    "refusal with no stored words"
                )
            refusal = records[0]
            lines.append(
                f"Q. {refusal.get('question')} — Nothing. "
                f"{refusal.get('refusal_detail')}"
            )
            # The decision that was ATTEMPTED, in its own registered phrase.
            # Without this the page states a missing item and never says what
            # could not be done because of it, which is a shorter version of
            # the beat above it rather than a beat of its own.
            carriers = analysis.refusing_conclusions()
            if carriers:
                said = carriers[0].value.get(FIELD_REFUSAL_PHRASE)
                if not said:
                    raise RendererGapError(
                        f"a refusing value on {analysis.graph.role!r} names no "
                        "words of its own for what could not be done, and this "
                        "module does not speak for a capacity about its own "
                        "outcome — refusing to compose one"
                    )
                lines.append(
                    f"   {analysis.phrase_for_value(carriers[0].value)} → {said}"
                )
        else:
            produced = analysis.terminal_produced()
            if produced:
                lines.extend(analysis.deciding_lines(produced[0].value))
                lines.extend(analysis.rule_lines(produced[0].value))
                # phrase_for_value, not phrase(): the leaf road carries the
                # SAME defect the member road fixed and nobody carried the fix
                # across — phrase() returns the first phrased capacity, which
                # on a reader+decision leaf is the READER, so the page credited
                # "reading the claim as filed" with a verdict the settle
                # capacity produced. Invisible until a leaf had two capacities.
                lines.append(
                    f"   {analysis.phrase_for_value(produced[0].value)} → "
                    f"{_verdict_text(produced[0].value)}"
                )
                lines.extend(_source_lines(analysis, produced[0]))
                for line in analysis.deciding_source_lines(produced[0].value):
                    if line not in lines:
                        lines.append(line)
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
        if terminal.stopped is not None or not terminal.terminal_outcomes():
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
