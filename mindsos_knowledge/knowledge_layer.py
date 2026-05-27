"""The :class:`KnowledgeLayer` entry point — Phase 14.

Holds the in-memory Global metagraph + a lazy per-user dict of Local
metagraphs. Owns the install/extract hook lifecycle for Locals (ADR-
0042) + the constructor + ``bootstrap()`` lifecycle for Global (ADR-
0042 §amendment-1, Phase 14 PB-7).

Per ADR-0043 (Accepted), KL is in-memory only: zero imports of any
FalkorDB client, persistence module, or file-I/O primitive. The
server (Phase 18+) handles persistence by:

1. Reading Global from FalkorDB → ``Metagraph``.
2. ``kl = KnowledgeLayer(global_metagraph=loaded_global)``.
3. Per logged-in user on warm-restart:
   ``kl.install_local_metagraph(user_id, loaded_local)``.

First-install (admin):

1. ``kl = KnowledgeLayer.bootstrap()`` — creates fresh Global with
   the 6 named role-graphs ensured (alignment pair-graphs are minted
   on demand by Phase 15 importers, not at bootstrap).
2. Server persists Global to FalkorDB.

Per ADR-0138 (Proposed) honoured by Phase 14 PB-6: KL ships **no
write API**. The shipped v3 ``add_local_node`` / ``add_local_edge`` /
``add_local_alignment`` / ``promote`` / ``similarity_report`` methods
are absent. Writes land via L3 capacities in Phase 33-35 through
``KLWriteHandle`` (ADR-0143 Proposed). KL exposes data + read
accessors only.

Per ADR-0139 (Proposed) Phase 36 home: KL ships **no validators** in
Phase 14 (PB-14). Phase 36 introduces ``mindsos_knowledge/validators.py``
NET-NEW; Phase 14's class has the data + lifecycle surface only.

Per Phase 14 PB-12 re-classification: this class is mostly NET-NEW
— no v3 ``KnowledgeLayer`` Python source exists to repackage. The v3
design lives only in ``_source_backup/root/knowledge_layer_design.md``
as a markdown doc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

from mindsos_core import Graph
from mindsos_core.models.identity import IdStrategy, UUID4Strategy
from mindsos_core.models.metagraph import Metagraph

from .bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)

if TYPE_CHECKING:
    from .types import SessionProtocol
    from .write_handle import KLWriteHandle
from .exceptions import AlreadyInstalledError, NotInstalledError


__all__ = ["KnowledgeLayer"]


#: Metagraph name for the Global metagraph created by
#: :meth:`KnowledgeLayer.bootstrap`. Server-loaded Global metagraphs
#: may have any name; bootstrap-fresh Globals use this canonical
#: string. Mirrors v3's `Metagraph(name="global_knowledge")` per the
#: legacy design doc §2.
_GLOBAL_METAGRAPH_NAME: str = "global_knowledge"


def _local_metagraph_name(user_id: str) -> str:
    """Return the canonical Local-metagraph name for ``user_id``.

    Mirrors v3 design doc §2: ``Metagraph(name="local_knowledge:<user_id>")``.
    """
    return f"local_knowledge:{user_id}"


class KnowledgeLayer:
    """L2 entry point: Global + per-user Local metagraphs + read views.

    Per ADR-0061, KL owns one Global Metagraph and a lazy dict of
    Local metagraphs keyed by ``user_id``. Per ADR-0044, ``memories``
    and ``capacity-state`` are Local-scoped; ``ontology``, ``lexicon``,
    ``concepts``, ``promoted-pipelines``, ``task-patterns``,
    ``problem-trace`` are Global-scoped; ``alignment:<a>:<b>`` is
    Global-only at v1 per ADR-0150 §amendment-1.

    **Lifecycle:**

    Construction (Phase 14 PB-7):

    * ``KnowledgeLayer(global_metagraph=loaded)`` — server-startup
      path with pre-loaded Global.
    * ``KnowledgeLayer.bootstrap()`` — first-install path; creates
      fresh Global with 6 named role-graphs ensured.
    * ``KnowledgeLayer()`` (no args) — empty test fixture; Global
      remains ``None`` until set externally.

    Per-user Locals (ADR-0042):

    * ``install_local_metagraph(user_id, mg)`` — server-driven on
      login; ``AlreadyInstalledError`` if a Local for ``user_id``
      already exists.
    * ``extract_local_metagraph(user_id)`` — server-driven on
      logout; ``NotInstalledError`` if no Local was installed.
    * ``local_metagraph(user_id)`` — lazy auto-create on first
      access (test convenience + library-style use); installs an
      empty Local with ``memories`` + ``capacity-state`` ensured.

    **Reads:**

    * ``global_view()`` / ``local_view(user_id)`` return
      :class:`MetagraphView` read-only wrappers.
    * Direct metagraph references via ``global_metagraph()`` /
      ``local_metagraph(user_id)`` for L1 callers (e.g., Phase
      33-35 ``KLWriteHandle`` reaching L1 mutation).
    """

    def __init__(
        self,
        global_metagraph: Optional[Metagraph] = None,
        *,
        id_strategy: IdStrategy = None,  # type: ignore[assignment]
    ) -> None:
        """Construct a KnowledgeLayer.

        Per Phase 14 PB-7 (ADR-0042 §amendment-1): Global is
        constructor-supplied, NOT install-hook-supplied. Locals use
        install/extract hooks per ADR-0042 verbatim.

        Args:
            global_metagraph: Pre-loaded Global :class:`Metagraph`
                (server-startup path). ``None`` for empty-KL test
                fixtures or pre-bootstrap state.
            id_strategy: Default :class:`IdStrategy` for any
                metagraphs minted internally (e.g., lazy Local
                creation in :meth:`local_metagraph`). Phase 14 PB-11
                lock: ``UUID4Strategy()`` default; parameter
                override for deterministic tests. Per ADR-0131.

        Note: Phase 14 PB-12 + PB-2 calibration — the constructor is
        **permissive** about ``global_metagraph``. No name check, no
        role-graph completeness check. The server is responsible for
        passing well-formed metagraphs; KL stores the reference as-is.
        """
        self._global: Optional[Metagraph] = global_metagraph
        self._locals: Dict[str, Metagraph] = {}
        # Phase 14 PB-11 — UUID4Strategy default; lazy local_metagraph
        # uses this for the Local Metagraph's own id_strategy.
        self._id_strategy: IdStrategy = id_strategy or UUID4Strategy()

    # ── construction helpers ─────────────────────────────────────────

    @classmethod
    def bootstrap(
        cls,
        *,
        id_strategy: IdStrategy = None,  # type: ignore[assignment]
    ) -> "KnowledgeLayer":
        """Create a fresh KL with Global ensured for all 6 named roles.

        First-install path. Mints a Global :class:`Metagraph` with
        ``name=_GLOBAL_METAGRAPH_NAME``, calls
        :func:`ensure_global_role_graph` for each role in
        ``_GLOBAL_NAMED_ROLES``. Alignment pair-graphs are NOT
        created at bootstrap; they're minted on demand by Phase 15's
        Alignments importer.

        Per Phase 14 PB-9 calibration: bootstrap auto-ensures
        Global; lazy ``local_metagraph(user_id)`` auto-ensures Local.

        Args:
            id_strategy: Optional :class:`IdStrategy` for the Global
                metagraph (and lazy Local metagraphs minted later).
                Defaults to ``UUID4Strategy()``.

        Returns:
            A :class:`KnowledgeLayer` with Global populated and 0
            Locals.
        """
        strategy = id_strategy or UUID4Strategy()
        global_mg = Metagraph(
            name=_GLOBAL_METAGRAPH_NAME, id_strategy=strategy
        )
        # Auto-ensure 6 Global named roles. Alignment pair-graphs are
        # importer-driven (Phase 15); bootstrap does not enumerate them.
        for role in sorted(_GLOBAL_NAMED_ROLES):
            ensure_global_role_graph(global_mg, role)
        return cls(global_metagraph=global_mg, id_strategy=strategy)

    # ── Global accessors ─────────────────────────────────────────────

    def global_metagraph(self) -> Metagraph:
        """Return the Global :class:`Metagraph` reference.

        Used by Phase 33-35 ``KLWriteHandle`` (ADR-0143 Proposed) to
        reach L1 mutation primitives on the Global graphs. KL itself
        exposes no write methods (ADR-0138 Proposed; Phase 14 PB-6).

        Raises:
            RuntimeError: No Global is installed (construction with
                ``global_metagraph=None`` and no ``bootstrap()`` was
                used). Caller MUST install a Global before reading.
        """
        if self._global is None:
            raise RuntimeError(
                "No Global metagraph installed. Use "
                "KnowledgeLayer.bootstrap() for first-install or "
                "KnowledgeLayer(global_metagraph=...) for server-load."
            )
        return self._global

    def global_view(self) -> "MetagraphView":
        """Return a read-only :class:`MetagraphView` over Global.

        Per ADR-0138 Proposed (Phase 14 PB-6 honoured): read-only
        wrapper; no write methods.

        Raises:
            RuntimeError: no Global installed (see :meth:`global_metagraph`).
        """
        from .metagraph_view import MetagraphView  # local: avoid cycle.

        return MetagraphView(self.global_metagraph())

    # ── Local accessors ──────────────────────────────────────────────

    def local_metagraph(self, user_id: str) -> Metagraph:
        """Return (or lazily create) the Local :class:`Metagraph` for ``user_id``.

        Lazy-create semantics (Phase 14 PB-9 lock):

        * If ``user_id`` already has a Local installed (either via
          this method's prior call or via :meth:`install_local_metagraph`),
          returns the existing reference.
        * Otherwise: creates a fresh :class:`Metagraph` with
          ``name=local_knowledge:<user_id>``, auto-ensures both
          Local-named role-graphs (``memories`` + ``capacity-state``
          per ADR-0044), stores in ``self._locals``, returns.

        Symmetric with :meth:`bootstrap` (Global auto-ensures 6 named
        roles; lazy Local auto-ensures 2 named roles).

        Per Phase 14 PB-12 calibration: lazy access is a library-style
        convenience. In production, the server uses
        :meth:`install_local_metagraph` to install pre-loaded Locals
        from FalkorDB.

        Args:
            user_id: The user identifier (per-user IRI charset per
                ADR-0044 §amendment-1).

        Returns:
            The :class:`Metagraph` for ``user_id``.
        """
        existing = self._locals.get(user_id)
        if existing is not None:
            return existing
        # Lazy mint with auto-ensure of the 2 Local-named role-graphs.
        local_mg = Metagraph(
            name=_local_metagraph_name(user_id),
            id_strategy=self._id_strategy,
        )
        for role in sorted(_LOCAL_NAMED_ROLES):
            ensure_local_role_graph(local_mg, role)
        self._locals[user_id] = local_mg
        return local_mg

    def local_view(self, user_id: str) -> "MetagraphView":
        """Return a read-only :class:`MetagraphView` over the user's Local.

        Triggers lazy-creation per :meth:`local_metagraph` semantics.
        """
        from .metagraph_view import MetagraphView  # local: avoid cycle.

        return MetagraphView(self.local_metagraph(user_id))

    # ── Phase 33 — write-handle entry point (ADR-0143) ───────────────

    def writeable(
        self,
        session: "Optional[SessionProtocol]",
        role: str,
        scope: str,
    ) -> "KLWriteHandle":
        """Return a :class:`KLWriteHandle` for ``(session, role, scope)``.

        Phase 33 ships the entry-point surface so L3 write capacities
        can be registered + invoked through the working invocation
        envelope (ADR-0146); the handle bodies are partially stubbed
        per ADR-0146 §amendment-1 clause 1.

        Routing:

        * ``scope='local'`` — routes to ``session.user_id``'s Local
          :class:`Metagraph`. ``session`` is REQUIRED; ``session=None``
          raises :class:`ValueError` (no user_id to route on; ADR-0080
          bootstrap carve-out does NOT extend to Local).
        * ``scope='global'`` — routes to the shared Global Metagraph.
          ``session=None`` is permitted per ADR-0080 (bootstrap path).

        The handle is *non-mutating* per ADR-0143 §Constraint. Capacity
        code calls ``handle.graph().add_node(...)`` etc. for mutation;
        the handle exposes accessors + validators only.

        Args:
            session: Bearer of capability + user identity, or ``None``
                for the bootstrap path (Global only).
            role: KL role name (e.g., ``"memories"``, ``"problem-trace"``).
                No membership check is enforced here; ``graph()`` will
                fail naturally if the role-graph is absent from the
                target Metagraph.
            scope: ``'local'`` or ``'global'``.

        Returns:
            A fresh :class:`KLWriteHandle` instance.

        Raises:
            ValueError: ``scope`` not in ``{'local', 'global'}``, or
                ``scope='local'`` with ``session is None``.
        """
        from .write_handle import KLWriteHandle  # local: avoid cycle

        if scope == "local":
            if session is None:
                raise ValueError(
                    "KnowledgeLayer.writeable(scope='local') requires a "
                    "session for user_id routing — None permitted only "
                    "for scope='global' per ADR-0080 bootstrap carve-out."
                )
            mg = self.local_metagraph(session.user_id)
        elif scope == "global":
            mg = self.global_metagraph()
        else:
            raise ValueError(
                f"KnowledgeLayer.writeable: scope must be 'local' or "
                f"'global', got {scope!r}"
            )

        # Use ``object.__setattr__`` not needed — KLWriteHandle is a
        # frozen dataclass; pass everything via constructor kwargs.
        return KLWriteHandle(
            role=role,
            scope=scope,  # type: ignore[arg-type]
            session=session,
            _kl=self,
            _metagraph=mg,
        )

    # ── install/extract hooks (ADR-0042) ─────────────────────────────

    def install_local_metagraph(
        self, user_id: str, metagraph: Metagraph
    ) -> None:
        """Install a pre-loaded Local :class:`Metagraph` for ``user_id``.

        Server-driven on user login. Per ADR-0042 §Decision: refuses
        with :class:`AlreadyInstalledError` if a Local is already
        present for ``user_id``.

        Per Phase 14 PB-9 lock: if the passed metagraph is missing
        either of the 2 Local-named role-graphs (``memories``,
        ``capacity-state``), they're auto-ensured before storage.
        This makes the install/lazy-access shapes symmetric.

        Per Phase 14 calibration: permissive about extra content. The
        passed Metagraph may carry additional graphs (e.g., per-user
        alignment pair-graphs once Local alignment is a future
        amendment); KL stores the reference as-is. ADR-0042's
        "exact object" contract is honoured.

        Args:
            user_id: The user identifier.
            metagraph: The pre-loaded Local :class:`Metagraph` to
                install.

        Raises:
            AlreadyInstalledError: a Local for ``user_id`` is already
                installed (caller must :meth:`extract_local_metagraph`
                first).
        """
        if user_id in self._locals:
            raise AlreadyInstalledError(
                f"Local metagraph for user_id {user_id!r} is already "
                f"installed. Extract first before installing a "
                f"replacement (ADR-0042 §Decision)."
            )
        # Phase 14 PB-9 — auto-ensure the 2 Local-named role-graphs if
        # the passed metagraph is missing them. Idempotent: if they
        # already exist (from a server reading them out of FalkorDB),
        # ensure_local_role_graph returns the existing references.
        for role in sorted(_LOCAL_NAMED_ROLES):
            ensure_local_role_graph(metagraph, role)
        self._locals[user_id] = metagraph

    def extract_local_metagraph(self, user_id: str) -> Metagraph:
        """Pop and return the Local :class:`Metagraph` for ``user_id``.

        Server-driven on user logout. Per ADR-0042 §Decision: returns
        the exact object that was installed (or lazy-created); raises
        :class:`NotInstalledError` on miss.

        Per ADR-0042 §Consequences: extract never persists; persistence
        is the server's decision after extract.

        Args:
            user_id: The user identifier.

        Returns:
            The :class:`Metagraph` previously installed (or lazy-
            created) for ``user_id``.

        Raises:
            NotInstalledError: no Local is installed for ``user_id``.
        """
        existing = self._locals.pop(user_id, None)
        if existing is None:
            raise NotInstalledError(
                f"No Local metagraph installed for user_id {user_id!r} "
                f"(ADR-0042 §Decision)."
            )
        return existing

    # ── introspection ────────────────────────────────────────────────

    def has_local(self, user_id: str) -> bool:
        """Return True iff a Local is currently installed for ``user_id``."""
        return user_id in self._locals

    def installed_user_ids(self) -> frozenset[str]:
        """Return the set of user_ids with installed Locals.

        Server uses this to drive extract-all on shutdown.
        """
        return frozenset(self._locals.keys())

    # ── repr ─────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        global_id = (
            self._global.metagraph_id if self._global is not None else None
        )
        return (
            f"KnowledgeLayer(global_metagraph_id={global_id!r}, "
            f"installed_local_count={len(self._locals)})"
        )
