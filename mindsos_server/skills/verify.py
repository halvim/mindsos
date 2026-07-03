"""Read-only cross-layer bundle verifier (``mindsos skill verify``).

Reports how an installed bundle's capacities sit in the persisted MindsOS
metagraphs by checking the links MindsOS actually stores. Read-only; stores
nothing. State-source approach C' (SKILL_VERIFY_DESIGN_NOTE.md §4): L2 read from
persisted knowledge, L3 read from the reactivated capacity layer.
"""

from __future__ import annotations

import ast
import importlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DEFECT = "DEFECT"
WARN = "WARN"
INFO = "INFO"
NEUTRAL = "NEUTRAL"

PRESENT = "PRESENT"
MISSING = "MISSING"
MALFORMED = "MALFORMED"
OK = "OK"


@dataclass
class CheckResult:
    check: int
    name: str
    status: str
    severity: str
    detail: str
    subject: str = ""


@dataclass
class VerifyReport:
    bundle_name: str
    bundle_version: str = ""
    bundle_status: str = ""
    found: bool = False
    stored: List[CheckResult] = field(default_factory=list)
    code_derived: List[CheckResult] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def defects(self) -> List[CheckResult]:
        return [r for r in self.stored if r.severity == DEFECT]

    def ok(self) -> bool:
        return self.found and not self.defects()


def _roster(record: Any) -> Dict[str, Any]:
    value = getattr(record, "value", None) or {}
    return dict(value)


def _l2_node(kl: Any, iri: str) -> Optional[Tuple[Any, Optional[str]]]:
    for graph in kl.global_metagraph().graphs.values():
        node = graph.nodes.get(iri)
        if node is not None:
            return node, graph.role
    return None


def _role_graph(kl: Any, role: str) -> Optional[Any]:
    for graph in kl.global_metagraph().graphs.values():
        if graph.role == role:
            return graph
    return None


def _capacity_view(cl: Any) -> Any:
    from mindsos_capacity.views import CapacityLayerView

    return CapacityLayerView(cl.global_metagraph())


def _check_atomic(view: Any, iri: str) -> CheckResult:
    outs = view.outputs_of(iri)
    ins = view.inputs_of(iri)
    if not outs:
        return CheckResult(
            1, "atomic-pipeline", MALFORMED, DEFECT,
            "capacity has no PRODUCES edge (not an atomic pipeline)", iri,
        )
    return CheckResult(
        1, "atomic-pipeline", PRESENT, INFO,
        f"consumes={len(ins)} produces={len(outs)}", iri,
    )


def _check_dangling(view: Any, iri: str) -> CheckResult:
    referenced = list(view.inputs_of(iri)) + list(view.outputs_of(iri))
    unregistered = [d for d in referenced if view.get_datastate(d) is None]
    if unregistered:
        return CheckResult(
            2, "dangling-edge", MISSING, DEFECT,
            "edges to unregistered DataStates: " + ", ".join(sorted(set(unregistered))),
            iri,
        )
    return CheckResult(
        2, "dangling-edge", OK, INFO, "all referenced DataStates registered", iri,
    )


def _check_drift(kl: Any, view: Any, roster: Dict[str, Any], prefix: str) -> List[CheckResult]:
    results: List[CheckResult] = []
    for iri in roster.get("l3_capacities") or []:
        if view.get_capacity(iri) is None:
            results.append(CheckResult(
                3, "drift-forward-l3", MISSING, DEFECT,
                "declared L3 capacity absent from reactivated state", iri,
            ))
    for iri in roster.get("l3_datastates") or []:
        if view.get_datastate(iri) is None:
            results.append(CheckResult(
                3, "drift-forward-l3", MISSING, DEFECT,
                "declared L3 DataState absent from reactivated state", iri,
            ))
    for iri in roster.get("l2_iris") or []:
        if _l2_node(kl, iri) is None:
            results.append(CheckResult(
                3, "drift-forward-l2", MISSING, DEFECT,
                "declared L2 node absent from persisted state", iri,
            ))
    declared_l2 = set(roster.get("l2_iris") or [])
    for graph in kl.global_metagraph().graphs.values():
        if graph.role is None:
            continue
        for node_id in graph.nodes:
            if node_id.startswith(prefix) and node_id not in declared_l2:
                results.append(CheckResult(
                    3, "drift-reverse-l2", PRESENT, WARN,
                    "bundle-prefixed L2 node present but undeclared", node_id,
                ))
    if not results:
        results.append(CheckResult(
            3, "drift", OK, INFO, "manifest roster matches state (forward)", "",
        ))
    return results


