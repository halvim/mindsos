---
title: Skill-bundle and install-lifecycle contract
status: Accepted
date: 2026-06-10
accepted_date: 2026-06-10
layer: server
related: [0010, 0150, 0151, 0153, 0159, 0180, 0182]
---

# ADR-0183: Skill-bundle and install-lifecycle contract

**Status:** Accepted (Phase 50 / SA-1 — drafted at ship R0 per the
SKILL_ACQUISITION design-log §5 reservation; design settled at
SKILL_ACQUISITION_PROCESS_CHAT closure 2026-06-09)

**Date:** 2026-06-10

**Related:** ADR-0010 (Server imports downward — the install driver is
server-side), ADR-0150 §am-6 (`installed-skills` role-graph; closed set
12 → 13), ADR-0151 (storage tiers), ADR-0153 (`append_only`
discipline), ADR-0159 (capacity registration contract v2 — bundle
bodies are CapacityContext-native), ADR-0180 (`make_writeable` — the
only write gate; installs add no write path), ADR-0182 (node-value
serialization — the install record is its first production consumer).

Design authority: `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md`
(S1–S13 + R2). This ADR fixes the contract durably; the log holds the
option analysis.

## Context

The 2026-05-28 charter framed a skill as "L1+L2+L3+L4+L5 artifacts as
an installable bundle". Probing the shipped system (design log §0.1)
found: nothing bundle-shaped exists; CapacityLayer has no deregister
surface; the closed role-set is runtime-enforced; the only write path
is the ADR-0180 gate; L4 registries are static skeletons. WSD/FOL/
code-skill installations all need one install lifecycle to inherit.

## Decision

### 1. What a bundle is (S1, R1 PB-1)

A **skill bundle** is a versioned **TOML manifest + data files**. Code
(capacity bodies, importers, schemas) arrives via a normal MindsOS
release; the manifest references **installer entry points by import
path**, resolved via `importlib` over release-shipped modules only
(R2-3). No bundle-path code loading exists anywhere. Full-plugin
(bundle-shipped code) is a recorded v2 trigger requiring the L0-5
sandbox first.

### 2. Per-layer slots (S2, R1 PB-2)

| Layer | v1 slot |
|---|---|
| L1 | None. |
| L2 | Role-graph **content** into existing role-graphs + importer invocations. NOT role-graph creation (closed set; ADR-0150). |
| L3 | DataStates + capacities + monitors via installer entry points; CapacityContext-native bodies only (S9 = L3-59(a)); new realm only via a manifest-declared `allow_new_realm`. |
| L4 | **Opaque key-value slots** — named in the manifest, uninterpreted by the v1 driver; WSD defines the real shapes by amendment. |
| L5 | None. Episodes/Memories are runtime products. |

The five-layer charter survives as the manifest's *contract sections*,
not as an artifact list.

### 3. Tier + authorization (S3, S6)

Installs are **Global-only and admin-gated** at v1: `CAN_INSTALL_SKILL`
/ `CAN_UNINSTALL_SKILL` (in `ADMIN_CAPS`), with `CAN_WRITE_GLOBAL`
co-held — every graph write travels through ADR-0180 `make_writeable`;
there is **no install-specific write path**. The manifest schema
carries a per-artifact `tier` field from day one (promotion-loop
forward-compatibility) but the v1 driver accepts `tier = "global"`
only. Audit events: `EVT_SKILL_INSTALLED`, `EVT_SKILL_UNINSTALLED`,
`EVT_SKILL_INSTALL_REJECTED` — payload carries `bundle_name`,
`bundle_version`, `bundle_digest`. Provenance split (L0-23 precedent):
audit row = who/when; install record = what/state.

### 4. Preflight + atomicity (S4)

Install runs a read-only **preflight** over every declared artifact.
Any collision aborts the whole bundle with a structured report +
`EVT_SKILL_INSTALL_REJECTED`: existing capacity/DataState IRI not owned
by a prior version of the same bundle; unknown role; realm conflict
absent `allow_new_realm`; missing `requires_bundles`; unsatisfied
`requires_mindsos_phase`. No merge/rename heuristics. Role-set
expansion is a non-goal: bundles cannot request it.

### 5. Install record (S5, R2-2; ADR-0150 §am-6)

