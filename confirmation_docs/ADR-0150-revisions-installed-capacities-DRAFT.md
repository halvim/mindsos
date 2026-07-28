# ADR-0150 §Revisions — new named role `installed-capacities` — DRAFT (proposed)

§Revisions entry in `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` (the
§am-5 escape clause: a new **named** role requires a §Revisions entry).
Implemented on `feat/skill-local-caps`; pairs with **ADR-0183 §am-5**.

---

### Revision — `installed-capacities` (Local-only named role)

Adds one **named** Local role, `installed-capacities`, the per-user store for
installed-skill Local capability **descriptors** (one dict node per capability:
`name`/`category`/`inputs`/`outputs`, `reactivation_key`, `params`,
`installed_by`). ADR-0183 §am-5 registers capabilities from these descriptors at
boot (metadata-only; function built on first use).

**Why a named role.** One fixed shape (all entries are capability descriptors),
so a single-schema named role fits — unlike the per-instance `dataset:` prefix.
Kept distinct from `learned-parameters` (user-*learned* params) so installed-app
provenance is separate and uninstall/upgrade can target it by role + tag.

**Scope.** **Local-only** (`ensure_global_role_graph` rejects it); auto-ensured on
Local mint/install (added to `_LOCAL_NAMED_ROLES`); persisted/reloaded by the
existing Local persister with no new machinery. Mutable
(`mutable_with_retention`) — descriptors are rewritten on upgrade, removed on
uninstall.

**Closed role-set update.** Named count **15 → 16**; prefixes unchanged
(`alignment:`, `dataset:`). The Phase-13 dispatch sentinel + `_ALL_NAMED_ROLES`
and the ALL_ROLES / dispatch-table count assertions across
`tests/{phase_13,dataset_role,learned_pipelines,phase_50,feat_subminds}` move to
16. Revises §am-9's "named count stays 14/15" to 16.

**Out of scope.** No Global `installed-capacities` form (Local-only at v1). Does
not reopen §am-6's Global-only install-record scope — only the capability
descriptors are Local.
