"""dr_render_pages — the RULES §12 command for item 7: real runs, a real store, the page.

Per case: run through `execution.run` → consolidate to a REAL FalkorDB
(`consolidate_request`, the production close) → hand `dr_render.render_record`
the Episode's properties and the client — the page is rendered FROM THE STORE
(plan §2.3 decision 5) — → print the page raw between markers.

Cases: claim (3 exposures + fold), refusal (no edition in force — in-band),
outage (store unreachable — RunStopped), boundary (zero exposures — the
reducer refuses), noroute (unroutable — manifest-only graph).

RULES §11 seam: everything between the BEGIN/END PAGE markers is the
renderer's composed page — layout and framing are `dr_render.py`'s, every fact
on it is a stored graph value, and a gap raises instead of rendering. Text
outside the markers is this driver's narration. ⚠ ONE STATED EXCEPTION
(coordination §51.1): the "Decided <date>" line comes from the Episode, which
lives in the in-process KnowledgeLayer — KL persistence is the server's job
(ADR-0042), so the date is NOT store-resident. The from-root mode below is the
honest form of that limit: it renders with no live KL at all, and the page
STATES the date's absence instead of omitting the line (§52 condition 1).

Two modes:

  (default)             run all five cases → consolidate → render each FROM
                        THE STORE. Narration prints each case's
                        capacity_root_ref so it can be fed to --from-root.
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
    EXPOSURES,
    _claim_plan,
    _leaf_plan,
    _lookup_declaration,
    _policy_datastates,
)
from decision_records_demo.dr_persist_smoke import _harness_with_consolidation
from decision_records_demo.dr_render import RendererGapError, render_record


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


CASES = {
    "claim": _case_claim,
    "refusal": _case_refusal,
    "outage": _case_outage,
    "boundary": _case_boundary,
    "noroute": _case_noroute,
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
        failures = 0
        roots = []
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
            print("-- BEGIN PAGE --")
            print(page, end="")
            print("-- END PAGE --")
            print()
        print("== END-STATE re-verify (§55): every Episode re-rendered from the store ALONE, after the last write ==")
        for name, root in roots:
            if not root:
                print(f"end-state {name!r}: no capacity_root_ref, nothing to render")
                failures += 1
                continue
            try:
                render_record(client, {"capacity_root_ref": root})
                print(f"end-state {name!r}: rendered from root {root!r}")
            except RendererGapError as exc:
                failures += 1
                print(f"end-state {name!r} RAISED: {exc}")
        print(f"cases that raised: {failures}")
        return 0 if failures == 0 else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
