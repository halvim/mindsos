"""``capacity:comprehension:record_reading_set`` — give a recorded set its home in L2.

``mindsos_llm`` plan item **I-10**. Rulings **R1** (L3 writes the L2 record),
**R3** (family ``comprehension``), **R4** (L4 decides when a record is needed),
**R5** (it consumes what was produced and never builds a client), **R7** (it
declares that it writes), **R8**–**R10**, **R12**–**R18**; shape recorded as
ADR-0210 amendments 4 and 6.

**What it does.** Given the path of a recorded-set file, it asks
``mindsos_llm.recorded_sets.describe_set`` what the file IS, then appends a
pointer to the user's Local ``recorded-sets`` role and RETURNS the pointer's IRI
as its declared output — so the run graph names the set, which is the reason
amendment 4 rejected an L0 writer.

⚠ **This capacity reads no file itself.** ``describe_set`` reads it once, hashes
those bytes, and derives the rest from them (R13). The body touches no
filesystem API, and neither does any other module in ``mindsos_capacity``.

⚠ **It consults no model.** It never reaches ``context.llm``, so
``EXPECTED_EXTERNAL_CLIENT_CONSUMERS`` stays at its one entry (R5): a
bookkeeping step must not inherit a model call's failure modes. A recorded set's
payloads ARE the answers a client stamped at capture; recording them is not
asking again.

**No don't-know** (R10). A file that is not a recorded set REFUSES, with the
reason in the exception; ``runtime.invoke`` carries it to the problem trace when
a sink and a ``request_id`` are present.

**Realm: always ``scope="local"``.** Recorded sets are never Global (plan §4).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, List

from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..identifiers import CATEGORY_COMPREHENSION, capacity_iri, datastate_iri


# ── DataState IRIs ─────────────────────────────────────────────────────

DS_READING_SET_RECORD = datastate_iri("core.reading_set_record")
DS_RECORDED_SET_POINTER = datastate_iri("core.recorded_set_pointer")


def recorded_set_datastates() -> List[DataState]:
    """The input record and the output pointer DataStates.

    Input keys (ADR-0210 am-4, am-6): ``set_path`` (str), ``recorded_by``
    (str); optional ``note`` (str), read defensively in the body.
    ⚠ ``credential_level`` is NOT an input (R15): it is derived from the
    payloads, and a supplied value beside a derived one is a claim.
    """
    return [
        DataState(
            name="core.reading_set_record",
            shape=ShapeDescriptor.record(
                {"set_path": "str", "recorded_by": "str"},
                opaque_tag="core.reading_set_record",
            ),
            description=(
                "Record naming one recorded-set FILE to give a home in the "
                "user's Local recorded-sets role: set_path is the file (a bare "
                "recording or an export), recorded_by the actor; note optional."
            ),
            provenance_category=CATEGORY_COMPREHENSION,
        ),
        DataState(
            name="core.recorded_set_pointer",
            shape=ShapeDescriptor.scalar(
                "str", opaque_tag="core.recorded_set_pointer"
            ),
            description=(
                "IRI of the RecordedSet pointer node, "
                "recorded-sets-<v>:set:<sha256> - the identity is the file's "
                "hash, so the pointer is verifiable against the file it names."
            ),
            provenance_category=CATEGORY_COMPREHENSION,
        ),
    ]


# ── Capacity body ──────────────────────────────────────────────────────


def _now_iso() -> str:
    """ISO-8601 UTC millisecond timestamp — the ``learn_parameter`` spelling."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _record_reading_set_impl(**kwargs: Any) -> Any:
    """Body of ``capacity:comprehension:record_reading_set`` (ADR-0180).

    Obtains its :class:`KLWriteHandle` from the **pre-authorized**
    ``context.writeable`` capability; holds no session, makes no
    authorization decision. Returns the pointer IRI (the declared output).
    """
    from mindsos_knowledge.identifiers import ROLE_RECORDED_SETS
    from mindsos_knowledge.recorded_sets import write_recorded_set
    from mindsos_llm.recorded_sets import describe_set

    from ..exceptions import WriteHandleNotWiredError

    context = kwargs.get("context")
    writeable = getattr(context, "writeable", None)
    if writeable is None:
        raise WriteHandleNotWiredError(
            "capacity:comprehension:record_reading_set requires a CapacityContext "
            "carrying a pre-authorized `writeable` capability (ADR-0180). It "
            "declares writes=True (plan R7), so both invoke sites inject one."
        )

    rec = kwargs[DS_READING_SET_RECORD]
    description = describe_set(str(rec["set_path"]))
    handle = writeable(role=ROLE_RECORDED_SETS, scope="local", version="v1")
    result = write_recorded_set(
        handle,
        description=description,
        recorded_by=str(rec["recorded_by"]),
        recorded_at=_now_iso(),
        note=rec.get("note"),
    )
    return result.iri


# ── Capacity factory ───────────────────────────────────────────────────


def build_record_reading_set() -> Capacity:
    """Build the ``capacity:comprehension:record_reading_set`` declaration."""
    return Capacity(
        name="record_reading_set",
        category=CATEGORY_COMPREHENSION,
        inputs=(DS_READING_SET_RECORD,),
        outputs=(DS_RECORDED_SET_POINTER,),
        writes=True,
        implementation=_record_reading_set_impl,
        description=(
            "Give a recorded-set file a home in the user's Local recorded-sets "
            "role: derive what the file is from its bytes, append a pointer "
            "whose identity is the file's sha256, and return the pointer's IRI. "
            "Refuses a file that is not a recorded set, and a re-capture of the "
            "same bytes."
        ),
        cost_prior=2.0,
        latency_ms_prior=5.0,
    )


# ── Idempotent installer (I-16's class guard requires it) ─────────────


_RECORD_READING_SET_IRI = capacity_iri(CATEGORY_COMPREHENSION, "record_reading_set")
_DS_IRIS = (DS_READING_SET_RECORD, DS_RECORDED_SET_POINTER)
_CAP_IRIS = (_RECORD_READING_SET_IRI,)
_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_recorded_set_capacities(capacity_layer) -> None:
    """Register the recorder's two DataStates and the capacity, idempotently.

    The ``install_prompt_edition_capacities`` shape: targets the Global
    registry; the WRITE targets Local at invoke time through the
    ``scope="local"`` handle.

    Raises:
        CapacityRegistrationError: partial install state detected.
    """
    from ..bootstrap import ensure_datastate_graph
    from ..exceptions import CapacityRegistrationError

    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_FAMILY_IRIS):
        return
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_recorded_set_capacities: partial install state - "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}, "
            f"missing={sorted(set(_FAMILY_IRIS) - ds_present - cap_present)}"
        )
    for ds in recorded_set_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_record_reading_set())


__all__ = [
    "DS_READING_SET_RECORD",
    "DS_RECORDED_SET_POINTER",
    "build_record_reading_set",
    "install_recorded_set_capacities",
    "recorded_set_datastates",
]
