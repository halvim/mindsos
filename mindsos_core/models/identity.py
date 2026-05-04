"""UUID generation and the per-scope identity registry.

Every ``Node``, ``Edge``, ``HyperEdge``, ``Graph``, ``Metagraph``, and
``ElementInstance`` receives an id at construction time. By default an
``IdentityRegistry`` ensures the same id cannot be registered twice
within a single scope (typically a ``Metagraph`` or a standalone
``Graph``).

ADR-0131 introduces a pluggable ``IdStrategy`` Protocol so a
``Metagraph`` can opt into a non-default id-minting strategy
(content-addressable for deterministic tests, IRI-passthrough for
KL importers, etc.). The default ``UUID4Strategy`` preserves the
historical behaviour.

ADR-0035 (Accepted): Core keeps UUID4 by default. Determinism is
delegated to higher layers that own the content (the Knowledge Layer
mints stable IRIs from source content where possible). Core itself
treats ``node_id`` as opaque — it does not parse IRIs. IRI parsing
lives in ``mindsos_knowledge`` (L2) and ships in Phase 12.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional, Protocol, Set, runtime_checkable
from uuid import uuid4

from ..exceptions import IdentityError


def generate_uuid() -> str:
    """Return a fresh UUID4 as a lowercase string."""
    return str(uuid4())


# ── ADR-0131 — pluggable IdStrategy ─────────────────────────────────────────


@runtime_checkable
class IdStrategy(Protocol):
    """Strategy for minting new node/edge/hyperedge ids inside a Metagraph.

    Implementations control how a fresh id is generated when the caller
    didn't supply one explicitly. The default ``UUID4Strategy`` ignores
    content; ``UUID5FromContentStrategy`` derives a deterministic id
    from canonical content; ``IRIPassthroughStrategy`` lets the caller
    supply an IRI under the ``"iri"`` content key.
    """

    def generate(self, kind: str, content: Optional[Dict[str, Any]] = None) -> str:
        """Mint a new id.

        Args:
            kind: One of ``"node"``, ``"edge"``, ``"hyperedge"``,
                ``"graph"``, ``"metaedge"``, ``"metahyperedge"``,
                ``"instance"``, ``"composite"``.
            content: Canonical content for content-addressable strategies;
                ``None`` for strategies that ignore content (e.g. UUID4).
        """
        ...


class UUID4Strategy:
    """Default strategy — non-deterministic UUID4 per call.

    Matches the historical behaviour. Content is ignored.
    """

    def generate(self, kind: str, content: Optional[Dict[str, Any]] = None) -> str:
        return str(uuid.uuid4())


# Stable namespace for content-addressable UUID5 generation.
# Generated once and committed; never regenerate (would invalidate every
# existing UUID5-derived id).
NAMESPACE_MINDSOS = uuid.UUID("a4b3f1d2-c8e6-4f7a-9b3d-2e1c4f5a6b7c")


class UUID5FromContentStrategy:
    """Deterministic UUID5 derived from canonical content.

    Same content + same namespace + same kind → same UUID. Useful for
    tests, idempotent derivations, and content-addressable nodes.

    .. warning::

       Content-addressable IDs change with content. Pivot's auto-upgrade
       contract (``docs/concepts/references.md``) requires id stability
       across mutation, so this strategy is **not** the right choice for
       a Metagraph whose nodes will be auto-upgraded under release. Use
       only for derivation outputs and test fixtures.
    """

    def __init__(self, namespace: uuid.UUID = NAMESPACE_MINDSOS) -> None:
        self.namespace = namespace

    def generate(self, kind: str, content: Optional[Dict[str, Any]] = None) -> str:
        if content is None:
            raise IdentityError(
                f"UUID5FromContentStrategy requires non-None content for kind={kind!r}"
            )
        canonical = json.dumps(
            {"kind": kind, "content": content},
            sort_keys=True,
            default=str,
        )
        return str(uuid.uuid5(self.namespace, canonical))


class IRIPassthroughStrategy:
    """Wrapper strategy — uses ``content["iri"]`` directly when supplied.

    Otherwise delegates to a fallback strategy. Useful for KL importers
    that mint stable IRIs (``oewn-2024:synset:02086723-n``) and want them
    used directly as node ids without ad-hoc handling.
    """

    def __init__(self, fallback: Optional[IdStrategy] = None) -> None:
        self.fallback: IdStrategy = fallback or UUID4Strategy()

    def generate(self, kind: str, content: Optional[Dict[str, Any]] = None) -> str:
        if content and "iri" in content:
            iri = content["iri"]
            if not isinstance(iri, str) or not iri:
                raise IdentityError(
                    f"IRIPassthroughStrategy: content['iri'] must be a "
                    f"non-empty string, got {iri!r}"
                )
            return iri
        return self.fallback.generate(kind, content)


class IdentityRegistry:
    """Guard against id collisions within an identity scope.

    Scopes are usually per-metagraph: the metagraph's registry is shared
    by every contained graph and by every element-instance, so no two
    objects anywhere in the metagraph can share an id.
    """

    __slots__ = ("_ids",)

    def __init__(self) -> None:
        self._ids: Set[str] = set()

    # ── read ──────────────────────────────────────────────────────────────

    def contains(self, uid: str) -> bool:
        """True iff ``uid`` is currently registered."""
        return uid in self._ids

    def __contains__(self, uid: object) -> bool:
        return isinstance(uid, str) and uid in self._ids

    def __len__(self) -> int:
        return len(self._ids)

    @property
    def ids(self) -> Set[str]:
        """Defensive copy of the currently registered id set."""
        return set(self._ids)

    # ── write ─────────────────────────────────────────────────────────────

    def register(self, uid: str) -> None:
        """Register a fresh id. Raises :class:`IdentityError` on duplicate."""
        if uid in self._ids:
            raise IdentityError(f"Duplicate id: {uid!r}")
        self._ids.add(uid)

    def unregister(self, uid: str) -> None:
        """Remove an id from the registry. No-op if not present."""
        self._ids.discard(uid)

    def replace(self, old_id: str, new_id: str) -> None:
        """Atomically swap ``old_id`` for ``new_id``.

        Used by reconstruction code to restore the original DB id after
        a ``_restore_*`` factory would otherwise have assigned a fresh UUID.
        The swap is atomic: if ``new_id`` is already registered (and is
        different from ``old_id``), nothing changes and
        :class:`IdentityError` is raised.
        """
        if old_id == new_id:
            return
        if new_id in self._ids:
            raise IdentityError(
                f"Cannot replace {old_id!r} with {new_id!r}: "
                f"{new_id!r} is already registered."
            )
        self._ids.discard(old_id)
        self._ids.add(new_id)

    def clear(self) -> None:
        """Remove every id. Primarily for tests."""
        self._ids.clear()
