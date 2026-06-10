"""Skill-bundle TOML manifest (Phase 50 — ADR-0183 §1-§2).

A bundle = versioned TOML manifest + data; code arrives via normal
release (design log S1/PB-1). The manifest references installer entry
points by import path (``"package.module:function"``), resolved over
release-shipped modules only (R2-3).

Digest discipline: ``bundle_digest`` = SHA-256 hex over the manifest
file bytes. v1 bundles carry content inline in the manifest (the
reference bundle has no sidecar data files); a sidecar-file digest
roster is added by amendment when a bundle first needs one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


class ManifestError(Exception):
    """Manifest unreadable or shape-invalid (fail before preflight)."""


@dataclass(frozen=True)
class L2ContentEntry:
    """One L2 content node declared by the bundle (ADR-0183 §2 L2 slot)."""

    role: str
    tier: str
    node_type: str
    iri: str
    value: Any
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.properties, MappingProxyType):
            object.__setattr__(
                self, "properties", MappingProxyType(dict(self.properties))
            )


@dataclass(frozen=True)
class SkillManifest:
    """Parsed, digest-stamped bundle manifest (ADR-0183 §1-§2)."""

    name: str
    version: str
    requires_mindsos_phase: int | None
    requires_bundles: Tuple[str, ...]
    l2_content: Tuple[L2ContentEntry, ...]
    l3_installers: Tuple[str, ...]
    l3_capacities: Tuple[str, ...]
    l3_datastates: Tuple[str, ...]
    allow_new_realm: Tuple[str, ...]
    l4_slots: Mapping[str, Any]
    digest: str
    source_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.l4_slots, MappingProxyType):
            object.__setattr__(
                self, "l4_slots", MappingProxyType(dict(self.l4_slots))
            )

    @property
    def provenance_tag(self) -> str:
        """The flat ``installed_by`` value stamped on bundle-written
        L2 nodes (ADR-0183 §8)."""
        return f"{self.name}@{self.version}"


def _require(table: Mapping[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in table:
        raise ManifestError(f"manifest {where} missing required key {key!r}")
    value = table[key]
    if not isinstance(value, kind):
        raise ManifestError(
            f"manifest {where}.{key} must be {kind.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _str_tuple(raw: Any, where: str) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ManifestError(f"manifest {where} must be a list of strings")
    return tuple(raw)


def parse_manifest(path: str | Path) -> SkillManifest:
    """Parse + digest a bundle ``manifest.toml``.

    Raises:
        ManifestError: unreadable file, TOML syntax error, or shape
            violation (missing/odd-typed keys, malformed entry point,
            non-table content entry).
    """
    p = Path(path)
    try:
        raw_bytes = p.read_bytes()
    except OSError as e:
        raise ManifestError(f"cannot read manifest {p}: {e}") from e
    try:
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise ManifestError(f"manifest {p} is not valid TOML: {e}") from e

    bundle = data.get("bundle")
    if not isinstance(bundle, dict):
        raise ManifestError(f"manifest {p} missing [bundle] table")
    name = _require(bundle, "name", str, "[bundle]")
    version = _require(bundle, "version", str, "[bundle]")
    phase_req = bundle.get("requires_mindsos_phase")
    if phase_req is not None and not isinstance(phase_req, int):
        raise ManifestError(
            "[bundle].requires_mindsos_phase must be an integer"
        )
    requires_bundles = _str_tuple(
        bundle.get("requires_bundles"), "[bundle].requires_bundles"
    )

    l2_table = data.get("l2") or {}
    entries: list[L2ContentEntry] = []
    for i, raw_entry in enumerate(l2_table.get("content") or []):
        if not isinstance(raw_entry, dict):
            raise ManifestError(f"[[l2.content]] entry {i} is not a table")
        where = f"[[l2.content]] entry {i}"
        props = raw_entry.get("properties") or {}
        if not isinstance(props, dict):
            raise ManifestError(f"{where}.properties must be a table")
        entries.append(
            L2ContentEntry(
                role=_require(raw_entry, "role", str, where),
                tier=_require(raw_entry, "tier", str, where),
                node_type=_require(raw_entry, "node_type", str, where),
                iri=_require(raw_entry, "iri", str, where),
                value=raw_entry.get("value"),
                properties=props,
            )
        )

    l3_table = data.get("l3") or {}
    installers = _str_tuple(l3_table.get("installers"), "[l3].installers")
    for ep in installers:
        if ":" not in ep or not all(ep.split(":", 1)):
            raise ManifestError(
                f"[l3].installers entry {ep!r} is not 'module:function'"
            )
    capacities = _str_tuple(l3_table.get("capacities"), "[l3].capacities")
    datastates = _str_tuple(l3_table.get("datastates"), "[l3].datastates")
    allow_new_realm = _str_tuple(
        l3_table.get("allow_new_realm"), "[l3].allow_new_realm"
    )

    l4_table = data.get("l4") or {}
    l4_slots = l4_table.get("slots") or {}
    if not isinstance(l4_slots, dict):
        raise ManifestError("[l4].slots must be a table")

    return SkillManifest(
        name=name,
        version=version,
        requires_mindsos_phase=phase_req,
        requires_bundles=requires_bundles,
        l2_content=tuple(entries),
        l3_installers=installers,
        l3_capacities=capacities,
        l3_datastates=datastates,
        allow_new_realm=allow_new_realm,
        l4_slots=l4_slots,
        digest=hashlib.sha256(raw_bytes).hexdigest(),
        source_path=str(p),
    )


__all__ = ["ManifestError", "L2ContentEntry", "SkillManifest", "parse_manifest"]
