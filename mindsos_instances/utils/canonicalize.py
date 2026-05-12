"""Canonicalization utility for stable comparison and JSON output.

Phase 06 row §D + P34 B. Two consumers:

1. **set_override-time validation** — equality comparison of old vs
   new override bundles for change detection on mutable instances.
2. **Composite materialise JSON stability (round-7 P63 A)** —
   ``dataclasses.asdict`` on Core objects containing ``Set[...]`` or
   ``FrozenSet[...]`` fields (e.g. ``HyperEdge.nodes``,
   ``MetaHyperEdge.graph_ids``) produces non-deterministic list
   ordering. Wrapping the output through this function gives stable
   JSON across runs and platforms.

Rule (P34 B):
* ``set`` and ``frozenset`` → ``list`` with elements canonicalized
  recursively, then sorted by their JSON-stringified form (stable
  ordering for heterogeneous sets).
* ``dict`` → ``dict`` with keys cast to ``str`` and values
  canonicalized recursively. ``json.dumps(..., sort_keys=True)``
  takes care of key ordering at the serialization boundary.
* ``list`` / ``tuple`` → ``list`` with elements canonicalized
  recursively (insertion order preserved — list/tuple ARE
  ordered).
* Primitives (``str``, ``int``, ``float``, ``bool``, ``None``) pass
  through unchanged.

Output is JSON-safe and deterministic. ``json.dumps(canonicalize(x),
sort_keys=True)`` is the canonical stable serialization.
"""

from __future__ import annotations

import json
from typing import Any


def canonicalize(value: Any) -> Any:
    """Return a canonical, JSON-safe, deterministic form of ``value``.

    Recursive on nested containers. Sets become sorted lists, dicts get
    string keys, lists/tuples preserve insertion order. Combine with
    ``json.dumps(..., sort_keys=True)`` for stable serialized output.
    """
    if isinstance(value, (set, frozenset)):
        # Canonicalize each element first, then sort by its JSON form so
        # heterogeneous sets order stably regardless of element type.
        elems = [canonicalize(v) for v in value]
        return sorted(elems, key=lambda x: json.dumps(x, sort_keys=True, default=str))
    if isinstance(value, dict):
        # Cast keys to str so JSON ordering is well-defined.
        return {str(k): canonicalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonicalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # Fallback: stringify (Phase 06 doesn't expect non-primitive
    # property values, but defensive `str(...)` keeps the canonical
    # form JSON-safe).
    return str(value)
