# ARC → Core change requests (C1, C3, C4, C5)

**Status:** filed 2026-07-06 · from the atom-grounding chat · **not built here** (ARC lane is
docs + demo; core is a separate chat). ARC is the **motivating consumer**; every item is a core
*inconsistency* ARC hit as a user — fixing it benefits every brain.
**Source:** `arc_solver/ATOM_TABLE.md` + `PIPELINE_DECISIONS.md §4/§5`.
**Discipline:** file as **one** proposal extending PIPELINE_DECISIONS §5 (the four are entangled).

---

## Frame

A **capacity = a DataState transition** (`consumes → produces`); the body must realize it. **L4 = the
substrate** (Executor/Dispatcher/MM) — it iterates, dispatches, routes; it owns **no** transitions.
Orchestration *decisions* are L3 caps (`planning.*`/`orchestration.*`/`phase1.*`). Any info in L2/L5
**is** a DataState; an L3 cap declares only `in_ds`/`out_ds` **types** — **L4 binds each to a source
(input/L2/L5) and a dest (output/L2/L5)**. These four requests are the gaps that model can't express.

---

## Disposition (updated 2026-07-07) — ARC commits to REAL registration; this is now a BUILD

Detail + rationale: `PIPELINE_DECISIONS.md §4` (2026-07-07). Spec for C1: `PART5_OPERAND_SPEC.md`.
- **C1** — ARC is now the **executing consumer of record** (will route comparators through `invoke`;
  reopens D3). Scope = **positional operand arity only** (5a); roles are ARC-local. Shape validated
  against all 14 bodies → `PART5_OPERAND_SPEC.md`; **Form B** recommended. bongard-m3 = same shape.
- **C3** — reframed to a buildable form: **restrict the body-facing MMHandle to writes/scope only;
  all read-data arrives as declared inputs** (Part-6 extension). Not "declared==body" (uncheckable).
- **C4** — unchanged; **lands now** (additive; unblocks group naming). No consumer gate.
- **C5** — deferred onto the **ADR-0184** promoted-pipelines seam (teaching/dream = a second trigger
  into the same writer). Non-blocking; ARC sequences known pipelines in L4 code meanwhile.
- **Sequence:** core ships **5a + C4** → ARC decomposes + re-registers. **Open decision for CORE:**
  consumer-discipline gate (RULES §3) is met by a *committed* consumer + validated spec, not a live
  one (see §4 caveat). CORE also owes: `STATE.json` part5 consumer update + the ADR.

---

## C1 — same-type operand arity  *(= §5 Part 5, deferred → un-defer)*

**Gap.** A transition consuming **two operands of the same DataState type** (`same_object: object ×
object`, `moved`, `touching`, all 14 ARC comparators/profilers) can't be declared — inputs are keyed
by DS-IRI, so two `object` slots collide. Shipped ARC fakes it as a **single-input** declaration.
**Need.** Operand **position/role** on the registration contract (roles, not just a set of input DS).
**Impact.** Unblocks the entire comparator/profiler family from honest registration.
**Note.** L4 still supplies *which* two operands (the correspondence/pairing is an L4 decision); C1 is
only about *expressing the arity* in the signature.

## C3 — truthful invoke contract  *(= §5 Part 6, shipped-partial → extend)*

**Gap.** Declared `consumes` must equal what the body actually reads. Part 6 validates inputs but not
"declared == body". ARC's `touching_delta` declares `(touching, correspondence)` while its body reads
`(pair, background)` and still runs — the declared topology is fiction.
**Need.** Enforce declared-inputs == body-reads (types), so a finder/plan can trust CONSUMES.
**Scope note.** Location is L4's (source input/L2/L5); C3 is about **types**, not locations.

## C4 — group / member DataState attribute  *(new; replaces the dropped C2)*

**Gap.** A DataState whose value is a **group** (list/set) of individually-addressable members
(`objects*`, `points*`, `pairs*`) has no typed distinction from its **member** (`object`). L4 must
iterate the group to feed member-consuming caps, but nothing types that seam.
**Need.** A `group=True` + `member_ds=<iri>` attribute on the DataState registration; `*` is its doc
rendering. Group and member are **distinct types** → the finder never bridges them; L4 owns the
unpack loop. Naming follows semantics (group → plural; member → singular); a single entity that
internally holds a set (`palette`) is **not** a group.
**Impact.** Types the L3→L4 iteration seam; makes runtime fan-out expressible **without** finder
cardinality (this is why C2 — "runtime fan-out as a finder feature" — is dropped: fan-out is L4 by
design; C4 just types where L4 iterates).

## C5 — known-pipeline record + lookup

**Gap.** L2 `promoted-pipelines` (the home for **known** pipelines like `perceive`) has **no writer**,
and the finder's promoted-path-**lookup** strategy is **deferred**. So `find_pipeline` — meant for
**unknown** compositions — is the only path; known pipelines can't be recorded or looked up.
**Need.** (a) A **writer** — populated by **user teaching (explicit entry)** now, **dream-suggestion**
later (**not** an auto-promotion loop); (b) the **promoted-path-lookup Finder strategy** un-deferred so
L4 looks a known pipeline up in L2 before falling back to `find_pipeline`.
**Not v1-blocking.** ARC can sequence known pipelines in L4 code meanwhile; C5 is the proper home.

---

## Not core (ARC-side code fixes, deferred to a gated demo chat)

- **E1** `perceived_grid` has no producer → add a `materialize_grid` cap or mark ∅-by-design.
- **E2** `arc.background` orphan (freq detector deleted) → drop or keep placeholder.
- **E7** `arc.color` mis-declared ("recolor param only") → Color value class; re-pair `recolor` around
  `recolor_transform` (ONTOLOGY #10).
- Group naming (`arc.object` → `arc.objects*`/`arc.object`) once **C4** lands.
- Comparator re-registration with real arity once **C1** lands (drop the single-input fictions).
