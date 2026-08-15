"""DataState definitions and structural-shape matching.

A ``DataState`` is a named representation shape (§4.1). Its declaration
carries:

- a **name** (the user-visible identifier, also used to build the IRI),
- a **structural shape** (the Python/graph shape used for matching),
- optional **provenance hints** (which functional category typically
  produces it; which L2 roles are typically consulted when moving into
  or out of it).

The design plan is explicit that **semantic richness is not typed** —
DataState descriptors stay purely structural. See §4.2.

Shape matching in this module is deliberately cheap: we compare a
shape's normalised JSON-like description. "Strict match" means the
descriptors are equal; "near match" means they differ only in
adapter-reachable dimensions (handled at the :mod:`.discovery` level).
"""

from __future__ import annotations

import warnings
from dataclasses import InitVar, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .exceptions import DataStateError
from .identifiers import datastate_iri


# ── Shape descriptor ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ShapeDescriptor:
    """Structural description of a DataState's Python-level shape.

    The descriptor is a tiny JSON-like structure so that equality and
    hashing are straightforward.

    Attributes:
        kind: One of ``"scalar"``, ``"list"``, ``"dict"``, ``"record"``,
            ``"graph"``. ``"scalar"`` + ``elem`` is enough for most
            vertical-slice use cases (e.g. ``scalar:str`` for raw text).
        elem: For ``"scalar"`` — the primitive type name
            (``"str"``, ``"int"``, ``"float"``, ``"bool"``).
            For ``"list"`` — the elem descriptor as a frozen dict
            tuple (see :meth:`ShapeDescriptor.normalised`).
        fields: For ``"record"`` — a mapping of field name → elem
            descriptor tuple. Sorted by field name for determinism.
        opaque_tag: Free-form tag that lets two shapes with identical
            kind/elem/fields still be distinguished when semantics
            demand (e.g. ``"text.tokens"`` vs ``"text.pos_tagged_tokens"``
            both list[str] but shouldn't auto-match). Optional.
    """

    kind: str
    elem: Optional[str] = None
    fields: Tuple[Tuple[str, str], ...] = ()  # ((name, elem_kind), ...)
    opaque_tag: Optional[str] = None

    @classmethod
    def scalar(cls, elem: str, *, opaque_tag: Optional[str] = None) -> "ShapeDescriptor":
        return cls(kind="scalar", elem=elem, opaque_tag=opaque_tag)

    @classmethod
    def list_of(cls, elem: str, *, opaque_tag: Optional[str] = None) -> "ShapeDescriptor":
        return cls(kind="list", elem=elem, opaque_tag=opaque_tag)

    @classmethod
    def record(
        cls,
        fields: Mapping[str, str],
        *,
        opaque_tag: Optional[str] = None,
    ) -> "ShapeDescriptor":
        sorted_fields = tuple(sorted(fields.items()))
        return cls(kind="record", fields=sorted_fields, opaque_tag=opaque_tag)

    @classmethod
    def opaque(cls, tag: str) -> "ShapeDescriptor":
        """Anonymous shape identified only by an opaque tag."""
        return cls(kind="opaque", opaque_tag=tag)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": self.kind}
        if self.elem is not None:
            out["elem"] = self.elem
        if self.fields:
            out["fields"] = list(self.fields)
        if self.opaque_tag is not None:
            out["opaque_tag"] = self.opaque_tag
        return out

    def signature(self) -> str:
        """Stable textual signature used by auto-discovery for equality."""
        parts = [self.kind]
        if self.elem is not None:
            parts.append(f"elem={self.elem}")
        if self.fields:
            fs = ",".join(f"{k}:{v}" for k, v in self.fields)
            parts.append(f"fields=({fs})")
        if self.opaque_tag is not None:
            parts.append(f"tag={self.opaque_tag}")
        return "|".join(parts)


# ── DataState declaration ──────────────────────────────────────────────

