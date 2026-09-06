"""L0 credential custody — which vendor, which level, which mode, which source.

**What L0 owns here, and what it deliberately does not.** L0 holds the *choice*
and the *custody*: a user's vendor id, credential level, mode, and a POINTER to
where their credential lives. It does not hold a credential, it does not build
a transport, and it does not construct a client. ADR-0210 decision 2 —
"L0 is auth, sessions, authorization and audit; giving it an outbound HTTP
client to a model vendor is a new egress it has never had."

:func:`release_credential` therefore returns a :class:`LLMCustody` — four
values, one of them a callable — and the caller hands them to
:func:`mindsos_llm.build_client`. **That split is guarded**
(``tests/llm_seam/test_l0_credential_custody.py``), because it is the kind of
boundary that erodes one convenience at a time.

⚠ **The stored credential spec is a POINTER, never a secret**, and the
levels do not mean what the phrase "MindsOS never knows your key" suggests.
Level 1 is never **stored**: the credential lives in the user's keychain or
environment and MindsOS holds it for one request. Level 2 is never **known**:
a broker the user runs adds it. Only level 2 is "never sees it".

⚠ **No verb here takes a ``user_id``.** Every row is addressed by
``session.user_id``, so cross-user reach is absent by construction rather than
refused by a check — a stronger guarantee, and the reason ``set_llm_config``
and ``get_llm_config`` need no capability at all. The one capability,
:data:`~mindsos_server.capabilities.CAN_USE_LLM_CREDENTIAL`, gates the moment a
stored pointer becomes a live credential, because that is the moment worth
refusing and the moment worth an audit row.

**A replay-mode user still names a credential source.** Mode is switchable at
any time, so the configuration describes the vendor relationship rather than
one run; a user who only ever replays names a source that is never read. The
alternative — nullable kind and spec — buys nothing and adds an absent case to
three call sites.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Optional

from mindsos_llm import MODES, adapters, credential_kinds
from mindsos_llm.credentials import Resolver

from mindsos_server.audit import EVT_LLM_CREDENTIAL_RELEASED, write_audit
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_USE_LLM_CREDENTIAL
from mindsos_server.session import Session


class LLMNotConfigured(Exception):
    """This user has chosen no vendor yet.

    A normal state, not an error condition of the system: core ships with no
    vendor, no credential and no network, and a user who has not run the
    first-run picker simply has no row.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__("no LLM configuration for this user")


class ReplayReleasesNoCredential(Exception):
    """Refused before the audit row, on purpose.

    A replay client answers from a file and reaches no provider. Releasing a
    credential for one would write a row saying a credential was used, for a
    run that never used one — a false entry in the record the capability gate
    exists to produce. ``mindsos_llm.build_client`` refuses the same thing one
    layer down; this refusal is the one that keeps the audit trail clean,
    because it happens before anything is written.
    """


@dataclass(frozen=True, slots=True)
class LLMConfigView:
    """A user's stored configuration, as they set it.

    Carries ``credential_spec`` because a picker showing a user their own
    configuration should be able to say *reads ``$ANTHROPIC_API_KEY``*. It is
    the user's own row, read by their own session. ⚠ The same fields are
    excluded from the audit trail, and that is not a contradiction: one is a
    person looking at their own settings, the other is a table an operator
    hands to an auditor.
    """

    vendor_id: str
    credential_level: int
    mode: str
    credential_kind: str
    credential_spec: Mapping[str, Any]
    updated_at: str


@dataclass(frozen=True, slots=True)
class LLMCustody:
    """What L0 pushes into ``mindsos_llm`` at client construction.

    Four values, one a callable, and no L0 type crosses the boundary —
    ``build_client`` takes these as plain arguments. ⚠ **The resolver has not
    been called.** It is a way to get a credential, not a credential; see
    :mod:`mindsos_llm.credentials` on why that indirection is load-bearing
    rather than stylistic.
    """

    vendor_id: str
    credential_level: int
    mode: str
    resolver: Resolver


