"""Node-value serialization codec (ADR-0182, Phase 50).

Extends the ADR-0130 ``_props_json`` JSON-encoding pattern to node
``value``. Primitive values (``str | int | float | bool | None``) pass
through unchanged — the persist row carries ``value`` and a NULL
``_value_json`` so existing rows and the loader fast path are untouched
(ADR-0182 rule 1). Structured values (``dict`` / ``list``) JSON-encode
into the node-level ``_value_json`` column with ``value`` NULLed
(rule 2); the loader treats a non-NULL ``_value_json`` as the
discriminator and decodes it back as ``value`` (rule 3). Non-JSON-
encodable values fail loud at the persist boundary with
:class:`PersistenceError` (rule 4).

Queryability (rule 5) is the writer's obligation: a JSON-encoded value
is opaque to Cypher filtering and to the ADR-0181 index strategy; any
field that must be queryable/indexable is lifted by the writer into a
flat primitive node property. This codec does no automatic lifting.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Tuple

from ..exceptions import PersistenceError

#: JSON primitive types passed through on the fast path (rule 1).
#: ``bool`` is listed for clarity even though it subclasses ``int``.
_PRIMITIVE_TYPES = (str, int, float, bool)


def encode_node_value(value: Any) -> Tuple[Any, Optional[str]]:
    """Split ``value`` into the ``(value, _value_json)`` persist pair.

    Returns ``(value, None)`` for JSON primitives (rule 1) and
    ``(None, <canonical JSON>)`` for ``dict`` / ``list`` (rule 2 — the
    same canonical encode discipline as
    ``MetagraphRepository._encode_props_json``: sorted keys, no ASCII
    escaping, compact separators). Any other type, or a dict/list whose
    interior is not JSON-encodable, raises :class:`PersistenceError`
    (rule 4 — fail loud at save, not at load).
    """
    if value is None or isinstance(value, _PRIMITIVE_TYPES):
        return value, None
    if isinstance(value, (dict, list)):
        try:
            return None, json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as e:
            raise PersistenceError(
                f"Node value is not JSON-encodable (ADR-0182 rule 4): {e}"
            ) from e
    raise PersistenceError(
        f"Node value of type {type(value).__name__!r} is neither a JSON "
        "primitive nor dict/list (ADR-0182 rule 4)."
    )


def decode_node_value(raw_value: Any, value_json: Optional[str]) -> Any:
    """Recover the in-memory ``value`` from a loaded row (rule 3).

    Presence of ``value_json`` is the discriminator: decode and return
    it; otherwise pass ``raw_value`` through (the pre-ADR-0182 fast
    path — existing rows never carry ``_value_json``).
    """
    if value_json is None:
        return raw_value
    try:
        return json.loads(value_json)
    except (TypeError, ValueError) as e:
        raise PersistenceError(
            f"Corrupt _value_json column (ADR-0182 rule 3): {e}"
        ) from e


__all__ = ["encode_node_value", "decode_node_value"]
