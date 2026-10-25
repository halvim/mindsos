"""The read surface a capacity body gets: only the roles it declared
(``mindsos_llm`` plan I-20, ruling R48).

A capacity declares the L2 roles it reads (``reads_roles``). Both invoke paths
- ``L4Dispatcher.build_context`` and ``CapacityLayer.invoke`` - hand a body
that declared reads a :class:`DeclaredReads` built here, and a body that
declared none gets no read handle at all. Before this, both paths handed every
body the whole :class:`~mindsos_knowledge.knowledge_layer.KnowledgeLayer`, so
which roles a conclusion rested on was a fact about the body's source, not
about anything a run could record.

Placement: L2 owns what a role is, so L2 builds the limit; L3 and L4 reach this
by duck-typing on the ``kl`` they hold (the Phase 28 isolation rule keeps
``mindsos_capacity`` free of ``mindsos_knowledge`` imports).

What the handle is, exactly:

* ``global_view()`` - a :class:`RoleLimitedView` over Global. Every role-taking
  accessor of :class:`~mindsos_knowledge.metagraph_view.MetagraphView` routes
  through ``graphs_by_role``, which refuses an undeclared role, and ``roles()``
  names only declared roles that exist.
* ``read_at_version(iri, version)`` - Global, then the caller's OWN Local; a
  node in an undeclared role raises. ``KnowledgeLayer.read_at_version`` scans
  every installed Local, any user's, which is a body-facing read this handle
  does not pass on.
* ``learned_parameters_snapshot()`` - the ``learned-parameters`` role as
  ``read_learned_parameter_snapshot`` folds it (Local over Global per knob);
  only when that role is declared.

Not claimed: that a body uses only this handle. A body that reaches past its
context into private attributes is beyond what a check outside the body can
see (plan R53).
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Set, Tuple

from .exceptions import KnowledgeError, UnknownRoleError
from .identifiers import ALL_ROLES, DATASET_ROLE_PREFIX, ROLE_LEARNED_PARAMETERS
from .metagraph_view import MetagraphView

_ALIGNMENT_PREFIX = "alignment:"

__all__ = [
    "DeclaredReads",
    "RoleLimitedView",
    "UndeclaredRoleReadError",
    "unknown_roles",
]


class UndeclaredRoleReadError(KnowledgeError):
    """A body read a role its capacity did not declare in ``reads_roles``."""


def _is_role(role: Any) -> bool:
    if not isinstance(role, str) or not role:
        return False
    if role in ALL_ROLES:
        return True
    for prefix in (_ALIGNMENT_PREFIX, DATASET_ROLE_PREFIX):
        if role.startswith(prefix) and len(role) > len(prefix):
            return True
    return False


def unknown_roles(roles: Iterable[Any]) -> Tuple[Any, ...]:
    """The entries of ``roles`` that are not knowledge roles, in order.

    A role is one of the closed named set (``ALL_ROLES``) or carries one of the
    two parametric prefixes (``alignment:``, ``dataset:``). Whether the graph
    exists yet is not asked: a ``dataset:`` role is created per user.
    """
    return tuple(r for r in roles if not _is_role(r))


def _refuse(role: str, declared: frozenset) -> UndeclaredRoleReadError:
    return UndeclaredRoleReadError(
        f"read of role {role!r}, which this capacity did not declare; it "
        f"declares reads_roles={tuple(sorted(declared))!r}. Declare the role "
        f"on the capacity (plan R48)."
    )


class RoleLimitedView(MetagraphView):
    """A :class:`MetagraphView` that answers only for declared roles."""

    __slots__ = ("_declared",)

    def __init__(self, metagraph: Any, declared: frozenset) -> None:
        super().__init__(metagraph)
        object.__setattr__(self, "_declared", frozenset(declared))

    def roles(self) -> Set[str]:
        return super().roles() & self._declared

    def graphs_by_role(self, role: str) -> List[Any]:
        if role not in self._declared:
            raise _refuse(role, self._declared)
        return super().graphs_by_role(role)

    def __repr__(self) -> str:
        return (
            f"RoleLimitedView(metagraph_id={self.metagraph_id!r}, "
            f"declared={tuple(sorted(self._declared))!r})"
        )


class DeclaredReads:
    """The ``kl`` a body that declared reads is handed (``KLHandle``)."""

    __slots__ = ("_kl", "_declared", "_user_id")

    def __init__(self, kl: Any, roles: Iterable[str], *, user_id: Optional[str]) -> None:
        roles = tuple(roles)
        bad = unknown_roles(roles)
        if bad:
            raise UnknownRoleError(
                f"reads_roles names {bad!r}, which are not knowledge roles. "
                f"Valid roles: {sorted(ALL_ROLES)}, or the 'alignment:' and "
                f"'dataset:' prefixed forms."
            )
        self._kl = kl
        self._declared = frozenset(roles)
        self._user_id = user_id or None

    @property
    def declared_roles(self) -> Tuple[str, ...]:
        return tuple(sorted(self._declared))

    @property
    def reads_learned_parameters(self) -> bool:
        return ROLE_LEARNED_PARAMETERS in self._declared

    def global_view(self) -> RoleLimitedView:
        return RoleLimitedView(self._kl.global_metagraph(), self._declared)

    def read_at_version(self, iri: str, version: int) -> Any:
        metagraphs = [self._kl.global_metagraph()]
        if self._user_id and self._kl.has_local(self._user_id):
            metagraphs.append(self._kl.local_metagraph(self._user_id))
        for mg in metagraphs:
            for g in mg.graphs.values():
                node = g.nodes.get(iri)
                if node is None:
                    continue
                if g.role not in self._declared:
                    raise _refuse(g.role, self._declared)
                return node
        return None

    def learned_parameters_snapshot(self) -> Any:
        if not self.reads_learned_parameters:
            raise _refuse(ROLE_LEARNED_PARAMETERS, self._declared)
        from .learned_parameters_snapshot import read_learned_parameter_snapshot

        return read_learned_parameter_snapshot(self._kl, self._user_id or "")

    def __repr__(self) -> str:
        return f"DeclaredReads(declared={self.declared_roles!r}, user_id={self._user_id!r})"
