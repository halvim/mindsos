---
title: D'1 retention model — version-pinned refs + lazy inline-on-retire (full KL stack)
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L5
related: [0161, 0153, 0150, 0044, 0176]
---

# ADR-0177: D'1 retention model — version-pinned refs + lazy inline-on-retire (full KL stack lands here)

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0161 (KL version-read + retire hook — forward-contract this completes; **amended here**), ADR-0153 (`append_only_with_lazy_inline` mutation discipline + `via_lazy_inline` validator), ADR-0150 (knowledge lifecycle — retire ≠ deprecate), ADR-0044 (`episodic_memories`), ADR-0176 (consolidation — produces the version-pinned Episodes this resolves).

## Context

Chat B §4.4 (D'1) retired note-fork: episodes reference L2/L3 nodes as version-pinned `(node_iri, version_int)` tuples, pinned **at instantiation** (during execution, not at consolidation); KL keeps versions side-by-side (Phase 11); on `retire_version`, affected episodes inline the retired content **lazily on first read after retire** (full snapshot; the inlined content's own outgoing refs stay pinned and inline on *their* next read — bounded transitive inflation, one level per read).

ADR-0161 (Phase 44, Rail C) **froze the design** — `kl.read_at_version`, `kl.retire_version`, the marker property `_retired_inline_pending`, and its `RESERVED_PROPERTY_KEYS` registration — and its §Decision text reads "Phase 44 ships both." **Grounding at Phase 48 R0 found none of it shipped** (no `read_at_version`/`retire_version` in `mindsos_knowledge`; `_retired_inline_pending` appears nowhere in `mindsos_knowledge`/`mindsos_core`). The Phase-44 CR-4 narrowing deferred S6 here; the §Decision text was never corrected. **Phase 48 lands the entire D'1 stack.** (ADR-0161 amended accordingly — see ADR-0161 §amendment-1.)

## Decision

### 1. KL surface (L2 — lands here, not Phase 44)

- `kl.read_at_version(metagraph, role, version)` — version-pinned read off the Phase-11 side-by-side version graphs.
- `kl.retire_version(metagraph, role, version)` — flips `_retired_inline_pending=true` on the retired version node and releases the KL-held content for lazy inlining. Distinct from `kl.deprecate_version` (deprecated content stays readable side-by-side; only **retire** releases).
- `_retired_inline_pending` (boolean node property, co-located with the versioned content) registered in `RESERVED_PROPERTY_KEYS` (`mindsos_core/schema/validation.py`) so schema validation accepts the marker write. Name + location are as ADR-0161 §3 froze them.

### 2. Read-time consumer (L4 — `retention.py`, PB-4)

Episode-load paths route version-pinned refs through `retention.resolve_refs(episode)`: for each `(iri, version)`, `kl.read_at_version(...)`; if the version node carries `_retired_inline_pending`, **inline a full snapshot into the episode** (the referrer) and clear that ref's pending consultation; the inlined content's outgoing refs stay pinned and inline on the next `resolve_refs` (bounded transitive inflation). The consultation lives in **L4**, not inside `kl.read_at_version` — KL stays a pure version-store; mutating episode content on read is an L5 concern (Episode-immutability §4.5 carves lazy-inline out explicitly).

### 3. v1 consumer status (PB-9 consequence)

The v1 dream driver re-runs from the episode's `task_input` (ADR-0178), **not** full episode-MM reconstruction, so `resolve_refs` has **no live v1 consumer**. S7 ships **unit-test-only** (retire → first read inlines + second read inlines the transitive ref); the real consumer is WSD retrieval / episode reconstruction. Consistent with the ship-ahead-of-consumer-if-testable bar (ADR-0155/0156/0159/0162 precedent).

## Rationale

- **Marker on the node, consumer in L4.** Co-location keeps retire a single-node write; L4 ownership keeps KL read/write-separated and keeps Episode immutability an L5 invariant.
- **Land the whole stack now.** Phase 44 shipped none of the forward-contract; splitting it again buys nothing and the design is frozen.
- **Bounded inflation.** One inline level per read prevents a retire from forcing a full transitive walk.

## Consequences

- New L2 KL methods + the reserved-key entry (an L2 surface beyond the PHASE_MAP Phase-48 "Modules touched" list — accepted scope delta).
- ADR-0161 §Decision/§Implementation text was aspirational; corrected by its §amendment-1.
- S7 is tested-not-consumed at v1.

## Alternatives considered

1. **Consultation inside `kl.read_at_version` (L2).** Rejected — a read with a cross-role-graph write side-effect; violates KL read/write separation + Episode-immutability ownership.
2. **Eager inline on retire (walk all episodes).** Rejected — unbounded write amplification on retire; D'1 is explicitly lazy.
3. **Re-defer to a later phase.** Rejected — the forward-contract has already slipped once; the design is frozen and the read-consumer is testable.

## §Implementation (Phase 48; pending ship)

`mindsos_knowledge` `read_at_version`/`retire_version` + `RESERVED_PROPERTY_KEYS` entry (commit-group 1); `mindsos_intelligence/retention.py` (NEW, read consumer — commit-group 4). Tests: `tests/phase_48/test_kl_version_hooks.py` (S6 — marker write + read + reserved-key), `test_d_prime_1_retention.py`, `test_episode_immutability_invariant.py`.

## §note (Opt C — `version_int` is the D'1 pin; multi-version is latent)

Phase-48 R0 grounding found the KL version surface thinner than this ADR's framing assumed: `KnowledgeLayer` has no version-lifecycle methods (`versions_in_role` is read-only on `MetagraphView`); `writeable(…, version="v1")` treats version as an **IRI literal** — "sole version under current role schemas." Per the chat decision (Opt C, user-ratified), `read_at_version`/`retire_version` keep the **already-shipped Protocol signature `(iri: str, version: int)`** (`CapacityContext.KLHandle`, ADR-0159) and are backed by the current single-version-per-role store: the version-qualified `iri` identifies the version, and `version_int` is the D'1 `(node_iri, version_int)` **pin** recorded by callers. Multi-version-per-node resolution (true Phase-11 side-by-side graphs) is **latent** and exercised on synthetic two-version data until real >1-version content exists. The retire marker is per-node as ADR-0161 §3 froze; bulk role-version retire is a caller loop. The earlier ADR-0161 `(metagraph, role, version)` framing is superseded by the shipped Protocol `(iri, version)` signature.
