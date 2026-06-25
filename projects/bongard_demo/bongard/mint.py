"""Teach-triggered Local shape-mint (PLAN §7, m2, option A).

A minted shape is a small composite **over the parse**: it consumes a
``SHAPE`` and runs ``extract_shape_atoms → matches_definition`` against a
stored ``ShapeDefinition`` (PLAN §2 "a concept = a predicate over the
parse"). Perception is shared infrastructure, run once; each minted shape
is a tiny test on top of it.

The durable unit is a ``learned-parameters`` descriptor carrying the
serialized ``COMPOSITE_DAG``, the induced definition, and the calibration
params (PB-9 — restart restores the exact capacity). A reactivation
factory rebuilds the runner at boot and injects the stored definition into
the ``matches`` step; the executor closure is re-supplied per process (the
F9 pattern), never serialized.

Recognition lives entirely in registered ``[SYSTEM]`` capacities (PB-10);
the only human input is the **name**, supplied at teach time (m2 is
Local-only — no Local→Global promotion yet).

Pure-``mindsos_capacity`` helpers import at module top; the durable
functions (KL / persister / server) lazy-import inside so this module is
importable without the server layer.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, List

from mindsos_capacity import (
    COMPOSITE_DAG,
    Capacity,
    DAGEdge,
    DAGStep,
    Pipeline,
    REACTIVATION_KEY,
    register_reactivation_factory,
)
from mindsos_capacity.identifiers import CATEGORY_PREDICATE
from mindsos_capacity.pipeline import START

from .calibration import Params
from .ontology import SHAPE
from .shapes import (
    ATOMS,
    ATOMS_SET,
    DEFINITION_MATCH,
    EXTRACT_IRI,
    INDUCE_IRI,
    MATCHES_IRI,
    SHAPE_DEFINITION,
    ShapeDefinition,
)

SHAPE_REACTIVATION_KEY = "bongard_shape"


def _definition_to_dict(d: ShapeDefinition) -> dict:
    return {"n": d.n, "target_angle": d.target_angle,
            "side_tol": d.side_tol, "angle_tol": d.angle_tol}


def _definition_from_dict(d: dict) -> ShapeDefinition:
    return ShapeDefinition(n=d["n"], target_angle=d["target_angle"],
                           side_tol=d["side_tol"], angle_tol=d["angle_tol"])


def shape_pipeline() -> Pipeline:
    """The minted composite: SHAPE → extract → matches[definition] → bool.

    ``SHAPE_DEFINITION`` is a start datastate the runner seeds from the
    stored definition (not a caller input), so the minted node's only
    declared input is ``SHAPE``."""
    return Pipeline(
        start_datastates=(SHAPE.iri, SHAPE_DEFINITION.iri),
        target_datastate=DEFINITION_MATCH.iri,
        steps=(
            DAGStep(EXTRACT_IRI, (SHAPE.iri,), (ATOMS.iri,)),
            DAGStep(MATCHES_IRI, (ATOMS.iri, SHAPE_DEFINITION.iri), (DEFINITION_MATCH.iri,)),
        ),
        edges=(
            DAGEdge(START, 0, SHAPE.iri),
            DAGEdge(0, 1, ATOMS.iri),
            DAGEdge(START, 1, SHAPE_DEFINITION.iri),
        ),
    )


def shape_descriptor(name: str, definition: ShapeDefinition, params: Params) -> dict:
    """The durable ``learned-parameters`` value dict for a minted shape."""
    return {
        "capability": name,
        REACTIVATION_KEY: SHAPE_REACTIVATION_KEY,
        "category": CATEGORY_PREDICATE,
        "inputs": [SHAPE.iri],
        "outputs": [DEFINITION_MATCH.iri],
        "node_kind": "reactive",
        COMPOSITE_DAG: shape_pipeline().to_dict(),
        "definition": _definition_to_dict(definition),
        "params": asdict(params),
    }


def shape_reactivation_factory(cl):
    """Rebuild a minted shape node, binding a runner that walks the stored
    DAG via ``cl.invoke`` and seeds the definition from the descriptor."""
    def factory(desc):
        pipeline = Pipeline.from_dict(desc[COMPOSITE_DAG])
        definition = _definition_from_dict(desc["definition"])
        in_iri = desc["inputs"][0]
        out_iri = desc["outputs"][0]

        def run(**kw):
            ctx = kw.get("context") or {}
            session = ctx.get("session")
            values = {in_iri: kw[in_iri], SHAPE_DEFINITION.iri: definition}
            for step in pipeline.steps:
                inputs = {ds: values[ds] for ds in step.input_datastates}
                result = cl.invoke(step.capacity_iri, inputs, session=session)
                if not result.success:
                    raise result.error
                values.update(result.outputs)
            return {out_iri: values[pipeline.target_datastate]}

        return Capacity(
            name=desc["capability"], category=desc["category"],
            inputs=tuple(desc["inputs"]), outputs=tuple(desc["outputs"]),
            implementation=run,
        )

    return factory


def register_shape_reactivation(cl) -> None:
    """Register the shape reactivation factory (idempotent)."""
    register_reactivation_factory(
        SHAPE_REACTIVATION_KEY, shape_reactivation_factory(cl), if_exists="upsert"
    )


def induce_from_examples(solver, example_samples: List[Any]) -> ShapeDefinition:
    """Perceive the teach examples, extract atoms, induce the definition —
    all through ``cl.invoke`` (recognition stays in capabilities)."""
    atoms_list = []
    for sample in example_samples:
        v = solver.perceive(sample)
        if not v.solved:
            raise ValueError(f"teach example did not parse: {sample.name} ({v.reason})")
        out = solver.cl.invoke(EXTRACT_IRI, {SHAPE.iri: v.shape}, session=solver.session)
        atoms_list.append(out.outputs[ATOMS.iri])
    return solver.cl.invoke(
        INDUCE_IRI, {ATOMS_SET.iri: atoms_list}, session=solver.session,
    ).outputs[SHAPE_DEFINITION.iri]


def mint_shape(solver, kl, persister, name: str, example_samples: List[Any]) -> str:
    """Teach-mint a named shape Local + persist it (durable; restart-safe).

    Perceive examples → induce the definition → write the descriptor into
    the user's Local ``learned-parameters`` → persist → register the node
    now (usable immediately). Returns the minted capability IRI.
    """
    from mindsos_knowledge import (
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

    definition = induce_from_examples(solver, example_samples)
    descriptor = shape_descriptor(name, definition, solver.params)

    user_id = solver.session.user_id
    local_mg = kl.local_metagraph(user_id)
    g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    g.add_node(
        dict(descriptor), NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": f"taught:{name}", "confidence": 1.0},
        node_id=learned_parameter_iri("v1", name),
    )
    persister.save(user_id, local_mg)

    register_shape_reactivation(solver.cl)
    decl = shape_reactivation_factory(solver.cl)(descriptor)
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")
    return decl.iri
