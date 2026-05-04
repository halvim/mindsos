"""Cross-invocation state-file persistence for the ``mindsos graph`` CLI.

Pure-function (de)serialization helpers. The CLI command layer does the
``Graph`` ↔ ``dict`` conversion; this module only deals with primitives,
``Path``, and plain ``dict``.

State-file location: ``${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json``.
Parity with Phase 02's ``identity-registry-<scope>.json`` pattern.

State-file v1 schema (per PHASE_MAP Phase 03 row appendix #29):

    {
      "_state_version": 1,
      "graph_id": "<uuid4>",
      "name": "<name>",
      "role": "<role-or-null>",
      "nodes": [ {"node_id", "value", "type_name", "properties"} ],
      "edges": [ {"edge_id", "source_id", "target_id", "type_name",
                  "label", "properties"} ],
      "hyperedges": [ {"edge_id", "member_ids" (sorted), "label",
                       "properties"} ]
    }

* ``_state_version`` — strict on load: missing or > 1 raises ``RuntimeError``.
* Top-level lists (``nodes``, ``edges``, ``hyperedges``) sorted by id on
  save for byte-stable output (golden-diff CI / ``cat`` ergonomics).
* ``hyperedges[].member_ids`` always sorted (canonicalisation).
* Atomic writes via ``<path>.tmp`` + ``os.replace``.

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

#: Safe-name regex for graph state files (avoids path traversal and weird
#: shell-interaction characters). Centralised here so any caller (CLI,
#: future Phase 07 importers, tests) gets validation.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

#: Strict schema version for the on-disk JSON. Phase 07+ may bump.
STATE_VERSION = 1


def state_dir() -> Path:
    """Resolve the state directory: ``$MINDSOS_STATE_DIR`` or ``~/.mindsos``.

    The directory is created on demand (no error if it already exists).
    """
    raw = os.environ.get("MINDSOS_STATE_DIR")
    base = Path(raw) if raw else Path.home() / ".mindsos"
    base.mkdir(parents=True, exist_ok=True)
    return base


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

    Raises:
        ValueError: invalid ``name`` (via ``state_file_path``).
        FileNotFoundError: state file does not exist.
        RuntimeError: malformed JSON, missing ``_state_version`` field, or
            ``_state_version`` > 1 (Phase 03 only supports v1).
    """
    path = state_file_path(name)
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
    if not isinstance(version, int) or version > STATE_VERSION:
        raise RuntimeError(
            f"State file {path} has _state_version={version!r}; "
            f"this CLI supports v{STATE_VERSION}. "
            f"Run a newer mindsos to read this file."
        )
    return state


def save_graph_state(name: str, state: dict) -> None:
    """Write ``state`` atomically to the state file for graph ``name``.

    Atomic: writes to ``<path>.tmp`` then ``os.replace`` onto the canonical
    path. A Ctrl-C mid-write cannot corrupt the canonical file.

    Raises:
        ValueError: invalid ``name``.
    """
    path = state_file_path(name)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, indent=2, sort_keys=False) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def delete_state_file(name: str) -> None:
    """Remove the state file for graph ``name``.

    Raises:
        ValueError: invalid ``name``.
        FileNotFoundError: state file does not exist.
    """
    path = state_file_path(name)
    path.unlink()  # FileNotFoundError if missing