def _check_broken_refs(kl: Any, view: Any) -> List[CheckResult]:
    from mindsos_knowledge import ROLE_PROMOTED_PIPELINES, ROLE_TASK_PATTERNS

    results: List[CheckResult] = []
    tp = _role_graph(kl, ROLE_TASK_PATTERNS)
    if tp is not None:
        for node in tp.nodes.values():
            ref = node.properties.get("sufficient_predicate_iri")
            if isinstance(ref, str) and ref.startswith("capacity:") and view.get_capacity(ref) is None:
                results.append(CheckResult(
                    4, "broken-ref", MISSING, DEFECT,
                    f"task-pattern predicate -> absent capacity {ref}", node.node_id,
                ))
    pp = _role_graph(kl, ROLE_PROMOTED_PIPELINES)
    if pp is not None:
        for node in pp.nodes.values():
            ref = node.properties.get("capacity_iri")
            if isinstance(ref, str) and view.get_capacity(ref) is None:
                results.append(CheckResult(
                    4, "broken-ref", MISSING, DEFECT,
                    f"pipeline step -> absent capacity {ref}", node.node_id,
                ))
    if not results:
        results.append(CheckResult(
            4, "broken-ref", OK, INFO, "no broken L2->L3 references", "",
        ))
    return results


def _paired_pipelines(node: Any) -> List[str]:
    paired = node.properties.get("paired_pipelines")
    if isinstance(paired, str):
        try:
            paired = json.loads(paired)
        except Exception:
            return []
    if isinstance(paired, (list, tuple)):
        return [str(p) for p in paired]
    return []


def _pipeline_mapped_capacities(kl: Any) -> set:
    from mindsos_knowledge import ROLE_PROMOTED_PIPELINES, ROLE_TASK_PATTERNS
    from mindsos_knowledge.schemas.promoted_pipelines import EDGE_HAS_STEP

    tp = _role_graph(kl, ROLE_TASK_PATTERNS)
    pp = _role_graph(kl, ROLE_PROMOTED_PIPELINES)
    mapped: set = set()
    if tp is None or pp is None:
        return mapped

    referenced: set = set()
    for node in tp.nodes.values():
        referenced.update(_paired_pipelines(node))

    for edge in pp.iter_edges():
        if edge.type_name != EDGE_HAS_STEP or edge.source.node_id not in referenced:
            continue
        step = pp.nodes.get(edge.target.node_id)
        if step is None:
            continue
        capacity = step.properties.get("capacity_iri")
        if isinstance(capacity, str):
            mapped.add(capacity)
    return mapped


def _check_chain(kl: Any, roster: Dict[str, Any]) -> List[CheckResult]:
    from mindsos_knowledge import ROLE_TASK_PATTERNS

    tp = _role_graph(kl, ROLE_TASK_PATTERNS)
    predicates: set = set()
    if tp is not None:
        for node in tp.nodes.values():
            ref = node.properties.get("sufficient_predicate_iri")
            if isinstance(ref, str):
                predicates.add(ref)
    pipeline_mapped = _pipeline_mapped_capacities(kl)

    results: List[CheckResult] = []
    for iri in roster.get("l3_capacities") or []:
        if iri in predicates:
            mapped = "direct-predicate"
        elif iri in pipeline_mapped:
            mapped = "pipeline"
        else:
            mapped = "none"
        results.append(CheckResult(
            5, "task-chain", PRESENT, NEUTRAL, f"mapped: {mapped}", iri,
        ))
    return results


def _check_schema(kl: Any, roster: Dict[str, Any]) -> List[CheckResult]:
    from mindsos_knowledge.schemas import schema_for_role

    results: List[CheckResult] = []
    for iri in roster.get("l2_iris") or []:
        found = _l2_node(kl, iri)
        if found is None:
            continue
        node, role = found
        if role is None:
            continue
        try:
            schema = schema_for_role(role, strict=True)
            schema.validate_node_properties(node.type_name, dict(node.properties))
            results.append(CheckResult(
                6, "schema", OK, INFO, f"conforms to '{role}' schema", iri,
            ))
        except Exception as exc:
            results.append(CheckResult(
                6, "schema", MALFORMED, DEFECT,
                f"{type(exc).__name__}: {exc}", iri,
            ))
    return results


def _scan_module_roles(module_name: str) -> List[Tuple[str, str]]:
    module = importlib.import_module(module_name)
    path = getattr(module, "__file__", None)
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    hits: List[Tuple[str, str]] = []
    func_stack: List[bool] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            func_stack.append(True)
            self.generic_visit(node)
            func_stack.pop()

        def visit_Name(self, node: ast.Name) -> None:
            if node.id.startswith("ROLE_"):
                confidence = "high" if func_stack else "low"
                hits.append((node.id, confidence))
            self.generic_visit(node)

    Visitor().visit(tree)
    return hits


