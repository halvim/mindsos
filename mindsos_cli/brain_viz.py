"""``mindsos_cli/brain_viz.py`` — build the viewer ``DATA`` object from a live
resident-brain stack, and inject it into the self-contained viewer template.

This is the headless, unit-testable core behind the REPL ``graph`` verb. It
reproduces the schema of ``brain_graph_2.html`` exactly:

    DATA = {
      nodes:   [ {id:"ds:x"|"cap:x", label, kind:"ds"|"cap", group,
                  color:{...}, shape:"box"|"ellipse", seg:[segkey,…],
                  cap?:{family, inputs:[name…], outputs:[name…]} } ],
      edges:   [ {id:"e#", from, to, arrows:"to", kind:"consume"|"produce",
                  seg:[segkey,…]} ],
      segments:{ key:{label, caps:[name…], nodeIds:["cap:x"|"ds:x", …]} },
      capColor:{ family:hex },  dsColor:{ group:hex },
    }

Everything except **ds groups** and **segments** is derived generically from
the capacity views (`iter_datastates` / `iter_categories` / `iter_capacities`
/ `inputs_of` / `outputs_of`). Groups + segments come from the per-brain
``viz_spec`` hook; when it is absent a topology heuristic fills groups and
there are simply no segments.

``viz_spec`` contract (every attribute optional)::

    DS_GROUPS : dict[str, str]          # short-name OR full iri -> group
    CAP_COLORS: dict[str, str]          # family -> "#rrggbb"
    DS_COLORS : dict[str, str]          # group  -> "#rrggbb"
    def SEGMENTS(context) -> list       # each item: an object with .steps
                                        #   (step.capacity_iri / .input_datastates
                                        #   / .output_datastates) and optional
                                        #   .target_datastate, OR a dict
                                        #   {key,label,steps,target}.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# Generic labels for the topology-heuristic ds groups (any brain, no viz_spec
# needed). Brain-specific nice names come from viz_spec.DS_LABELS / CAP_LABELS.
_HEURISTIC_DS_LABELS: Dict[str, str] = {
    "given": "given (entry input)", "derived": "derived",
    "verdict": "verdict (terminal output)", "constant": "constant / unused",
    "other": "other",
}

# Palette parity with brain_graph_2.html (the shipped prototype).
DEFAULT_CAP_COLORS: Dict[str, str] = {
    "perception": "#ff8f6b", "derivation": "#2dd4bf", "scoring": "#fbbf24",
    "decision": "#c084fc", "comprehension": "#93c5fd", "predicate": "#a3e635",
}
DEFAULT_DS_COLORS: Dict[str, str] = {
    "given": "#37568a", "l2": "#8a6d3b", "floor": "#7d5a4f", "derived": "#3f6d78",
    "learned_out": "#556b2f", "appliance": "#714a6b", "verdict": "#a83254",
    # generic topology-heuristic fallbacks (used only when no per-brain map):
    "constant": "#5b6470", "other": "#4b5560",
}
_CAP_RAMP = ["#ff8f6b", "#2dd4bf", "#fbbf24", "#c084fc", "#93c5fd", "#a3e635",
             "#f472b6", "#34d399", "#facc15", "#a78bfa"]
_BORDER = "#0b0d12"
_HILITE = "#f5f7fa"


def _short(iri: Any) -> str:
    s = str(iri)
    return s.rsplit(":", 1)[-1].rsplit(".", 1)[-1]


def _vid(kind: str, iri: Any) -> str:
    # Full IRI keeps ids unique — two datastates that share a short name
    # (e.g. path_finding.goal vs phase1.goal) must not collapse to one node,
    # or vis.DataSet raises "id already exists" and the graph never renders.
    return ("cap:" if kind == "cap" else "ds:") + str(iri)


def _node_color(bg: str) -> Dict[str, Any]:
    return {"background": bg, "border": _BORDER,
            "highlight": {"background": bg, "border": _HILITE},
            "hover": {"background": bg, "border": _HILITE}}


# ── introspection ────────────────────────────────────────────────────────

def _iter_unique(views: List[Any], meth: str, *args: Any):
    seen = set()
    for v in views:
        fn = getattr(v, meth, None)
        if fn is None:
            continue
        for n in fn(*args):
            if n.node_id in seen:
                continue
            seen.add(n.node_id)
            yield n, v


def _family_map(views: List[Any]) -> Dict[str, str]:
    fam: Dict[str, str] = {}
    for v in views:
        try:
            cats = list(v.iter_categories())
        except Exception:
            cats = []
        for cat in cats:
            for cap in v.iter_capacities(cat):
                fam.setdefault(cap.node_id, cat)
    return fam


def _io_of(views: List[Any], cap_iri: str) -> Tuple[List[str], List[str]]:
    ins: List[str] = []
    outs: List[str] = []
    for v in views:
        if v.get_capacity(cap_iri) is None:
            continue
        try:
            for i in v.inputs_of(cap_iri):
                if i not in ins:
                    ins.append(i)
            for o in v.outputs_of(cap_iri):
                if o not in outs:
                    outs.append(o)
        except Exception:
            pass
    return ins, outs


# ── group resolution ─────────────────────────────────────────────────────

def _resolve_groups(ds_iris: List[str], cap_io: Dict[str, Tuple[List[str], List[str]]],
                    ds_group_map: Dict[str, str]) -> Dict[str, str]:
    produced, consumed = set(), set()
    for ins, outs in cap_io.values():
        produced |= set(outs)
        consumed |= set(ins)
    groups: Dict[str, str] = {}
    for iri in ds_iris:
        # explicit per-brain map wins (match on full iri or short name)
        g = ds_group_map.get(iri) or ds_group_map.get(_short(iri))
        if g is None:
            p, k = iri in produced, iri in consumed
            g = ("derived" if p and k else "given" if k and not p
                 else "verdict" if p and not k else "constant")
        groups[iri] = g
    return groups


# ── segment normalisation ────────────────────────────────────────────────

def _norm_segments(raw: Any) -> List[Dict[str, Any]]:
    """Normalise whatever ``spec.SEGMENTS(context)`` returns into a list of
    ``{key,label,steps:[(cap_iri, in_iris, out_iris)]}``."""
    out: List[Dict[str, Any]] = []
    if not raw:
        return out
    for i, item in enumerate(raw):
        key = label = None
        steps_src = None
        if isinstance(item, tuple) and len(item) == 2:
            label, seg_obj = item
        else:
            seg_obj = item
        if isinstance(seg_obj, dict):
            key = seg_obj.get("key")
            label = label or seg_obj.get("label")
            steps_src = seg_obj.get("steps")
        else:
            steps_src = getattr(seg_obj, "steps", None)
            label = label or getattr(seg_obj, "label", None)
        steps: List[Tuple[str, List[str], List[str]]] = []
        for st in steps_src or []:
            if isinstance(st, dict):
                cap = st.get("capacity_iri") or st.get("capacity")
                ins = st.get("input_datastates") or st.get("inputs") or []
                outs = st.get("output_datastates") or st.get("outputs") or []
            else:
                cap = getattr(st, "capacity_iri", None) or getattr(st, "capacity", None)
                ins = getattr(st, "input_datastates", None) or []
                outs = getattr(st, "output_datastates", None) or []
            if cap:
                steps.append((cap, list(ins), list(outs)))
        out.append({"key": key or f"seg{i}", "label": label or f"segment {i+1}",
                    "steps": steps})
    return out


# ── main builder ─────────────────────────────────────────────────────────

def build_data(views: List[Any], spec: Any = None, context: Any = None) -> Dict[str, Any]:
    views = [v for v in views if v is not None]
    ds_group_map = dict(getattr(spec, "DS_GROUPS", {}) or {})
    cap_colors = {**DEFAULT_CAP_COLORS, **(getattr(spec, "CAP_COLORS", {}) or {})}
    ds_colors = {**DEFAULT_DS_COLORS, **(getattr(spec, "DS_COLORS", {}) or {})}
    cap_labels = dict(getattr(spec, "CAP_LABELS", {}) or {})
    ds_labels = {**_HEURISTIC_DS_LABELS, **(getattr(spec, "DS_LABELS", {}) or {})}
    title = getattr(spec, "TITLE", None)

    fam = _family_map(views)
    ds_iris = [n.node_id for n, _ in _iter_unique(views, "iter_datastates")]
    cap_iris = [n.node_id for n, _ in _iter_unique(views, "iter_capacities")]
    cap_io = {c: _io_of(views, c) for c in cap_iris}
    groups = _resolve_groups(ds_iris, cap_io, ds_group_map)

    # assign ramp colors to any family lacking an explicit color
    for c in cap_iris:
        f = fam.get(c, "other")
        if f not in cap_colors:
            cap_colors[f] = _CAP_RAMP[len(cap_colors) % len(_CAP_RAMP)]

    nodes: List[Dict[str, Any]] = []
    for iri in ds_iris:
        g = groups[iri]
        nodes.append({"id": _vid("ds", iri), "label": _short(iri), "kind": "ds",
                      "group": g, "color": _node_color(ds_colors.get(g, ds_colors["other"])),
                      "shape": "box", "seg": []})
    for iri in cap_iris:
        f = fam.get(iri, "other")
        ins, outs = cap_io[iri]
        nodes.append({"id": _vid("cap", iri), "label": _short(iri), "kind": "cap",
                      "group": f, "color": _node_color(cap_colors.get(f, "#4b5560")),
                      "shape": "ellipse", "seg": [],
                      "cap": {"family": f,
                              "inputs": [_short(x) for x in ins],
                              "outputs": [_short(x) for x in outs]}})

    known = {n["id"] for n in nodes}
    edges: List[Dict[str, Any]] = []
    ei = 0
    for iri in cap_iris:
        ins, outs = cap_io[iri]
        cvid = _vid("cap", iri)
        for i in ins:
            dvid = _vid("ds", i)
            if dvid in known:
                edges.append({"id": f"e{ei}", "from": dvid, "to": cvid,
                              "arrows": "to", "kind": "consume", "seg": []}); ei += 1
        for o in outs:
            dvid = _vid("ds", o)
            if dvid in known:
                edges.append({"id": f"e{ei}", "from": cvid, "to": dvid,
                              "arrows": "to", "kind": "produce", "seg": []}); ei += 1

    # segments (per-brain) → DATA.segments + seg membership on nodes/edges
    segments: Dict[str, Any] = {}
    seg_fn = getattr(spec, "SEGMENTS", None)
    raw = seg_fn(context) if callable(seg_fn) else None
    for seg in _norm_segments(raw):
        caps: List[str] = []
        node_ids: List[str] = []

        def push(x: str) -> None:
            if x and x not in node_ids:
                node_ids.append(x)

        for cap_iri, ins, outs in seg["steps"]:
            for i in ins:
                push(_vid("ds", i))
            caps.append(_short(cap_iri))
            push(_vid("cap", cap_iri))
            for o in outs:
                push(_vid("ds", o))
        segments[seg["key"]] = {"label": seg["label"], "caps": caps,
                                "nodeIds": [n for n in node_ids if n in known]}

    for n in nodes:
        n["seg"] = [k for k, s in segments.items() if n["id"] in s["nodeIds"]]
    nid_seg = {k: set(s["nodeIds"]) for k, s in segments.items()}
    for e in edges:
        e["seg"] = [k for k, ids in nid_seg.items() if e["from"] in ids and e["to"] in ids]

    present_fams = {n["group"] for n in nodes if n["kind"] == "cap"}
    present_grps = {n["group"] for n in nodes if n["kind"] == "ds"}
    return {
        "nodes": nodes,
        "edges": edges,
        "segments": segments,
        "capColor": {f: cap_colors[f] for f in cap_colors if f in present_fams},
        "dsColor": {g: ds_colors[g] for g in ds_colors if g in present_grps},
        "title": title,
        "capNames": {f: cap_labels[f] for f in cap_labels if f in present_fams},
        "dsNames": {g: ds_labels[g] for g in ds_labels if g in present_grps},
    }


def build_html(views: List[Any], template: str, spec: Any = None,
               context: Any = None) -> str:
    """Inject ``build_data`` output into the viewer template placeholder."""
    data = build_data(views, spec=spec, context=context)
    payload = "const DATA = " + json.dumps(data, separators=(",", ":")) + ";"
    if "/*__DATA__*/{}" in template:
        return template.replace("const DATA = /*__DATA__*/{};", payload)
    raise ValueError("template is missing the /*__DATA__*/{} placeholder")


__all__ = ["build_data", "build_html", "DEFAULT_CAP_COLORS", "DEFAULT_DS_COLORS"]
