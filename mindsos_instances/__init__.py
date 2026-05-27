"""MindsOS Instances — sibling package for L1 instancing (Phase 06).

Per ADR-0132 (deferred Phase 38 file edit) and Phase 06 row §A. The
package ships eight element-instance subclasses, a per-metagraph
``ElementRegistry``, materialise machinery, a canonicalize utility, and
an idempotent ``attach_registry`` helper that subscribes the registry
to the metagraph's Core-side remove observers (Phase 06 row §F + §C +
round-7 P49 A).

Public surface (Phase 06):

* :class:`ElementInstance` — abstract base.
* :class:`NodeInstance`, :class:`EdgeInstance`, :class:`HyperEdgeInstance`,
  :class:`SubGraphInstance`, :class:`GraphInstance`,
  :class:`MetaEdgeInstance`, :class:`MetaHyperEdgeInstance`,
  :class:`CompositeInstance` — eight concrete subclasses.
* :class:`ElementRegistry` — per-metagraph in-memory registry.
* :func:`attach_registry` — idempotent helper that constructs (or
  returns the existing) :class:`ElementRegistry` for a metagraph.
* Exceptions: :class:`DanglingTemplateError`,
  :class:`CompositeCycleError`,
  :class:`CrossMetagraphCompositeError`,
  :class:`SubGraphInvariantError`,
  :class:`OverrideScopeError`.

Persistence (``InstanceRepository`` / ``InstanceLoader``) and the
``MetagraphLoader.register_attach_handler`` extension point are
deferred to Phases 07 + 08 per Phase 06 row §A (P4 B + P5 B).
"""

from __future__ import annotations

from .exceptions import (
    CompositeCycleError,
    CrossMetagraphCompositeError,
    DanglingTemplateError,
    OverrideScopeError,
    SubGraphInvariantError,
)
from .models import (
    CompositeInstance,
    EdgeInstance,
    ElementInstance,
    GraphInstance,
    HyperEdgeInstance,
    MetaEdgeInstance,
    MetaHyperEdgeInstance,
    NodeInstance,
    SubGraphInstance,
)
from .registry import ElementRegistry, attach_registry
from .utils.canonicalize import canonicalize

#: Phase 06 version string. Doctor self-test asserts parity with
#: ``mindsos_core.__version__`` and ``mindsos_cli.__version__``
#: (round-7 P62 A — new top-level package adds a fourth checked site).
#: Phase 09 bumps to phase09 per cross-package version-string parity.
#: Phase 10 bumps to phase10 (Phase 06 P62 A 3-package parity carry).
#: Phase 11 bumps to phase11 (loader policy + schema migration scanner).
#: Phase 12 bumps to phase12 (L2 Identifiers + role IRIs + REF_TYPES).
#: Phase 13 bumps to phase13 (L2 Schemas — 8 role-graph builders + dispatch).
#: Phase 14 bumps to phase14 (L2 KnowledgeLayer + role-graph bootstrap + MetagraphView).
#: Phase 16 bumps to phase16 (L2 admin similarity surface — NEW
#: mindsos_admin/similarity.py + _content_hash.py + exceptions.py per
#: ADR-0144 §amendment-1 partial §Heuristic Accept; read-only at 16;
#: mutating entry-point defers to Phase 24).
__version__ = "0.0.0+phase34"

__all__ = [
    # exceptions
    "CompositeCycleError",
    "CrossMetagraphCompositeError",
    "DanglingTemplateError",
    "OverrideScopeError",
    "SubGraphInvariantError",
    # models
    "CompositeInstance",
    "EdgeInstance",
    "ElementInstance",
    "GraphInstance",
    "HyperEdgeInstance",
    "MetaEdgeInstance",
    "MetaHyperEdgeInstance",
    "NodeInstance",
    "SubGraphInstance",
    # registry + attach helper
    "ElementRegistry",
    "attach_registry",
    # canonicalize utility
    "canonicalize",
]
