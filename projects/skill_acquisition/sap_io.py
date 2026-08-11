"""SAP I/O — friendly YAML authoring format ⇄ backend JSON (v0.1).

Humans (and the probing LLM) author in YAML; the backend consumes flat JSON. This is the
only translator between them. Friendly shape:

    skill: arc
    ground: arc.raw_task            # the single starting datastate
    datastates:                     # simple ids, or {id, note}
      - arc.grid
      - {id: arc.color, note: "recolor parameter"}
    capabilities:
      - name: build_grid
        family: perception
        reads:  [arc.raw_grid]      # → inputs
        writes: [arc.grid]          # → outputs
    tasks:
      - {id: 05f2a901, status: solved}

`load(path)` returns the backend-internal dict (dispatch on extension: .yaml/.yml friendly,
.json passthrough). Requires PyYAML for YAML inputs.
"""
from __future__ import annotations
import json


def _expand(doc: dict) -> dict:
    """Friendly YAML dict → backend-internal {skill, components[], tasks[]}."""
    ground = doc.get("ground")
    comps = []
    for ds in doc.get("datastates", []):
        d = ds if isinstance(ds, dict) else {"id": ds}
        iri = d["id"]
        comps.append({"id": iri, "kind": "datastate",
                      "is_ground": iri == ground,
                      "realm": iri.split(".", 1)[0] if "." in iri else None,
                      **({"note": d["note"]} if d.get("note") else {})})
    if ground and not any(c["id"] == ground for c in comps):
        comps.insert(0, {"id": ground, "kind": "datastate", "is_ground": True,
                         "realm": ground.split(".", 1)[0] if "." in ground else None})
    for cap in doc.get("capabilities", []):
        comps.append({"id": cap["name"], "kind": "capacity",
                      "inputs": cap.get("reads", []), "outputs": cap.get("writes", []),
                      "family": cap.get("family")})
    for rel in doc.get("relations", []):
        comps.append({"id": rel["name"], "kind": "relation",
                      "endpoints": rel.get("between", [])})
    return {"skill": doc.get("skill", "unnamed"), "components": comps,
            "tasks": doc.get("tasks", [])}


def load(path: str) -> dict:
    if path.endswith((".yaml", ".yml")):
        import yaml  # local import so JSON-only use needs no dependency
        return _expand(yaml.safe_load(open(path, encoding="utf-8")))
    return json.load(open(path, encoding="utf-8"))