def _now_utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def set_llm_config(
    conn: sqlite3.Connection,
    session: Session,
    *,
    vendor_id: str,
    credential_level: int,
    mode: str,
    credential_kind: str,
    credential_spec: Mapping[str, Any],
) -> None:
    """Write (or replace) this session's own configuration.

    **Everything is validated HERE, when the configuration is set** — that is
    the whole benefit of storing a typed spec rather than an opaque blob. Three
    checks, and they are three because a configuration can pass any two:

    1. the mode is one ``mindsos_llm`` serves;
    2. the vendor is registered, and its WIRE can present a credential of this
       level (``adapters.supported_levels``);
    3. the credential kind is registered, its SOURCE can produce a credential
       of this level, and the spec is one that kind accepts.

    A wrong environment-variable name fails now, not at the moment a reading
    was supposed to happen.

    No capability: the row is addressed by ``session.user_id`` and reaches no
    other user.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES!r}, got {mode!r}")

    serves = adapters.supported_levels(vendor_id)  # raises UnknownVendor
    if credential_level not in serves:
        raise ValueError(
            f"vendor {vendor_id!r} serves credential levels {serves!r}, "
            f"not {credential_level!r}"
        )
    credential_kinds.validate(
        credential_kind, credential_spec, level=credential_level
    )

    conn.execute(
        "INSERT OR REPLACE INTO llm_config (user_id, vendor_id, "
        "credential_level, mode, credential_kind, credential_spec_json, "
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            session.user_id,
            vendor_id,
            int(credential_level),
            mode,
            credential_kind,
            json.dumps(dict(credential_spec), sort_keys=True),
            _now_utc_iso(),
        ),
    )
    conn.commit()


def _row(conn: sqlite3.Connection, session: Session) -> Optional[tuple]:
    return conn.execute(
        "SELECT vendor_id, credential_level, mode, credential_kind, "
        "credential_spec_json, updated_at FROM llm_config WHERE user_id = ?",
        (session.user_id,),
    ).fetchone()


def get_llm_config(conn: sqlite3.Connection, session: Session) -> LLMConfigView:
    """This session's own configuration. Raises :class:`LLMNotConfigured`."""
    row = _row(conn, session)
    if row is None:
        raise LLMNotConfigured(session.user_id)
    return LLMConfigView(
        vendor_id=row[0],
        credential_level=int(row[1]),
        mode=row[2],
        credential_kind=row[3],
        credential_spec=json.loads(row[4]),
        updated_at=row[5],
    )


def release_credential(conn: sqlite3.Connection, session: Session) -> LLMCustody:
    """Turn this session's stored pointer into a live resolver.

    Gated on :data:`~mindsos_server.capabilities.CAN_USE_LLM_CREDENTIAL`, which
    audits its own denial. On success one
    :data:`~mindsos_server.audit.EVT_LLM_CREDENTIAL_RELEASED` row records which
    vendor, level, mode and credential KIND — **never the kind's fields**, per
    ADR-0013's "every privileged endpoint audits both paths" and this slice's
    rule that the audit trail names the source, never where it points.

    ⚠ **The resolver is returned, not called.** L0 never holds a credential
    value; it hands out a way to ask for one.
    """
    _require_or_audit(
        conn, session, CAN_USE_LLM_CREDENTIAL, verb="release_credential"
    )
    view = get_llm_config(conn, session)
    if view.mode == "replay":
        raise ReplayReleasesNoCredential(
            "a replay client answers from a file and reaches no provider; "
            "releasing a credential for it would record a credential use that "
            "did not happen"
        )
    resolver = credential_kinds.build(
        view.credential_kind, view.credential_spec, level=view.credential_level
    )
    write_audit(
        conn,
        actor=session.user_id,
        event=EVT_LLM_CREDENTIAL_RELEASED,
        target=None,
        extra={
            "vendor_id": view.vendor_id,
            "credential_level": view.credential_level,
            "mode": view.mode,
            "credential_kind": view.credential_kind,
        },
    )
    conn.commit()
    return LLMCustody(
        vendor_id=view.vendor_id,
        credential_level=view.credential_level,
        mode=view.mode,
        resolver=resolver,
    )


__all__ = [
    "LLMConfigView",
    "LLMCustody",
    "LLMNotConfigured",
    "ReplayReleasesNoCredential",
    "get_llm_config",
    "release_credential",
    "set_llm_config",
]