Install state lives in the Global **`installed-skills`** role-graph as
**append-only action records** (`Discipline.APPEND_ONLY`): one
`SkillInstallRecord` per install / uninstall / failure; current state =
latest record per `bundle_name`. The record `value` is a structured
dict (manifest digest, artifact roster, installer outcomes) — the
first production consumer of ADR-0182 `_value_json`. Queryable fields
lifted flat by the writer per ADR-0182 rule 5: `bundle_name`,
`bundle_version`, `status` (`installed` / `uninstalled` / `failed`),
`action`, `recorded_at`. IRI: `installed-skills-<v>:record:
<bundle_name>:<record_id>` (`record_id` = `<bundle_version>:<seq>`).

### 6. Two-stage lifecycle (S7, R1 PB-4)

1. **Install (once, admin):** preflight → L2 content (durable) → L3
   DataStates → L3 capacities → opaque L4 slots → install record +
   audit. Failure mid-sequence fails loud: record `status = "failed"`
   with the completed-step roster; no automatic rollback (idempotent
   re-run repairs, §7).
2. **Activation (every process start):** `apply_installed_skills(cl)` —
   a free function (Phase 44 CR-3/PB-38 precedent) — walks `installed`
   records in install order and re-runs the L3 installer entry points
   (idempotent). Cross-bundle order: install order + `requires_bundles`
   edges; cycles reuse the `kahn_sort` / `BootstrapCycleError` shape.
   v1 caller: a CLI activation flag mirroring `--install-builtins`; a
   server-startup hook lands when a server consumer exists.

### 7. Idempotency (S8)

The builtins triple at two granularities. **Artifact:** all-present →
no-op; partial → error naming the partials — except when re-running the
same bundle-version after a `failed` record, where completed steps
no-op and remaining steps run. **Bundle:** same name+version+digest →
no-op (audited); same name+version, different digest → reject;
higher version → reject (**upgrade is a v2 trigger**; manual path =
de-install + install).

### 8. De-installation (S11, R2-1, Phase 50 G1)

Narrow v1 semantics: (1) **refuse** if any installed bundle's
`requires_bundles` names the target (reverse-dependency check — the
whole v1 safety story; episode/MM references are NOT chased — D'1 pins
versions; dangling capacity IRIs in old episodes are tolerated, v2
trigger); (2) **deprecate** bundle-tagged L2 content (provenance tag:
flat `installed_by = "<bundle>@<version>"` node property) by stamping
`deprecated_at` via direct system write (the `retire_version`
precedent — `deprecated_at` is a reserved key). **Marker-only at v1
(G1):** no node-level read filter exists in shipped read paths;
deprecated content stays visible-but-marked. Node-level
`include_deprecated` filtering = v2 trigger. Hard delete = admin
escalation, v2 trigger (`CAN_HARD_DELETE_ARCHIVED` naming precedent);
(3) append an `uninstalled` record + `EVT_SKILL_UNINSTALLED`;
(4) **no in-process deregistration** — no CapacityLayer.deregister
surface exists; registrations expire at process end and activation
skips uninstalled records.

### 9. Promotion loop (S10)

The runtime promotion loop (`parameter-staging` → `pending-promotions`
→ `learned-parameters`) is a **second producer of the same artifacts**
under this same contract (tiers, audit-event family, provenance shape,
conflict preflight). Its mechanism ships in WSD
(`SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §3/§5).

## Rejected options

- **Full plugin at v1** — arbitrary-code-execution surface with no
  sandbox; zero v1 consumer; WSD ships as a release anyway.
- **SQLite install record** — orphans ADR-0182's slot-1 implementation;
  splits Global state across stores (the split ADR-0182 §Rejected
  rejected for Locals); invisible to KL/audit/mutation discipline.
- **Hard-delete de-install** — breaks D'1 reference-safety for episodes
  pinning bundle content.
- **CapacityLayer.deregister** — new L3 surface for a v1 with zero real
  consumers.

## Consequences

- Phase 50 ships: `installed-skills` schema + bootstrap (ADR-0150
  §am-6), capabilities/audit constants, ADR-0182 implementation,
  manifest parser + preflight + install/de-install driver +
  `apply_installed_skills` + CLI surface, and a trivial reference
  bundle validating install / de-install / provenance / idempotency
  ONLY (no dispatch work — Phase 49 PB-1a is WSD's).
- WSD inherits per `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §5;
  rich L4 slots and the L3-59(b) corpus migration land there.
- v2-trigger ledger (phase-map §3): bundle-shipped code; Local-tier
  installs; in-place upgrade; hard delete; node-level deprecation
  read-filtering; dangling-IRI chasing; rich L4 slots.
