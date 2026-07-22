---
title: reads_mm gates the body-facing MM read handle (truthful invoke read contract)
status: Accepted
date: 2026-07-07
layer: L3
amends: [ADR-0159, ADR-0072]
aliases: [C3, truthful-read-contract, reads-mm-enforcement]
---

# ADR-0200: `reads_mm` gates the body-facing MM read handle

**Status:** Accepted (shipped 2026-07-07, main 54b00c0, tag operand-arity-groups-readsmm-confirmed; built with ADR-0198 + ADR-0199)

**Date:** 2026-07-07 (CORE build chat — ARC comparator family)

## Context

A capacity body must read only what it **declares** it consumes, so that every
finder/plan can trust the `CONSUMES` topology. Part 6 (ADR-0072 §am-2, shipped
`2676b9d`) enforces that declared inputs are **present**, but a body can still
read **undeclared** data through a side channel: the `mm_handle` (MM read
surface) on `CapacityContext`. ARC's `touching_delta` is the worked case — it
declares `(touching, correspondence)` while its body reads `(pair, background)`
and still runs; `background` arrives out-of-band.

ARC filed this as C3 ("declared == body"). That exact form is **not statically
checkable** — you cannot inspect body internals. So C3's buildable form removes
the *ability* to cheat rather than checking for it.

**Grounding verified this chat:**

- `_CapacityBase.reads_mm: bool = False` ships (ADR-0159, Chat B D-B14 read
  discipline) but is **dead** — grep finds it only at its definition; nothing
  reads it.
- `build_context` (`mindsos_intelligence/dispatch.py`) injects
  `mm_handle=self._mm_handle` **unconditionally** to every body.
- **No capacity body anywhere in core reads `context.mm_handle`** (grep across
  `mindsos_capacity` / `mindsos_server` / `mindsos_knowledge`; the only
  `mm_handle` users are the L4 substrate handle impls, not bodies).

So the situation is the exact pre-Part-6 pattern: a declared contract field
(`reads_mm`) that nothing enforces at the injection point.

**ARC's "restrict MMHandle to writes/scope" phrasing is corrected here.** In core
`MMHandle` is a pure **read** surface (`get_or_instantiate`,
`find_instances_by_type`, `produces_of`, `consumes_of`); writes are not on it —
they are on the separate `writeable` callable (ADR-0180). C3 is therefore about
gating a **read** handle, not restricting a write one.

## Decision

**Inject the body-facing `mm_handle` only when the declaration sets
`reads_mm=True`; otherwise inject `None`.** `mm_handle` is injected at exactly
**one** site — L4 `dispatch.build_context` (every L4 invocation funnels through
`L4Dispatcher.dispatch` → `build_context`) — so the gate lives there and is
complete. The other paths carry no MM to leak: `intelligence_layer` builds no
`CapacityContext` (it only passes `mm_handle` to the dispatcher constructor),
and the `capacity_layer.invoke` write path constructs its `CapacityContext`
without an `mm_handle` at all (L3 has no MM handle — it is structurally `None`,
trivially compliant for `reads_mm=False`; a `reads_mm=True` write-body invoked
via the L3/CLI path receiving no MM is a known limitation with no v1 caller).

Consequence for a `reads_mm=False` body (the default): its only read-data source
is its **declared inputs** — declared == body-reads becomes **structurally true
for the MM channel**, without any static body inspection. A body that
legitimately navigates the MM (retrieval / path-finding / trace families)
declares `reads_mm=True` and receives the handle as before.

**Scope fences:**

- **`mm_handle` only.** `kl` is **not** gated — it carries the Phase-34 write
  handles (and relates to the ADR-0180 `writeable` path); gating it would break
  write-bodies. Its read method `read_at_version` has no v1 body caller, so it is
  not a read cheat-channel. `writeable` is untouched.
- **Partial by design.** C3 closes the *declared read handle* side-channel (the
  one ARC cheated through). It cannot stop a body reading module-level globals or
  other imports. C3 = "the only core-provided read handle is declaration-gated,"
  **not** "bodies provably read only declared inputs" (ARC conceded the latter is
  unachievable statically).

