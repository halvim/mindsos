"""Cross-invocation state-file persistence (Phase 05c surface).

Pure-function (de)serialization helpers. The CLI command layer does the
``Graph`` / ``Schema`` / ``Metagraph`` / ``MetagraphSchema`` ↔ ``dict``
conversion; this module only deals with primitives, ``Path``, and plain
``dict``.

State-file location: ``${MINDSOS_STATE_DIR or ~/.mindsos}/<kind>-<name>.json``.

Phase 05c ships FOUR state-file kinds with INDEPENDENT version stories:

  - ``graph-<name>.json``         — current v=4 (Phase 05a; unchanged in
                                    05b/05c). v=1..3 load via
                                    ``mindsos_cli.migrations.graph``.
                                    Phase 05a added the optional
                                    ``metagraph_name: str | null`` back-pointer
                                    field (B2 lock).
  - ``schema-<name>.json``        — current v=2 (Phase 04-v2; unchanged
                                    in 05a/05b/05c). v=1 (Phase 04)
                                    loads via ``mindsos_cli.migrations.schema``.
  - ``metagraph-<name>.json``     — current v=3 (Phase 05c — P14-A
                                    smaller-items fold bump). v=1..2
                                    load via ``mindsos_cli.migrations.metagraph``
                                    chain. 05b added top-level
                                    ``intergraph_edges`` + ``schema_name``;
                                    05c adds ``intergraph_hyperedges``.
  - ``metagraph-schema-<name>.json`` — current v=2 (Phase 05c — P14-A
                                    smaller-items fold bump). v=1 (Phase
                                    05b) loads via
                                    ``mindsos_cli.migrations.metagraph_schema``.
                                    05c adds ``intergraph_hyperedge_types``;
                                    Phase 05d adds ``meta_edge_types`` +
                                    ``meta_hyperedge_types``.

Migration chain (P14 lock):
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The cumulative-migration switch that previously lived inline in
``_state_to_graph`` is now a per-file chain of pure dict→dict steps under
``mindsos_cli/migrations/``. ``_load_state_file`` calls ``migrate(state)``
after parsing JSON and before handing the dict to the rehydrator. Each
new version bump appends one migration step to the relevant module —
never edits a prior step. This keeps ``_state_to_graph`` etc. focused on
the current-version shape.

Per-kind version constants (Phase 10):

    GRAPH_STATE_VERSION            = 5   (P03→1; P04→2; P04-v2→3; P05a→4; P10→5)
    SCHEMA_STATE_VERSION           = 2   (P04→1; P04-v2→2)
    METAGRAPH_STATE_VERSION        = 5   (P05a→1; P05b→2; P05c→3; P09→4; P10→5)
    METAGRAPH_SCHEMA_STATE_VERSION = 3   (P05b→1; P05c→2; P05d→3)

The legacy ``STATE_VERSION`` alias is kept for any external caller; it
equals ``GRAPH_STATE_VERSION``.

Graph state-file v4 schema (Phase 05a, unchanged in 05b):

    {
      "_state_version": 4,
      "graph_id": "<uuid4>",
      "name": "<name>",
      "role": "<role-or-null>",
      "schema_name": "<schema-name-or-null>",
      "metagraph_name": "<metagraph-name-or-null>",   # P05a B2 — back-pointer.
      "nodes": [ {"node_id", "value", "type_name", "properties"} ],
      "edges": [ {"edge_id", "source_id", "target_id", "type_name",
                  "label", "properties"} ],
      "hyperedges": [ {"edge_id", "type_name", "member_ids" (sorted),
                       "label", "properties"} ]
    }

Metagraph state-file v3 schema (Phase 05c — P14-A bump; v=2 adds
``intergraph_edges`` + ``schema_name``; v=3 adds ``intergraph_hyperedges``):

    {
      "_state_version": 3,
      "metagraph_id": "<uuid4>",
      "name": "<name>",
      "properties": {"<k>": "<value>"},
      "schema_name": "<metagraph-schema-name-or-null>",  # P05b — Pushback 11-A reference
      "contained_graphs": ["<gname>", ...sorted],
      "metaedges": [
        {"edge_id", "source_graph": "<gname>", "target_graph": "<gname>",
         "type_name": "<UPPER>", "label": "<text-or-null>", "properties": {...}}
      ],
      "metahyperedges": [
        {"edge_id", "type_name": "<UPPER>",
         "member_graphs": [...sorted by gname], "label", "properties"}
      ],
      "intergraph_edges": [
        {"edge_id", "source_graph": "<gname>", "source_node": "<node-id>",
         "target_graph": "<gname>", "target_node": "<node-id>",
         "type_name": "<UPPER>", "compositional": <bool>,
         "label": "<text-or-null>", "properties": {...}}
      ],
      "intergraph_hyperedges": [
        {"edge_id",
         "anchors": [["<gname>", "<node-id>"], ...],
         "members": [["<gname>", "<node-id>"], ...],
         "type_name": "<UPPER>", "compositional": <bool>,
         "label": "<text-or-null>", "properties": {...}}
      ]
    }

MetagraphSchema state-file v2 schema (Phase 05c — v=1 added
``intergraph_edge_types``; v=2 adds ``intergraph_hyperedge_types``):

    {
      "_state_version": 2,
      "name": "<name>",
      "strict": <bool>,
      "intergraph_edge_types": [
        {"name": "<UPPER>",
         "allowed_source_types": [...sorted],
         "allowed_target_types": [...sorted],
         "allowed_source_graphs": [...sorted],
         "allowed_target_graphs": [...sorted],
         "property_types": {"<k>": "<PropertyType.value>"},
         "description": "<text-or-null>"}
      ],
      "intergraph_hyperedge_types": [
        {"name": "<UPPER>",
         "allowed_anchor_types": [...sorted],
         "allowed_member_types": [...sorted],
         "allowed_anchor_graphs": [...sorted],
         "allowed_member_graphs": [...sorted],
         "ordered": <bool>,
         "property_types": {"<k>": "<PropertyType.value>"},
         "description": "<text-or-null>"}
      ]
    }

Top-level lists sorted byte-stably on save. Atomic write via ``<path>.tmp``
+ ``os.replace`` (parity with graph and schema state files).

Errors are plain Python exceptions; the CLI command layer wraps with
``typer.Exit(1)`` + stderr structured message.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterator, Optional

from mindsos_cli.migrations import graph as _graph_migrations
from mindsos_cli.migrations import metagraph as _metagraph_migrations
from mindsos_cli.migrations import metagraph_schema as _metagraph_schema_migrations
from mindsos_cli.migrations import schema as _schema_migrations

#: Safe-name regex for state files (avoids path traversal and weird
#: shell-interaction characters). Centralised here so any caller (CLI,
#: future Phase 07 importers, tests) gets validation. Same regex used
#: for graph, schema, and metagraph names.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

#: Graph state-file version. P03→1, P04→2, P04-v2→3, P05a→4. Loaders
#: accept v=1..4 (via migration chain); writers emit v=4.
GRAPH_STATE_VERSION = _graph_migrations.CURRENT_VERSION  # = 5

#: Schema state-file version. P04→1, P04-v2→2. Loaders accept v=1..2;
#: writers emit v=2.
SCHEMA_STATE_VERSION = _schema_migrations.CURRENT_VERSION  # = 2

#: Metagraph state-file version. P05a→1, P05b→2, P05c→3. Loaders accept
#: v=1..3 (via migration chain); writers emit v=3.
METAGRAPH_STATE_VERSION = _metagraph_migrations.CURRENT_VERSION  # = 5

#: MetagraphSchema state-file version. P05b→1, P05c→2. Loaders accept
#: v=1..2 (via migration chain); writers emit v=2.
METAGRAPH_SCHEMA_STATE_VERSION = _metagraph_schema_migrations.CURRENT_VERSION  # = 3

#: Backward-compat alias for any external caller.
STATE_VERSION = GRAPH_STATE_VERSION


def state_dir() -> Path:
    """Resolve ``$MINDSOS_STATE_DIR`` or ``~/.mindsos``; create on demand."""
    raw = os.environ.get("MINDSOS_STATE_DIR")
    base = Path(raw) if raw else Path.home() / ".mindsos"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _validate_name(name: str, *, kind: str) -> None:
    """Validate a state-file name; raise ValueError on miss."""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid {kind} name {name!r}: must match {_NAME_RE.pattern}"
        )


# ── graph state file ─────────────────────────────────────────────────────────


def state_file_path(name: str) -> Path:
    """Compute the state-file path for graph ``name``, validating the name."""
    _validate_name(name, kind="graph")
    return state_dir() / f"graph-{name}.json"


def iter_state_files() -> Iterator[Path]:
    """Yield every ``graph-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("graph-*.json")))


