"""Fixture solver-output DataStates (the §1 shapes) for the standalone viz gate.

Two cases exercise the outcome enum end-to-end WITHOUT importing/running the
solver: a solved+verified recolor-enclosed task (#2 `00d62c1b`) and an abstain
task (#5 `045e512c`). Grids are small valid cell arrays — the gate tests viz
logic, not solve correctness.
"""

from __future__ import annotations

from .capabilities import DS_ENCLOSED, DS_PROFILE, DS_RULES, DS_SELECTION, DS_SOLVE

# recolor-enclosed: the enclosed background pockets (2,2)/(3,3) become yellow(4).
_T_IN = [[0, 0, 0, 0, 0, 0],
         [0, 0, 3, 0, 0, 0],
         [0, 3, 0, 3, 0, 0],
         [0, 0, 3, 0, 3, 0],
         [0, 0, 0, 3, 0, 0],
         [0, 0, 0, 0, 0, 0]]
_T_OUT = [[0, 0, 0, 0, 0, 0],
          [0, 0, 3, 0, 0, 0],
          [0, 3, 4, 3, 0, 0],
          [0, 0, 3, 4, 3, 0],
          [0, 0, 0, 3, 0, 0],
          [0, 0, 0, 0, 0, 0]]
_ENC = [[2, 2], [3, 3]]

#: #2 00d62c1b — solved, answer matches the withheld test -> verified.
SOLVED_2 = {
    DS_PROFILE: {
        "task_id": "00d62c1b", "split": "train",
        "train": [{"input": {"cells": _T_IN}, "output": {"cells": _T_OUT}}],
        "test": [{"input": {"cells": _T_IN}}],
    },
    DS_RULES: {"candidates": [{"text": "recolor [enclosed] yellow", "complete": True}],
               "bg": 0},
    DS_SELECTION: {"set": [{"kind": "recolor_cells", "text": "recolor [enclosed] yellow"}],
                   "size": 1, "text": "recolor [enclosed] yellow"},
    DS_SOLVE: {"output": _T_OUT, "matches_withheld": True},
    DS_ENCLOSED: {"train": [_ENC], "test": [_ENC]},
}

#: #5 045e512c — no covering rule set -> abstained ("I don't know").
ABSTAIN_5 = {
    DS_PROFILE: {
        "task_id": "045e512c", "split": "train",
        "train": [{"input": {"cells": [[0, 8, 0], [8, 0, 8], [0, 8, 0]]},
                   "output": {"cells": [[0, 8, 0], [8, 0, 8], [0, 8, 0]]}}],
        "test": [{"input": {"cells": [[0, 0, 0], [0, 2, 0], [0, 0, 0]]}}],
    },
    DS_RULES: {"candidates": [], "bg": 0},
    DS_SELECTION: None,
    DS_SOLVE: None,
    DS_ENCLOSED: None,
}
