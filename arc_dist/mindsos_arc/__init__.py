"""mindsos_arc — the ARC intelligence, packaged as an on-top MindsOS skill bundle.

A *consumer* of MindsOS (installs through the public Phase-50 skill path;
depends on released ``mindsos``). NOT part of the core stack — not in the
mindsos wheel's ``packages.find``. The bundle manifest (``bundle/manifest.toml``)
names ``mindsos_arc.capacities:install_arc`` as its L3 installer entry point.
"""
from __future__ import annotations

from .capacities import arc_datastates, install_arc

__all__ = ["install_arc", "arc_datastates"]
__version__ = "0.1.0"
