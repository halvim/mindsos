"""Built-in capacities shipped with L3 (Phase 31).

First subpackage under ``mindsos_capacity/``. Holds the text-realm
vertical-slice family: 3 DataStates (``text.raw`` / ``text.tokens`` /
``text.sentences``) + 2 capacities (``text.space_split`` /
``text.sentence_split``) + an idempotent installer.

Pathfinding is NOT shipped as a registered builtin at Phase 31 per
pre-R0 PB-β + R0 PB-2 (locks; ADR-0071 §Implementation Phase-31 footer).
``find_pipeline`` (Phase 30 plain function in
``mindsos_capacity.pipeline``) is canonical; the parent's
``build_bfs_capacity_declaration`` scaffolding retires.

Halvim divergences from parent:

- Pathfinding is intentionally absent here (parent's ``pathfinding.py``
  ships Pipeline / PipelineStep / find_pipeline + the
  NotImplementedError stub; halvim Phase 30 already shipped
  Pipeline / PipelineStep / find_pipeline at the top of
  ``mindsos_capacity/`` and dropped the stub).
- Top-level ``mindsos_capacity/__init__.py`` does NOT re-export this
  subpackage's surface (R0 PB-5 lock) — users do
  ``from mindsos_capacity.builtins import install_text_capacities``.
"""

from __future__ import annotations

from .text import (
    DS_RAW_TEXT,
    DS_SENTENCES,
    DS_TOKENS,
    build_sentence_split,
    build_space_split,
    install_text_capacities,
    text_datastates,
)

__all__ = [
    "DS_RAW_TEXT",
    "DS_TOKENS",
    "DS_SENTENCES",
    "text_datastates",
    "build_space_split",
    "build_sentence_split",
    "install_text_capacities",
]
