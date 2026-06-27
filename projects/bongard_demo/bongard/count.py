"""Taught count operator (m5 tier-2; PLAN D-M5-8 + D-M5-14 bool refinement).

``count_eq(k): SCENE -> bool`` — the *authored* operand the invented
``same_shape`` composes with. Per the repass (D-M5-14 reversed int->bool), the
count operand is a SCENE->bool predicate, NOT a raw int, so the tier-2
conjunction is a uniform bool-AND over registered capabilities (the
``compose.py`` runner ANDs ``bool(next(iter(outputs.values())))`` over its
referenced operands). The ``count`` operator + the ``==k`` comparator are
authored together inside the capability (the comparator stays in a registered
[SYSTEM] capability, never the demo closure — PB-10).

``count`` is TAUGHT, not assumed: ``register_count`` registers one
``count_eq_k`` predicate per observed ``k`` (params bound from scenes, like
m4's library). The SEARCH (``tier2.discover_conjunction``) discovers *which*
``k`` and that the conjunction with ``same_shape`` is the separator.
"""

from __future__ import annotations

from typing import Iterable, List

from mindsos_capacity import Capacity, DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_PREDICATE

from .ontology import BONGARD_REALM, SCENE


def _ds(suffix: str) -> DataState:
    name = f"{BONGARD_REALM}.{suffix}"
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


#: the bool verdict every count_eq_k predicate produces.
COUNT_VERDICT = _ds("count_verdict")


def count_eq_iri(k: int) -> str:
    return f"capacity:{CATEGORY_PREDICATE}:count_eq_{k}"


def _count_eq_impl(k: int):
    def run(**kw):
        scene = kw[SCENE.iri]
        return {COUNT_VERDICT.iri: len(scene.shapes) == k}
    return run


def register_count_datastates(cl, session) -> None:
    """Register COUNT_VERDICT (idempotent — boot + register paths both call it)."""
    from mindsos_capacity.exceptions import CapacityRegistrationError
    try:
        cl.register_datastate(COUNT_VERDICT, session=session, allow_new_realm=True)
    except CapacityRegistrationError as e:
        if "already" not in str(e).lower():
            raise


def register_count(cl, session, ks: Iterable[int]) -> List[str]:
    """Register ``count_eq_k: SCENE->bool`` for each ``k``. Returns the IRIs."""
    register_count_datastates(cl, session)
    iris: List[str] = []
    for k in ks:
        cap = Capacity(
            name=f"count_eq_{k}", category=CATEGORY_PREDICATE,
            inputs=(SCENE.iri,), outputs=(COUNT_VERDICT.iri,),
            implementation=_count_eq_impl(k),
            description=f"hard verdict: scene has exactly {k} solved figures (taught count operator)",
        )
        cl.register_capacity(cap, session=session, if_exists="upsert")
        iris.append(cap.iri)
    return iris
