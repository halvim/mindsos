# CORE — ADR contradiction sweep against ADR-0205 · coverage ledger

**Item:** CORE-C1R4. **Branch:** `feat/adr-sweep` (off `b612c93`).
**Note:** `main` moved to `60fe2ae` during this pass — `#103` shipped, editing **ADR-0071**
and rewriting `CORE_RECONCILIATION_PLAN.md` (C2 id collision, S14 struck, C2R4a claim false,
C3R1 half-shipped, C3R3 merged). **Re-check every CORE-C id below against the new plan.**

**This file carries no decisions.** It proves coverage and routes findings. Decisions land as
amendments in the ADRs themselves.

---

## 0. The result

Six passes. Passes 1–4 asked *"which ADRs contradict ADR-0205?"* and reversed each other every
time — 3, then 9, then 5, then 8 reversals. Pass 5 inverted the method and swept the **code**
for the violation shapes, then mapped back to ADRs. Pass 6 verified the three load-bearing
claims. No reversals in 5 or 6.

**The per-ADR question converged on an answer it was the wrong shape to hold:**

> **No abstraction level above `capacity` has a graph representation at all.**

Verified:

- `IntergraphHyperEdge` / `compositional` — the primitive ADR-0205 §2 rests on — has **zero
  users** in `mindsos_capacity/`, `mindsos_intelligence/`, `mindsos_knowledge/`. Its only
  consumers are `mindsos_instances/` and core itself.
- `mindsos_intelligence/chain_artifacts.py` contains exactly **one** graph call — `add_node`
  at `:216`. **Zero `add_edge`.** All nine chain artifact types are dataclasses stored whole
  as node values; every plan/milestone/pipeline/run relation is a `*_ref` string inside one.
- `Pipeline.edges` — the finder's own dataflow wiring — is read **only inside `to_dict()`**
  (`pipeline.py:171`). `execute_pipeline` walks `steps` in tuple order and re-derives dataflow
  from blackboard key collision. The `ConjunctionFinder` D-E defect documented at
  `pipeline.py:376-388` is that divergence's failure mode.
- The plan level's shipped representation is a nested dict inside a `ShapeDescriptor.opaque`
  DataState value (`planning_v0.py:88-103`), read back out at `plan_construction.py:170-185`.

So every ADR touching the ladder above `capacity` contradicts ADR-0205 — not because each made
a local mistake, but because the primitive was never used. **50 distinct code instances, across
four shapes.** Listing them per ADR describes the symptom.

---

## 1. The criterion, and the scope line it needs

> Does this decision store a ladder **structure** opaquely, or duplicate a ladder structure
> outside the graph?

**Scope** — applies to ladder members at **any level, including the ground**: capacities,
DataStates, pipelines, milestones, plans, request knowledge; their composition, ordering,
subsumption, dependencies. Not to substrate: `Metagraph`, `Graph`, persistence, release
manifests, server/session/auth, audit, `ref:<role>`, `XRef`, `mindsos_instances/`.

Test: *if this structure disappeared, would the system have forgotten something it knows, or
merely lost a way to store it?* Forgotten → in scope.

**ADR-0205 §5 must carry this sentence.** As published the criterion has no boundary; applied
literally it condemns ADR-0016 and ADR-0029, which it does not intend to touch.

### The four shapes

| | |
|---|---|
| **S1** | ladder structure serialized into a value (`to_dict`, `asdict`, hand-built dict) — **20 instances** |
| **S2** | ladder structure as properties instead of edges (`list[IRI]`, `*_ref`, `*_iri`, ordering ints) — **22** |
| **S3** | the same ladder structure described in two places — **10** |
| **S4** | ladder structure that exists only in Python and never reaches any graph — **10** |

By reachability: **16 LIVE-WRITE · 21 LIVE-READ · 13 DECLARED.**

---

## 2. The load-bearing question — answered

ADR-0082 makes plan generation a capacity. A capacity's output channel is a DataState value.
`DS_PLAN` is `ShapeDescriptor.opaque`. Does that force the plan level through a blob, putting
ADR-0082 and ADR-0205 §5 in permanent conflict?

**No. It is wiring, not the contract.**

