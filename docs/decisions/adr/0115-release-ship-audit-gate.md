---
title: Release-ship audit gate + impact report (v1 narrow — ReleaseSummary + SimilarityWarning only)
status: Accepted
date: 2026-05-22
layer: L0
amends: []
related: [0049, 0053, 0056, 0114, 0118, 0141, 0144]
supersedes: [0009]
---

# ADR-0115: Release-ship audit gate + impact report (v1 narrow)

**Status:** Accepted (2026-05-22 — Phase 24 ship; `mindsos_admin/audit_gate.py::run` ships; `mindsos_server/release.py::release_update` consumes; two-pass `compute_similarity` per PB-24(b) wired.)

**Date:** 2026-05-22

**Supersedes:** [ADR-0009](0009-similarity-report-freshness.md) (freshness-id mechanism — replaced by audit-gate two-pass similarity).

**Related:** [ADR-0118](0118-per-user-transactional-promotion.md) (`release_update` callsite); [ADR-0144](0144-similarity-at-release-ship-audit-gate.md) (`compute_similarity` heuristic + §Placement full Accept at this ship); [ADR-0114](0114-release-manifest-and-version-db-schema.md) (releases / pending_mutations tables the gate reads); [ADR-0049](0049-similarity-report-before-promotion.md) + [ADR-0053](0053-promote-per-candidate-atomic-rollback.md) + [ADR-0056](0056-promotion-result-preserves-input-order.md) (indirect Supersessions per Phase 16 §am1 lock — fully closed at this ship); [PIVOT_V1_SCOPE_2026-04-26.md](../../PIVOT_V1_SCOPE_2026-04-26.md) §7.8 (ImpactReport future shape — v1 narrows).

## Context

ADR-0118 §"Decision" §2 prescribes "Release-level audit gate runs" as
a step in `release_update`. ADR-0144 §Decision §"Placement" prescribes
`compute_similarity` as one of the gate's checks. PIVOT §7.8
specifies a 5-section `ImpactReport` (`ReleaseSummary` +
`PeerDepStatus` + `UserImpactDistribution` + `SimilarityWarning` +
`CompositionCheck`). Three of those 5 sections gate on Phase 24-
deferred substrate:

- **PeerDepStatus** — requires `peer_deps` table (ADR-0114 §5
  defers).
- **UserImpactDistribution** — requires cross-user read (Phase 25
  substrate per ADR-0008 §am1).
- **CompositionCheck** — requires `CompositionalMetaEdge` Core
  subclass (Phase 05a Dropped; deferred).

Phase 24 design log §6 narrows the v1 audit gate to the 2 sections
whose substrate is shipped (`ReleaseSummary` from pending_mutations
data + `SimilarityWarning` from `compute_similarity` Phase 16
surface). This ADR is the gate-side record of that scope.

Phase 24 design log PB-24(b) surfaced a load-bearing correctness
gap: single-pass cross-mg similarity misses pending-vs-pending
duplicates. The gate runs **two `compute_similarity` passes** to
close the gap.

## Decision

A new module `mindsos_admin/audit_gate.py` ships a single entry-
point:

```python
def run(
    admin_session: SessionProtocol,
    *,
    pending_mutations: Sequence[PendingMutationRow],   # PB-26(b) audit-gate-snapshot set
    canonical_global: Mapping[str, Metagraph],         # role → canonical role-graph
    pending_global: Mapping[str, Metagraph],           # role → pending role-graph
) -> AuditGateResult: ...
```

### 1. Two-pass `compute_similarity` (per PB-24(b))

For each role with pending content in the snapshot set:

```python
candidates: list[CandidateRef] = candidates_for_role(pending_mutations, role)

intra_pending = compute_similarity(
    mg=pending_global[role],
    candidates=candidates,
    role=role,
    target_mg=None,                # intra-mg form per Phase 16 PB-K2 + PB-M2
)

cross_mg = compute_similarity(
    mg=pending_global[role],
    candidates=candidates,
    role=role,
    target_mg=canonical_global[role],  # cross-mg form per Phase 16 PB-K2
)
```

**Two passes are not redundant.** Phase 16 `compute_similarity` excludes
self-comparison in intra-mg mode but INCLUDES candidate-vs-candidate
(per Phase 16 PB-M2 — flagged with `Finding.matched_is_candidate=True`).
Cross-mg mode compares candidates → target_mg only; it does NOT
compare candidates to each other. The intra-pending pass catches
"admin proposed the same content twice" duplicates that the cross-mg
pass misses entirely.

