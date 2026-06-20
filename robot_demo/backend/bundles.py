"""DM-2 — bundle-name → manifest-path resolver (P-8 selective install).

``DeviceProfile.bundle_names`` carries hyphenated bundle names
(``core``/``manager``/``arm-suction``/``arm-jaw``/``conveyor``); the
on-disk bundle dirs are underscore-named (TOML lives at
``robot_demo/bundles/<dir>/manifest.toml``). This module is the single
place that maps one to the other so the bootstrap install loop stays
declarative.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

#: Package-relative bundles root (``robot_demo/bundles``).
BUNDLES_ROOT = Path(__file__).resolve().parent.parent / "bundles"

#: Bundle name (as declared on DeviceProfile.bundle_names) → dir name.
_BUNDLE_DIRS: Dict[str, str] = {
    "core": "core",
    "manager": "manager",
    "arm-suction": "arm_suction",
    "arm-jaw": "arm_jaw",
    "conveyor": "conveyor",
}


def manifest_path(bundle_name: str) -> str:
    """Absolute path to a bundle's ``manifest.toml``.

    Raises:
        KeyError: unknown bundle name (profile/bundle mismatch).
        FileNotFoundError: the manifest is missing on disk.
    """
    if bundle_name not in _BUNDLE_DIRS:
        raise KeyError(
            f"unknown bundle {bundle_name!r}; known: {sorted(_BUNDLE_DIRS)}"
        )
    p = BUNDLES_ROOT / _BUNDLE_DIRS[bundle_name] / "manifest.toml"
    if not p.is_file():
        raise FileNotFoundError(f"bundle manifest not found: {p}")
    return str(p)


__all__ = ["BUNDLES_ROOT", "manifest_path"]
