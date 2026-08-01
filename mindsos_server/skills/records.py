"""``installed-skills`` record read/write (Phase 50 — ADR-0183 §5).

Append-only action records (design log R2-2): one ``SkillInstallRecord``
node per install / uninstall / failure; current state = the latest
record (highest ``seq``) per ``bundle_name``; no record is ever mutated.

The record ``value`` is a structured dict — the first production
consumer of the ADR-0182 ``_value_json`` round-trip. Queryable fields
are lifted flat by this writer per ADR-0182 rule 5: ``bundle_name``,
``bundle_version``, ``bundle_digest``, ``status``, ``action``,
``recorded_at``, ``seq``, and (ADR-0183 §am-1, Slice 2) the optional
runtime-entry props ``entry_start_datastate`` / ``entry_target_datastate``.

All writes travel through the ADR-0180 ``make_writeable`` gate built by
the caller (driver) — this module receives the gate, never a session.

**Dual-scope since CORE-C2R1 (ADR-0150 §amendment-11).** The role shipped
Global-only at §am-6, which made skill install effectively admin-only —
not through ``CAN_INSTALL_SKILL`` but because every write went to
``scope="global"``, which the ADR-0180 gate guards with
``CAN_WRITE_GLOBAL``. Under ADR-0205 §8 a user installs a Skill into
their own realm and an admin promotes it. So:

* **reads union both realms** — ``iter_skill_records`` walks the Global
  role-graph and, when a ``user_id`` is supplied, that user's Local one.
  A Local record for a bundle shadows the Global record of the same
  name (the ``LocalPreferringView`` precedent): the user's own install
  state is what governs for that user.
* **writes take an explicit ``scope``** — ``append_record`` no longer
  hardcodes ``"global"``.

``seq`` is minted across the **unioned** record set, so install order
stays a single sequence for a given principal and activation replays in
that order regardless of which realm each record landed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

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
    entry_start_datastate: Optional[str] = None
    entry_target_datastate: Optional[str] = None
    #: ADR-0183 §am-4 — ``"module:function"`` of a first-run Local-bootstrap
    #: importer (e.g. an arc corpus loader). Resolved + invoked once at boot
    #: by ``boot_brain`` with ``(cl, kl, session)``; None when the bundle
    #: declares no importer.
    local_bootstrap_importer: Optional[str] = None


def _role_graph_in(metagraph: Any):
    """The ``installed-skills`` role-graph of ``metagraph``, or ``None``."""
    if metagraph is None:
        return None
    for g in metagraph.graphs.values():
        if g.role == ROLE_INSTALLED_SKILLS:
            return g
    return None


def _installed_skills_graph(kl: Any):
    """The Global ``installed-skills`` role-graph, or ``None`` pre-bootstrap.

    Retained for the Global-only callers; ``_installed_skills_graphs``
    is the dual-scope form (ADR-0150 §am-11).
    """
    return _role_graph_in(kl.global_metagraph())


def _installed_skills_graphs(kl: Any, user_id: Optional[str] = None):
    """Global first, then ``user_id``'s Local, skipping absent graphs.

    ADR-0150 §am-11. Global-then-Local ordering matters: the caller
    lets a Local record shadow a Global one of the same bundle name, so
    Local must be walked second.

    A Local metagraph that has not been installed for ``user_id`` is not
    an error — a user with no installs of their own simply contributes
    nothing, and the Global roster stands alone.
    """
    graphs = []
    g = _role_graph_in(kl.global_metagraph())
    if g is not None:
        graphs.append(g)
    if user_id and getattr(kl, "has_local", lambda _u: False)(user_id):
        # ``has_local`` first: ``local_metagraph`` LAZILY CREATES, and
        # materialising an empty Local while reading a roster would run
        # ahead of the durable boot that restores one. Reading must
        # never mint state.
        g = _role_graph_in(kl.local_metagraph(user_id))
        if g is not None:
            graphs.append(g)
    return graphs


def iter_skill_records(
    kl: Any, user_id: Optional[str] = None
) -> List[SkillRecordView]:
    """All records, ordered by ``seq`` (install order).

    Unions the Global roster with ``user_id``'s Local one when a user is
    supplied (ADR-0150 §am-11). Omitting ``user_id`` reads the Global
    roster alone, which is the pre-§am-11 behaviour and remains correct
    for admin and system callers.
    """
    nodes = [
        node
        for g in _installed_skills_graphs(kl, user_id)
        for node in g.nodes.values()
    ]
    if not nodes:
        return []
    views: List[SkillRecordView] = []
    for node in nodes:
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
                entry_start_datastate=props.get("entry_start_datastate"),
                entry_target_datastate=props.get("entry_target_datastate"),
                local_bootstrap_importer=props.get("local_bootstrap_importer"),
            )
        )
    views.sort(key=lambda v: v.seq)
    return views


def latest_records_by_bundle(
    kl: Any, user_id: Optional[str] = None
) -> Dict[str, SkillRecordView]:
    """Current state per bundle = the highest-``seq`` record (R2-2).

    With ``user_id`` the Global and Local rosters are unioned first
    (ADR-0150 §am-11), so a user's own install state governs for that
    user while the shared roster stands where they have none.
    """
    latest: Dict[str, SkillRecordView] = {}
    for view in iter_skill_records(kl, user_id):  # seq-ascending
        latest[view.bundle_name] = view
    return latest


def skill_entries(
    kl: Any, user_id: Optional[str] = None
) -> List[Tuple[str, str, str]]:
    """``(bundle_name, entry_start, entry_target)`` for currently-installed
    skills whose latest record declares a runtime entry (ADR-0183 §am-1).

    ``user_id`` unions that user's Local roster (ADR-0150 §am-11)."""
    out: List[Tuple[str, str, str]] = []
    for name, r in latest_records_by_bundle(kl, user_id).items():
        if r.status != "installed":
            continue
        if r.entry_start_datastate and r.entry_target_datastate:
            out.append((name, r.entry_start_datastate, r.entry_target_datastate))
    out.sort()
    return out


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
    scope: str = "global",
    user_id: Optional[str] = None,
    entry_start_datastate: Optional[str] = None,
    entry_target_datastate: Optional[str] = None,
    local_bootstrap_importer: Optional[str] = None,
) -> SkillRecordView:
    """Append one action record through the ADR-0180 gate.

    ``seq`` is minted as ``max(existing) + 1`` over ALL records visible
    to this principal — the Global roster unioned with ``user_id``'s
    Local one (ADR-0150 §am-11) — so install order stays one sequence
    and activation replays in it. The record-walk cost note (R2-2)
    tracks here: flip to a counter only with evidence.

    ``scope`` defaults to ``"local"``: under ADR-0205 §8 a user installs
    a Skill into their own realm, and a Global install is the admin
    promotion path. ``scope="global"`` still requires
    ``CAN_WRITE_GLOBAL`` at the ADR-0180 gate, so the default does not
    widen anyone's write reach — it narrows it.

    ADR-0183 §am-1: when supplied, the runtime-entry props are lifted flat
    (queryable) alongside the other flat fields.
    """
    existing = iter_skill_records(kl, user_id)
    seq = (existing[-1].seq + 1) if existing else 1
    recorded_at = _now_iso()
    handle = writeable(role=ROLE_INSTALLED_SKILLS, scope=scope)
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
    if entry_start_datastate is not None:
        flat["entry_start_datastate"] = entry_start_datastate
    if entry_target_datastate is not None:
        flat["entry_target_datastate"] = entry_target_datastate
    if local_bootstrap_importer is not None:
        flat["local_bootstrap_importer"] = local_bootstrap_importer
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
        entry_start_datastate=entry_start_datastate,
        entry_target_datastate=entry_target_datastate,
        local_bootstrap_importer=local_bootstrap_importer,
    )


__all__ = [
    "SkillRecordView",
    "iter_skill_records",
    "latest_records_by_bundle",
    "skill_entries",
    "append_record",
]
