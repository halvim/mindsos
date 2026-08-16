"""dr_render_pages — the RULES §12 command for item 7: real runs, a real store, the page.

Per case: run through `execution.run` → consolidate to a REAL FalkorDB
(`consolidate_request`, the production close) → hand `dr_render.render_record`
the Episode's properties and the client — the page is rendered FROM THE STORE
(plan §2.3 decision 5) — → print the page raw between markers.

Cases: claim (3 exposures + fold), refusal (no edition in force — in-band),
outage (store unreachable — RunStopped), boundary (zero exposures — the FOLD
stops pre-dispatch, empty_domain), noroute (unroutable — manifest-only
graph), routing (beat 1: one claim, two desks, by position off the am-5
manifest ids), routingrefusal (beat 2: an in-band member refusal BESIDE
routed siblings, the missing item named from the stored record),
policyprior + policycurrent (beat 4: the same claim asked as of two dates,
naming two editions and two in-force windows — G5's pair), settlement
(beat 3: the claim cannot be settled until a named document arrives).

⚠ The case list above was stated as "five" for three ships while the tree
held seven. It is derived from ``CASES`` by every count that matters (the
loop below), so the prose is the only place it can drift — grep it, do not
trust it.

RULES §11 seam: everything between the BEGIN/END PAGE markers is the
renderer's composed page — layout and framing are `dr_render.py`'s, every fact
on it is a stored graph value, and a gap raises instead of rendering. Text
outside the markers is this driver's narration. ⚠ ONE STATED EXCEPTION
(coordination §51.1): the "Decided <date>" line comes from the Episode, which
lives in the in-process KnowledgeLayer — KL persistence is the server's job
(ADR-0042), so the date is NOT store-resident. The from-root mode below is the
honest form of that limit: it renders with no live KL at all, and the page
STATES the date's absence instead of omitting the line (§52 condition 1).

Modes (combinable where sensible):

  (default)             run every case in ``CASES`` → consolidate → render each FROM
                        THE STORE. Narration prints each case's
                        capacity_root_ref so it can be fed to --from-root.
  --screens <dir>       additionally compose each case's SCREEN (dr_screen:
                        the "what arrived" panel + the styled Record; §78–§80)
                        and write one self-contained HTML file per case. The
                        raw pages between the markers stay the §12 evidence;
                        the screens are what the room sees.
  --from-root <ref>     NO cases are run and NO KnowledgeLayer exists in the
                        process: the page is rendered from the store alone,
                        given only the index graph's id. This is the
                        reconstructibility proof (plan §2.3 decision 5) and a
                        GATE-7 PREDECESSOR by owner ruling (coordination §54)
                        — green before the gate may be attempted, not part of
                        the cold-run set.

Requires a reachable FalkorDB (`FALKORDB_HOST`/`FALKORDB_PORT`); unreachable →
raw error, exit 3. Exit 1 if any render raises. On the Linux box:

    docker run --rm -d --name drdemo-falkor -p 6382:6379 falkordb/falkordb
    PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_render_pages.py
    PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_render_pages.py --from-root <capacity_root_ref>
    docker rm -f drdemo-falkor
"""

from __future__ import annotations

import os
import sys

from mindsos_capacity.context import make_writeable
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_intelligence import execution
from mindsos_intelligence.consolidation import consolidate_request
from mindsos_intelligence.execution import LeafPipelineNotFound
from mindsos_intelligence.mm_persister import FalkorMMPersister
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES

from decision_records_demo.dr_dump import (
    DS_CLAIM_EXPOSURES,
    _build_kl,
    DS_DWELLING_LIMIT,
    DS_EXPOSURE,
    DS_POLICY_AS_OF,
    DS_UNREACHED,
    EDITION_2023,
    EDITION_2024,
    EXPOSURES,
    _claim_plan,
    _leaf_plan,
    _lookup_declaration,
    _policy_datastates,
)
from decision_records_demo.dr_persist_smoke import _harness_with_consolidation
from decision_records_demo.dr_render import RendererGapError, render_record
from decision_records_demo.dr_screen import compare_pages, compose_screen


def _policy_harness(kl, scope):
    """The consolidation harness with the LOOKUP capacity instead of the
    decide/conclude pair (route: as-of date → dwelling limit). ``scope`` must
    be case-unique — node ids derive from it and the store MERGEs nodes
    globally by id (§55)."""
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_capacity.datastate import DataState, ShapeDescriptor
    from mindsos_capacity.identifiers import CATEGORY_DERIVATION
    from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel

    from decision_records_demo.dr_dump import COLLECTIONS, DESCRIPTIONS, _Session

    session = _Session()
    layer = CapacityLayer()
    for name, description in DESCRIPTIONS.items():
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=description,
                provenance_category=CATEGORY_DERIVATION,
                **COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    for datastate in _policy_datastates():
        layer.register_datastate(datastate, session=session, allow_new_realm=True)
    layer.register_capacity(_lookup_declaration(), session=session)
    install_consolidate_capacities(layer)
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, scope)
    return session, kl, mm, dispatcher, writer, writer.emit_request_run()


