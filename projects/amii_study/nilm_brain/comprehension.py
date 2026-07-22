"""Comprehension + predicate families — the acquisition path (§6 / #2).

These serve declared-vs-induced structure acquisition, not the cycle
recognition. They are registered (the user asked for the whole doc registry in
the brain) with real-but-minimal bodies; they do not compose into the cycle
pipeline. `induce_structure` (its counterpart) lives in derivation.py.

- comprehension `bind_declaration`: a human-authored DAG -> bound | request.
  (comprehension resolves to the DATASTATE_MARKER don't-know default.)
- predicate `compare`: two shapes -> equal? (predicate = NO_DONT_KNOW, hard bool).
- predicate `compare_structures`: declared vs induced -> agreement.
"""

from __future__ import annotations

from mindsos_capacity import Capacity, CATEGORY_COMPREHENSION
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from .ontology import (
    DECLARED_STRUCTURE, BOUND_DECLARATION, SHAPE, COMPARISON,
    INDUCED_STRUCTURE, STRUCTURE_AGREEMENT,
)


def _bind_declaration(**kw):
    decl = kw[DECLARED_STRUCTURE.iri]
    # A declared structure is a DAG {nodes, edges}. Well-formed -> bound;
    # otherwise the honest failure is a request for a usable declaration.
    ok = isinstance(decl, dict) and "nodes" in decl and "edges" in decl
    if ok:
        return {BOUND_DECLARATION.iri: {"status": "bound", "declaration": decl}}
    return {BOUND_DECLARATION.iri: {"status": "request",
                                    "detail": "declared_structure is not a {nodes, edges} DAG"}}


def _compare(**kw):
    a, b = kw[SHAPE.iri]          # operand_arity 2 -> a length-2 list
    return {COMPARISON.iri: bool(a == b)}


def _compare_structures(**kw):
    declared = kw[DECLARED_STRUCTURE.iri]
    induced = kw[INDUCED_STRUCTURE.iri]
    d_nodes = set(declared.get("nodes", [])) if isinstance(declared, dict) else set()
    i_nodes = set(induced.get("nodes", [])) if isinstance(induced, dict) else set()
    inter = len(d_nodes & i_nodes)
    union = len(d_nodes | i_nodes) or 1
    return {STRUCTURE_AGREEMENT.iri: {"agreement": inter / union,
                                      "declared_only": sorted(d_nodes - i_nodes),
                                      "induced_only": sorted(i_nodes - d_nodes)}}


def register_comprehension(cl, session):
    caps = [
        Capacity(name="bind_declaration", category=CATEGORY_COMPREHENSION,
                 inputs=(DECLARED_STRUCTURE.iri,), outputs=(BOUND_DECLARATION.iri,),
                 implementation=_bind_declaration,
                 description="declared_structure -> bound | request"),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]


def register_predicate(cl, session):
    caps = [
        Capacity(name="compare", category=CATEGORY_PREDICATE, inputs=(SHAPE.iri,),
                 outputs=(COMPARISON.iri,), operand_arity={SHAPE.iri: 2},
                 implementation=_compare, description="two shapes -> equal?"),
        Capacity(name="compare_structures", category=CATEGORY_PREDICATE,
                 inputs=(DECLARED_STRUCTURE.iri, INDUCED_STRUCTURE.iri),
                 outputs=(STRUCTURE_AGREEMENT.iri,), implementation=_compare_structures,
                 description="declared vs induced -> agreement"),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
