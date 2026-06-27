"""m5 tier-2 DE-RISK — a REFERENCING composite over a minted predicate.

Tier-1 minted ``capacity:predicate:same_shape`` as a durable SCENE->bool
predicate. Tier-2 will compose ``count_eq ∧ same_shape`` over that *persisted*
node (PLAN D-M5-16: the conjunction REFERENCES the invented relation, so the
§14 "an invented relation can be consumed by a higher tier" claim is
load-bearing — the higher concept points at the lower minted node, it does not
re-derive it).

The new restart risk that tier-1 never exercised: a composite whose
``COMPOSITE_DAG`` names *another minted node's* capacity IRI must reactivate
**after** that node at ``boot_local``. This module is the minimal backbone
that isolates exactly that risk (one referenced operand — the invented
``same_shape`` — is enough to prove dep-ordered reactivation; tier-2 adds the
taught ``count_eq`` as a second operand):

* a composite = AND over a list of *referenced* SCENE->bool predicate IRIs;
* its ``COMPOSITE_DAG`` names each referenced IRI as a step, so
  :func:`mindsos_capacity.composite_dependencies` returns them and
  ``mindsos_server.local_boot._dep_order_descriptors`` reactivates the
  operands first (the data + order halves of F9 dep-ordered boot);
* durable mint + restart reuses the m2 / tier-1 path verbatim (a
  ``learned-parameters`` descriptor + a reactivation factory + ``boot_local``).

Forward-compatible with tier-2 (``operands`` is a list); the de-risk wires a
single operand so the serialized DAG is the gate-proven single-step shape of
tier-1's ``relation_pipeline``. No ``mindsos_*`` edits; pin unchanged.
"""

from __future__ import annotations

from typing import List

from mindsos_capacity import (
    COMPOSITE_DAG,
    Capacity,
    DAGEdge,
    DAGStep,
    DataState,
    Pipeline,
    REACTIVATION_KEY,
    ShapeDescriptor,
    register_reactivation_factory,
)
from mindsos_capacity.identifiers import CATEGORY_PREDICATE
from mindsos_capacity.pipeline import START

from .ontology import BONGARD_REALM, SCENE


COMPOSITE_REACTIVATION_KEY = "bongard_composite"


def _ds(suffix: str) -> DataState:
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


#: the bool verdict a reactivated composite predicate produces.
COMPOSITE_VERDICT = _ds("composite_verdict")


def composite_pipeline(operands: List[str]) -> Pipeline:
    """Declarative body: SCENE -> (invoke each referenced predicate) -> AND.

    Each operand IRI is named as a step so ``composite_dependencies`` returns
    it (the *data* half of dep-ordered boot); the AND runner is supplied by
    the boot closure (the F9 pattern), the DAG records the shape for audit.
    With one operand this is byte-for-byte tier-1's gate-proven single-step
    ``relation_pipeline`` shape.
    """
    steps = tuple(
        DAGStep(ir, (SCENE.iri,), (COMPOSITE_VERDICT.iri,)) for ir in operands
    )
    edges = tuple(DAGEdge(START, i, SCENE.iri) for i in range(len(operands)))
    return Pipeline(
        start_datastates=(SCENE.iri,),
        target_datastate=COMPOSITE_VERDICT.iri,
        steps=steps,
        edges=edges,
    )


def composite_descriptor(name: str, operands: List[str]) -> dict:
    """The durable ``learned-parameters`` value dict for a referencing composite."""
    return {
        "capability": name,
        REACTIVATION_KEY: COMPOSITE_REACTIVATION_KEY,
        "category": CATEGORY_PREDICATE,
        "inputs": [SCENE.iri],
        "outputs": [COMPOSITE_VERDICT.iri],
        "node_kind": "reactive",
        COMPOSITE_DAG: composite_pipeline(list(operands)).to_dict(),
        "operands": list(operands),
    }


def composite_reactivation_factory(cl):
    """Rebuild a composite predicate: SCENE -> invoke each referenced operand
    IRI -> AND their bool verdicts. The referenced operands are themselves
    reactivated nodes (dep-ordered boot guarantees they are registered first)."""
    def factory(desc):
        operands = list(desc["operands"])
        out_iri = desc["outputs"][0]

        def run(**kw):
            ctx = kw.get("context") or {}
            session = ctx.get("session")
            scene = kw[SCENE.iri]
            verdict = True
            for ir in operands:
                r = cl.invoke(ir, {SCENE.iri: scene}, session=session)
                if not r.success:
                    raise r.error
                verdict = verdict and bool(next(iter(r.outputs.values())))
            return {out_iri: verdict}

        return Capacity(
            name=desc["capability"], category=desc["category"],
            inputs=tuple(desc["inputs"]), outputs=tuple(desc["outputs"]),
            implementation=run,
        )

    return factory


def register_composite_reactivation(cl) -> None:
    """Register the composite reactivation factory (idempotent)."""
    register_reactivation_factory(
        COMPOSITE_REACTIVATION_KEY, composite_reactivation_factory(cl),
        if_exists="upsert",
    )


def register_composite_datastates(cl, session) -> None:
    """Register the composite output DataState (must run at boot before
    ``boot_local`` reactivates, exactly like tier-1's
    ``register_relation_datastates`` registers ``RELATION_VERDICT``).
    Idempotent so the boot path and the mint path can both call it."""
    from mindsos_capacity.exceptions import CapacityRegistrationError
    try:
        cl.register_datastate(COMPOSITE_VERDICT, session=session, allow_new_realm=True)
    except CapacityRegistrationError as e:
        if "already" not in str(e).lower():
            raise


def register_composite(solver, name: str, operands: List[str]) -> str:
    """In-memory register a composite predicate over the referenced operand
    IRIs (usable immediately); returns its capability IRI. Durable persistence
    + cross-process restart is :func:`mint_composite`."""
    register_composite_datastates(solver.cl, solver.session)
    register_composite_reactivation(solver.cl)
    decl = composite_reactivation_factory(solver.cl)(composite_descriptor(name, operands))
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")
    return decl.iri


def mint_composite(solver, kl, persister, name: str, operands: List[str]) -> str:
    """Durably mint a referencing composite Local (restart-safe; the m2 path).

    Writes the composite descriptor into the user's Local ``learned-parameters``
    -> persists -> registers the predicate now. Survives a fresh-process restart
    via ``boot_local`` reactivation, which reactivates the referenced operand
    nodes first (``composite_dependencies`` + ``_dep_order_descriptors``).
    Returns the composite capability IRI.
    """
    from mindsos_knowledge import (
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

    descriptor = composite_descriptor(name, operands)
    user_id = solver.session.user_id
    local_mg = kl.local_metagraph(user_id)
    g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    g.add_node(
        dict(descriptor), NODE_LEARNED_PARAMETER,
        properties={"parameter_set_iri": f"composed:{name}", "confidence": 1.0},
        node_id=learned_parameter_iri("v1", name),
    )
    persister.save(user_id, local_mg)

    register_composite_datastates(solver.cl, solver.session)
    register_composite_reactivation(solver.cl)
    decl = composite_reactivation_factory(solver.cl)(descriptor)
    solver.cl.register_capacity(decl, session=solver.session, if_exists="upsert")
    return decl.iri
