"""Guards for the credential-kind registry and the one kind core ships.

**What this file is watching.** L0 stores a POINTER to where a credential
lives — a kind id plus that kind's own fields — and never interprets the
fields. Everything that could go wrong with that arrangement goes wrong
quietly: an unregistered kind silently defaulting, a duplicate id resolving by
import order, a stored level the source cannot actually serve, a variable name
leaking into an exception, a credential captured in a closure instead of read
per call. Each of those has a named test below.

⚠ **The registry is module-level state**, so every test that registers
anything uses :func:`restore_registry`. A leaked registration would make a
later test pass or fail on collection order, which is the failure mode this
suite is least able to see.
"""

from __future__ import annotations

import pytest

from mindsos_llm import credential_kinds as ck
from mindsos_llm.credential_kinds import env
from mindsos_llm.credentials import CredentialUnavailable

VAR = "MINDSOS_TEST_CREDENTIAL_KIND_VAR"


@pytest.fixture
def restore_registry():
    saved = dict(ck._REGISTRY)
    yield
    ck._REGISTRY.clear()
    ck._REGISTRY.update(saved)


class _WellFormedKind:
    KIND_ID = "well-formed"
    SUPPORTED_LEVELS = (1,)

    @staticmethod
    def validate(spec):
        return None

    @staticmethod
    def build(spec):
        raise AssertionError("not reached")


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def test_an_unregistered_kind_is_refused_loudly_never_defaulted():
    """MUTATION: make ``get`` fall back to ``env`` on KeyError.

    A silent default would fetch a credential from a source the user did not
    choose. The call would then SUCCEED, and the answer would carry provenance
    that was never true — which is worse than a failure, because nothing
    downstream can tell.
    """
    with pytest.raises(ck.UnknownCredentialKind):
        ck.get("a-kind-nobody-registered")


def test_a_duplicate_kind_id_is_refused_rather_than_overwritten(restore_registry):
    """MUTATION: drop the ``kind_id in _REGISTRY`` branch from ``register``.

    Last-write-wins makes the resolved credential SOURCE depend on import
    order. ``adapters.register`` refuses duplicates for the same reason; here
    the order-dependent thing is where a secret is read from.
    """
    class _Impostor(_WellFormedKind):
        KIND_ID = env.KIND_ID

    with pytest.raises(ValueError, match="already registered"):
        ck.register(_Impostor)
    assert ck.get(env.KIND_ID) is env


def test_registering_the_same_module_twice_is_a_no_op(restore_registry):
    """The other door of the duplicate branch.

    Two-door rule: the predicate is ``id present AND a different object``, and
    a guard that only exercises the refusing exit would pass for the wrong
    reason if the second conjunct were dropped.
    """
    assert ck.register(env) is env
    assert ck.kinds().count(env.KIND_ID) == 1


@pytest.mark.parametrize("missing", ["KIND_ID", "SUPPORTED_LEVELS", "validate", "build"])
def test_a_kind_missing_any_required_attribute_is_refused(restore_registry, missing):
    """MUTATION: shorten the attribute tuple in ``register``.

    Parametrized over the four so that dropping ONE name from the tuple
    reddens exactly one case and names it, rather than leaving three green and
    the roster quietly shorter.
    """
    attrs = {
        "KIND_ID": "partial",
        "SUPPORTED_LEVELS": (1,),
        "validate": staticmethod(lambda spec: None),
        "build": staticmethod(lambda spec: None),
    }
    del attrs[missing]
    with pytest.raises(ValueError, match=missing):
        ck.register(type("_Partial", (), attrs))


def test_env_is_the_ONLY_kind_core_ships():
    """Decision 9, pinned as a literal.

    An option in a picker that nothing implements is dead — and the inverse
    matters just as much: a SECOND kind arriving in core is a design event
    (which credential sources does core itself vouch for?), not an
    implementation detail. It lands with this literal changed, or not at all.
    """
    assert ck.kinds() == ("env",)


# ---------------------------------------------------------------------------
# The (kind, level) pairing — unchecked anywhere else in the tree
# ---------------------------------------------------------------------------


def test_a_level_the_kind_cannot_serve_is_refused_when_the_config_is_SET():
    """MUTATION: delete the ``level not in SUPPORTED_LEVELS`` branch.

    ``kind="env"`` with ``level=3`` stores a claim that the credential expires,
    from a source that mints nothing. The level is STAMPED ON EVERY ANSWER
    (ADR-0210 decision 6), so an unchecked pairing does not merely fail later —
    it corrupts the provenance of answers that succeed.
    """
    with pytest.raises(ck.CredentialLevelUnsupported):
        ck.validate(env.KIND_ID, {"var": VAR}, level=3)


def test_the_level_the_kind_DOES_serve_is_accepted():
    """The other door. Without it, a mutation that refuses every level would
    leave the test above green and the whole kind unusable."""
    assert ck.validate(env.KIND_ID, {"var": VAR}, level=1) is None


def test_the_source_and_the_wire_answer_DIFFERENT_questions():
    """``env`` and the shipped adapter both say level 1, and they must be
    read as two separate promises: the adapter's tuple says an expiring
    credential could be SENT, the kind's says one could be OBTAINED. A
    deployment can satisfy one and not the other, and only checking both
    catches it."""
    from mindsos_llm import adapters

    assert ck.supported_levels(env.KIND_ID) == (1,)
    assert adapters.supported_levels("anthropic") == (1,)


