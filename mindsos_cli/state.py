"""Cross-invocation state-file persistence for the ``mindsos graph`` and
``mindsos schema`` CLIs (Phase 04-v2 surface).

Pure-function (de)serialization helpers. The CLI command layer does the
``Graph`` / ``Schema`` ↔ ``dict`` conversion; this module only deals with
primitives, ``Path``, and plain ``dict``.

State-file location: ``${MINDSOS_STATE_DIR or ~/.mindsos}/<kind>-<name>.json``.
Parity with Phase 02's ``identity-registry-<scope>.json`` pattern.

Phase 04-v2 ships TWO state-file kinds with INDEPENDENT version stories:

  - ``graph-<name>.json``   — Phase 03 shipped v=1; Phase 04 BUMPED to v=2
                              (adds optional ``schema_name`` field);
                              Phase 04-v2 BUMPS to v=3 (adds required
                              ``type_name`` per hyperedge entry).
                              Phase 04-v2 binary accepts v=1 (legacy v=1
                              from Phase 03), v=2 (Phase 04), and v=3
                              (current); writes v=3 on every save.
                              Cumulative migration is one-way: first
                              Phase 04-v2 mutation upgrades any pre-v=3
                              file directly to v=3; Phase 04 binary then
                              refuses (strict-version contract). Pre-v=3
                              hyperedges receive ``type_name="UNSPECIFIED"``
                              on first read (SENT-1 sentinel literal,
                              passes ADR-0021 cypher rel-type regex).
  - ``schema-<name>.json``  — Phase 04 shipped v=1; Phase 04-v2 BUMPS
                              to v=2 (adds optional ``hyperedge_types``
                              field). Phase 04-v2 binary accepts v=1
                              and v=2; writes v=2 on every save. v=1
                              → v=2 migration is one-way; missing
                              ``hyperedge_types`` treated as empty list.

Per-kind version constants (Phase 04-v2):

    GRAPH_STATE_VERSION  = 3  (Phase 03→v=1; Phase 04→v=2; Phase 04-v2→v=3)
    SCHEMA_STATE_VERSION = 2  (Phase 04→v=1; Phase 04-v2→v=2)

The legacy ``STATE_VERSION`` alias is kept for any external caller that
imported it; it equals ``GRAPH_STATE_VERSION``.

Graph state-file v3 schema (Phase 04-v2):

    {
      "_state_version": 3,
      "graph_id": "<uuid4>",
      "name": "<name>",
      "role": "<role-or-null>",
      "schema_name": "<schema-name-or-null>",
      "nodes": [ {"node_id", "value", "type_name", "properties"} ],
      "edges": [ {"edge_id", "source_id", "target_id", "type_name",
                  "label", "properties"} ],
      "hyperedges": [ {"edge_id", "type_name" (Phase 04-v2 — required;
                       UNSPECIFIED for legacy migration), "member_ids"
                       (sorted), "label", "properties"} ]
    }

Phase 03 v=1 files (no ``schema_name``, no hyperedge ``type_name``) and
Phase 04 v=2 files (no hyperedge ``type_name``) load fine — the loader
populates missing ``schema_name`` as ``None`` and missing hyperedge
``type_name`` as the SENT-1 sentinel ``"UNSPECIFIED"``.

Schema state-file v2 schema (Phase 04-v2):

    {
      "_state_version": 2,
      "name": "<name>",
      "strict": false,
      "node_types": [...sorted by name],
      "edge_types": [...sorted by name],
      "hyperedge_types": [   # Phase 04-v2 — optional; v=1 reads as empty.
        {
          "name": "<NAME>",
          "allowed_member_types": [ ...sorted ],
          "property_types": {"<key>": "<PropertyType.value>"},
          "description": "<text-or-null>"
        }
      ]
    }

Top-level lists sorted by ``name`` on save (byte-stable).
``allowed_sources`` / ``allowed_targets`` / ``allowed_member_types``
sorted on save. Atomic write via ``<path>.tmp`` + ``os.replace`` (parity
with the graph state file).

Errors are plain Python exceptions; the CLI command layer wraps with
``typer.Exit(1)`` + stderr structured message. No new ``StateError``
class in ``mindsos_core.exceptions``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterator

#: Safe-name regex for graph / schema state files (avoids path traversal
#: and weird shell-interaction characters). Centralised here so any
#: caller (CLI, future Phase 07 importers, tests) gets validation. The
#: same regex is used for both graph names and schema names.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

#: Strict on-disk version for ``graph-*.json``. Phase 03 wrote v=1.
#: Phase 04 BUMPED to v=2 (adds optional ``schema_name`` field).
#: Phase 04-v2 BUMPS to v=3 (adds required ``type_name`` per hyperedge
#: entry). Phase 04-v2 loaders accept v=1 ∪ v=2 ∪ v=3; writers always
#: emit v=3 (cumulative one-way migration; pre-v=3 hyperedges populated
#: with SENT-1 sentinel ``"UNSPECIFIED"``).
GRAPH_STATE_VERSION = 3

#: Strict on-disk version for ``schema-*.json``. Phase 04 introduced
#: this state-file kind at v=1. Phase 04-v2 BUMPS to v=2 (adds optional
#: ``hyperedge_types`` field). Phase 04-v2 loaders accept v=1 ∪ v=2;
#: writers always emit v=2 (one-way migration; missing
#: ``hyperedge_types`` treated as empty list for v=1 backward-compat).
SCHEMA_STATE_VERSION = 2

#: Backward-compat alias for any external caller that imported the old
#: name. Equals ``GRAPH_STATE_VERSION``. Will be removed when Phase 07
#: persistence rewrites supersede this module.
STATE_VERSION = GRAPH_STATE_VERSION


def state_dir() -> Path:
    """Resolve the state directory: ``$MINDSOS_STATE_DIR`` or ``~/.mindsos``.

    The directory is created on demand (no error if it already exists).
    """
    raw = os.environ.get("MINDSOS_STATE_DIR")
    base = Path(raw) if raw else Path.home() / ".mindsos"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── graph state file ─────────────────────────────────────────────────────────


def state_file_path(name: str) -> Path:
    """Compute the state-file path for graph ``name``, validating the name.

    Raises:
        ValueError: if ``name`` violates ``^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$``.
            The CLI catches this and exits 2 with a structured message.
    """
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid graph name {name!r}: must match {_NAME_RE.pattern}"
        )
    return state_dir() / f"graph-{name}.json"


def iter_state_files() -> Iterator[Path]:
    """Yield every ``graph-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("graph-*.json")))


