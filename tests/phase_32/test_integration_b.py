"""Phase 32 — Integration B: L0+L1+L2+L3 read-side end-to-end scenario.

Single ``test_integration_b`` + 11 step helpers + ScenarioState thread
per R2-PB-1. Composes the Phases 02-31 substrate end-to-end:

* CLI invocations (via Typer CliRunner per Phase 26b precedent; each
  invoke gets fresh state via HOME-inherited token).
* In-process Python helpers for steps without CLI verbs (L3 bootstrap,
  install_text_capacities, in-process find).

Substep map (PHASE_MAP §32 7 substeps → 11 helpers per R2-PB-1):

  | substep | helper | kind |
  | 1a server bootstrap | _step_01_bootstrap_admin | CLI |
  | 1b admin login | _step_02_login_admin | CLI |
  | 1c KL bootstrap + import | _step_03_kl_bootstrap_and_import | in-process |
  | 2 L3 Global + Local bootstrap | _step_04_l3_bootstrap | in-process |
  | 3 install text capacities | _step_05_install_text_capacities | in-process |
  | 4 find pipeline | _step_06_find_pipeline | in-process + CLI smoke |
  | 5 CLI invoke | _step_07_cli_invoke | CLI |
  | 6 problem-trace tail | _step_08_problem_trace_tail | CLI |
  | 7 logout | _step_09_logout | CLI |
  | 7 re-login for audit | _step_10_login_admin_for_audit | CLI |
  | 7a query-audit | _step_11_query_audit | CLI |

Audit-event table (R0-PB-10 / R2-PB-3 lock):

  EVT_BOOTSTRAP: 1, EVT_LOGIN: 2, EVT_LOGOUT: 1
  EVT_AUDIT_QUERY filtered from this call's SELECT (Phase 21 B-21-T1).

Background — Integration B is co-resident execution, NOT co-resident
persistence (R0-PB-7). L1/L2 substrate lives in FalkorDB (via
``bootstrap_global_pair_from_falkordb``). L3 substrate is in-memory
Python — every ``mindsos capacity invoke`` rebuilds Global +
auto-installs text builtins via the CLI's ``_construct_invoke_layer``.
Phase 30 carry-forward #3 (Falkor-backed L3 bootstrap) stays open.

Net-new features: No. Net-new test code: yes (scenario harness only).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest
from typer.testing import CliRunner

from mindsos_capacity import CapacityLayer, find_pipeline
from mindsos_capacity.builtins.text import (
    DS_RAW_TEXT,
    DS_TOKENS,
    install_text_capacities,
)
from mindsos_cli.app import app
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.persistence.metagraph_repository import MetagraphRepository
from mindsos_server.persistence import bootstrap_global_pair_from_falkordb

from tests.phase_32.fixtures._text_importer import TextFixtureImporter


# Concrete IRI literals (per R4 §am-impl-2 — verified against
# mindsos_capacity/identifiers.py + builtins/text.py).
SPACE_SPLIT_IRI = "capacity:perception:text.space_split"


# ── ScenarioState (R1-PB-6 — 7 fields) ─────────────────────────────────


@dataclass
class ScenarioState:
    runner: CliRunner
    db_path: Path
    home: Path
    layer: Optional[CapacityLayer] = None       # populated in step 4
    pipelines_found: list = field(default_factory=list)  # step 6
    invoke_payload: Optional[dict] = None       # step 7 (parsed envelope)
    audit_rows: list = field(default_factory=list)  # step 11


# ── Pytest fixtures ────────────────────────────────────────────────────


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def scenario_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario_falkordb_clean: None,  # noqa: ARG001 — fixture-side-effect
) -> dict[str, Path]:
    """Per-scenario fresh server.db + HOME; FalkorDB pre-cleaned by conftest."""
    db_path = tmp_path / "server.db"
    monkeypatch.setenv("MINDSOS_SERVER_DB", str(db_path))
    monkeypatch.delenv("MINDSOS_TOKEN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    return {"db": db_path, "home": tmp_path}


# ── Step helpers (11 substeps per R2-PB-1) ─────────────────────────────


def _step_01_bootstrap_admin(state: ScenarioState) -> ScenarioState:
    """Substep 1a — `mindsos server bootstrap admin`. Emits EVT_BOOTSTRAP."""
    r = state.runner.invoke(
        app, ["server", "bootstrap", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_02_login_admin(state: ScenarioState) -> ScenarioState:
    """Substep 1b — `mindsos server login admin`. Emits EVT_LOGIN."""
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_03_kl_bootstrap_and_import(state: ScenarioState) -> ScenarioState:
    """Substep 1c — KL bootstrap + import via FalkorDB pair helper.

    Python-API in-process (no `mindsos admin import text-importer` CLI
    verb; Phase 32 ships zero new CLI verbs). Mirrors Phase 26b's exact
    7-line pattern with TextFixtureImporter swapped in.
    """
    client = FalkorClient(FalkorConfig.from_env())
    try:
        canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
        importer = TextFixtureImporter()
        importer.run(canonical_kl.global_metagraph())
        repo = MetagraphRepository(client)
        repo.persist(canonical_kl.global_metagraph())
    finally:
        client.close()
    return state


def _step_04_l3_bootstrap(state: ScenarioState) -> ScenarioState:
    """Substep 2 — L3 Global + Local bootstrap (in-process).

    Per R4 §am-impl-4: CapacityLayer has NO classmethod bootstrap_global;
    constructor builds Global; .local_metagraph(user_id) lazily creates
    Local. R0-PB-4 lock: bootstrap both (Local-bootstrap path coverage
    even though scenario doesn't otherwise use Local).
    """
    layer = CapacityLayer()                       # Global (constructor)
    _ = layer.local_metagraph("admin")            # Lazy admin Local
    state.layer = layer
    return state


def _step_05_install_text_capacities(state: ScenarioState) -> ScenarioState:
    """Substep 3 — install_text_capacities on the in-process layer.

    R3-PB-1 pick B: call twice; second call must be no-op (idempotent).
    Verifies Phase 31's idempotency contract directly (partial-state
    detection is Phase 31's own test scope).
    """
    assert state.layer is not None
    install_text_capacities(state.layer)
    install_text_capacities(state.layer)          # idempotent: no error
    return state


def _step_06_find_pipeline(state: ScenarioState) -> ScenarioState:
    """Substep 4 — find pipeline raw-text → tokens.

    Two paths per R1-PB-1 pick C (revised at R4 §am-impl-5):

    1. In-process hard assertion (positive path) — uses state.layer
       with text capacities installed from step 5.
    2. CLI smoke (negative path per R4 §am-impl-5) — `mindsos capacity
       find` builds a fresh EMPTY layer (no auto-install), so it
       returns exit 1 + a ``bfs_exhausted`` verdict. The smoke verifies the
       CLI verb is wired correctly; positive-path CLI find is a
       Phase 33+ enhancement (carry-forward).

    `state.layer` is orphaned after this step per R2-PB-4 (substeps 7+
    spawn their own layers in subprocess).
    """
    assert state.layer is not None

    # 1. In-process — positive path, hard assertion.
    pipeline = find_pipeline(
        state.layer,
        start_datastate=DS_RAW_TEXT,
        target_datastate=DS_TOKENS,
    ).pipeline
    assert len(pipeline.steps) == 1, (
        f"expected 1-step pipeline; got {len(pipeline.steps)} steps"
    )
    assert pipeline.steps[0].capacity_iri == SPACE_SPLIT_IRI, (
        f"expected step 0 capacity_iri={SPACE_SPLIT_IRI!r}; "
        f"got {pipeline.steps[0].capacity_iri!r}"
    )
    state.pipelines_found.append(pipeline)

    # 2. CLI find smoke — negative path (empty layer construction).
    r = state.runner.invoke(
        app,
        [
            "capacity", "find",
            "--start", DS_RAW_TEXT,
            "--target", DS_TOKENS,
            "--json",
        ],
    )
    assert r.exit_code == 1, (
        f"expected exit 1 (empty CLI layer → bfs_exhausted verdict); "
        f"got exit {r.exit_code} / output={r.output!r}"
    )
    payload = json.loads(r.output)
    assert payload.get("error") == "bfs_exhausted", (
        f"expected error=bfs_exhausted; got {payload!r}"
    )
    return state


def _step_07_cli_invoke(state: ScenarioState) -> ScenarioState:
    """Substep 5 — CLI invoke of the space_split capacity.

    R3-PB-2 pick B: `--input-file <tmp_path>` form (more script-like
    than inline `--input-json`). The CLI's `_construct_invoke_layer`
    auto-installs text builtins (Phase 31 R3-PB-29 lock), so this works
    against a fresh subprocess layer with no prior install.

    Envelope assertion (R4 §am-impl-7): success=True; outputs[DS_TOKENS]
    == ["the", "cat", "sat"]; error is null.
    """
    invoke_input = state.home / "invoke_input.json"
    invoke_input.write_text(json.dumps({DS_RAW_TEXT: "the cat sat"}))

    r = state.runner.invoke(
        app,
        [
            "capacity", "invoke", SPACE_SPLIT_IRI,
            "--input-file", str(invoke_input),
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    assert payload["success"] is True, f"envelope failure: {payload!r}"
    assert payload["outputs"][DS_TOKENS] == ["the", "cat", "sat"], (
        f"unexpected tokens: {payload['outputs']}"
    )
    assert payload["error"] is None
    state.invoke_payload = payload
    return state


def _step_08_problem_trace_tail(state: ScenarioState) -> ScenarioState:
    """Substep 6 — `mindsos capacity problem-trace tail --json`.

    Empty by construction (R0-PB-9 / R4 §am-impl-5): the CLI's
    `_construct_global_layer` builds a fresh empty layer; its
    problem-trace sink is empty. The smoke verifies the CLI verb is
    wired; subprocess isolation means substep 7's invoke can't have
    written to this fresh sink.
    """
    r = state.runner.invoke(
        app, ["capacity", "problem-trace", "tail", "--json"],
    )
    assert r.exit_code == 0, r.output
    records = json.loads(r.output)
    assert records == [], f"expected empty trace; got {records!r}"
    return state


def _step_09_logout(state: ScenarioState) -> ScenarioState:
    """Substep 7 first half — admin logout. Emits EVT_LOGOUT."""
    r = state.runner.invoke(app, ["server", "logout"])
    assert r.exit_code == 0, r.output
    return state


def _step_10_login_admin_for_audit(state: ScenarioState) -> ScenarioState:
    """Substep 7 transition — re-login admin for query-audit.

    Per R2-PB-2: query-audit needs an admin session (CAN_QUERY_AUDIT).
    The 26b pattern: logout actor → fresh admin login → audit. Cost is
    one extra EVT_LOGIN row in the audit table (locked in R2-PB-3).
    """
    r = state.runner.invoke(
        app, ["server", "login", "admin"], input="adminpw\n",
    )
    assert r.exit_code == 0, r.output
    return state


def _step_11_query_audit(state: ScenarioState) -> ScenarioState:
    """Substep 7a — `mindsos server query-audit --json`.

    Asserts audit event-set per R2-PB-3 locked table:
    EVT_BOOTSTRAP=1, EVT_LOGIN=2, EVT_LOGOUT=1.

    EVT_AUDIT_QUERY is filtered from this call's own SELECT result per
    Phase 21 B-21-T1 lesson (SELECT → write → return ordering).

    Wire shape (R4 Probe 14 / B-26b-T8): `{"rows":[...], "count":N,
    "next_after_id":...}`; row field is `"event"` (not `"kind"`).
    """
    r = state.runner.invoke(app, ["server", "query-audit", "--json"])
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    rows = payload["rows"]
    state.audit_rows = rows

    counts = Counter(row["event"] for row in rows)
    assert counts.get("EVT_BOOTSTRAP", 0) == 1, f"audit: {counts}"
    assert counts.get("EVT_LOGIN", 0) == 2, f"audit: {counts}"
    assert counts.get("EVT_LOGOUT", 0) == 1, f"audit: {counts}"

    # EVT_AUDIT_QUERY filtered from this call's own SELECT result
    # (Phase 21 read-then-write order).
    assert counts.get("EVT_AUDIT_QUERY", 0) == 0, (
        f"expected EVT_AUDIT_QUERY filtered from self-result; got {counts}"
    )
    return state


# ── The scenario ───────────────────────────────────────────────────────


@pytest.mark.integration
def test_integration_b(runner, scenario_env, scenario_state_dir) -> None:
    """Phase 32 — L0+L1+L2+L3 read-side end-to-end scripted scenario."""
    state = ScenarioState(
        runner=runner,
        db_path=scenario_env["db"],
        home=scenario_env["home"],
    )

    state = _step_01_bootstrap_admin(state)
    state = _step_02_login_admin(state)
    state = _step_03_kl_bootstrap_and_import(state)
    state = _step_04_l3_bootstrap(state)
    state = _step_05_install_text_capacities(state)
    state = _step_06_find_pipeline(state)
    state = _step_07_cli_invoke(state)
    state = _step_08_problem_trace_tail(state)
    state = _step_09_logout(state)
    state = _step_10_login_admin_for_audit(state)
    state = _step_11_query_audit(state)
