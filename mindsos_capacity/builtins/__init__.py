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

from .dream import (
    DS_DREAM_DIRECTIVE,
    DS_DREAM_TASK_REF,
    DreamDirective,
    DreamExecutionPolicy,
    ReplanInjectionDirective,
    build_dream_exploration,
    build_dream_maintenance,
    build_dream_retry,
    dream_datastates,
    install_dream_capacities,
)
from .text import (
    DS_RAW_TEXT,
    DS_SENTENCES,
    DS_TOKENS,
    build_sentence_split,
    build_space_split,
    install_text_capacities,
    text_datastates,
)
from .planning_v0 import install_planning_v0
from .reduction_v0 import install_reduction_v0
from .phase1_v0 import install_phase1_v0
from .orchestration_v0 import (
    classify_signal_to_tier,
    install_orchestration_v0,
    reset_v0_verdicts,
    set_should_replan_decision,
    set_sufficient_result,
)

__all__ = [
    "DS_RAW_TEXT",
    "DS_TOKENS",
    "DS_SENTENCES",
    "text_datastates",
    "build_space_split",
    "build_sentence_split",
    "install_text_capacities",
    # dream family (Phase 45)
    "DS_DREAM_TASK_REF",
    "DS_DREAM_DIRECTIVE",
    "DreamExecutionPolicy",
    "ReplanInjectionDirective",
    "DreamDirective",
    "dream_datastates",
    "build_dream_maintenance",
    "build_dream_exploration",
    "build_dream_retry",
    "install_dream_capacities",
    # Phase 47 placeholder v0 catalogs (ADR-0172)
    "install_planning_v0",
    "install_reduction_v0",
    "install_phase1_v0",
    "install_orchestration_v0",
    "classify_signal_to_tier",
    "set_should_replan_decision",
    "set_sufficient_result",
    "reset_v0_verdicts",
]
