"""Read-only install preflight (Phase 50 — ADR-0183 §4).

Any finding aborts the whole bundle (atomic-abort; no merge/rename
heuristics). The report is structured so the driver can embed it in
the ``EVT_SKILL_INSTALL_REJECTED`` audit payload and the
``SkillInstallRejectedError``.

Check roster (design log S4): tier; ``requires_mindsos_phase``;
``requires_bundles``; unknown/non-Global role; capacity + DataState IRI
collisions; realm conflicts absent ``allow_new_realm``. Role-set
expansion is a non-goal — a bundle naming an unknown role is rejected,
never accommodated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from mindsos_capacity.identifiers import RESERVED_REALMS
from mindsos_knowledge.bootstrap import _ALIGNMENT_PREFIX, _GLOBAL_NAMED_ROLES

from .manifest import SkillManifest
from .records import iter_skill_records, latest_records_by_bundle

#: ``+phaseNN`` suffix on package ``__version__`` strings (e.g.
#: ``0.0.0+phase50``) — the release-phase source for the
#: ``requires_mindsos_phase`` check.
_PHASE_SUFFIX_RE = re.compile(r"\+phase(\d+)$")


def current_mindsos_phase() -> Optional[int]:
    """Parse the running phase from ``mindsos_server.__version__``."""
    from mindsos_server import __version__

    m = _PHASE_SUFFIX_RE.search(__version__)
    return int(m.group(1)) if m else None


@dataclass(frozen=True)
class PreflightFinding:
    """One rejection reason: stable ``code`` + human ``message``."""

    code: str
    message: str


@dataclass(frozen=True)
class PreflightReport:
    """Structured preflight outcome (ADR-0183 §4)."""

    bundle_name: str
    bundle_version: str
    bundle_digest: str
    findings: Tuple[PreflightFinding, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.findings

    @property
    def reasons(self) -> List[str]:
        return [f"{f.code}: {f.message}" for f in self.findings]


def _datastate_realm(iri: str) -> Optional[str]:
    """Realm of a ``datastate:<realm>.<name>`` IRI, or None if unparseable."""
    if not iri.startswith("datastate:"):
        return None
    name = iri[len("datastate:"):]
    if "." not in name:
        return None
    return name.split(".", 1)[0]


def run_preflight(
    manifest: SkillManifest,
    *,
    kl: Any,
    cl: Any,
    current_phase: Optional[int] = None,
    user_id: Optional[str] = None,
) -> PreflightReport:
    """Scan every declared artifact; collect ALL findings (not fail-fast)
    so the rejection report names the full conflict set.

    ``current_phase`` defaults to :func:`current_mindsos_phase`;
    injectable for tests.

    ``user_id`` unions that user's Local install roster with the Global one
    (ADR-0150 §amendment-11) for both the ``requires_bundles`` check and the
    prior-ownership scan — otherwise a dependency the user installed into
    their own realm reads as missing, and their own prior install of the
    same bundle reads as a foreign conflict.
    """
    findings: List[PreflightFinding] = []

    def reject(code: str, message: str) -> None:
        findings.append(PreflightFinding(code=code, message=message))

    # ── tier (S3: Global-only at v1) ──────────────────────────────────
    for entry in manifest.l2_content:
        if entry.tier != "global":
            reject(
                "tier-not-global",
                f"l2 entry {entry.iri!r} declares tier {entry.tier!r}; "
                "v1 installs are Global-only (Local = v2 trigger).",
            )

    # ── requires_mindsos_phase ────────────────────────────────────────
    if manifest.requires_mindsos_phase is not None:
        phase = (
            current_phase
            if current_phase is not None
            else current_mindsos_phase()
        )
        if phase is not None and phase < manifest.requires_mindsos_phase:
            reject(
                "phase-unsatisfied",
                f"bundle requires phase >= {manifest.requires_mindsos_phase}; "
                f"running phase is {phase}.",
            )

    # ── requires_bundles ──────────────────────────────────────────────
    latest = latest_records_by_bundle(kl, user_id)
    for dep in manifest.requires_bundles:
        view = latest.get(dep)
        if view is None or view.status != "installed":
            reject(
                "missing-required-bundle",
                f"required bundle {dep!r} is not installed "
                f"(state: {view.status if view else 'absent'}).",
            )

    # ── roles (closed set; Global-named or alignment-prefix only) ────
    for entry in manifest.l2_content:
        role_ok = (
            entry.role in _GLOBAL_NAMED_ROLES
            or entry.role.startswith(_ALIGNMENT_PREFIX)
        )
        if not role_ok:
            reject(
                "unknown-or-non-global-role",
                f"l2 entry {entry.iri!r} targets role {entry.role!r}, "
                "which is not a Global-named role (closed set; "
                "ADR-0150 — bundles cannot expand the role-set).",
            )

    # ── L3 IRI collisions (S4: a collision is waived when the IRI is
    #    owned by a prior record of the SAME bundle — the failed-run
    #    repair path, and in-process reinstall after uninstall, where
    #    registrations persist because S11 ships no deregistration) ──
    owned: set[str] = set()
    for view in iter_skill_records(kl, user_id):
        if view.bundle_name == manifest.name:
            owned.update(view.value.get("l3_capacities") or [])
            owned.update(view.value.get("l3_datastates") or [])

    mg = cl.global_metagraph()
    cap_index = cl._capacity_index.get(mg.metagraph_id, {})
    for cap_iri in manifest.l3_capacities:
        if cap_iri in cap_index and cap_iri not in owned:
            reject(
                "capacity-iri-collision",
                f"capacity {cap_iri!r} is already registered and not "
                f"owned by a prior record of bundle {manifest.name!r}.",
            )
    from mindsos_capacity.bootstrap import ensure_datastate_graph

    ds_graph = ensure_datastate_graph(mg, strict=cl._strict)
    for ds_iri in manifest.l3_datastates:
        if ds_iri in ds_graph.nodes and ds_iri not in owned:
            reject(
                "datastate-iri-collision",
                f"DataState {ds_iri!r} is already registered and not "
                f"owned by a prior record of bundle {manifest.name!r}.",
            )

    # ── realms (strict per Phase 40; new only via allow_new_realm) ───
    for ds_iri in manifest.l3_datastates:
        realm = _datastate_realm(ds_iri)
        if realm is None:
            reject(
                "datastate-iri-malformed",
                f"DataState {ds_iri!r} is not 'datastate:<realm>.<name>'.",
            )
        elif realm not in RESERVED_REALMS and realm not in manifest.allow_new_realm:
            reject(
                "realm-conflict",
                f"DataState {ds_iri!r} uses realm {realm!r}, not in the "
                f"reserved set and not declared in [l3].allow_new_realm.",
            )

    return PreflightReport(
        bundle_name=manifest.name,
        bundle_version=manifest.version,
        bundle_digest=manifest.digest,
        findings=tuple(findings),
    )


__all__ = [
    "PreflightFinding",
    "PreflightReport",
    "run_preflight",
    "current_mindsos_phase",
]
