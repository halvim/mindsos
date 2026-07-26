"""nilm viz_spec — the per-brain hook the shared `graph` REPL verb reads.

Supplies the two brain-specific pieces the generic builder cannot know:
the semantic DataState **groups** (nilm's 7-way given/l2/floor/derived/
learned_out/appliance/verdict taxonomy) and the finder-composed **segments**.
Everything else (nodes, edges, capacity families, colors) the builder derives
from the live capacity views.

Wire it in `nilm_brain/repl.py`::

    from nilm_brain import viz_spec
    loop(BrainREPL(stack, viz_spec=viz_spec))

Colors are omitted here on purpose — the builder's defaults already match the
brain_graph_2.html palette. Override CAP_COLORS / DS_COLORS only to diverge.
"""
from __future__ import annotations

from typing import Any, Dict, List


0


def SEGMENTS(context: Any) -> List[Dict[str, Any]]:
    """Recompose nilm's two finder segments against the live stack's cl.

    The resident REPL discards the Solver, so the segments must be recomposed
    here (a recompute, not a read) from the same composer the Solver uses.
    Returns dicts in the builder's segment contract: {key, label, steps}
    where each step carries capacity_iri / input_datastates /
    output_datastates (the composed Segment.steps shape).
    """
    cl = getattr(context, "cl", None)
    session = getattr(context, "session", None)
    if cl is None:
        return []
    try:
        from nilm_brain.pipelines import (
            compose_recognition_segment, compose_appliance_segment,
        )
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    try:
        seg = compose_recognition_segment(cl, session)
        out.append({"key": "cycle",
                    "label": "1 · cycle_recognition  →  cycle_verdict",
                    "steps": list(seg.steps)})
    except Exception:
        pass
    try:
        seg = compose_appliance_segment(cl, session)
        out.append({"key": "appliance",
                    "label": "2 · appliance_signature  →  steady_signature",
                    "steps": list(seg.steps)})
    except Exception:
        pass
    return out


__all__ = ["DS_GROUPS", "SEGMENTS"]