def _check_code_roles(roster: Dict[str, Any]) -> List[CheckResult]:
    results: List[CheckResult] = []
    modules = set()
    for spec in roster.get("l3_installers") or []:
        modules.add(spec.split(":", 1)[0])
    for module_name in sorted(modules):
        try:
            hits = _scan_module_roles(module_name)
        except Exception as exc:
            results.append(CheckResult(
                7, "code-role", MALFORMED, INFO,
                f"scan failed: {type(exc).__name__}", module_name,
            ))
            continue
        if not hits:
            results.append(CheckResult(
                7, "code-role", OK, INFO, "no ROLE_* references", module_name,
            ))
            continue
        for role_name, confidence in hits:
            results.append(CheckResult(
                7, "code-role", PRESENT, INFO,
                f"{role_name} ({confidence} confidence)", module_name,
            ))
    return results


def verify_bundle(kl: Any, cl: Any, bundle_name: str) -> VerifyReport:
    from mindsos_server.skills import latest_records_by_bundle

    report = VerifyReport(bundle_name=bundle_name)
    latest = latest_records_by_bundle(kl)
    record = latest.get(bundle_name)
    if record is None:
        report.notes.append("bundle has no install record")
        return report

    report.found = True
    report.bundle_version = record.bundle_version
    report.bundle_status = record.status
    roster = _roster(record)
    prefix = f"{record.bundle_name}-{record.bundle_version}:"
    view = _capacity_view(cl)

    present_caps = [
        iri for iri in (roster.get("l3_capacities") or [])
        if view.get_capacity(iri) is not None
    ]
    for iri in present_caps:
        report.stored.append(_check_atomic(view, iri))
        report.stored.append(_check_dangling(view, iri))
    report.stored.extend(_check_drift(kl, view, roster, prefix))
    report.stored.extend(_check_broken_refs(kl, view))
    report.stored.extend(_check_chain(kl, roster))
    report.stored.extend(_check_schema(kl, roster))
    report.code_derived.extend(_check_code_roles(roster))

    report.notes.append("reverse-L3 drift undetectable (bundle attribution via manifest [l3]); see design note §6")
    chain = [r for r in report.stored if r.check == 5]
    report.metrics = {
        "broken_atomic": len([r for r in report.stored if r.check == 1 and r.severity == DEFECT]),
        "task_unmapped": len([r for r in chain if r.detail.endswith("none")]),
        "task_total": len(chain),
        "code_scan_hits": len([r for r in report.code_derived if r.status == PRESENT]),
    }
    return report


def verify_all(kl: Any, cl: Any) -> List[VerifyReport]:
    from mindsos_server.skills import latest_records_by_bundle

    names = sorted(latest_records_by_bundle(kl).keys())
    return [verify_bundle(kl, cl, name) for name in names]


def render_json(report: VerifyReport) -> Dict[str, Any]:
    def rows(items: List[CheckResult]) -> List[Dict[str, Any]]:
        return [
            {
                "check": r.check, "name": r.name, "subject": r.subject,
                "status": r.status, "severity": r.severity, "detail": r.detail,
            }
            for r in items
        ]

    return {
        "bundle": report.bundle_name,
        "version": report.bundle_version,
        "bundle_status": report.bundle_status,
        "found": report.found,
        "ok": report.ok(),
        "stored_links": rows(report.stored),
        "code_derived_links": rows(report.code_derived),
        "metrics": report.metrics,
        "notes": report.notes,
    }


def render_human(report: VerifyReport) -> str:
    lines: List[str] = []
    header = f"skill verify: {report.bundle_name}"
    if report.found:
        header += f"@{report.bundle_version} [{report.bundle_status}]"
    lines.append(header)
    if not report.found:
        lines.append("  not installed — " + "; ".join(report.notes))
        return "\n".join(lines)

    lines.append("  exact stored links (graph-queried):")
    for r in report.stored:
        subject = f" {r.subject}" if r.subject else ""
        lines.append(f"    [{r.severity}] check {r.check} {r.name}{subject}: {r.detail}")
    lines.append("  code-derived links (static, may be incomplete):")
    for r in report.code_derived:
        subject = f" {r.subject}" if r.subject else ""
        lines.append(f"    [{r.severity}] check {r.check} {r.name}{subject}: {r.detail}")
    lines.append("  rollup:")
    for key, value in report.metrics.items():
        lines.append(f"    {key} = {value}")
    for note in report.notes:
        lines.append(f"  note: {note}")
    verdict = "OK" if report.ok() else f"{len(report.defects())} DEFECT(s)"
    lines.append(f"  verdict: {verdict}")
    return "\n".join(lines)