@dataclass(frozen=True)
class DataState:
    """User-facing declaration of a DataState node.

    When a DataState is registered with a :class:`CapacityLayer`, one
    Core ``Node`` is created in the ``capacity:datastates`` graph of
    the target metagraph. The IRI of that node equals :attr:`iri`.
    """

    name: str
    shape: ShapeDescriptor
    description: str = ""
    provenance_category: Optional[str] = None
    l2_roles: Tuple[str, ...] = ()
    # ADR-0199 (C4) — collection / member typing. ``collection=True`` marks
    # a DataState whose value is a set/list of individually-addressable
    # members; ``member_ds`` is the DS-IRI of the member type L4 iterates
    # into. Collection and member stay distinct DataState types — the finder
    # never bridges them (it already treats them as distinct IRIs); L4
    # owns the unpack loop. Absent (``collection=False``, ``member_ds=None``)
    # = today's behaviour. A single entity that internally holds a set
    # (e.g. a palette) is NOT a collection.
    collection: bool = False
    member_ds: Optional[str] = None
    # ADR-0209 (shape (a)) — member-level in-band refusal. ``True`` marks a
    # DataState whose VALUES may be an in-band refusal (a value that says "this
    # cannot be decided", carrying its origin record per ADR-0208) rather than
    # only a substantive answer. Machinery outcomes stay binary; epistemic
    # outcomes are values in the graph — this flag is how a value type SAYS so,
    # instead of a consumer inferring it from values (the unenforced-convention
    # class twice found insufficient). Deliberately FREE-STANDING: not tied to
    # being some collection's ``member_ds`` (that tie would make registration
    # order-dependent and block a future leaf consumer); the plan-construction
    # decode check (ADR-0209) is the sole consumer today, and a coherence pair
    # rule is added when a second consumer exists, not before.
    refusal_capable: bool = False
    # PB-1 (CR: capacity_mm persist Slice B) — optional brain-supplied value
    # encoder for capacity_mm persistence. A DataStateInstance's runtime value
    # is an arbitrary domain object (a grid, a component set, …) that the
    # ADR-0182 node-value codec rejects unless it is already a primitive /
    # dict / list. ``encode`` reduces such a value to an **inspectable**
    # JSON-native structure (D-C: nested list, structured records — never an
    # opaque blob) at persist time. Core only *dispatches* on it (see
    # ``mindsos_intelligence/capacity_persister.py``); the encoders themselves
    # are brain-owned follow-up. ``None`` (default A) = require the value be
    # primitive/dict/list already, else ``PersistenceError`` at persist. Not
    # emitted by :meth:`to_properties` — it is live brain code, not node data,
    # and never rides into the Core DataState node. Excluded from eq/hash: a
    # DataState's identity is its structural declaration, not which function
    # object happens to encode it (two otherwise-identical declarations must
    # stay equal even with distinct encoder objects).
    encode: Optional[Callable[[Any], Any]] = field(
        default=None, compare=False, repr=False
    )
    # DEPRECATED constructor alias (transition window, ADR-0199 am-1). Accepts
    # ``DataState(group=...)`` from not-yet-migrated consumers (e.g. arc3),
    # emits a DeprecationWarning, and folds the value into ``collection``.
    # InitVar: consumed at construction, NOT stored — ``ds.group`` does not
    # exist (reads must use ``ds.collection``). Drop once consumers migrate.
    group: InitVar[Optional[bool]] = None

    def __post_init__(self, group: Optional[bool]) -> None:
        if group is not None:
            warnings.warn(
                "DataState(group=...) is deprecated (ADR-0199 am-1); "
                "use collection= instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            if group and not self.collection:
                # frozen dataclass — bypass the immutability guard.
                object.__setattr__(self, "collection", True)

    @property
    def iri(self) -> str:
        return datastate_iri(self.name)

    def to_properties(self) -> Dict[str, Any]:
        """Build the property dict used when creating the Core node."""
        props: Dict[str, Any] = {
            "name": self.name,
            "shape_kind": self.shape.kind,
        }
        if self.description:
            props["description"] = self.description
        if self.provenance_category is not None:
            props["provenance_category"] = self.provenance_category
        if self.l2_roles:
            props["l2_roles"] = list(self.l2_roles)
        # Encode shape sub-fields onto the node as auxiliary keys so the
        # Core node is inspectable without rehydrating a descriptor.
        if self.shape.elem is not None:
            props["shape_elem"] = self.shape.elem
        if self.shape.opaque_tag is not None:
            props["shape_opaque_tag"] = self.shape.opaque_tag
        if self.shape.fields:
            props["shape_fields"] = [f"{k}:{v}" for k, v in self.shape.fields]
        # ADR-0199 (C4) — collection / member typing, emitted for inspectability.
        if self.collection:
            props["collection"] = True
        if self.member_ds is not None:
            props["member_ds"] = self.member_ds
        # ADR-0209 — emitted for inspectability, and because the
        # plan-construction decode check reads it off the registered NODE via
        # the scope-correct views (a declaration object is not retrievable at
        # that site; the node is).
        if self.refusal_capable:
            props["refusal_capable"] = True
        return props


def validate_datastate(ds: DataState) -> None:
    """Check vertical-slice invariants on a DataState declaration."""
    if not isinstance(ds, DataState):
        raise DataStateError(f"Expected DataState, got {type(ds).__name__}")
    if not ds.name:
        raise DataStateError("DataState must have a non-empty name")
    if not isinstance(ds.shape, ShapeDescriptor):
        raise DataStateError("DataState.shape must be a ShapeDescriptor")
    if ds.shape.kind not in {"scalar", "list", "record", "opaque", "graph", "dict"}:
        raise DataStateError(
            f"DataState {ds.name!r}: unknown shape kind {ds.shape.kind!r}"
        )
    # ADR-0199 (C4) — collection / member coherence. ``collection`` and
    # ``member_ds`` travel together: a collection must name its member type;
    # a non-collection must not carry one. Member-IRI *existence* is NOT
    # validated at v1 (no consumer requires it; the pointer is advisory
    # metadata L4 reads). DataStates may register in any order, so an
    # existence check would need a seal-time pass — deferred until a
    # consumer needs it.
    if ds.collection and not ds.member_ds:
        raise DataStateError(
            f"DataState {ds.name!r}: collection=True requires a member_ds IRI"
        )
    if not ds.collection and ds.member_ds is not None:
        raise DataStateError(
            f"DataState {ds.name!r}: member_ds is set but collection=False"
        )
    # PB-1 — an ``encode`` hint, when present, must be callable (core
    # dispatches on it at persist; a non-callable would fail obscurely there).
    if ds.encode is not None and not callable(ds.encode):
        raise DataStateError(
            f"DataState {ds.name!r}: encode must be callable or None, "
            f"got {type(ds.encode).__name__}"
        )


# ── Compatibility primitives ───────────────────────────────────────────

def strict_compatible(a: ShapeDescriptor, b: ShapeDescriptor) -> bool:
    """Return ``True`` iff ``a`` and ``b`` are identical shapes."""
    return a.signature() == b.signature()


def list_of_compat(a: ShapeDescriptor, b: ShapeDescriptor) -> bool:
    """Return ``True`` iff ``a`` is ``list[T]`` and ``b`` is ``scalar:T``.

    Used as a simple near-compatibility heuristic: a pipeline stage
    producing ``list[str]`` can feed a stage expecting ``str`` if an
    adapter flattens or iterates. The heuristic is cheap enough to
    always run during discovery.
    """
    return (
        a.kind == "list"
        and b.kind == "scalar"
        and a.elem == b.elem
        and a.opaque_tag == b.opaque_tag
    )


__all__ = [
    "ShapeDescriptor",
    "DataState",
    "validate_datastate",
    "strict_compatible",
    "list_of_compat",
]
