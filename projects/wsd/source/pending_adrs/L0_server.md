# L0 / Server Layer — Updates from WSD Goal-Finalization

**For:** Resuming the L0/Server design chat with goal-finalization decisions loaded.
**Source:** `WSD_GOAL_FINALIZATION_OUTPUT.md` (project root). All items here are PROPOSED — ratification happens in the L0 design chat.

## How to use this file

Paste this file into the L0 design chat as loading context. Then work through:
- **§A** — ADRs to formalize.
- **§B** — schema / code changes to land in `mindsos_server`.
- **§C** — interfaces L0 must expose to other layers.
- **§D** — open sub-questions to resolve before implementation.

---

## §A — Required ADRs

### A.1 — Minimal user UI is v1 critical-path

v1 ships two UI surfaces:

- **End-user UI (Local admin role).** Available to every user for their own Local metagraph:
  - Add to local L2: nodes/edges/graphs (knowledge instances).
  - Add to local L3: nodes/edges/graphs (atomic *and* composed capabilities).
  - Add to local L4: pipelines (paths through the capacity graph).
  - Edit dream priorities (4 kinds: goals, metrics, paths-to-vary, cycle-weight).
  - Audit/decision panels: multi-variant comparison, rationale logging, capacity-gap reports, supersedes/version-history viewer, contradiction queue, dependency-tree views.
- **Admin UI (system-wide).** Superset of end-user UI plus:
  - Cross-user staging review (Local→Global promotion).
  - Capacity-gap admin queue (UC-14).
  - System-level schema changes (DS modification, capacity-edge replacement) — high-friction approval gates per L1's three-phase migration protocol.

### A.2 — Schema-conformance validation for user-added knowledge / capacities

- Every L2/L3 user-add validated against schema before landing in Local metagraph.
- Failed validations route to a quarantine area with admin review path.
- Schemas themselves are admin-only; instances are user-addable.

### A.3 — User-authored atomic capacity Python sandbox

- End-user-authored atomic capacities run in a Python sandbox at the Server layer.
- Resource limits (CPU, memory, wall-clock).
- Restricted import surface (no network, no filesystem outside scoped workspace, no subprocess).
- Typed error containment — capacity exceptions → structured path-execution failures, never backend crashes.
- DataState signature validation at registration via `validate_datastate` and `strict_compatible` (from L3 capacity layer + named-DS-registry from L3-PROPOSAL-2).

### A.4 — Cross-domain admin governance (post-v1)

- Stratify Global metagraph by domain post-v1.
- Each domain has its own admin pool + audit-policy defaults.
- v1 ships single-domain (general-English) Global; v2 introduces domain-stratified Global.

### A.5 — Per-capacity I/O extraction from audit trail (v1 affordance for external LLM comparison)

- Admin can extract a specific capacity's exact input + output for any past execution from the audit trail.
- Used by admin to feed external LLM-comparison tooling.

### A.6 — Standalone capacity / pipeline execution (v1 affordance)

- Admin can run a single capacity on a given input from UI/API in isolation.
- Admin can run a chosen pipeline on dataset inputs without going through the normal task lifecycle (simplified execution mode alongside the full six-phase lifecycle).

### A.7 — Reproducibility infrastructure (v1 affordance)

- Same input + same path + same parameter snapshot → same output.
- Stochastic capacities require fixed-seed support.

### A.8 — Per-user training preferences in L0 server settings

- Per-user opt-in/opt-out for each subsystem.
- Per-user audit-policy override (more-conservative-only direction).

---

## §B — Required schema / code changes in `mindsos_server`

### B.1 — Server endpoints / API surface

Add endpoints (or whatever the chosen API style is):

- `POST /local/l2/{sub-graph}/node` — add knowledge node (instance).
- `POST /local/l2/{sub-graph}/edge` — add knowledge edge.
- `POST /local/l3/capacity/atomic` — register user-authored atomic capacity (signature + Python algorithm).
- `POST /local/l3/capacity/composed` — register user-composed capacity (path).
- `POST /local/l4/pipeline` — register pipeline.
- `POST /local/dream-priorities` — set/update dream priorities.
- `GET  /audit-trail/{execution_id}` — retrieve audit trail.
- `GET  /audit-trail/{execution_id}/capacity/{capacity_id}/io` — extract per-capacity I/O.
- `POST /capacity/{id}/execute` — standalone capacity execution.
- `POST /pipeline/{id}/execute` — standalone pipeline execution.
- `POST /knowledge/{id}/supersede` — supersede a knowledge node.
- `GET  /contradiction-queue` — admin contradiction queue.
- `GET  /capacity-gap-queue` — admin capacity-gap queue.
- `GET  /dream/{cycle_id}/variants` — multi-variant comparison panel data.
- Auth + capability checks on all of the above.

### B.2 — Audit trail storage

- Per-execution audit record carrying: input DS reference, path ID, ordered list of (capacity invocation, input snapshot, output snapshot, parameter snapshot, confidence, replan-divergence, output markers).
- Indexed by execution_id and by capacity_id.
- Retention policy decision (open question — see §D).

### B.3 — User-authored capacity sandbox runtime

- Sandbox process lifecycle.
- Capacity registration validates code parseability + DataState signature compatibility before storage.
- Per-execution: spawn sandboxed runner, marshal input DataState, capture output or typed error, marshal back.
- Resource accounting per user / per capacity.

### B.4 — Schema-validation pipeline

- L2 sub-graph schemas queryable from Server.
- Validation runs on every user-add request.
- Failed validations route to quarantine (storage + admin queue surface).

### B.5 — Per-user training preferences

- L0 settings store: per-subsystem opt-in/opt-out flags, per-user audit-policy overrides.
- ALS pipeline reads these settings before staging signals.

### B.6 — Capability-based authorization

- End-user-as-Local-admin role on own Local metagraph.
- Admin role on Global metagraph + cross-user views.

---

## §C — Interfaces L0 exposes to other layers

- **To L4:** auth context (current user, capabilities) for every task; per-user training-preference reads; audit-trail write API.
- **To L2:** Local-vs-Global write routing based on auth context; supersedes write API; quarantine write API.
- **To L3:** capacity registry write API for atomic + composed registrations; sandbox execution API.
- **To L1:** persistence orchestration — falls through L2's storage which goes to FalkorDB / SQLite per ADR-0121.

---

## §D — Open sub-questions for L0 design chat

1. Concrete UI technology choice (web framework, framework-less, native, etc.).
2. Sandbox technology — subprocess + seccomp / RestrictedPython / WASM / other.
3. Persistent state for user-authored capacities — allowed (scoped to local metagraph only) or not.
4. Code-review / static-analysis step before first execution of user-authored capacities.
5. Audit-trail retention policy — duration, archival rules, GDPR-style deletion path.
6. Quarantine workflow specifics — staging area schema, admin notification mechanism.
7. Decision-precedent retrieval UX (UC-13) — similarity function over admin decisions.
8. Cross-domain governance details (post-v1).

---

**End of L0 updates.**
