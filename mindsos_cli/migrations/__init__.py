"""State-file migration chains (Phase 05a — P14).

Each state-file kind owns its own migration chain in a sibling module:

* ``mindsos_cli.migrations.graph``    — ``graph-<name>.json`` (current v=4)
* ``mindsos_cli.migrations.schema``   — ``schema-<name>.json`` (current v=2)
* ``mindsos_cli.migrations.metagraph`` — ``metagraph-<name>.json`` (current v=1)

Each module exposes:

* ``CURRENT_VERSION: int``         — the current shipping version.
* ``MIGRATIONS: list[Callable]``   — ``MIGRATIONS[i]`` migrates v(i+1) → v(i+2).
* ``migrate(state: dict) -> dict`` — apply MIGRATIONS from ``state["_state_version"]``
  forward to ``CURRENT_VERSION``; sets ``state["_state_version"] = CURRENT_VERSION``
  on the returned dict. Caller is responsible for atomic write.

The chain pattern was introduced in Phase 05a (P12 / P14 design locks) to
replace inline switch statements that grew O(N) per phase. Each version
bump appends one migration step to the relevant module — never edits a
prior step.

Loaders in ``mindsos_cli.state`` call ``migrate()`` after reading the raw
JSON and before handing the dict to the rehydration logic.
"""

from __future__ import annotations

from . import graph, metagraph, schema

__all__ = ["graph", "schema", "metagraph"]