def test_build_revalidates_rather_than_trusting_storage():
    """MUTATION: drop the ``validate`` call from ``build``.

    A row reaches the table by a migration, a restore or a hand-edit as easily
    as by the setter. The cheapest failure is the one at construction, not the
    one at the moment a reading was supposed to happen.
    """
    with pytest.raises(env.EnvSpecInvalid):
        ck.build(env.KIND_ID, {"var": "not a name"}, level=1)


def test_build_checks_the_LEVEL_and_not_only_the_spec():
    """MUTATION: drop the ``validate`` call from ``ck.build``.

    ⚠ Written because the obvious version of the test above reddens NOTHING
    under that mutation: ``env.build`` validates the spec too, so removing
    ``ck.build``'s call leaves the spec check standing and only the LEVEL
    check disappears. The level is the half no kind can check for itself —
    a kind knows which levels it serves, not which one this row claims.
    """
    with pytest.raises(ck.CredentialLevelUnsupported):
        ck.build(env.KIND_ID, {"var": VAR}, level=3)


# ---------------------------------------------------------------------------
# The env kind's spec
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec",
    [
        {},
        {"var": ""},
        {"var": 7},
        {"var": "2LEADING_DIGIT"},
        {"var": "HAS SPACE"},
        {"var": VAR, "value": "sk-this-is-the-mistake"},
    ],
    ids=["missing", "empty", "not-a-string", "leading-digit", "space", "unasked-key"],
)
def test_the_env_kind_refuses_a_spec_that_is_not_a_reference(spec):
    """MUTATION: relax any one clause of ``env.validate``.

    ⚠ The last case is the one that matters most and the one a shape-check
    alone would miss: a spec carrying a ``value`` key is somebody putting the
    CREDENTIAL where the POINTER goes. It is refused, never stripped —
    stripping would store a working configuration and silently discard the
    evidence that someone misunderstood where secrets live.
    """
    with pytest.raises(env.EnvSpecInvalid):
        env.validate(spec)


def test_validate_does_NOT_read_the_environment(monkeypatch):
    """The tempting wrong version, refused deliberately.

    Checking that the variable is SET would make a configuration valid on the
    machine that wrote it and invalid on the machine that runs it, and would
    make the same spec valid and invalid at different minutes of the same day.
    What is checked is the only thing true independent of any machine: the
    name is a name.
    """
    monkeypatch.delenv(VAR, raising=False)
    assert env.validate({"var": VAR}) is None


def test_a_refusal_never_echoes_the_spec_value():
    """The value here IS the variable name, which fingerprints the deployment.

    An exception is the one object in this package that reliably ends up
    somewhere it was not aimed — a log, a traceback, a rendered page. It names
    the FIELD and the RULE, which is all the person fixing it needs.
    """
    secretish = "ACME_PROD_ANTHROPIC_KEY_2026"
    with pytest.raises(env.EnvSpecInvalid) as exc:
        env.validate({"var": secretish + " "})
    assert secretish not in str(exc.value)


# ---------------------------------------------------------------------------
# The resolver the kind builds
# ---------------------------------------------------------------------------


def test_the_resolver_reads_the_environment_PER_CALL(monkeypatch):
    """MUTATION: capture ``os.environ[var]`` at build time.

    Two properties in one line. A rotated credential is picked up without
    reconstructing the client — and, load-bearing, the VALUE is a local of a
    frame that always returns rather than a free variable of a long-lived
    closure, which is round one of the credential review.
    """
    monkeypatch.setenv(VAR, "sk-first")
    resolver = ck.build(env.KIND_ID, {"var": VAR}, level=1)
    assert resolver() == "sk-first"
    monkeypatch.setenv(VAR, "sk-second")
    assert resolver() == "sk-second"


def test_the_resolver_carries_the_level_and_does_not_expire(monkeypatch):
    """The level is stamped on answers, so the resolver has to know it. An
    environment variable does not expire, so ``needs_refresh`` is False and
    the pre-call refresh path is never entered — which is what keeps level 1
    clear of ``no_silent_retry``."""
    monkeypatch.setenv(VAR, "sk-x")
    resolver = ck.build(env.KIND_ID, {"var": VAR}, level=1)
    assert resolver.level == 1
    assert resolver.expires_at() is None
    assert resolver.needs_refresh() is False


def test_the_variable_NAME_never_reaches_the_credential_failure(monkeypatch):
    """MUTATION: let ``os.environ[var]``'s KeyError propagate.

    An absent variable is ``CredentialUnavailable`` with fixed prose. A bare
    KeyError would carry the variable name to whoever catches it, and
    ``LLMCallFailed`` can put that on a page — where a deployment's
    environment layout would be printed to somebody's customer.
    """
    monkeypatch.delenv(VAR, raising=False)
    resolver = ck.build(env.KIND_ID, {"var": VAR}, level=1)
    with pytest.raises(CredentialUnavailable) as exc:
        resolver()
    assert VAR not in str(exc.value)
    assert str(exc.value) == CredentialUnavailable.MESSAGE