def _episode_props(kl, session, episode_id: str):
    handle = make_writeable(kl, session)(
        role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1"
    )
    for node in handle.graph().nodes.values():
        if getattr(node, "type_name", None) == "Episode" and node.value == episode_id:
            return dict(node.properties or {})
    raise RuntimeError(f"no Episode node for {episode_id!r}")


def _close(dispatcher, mm, request_run, episode_id, outcome, client, graphs):
    consolidate_request(
        dispatcher, mm, request_run,
        episode_id=episode_id,
        request_pattern_iri=None,
        outcome_classification=outcome,
        mm_persister=FalkorMMPersister(client),
        capacity_graphs=graphs,
    )


def _case_claim(client):
    session, kl, mm, dispatcher, writer, request_run = _harness_with_consolidation(scope="drdemo-page-claim")
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs, case_label="claim CLM-2041",
    )
    _close(dispatcher, mm, request_run, "drdemo-page-claim", "completed", client, graphs)
    return kl, session, "drdemo-page-claim"


def _case_boundary(client):
    session, kl, mm, dispatcher, writer, request_run = _harness_with_consolidation(scope="drdemo-page-boundary")
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: []},
        capacity_graphs=graphs, case_label="claim CLM-2041 (no exposures filed)",
    )
    _close(dispatcher, mm, request_run, "drdemo-page-boundary", "stopped", client, graphs)
    return kl, session, "drdemo-page-boundary"


def _case_refusal(client):
    session, kl, mm, dispatcher, writer, request_run = _policy_harness(
        _build_kl(EDITION_2023), scope="drdemo-page-refusal"
    )
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-refusal", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
        request_run, mm=mm,
        solve_seed={DS_POLICY_AS_OF: "2026-07-01"},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, dwelling limit as of 2026-07-01",
    )
    _close(dispatcher, mm, request_run, "drdemo-page-refusal", "completed", client, graphs)
    return kl, session, "drdemo-page-refusal"


class _StoreDownKL:
    """A KL whose READ side is down while Episode writes still land — the
    outage under test is the POLICY store's, not the Episode store's (the
    first cut passed kl=None and killed both; caught on the owner's run)."""

    def __init__(self, real):
        self._real = real

    def writeable(self, *args, **kwargs):
        return self._real.writeable(*args, **kwargs)

    def global_view(self):
        raise RuntimeError("simulated outage: the policy store cannot be read")


def _policy_case(client, scope, as_of):
    """One dated policy question against a store holding BOTH editions.

    Beat 4's pair differ in the as-of date and in nothing else — same claim,
    same plan, same store — so a difference between the two pages can only
    have come from the date.
    """
    session, kl, mm, dispatcher, writer, request_run = _policy_harness(
        _build_kl(EDITION_2023, EDITION_2024), scope=scope
    )
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan(f"plan:{scope}", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
        request_run, mm=mm,
        solve_seed={DS_POLICY_AS_OF: as_of},
        capacity_graphs=graphs,
        case_label=f"claim CLM-4188, dwelling limit as of {as_of}",
    )
    _close(dispatcher, mm, request_run, scope, "completed", client, graphs)
    return kl, session, scope


def _case_policy_prior(client):
    """Submitted under the 2023 edition — 350,000, a window that has closed."""
    return _policy_case(client, "drdemo-page-policyprior", "2023-06-01")


def _case_policy_current(client):
    """Assessed under the 2024 edition — 375,000, still open."""
    return _policy_case(client, "drdemo-page-policycurrent", "2024-06-01")


def _case_outage(client):
    session, kl, mm, dispatcher, writer, request_run = _policy_harness(
        _StoreDownKL(_build_kl()), scope="drdemo-page-outage"
    )
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-outage", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
        request_run, mm=mm,
        solve_seed={DS_POLICY_AS_OF: "2026-07-01"},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, dwelling limit as of 2026-07-01",
    )
    _close(dispatcher, mm, request_run, "drdemo-page-outage", "stopped", client, graphs)
    return kl, session, "drdemo-page-outage"