def load_graph_state(name: str) -> dict:
    """Read, parse, and migrate the state file for graph ``name``.

    The raw JSON is loaded then passed through
    ``mindsos_cli.migrations.graph.migrate(state)`` which forward-migrates
    v=1..3 → v=4 in-place (idempotent on v=4). The returned dict ALWAYS
    has ``_state_version == GRAPH_STATE_VERSION``.

    Raises:
        ValueError: invalid ``name``.
        FileNotFoundError: state file does not exist.
        RuntimeError: malformed JSON, missing/invalid ``_state_version``,
            or version > current.
    """
    path = state_file_path(name)
    return _load_and_migrate(
        path, _graph_migrations.migrate, current=GRAPH_STATE_VERSION,
    )


def save_graph_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for graph ``name``."""
    path = state_file_path(name)
    _atomic_write(path, state)


def delete_state_file(name: str) -> None:
    """Remove the state file for graph ``name``."""
    path = state_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── schema state file ───────────────────────────────────────────────────────


def schema_file_path(name: str) -> Path:
    """Compute the state-file path for schema ``name``, validating the name."""
    _validate_name(name, kind="schema")
    return state_dir() / f"schema-{name}.json"


def iter_schema_files() -> Iterator[Path]:
    """Yield every ``schema-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("schema-*.json")))