**Gate-clearance basis:** this clears the "no scaffolding without a consumer"
gate (design-log §0) on the **Part-6 precedent** — it enforces an
already-shipped, currently-dead declared contract and is a standing correctness /
honesty fix defensible with no live consumer — **not** on additive-inertness
(ADR-0198/0199 clear on that; C3 changes behavior: `mm_handle` moves from
always-injected to declaration-gated). Core blast radius is **0** (nothing reads
`mm_handle`; nothing declares `reads_mm=True`).

## Consequences

- The `CONSUMES` topology becomes trustworthy against the MM side-channel: a
  finder/plan reading declared inputs is no longer trusting an unenforced
  contract for MM reads.
- **Re-pin cost (eyes-open).** On re-pin to the new tag, any consumer-lane body
  (ARC/bongard/robot/WSD) that reads `mm_handle` without declaring `reads_mm=True`
  begins receiving `None`. That is the intended surfacing of an undeclared read;
  those lanes re-gate deliberately (RULES §3) and set `reads_mm=True` where the
  read is legitimate.
- `reads_mm` transitions from dead field to load-bearing declaration.
- **Zero task-solving payoff** — honest grounding, not new solves.

## Alternatives considered

- **Static "declared == body" check** (ARC's original C3). Rejected: body
  internals are not inspectable; ARC conceded this.
- **Remove `mm_handle` from all reactive read-bodies unconditionally.** Rejected:
  breaks legitimate MM-reading families (retrieval/trace) and ignores the
  existing `reads_mm` declaration that already names the distinction.
- **Also gate `kl` on `reads_mm`.** Rejected: `kl` carries write handles; gating
  it breaks write-bodies, and its read method has no v1 caller.
- **A new "read scope" field.** Rejected: `reads_mm` already exists for exactly
  this; adding a parallel field duplicates a shipped contract.

## Supersession / amendment trail

- Amends **ADR-0159** (activates the dead `reads_mm` field at the injection
  point) and **ADR-0072** (extends the Part-6 truthful-invoke contract from
  input-presence to the MM read channel). Ships with **ADR-0198** (operand arity)
  and **ADR-0199** (group/member) as one ARC comparator-family enablement.

## Amendment 1 (2026-07-22 — the handle is the concrete `MMResolver`, Slice 3)

_Inline amendment; base ADR status unchanged (Accepted)._

Records the L5 umbrella CR (`CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md`)
**Slice 3**. C3 gated `mm_handle` at `build_context` but left *what* gets injected
as the raw `MentalModel` (`intelligence_layer.py`) or absent
(`mindsos_server/boot.py`). A `MentalModel` is not an `MMHandle` — it lacks
`get_or_instantiate` — so a `reads_mm=True` body would have received a non-handle.
The gate never fired in prod only because **no shipped capacity declares
`reads_mm=True`** (the §Consequences re-pin cost is still latent).

Slice 3 makes the injected value the concrete read-only **`MMResolver`** (its
`get_or_instantiate` now finishes the pinned instance INTO the routed sub-MM graph
— the knowledge writer; see ADR-0201 Amendment 3), sourced by the new KL-backed
`KnowledgeMMSource`. Wired at both L4 dispatcher sites (`intelligence_layer.py`
submind path + `mindsos_server/boot.py` solve path). The read handle stays
**distinct from write access**: L4 is the sole L5 writer (the capacity writer holds
the real `mm`; ADR-0201/0202), and capacity bodies only *read* through this handle.

- **Blast radius still empty:** no non-test body reads `mm_handle`; no shipped cap
  declares `reads_mm=True`. The handle is inert in prod until a `reads_mm=True`
  consumer ships — same posture as the capacity writer (Slices A/C). Exercised by
  `tests/phase_48/test_knowledge_mm_writer.py`.
- **No status flip.** Additive wiring on the existing gate; C3 semantics unchanged.
