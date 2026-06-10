"""``installed-skills`` record read/write (Phase 50 — ADR-0183 §5).

Append-only action records (design log R2-2): one ``SkillInstallRecord``
node per install / uninstall / failure; current state = the latest
record (highest ``seq``) per ``bundle_name``; no record is ever mutated.

The record ``value`` is a structured dict — the first production
consumer of the ADR-0182 ``_value_json`` round-trip. Queryable fields
are lifted flat by this writer per ADR-0182 rule 5: ``bundle_name``,
``bundle_version``, ``bundle_digest``, ``status``, ``action``,
``recorded_at``, ``seq``.

All writes travel through the ADR-0180 ``make_writeable`` gate built by
the caller (driver) — this module receives the gate, never a session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Mapping, Optional

from mindsos_knowledge import ROLE_INSTALLED_SKILLS
from mindsos_knowledge.schemas.installed_skills import (
    NODE_SKILL_INSTALL_RECORD,
)


def _now_iso() -> str:
    """ISO-8601 UTC millisecond timestamp (Phase 18 PB-35 format)."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


@dataclass(frozen=True)
class SkillRecordView:
    """Read-side projection of one ``SkillInstallRecord`` node."""

    iri: str
    bundle_name: str
    bundle_version: str
    bundle_digest: Optional[str]
    status: str
    action: str
    recorded_at: str
    seq: int
    value: Mapping[str, Any]


def _installed_skills_graph(kl: Any):
    """The Global ``installed-skills`` role-graph, or ``None`` pre-bootstrap."""
    for g in kl.global_metagraph().graphs.values():
        if g.role == ROLE_INSTALLED_SKILLS:
            return g
    return None


def iter_skill_records(kl: Any) -> List[SkillRecordView]:
    """All records, ordered by ``seq`` (global install order)."""
    g = _installed_skills_graph(kl)
    if g is None:
        return []
    views: List[SkillRecordView] = []
    for node in g.nodes.values():
        if node.type_name != NODE_SKILL_INSTALL_RECORD:
            continue
        props = node.properties
        views.append(
            SkillRecordView(
                iri=node.node_id,
                bundle_name=str(props.get("bundle_name")),
                bundle_version=str(props.get("bundle_version")),
                bundle_digest=props.get("bundle_digest"),
                status=str(props.get("status")),
                action=str(props.get("action")),
                recorded_at=str(props.get("recorded_at")),
                seq=int(props.get("seq", 0)),
                value=node.value if isinstance(node.value, dict) else {},
            )
        )
    views.sort(key=lambda v: v.seq)
    return views


def latest_records_by_bundle(kl: Any) -> Dict[str, SkillRecordView]:
    """Current state per bundle = the highest-``seq`` record (R2-2)."""
    latest: Dict[str, SkillRecordView] = {}
    for view in iter_skill_records(kl):  # seq-ascending
        latest[view.bundle_name] = view
    return latest


def append_record(
    *,
    writeable: Callable[..., Any],
    kl: Any,
    bundle_name: str,
    bundle_version: str,
    bundle_digest: Optional[str],
    status: str,
    action: str,
    value: Dict[str, Any],
) -> SkillRecordView:
    """Append one action record through the ADR-0180 gate.

    ``seq`` is minted as ``max(existing) + 1`` over ALL records (global
    install order — activation replays in this order). The record-walk
    cost note (R2-2) tracks here: flip to a counter only with evidence.
    """
    existing = iter_skill_records(kl)
    seq = (existing[-1].seq + 1) if existing else 1
    recorded_at = _now_iso()
    handle = writeable(role=ROLE_INSTALLED_SKILLS, scope="global")
    iri = handle.mint_iri(
        NODE_SKILL_INSTALL_RECORD,
        bundle_name=bundle_name,
        record_id=f"{bundle_version}:{seq}",
    )
    full_value = dict(value)
    full_value["bundle_digest"] = bundle_digest
    flat: Dict[str, Any] = {
        "bundle_name": bundle_name,
        "bundle_version": bundle_version,
        "status": status,
        "action": action,
        "recorded_at": recorded_at,
        "seq": seq,
    }
    if bundle_digest is not None:
        flat["bundle_digest"] = bundle_digest
    handle.graph().add_node(
        full_value,
        NODE_SKILL_INSTALL_RECORD,
        properties=flat,
        node_id=iri,
    )
    return SkillRecordView(
        iri=iri,
        bundle_name=bundle_name,
        bundle_version=bundle_version,
        bundle_digest=bundle_digest,
        status=status,
        action=action,
        recorded_at=recorded_at,
        seq=seq,
        value=full_value,
    )


__all__ = [
    "SkillRecordView",
    "iter_skill_records",
    "latest_records_by_bundle",
    "append_record",
]
