"""Point the published contract harness at the adapter core actually ships.

**Why this file exists, and it is not a duplicate of
``test_transport_contract.py``.** That file verifies the HARNESS, against
lambdas. Every other adapter guard in this suite injects an ``opener`` —
``test_adapter_and_seam_guards.py`` says so in its own banner: *"Every guard
injects an opener, so none of them exercises the DEFAULT opener."* So core
published a contract, shipped one wire implementation, and never aimed the
first at the second **on the path a deployment actually takes**.

⚠ **The stub goes at ``urllib.request.urlopen``, NOT at the ``opener``
keyword.** Passing ``opener=`` would re-run the configuration round four of
the credential review was found in. ``build_transport`` is called with no
``opener`` here, on purpose, so ``seam.default_opener()`` is what resolves.
"""

from __future__ import annotations

import io
import json
import urllib.request

import pytest

from mindsos_llm import adapters
from mindsos_llm.contract import (
    FAILED,
    UNVERIFIABLE,
    UNVERIFIABLE_PROPERTIES,
    verify_transport,
)
from mindsos_llm.credentials import static_resolver
from mindsos_llm.adapters.anthropic import CREDENTIAL_HEADER, VENDOR_ID

SCHEMA = {"properties": {"days": {"type": "integer"}}}
ANSWER = {"days": 7}
KEY = "sk-not-a-real-key"


class _Response(io.BytesIO):
    status = 200


def _envelope(answer):
    return json.dumps(
        {"content": [{"type": "tool_use", "name": "extract", "input": answer}]}
    ).encode("utf-8")


@pytest.fixture
def wire(monkeypatch):
    """Stub the DEFAULT opener and record every request that reached it."""
    seen = []

    def urlopen(request, timeout=None):
        seen.append(request)
        return _Response(_envelope(ANSWER))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def _shipped_transport(**over):
    """The transport a deployment gets. No ``opener`` — that is the point."""
    kwargs = dict(
        resolve_credential=static_resolver(lambda: KEY),
        model_id="claude-x",
        resolve_prompt=lambda **_: "extract the number of days",
        tool_name="extract",
        tool_description="extract the declared fields",
    )
    kwargs.update(over)
    return adapters.build_transport(VENDOR_ID, **kwargs)


def test_the_shipped_adapter_passes_every_runnable_contract_check(wire):
    """Row 9 of the capability contract. Before this, core published
    ``verify_transport`` and had never run it against its own wire."""
    report = verify_transport(
        _shipped_transport(),
        prompt_iri="prompt:p",
        prompt_version=1,
        source_text="it took seven days",
        extraction_schema=SCHEMA,
    )
    assert not [c for c in report.checks if c.status == FAILED], str(report)
    assert report.ok


def test_the_verification_went_through_the_DEFAULT_opener(wire):
    """Without this the file could pass while proving nothing: a transport
    built with an injected opener would satisfy the check above and leave
    ``urllib.request.urlopen`` untouched, which is exactly the blind spot
    this file was written to close."""
    verify_transport(
        _shipped_transport(),
        prompt_iri="prompt:p",
        prompt_version=1,
        source_text="it took seven days",
        extraction_schema=SCHEMA,
    )
    assert wire, (
        "the default opener was never reached - this file is asserting "
        "nothing about the path a deployment takes"
    )


def test_the_default_opener_path_scrubs_the_credential(wire):
    """The scrub is guarded elsewhere against an INJECTED opener only. Here
    the composed request is captured on the default path, after the call."""
    verify_transport(
        _shipped_transport(),
        prompt_iri="prompt:p",
        prompt_version=1,
        source_text="it took seven days",
        extraction_schema=SCHEMA,
    )
    assert wire
    for request in wire:
        stores = (
            dict(getattr(request, "headers", {}) or {}),
            dict(getattr(request, "unredirected_hdrs", {}) or {}),
        )
        for store in stores:
            assert not [k for k in store if k.lower() == CREDENTIAL_HEADER], (
                f"{CREDENTIAL_HEADER!r} survived on the composed request"
            )
            assert KEY not in json.dumps(store, default=str)


def test_the_contract_names_the_credential_property_it_cannot_verify(wire):
    """ADR-0210 §5. The property above is ENFORCED and guarded, and it is
    still UNVERIFIABLE from outside a transport core did not write — so the
    report names it rather than reading as a clean bill of health."""
    report = verify_transport(
        _shipped_transport(),
        prompt_iri="prompt:p",
        prompt_version=1,
        source_text="it took seven days",
        extraction_schema=SCHEMA,
    )
    named = {c.name for c in report.checks if c.status == UNVERIFIABLE}
    assert "credential_not_retained_on_the_composed_request" in named
    assert named == {name for name, _ in UNVERIFIABLE_PROPERTIES}
