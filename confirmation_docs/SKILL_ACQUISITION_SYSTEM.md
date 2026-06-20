# MindsOS Skill Acquisition System — Architecture

**Status:** design draft · started 2026-06-18 · living document.
**Type:** product/system spec (UI + backend) for the end-to-end Skill Acquisition process.
**Companions:** `SKILL_ACQUISITION_MANUAL.md` (the *method* this system supports);
`SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` (the *distribution/install* mechanism, already
designed).

> **Build gate (consumer discipline).** This is a **spec**, not a build order. The system
> is implemented only **after** the manual process has been exercised by hand on at least
> one real skill (ARC first). Designing a UI+backend for a process not yet run once risks
> building the wrong product. Mock UI precedes any implementation (project working style).

> **Canonical-store rule.** The L3 graph is the source of truth. Every working store in
> this system (term tables, drafts) is **transitional scaffolding** that resolves into the
> graph; the glossary/lexicon view is *generated from* the graph. The backend must not
> institutionalize a parallel permanent register.

---

## 1. What the system is

A guided environment that walks a user (a "skill author") through teaching MindsOS a new
domain — from raw substrate to a grounded, installable skill — without writing glue code.
It turns the manual's method into surfaces and services: harvest terms, model them, ground
them, verify, package.

## 2. Sub-systems (overview)

The Skill Acquisition system decomposes into sub-systems, one per stage of the method.
This document details the **Vocabulary Consolidation** sub-system; the others are stubs
here, to be expanded as the method is exercised.

| Sub-system | Responsibility | Spec status |
|---|---|---|
| **Substrate / Ground setup** | declare the skill's one raw input (ground) | stub |
| **Vocabulary Consolidation** | drive every term to its three homes + edges + ground (§3) | **detailed below** |
| **Ontology / Lexicon authoring** | edit classes, relationships, terms (projection of the graph) | stub |
| **Capacity authoring** | declare DataStates + capacities (`consumes → produces`, family, don't-know) | stub |
| **Grounding verification** | run the provenance walk; report orphans/inline-shortcuts | stub (consumes the §5 invariant) |
| **Packaging / install** | bundle + manifest + admin-gated install lifecycle | **already designed** (`..._DESIGN_LOG.md`) |

Sub-systems are pipeline-ordered but iterative: Grounding verification failing sends the
author back into Vocabulary Consolidation.

---

## 3. Vocabulary Consolidation sub-system

### 3.1 Responsibility
Own the per-term lifecycle `surfaced → classified → reconciled → placed → edged → grounded`
(manual §6A) for a skill under construction. Turn a pile of surfaced terms into entries that
exist in all three homes with correct provenance + attachment edges, and that pass the
grounding walk.

### 3.2 State model (per term)
A **Term record** (the transitional working unit; resolves into the graph):

| Field | Meaning |
|---|---|
| `canonical_name` | the one chosen name |
| `kind` | data \| derivation \| relationship |
| `aliases[]` | merged duplicate names (drift reconciled) |
| `homes` | refs to its ontology class · lexicon entry · L3 registration (DataState/capacity) |
| `provenance[]` | inbound edges: composed-of \| produced-by \| derived-from (or `ground`) |
| `attachment[]` | attribute-of \| part-of \| relation-participant edges |
| `taxonomic[]` | subclass-of \| instance-of \| exemplifies |
| `state` | the lifecycle state |
| `source` | where it surfaced (doc / code / chat) — provenance of the *term itself* |

### 3.3 UI surfaces (to be mocked before build)
- **Harvest inbox** — incoming terms (auto-scraped from code identifiers + docs, plus
  manual add), each as a card with `state = surfaced`.
- **Classify panel** — assign `kind`; quick-filter unclassified.
- **Reconcile / merge** — alias detection (same thing, two names); merge into one canonical;
  split a conflated term.
- **Placement editor** — for a term, create/link its three homes; flags any missing home.
- **Edge editor** — assign provenance + attachment + taxonomic edges; the **two axes are
  visually separated** (provenance vs attachment) so they're never conflated.
- **Grounding map** — a live provenance graph rooted at the substrate; orphans highlighted;
  click a node to walk its path to the ground.
- **Status dashboard** — counts per lifecycle state; "% grounded"; blocking list.

### 3.4 Backend components
- **Harvester** — scrapes identifiers from registered code + parses design docs into
  candidate terms; dedup against existing records.
- **Term store** — holds Term records *during* a consolidation pass. **Transitional**: a row
  is deleted once fully promoted into the graph; the store is empty at steady state.
- **Reconciler** — alias/duplicate detection (string + semantic); merge/split operations.
- **Placement writer** — creates ontology classes, lexicon entries, and L3 registrations
  (DataStates/capacities) from a Term record; keeps the three in parity.
- **Edge manager** — writes provenance/attachment/taxonomic edges (using the shipped core
  edge primitives, incl. same-graph compositional `IntergraphHyperEdge` per L1-10).
- **Grounding walker** — the provenance-only walk from any node to the ground; the engine
  behind the Grounding map and the §5 acceptance gate. Shared with the Grounding-verification
  sub-system (one implementation).
- **Glossary projector** — generates the human-readable lexicon/term list **from the graph**
  (so the lexicon is never hand-maintained at steady state).

### 3.5 Key flows
1. **Pass start** → Harvester populates the inbox from the skill's code + docs.
2. **Per term** → classify → reconcile (merge aliases) → place (three homes) → edge (two
   axes) → walker confirms it grounds → record removed from term store (now in the graph).
3. **Pass end** → Grounding map shows zero orphans → the sub-system signals
   Grounding-verification green → author proceeds to packaging.

### 3.6 Interfaces
- **Consumes:** the substrate declaration (Ground setup); code identifiers + design docs
  (Harvester input).
- **Produces:** populated ontology/lexicon/L3 graph content; a green grounding signal.
- **Shares:** the Grounding walker with the Grounding-verification sub-system.

### 3.7 Open questions (deferred)
- Auto-classification confidence: how much does the Harvester guess `kind` vs require the
  author to set it?
- Alias detection: string-only at v1, or semantic (embedding/synonym) matching?
- Where the transitional term store physically lives (in-memory session vs a scratch graph)
  — must not become durable to avoid the 4th-source-of-truth trap.
- How the two-axis edge editor enforces "provenance walks to ground" *as you edit* (live
  validation vs end-of-pass check).

---

## 4. Status
Vocabulary Consolidation sub-system specified at draft depth. Other sub-systems are stubs.
Next: exercise the manual on ARC by hand, then mock the Vocabulary Consolidation UI before
any implementation.
