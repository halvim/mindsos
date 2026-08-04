"""Installed-skills role-graph schema (Phase 50 — SA-1 NET-NEW).

Per ADR-0183 + ADR-0150 §amendment-6 (closed role-set 12 → 13) and
**§amendment-11 (CORE-C2R1)**, which added the Local form.

**Dual-scope.** §am-6 shipped this role Global-only, on the reading that
skill installs are admin-gated Global actions (SKILL_ACQUISITION design
log S3). Under ADR-0205 §8 a Skill is the unit of structural change and
**a user installs one into their own realm**; an admin promotes it to
Global. The Global-only shape made install effectively admin-only —
not through ``CAN_INSTALL_SKILL`` but because every write went to
``scope="global"``, which the ADR-0180 gate guards with
``CAN_WRITE_GLOBAL``. §am-11 adds the Local form; scope now decides
which realm, and the capability decides whether the user may install at
all. The closed role-set count is unchanged (an existing role gains a
scope — the ADR-0150 §am-8 precedent for ``request-patterns``).

**One schema serves both scopes.** Unlike ``learned-parameters``, whose
Local and Global forms differ in mutation discipline, an install record
is an action record in either realm — ``append_only`` is correct for
both, so ``build_installed_skills_schema`` takes no ``scope`` kwarg.

Discipline: ``append_only`` per design log R2-2 — one
``SkillInstallRecord`` action record per install / uninstall / failure
event; current state = the latest record per ``bundle_name``. No
record is ever mutated (avoids a mutable-status discipline exception;
reads like provenance).

Single NodeType (``SkillInstallRecord``); no EdgeTypes in v1.

**Record shape (ADR-0182 first consumer).** The record's ``value`` is a
structured dict (manifest digest, artifact roster, installer outcomes,
completed-step roster on failure) — the first production consumer of
the ADR-0182 ``_value_json`` round-trip. Per ADR-0182 rule 5
(queryability is the writer's obligation), the install driver lifts the
filterable fields flat into node properties: ``bundle_name``,
``bundle_version``, ``status``, ``action``, ``recorded_at``.

**Per-NodeType storage_mode** (ADR-0151 + learned-parameters NPB8-1
precedent): ``SkillInstallRecord.value`` is the large-payload field;
``STORAGE_MODE_FIELDS`` declares it, tier ``inline`` at v1 (trivial
bundles; an oversized roster fails loud at the ADR-0182 rule-4 persist
boundary, which is the correct v1 behavior).

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


# ── Node type ──────────────────────────────────────────────────────────

NODE_SKILL_INSTALL_RECORD = "SkillInstallRecord"

INSTALLED_SKILLS_NODE_TYPES: tuple[str, ...] = (NODE_SKILL_INSTALL_RECORD,)


# ── Edge types ─────────────────────────────────────────────────────────

INSTALLED_SKILLS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (ADR-0183; flat per ADR-0182 rule 5) ──

SKILL_INSTALL_RECORD_PROPS: frozenset[str] = frozenset({
    "bundle_name",
    "bundle_version",
    "bundle_digest",
    "status",
    "action",
    "recorded_at",
    "entry_start_datastate",
    "entry_target_datastate",
    # ADR-0183 §am-4 — first-run Local-bootstrap importer entry point.
    "local_bootstrap_importer",
})

#: ``status`` vocabulary per ADR-0183 (install lifecycle S7/S8/S11):
#: a record's flat ``status`` property carries the bundle state the
#: action produced.
SKILL_INSTALL_STATUSES: frozenset[str] = frozenset({
    "installed",
    "uninstalled",
    "failed",
})

#: ``action`` vocabulary per design log R2-2 (append-only action
#: records): what the record describes.
SKILL_INSTALL_ACTIONS: frozenset[str] = frozenset({
    "install",
    "uninstall",
    "install-failed",
})


# ── Per-NodeType large-payload field declaration (ADR-0151 precedent) ─

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_SKILL_INSTALL_RECORD: frozenset({"value"}),
}


def build_installed_skills_schema(strict: bool = False) -> L2Schema:
    """Construct the installed-skills role Schema (Global + Local).

    Discipline ``append_only`` per ADR-0183 + design log R2-2. No
    ``scope`` kwarg — unlike learned-parameters, both scopes share one
    discipline, so one schema serves the Global form (ADR-0150 §am-6)
    and the Local form (§am-11, CORE-C2R1).

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
    """
    s = L2Schema(mutation_discipline=Discipline.APPEND_ONLY, strict=strict)

    for nt in INSTALLED_SKILLS_NODE_TYPES:
        s.add_node_type(NodeType(nt))

    # No EdgeTypes per ADR-0183.
    return s
