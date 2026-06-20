# MindsOS Skill Acquisition Manual

**Status:** working draft · started 2026-06-18 · living document.
**Audience:** anyone who wants to teach MindsOS a new skill — a new domain it can
reason about and solve tasks in.
**Scope:** the **authoring** half of skill acquisition (how you design and ground a
skill). The **distribution** half (how a finished skill is packaged and installed)
is specified in `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` + `..._PHASE_MAP.md`.
Authoring comes first; distribution packages the result.

> This manual is distilled from worked examples (the first being an ARC-AGI solver).
> Examples below are deliberately **generic** so the method transfers to any domain —
> reading receipts, planning routes, parsing logs, controlling a robot, etc.

---

## 0. What a "skill" is in MindsOS

A skill is a **self-grounding region of the MindsOS graph** for one domain:

- an **L2 world-model** — the *ontology* (the classes of thing the domain contains
  and how they relate) and the *lexicon* (the named terms);
- an **L3 capability layer** — the *DataStates* (the data the skill manipulates) and
  the *capacities* (the functions that derive and transform that data);
- such that, given a task, MindsOS can **compose the solution by walking its own
  graph** — with no human-supplied glue code in between.

The test of a real skill is not "does it produce the right answer once." It is:
**can the system, by itself, trace every conclusion back to what it was given?**
If a human has to supply the connecting logic, the skill is not yet acquired.

---

## 1. The first principle — nothing is intrinsic

Everything the skill knows must come from somewhere the system can point to.

> **Rule 1 — three homes.** If a thing has a name, it must exist in three places:
> the **ontology** (as a class/relationship), the **lexicon** (as a term), and **L3**
> (as a *DataState* if it is data, or a *capacity* if it is a derivation).
> Nothing is computed silently inside code that the graph cannot see.

> **Rule 2 — one ground.** Every skill has exactly one **ground**: the raw input it
> is handed (its *substrate*). Everything else in the skill is *derived from* or
> *composed of* other things, ultimately bottoming out at the ground.

*Generic example.* A receipt-reading skill is handed a `RawReceipt` (the ground).
Everything it later talks about — `LineItem`, `Price`, `Total`, `Vendor` — must trace
back to `RawReceipt`. `Total` is not a fact that appears from nowhere; it is *derived*
(summing the `Price` of each `LineItem`), and that derivation is a capacity the graph
records, not a line of code hidden in a script.

> The ground itself may have a deeper origin in the wider world (a `RawReceipt` is
> really pixels, or characters and tokens). For one skill you **declare** a ground and
> stop there; grounding *below* it is a separate, larger concern.

---

## 2. Two axes every term lives on — provenance and attachment

This is the distinction that makes Rule 1 precise. Every term answers **two different
questions**, and they must not be confused:

- **Provenance — *how did this come to be?*** Exactly one of:
  - it is the **ground** (handed in), or
  - it is **composed** of parts (a whole built from constituents), or
  - it is **produced** by a capacity (computed/derived from inputs).
  This is the axis the system walks to prove grounding.

- **Attachment — *what is this bound to in the world-model?*** Zero or more of:
  - it is an **attribute of** something (a borne property),
  - it is a **part of** something (a constituent),
  - it is a **participant in** a relation.

The same node can play **different roles in different wholes**.

*Generic example.* A `Color`:
- is a **constituent part of** a `Pixel` (a Pixel *is* a position bound to a color —
  remove the color and there is no pixel) → on the *attachment* axis, compositional;
- is an **attribute of** a `Region` (the region *has* a dominant color, but a region
  is not *made of* its color) → on the *attachment* axis, an attribute;
- and on the *provenance* axis it was **read from** the ground.

And a derived value is **both** derived and attached: a `BoundingBox` is *produced* by
a capacity (provenance) **and** is an *attribute of* the region it bounds (attachment).
"Derived" and "attribute" are answers to different questions — never an either/or.

> **Why this matters for grounding.** The grounding check (§5) walks **provenance
> edges only**. An attribute edge ("Region has Color") is *not* how the Color was
> grounded — the Color grounds through its own provenance (read from the ground). If
> the check walked attribute edges it would "ground" things through the wrong path.

---

## 3. The building blocks

### 3.1 DataStates — the nouns
Every kind of data the skill handles is a **DataState** (a node type in L3). The ground
is a DataState; so is every derived or composed thing. **Attributes are DataStates too**
— a color, a size, a bounding box are *nodes*, attached by edges, **not opaque fields
hidden inside a blob.** If you find yourself stashing a value inside a record that the
graph cannot address, you have broken Rule 1.

