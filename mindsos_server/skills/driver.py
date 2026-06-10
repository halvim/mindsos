"""Skill install / de-install driver (Phase 50 — ADR-0183 §3-§8).

Authorization: ``CAN_INSTALL_SKILL`` / ``CAN_UNINSTALL_SKILL`` gate the
lifecycle; every graph write travels through the ADR-0180
``make_writeable`` gate (which enforces ``CAN_WRITE_GLOBAL`` on Global
writes). ``session=None`` is the ADR-0080 bootstrap carve-out — the
session-less CLI path, same as every other admin CLI verb at v1.

Audit: ``write_audit`` rows when an ``audit_conn`` is supplied (the
driver commits — it owns no wider transaction); provenance split per
design log S6 — audit = who/when, install record = what/state.

Install ordering within a bundle (S7): preflight → L2 content → L3
installer entry points → opaque L4 slots (record-carried; uninterpreted
at v1 per S2) → record + audit. Failure mid-sequence fails loud and
appends a ``failed`` record with the completed-step roster; re-running
the same bundle-version+digest repairs (completed steps no-op, S8).
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from mindsos_capacity.context import make_writeable
from mindsos_server.audit import (
    EVT_SKILL_INSTALL_REJECTED,
    EVT_SKILL_INSTALLED,
    EVT_SKILL_UNINSTALLED,
    write_audit,
)
from mindsos_server.capabilities import CAN_INSTALL_SKILL, CAN_UNINSTALL_SKILL

from .manifest import SkillManifest, parse_manifest
from .preflight import PreflightReport, run_preflight
from .records import (
    SkillRecordView,
    append_record,
    latest_records_by_bundle,
)


class SkillInstallError(Exception):
    """Install failed mid-sequence (a ``failed`` record was appended)."""


class SkillInstallRejectedError(Exception):
    """Preflight or bundle-level idempotency rejected the install."""

    def __init__(self, report: PreflightReport, reasons: List[str]) -> None:
        self.report = report
        self.reasons = reasons
        super().__init__("; ".join(reasons) or "install rejected")


class SkillUninstallRefusedError(Exception):
    """Reverse-dependency check refused the de-install (ADR-0183 §8)."""


@dataclass(frozen=True)
class InstallResult:
    """Driver outcome for a successful (or no-op) install."""

    bundle_name: str
    bundle_version: str
    bundle_digest: str
    no_op: bool
    record: Optional[SkillRecordView]
    l2_written: Tuple[str, ...] = field(default_factory=tuple)
    installers_run: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UninstallResult:
    """Driver outcome for a successful de-install."""

    bundle_name: str
    bundle_version: str
    record: SkillRecordView
    deprecated_node_ids: Tuple[str, ...] = field(default_factory=tuple)


def _now_iso() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _require_capability(session: Any, capability: str, op: str) -> None:
    """ADR-0183 §3 lifecycle gate. ``session=None`` = ADR-0080 carve-out."""
    if session is not None and not session.has(capability):
        raise PermissionError(
            f"{op} requires {capability!r}; session "
            f"{getattr(session, 'session_id', None)!r} lacks it (ADR-0183)."
        )


def _audit(
    audit_conn: Any,
    *,
    session: Any,
    event: str,
    extra: Dict[str, Any],
) -> None:
    if audit_conn is None:
        return
    write_audit(
        audit_conn,
        actor=getattr(session, "user_id", None),
        event=event,
        target=None,
        extra=extra,
    )
    audit_conn.commit()


def _resolve_entry_point(spec: str):
    """``"package.module:function"`` → callable, over release-shipped
    modules only (R2-3; no bundle-path code loading)."""
    module_name, func_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, func_name, None)
    if fn is None or not callable(fn):
        raise SkillInstallError(
            f"installer entry point {spec!r} did not resolve to a callable."
        )
    return fn


def _roster_value(manifest: SkillManifest) -> Dict[str, Any]:
    """The structured record ``value`` (ADR-0182 first consumer)."""
    return {
        "manifest_path": manifest.source_path,
        "l2_iris": [e.iri for e in manifest.l2_content],
        "l3_installers": list(manifest.l3_installers),
        "l3_capacities": list(manifest.l3_capacities),
        "l3_datastates": list(manifest.l3_datastates),
        "l4_slots": dict(manifest.l4_slots),
        "requires_bundles": list(manifest.requires_bundles),
    }


def install_skill(
    manifest_or_path: SkillManifest | str,
    *,
    kl: Any,
    cl: Any,
    session: Any = None,
    audit_conn: Any = None,
    current_phase: Optional[int] = None,
) -> InstallResult:
    """Install a bundle per ADR-0183 §4-§7.

    Raises:
        PermissionError: session lacks ``CAN_INSTALL_SKILL``.
        SkillInstallRejectedError: bundle-level idempotency reject
            (digest mismatch / version change while installed) or
            preflight findings; audited ``EVT_SKILL_INSTALL_REJECTED``.
        SkillInstallError: mid-sequence failure; a ``failed`` record
            with the completed-step roster was appended first.
    """
    _require_capability(session, CAN_INSTALL_SKILL, "install_skill")
    manifest = (
        manifest_or_path
        if isinstance(manifest_or_path, SkillManifest)
        else parse_manifest(manifest_or_path)
    )
    writeable = make_writeable(kl, session)

    def reject(reasons: List[str], report: PreflightReport) -> None:
        _audit(
            audit_conn,
            session=session,
            event=EVT_SKILL_INSTALL_REJECTED,
            extra={
                "bundle_name": manifest.name,
                "bundle_version": manifest.version,
                "bundle_digest": manifest.digest,
                "reasons": reasons,
            },
        )
        raise SkillInstallRejectedError(report, reasons)

    empty_report = PreflightReport(
        bundle_name=manifest.name,
        bundle_version=manifest.version,
        bundle_digest=manifest.digest,
    )

    # ── bundle-level idempotency (S8) ─────────────────────────────────
    prior = latest_records_by_bundle(kl).get(manifest.name)
    if prior is not None:
        if prior.status == "installed":
            if (
                prior.bundle_version == manifest.version
                and prior.bundle_digest == manifest.digest
            ):
                _audit(
                    audit_conn,
                    session=session,
                    event=EVT_SKILL_INSTALLED,
                    extra={
                        "bundle_name": manifest.name,
                        "bundle_version": manifest.version,
                        "bundle_digest": manifest.digest,
                        "no_op": True,
                    },
                )
                return InstallResult(
                    bundle_name=manifest.name,
                    bundle_version=manifest.version,
                    bundle_digest=manifest.digest,
                    no_op=True,
                    record=prior,
                )
            if prior.bundle_version == manifest.version:
                reject(
                    [
                        "digest-mismatch: same name+version with a "
                        "different digest is rejected (S8)."
                    ],
                    empty_report,
                )
            reject(
                [
                    f"version-change: {prior.bundle_version!r} is installed; "
                    "in-place upgrade is a v2 trigger — de-install first (S8)."
                ],
                empty_report,
            )

    # ── preflight (S4: atomic abort) ──────────────────────────────────
    report = run_preflight(
        manifest, kl=kl, cl=cl, current_phase=current_phase
    )
    if not report.ok:
        reject(report.reasons, report)

    # ── execute (S7 ordering; fail loud + failed record) ─────────────
    completed: List[str] = []
    l2_written: List[str] = []
    installers_run: List[str] = []
    try:
        for entry in manifest.l2_content:
            handle = writeable(role=entry.role, scope="global")
            graph = handle.graph()
            existing = graph.nodes.get(entry.iri)
            if existing is not None:
                if (
                    existing.properties.get("installed_by")
                    == manifest.provenance_tag
                ):
                    # Owned by this bundle-version: the failed-run
                    # repair path (S8) or reinstall-after-uninstall —
                    # re-claim by clearing the G1 deprecation marker
                    # (direct system write, retire_version precedent).
                    existing.properties.pop("deprecated_at", None)
                    completed.append(f"l2:{entry.iri}")
                    continue
                raise SkillInstallError(
                    f"l2 node {entry.iri!r} already exists in role "
                    f"{entry.role!r} and is not owned by "
                    f"{manifest.provenance_tag!r} (S8 names the partials)."
                )
            props = dict(entry.properties)
            props["installed_by"] = manifest.provenance_tag
            graph.add_node(
                entry.value,
                entry.node_type,
                properties=props,
                node_id=entry.iri,
            )
            l2_written.append(entry.iri)
            completed.append(f"l2:{entry.iri}")

        for spec in manifest.l3_installers:
            fn = _resolve_entry_point(spec)
            fn(cl)
            installers_run.append(spec)
            completed.append(f"l3:{spec}")

        completed.append("l4:slots-recorded")
    except Exception as e:
        value = _roster_value(manifest)
        value["completed_steps"] = completed
        value["error"] = f"{type(e).__name__}: {e}"
        append_record(
            writeable=writeable,
            kl=kl,
            bundle_name=manifest.name,
            bundle_version=manifest.version,
            bundle_digest=manifest.digest,
            status="failed",
            action="install-failed",
            value=value,
        )
        raise SkillInstallError(
            f"install of {manifest.provenance_tag} failed at step "
            f"{len(completed) + 1}: {e}"
        ) from e

    value = _roster_value(manifest)
    value["completed_steps"] = completed
    record = append_record(
        writeable=writeable,
        kl=kl,
        bundle_name=manifest.name,
        bundle_version=manifest.version,
        bundle_digest=manifest.digest,
        status="installed",
        action="install",
        value=value,
    )
    _audit(
        audit_conn,
        session=session,
        event=EVT_SKILL_INSTALLED,
        extra={
            "bundle_name": manifest.name,
            "bundle_version": manifest.version,
            "bundle_digest": manifest.digest,
        },
    )
    return InstallResult(
        bundle_name=manifest.name,
        bundle_version=manifest.version,
        bundle_digest=manifest.digest,
        no_op=False,
        record=record,
        l2_written=tuple(l2_written),
        installers_run=tuple(installers_run),
    )


def uninstall_skill(
    bundle_name: str,
    *,
    kl: Any,
    session: Any = None,
    audit_conn: Any = None,
) -> UninstallResult:
    """De-install per ADR-0183 §8 (narrow v1 semantics).

    (1) reverse-dependency refuse; (2) deprecate bundle-tagged L2
    content — ``deprecated_at`` stamped via direct system write
    (``retire_version`` precedent; marker-only at v1 per G1);
    (3) append ``uninstalled`` record + ``EVT_SKILL_UNINSTALLED``;
    (4) no in-process deregistration.

    Raises:
        PermissionError: session lacks ``CAN_UNINSTALL_SKILL``.
        SkillUninstallRefusedError: bundle not installed, or another
            installed bundle requires it (audited
            ``EVT_SKILL_INSTALL_REJECTED``).
    """
    _require_capability(session, CAN_UNINSTALL_SKILL, "uninstall_skill")
    writeable = make_writeable(kl, session)

    latest = latest_records_by_bundle(kl)
    target = latest.get(bundle_name)
    if target is None or target.status != "installed":
        raise SkillUninstallRefusedError(
            f"bundle {bundle_name!r} is not installed "
            f"(state: {target.status if target else 'absent'})."
        )

    dependants = [
        view.bundle_name
        for view in latest.values()
        if view.status == "installed"
        and bundle_name in (view.value.get("requires_bundles") or [])
    ]
    if dependants:
        reasons = [
            f"reverse-dependency: installed bundle(s) "
            f"{sorted(dependants)!r} require {bundle_name!r}."
        ]
        _audit(
            audit_conn,
            session=session,
            event=EVT_SKILL_INSTALL_REJECTED,
            extra={
                "bundle_name": bundle_name,
                "bundle_version": target.bundle_version,
                "bundle_digest": target.bundle_digest,
                "reasons": reasons,
            },
        )
        raise SkillUninstallRefusedError(reasons[0])

    # ── deprecate bundle-tagged content (G1: marker-only) ────────────
    tag = f"{bundle_name}@{target.bundle_version}"
    stamp = _now_iso()
    deprecated: List[str] = []
    for g in kl.global_metagraph().graphs.values():
        for node in g.nodes.values():
            if node.properties.get("installed_by") == tag:
                # Direct system write (bypasses the user-prop validator
                # that reserves the key) — retire_version precedent.
                node.properties["deprecated_at"] = stamp
                deprecated.append(node.node_id)

    record = append_record(
        writeable=writeable,
        kl=kl,
        bundle_name=bundle_name,
        bundle_version=target.bundle_version,
        bundle_digest=target.bundle_digest,
        status="uninstalled",
        action="uninstall",
        value={
            "deprecated_node_ids": deprecated,
            "uninstalled_at": stamp,
        },
    )
    _audit(
        audit_conn,
        session=session,
        event=EVT_SKILL_UNINSTALLED,
        extra={
            "bundle_name": bundle_name,
            "bundle_version": target.bundle_version,
            "bundle_digest": target.bundle_digest,
        },
    )
    return UninstallResult(
        bundle_name=bundle_name,
        bundle_version=target.bundle_version,
        record=record,
        deprecated_node_ids=tuple(deprecated),
    )


__all__ = [
    "InstallResult",
    "UninstallResult",
    "SkillInstallError",
    "SkillInstallRejectedError",
    "SkillUninstallRefusedError",
    "install_skill",
    "uninstall_skill",
]
