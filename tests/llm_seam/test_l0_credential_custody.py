"""Guards for L0 credential custody (ADR-0210 slice 2).

Four properties this file exists to keep, each of which would erode silently:

* **The audit trail names the SOURCE, never where it points.** A stored spec
  is a pointer rather than a secret, but an environment-variable name is a
  fingerprint of the deployment and this table is what an operator hands an
  auditor.
* **No verb reaches another user.** Every row is addressed by
  ``session.user_id``; cross-user reach is absent by construction, not refused
  by a check.
* **L0 builds no transport and no client.** ADR-0210 decision 2. L0 now
  imports ``mindsos_llm`` — this is the guard that stops that import becoming
  an outbound client one convenience at a time.
* **A credential is released only when one will be used.** Replay is refused
  BEFORE the audit row, so the record of credential use contains no uses that
  did not happen.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path

import pytest

from mindsos_server import llm_custody as LC
from mindsos_server.audit import ALL_AUDIT_EVENTS, EVT_LLM_CREDENTIAL_RELEASED
from mindsos_llm.adapters import UnknownVendor
from mindsos_llm.credential_kinds import UnknownCredentialKind
from mindsos_llm.credential_kinds.env import EnvSpecInvalid
from mindsos_server.errors import PermissionDeniedError

VAR = "ACME_PROD_ANTHROPIC_KEY_2026"
GOOD = dict(
    vendor_id="anthropic",
    credential_level=1,
    mode="live",
    credential_kind="env",
    credential_spec={"var": VAR},
)


def _events(conn):
    return [r[0] for r in conn.execute("SELECT event FROM audit")]


def _audit_text(conn):
    return " ".join(
        str(r) for r in conn.execute("SELECT actor_user, event, target_user, extra_json FROM audit")
    )


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_a_configuration_round_trips(tmp_server_db, alice):
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    view = LC.get_llm_config(tmp_server_db, alice)
    assert (view.vendor_id, view.credential_level, view.mode) == ("anthropic", 1, "live")
    assert view.credential_kind == "env"
    assert view.credential_spec == {"var": VAR}
    assert view.updated_at.endswith("Z")


def test_setting_twice_replaces_rather_than_duplicating(tmp_server_db, alice):
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    LC.set_llm_config(tmp_server_db, alice, **{**GOOD, "mode": "capture"})
    assert LC.get_llm_config(tmp_server_db, alice).mode == "capture"
    assert tmp_server_db.execute("SELECT count(*) FROM llm_config").fetchone()[0] == 1


def test_an_unconfigured_user_is_a_normal_state_not_a_broken_one(tmp_server_db, alice):
    """Core ships with no vendor, no credential and no network. A user who
    has not run the picker has no row, and that is what is reported."""
    with pytest.raises(LC.LLMNotConfigured):
        LC.get_llm_config(tmp_server_db, alice)


# ---------------------------------------------------------------------------
# Set-time validation — the whole benefit of a typed spec
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "over, exc, match",
    [
        ({"mode": "lve"}, ValueError, "mode must be one of"),
        ({"vendor_id": "a-vendor-nobody-registered"}, UnknownVendor, ""),
        ({"credential_level": 3}, ValueError, "serves credential levels"),
        ({"credential_kind": "a-kind-nobody-registered"}, UnknownCredentialKind, ""),
        ({"credential_spec": {"var": "not a name"}}, EnvSpecInvalid, "portable"),
        (
            {"credential_spec": {"var": VAR, "value": "sk-the-mistake"}},
            EnvSpecInvalid,
            "did not ask",
        ),
    ],
    ids=["mode", "vendor", "level-vs-wire", "kind", "spec-shape", "spec-carries-a-secret"],
)
def test_a_configuration_that_cannot_work_is_refused_when_it_is_SET(
    tmp_server_db, alice, over, exc, match
):
    """MUTATION: drop any one of the three checks in ``set_llm_config``.

    Three checks because a configuration can pass any two: the mode, the
    vendor's WIRE against the level, and the kind's SOURCE against the level
    and the spec. ⚠ The ``spec-carries-a-secret`` case is the one shape-checking
    alone would miss — a spec with a ``value`` key is somebody putting the
    credential where the pointer goes, refused rather than stripped.

    ⚠⚠ **EACH CASE NAMES ITS EXCEPTION AND ITS MESSAGE, and that is a
    correction rather than thoroughness.** Written first as
    ``pytest.raises(Exception)``, this guard let TWO designated mutations come
    back GREEN, and both were findings:

    * dropping the MODE check reddened nothing, because the SQL ``CHECK`` on
      ``llm_config.mode`` refuses ``"lve"`` at INSERT. The row never lands
      either way, so a test asking only "did something raise" cannot tell a
      Python guard from a database constraint — and the two fail differently:
      one before the write with a sentence a person can act on, one at the
      write with ``IntegrityError``;
    * dropping the WIRE-level check reddened nothing, because
      ``credential_kinds.validate`` refuses level 3 too. That one is real
      redundancy rather than a bad test: with only ``env`` and ``anthropic``
      in the tree, SOURCE and WIRE serve exactly the same levels, so the two
      checks are separable only by the message they raise. They stop being
      redundant the moment a kind serves a level some vendor does not — which
      is what slice 4's broker and a hosted adapter will do.
    """
    with pytest.raises(exc, match=match or None):
        LC.set_llm_config(tmp_server_db, alice, **{**GOOD, **over})
    assert tmp_server_db.execute("SELECT count(*) FROM llm_config").fetchone()[0] == 0


# ---------------------------------------------------------------------------
# The capability, both doors
# ---------------------------------------------------------------------------


def test_release_without_the_capability_is_denied_and_audited(
    tmp_server_db, alice, alice_without_the_capability
):
    """MUTATION: remove the ``_require_or_audit`` call.

    The denial row is written and COMMITTED before the raise — ADR-0013's
    "permission denials are audit events", which cannot be lost to the
    caller's rollback.
    """
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    with pytest.raises(PermissionDeniedError):
        LC.release_credential(tmp_server_db, alice_without_the_capability)
    assert "EVT_PERMISSION_DENIED" in _events(tmp_server_db)
    assert EVT_LLM_CREDENTIAL_RELEASED not in _events(tmp_server_db)


def test_release_with_the_capability_hands_back_custody_and_audits_it(
    tmp_server_db, alice
):
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    custody = LC.release_credential(tmp_server_db, alice)
    assert (custody.vendor_id, custody.credential_level, custody.mode) == (
        "anthropic", 1, "live",
    )
    assert _events(tmp_server_db).count(EVT_LLM_CREDENTIAL_RELEASED) == 1
    extra = json.loads(
        tmp_server_db.execute(
            "SELECT extra_json FROM audit WHERE event = ?",
            (EVT_LLM_CREDENTIAL_RELEASED,),
        ).fetchone()[0]
    )
    assert extra["credential_kind"] == "env"
    assert extra["credential_level"] == 1


def test_the_event_is_in_the_roster():
    assert EVT_LLM_CREDENTIAL_RELEASED in ALL_AUDIT_EVENTS


# ---------------------------------------------------------------------------
# ⚠ The audit trail names the source, never where it points
# ---------------------------------------------------------------------------


def test_the_spec_FIELDS_never_reach_the_audit_trail(tmp_server_db, alice):
    """MUTATION: add ``credential_spec`` to the ``extra`` mapping.

    The stored value is a pointer and not a secret — and it is still a
    fingerprint of the deployment. This asserts against the WHOLE audit table
    rather than the one row, because the leak that matters is the one written
    by a path nobody thought about.
    """
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    LC.release_credential(tmp_server_db, alice)
    assert VAR not in _audit_text(tmp_server_db)


def test_release_does_NOT_fetch_the_credential(tmp_server_db, alice, monkeypatch):
    """L0 hands out a way to ask for a credential, never a credential. If the
    variable were read here the value would be a local of this frame — and
    ``release_credential`` succeeds below with the variable UNSET, which is
    only possible because nothing asked."""
    monkeypatch.delenv(VAR, raising=False)
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    custody = LC.release_credential(tmp_server_db, alice)
    monkeypatch.setenv(VAR, "sk-set-afterwards")
    assert custody.resolver() == "sk-set-afterwards"


# ---------------------------------------------------------------------------
# ⚠ Replay is refused BEFORE anything is written
# ---------------------------------------------------------------------------


def test_replay_releases_no_credential_and_writes_no_row(tmp_server_db, alice):
    """MUTATION: delete the replay branch.

    Without it a replay user's release writes EVT_LLM_CREDENTIAL_RELEASED for
    a run that answers from a file and reaches no provider — a use recorded
    that did not occur. The refusal is placed before the write for exactly
    that reason, and this test asserts the absence, not just the raise.
    """
    LC.set_llm_config(tmp_server_db, alice, **{**GOOD, "mode": "replay"})
    with pytest.raises(LC.ReplayReleasesNoCredential):
        LC.release_credential(tmp_server_db, alice)
    assert EVT_LLM_CREDENTIAL_RELEASED not in _events(tmp_server_db)


def test_capture_DOES_release_a_credential(tmp_server_db, alice):
    """The other door: capture calls a provider, so it releases."""
    LC.set_llm_config(tmp_server_db, alice, **{**GOOD, "mode": "capture"})
    assert LC.release_credential(tmp_server_db, alice).mode == "capture"


# ---------------------------------------------------------------------------
# Structural: no cross-user reach, no client in L0
# ---------------------------------------------------------------------------


def test_no_verb_here_accepts_a_user_id(tmp_server_db):
    """Cross-user reach is absent by CONSTRUCTION, not refused by a check.

    A ``user_id`` parameter is the whole mechanism by which one would arrive,
    so its absence is asserted from the signatures rather than assumed. This
    is why ``set_llm_config`` and ``get_llm_config`` need no capability.
    """
    offenders = []
    for name, fn in vars(LC).items():
        if name.startswith("_") or not inspect.isfunction(fn):
            continue
        if fn.__module__ != LC.__name__:
            continue
        if "user_id" in inspect.signature(fn).parameters:
            offenders.append(name)
    assert offenders == [], (
        f"{offenders} take a user_id. Every row here is addressed by "
        "session.user_id; a user_id parameter is how cross-user reach arrives."
    )


_CLIENT_SYMBOLS = {
    "build_transport",
    "build_client",
    "LiveLLM",
    "CapturingLLM",
    "RecordedLLM",
}


def test_L0_builds_no_transport_and_no_client():
    """ADR-0210 decision 2, asked from the SOURCE of the whole package.

    ⚠ **This is the guard that pays for L0's new import of ``mindsos_llm``.**
    Slice 2 created the first ``mindsos_server`` -> ``mindsos_llm`` edge, which
    is legal (the isolation guard runs the other way) and necessary
    (``seam.require_resolver`` is an ``isinstance`` check, so whoever builds a
    resolver imports ``credentials``). What must not follow is L0 acquiring an
    outbound client: "L0 is auth, sessions, authorization and audit; giving it
    an HTTP client to a model vendor is a new egress it has never had."

    Asked as an AST walk over every module in the package rather than a grep,
    and over the FILESYSTEM rather than a listed set of files, because both
    shortcuts have been the defect in this repo before.
    """
    pkg = Path(LC.__file__).parent
    offenders = []
    for path in sorted(pkg.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    if a.name in _CLIENT_SYMBOLS:
                        offenders.append(f"{path.relative_to(pkg)}:{a.name}")
                continue
            if name in _CLIENT_SYMBOLS:
                offenders.append(f"{path.relative_to(pkg)}:{name}")
    assert offenders == [], (
        f"{offenders} build an outbound model client inside L0. L0 holds the "
        "choice and the custody; mindsos_llm.build_client holds the wire."
    )


def test_the_walk_covers_this_module():
    """The domain-emptied failure mode, pinned. A walk that stops finding
    L0's modules is a red, not a quiet pass."""
    pkg = Path(LC.__file__).parent
    walked = {p.name for p in pkg.rglob("*.py")}
    assert "llm_custody.py" in walked
    assert len(walked) >= 20, f"only {len(walked)} modules walked in {pkg}"


