"""The one credential kind core ships: a named environment variable.

``{"var": "ANTHROPIC_API_KEY"}``. That is the whole spec, and it is a
**pointer** — the name of a place a credential lives, never the credential.

**Why core ships exactly one.** Decision 9's precedent: an option in a picker
that nothing implements is dead. A registry with no reference implementation is
a shape nobody has proved fits, so ``env`` exists both to be useful and to be
the worked example a deployment copies for its keychain, its secret manager or
its file.

⚠ **:func:`validate` deliberately does NOT check that the variable is SET.**
That is the tempting version and it is wrong twice over. It makes set-time
validation depend on the machine doing the setting, so a configuration written
on a laptop and deployed to a server would validate in one place and not the
other; and it turns configuration into a probe of the live environment, which
means the same spec is valid and invalid at different minutes of the same day.
What is checked here is the only thing that is true independent of any machine:
the NAME is a name. A variable that is absent at call time is
:class:`~mindsos_llm.credentials.CredentialUnavailable`, which is the failure
that path already has and states in fixed prose.

**Per-call evaluation is load-bearing.** :func:`build` closes over the variable
NAME, not over its value, and reads ``os.environ`` inside the fetch. A rotated
credential is therefore picked up without reconstructing the client — and,
more importantly, the value is a local of a frame that always returns rather
than a free variable of a long-lived closure. That is round one of the
credential review, stated in :mod:`mindsos_llm.credentials`, obeyed here.
"""

from __future__ import annotations

import os
import re
from typing import Any, Mapping

from ..credentials import LEVEL_NEVER_STORED, Resolver

#: The stable id a stored ``credential_kind`` resolves through.
KIND_ID = "env"

#: ⚠ A promise about the SOURCE, exactly as an adapter's ``SUPPORTED_LEVELS``
#: is a promise about the wire. An environment variable is long-lived and it is
#: read by MindsOS, so it can serve level 1 and nothing else: level 2 means a
#: broker holds the credential and MindsOS never sees it, and level 3 means the
#: source mints something that expires. Declaring only what is true here is
#: what lets a stored ``(kind, level)`` pair be refused rather than silently
#: mismatched.
SUPPORTED_LEVELS = (LEVEL_NEVER_STORED,)

#: POSIX portable environment-variable name. Deliberately strict: a name with a
#: space or a leading digit is a typo every time, and catching it when the
#: configuration is written is the entire point of set-time validation.
_VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: The kind's own fields. A closed set, refused rather than ignored when it
#: grows — an unasked key in a credential spec is somebody's misunderstanding
#: about where a secret goes, and stripping it silently would hide that.
_FIELDS = ("var",)


class EnvSpecInvalid(ValueError):
    """This spec is not a usable ``env`` reference.

    ⚠ **Never echoes the offending value.** The value here IS the variable
    name, which is a fingerprint of the deployment, and an exception is the one
    object in this package that reliably ends up somewhere it was not aimed —
    a log, a traceback, a page. It names the FIELD and the RULE, which is
    everything the person fixing it needs.
    """


def validate(spec: Mapping[str, Any]) -> None:
    """Refuse anything but ``{"var": "<A_NAME>"}``. Returns None on success."""
    if not isinstance(spec, Mapping):
        raise EnvSpecInvalid("an env credential spec must be a mapping")
    unasked = set(spec) - set(_FIELDS)
    if unasked:
        raise EnvSpecInvalid(
            "an env credential spec declares only "
            f"{_FIELDS!r}; it carries {len(unasked)} field(s) it did not ask "
            "for, and they are refused rather than ignored"
        )
    if "var" not in spec:
        raise EnvSpecInvalid("an env credential spec must declare 'var'")
    var = spec["var"]
    if not isinstance(var, str) or not var:
        raise EnvSpecInvalid("'var' must be a non-empty string")
    if not _VAR_RE.match(var):
        raise EnvSpecInvalid(
            "'var' must be a portable environment-variable name: a letter or "
            "underscore, then letters, digits or underscores"
        )


def build(spec: Mapping[str, Any]) -> Resolver:
    """Build the level-1 resolver this spec names.

    ``validate`` runs first, so a spec that reached storage without being
    validated is still refused here rather than producing a resolver that
    fails later and further away.
    """
    validate(spec)
    var = spec["var"]
    return Resolver(
        fetch=lambda: os.environ[var],
        level=LEVEL_NEVER_STORED,
        expires_at=None,
    )


__all__ = ["KIND_ID", "SUPPORTED_LEVELS", "EnvSpecInvalid", "build", "validate"]