`SimilarityWarning` records carry a `source: Literal["intra_pending",
"cross_mg"]` discriminator so admin (and future tooling) can tell
which pass surfaced each finding.

### 2. Blocking-finding handling (per PB-20(c))

`compute_similarity` returns findings classified `"blocking"` (>=0.85)
or `"review"` (0.5-0.85) per ADR-0144 §Heuristic. The audit gate
collects findings from both passes:

- **Any `blocking` finding from either pass:** `AuditGateResult.passed
  = False` + `AuditGateResult.blocking_findings = [...]`. `release_
  update` writes a `FAILED` releases row with `error_class=
  "blocking_similarity_findings"` and raises `BlockingFindingError`.
- **`review` findings:** recorded in `AuditGateResult.review_findings`
  but do not block. v1 admin sees them in the CLI output as a soft
  signal.
- **No findings:** `AuditGateResult.passed = True`. `release_update`
  proceeds to FalkorDB copies.

Force-override (`release_update(..., *, force=True)`) is **v2 per
ADR-0118 §Tradeoffs** ("Override path is v2") and does **not** ship
at P24. Admin's recourse on blocking: amend pending content (remove
or merge the colliding candidate via Phase 25 admin tooling, or
DELETE FROM pending_mutations directly) then rerun release_update.

### 3. `AuditGateResult` shape

```python
@dataclass(frozen=True)
class SimilarityWarning:
    candidate_node_id: str
    matched_node_id: str
    score: float
    classification: Literal["blocking", "review"]
    source: Literal["intra_pending", "cross_mg"]
    matched_is_candidate: bool                       # only meaningful when source == "intra_pending"
    role: str

@dataclass(frozen=True)
class ReleaseSummary:
    mutation_count: int                              # == len(pending_mutations)
    roles_affected: list[str]                        # union of roles in pending_mutations
    proposer_admin_user_ids: list[str]               # distinct proposers across pending_mutations

@dataclass(frozen=True)
class AuditGateResult:
    passed: bool                                     # False iff any blocking_findings
    summary: ReleaseSummary
    blocking_findings: list[SimilarityWarning]       # empty unless passed=False
    review_findings: list[SimilarityWarning]         # informational; never blocks
    # v1 omitted (substrate-gated):
    #   peer_dep_status: PeerDepStatus   — needs peer_deps table
    #   user_impact:     UserImpactDistribution — needs cross-user read
    #   composition:     CompositionCheck — needs CompositionalMetaEdge
```

### 4. v1 omitted ImpactReport sections

PIVOT §7.8 + ADR-0144 §Decision name 5 sections; v1 ships 2. The
other 3 land at their substrate phase:

- **`PeerDepStatus`** — first STRUCTURE phase (peer_deps table from
  ADR-0114 §5 ships there).
- **`UserImpactDistribution`** — Phase 25 alongside cross-user
  read substrate.
- **`CompositionCheck`** — post-Core-CompositionalMetaEdge phase.

When those sections ship, `AuditGateResult` extends additively (new
optional fields with default `None`). No breaking change to the
v1 audit gate contract.

### 5. Idempotency + side-effect freedom

The audit gate is **pure read-only** at v1. It executes inside the
`release_update` lock + `admin_tx` window but does not mutate any
SQLite or FalkorDB state. Re-running with the same inputs returns
the same result. The only side effect is `compute_similarity`'s
internal caching (per Phase 16 `_content_hash` keyed cache) which is
process-local.

This property matters for the FAILED-row contract per ADR-0114 §3:
on blocking, the FAILED row records the attempt + findings without
the gate having committed any state.

## Rationale

- **Two-pass closes a real correctness gap.** PB-24 surfaced that
  cross-mg-only ships duplicate canonical nodes when admin proposes
  identical content twice. The intra-pending pass uses Phase 16's
  shipped intra-mg mode unchanged.
- **`mindsos_admin` is the right home** per ADR-0144 §am1 admin-
  relocation precedent (similarity machinery lives in admin; audit
  gate composes similarity → also admin). `mindsos_server →
  mindsos_admin` is the legitimate composition direction.
- **v1 narrow ships only what has substrate.** Shipping
  PeerDepStatus / UserImpactDistribution / CompositionCheck stubs
  ships dead code that drifts from their respective substrate phase
  designs. Additive extension is structurally safe.
- **`source` discriminator on findings** lets admin (and future
  tooling like quorum-approve) reason about which kind of conflict
  to resolve (delete a pending row vs amend a canonical-collision).
- **`force=True` deferral is intentional** — v2 quorum-approve will
  require it; v1's strict-default + amend-then-retry is the correct
  workflow for admin-curated batches per ADR-0118 §Tradeoffs.

