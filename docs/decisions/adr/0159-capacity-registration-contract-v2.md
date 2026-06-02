---
title: Capacity registration contract v2 — concurrent / inline / action contracts / reads_mm / typed CapacityContext
status: Accepted
date: 2026-06-01
layer: L3
amends: [ADR-0072, ADR-0078, ADR-0143, ADR-0146, ADR-0147]
aliases: [L3-3, L3-34, L3-47, registration-contract-v2]
---

# ADR-0159: Capacity registration contract v2

**Status:** Accepted

**Date:** 2026-06-01

## Context

`_CapacityBase` (Phase 27, `mindsos_capacity/capacity.py:51-104`) ships fields: `iri`, `name`, `category`, `inputs`, `outputs`, `node_type`, `node_kind`. Chat A R1 + R2 + R5 + Chat B accumulated 5 new fields + typed CapacityContext requirements without formal ratification. ADR-0159 ratifies the full v2 contract as one bundle so the `_CapacityBase` schema change is atomic.

Pending additions:

- Chat A R1 D32.4 (concurrency model): `concurrent: bool` flag.
- Chat A R1 L4-vs-L3 boundary: `inline: bool` flag + `max_latency_ms` declaration when `inline=True`.
- Chat A R2 Push 2 (action contracts): `precondition_iri` + `effect_iri` optional fields.
- Chat A R5 D31 (FOL #9): typed `CapacityContext` base class + per-family extension Protocol.
- Chat B D-B14 (L3 read discipline): `reads_mm` semantic + `version_snapshot: dict[IRI, version_int]` on CapacityContext.
- Chat B D-B14 cascade: new L4 substrate helper `mm.get_or_instantiate(node_iri)` exposed to worker threads; new KL public API `kl.read_at_version(iri, version)` per L0-21.

ADR-0157 (D46) retracted the `dont_know_contract_iri` field claim — family rule is implicit from prefix; not part of ADR-0159 scope.

## Decision

**5 new fields on `_CapacityBase`** (all default-valued; Phase 27–33 capacities pass without migration):

```python
@dataclass
class _CapacityBase:
    # ... existing fields ...
    concurrent: bool = True
    inline: bool = False
    max_latency_ms: Optional[int] = None      # required if inline=True
    precondition_iri: Optional[str] = None
    effect_iri: Optional[str] = None
    reads_mm: bool = False                     # two-valued; L4 acquires read-lock when True
```

`reads_mm` is two-valued: under Chat B D-B13 + D-B15 invariants, L3 capacities never write to MM at v1. The `read_write` enum value (drafted earlier) is dropped as unused.

**New module `mindsos_capacity/context.py`** ships:

```python
@dataclass(frozen=True)
class CapacityContext:
    session_id: str
    user_id: str
    learned_parameters_snapshot: Mapping[str, Any]
    mm_handle: Optional["MMHandle"]
    cancel_token: Optional["CancelTokenView"]
    current_task_iri: Optional[str]
    current_pattern_iri: Optional[str]
    version_snapshot: Mapping[str, int]        # IRI → version_int (read-only via MappingProxyType)
    kl: Optional["KLHandle"]                    # Protocol; Phase 28 import-isolation preserved
    cl: Optional["CapacityLayerHandle"]         # for decision.should_replan etc. registry reads
```

**MMHandle Protocol** (4 methods):

```python
class MMHandle(Protocol):
    def get_or_instantiate(self, node_iri: str) -> "ElementInstance": ...
    def find_instances_by_type(self, type_iri: str) -> list["ElementInstance"]: ...
    def produces_of(self, capacity_instance) -> list["DataStateInstance"]: ...
    def consumes_of(self, data_state_instance) -> list["CapacityInstance"]: ...
```

**KLHandle Protocol** (read methods consumed by capacity bodies):

```python
class KLHandle(Protocol):
    def read_at_version(self, iri: str, version: int) -> Any: ...
    # plus Phase 34 KLWriteHandle methods used by write capacities
```

**CapacityLayerHandle Protocol**:

```python
class CapacityLayerHandle(Protocol):
    def get_declaration(self, capacity_iri: str) -> "_CapacityBase": ...
```

**CancelToken + CancelTokenView**: underlying class has `is_set()` + `request_cancel()`. Body sees `CancelTokenView` wrapper exposing only `is_set()`. L4 substrate holds the full token.

**Per-family CapacityContext extensions** via standard Python subclass + Protocol pattern:

```python
@dataclass(frozen=True)
class WSDCapacityContext(CapacityContext):
    # WSD-specific fields
    ...
```

Family extensions live in their owning chat's scope (WSD installation, FOL installation, etc.).

**5 canonical decision verdict types** (per L3-36 family contract refinement) — `decision.*` family wraps bare-value returns in verdict types so the VERDICT family rule (ADR-0157) applies uniformly:

```python
@dataclass(frozen=True)
class TierVerdict:
    tier: Optional["TierEnum"]
    rationale: str

@dataclass(frozen=True)
class GoalVerdict:
    goal: Optional["Goal"]
    rationale: str

@dataclass(frozen=True)
class PipelineFindVerdict:
    pipeline_iri: Optional[str]
    rationale: str

@dataclass(frozen=True)
class PromotionRuleVerdict:
    rule_iri: Optional[str]
    rationale: str

# Plus existing ReplanVerdict (Chat A R2)
```

**`register_capacity` validation expansion** (~20 LOC):

- `inline=True` requires `max_latency_ms` declared; else raise `CapacityRegistrationError`.
- `precondition_iri` + `effect_iri` must resolve to capacities under `predicate.*` family (per L3-36); else raise.
- `reads_mm=True` declarations sanity-checked against MMHandle availability at runtime.

**Strict-line preservation**: `decision.should_replan` capacity body reads `precondition_iri` + `effect_iri` from step capacity declaration via `context.cl.get_declaration(step_iri)` then invokes them via standard `cl.invoke()`. L4 substrate is data plumbing only; never reads contract IRIs directly.

**Backward compat for Phase 27–33 capacities**:

- Declarations: all new fields default-valued; no migration of declarations.
- Phase 33-35 write capacity **bodies** (consolidate:mm, trace:problem) migrate `context["kl"]` → `context.kl` attribute access (~2-3 bodies; sized at ship R0 probe). Tracked as Phase 27 reframe ship migration item.

## Consequences

**Good:**

- Atomic schema change: ADR-0159 ships with ADR-0156 (D38 bipartite reframe) in Phase X3; one `_CapacityBase` rewrite covers both ADRs.
- Typed CapacityContext gives capacity body authors IDE support + type-checked field access.
- Phase 28 import-isolation invariant preserved (capacity_layer.py imports `KLHandle` Protocol, not `KnowledgeLayer`).
- Strict-line architecture preserved: L4 substrate is plumbing; L3 capacities own all decisions including contract reads.
- Phase 27–33 declarations pass via defaults; no mass migration of capacity authoring code.

**Cost:**

- 5 new fields on `_CapacityBase` + 1 new module (`context.py`) + 4 new Protocols + 5 new verdict types + ~20 LOC `register_capacity` validation.
- `context["kl"]` → `context.kl` body migration for ~2-3 shipped write capacity bodies.
- Phase 27–33 thread-safety audit (L3-32) tags `concurrent=False` on shipped capacities found unsafe; sized at ship R0 probe.

## Alternatives considered

1. **Field-by-field separate ADRs** (one ADR per new field) — rejected: `_CapacityBase` schema change is structurally atomic; splitting into 5 ADRs creates 5 phase-ship coordinations for what is one decision.

2. **`Optional[Any]` typing for KL on CapacityContext** — rejected: loses IDE support; Protocol-based typing satisfies Phase 28 import-isolation without sacrificing types.

3. **3-method MMHandle** (without `produces_of`/`consumes_of`) — rejected: forces every capacity body to re-implement bipartite walks; 4-method surface is the right ergonomic balance.

4. **Per-capacity `dont_know_contract_iri` field** — rejected per ADR-0157; rule implicit from prefix.

## Amendment trail

- Amends **ADR-0072** ("Invoke envelope, ADR-0072 §amendment-1") — context shape transitions from `Optional[Mapping[str, Any]]` to `Optional[CapacityContext]`; envelope contract preserved.
- Amends **ADR-0078** ("L3 capability local copy") — capability check still on session; context.cl Protocol surface unchanged.
- Amends **ADR-0143** ("KL write-handle pattern") — KL injection becomes typed via `context.kl` (Protocol) rather than `context["kl"]` (dict key).
- Amends **ADR-0146** ("L3 symmetric write invocation contract") — write-capacity contract unchanged; typed access path.
- Amends **ADR-0147** ("L3 per-flow write-capacity build pattern") — build pattern unchanged; typed access path.

## Sequencing

Ship phase **X3** — atomic bundle with ADR-0156 (D38 bipartite reframe) + Phase 27 audit deliverable. Two ADRs on `_CapacityBase` → single phase ship for atomic schema change.

## R0 probe set (required before ship R1)

1. `_CapacityBase` dataclass field-order convention (positional vs keyword args at registration).
2. Phase 27–33 shipped capacities count needing `concurrent=False` annotation (L3-32 audit).
3. `MMHandle` Protocol consumers in L4 substrate design notes — verify the 4-method surface is sufficient.
4. `CapacityContext` usage in shipped capacity bodies (Phase 30/31/33) — count of bodies that already destructure context dict; confirm backward-compat shape.
5. KL `read_at_version` Phase 11 side-by-side versioning support — L0-21 cascade sizing.
6. Test impact — Phase 27 dataclass + Phase 28 register + Phase 33 write capacity tests need extension.

## Rationale

Per-decision rationale, 3-round saturation (1 reversal R2 on Fork 5 three-valued → two-valued, 0 reversals R3), and the typed CapacityContext + MMHandle Protocol refinement at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` §registration-contract-v2.
