"""L2-private schema vocabulary — ``Discipline``, ``StorageMode``, ``L2Schema``.

Phase 43 (Rail A slot 2) per ADR-0153 §amendment-1 + ADR-0151 §Decision +
ADR-0152 §6. L2-private vocabulary (``Discipline`` + ``StorageMode``
enums) lives here rather than on ``mindsos_core.Schema`` per ADR-0010
import-direction symmetry — L1 stays primitive; L2 owns its own
vocabulary.

``L2Schema(Schema)`` is the L2 subclass; every L2 role-graph schema MUST
construct via ``L2Schema(mutation_discipline=Discipline.X, strict=...)``.
The discipline is required at construction (no backward-compat default
per ADR-0153 §amendment-1 — L2 schemas declare explicitly).

``StorageMode`` is the per-NodeType property declaration vocabulary for
large-payload fields per ADR-0151 §Decision. Phase 43 v1 consumer is
``learned_parameters.LearnedParameter.value`` only per ADR-0152 §6;
``INLINE`` + ``FALKOR_BLOB`` ship, ``BLOB_REF`` reserved for FOL chat
(Chat A R5 D30).
"""

from __future__ import annotations

from enum import Enum

from mindsos_core import Schema


class Discipline(str, Enum):
    """Per-role-graph mutation discipline per ADR-0153 §1.

    Six values; expanded from R0's "5 disciplines" framing by ADR-0153
    §1's ``append_only`` row (added per R0a-4 / S3 — used by
    ``problem-trace``).
    """

    IMMUTABLE_SUCCESSOR = "immutable_successor"
    APPEND_ONLY_WITH_LAZY_INLINE = "append_only_with_lazy_inline"
    MUTABLE_WITH_RETENTION = "mutable_with_retention"
    AUDIT_ONLY_AFTER_SETTLED = "audit_only_after_settled"
    ADMIN_AUTHORED = "admin_authored"
    APPEND_ONLY = "append_only"


class StorageMode(str, Enum):
    """L2 large-payload storage tier per ADR-0151 §Decision.

    Three values: ``INLINE`` (≤ ~4 KB; JSON-encoded property),
    ``FALKOR_BLOB`` (~4 KB to ~1 MB; Falkor BLOB-style property),
    ``BLOB_REF`` (> ~1 MB; v2 only, reserved for FOL chat per
    ADR-0151 §Decision + Chat A R5 D30).
    """

    INLINE = "inline"
    FALKOR_BLOB = "falkor_blob"
    BLOB_REF = "blob_ref"


class L2Schema(Schema):
    """L2 role-graph schema subclass per ADR-0153 §amendment-1.

    Adds ``mutation_discipline: Discipline`` as a required-at-
    construction field. ``mindsos_core.Schema`` stays primitive (no L2
    vocabulary imports) per ADR-0010 import-direction symmetry.

    Existing schemas (Phase 13's 9 builders) migrate from
    ``Schema(strict=...)`` to
    ``L2Schema(mutation_discipline=..., strict=...)`` in Phase 43 PR1
    commit 4 audit.
    """

    def __init__(
        self,
        *,
        mutation_discipline: Discipline,
        strict: bool = False,
    ) -> None:
        super().__init__(strict=strict)
        self.mutation_discipline: Discipline = mutation_discipline