def load_schema_state(name: str) -> dict:
    """Read, parse, and migrate the state file for schema ``name``."""
    path = schema_file_path(name)
    return _load_and_migrate(
        path, _schema_migrations.migrate, current=SCHEMA_STATE_VERSION,
    )


def save_schema_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for schema ``name``."""
    path = schema_file_path(name)
    _atomic_write(path, state)


def delete_schema_state_file(name: str) -> None:
    """Remove the state file for schema ``name``."""
    path = schema_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── metagraph state file (Phase 05a — NEW) ──────────────────────────────────


def metagraph_file_path(name: str) -> Path:
    """Compute the state-file path for metagraph ``name``, validating the name."""
    _validate_name(name, kind="metagraph")
    return state_dir() / f"metagraph-{name}.json"


def iter_metagraph_files() -> Iterator[Path]:
    """Yield every ``metagraph-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("metagraph-*.json")))


def load_metagraph_state(name: str) -> dict:
    """Read, parse, and migrate the state file for metagraph ``name``."""
    path = metagraph_file_path(name)
    return _load_and_migrate(
        path, _metagraph_migrations.migrate, current=METAGRAPH_STATE_VERSION,
    )


def save_metagraph_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for metagraph ``name``."""
    path = metagraph_file_path(name)
    _atomic_write(path, state)


def delete_metagraph_state_file(name: str) -> None:
    """Remove the state file for metagraph ``name``."""
    path = metagraph_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── metagraph-schema state file (Phase 05b — NEW) ──────────────────────────


def metagraph_schema_file_path(name: str) -> Path:
    """Compute the state-file path for metagraph-schema ``name``, validating the name."""
    _validate_name(name, kind="metagraph-schema")
    return state_dir() / f"metagraph-schema-{name}.json"


def iter_metagraph_schema_files() -> Iterator[Path]:
    """Yield every ``metagraph-schema-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("metagraph-schema-*.json")))


def load_metagraph_schema_state(name: str) -> dict:
    """Read, parse, and migrate the state file for metagraph-schema ``name``."""
    path = metagraph_schema_file_path(name)
    return _load_and_migrate(
        path,
        _metagraph_schema_migrations.migrate,
        current=METAGRAPH_SCHEMA_STATE_VERSION,
    )


def save_metagraph_schema_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for metagraph-schema ``name``."""
    path = metagraph_schema_file_path(name)
    _atomic_write(path, state)


def delete_metagraph_schema_state_file(name: str) -> None:
    """Remove the state file for metagraph-schema ``name``."""
    path = metagraph_schema_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── shared helpers ───────────────────────────────────────────────────────────


def _load_and_migrate(path: Path, migrate_fn, *, current: int) -> dict:
    """Read + parse + migrate (P14).

    The migration function (one per state-file kind) raises ``ValueError``
    on missing/invalid ``_state_version`` or forward-version.
    """
    raw = path.read_text(encoding="utf-8")  # FileNotFoundError if missing
    try:
        state = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"State file {path} is not valid JSON: {e.msg} at line {e.lineno}"
        ) from e
    if not isinstance(state, dict):
        raise RuntimeError(
            f"State file {path} top-level value must be a JSON object"
        )
    try:
        return migrate_fn(state)
    except ValueError as e:
        # Surface forward-version files with the strict-version error
        # message that earlier phases used (preserves Phase 03/04
        # diagnostic UX).
        raise RuntimeError(
            f"State file {path}: {e}. "
            f"This CLI supports v{current}. Run a newer mindsos to read this file."
        ) from e


def _atomic_write(path: Path, state: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, indent=2, sort_keys=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