# ---------------------------------------------------------------------------
# The two places the mode set is written down
# ---------------------------------------------------------------------------


def test_the_sql_CHECK_and_the_python_MODES_are_the_same_set():
    """MUTATION: add a mode to ``MODES`` without touching the DDL.

    A constraint cannot import Python, so the closed set is written twice —
    once as :data:`mindsos_llm.MODES` and once as a SQL ``CHECK`` on
    ``llm_config``. A hand-copied roster that drifts is this repo's most
    repeated defect; this is its mechanical inverse.
    """
    from mindsos_llm import MODES
    from mindsos_server._schema import _DDL_LLM_CONFIG

    clause = re.search(r"mode\s+TEXT NOT NULL CHECK \(mode IN \(([^)]*)\)\)", _DDL_LLM_CONFIG)
    assert clause, _DDL_LLM_CONFIG
    in_sql = {m.strip().strip("'") for m in clause.group(1).split(",")}
    assert in_sql == set(MODES), f"SQL CHECK {in_sql!r} vs MODES {set(MODES)!r}"


# ---------------------------------------------------------------------------
# The credential pointer does not outlive its user
# ---------------------------------------------------------------------------


def test_hard_deleting_the_user_takes_the_credential_pointer_with_them(
    tmp_server_db, alice
):
    """The OPPOSITE of ``audit``'s FK choice, and deliberately so.

    An audit row must outlive its subject (ADR-0013). A credential pointer
    must not: it names a place a secret lives, and a row surviving its owner
    leaves that name behind with nobody to own it. ``hard_delete_user`` deletes
    only from ``users`` and relies on this cascade, exactly as ``sessions``
    does — so the cascade IS the mechanism, not a safety net.
    """
    LC.set_llm_config(tmp_server_db, alice, **GOOD)
    tmp_server_db.execute("DELETE FROM users WHERE user_id = 'alice'")
    tmp_server_db.commit()
    assert tmp_server_db.execute("SELECT count(*) FROM llm_config").fetchone()[0] == 0