`CapacityContext.writeable` (`context.py:145`) is injected unconditionally for every dispatched
capacity (`dispatch.py:125`), returns a `KLWriteHandle`, and that handle exposes `graph()` —
raw L1 access (`write_handle.py:93`). Three shipped capacity bodies use it: `trace.py:119`,
`learn_parameter.py:139`, and `consolidate.py:299`, where `g.add_edge(..., EDGE_MEMORY_CONTAINS_EPISODE)`
writes a real composition edge from inside a capacity body, on the live terminal path.

So a planning capacity **could** emit Plan and Milestone nodes with real edges and return only
the root IRI. What is missing is (a) a role-graph with Plan/Milestone NodeTypes and their IRI
builders — the role set is closed at 14/16 and `promoted-pipelines` has no Plan or Milestone
type — and (b) the chain artifacts living in `intelligence_mm`, whose only body-facing handle
(`MMResolver`) has **no write method**.

**ADR-0205 §5 and ADR-0082 can both hold.** This is the single most important finding for the
build plan: it means the plan level can be made a graph without renegotiating the capacity
contract.

---

## 3. Coverage

| Band | Read | Passes applied |
|---|---|---|
| 0060–0100 | 41 | 1, 3 |
| 0101–0112 (Deferred) | 13 | 1, 4 |
| 0114–0144 + 0001–0057 (substrate) | 85 | 1 (band), 3 (wider net) |
| 0145–0170 | 26 + amendments | 1, 3 |
| 0171–0190, 0201–0202 | 21 + amendments | 1, 2, 4 |
| **0191–0200, 0204** | 11 | **2 only — coverage hole found in pass 2** |
| Superseded | 13 | 1, 4 |
| Code sweep (5 packages) | 50 instances | 5, 6 |

**204 ADRs + 115 amendment sections + 50 code instances.**

---

## 4. What the per-ADR pass established that the code sweep does not

Three classes that a code sweep cannot see, and that matter:

**4.1 — Deferred ADRs encode the pre-0205 model and are cheap to correct.** 0083, 0102, 0107,
0108, 0110, 0111, 0118, 0152 §5, 0159, 0177 are `contradicts-if-built`. 0107's six walk
strategies are still wanted; they become strategies on one `Finder`, which is unbuilt work C3
must schedule, not paperwork.

**4.2 — "Superseded ⇒ unaffected" is false.** 4 of 13 carried their defect into the superseder:
0073 → 0155 (`subscribes_to` survived the L3→L4 move), 0104/0105 → 0173 (invalidation as list
slicing), 0106 → 0172 (planning as a capacity emitting an opaque plan). The band's original
clearance was method error.

**4.3 — ADRs that assert the opposite of the code.**

- **ADR-0148** records as shipped fact that compositional hyperedges are `ordered=False` by
  default. The factory **raises** on exactly that pair (`metagraph.py:1916-1922`, `:2183-2187`).
  ADR-0205 §2 amends P8-A; the code still refuses. **This is the first blocking edit in the
  whole plan** — set-composed milestones and plans are unconstructible until it is removed.
- **ADR-0205 §Context** calls the promoted pipeline "a normalised graph." It is
  `edge_sequence: list[capacity_edge_id]` as a content field, plus `start_ds`/`end_ds`
  annotated "Derivable", plus writer-less `HAS_STEP`/`PipelineStep` — three descriptions, no
  writer.
- **ADR-0150** added `learned-pipelines` to a closed role set **with no §Revisions entry**.
  §am-9 says the count "stays 14", §am-10 says "15 → 16". Role #15 is unamended.
- **ADR-0173** §3 specifies bidirectional XRefs; the code ships plain `list[str]`.
- **ADR-0109** rejects static cost properties; `capacity.py:75-76` ships `cost_prior` and
  `latency_ms_prior` as static node properties, LIVE-WRITE, zero readers. (Scalars, so a value
  under §5 — an ADR-vs-code contradiction on a different axis, not a criterion hit.)

**4.4 — Six duplicate-decision pairs.** 0065≡0084 · 0088≡0100 · 0069≡0086 · 0083≡0111 ·
0161 vs 0177 · 0170/0175 §am-1/0180.

---

## 5. Confidence — ADR-0206's claim, verified