## Consequences

**Good:**

- Single-callsite audit gate; one `run(...)` function; testable in
  isolation.
- Two-pass similarity is one extra `compute_similarity` call at
  release-rare frequency — cost negligible.
- FAILED row + `EVT_RELEASE_FAILED` + admin CLI output give admin
  full forensic visibility on blocking.
- Additive extension path for v2 sections (no breaking change).
- ADR-0009 (freshness-id) fully retires — single similarity
  mechanism, single callsite.

**Tradeoffs:**

- v1 has no peer-dep / user-impact / composition awareness in the
  gate. ATOM admin-direct scope makes this acceptable (no
  cross-layer or compositional content yet). STRUCTURE / PIPELINE
  phases will land the missing checks.
- Admin force-override is missing — v1 admin must amend pending
  content to bypass blocking. v2 will revisit.
- `review` findings are informational only; admin may ignore them.
  Acceptable: review-class is by definition "score not high enough
  to block."
- Two-pass cost is O(candidates²) intra-pending (Phase 16
  candidate-vs-candidate enumeration). Release-rare frequency keeps
  this acceptable; PIVOT §7.9 admin candidate-discovery tooling
  (v2) will bound batch sizes.

**Coordinated changes:**

- `mindsos_admin/audit_gate.py` — new module.
- `mindsos_admin/__init__.py` — exports `run` + `AuditGateResult` +
  `SimilarityWarning` + `ReleaseSummary`.
- `mindsos_admin/exceptions.py` — `BlockingFindingError`.
- `mindsos_server/release.py::release_update` — calls `audit_gate.
  run(...)` after acquiring RELEASE_SHIP_LOCK + audit-gate-snapshot
  set selection.
- ADR-0009 status → Superseded.
- `tests/phase_24/test_release_update_audit_gate_blocking.py` +
  `test_release_update_audit_gate_intra_pending.py` +
  `test_release_update_audit_gate_cross_mg.py`.

## Alternatives considered

1. **Single-pass cross-mg only.** Rejected at PB-24 — ships
   pending-vs-pending duplicate canonical nodes. Real correctness
   gap.
2. **propose_for_promotion runs intra-pending check at propose
   time.** Rejected at PB-24(c) — doubles compute cost at propose
   rate; release-time gate is the established canonical choke point;
   admin sees aggregate conflict picture at release time, not one-
   at-a-time at propose time.
3. **DB UNIQUE constraint on payload_json hash.** Rejected at
   PB-24(d) — catches exact-duplicate retries only; misses near-
   duplicates that differ in metadata but share IRI / properties /
   content.
4. **Ship v1 with `force=True` override.** Rejected per ADR-0118
   §Tradeoffs ("Override path is v2"). Strict-default is the correct
   admin-curation workflow.
5. **Inline the audit gate in `mindsos_server/release.py`.**
   Rejected at PB-9 — admin owns audit machinery per ADR-0144 §am1
   symmetry; separate module is testable in isolation and extends
   cleanly as v2 sections land.
6. **Make the audit gate write its own audit row.** Rejected — the
   gate is pure read-only; `release_update`'s `EVT_RELEASE_SHIPPED`
   / `EVT_RELEASE_FAILED` records the outcome with findings in
   manifest_json. One audit event per release call is the cleaner
   ledger.

## Implementation references

- `mindsos_admin/audit_gate.py` — `run(...) -> AuditGateResult`;
  two-pass `compute_similarity`; finding aggregation;
  `BlockingFindingError` raise on blocking.
- `mindsos_admin/__init__.py` — re-exports.
- `mindsos_admin/exceptions.py` — `BlockingFindingError(blocking_
  findings: list[SimilarityWarning])`.
- `mindsos_server/release.py::release_update` — `audit_gate.run(...)`
  callsite after lock + audit-gate-snapshot selection; on
  `BlockingFindingError`: write FAILED row + emit `EVT_RELEASE_FAILED`
  with `error_class="blocking_similarity_findings"`.
- `tests/phase_24/test_release_update_audit_gate_blocking.py` —
  blocking finding → FAILED row + manifest_json forensic content.
- `tests/phase_24/test_release_update_audit_gate_intra_pending.py` —
  duplicate pending rows → blocking from intra_pending source.
- `tests/phase_24/test_release_update_audit_gate_cross_mg.py` —
  pending vs canonical collision → blocking from cross_mg source.

ADR-0009 status flips Accepted → Superseded at this ship (per
§"Supersedes" header).

ADR moves Proposed → Accepted at Phase 24 ship (this row).