### 3.2 Capacities — the verbs
Every derivation or comparison is a **capacity**: a function declared as
`consumes → produces` over DataStates. A capacity belongs to a **family** (perception,
decomposition, derivation, comparison, transform, …) and declares how it signals
*"I don't apply here"* (its don't-know contract). Capacities never call other capacities
and never choose which capacity runs next — that is the graph's job (§4).

### 3.3 Edges — the connective tissue
Edges come in three groups. Keep them straight:

| Group | Edge kinds | Answers |
|---|---|---|
| **Provenance** | composed-of (whole ⊣ parts), produced-by (capacity output), derived-from | how a thing came to be |
| **Attachment** | attribute-of, part-of, relation-participant (from/to, between) | what a thing is bound to |
| **Taxonomic** | subclass-of, instance-of, exemplifies | what kind of thing it is |

MindsOS provides the structural primitives for these (binary edges, n-ary hyperedges,
cross-graph edges, and the OWL taxonomic edges). A **composition** — a whole built from
ordered, named parts (a Pixel from a Position *slot* and a Color *slot*) — is the one to
watch: it needs a hyperedge that distinguishes the **whole** from its **parts** and keeps
the part **roles ordered**. (See the *Pending primitive* note at the end.)

### 3.4 Attributes are nodes
Repeating because it is the most common mistake: model `size`, `color`, `bbox`,
`position` as **DataState nodes** with `attribute-of` edges — not as fields. This is
what lets the system reason about an attribute, ground it, and reuse it across wholes.

---

## 4. Activation is graph paths, not a program

You do **not** write the pipeline that solves a task. You declare DataStates and
capacities with their `consumes → produces` signatures, and the system **composes** the
chain by matching outputs to inputs (a path-finder over the capability graph). Adding a
capacity extends what can be solved automatically; you never edit a dispatcher.

*Consequence.* If part of your skill only works because a script calls functions in a
fixed order, that part is **not in the skill** — it is glue outside the graph, and it
will not generalize. Move the logic into capacities and let the path-finder connect them.

---

## 5. The grounding invariant — the definition of "done"

This is how MindsOS *knows the skill by itself*, with no author standing by:

> **Grounding invariant.** Within the skill's graph, every DataState except the
> ground has **at least one inbound provenance edge** (composed-of, produced-by, or
> derived-from), and a **provenance walk from any node reaches the ground**. A
> non-ground node with no inbound provenance edge is an **orphan** → the skill fails
> the check.

Build a **checker** that runs this walk (the same spirit as a test). When it passes,
the skill is acquired: the system can explain the origin of anything it derived, all the
way down to what it was handed. Until it passes, you have inline shortcuts or floating
terms — find them and ground them.

> Grounding is **per-skill-graph**. A skill grounds to *its own* declared substrate, not
> to the whole of MindsOS. Other parts of the system have their own grounds.

---

## 6. The process, step by step

1. **Declare the substrate.** Name the one raw input the skill is handed (the ground).
2. **Enumerate the terms (ontology pass).** List the classes the domain contains and the
   relationships among them. Resist inventing things that don't trace to the ground.
3. **Place every term in all three homes.** For each: an ontology class, a lexicon entry,
   and an L3 DataState (data) or capacity (derivation). Nothing skips a home.
4. **Assign each term's edges.** Give every non-ground term its **provenance** edge(s)
   (composed-of / produced-by / derived-from) and its **attachment** edge(s)
   (attribute-of / part-of / relation). Attributes become nodes here.
5. **Write the capacities.** Implement each derivation as a `consumes → produces` capacity
   in the right family with a don't-know contract; register its DataStates.
6. **Let the path-finder compose.** Verify that, given the ground, the system can *find*
   the chain to the target — don't hand-wire it.
7. **Run the grounding check.** Walk provenance to the ground from every node; fix orphans
   and inline shortcuts until it passes.
8. **Package and install.** Hand the grounded skill to the distribution mechanism
   (`SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md`): a manifest + data, installed under the
   admin-gated lifecycle.

Steps 2–7 iterate. Each new task you point the skill at exposes a missing term or a
missing capacity; add it, re-ground, repeat.

---

## 6A. Sub-process — Vocabulary Consolidation

Steps 2–5 above are one named, repeatable sub-process: **Vocabulary Consolidation** —
taking every term that has surfaced (in design notes, code identifiers, or discussion) and
driving it until it has all three homes, its edges, and a path to the ground. Run it
**iteratively**: every new task you point the skill at surfaces new terms; consolidate them,
re-ground, repeat.

**Per-term lifecycle.** Each term moves through:

`surfaced → classified → reconciled → placed → edged → grounded`

1. **Harvest** — collect every named term from all sources into one flat list.
2. **Classify** — each term is exactly one of: *data* (→ DataState), *derivation*
   (→ capacity), or *relationship* (→ edge type). Attributes are data (nodes).
3. **Reconcile** — merge aliases to one canonical name (e.g. two names for the same
   capacity, or a casual word for an existing class), kill duplicates, split conflations.
4. **Place** — give the canonical term all **three homes**: ontology class, lexicon entry,
   L3 registration. None skipped (Rule 1).
5. **Edge** — assign its **provenance** edge(s) (composed-of / produced-by / derived-from),
   **attachment** edge(s) (attribute / part / relation), and taxonomic edge(s).
6. **Ground** — verify the term reaches the substrate via a provenance walk. Orphan →
   back to step 5.

**Acceptance = the grounding invariant (§5).** Consolidation is "done" for a skill when
every harvested term is `grounded`. Vocabulary Consolidation is literally the work that
makes the grounding check pass.

**Working artifact (transitional, by design).** During a consolidation pass, keep a scratch
**term table** (one row/term: canonical name · kind · aliases · the three home refs ·
provenance edge(s) · attachment edge(s) · state). Promote each row into the three homes as
you go. **Then discard the table** — once the L3 graph is real, the graph is canonical and
the glossary is *generated from it*. The table is scaffolding, never a fourth source of
truth. (A system that supports this sub-process is specified in
`SKILL_ACQUISITION_SYSTEM.md` §"Vocabulary Consolidation sub-system".)

---

## 7. Anti-patterns (failure smells)

- **Inline computation.** A value the graph can't see (computed in a helper, stored in a
  field). The cardinal sin — it breaks grounding silently.