def _case_noroute(client):
    session, kl, mm, dispatcher, writer, request_run = _harness_with_consolidation(scope="drdemo-page-noroute")
    graphs: list = []
    try:
        execution.run(
            dispatcher, writer,
            _leaf_plan("plan:drdemo-noroute", DS_UNREACHED, start=DS_EXPOSURE),
            request_run, mm=mm,
            solve_seed={DS_EXPOSURE: EXPOSURES[0]},
            capacity_graphs=graphs,
            case_label="claim CLM-2041, unroutable ask",
        )
    except LeafPipelineNotFound:
        pass
    _close(dispatcher, mm, request_run, "drdemo-page-noroute", "stopped", client, graphs)
    return kl, session, "drdemo-page-noroute"


def _routing_page_harness(scope):
    """The routing-content harness (dr_routing) + the consolidate builtin +
    a KL — the beat-1/2 cases through the same production close as every
    other case. ``scope`` case-unique (§55)."""
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer

    from decision_records_demo.dr_dump import _Session
    from decision_records_demo.dr_routing import (
        routing_capacities,
        routing_datastates,
    )

    session = _Session()
    layer = CapacityLayer()
    for ds in routing_datastates():
        layer.register_datastate(ds, session=session, allow_new_realm=True)
    for cap in routing_capacities():
        layer.register_capacity(cap, session=session)
    install_consolidate_capacities(layer)
    kl = KnowledgeLayer.bootstrap()
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, scope)
    return session, kl, mm, dispatcher, writer, writer.emit_request_run()


def _run_routing_case(client, scope, exposures, label):
    from decision_records_demo.dr_routing import (
        DS_CLAIM_EXPOSURES as DS_ROUTED_EXPOSURES,
        routing_plan,
    )

    session, kl, mm, dispatcher, writer, request_run = _routing_page_harness(scope)
    graphs: list = []
    execution.run(
        dispatcher, writer, routing_plan(), request_run, mm=mm,
        solve_seed={DS_ROUTED_EXPOSURES: [dict(e) for e in exposures]},
        capacity_graphs=graphs, case_label=label,
    )
    _close(dispatcher, mm, request_run, scope, "completed", client, graphs)
    return kl, session, scope


def _settlement_harness(scope):
    """Beat 3's harness (dr_settlement) + the consolidate builtin + a KL,
    through the same production close as every other case. ``scope``
    case-unique (§55)."""
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
    from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer

    from decision_records_demo.dr_dump import _Session
    from decision_records_demo.dr_settlement import (
        settlement_capacities,
        settlement_datastates,
    )

    session = _Session()
    layer = CapacityLayer()
    for ds in settlement_datastates():
        layer.register_datastate(ds, session=session, allow_new_realm=True)
    for cap in settlement_capacities():
        layer.register_capacity(cap, session=session)
    install_consolidate_capacities(layer)
    kl = KnowledgeLayer.bootstrap()
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, scope)
    return session, kl, mm, dispatcher, writer, writer.emit_request_run()


def _case_settlement(client):
    """Beat 3: the claim cannot be settled until a document arrives, and the
    Record names which one."""
    from decision_records_demo.dr_settlement import (
        CASE_MISSING_DOCUMENT, DS_CLAIM_INTAKE, settlement_plan,
    )

    scope = "drdemo-page-settlement"
    session, kl, mm, dispatcher, writer, request_run = _settlement_harness(scope)
    graphs: list = []
    execution.run(
        dispatcher, writer, settlement_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_INTAKE: dict(CASE_MISSING_DOCUMENT)},
        capacity_graphs=graphs, case_label="claim CLM-5093",
    )
    _close(dispatcher, mm, request_run, scope, "completed", client, graphs)
    return kl, session, scope


def _case_routing(client):
    from decision_records_demo.dr_routing import CASE_A_EXPOSURES

    return _run_routing_case(
        client, "drdemo-page-routing", CASE_A_EXPOSURES, "claim CLM-3007"
    )


def _case_routingrefusal(client):
    from decision_records_demo.dr_routing import CASE_B_EXPOSURES

    return _run_routing_case(
        client, "drdemo-page-routingrefusal", CASE_B_EXPOSURES,
        "claim CLM-3007 (one more exposure filed)",
    )


from decision_records_demo.dr_settlement import (
    CASE_MISSING_DOCUMENT as _SETTLEMENT_INTAKE,
)


