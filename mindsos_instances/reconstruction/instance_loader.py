"""Reconstruct ElementInstance / CompositeInstance from FalkorDB (Phase 08).

Slim-port of the v3 baseline at
``/Layered Intelligence/mindsos_instances/reconstruction/instance_loader.py``
(256 LOC) with the following Phase 08 adaptations per locked picks:

* **Substrate API rewrite** — v3 used ``mg._attach_instance(inst)``
  + ``mg._attach_composite(comp)`` + reads ``mg.element_instances[...]``.
  Halvim Phase 06 substituted :class:`ElementRegistry`:
  ``registry.add(inst)`` and ``registry.get(id)``. This port consumes
  the registry that :func:`mindsos_instances.attach_registry` attached
  to the metagraph.
* **R4-3 A** — ``ReconstructionError`` umbrella dropped; replaced with
  :class:`mindsos_core.exceptions.PersistenceError`.
* **RR-3 A** — Override allow-list validation at load: each rehydrated
  instance's ``overrides`` is re-validated against the Phase 06 P36 A
  per-subclass allow-list (via :func:`validate_overrides`). Offenders
  raise :class:`PersistenceError` with the bad key surfaced.
* **RR-4 B** — Orphan template (``source_id``/``template_id`` missing
  from the metagraph) at load: log WARNING + skip (instead of v3's
  silent ``return None`` swallow). Surfaces as a ``verify`` finding
  bucket for operator awareness.
* **R4-13 B** — :class:`InstanceLoader` is NOT re-exported from
  :mod:`mindsos_instances.__init__`. Deep-import only.

Two-pass design preserved:

* Pass 1 — rehydrate every ElementInstance subclass (NodeInstance /
  EdgeInstance / HyperEdgeInstance / SubGraphInstance / GraphInstance /
  MetaEdgeInstance / MetaHyperEdgeInstance). Use ``__new__`` +
  ``object.__setattr__`` to bypass the registry-driven id-minting in
  the regular ``__init__`` path so the persisted id round-trips
  exactly.
* Pass 2 — rehydrate every CompositeInstance. Members may reference
  element instances (Pass 1 output) OR other composites; the second
  member-resolution sub-pass populates the member list after every
  composite shell has been constructed.

Subscribed via :func:`mindsos_instances.attach_registry`'s after-load
observer extension (Phase 08 row §Modules touched). The observer
fires once after :meth:`mindsos_core.reconstruction.MetagraphLoader.load`
completes its locked R4-1 A read sequence (per-observer exception
isolation per RR-9 A — a failing InstanceLoader does NOT tear down the
core load).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, List, Optional, TYPE_CHECKING

from mindsos_core.exceptions import PersistenceError

from ..models._overrides import validate_overrides
from ..models.element_instance import (
    CompositeInstance,
    CompositeMember,
    EdgeInstance,
    ElementInstance,
    GraphInstance,
    HyperEdgeInstance,
    MetaEdgeInstance,
    MetaHyperEdgeInstance,
    NodeInstance,
    SubGraphInstance,
)

if TYPE_CHECKING:
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence.client import Client

    from ..registry import ElementRegistry

_log = logging.getLogger(__name__)


# ``kind`` (persisted as a top-level property + dual label) → class.
# Maps the Phase 06 P49 B persist scheme back to the subclass.
_KIND_TO_CLASS: Dict[str, type] = {
    "node": NodeInstance,
    "edge": EdgeInstance,
    "hyperedge": HyperEdgeInstance,
    "subgraph": SubGraphInstance,
    "graph": GraphInstance,
    "metaedge": MetaEdgeInstance,
    "metahyperedge": MetaHyperEdgeInstance,
}


class InstanceLoader:
    """Reconstruct mental-model instance artefacts for a metagraph (Phase 08)."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def load_into(self, mg: "Metagraph") -> None:
        """Populate ``mg.element_registry`` with persisted instance state.

        Idempotent on re-call: already-registered ids are skipped (so a
        second fire of the after-load observer does not raise on
        ``ElementRegistry.add``'s duplicate-id guard).

        Args:
            mg: target :class:`Metagraph` with an attached
                :class:`ElementRegistry` (set by
                :func:`mindsos_instances.attach_registry` before the
                load fired).

        Raises:
            PersistenceError: substrate-side corruption surfaces as a
                loud failure (orphan templates log + skip per RR-4 B;
                override allow-list violations raise per RR-3 A).
        """
        registry = getattr(mg, "element_registry", None)
        if registry is None:
            # No registry attached — sibling-package observer wiring
            # was bypassed. Nothing to populate; tester convention is
            # ``mindsos_instances.attach_registry(mg)`` BEFORE the load.
            _log.debug(
                "InstanceLoader.load_into: metagraph %r has no "
                "element_registry; sibling-package observer not "
                "subscribed. Skipping.",
                mg.metagraph_id,
            )
            return

        # ── Pass 1: element instances ──────────────────────────────────
        element_rows = self._fetch_element_instances(mg.metagraph_id)
        for row in element_rows:
            inst = self._rehydrate_element(row, mg, registry)
            if inst is None:
                continue
            if inst.id in registry:
                # Idempotent re-load — second observer fire under the
                # same client. Skip silently.
                continue
            registry.add(inst)

        # ── Pass 2: composite instances (two sub-passes) ───────────────
        comp_rows = self._fetch_composite_instances(mg.metagraph_id)
        # Sub-pass A — construct composite shells (members tuple empty).
        built: Dict[str, CompositeInstance] = {}
        for row in comp_rows:
            comp = _unchecked_composite(
                instance_id=row["id"],
                metagraph_id=mg.metagraph_id,
                bundle_overrides=_strip_override_prefix(row.get("props") or {}),
            )
            built[comp.id] = comp

        # Sub-pass B — resolve members. Order doesn't matter because
        # we've already shelled every composite.
        for row in comp_rows:
            member_ids = self._fetch_composite_members(row["id"])
            members: List[CompositeMember] = []
            for mid in member_ids:
                # Members may reference element instances (Pass 1) or
                # other composites (sub-pass A shells).
                if mid in registry:
                    members.append(registry.get(mid))  # type: ignore[arg-type]
                elif mid in built:
                    members.append(built[mid])
                else:
                    # Substrate corruption — composite references a
                    # missing member. Loud failure per Phase 08 RR-3
                    # spirit (loud > silent on substrate issues).
                    raise PersistenceError(
                        f"CompositeInstance {row['id']!r} references "
                        f"missing member {mid!r} (not in registry, not "
                        f"in built shells)"
                    )
            comp = built[row["id"]]
            comp.members = members  # type: ignore[assignment]
            if comp.id in registry:
                # Idempotent re-load.
                continue
            registry.add(comp)

    # ── private read helpers ───────────────────────────────────────────

    def _fetch_element_instances(
        self, metagraph_id: str
    ) -> List[Dict[str, Any]]:
        """Read every :ElementInstance row for ``metagraph_id`` + members.

        Returns rows shaped:
            {id, kind, source_id, source_graph_id, label, props,
             member_ids, version}

        ``member_ids`` is populated for SubGraphInstance / GraphInstance
        rows (those with attached ``:MEMBER`` rels per Phase 06 persist).
        """
        q = (
            "MATCH (i:ElementInstance {metagraph_id: $mid}) "
            "OPTIONAL MATCH (i)-[:MEMBER]->(n:Node) "
            "WITH i, collect(DISTINCT n.id) AS member_ids "
            "RETURN i.id AS id, i.kind AS kind, i.source_id AS source_id, "
            "       i.source_graph_id AS source_graph_id, "
            "       i.label AS label, i._version AS version, "
            "       properties(i) AS props, member_ids"
        )
        return self._client.run_query(q, {"mid": metagraph_id}).rows

    def _fetch_composite_instances(
        self, metagraph_id: str
    ) -> List[Dict[str, Any]]:
        q = (
            "MATCH (c:CompositeInstance {metagraph_id: $mid}) "
            "RETURN c.id AS id, c.label AS label, c._version AS version, "
            "       properties(c) AS props"
        )
        return self._client.run_query(q, {"mid": metagraph_id}).rows

    def _fetch_composite_members(self, composite_id: str) -> List[str]:
        q = (
            "MATCH (c:CompositeInstance {id: $cid})-[:HAS_MEMBER]->(x) "
            "WHERE x:ElementInstance OR x:CompositeInstance "
            "RETURN x.id AS id"
        )
        return [
            row["id"]
            for row in self._client.run_query(q, {"cid": composite_id}).rows
        ]

    # ── rehydration ────────────────────────────────────────────────────

    def _rehydrate_element(
        self,
        row: Dict[str, Any],
        mg: "Metagraph",
        registry: "ElementRegistry",
    ) -> Optional[ElementInstance]:
        """Construct an ElementInstance subclass from a Cypher row.

        Returns ``None`` for orphan templates (RR-4 B — log + skip).
        Raises :class:`PersistenceError` for override-allow-list
        violations (RR-3 A) or unknown ``kind``.
        """
        kind = row.get("kind")
        cls = _KIND_TO_CLASS.get(kind)
        if cls is None:
            raise PersistenceError(
                f"InstanceLoader: unknown ElementInstance kind {kind!r} "
                f"on row id={row.get('id')!r}"
            )

        source_id = row.get("source_id")
        source_graph_id = row.get("source_graph_id")
        instance_id = row["id"]

        # RR-4 B — orphan template handling. Check resolves per-kind.
        if not _template_resolves(kind, source_id, source_graph_id, mg, row):
            _log.warning(
                "orphan instance %r: template_id=%r missing in "
                "metagraph %r; skipping (RR-4 B)",
                instance_id, source_id, mg.metagraph_id,
            )
            return None

        raw_overrides = _strip_override_prefix(row.get("props") or {})

        # RR-3 A — re-validate the rehydrated override dict against the
        # Phase 06 P36 A per-subclass allow-list. Substrate-side bad
        # keys become loud PersistenceError failures with the offending
        # key surfaced.
        try:
            overrides = validate_overrides(
                raw_overrides,
                kind=cls.KIND,
                structural_keys=cls.STRUCTURAL_KEYS,  # type: ignore[arg-type]
                set_typed_keys=cls.SET_TYPED_KEYS,  # type: ignore[arg-type]
                forbids_type_name=cls.FORBIDS_TYPE_NAME,  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise PersistenceError(
                f"InstanceLoader: override-allow-list violation on "
                f"rehydrated instance {instance_id!r} (kind={kind!r}): "
                f"{exc}"
            ) from exc

        # SubGraphInstance carries `:MEMBER` rels for node-id membership;
        # the persisted node-id list lands as overrides['node_ids']. The
        # validator already coerced list → frozenset under the
        # SET_TYPED_KEYS contract. For graph/subgraph kinds where the
        # member_ids list arrived on the row instead of in the override
        # bag, fold it into the overrides for backwards-compat.
        member_ids = row.get("member_ids") or []
        if (
            kind == "subgraph"
            and member_ids
            and "node_ids" not in overrides
        ):
            overrides["node_ids"] = frozenset(member_ids)

        # Phase 06 ElementInstance __init__ mints the id via
        # ``registry._mint_instance_id`` — we need to bypass that path
        # so the persisted id round-trips. Use __new__ +
        # object.__setattr__ to populate slots directly.
        inst = cls.__new__(cls)
        object.__setattr__(inst, "id", instance_id)
        object.__setattr__(inst, "template_id", source_id)
        object.__setattr__(inst, "metagraph_id", mg.metagraph_id)
        object.__setattr__(inst, "overrides", dict(overrides))
        # Per Phase 06 round-7 P46 C — _instance_seq is the per-template
        # monotonic counter. We can't reliably recover it from the id
        # alone (id-minting is strategy-pluggable); use 0 as a sentinel
        # and advance the registry's counter for the template_id so
        # subsequent fresh instances don't collide with the rehydrated id.
        object.__setattr__(inst, "_instance_seq", 0)
        # Advance registry's counter so future fresh-id mints skip this.
        try:
            _ = registry._next_seq_for(source_id or "")  # type: ignore[attr-defined]
        except Exception:
            pass
        # _version — Phase 07 P11 A field. Default 1; row carries the
        # persisted value.
        version_raw = row.get("version")
        try:
            object.__setattr__(
                inst, "_version", int(version_raw) if version_raw is not None else 1
            )
        except (TypeError, ValueError):
            object.__setattr__(inst, "_version", 1)

        return inst

    # ── helpers (instance-side; no module-level state) ─────────────────


# ── module-level rehydration helpers ───────────────────────────────────────


_CORE_INSTANCE_KEYS: FrozenSet[str] = frozenset({
    "id", "kind", "metagraph_id", "source_id", "source_graph_id",
    "label", "_version", "_props_json",
})


def _strip_override_prefix(props: Dict[str, Any]) -> Dict[str, Any]:
    """Pull back out the ``ov__`` prefix used when persisting overrides.

    Drops Core-reserved keys (id / kind / metagraph_id / source_id /
    source_graph_id / label / _version) before applying the prefix
    strip; everything else with an ``ov__`` prefix becomes a regular
    override key. Anything without the prefix that isn't reserved is
    silently dropped (Phase 07 persist writes ONLY ``ov__``-prefixed
    overrides; non-prefixed non-reserved keys are substrate noise).
    """
    out: Dict[str, Any] = {}
    for k, v in props.items():
        if k in _CORE_INSTANCE_KEYS:
            continue
        if isinstance(k, str) and k.startswith("ov__"):
            out[k[len("ov__"):]] = v
    return out


def _unchecked_composite(
    *,
    instance_id: str,
    metagraph_id: str,
    bundle_overrides: Dict[str, Any],
) -> CompositeInstance:
    """Build a CompositeInstance bypassing the registry-driven __init__.

    Mirrors the v3 ``_unchecked_composite`` pattern but adapted to
    Phase 06 / 07 slot layout (``id``, ``metagraph_id``, ``members``,
    ``bundle_overrides``, ``_instance_seq``, ``_version``).
    Used in the first pass of reconstruction where we stage composites
    and resolve members in a second pass.
    """
    comp = CompositeInstance.__new__(CompositeInstance)
    object.__setattr__(comp, "id", instance_id)
    object.__setattr__(comp, "metagraph_id", metagraph_id)
    object.__setattr__(comp, "members", [])
    object.__setattr__(comp, "bundle_overrides", dict(bundle_overrides))
    object.__setattr__(comp, "_instance_seq", 0)
    object.__setattr__(comp, "_version", 1)
    return comp


def _template_resolves(
    kind: Optional[str],
    source_id: Optional[str],
    source_graph_id: Optional[str],
    mg: "Metagraph",
    row: Dict[str, Any],
) -> bool:
    """Return True iff the persisted template_id can be resolved in ``mg``.

    Per-kind resolution:

    * ``node`` / ``edge`` / ``hyperedge`` — ``source_graph_id`` must be
      a contained graph; ``source_id`` must be a node/edge/hyperedge in
      that graph (best-effort; we accept any matching id).
    * ``subgraph`` / ``graph`` — ``source_graph_id`` (or ``source_id``
      for plain Graph) must be a contained graph.
    * ``metaedge`` — ``source_id`` must be in ``mg.metaedges``.
    * ``metahyperedge`` — ``source_id`` must be in ``mg.metahyperedges``.

    Unknown kinds resolve False (caller treats as orphan).
    """
    if kind in {"node", "edge", "hyperedge"}:
        if source_graph_id is None or source_graph_id not in mg.graphs:
            return False
        g = mg.graphs[source_graph_id]
        if kind == "node":
            return source_id in g.nodes
        if kind == "edge":
            return source_id in g.edges
        return source_id in g.hyperedges
    if kind == "subgraph":
        # SubGraphInstance.template_id IS the source Graph id; field
        # ``source_id`` carries that value in the persist shape.
        # ``source_graph_id`` may be redundant or None.
        return source_id in mg.graphs
    if kind == "graph":
        return source_id in mg.graphs
    if kind == "metaedge":
        return source_id in mg.metaedges
    if kind == "metahyperedge":
        return source_id in mg.metahyperedges
    return False


__all__ = ["InstanceLoader"]