- **Attributes as fields.** Stuffing `size`/`color`/`bbox` inside a record instead of
  modeling them as attached nodes.
- **Confusing provenance with attachment.** Treating "is an attribute of" as if it
  explained where a thing came from.
- **"Intrinsic" anything.** If you catch yourself saying a property is "just part of"
  a thing with no producing edge, you have an ungrounded term.
- **Hand-wired pipelines.** A fixed call order standing in for graph composition.
- **Verify-green but ungeneralizable.** A rule that reproduces the examples by encoding
  the specific answer (e.g. "move this object to row 4") rather than the *generator* of
  it ("move until it touches the wall"). Passing the examples is necessary, not
  sufficient — carry the rule that *produces* the value, not the value.

---

## 8. A tiny worked sketch (generic)

Teaching a "stack of blocks" skill:

- **Ground:** `RawScene` (handed in).
- **Compose down:** `RawScene ⊣ {Cell*}`; a `Cell` is a composition
  `Cell ⊣ {Position(slot), Color(slot)}` — ordered parts, so the slots are named.
- **Derive:** `Block` is *produced* by a capacity (connected same-color cells);
  `Height` is *derived from* a `Block` (a capacity); `restingOn` is a *relation*
  between two `Block`s (a comparator).
- **Attach:** `Color` is an *attribute of* `Block` **and** a *part of* `Cell`;
  `Height` is an *attribute of* `Block`.
- **Compose a task:** "how tall is the red stack?" → the path-finder chains
  `RawScene → Cell* → Block* → (select red) → Height`, no hand-wiring.
- **Ground check:** every node — `Block`, `Height`, `Color`, `restingOn` — walks back to
  `RawScene`. Passes → the skill can explain its own answer.

Swap "blocks" for invoices, log lines, or map tiles and the shape is identical.

---

## 9. Relationship to the rest of skill acquisition

| Concern | Where |
|---|---|
| **Authoring** a skill (this manual) — ontology, grounding, capacities | this document |
| **Packaging & installing** a finished skill — bundle/manifest, lifecycle | `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` |
| Sequencing of the install mechanism into MindsOS phases | `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` |

A skill is **authored and grounded first** (this manual), then **packaged** (the design
log). A bundle that hasn't passed the grounding check should not be packaged.

---

## 10. Pending primitive (author's note)

A clean intra-graph **composition** (`whole ⊣ {ordered, named parts}` in a single graph)
currently needs a core hyperedge that distinguishes whole from parts and keeps part-roles
ordered and identity-bearing. Until that primitive lands, compositions are modeled either
across graphs (cross-graph composition edges) or by a documented convention. Authors
should write compositions against the **abstract contract** — *one whole anchor, N ordered
member parts, immutable* — and not depend on the concrete realization. (Tracked as a
MindsOS-core item, not a per-skill one.)

---

## 11. Status

Living draft. Each worked skill (ARC first) feeds refinements back here. To be formalized
into a published guide once the method has been exercised on two or three distinct
domains.
