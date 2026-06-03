"""Phase 43 PR2 — storage_mode field declared per ADR-0151 + ADR-0152 §6.

Per NPB11-4 regression guard: ``LearnedParameter.value`` is the SOLE
Phase 43 NodeType with a ``storage_mode`` large-payload declaration.
Other Phase 43 schemas must NOT export ``STORAGE_MODE_FIELDS``.
"""

from __future__ import annotations

import importlib

from mindsos_knowledge.schemas import learned_parameters


_PHASE_43_NEW_SCHEMA_MODULES = (
    "mindsos_knowledge.schemas.parameter_staging",
    "mindsos_knowledge.schemas.pending_promotions",
    "mindsos_knowledge.schemas.capacity_gaps",
    "mindsos_knowledge.schemas.episodic_memories",
)


def test_learned_parameter_value_declared_as_large_payload() -> None:
    sm = learned_parameters.STORAGE_MODE_FIELDS
    assert sm == {"LearnedParameter": frozenset({"value"})}


def test_learned_parameter_storage_mode_field_in_props() -> None:
    assert "storage_mode" in learned_parameters.LEARNED_PARAMETER_PROPS
    assert "value" in learned_parameters.LEARNED_PARAMETER_PROPS


def test_other_phase_43_schemas_do_not_export_storage_mode_fields() -> None:
    """NPB11-4 regression guard."""
    for mod_name in _PHASE_43_NEW_SCHEMA_MODULES:
        mod = importlib.import_module(mod_name)
        assert not hasattr(mod, "STORAGE_MODE_FIELDS"), (
            f"{mod_name} unexpectedly exports STORAGE_MODE_FIELDS — "
            f"only learned_parameters should per ADR-0151 + ADR-0152 §6"
        )


def test_storage_mode_enum_values() -> None:
    """``storage_mode`` accepts inline / falkor_blob / blob_ref only."""
    from mindsos_knowledge import StorageMode

    assert StorageMode.INLINE.value == "inline"
    assert StorageMode.FALKOR_BLOB.value == "falkor_blob"
    assert StorageMode.BLOB_REF.value == "blob_ref"
    assert len(StorageMode) == 3
