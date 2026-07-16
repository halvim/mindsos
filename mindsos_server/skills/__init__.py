"""Skill-bundle install lifecycle (Phase 50 — ADR-0183).

Server-side per ADR-0010 (Server imports downward): the install driver
needs session capabilities + audit (server), KL Global writes (L2,
through the ADR-0180 ``make_writeable`` gate), and L3 installer entry
points (capacity). Layout:

* :mod:`manifest` — TOML manifest parser + ``SkillManifest`` + digest.
* :mod:`preflight` — read-only collision scan; ``PreflightReport``.
* :mod:`records` — ``installed-skills`` append-only record read/write
  (ADR-0150 §am-6; the ADR-0182 ``_value_json`` first consumer).
* :mod:`entry_points` — shared ``module:function`` installer resolution.
* :mod:`driver` — ``install_skill`` / ``uninstall_skill``.
* :mod:`activation` — ``apply_installed_skills`` per-process re-run
  (resilient at boot, strict on explicit activate; ``ActivationReport``).
"""

from .activation import ActivationReport, apply_installed_skills
from .driver import (
    InstallResult,
    SkillInstallError,
    SkillInstallRejectedError,
    SkillUninstallRefusedError,
    UninstallResult,
    install_skill,
    uninstall_skill,
)
from .entry_points import EntryPointError, resolve_entry_point
from .manifest import L2ContentEntry, ManifestError, SkillManifest, parse_manifest
from .preflight import PreflightFinding, PreflightReport, run_preflight
from .records import SkillRecordView, iter_skill_records, latest_records_by_bundle

__all__ = [
    "L2ContentEntry",
    "ManifestError",
    "SkillManifest",
    "parse_manifest",
    "PreflightFinding",
    "PreflightReport",
    "run_preflight",
    "SkillRecordView",
    "iter_skill_records",
    "latest_records_by_bundle",
    "EntryPointError",
    "resolve_entry_point",
    "InstallResult",
    "UninstallResult",
    "SkillInstallError",
    "SkillInstallRejectedError",
    "SkillUninstallRefusedError",
    "install_skill",
    "uninstall_skill",
    "ActivationReport",
    "apply_installed_skills",
]
