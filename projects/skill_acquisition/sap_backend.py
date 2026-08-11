"""SAP backend — validator (v0.2).

Pipeline: LLM writes an input JSON (from probing docs+code) → this validates it against the
SAP_RULES catalog and writes a report (JSON + markdown, per-gap) → user fixes gaps, re-runs →
once the report is approved, `sap_install.py` turns it into a MindsOS register-plan.

Standalone (no mindsos import); rules mirror shipped MindsOS invariants (see SAP_RULES.md).

CLI:  python3 sap_backend.py <input.json> [--report-prefix out]
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple

KINDS = {"datastate", "capacity", "relation", "meta", "param"}


@dataclass
class Component:
    id: str
    kind: str
    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()
    family: str | None = None
    is_ground: bool = False
    endpoints: Tuple[str, str] | Tuple = ()
    realm: str | None = None

    @staticmethod
    def from_dict(d: dict) -> "Component":
        return Component(
            id=d["id"], kind=d["kind"],
            inputs=tuple(d.get("inputs", ())), outputs=tuple(d.get("outputs", ())),
            family=d.get("family"), is_ground=bool(d.get("is_ground", False)),
            endpoints=tuple(d.get("endpoints", ())), realm=d.get("realm"),
        )


@dataclass
class Violation:
    rule: str
    component: str
    message: str
    severity: str = "block"          # "block" (fails install) | "note" (reported, accepted)


@dataclass
class Report:
    skill: str
    ok: bool
    order: List[str]
    violations: List[Violation] = field(default_factory=list)
    tasks: Dict[str, str] = field(default_factory=dict)
    approved: bool = False          # user flips this to True to authorise install


# ── rules ────────────────────────────────────────────────────────────
def _edges(comps: Dict[str, Component]) -> Dict[str, set]:
    after: Dict[str, set] = {cid: set() for cid in comps}
    for c in comps.values():
        if c.kind == "capacity":
            for ds in (*c.inputs, *c.outputs):          # C1
                if ds in comps:
                    after[c.id].add(ds)
        if c.kind == "relation":                         # RL1
            for e in c.endpoints:
                if e in comps:
                    after[c.id].add(e)
    return after


def _kahn(after: Dict[str, set]) -> Tuple[List[str], bool]:
    after = {k: set(v) for k, v in after.items()}
    order, ready = [], sorted(k for k, d in after.items() if not d)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for k in after:
            if n in after[k]:
                after[k].discard(n)
                if not after[k] and k not in order and k not in ready:
                    ready.append(k)
        ready.sort()
    return order, len(order) == len(after)


def validate(components: List[Component], tasks: Dict[str, str], skill: str) -> Report:
    comps = {c.id: c for c in components}
    V: List[Violation] = []

    for c in comps.values():                                     # CL1
        if c.kind not in KINDS:
            V.append(Violation("CL1", c.id, f"unknown kind {c.kind!r}"))
        if c.kind == "datastate" and c.realm and "." in c.id and c.id.split(".", 1)[0] != c.realm:
            V.append(Violation("DS1", c.id, "id realm-prefix != realm field"))

    seen: set = set()                                            # DUP
    for c0 in components:
        if c0.id in seen:
            V.append(Violation("DUP", c0.id, "id declared more than once"))
        seen.add(c0.id)

    for c in comps.values():                                     # C1
        if c.kind == "capacity":
            for ds in (*c.inputs, *c.outputs):
                if ds not in comps:
                    V.append(Violation("C1", c.id, f"datastate {ds!r} not declared"))
                elif comps[ds].kind != "datastate":
                    V.append(Violation("C1", c.id, f"{ds!r} is {comps[ds].kind}, not a datastate"))
            if not c.family:                                     # C5
                V.append(Violation("C5", c.id, "capacity has no family"))
            if not c.inputs or not c.outputs:                    # TRANS — must be a transition
                miss = "reads nothing" if not c.inputs else ""
                miss += (" and " if miss and not c.outputs else "") + ("writes nothing" if not c.outputs else "")
                V.append(Violation("TRANS", c.id,
                                   f"not a datastate transition ({miss})"))

    produced = {ds for c in comps.values() if c.kind == "capacity" for ds in c.outputs}
    for c in comps.values():                                     # DS5 — accepted note
        if c.kind == "datastate" and not c.is_ground and c.id not in produced:
            V.append(Violation("DS5", c.id, "datastate with no producing capacity",
                               severity="note"))

    grounds = [c.id for c in comps.values() if c.is_ground]      # ground
    if len(grounds) != 1:
        V.append(Violation("ground", ",".join(grounds) or "-",
                           f"expected exactly 1 ground, found {len(grounds)}"))

    order, acyclic = _kahn(_edges(comps))
    if not acyclic:
        V.append(Violation("O1", "-", "dependency cycle — no valid creation order"))

    blocking = any(v.severity == "block" for v in V)
    return Report(skill=skill, ok=not blocking, order=order, violations=V, tasks=tasks)


# ── IO ───────────────────────────────────────────────────────────────
def load_input(path: str) -> Tuple[List[Component], Dict[str, str], str]:
    import sap_io                       # friendly YAML → internal dict; JSON passthrough
    d = sap_io.load(path)
    comps = [Component.from_dict(c) for c in d.get("components", [])]
    tasks = {t["id"]: t.get("status", "unknown") for t in d.get("tasks", [])}
    return comps, tasks, d.get("skill", "unnamed")


# Plain-language problem + fix per rule, in authoring (YAML) vocabulary. {c} = component id.
_PLAIN: Dict[str, Tuple[str, str]] = {
    "DS5": ("Nothing produces the data '{c}' — it's an orphan.",
            "Add a capability with `writes: [{c}]`, or set it as `ground:` if it's raw input, "
            "or remove '{c}' if unused."),
    "C1":  ("Capability '{c}' reads/writes data that isn't declared.",
            "Add the missing item to `datastates:`, or fix the name in its `reads:`/`writes:`."),
    "C5":  ("Capability '{c}' has no family.",
            "Give it a `family:` (perception, derivation, comparator, generator, predicate, …)."),
    "CL1": ("'{c}' isn't classified.",
            "List it under `datastates:`, `capabilities:`, or `relations:`."),
    "DS1": ("Data '{c}' — its name prefix doesn't match its realm.",
            "Make the id read `<realm>.<name>` matching the realm."),
    "DUP": ("'{c}' is declared more than once.",
            "Remove the duplicate — each id must be unique."),
    "TRANS": ("Capability '{c}' isn't a datastate transition — a capability must read ≥1 datastate and write ≥1 datastate.",
              "Give it both `reads: [...]` and `writes: [...]`, or remove it if it's not a real operation."),
    "ground": ("There must be exactly one starting point (ground).",
               "Mark exactly one datastate with `ground:`."),
    "O1":  ("The components form a dependency loop — no valid build order.",
            "Break the cycle: a capability can't (transitively) depend on its own output."),
}


def _plain(v: Violation) -> Tuple[str, str]:
    prob, fix = _PLAIN.get(v.rule, ("{c}: " + v.message, "Review this component."))
    c = v.component
    return prob.format(c=c), fix.format(c=c)


def write_report(rep: Report, prefix: str) -> None:
    j = asdict(rep)
    for vd, v in zip(j["violations"], rep.violations):        # enrich machine json
        vd["problem"], vd["fix"] = _plain(v)
    json.dump(j, open(prefix + ".json", "w"), indent=2)

    blocks = [v for v in rep.violations if v.severity == "block"]
    notes = [v for v in rep.violations if v.severity == "note"]
    head = "✓ PASS — ready to approve" if rep.ok else f"✗ {len(blocks)} blocking gap(s) to fix"
    L = [f"# SAP report — {rep.skill}", "", f"**{head}**",
         f"Approved for install: **{rep.approved}**", ""]
    if blocks:
        L += ["## Must fix (blocks install)", ""]
        for i, v in enumerate(blocks, 1):
            prob, fix = _plain(v)
            L += [f"**{i}. {prob}**", f"→ {fix}",
                  f"<sub>rule {v.rule} · `{v.component}`</sub>", ""]
    elif not notes:
        L += ["No gaps. Every data type traces to the ground and every capability is wired.", ""]
    if notes:
        L += ["## Notes (accepted — e.g. planned concepts; won't block install)", ""]
        L += [f"- {_plain(v)[0]} <sub>`{v.component}`</sub>" for v in notes] + [""]
    L += [f"## Build order ({len(rep.order)} components)", "",
          "  " + " → ".join(rep.order) if rep.order else "  (none)", "",
          "## Tasks", ""] + [f"- {k}: {s}" for k, s in rep.tasks.items()]
    L += ["", "---", "_When Status is PASS, set `\"approved\": true` in the .json and run "
          "`sap_install.py` to install._"]
    open(prefix + ".md", "w").write("\n".join(L))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python3 sap_backend.py <input.json> [--report-prefix out]")
    inp = sys.argv[1]
    prefix = sys.argv[sys.argv.index("--report-prefix") + 1] if "--report-prefix" in sys.argv \
        else inp.rsplit(".", 1)[0] + "_report"
    comps, tasks, skill = load_input(inp)
    rep = validate(comps, tasks, skill)
    write_report(rep, prefix)
    print(f"{skill}: {'PASS' if rep.ok else str(len(rep.violations)) + ' gaps'} "
          f"→ {prefix}.md / .json")