def _case_intake(name):
    """The room-safe intake for each case — the same VALUES the case feeds
    ``execution.run``, never the IRI-keyed seed (an IRI on the arrived panel
    would be G6's sin on the other screen)."""
    from decision_records_demo.dr_routing import (
        CASE_A_EXPOSURES, CASE_B_EXPOSURES,
    )

    return {
        "claim": list(EXPOSURES),
        "refusal": "2026-07-01",
        "outage": "2026-07-01",
        "boundary": [],
        "noroute": EXPOSURES[0],
        "policyprior": "2023-06-01",
        "policycurrent": "2024-06-01",
        "settlement": dict(_SETTLEMENT_INTAKE),
        "routing": CASE_A_EXPOSURES,
        "routingrefusal": CASE_B_EXPOSURES,
    }[name]


CASES = {
    "claim": _case_claim,
    "refusal": _case_refusal,
    "outage": _case_outage,
    "boundary": _case_boundary,
    "noroute": _case_noroute,
    "policyprior": _case_policy_prior,
    "policycurrent": _case_policy_current,
    "settlement": _case_settlement,
    "routing": _case_routing,
    "routingrefusal": _case_routingrefusal,
}


def _main_from_root(client, root: str) -> int:
    """Render one page from the store ALONE (coordination §51.3 option c).

    No case runs, no KnowledgeLayer exists in this code path: the only inputs
    are the client and the index graph's id. The Episode's fields are absent
    by construction, so the page states the decided date's absence (§52
    condition 1) — that stated line IS the finding, on the artifact.
    """
    print(f"== from-root render — capacity_root_ref {root!r}, no live KL in process ==")
    try:
        page = render_record(client, {"capacity_root_ref": root})
    except RendererGapError as exc:
        print(f"RENDER RAISED: {type(exc).__name__}: {exc}")
        return 1
    print("-- BEGIN PAGE --")
    print(page, end="")
    print("-- END PAGE --")
    return 0


def main(argv) -> int:
    try:
        client = FalkorClient(FalkorConfig.from_env())
        client.run_query("RETURN 1 AS ok", {})
    except Exception as exc:  # noqa: BLE001 — the raw error IS the output
        print(f"FalkorDB unreachable: {type(exc).__name__}: {exc}")
        return 3
    try:
        if len(argv) > 1 and argv[1] == "--from-root":
            if len(argv) != 3:
                print("usage: dr_render_pages.py [--from-root <capacity_root_ref>]")
                return 2
            return _main_from_root(client, argv[2])
        screens_dir = None
        if len(argv) > 1 and argv[1] == "--screens":
            if len(argv) != 3:
                print("usage: dr_render_pages.py [--screens <dir>] [--from-root <capacity_root_ref>]")
                return 2
            screens_dir = argv[2]
            os.makedirs(screens_dir, exist_ok=True)
        failures = 0
        roots = []
        pages = {}
        for name, case in CASES.items():
            kl, session, episode_id = case(client)
            props = _episode_props(kl, session, episode_id)
            print(f"== case: {name} — Episode {episode_id!r} ==")
            print(f"capacity_root_ref: {props.get('capacity_root_ref')!r}")
            roots.append((name, props.get("capacity_root_ref")))
            try:
                page = render_record(client, props)
            except RendererGapError as exc:
                failures += 1
                print(f"RENDER RAISED: {type(exc).__name__}: {exc}")
                print()
                continue
            pages[name] = page
            print("-- BEGIN PAGE --")
            print(page, end="")
            print("-- END PAGE --")
            if screens_dir:
                target = os.path.join(screens_dir, f"{name}.html")
                with open(target, "w", encoding="utf-8") as fh:
                    fh.write(compose_screen(page, intake=_case_intake(name)))
                print(f"screen written: {target}")
            print()
        print(
            "== END-STATE re-verify (§55 + §79-5): every Episode re-rendered "
            "from the store ALONE, after the last write — and the store-alone "
            "page must differ from the live page in EXACTLY the date line =="
        )
        for name, root in roots:
            if not root:
                print(f"end-state {name!r}: no capacity_root_ref, nothing to render")
                failures += 1
                continue
            try:
                page_root = render_record(client, {"capacity_root_ref": root})
            except RendererGapError as exc:
                failures += 1
                print(f"end-state {name!r} RAISED: {exc}")
                continue
            if name not in pages:
                print(f"end-state {name!r}: rendered from root {root!r} (no live page to compare)")
                continue
            diffs = compare_pages(pages[name], page_root)
            expected_absence = "Decided date: not available from stored evidence"
            if (
                len(diffs) == 1
                and diffs[0][0].startswith("Decided ")
                and diffs[0][1] == expected_absence
            ):
                print(f"end-state {name!r}: store-alone page matches except the date line")
            else:
                failures += 1
                print(f"end-state {name!r}: UNEXPECTED differences: {diffs!r}")
        print(f"cases that raised: {failures}")
        return 0 if failures == 0 else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