def load_graph_state(name: str) -> dict:
    """Read and parse the state file for graph ``name``.

    Phase 04-v2 accepts ``_state_version ∈ {1, 2, 3}``:
      - v=1 (Phase 03 legacy): no ``schema_name`` field; no hyperedge
        ``type_name`` field. Loader treats missing ``schema_name`` as
        ``None`` and missing hyperedge ``type_name`` as the SENT-1
        sentinel ``"UNSPECIFIED"``.
      - v=2 (Phase 04 legacy): ``schema_name`` present; no hyperedge
        ``type_name``. Loader populates SENT-1 sentinel as above.
      - v=3 (Phase 04-v2 current): both fields present.
    First mutation under Phase 04-v2 binary upgrades the file directly
    to v=3 (cumulative one-way migration).

    Raises:
        ValueError: invalid ``name`` (via ``state_file_path``).
        FileNotFoundError: state file does not exist.
        RuntimeError: malformed JSON, missing ``_state_version`` field, or
            ``_state_version`` > ``GRAPH_STATE_VERSION``.
    """
    path = state_file_path(name)
    return _load_state_file(path, max_version=GRAPH_STATE_VERSION)


def save_graph_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for graph ``name``.

    Atomic: writes to ``<path>.tmp`` then ``os.replace`` onto the canonical
    path. A Ctrl-C mid-write cannot corrupt the canonical file.

    Phase 04-v2 always writes v=3 (callers MUST set ``_state_version: 3``
    in the dict; this function does not coerce).

    Raises:
        ValueError: invalid ``name``.
    """
    path = state_file_path(name)
    _atomic_write(path, state)


def delete_state_file(name: str) -> None:
    """Remove the state file for graph ``name``.

    Raises:
        ValueError: invalid ``name``.
        FileNotFoundError: state file does not exist.
    """
    path = state_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── schema state file (Phase 04) ─────────────────────────────────────────────


def schema_file_path(name: str) -> Path:
    """Compute the state-file path for schema ``name``, validating the name.

    Raises:
        ValueError: if ``name`` violates the same regex used for graphs.
    """
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid schema name {name!r}: must match {_NAME_RE.pattern}"
        )
    return state_dir() / f"schema-{name}.json"


def iter_schema_files() -> Iterator[Path]:
    """Yield every ``schema-*.json`` in the state dir, sorted by name."""
    return iter(sorted(state_dir().glob("schema-*.json")))


def load_schema_state(name: str) -> dict:
    """Read and parse the state file for schema ``name``.

    Phase 04-v2 accepts ``_state_version ∈ {1, 2}``:
      - v=1 (Phase 04 legacy): no ``hyperedge_types`` field. Loader
        treats missing as empty list.
      - v=2 (Phase 04-v2 current): ``hyperedge_types`` present.
    First mutation under Phase 04-v2 binary upgrades to v=2.

    Raises:
        ValueError: invalid ``name``.
        FileNotFoundError: state file does not exist.
        RuntimeError: malformed JSON, missing ``_state_version``, or
            ``_state_version`` > ``SCHEMA_STATE_VERSION``.
    """
    path = schema_file_path(name)
    return _load_state_file(path, max_version=SCHEMA_STATE_VERSION)


def save_schema_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for schema ``name``."""
    path = schema_file_path(name)
    _atomic_write(path, state)


def delete_schema_state_file(name: str) -> None:
    """Remove the state file for schema ``name``."""
    path = schema_file_path(name)
    path.unlink()  # FileNotFoundError if missing


# ── shared helpers ───────────────────────────────────────────────────────────


def _load_state_file(path: Path, *, max_version: int) -> dict:
    """Read + parse + version-check a state file.

    Args:
        path: Absolute path to the state file.
        max_version: Highest version this caller accepts (inclusive).
            Files with ``_state_version > max_version`` are refused.
            Older versions (≤ max_version, ≥ 1) are accepted; the
            caller is responsible for handling missing/optional fields.

    Raises:
        FileNotFoundError: file missing.
        RuntimeError: malformed JSON, missing ``_state_version``, or
            version > ``max_version``.
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
    version = state.get("_state_version")
    if version is None:
        raise RuntimeError(
            f"State file {path} missing required field '_state_version'."
        )
    if not isinstance(version, int) or version > max_version:
        raise RuntimeError(
            f"State file {path} has _state_version={version!r}; "
            f"this CLI supports v{max_version}. "
            f"Run a newer mindsos to read this file."
        )
    return state


def _atomic_write(path: Path, state: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, indent=2, sort_keys=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
