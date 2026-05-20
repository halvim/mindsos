"""Phase 15a — ImporterProtocol contract tests.

Locks Phase 15a PB-22 (Round 5): every importer self-describes its
target role-graphs via the ``target_roles: tuple[str, ...]``
class/instance attribute, and implements ``run(mg) -> ImportResult``.
"""

from __future__ import annotations

import pytest

from mindsos_admin import (
    DolceImporter,
    FrameNetImporter,
    ImporterProtocol,
    ImportResult,
    OewnImporter,
)


_IMPORTER_CLASSES = (DolceImporter, OewnImporter, FrameNetImporter)


@pytest.mark.parametrize("importer_cls", _IMPORTER_CLASSES)
def test_target_roles_attribute_present(importer_cls: type) -> None:
    """PB-22: every importer class exposes target_roles."""
    assert hasattr(importer_cls, "target_roles")


@pytest.mark.parametrize("importer_cls", _IMPORTER_CLASSES)
def test_target_roles_is_tuple_of_strings(importer_cls: type) -> None:
    """target_roles is a tuple of str (per ImporterProtocol type)."""
    tr = importer_cls.target_roles
    assert isinstance(tr, tuple)
    assert len(tr) > 0
    for role in tr:
        assert isinstance(role, str)
        assert role  # non-empty


@pytest.mark.parametrize("importer_cls,expected_role", [
    (DolceImporter, "ontology"),
    (OewnImporter, "lexicon"),
    (FrameNetImporter, "concepts"),
])
def test_phase_15a_role_mapping(importer_cls: type, expected_role: str) -> None:
    """Phase 15a's 3 importers map 1-1 to the 3 importer-driven Global roles."""
    assert importer_cls.target_roles == (expected_role,)


@pytest.mark.parametrize("importer_cls", _IMPORTER_CLASSES)
def test_run_method_signature_present(importer_cls: type) -> None:
    """Every importer has a callable ``run`` method."""
    assert hasattr(importer_cls, "run")
    assert callable(getattr(importer_cls, "run"))


@pytest.mark.parametrize("importer_cls", _IMPORTER_CLASSES)
def test_satisfies_runtime_checkable_protocol(importer_cls: type) -> None:
    """Instance is a runtime-checkable ImporterProtocol."""
    instance = importer_cls(source=None)
    assert isinstance(instance, ImporterProtocol)


def test_import_result_to_dict_shape() -> None:
    """ImportResult.to_dict() yields the JSON-serialisable shape used by CLI."""
    from datetime import datetime, timezone

    result = ImportResult(
        role="ontology",
        version="4.1",
        source="dolce-dul",
        imported_at=datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc),
        stats={"classes": 5, "edges": 3},
    )
    d = result.to_dict()
    assert d["role"] == "ontology"
    assert d["version"] == "4.1"
    assert d["source"] == "dolce-dul"
    assert d["imported_at"] == "2026-05-19T12:00:00+00:00"
    assert d["stats"] == {"classes": 5, "edges": 3}


def test_import_result_is_frozen() -> None:
    """ImportResult is a frozen dataclass — attempts to mutate raise."""
    from datetime import datetime, timezone
    result = ImportResult(
        role="ontology",
        version="4.1",
        source="dolce-dul",
        imported_at=datetime.now(timezone.utc),
    )
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError
        result.role = "lexicon"  # type: ignore[misc]
