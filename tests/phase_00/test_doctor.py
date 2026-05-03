"""`mindsos doctor` and `mindsos doctor --self-test` — runtime + drift checks."""

from __future__ import annotations

import json


def test_doctor_exits_zero_and_reports_pins(cli):
    proc = cli("doctor")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "FalkorDB pin" in out
    assert "Python pin" in out
    assert "Lockfile sha" in out
    assert "FalkorDB ping" in out + proc.stderr


def test_doctor_falkordb_reachable(cli):
    proc = cli("doctor", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    state = payload["runtime"]["falkordb"]
    assert state["reachable"] is True, f"FalkorDB unreachable: {state}"


def test_self_test_passes(cli):
    """`doctor --self-test` exits 0 when manifest is fully populated.

    Precondition: tester has run `tools/lock.sh` AND updated
    mindsos_cli/manifest.toml's [lockfile] requirements_txt_sha256 with the
    printed value. If that step was skipped, this test fails with a clear
    PENDING_LOCK diagnostic — re-run lock.sh and update the manifest.
    """
    proc = cli("doctor", "--self-test", "--json")
    # JSON is on stdout regardless of pass/fail, so parse first then assert.
    payload = json.loads(proc.stdout)
    assert proc.returncode == 0, (
        f"self-test failed; failures={payload.get('failures', [])}"
    )
    assert payload["ok"] is True