**No edge anywhere in production carries a confidence.** `MappingResult.mapping_confidence`
and `StepExecutionRecord.confidence` are fields inside node-value blobs; `RequestPattern.confidence`
and `LearnedParameter.confidence` are node properties; the intended ALS home
(`als_subsystems.py:20,32-41`) is an empty skeleton with no writer. `mapping_confidence` is a
relation — request ↔ pattern — stored on neither endpoint.

ADR-0094 §am-1 is the sharpest instance: it moved confidence off the Pipeline node into
`learned-parameters`, a role whose `EDGE_TYPES = ()`. It relocated a relational quantity into a
keyed side table with no edges at all.

---

## 6. The §10 walk — already one consumer late

ADR-0205 §10 says invalidation, hub discovery, verification and attribution are one walk, built
with the first consumer. **Invalidation already shipped**, as list-index arithmetic:
`replan_check.py:56-61` slices `request_run.pipeline_runs[at_index:]` — a `list[IRI]` inside a
node value. Eight further bespoke traversals exist (`views.py`, both finders,
`MMHandle.produces_of`, the monitor inverted index, `composite_dependencies` parsing a blob,
`capacity_mm_writer.index`, `phase6.attribute_blame` specified-unbuilt).

The ladder is also spelled out as a string enum twice: `replan_check.REPLAN_LEVELS` and
`BlameVerdict.chain_level`.

---

## 7. Where the full instance inventory lives

The 50-instance table with `file:line`, shape, reachability and owning ADR is the working
artifact for whoever builds C2. It is not reproduced here because a central list is not what a
cold chat reads — each instance belongs in the module docstring at its point of use, and each
decision in its ADR. Regenerate it with the pass-5 method: sweep `mindsos_capacity/`,
`mindsos_intelligence/`, `mindsos_knowledge/`, `mindsos_server/`, `mindsos_cli/` for the four
shapes; exclude `mindsos_core/`, `mindsos_instances/`, tests.

---

## 8. Outcome — where the decisions landed

**The C1R4 deliverable is `docs/decisions/adr/0205-abstraction-levels.md` §amendment-1**, not
this file. This file is coverage only.

### 8.1 One finding in §0 was wrong and is corrected in the amendment

An interim reading held that the composition primitive cannot express the ladder's base case,
because `add_intergraph_hyperedge` refuses 1-anchor/1-member. **False** — it looked at one of
two primitives. `IntergraphEdge.compositional` shipped in Phase 05b with identical semantics,
and P19-A already names it as the route for a 1-1 composition. The primitives partition by
arity; ADR-0205 §2 used only one. No core change is needed. See §amendment-1.2.

### 8.2 Rulings taken

- **A — subsumption is not composition.** C11's `SPECIALIZES` ships as a plain typed edge in
  the datastates graph. This is what makes the arity split sufficient: with subsumption
  excluded, no ladder composition is same-graph, and `add_intergraph_edge`'s same-graph
  refusal never binds.
- **B — anchor direction.** `source` = anchor, `target` = member, for compositional
  `IntergraphEdge`. Owed to `INTERGRAPH_EDGES_DESIGN.md` §4.3.

### 8.3 The one open item that blocks C2R2

`remove_graph` refuses if any incident compositional edge exists (Pushback 17-A), and
ADR-0202 persists one chain graph per task. If per-request plan structure is compositional,
every task's graph is permanently unremovable. Three options recorded in §amendment-1.6; none
chosen. **Decide before the milestone graph is built.**

### 8.4 P8-A is a small edit, and it is not the blocker

Two `if` blocks (`metagraph.py:1916`, `:2182`), one test
(`tests/phase_05c/test_validation_order_hyperedge.py:210-224`), three docstring lines.
`ordered=False` types already construct fine (`schema/types.py:164`); only the combination is
refused. The real constraints are §amendment-1.5 (compositional is terminal) and §8.3.

### 8.5 Four orphaned deferrals

`_source_backup/root/mindsos_future_plans.md` does not exist. It is the filed home of:
Pushback 6-A's escape hatch, the `IntergraphEdge` endpoint-update verb, the in-place
hyperedge→edge downgrade (P19-A), and Pushbacks 25-B / 31-B / 33-B / 34-B. No record survives
anywhere.
