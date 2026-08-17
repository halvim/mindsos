"""The step-1 gate: ONE real call, and the owner watches the answer come back.

Plan §0.4 item 7 step 1's gate is *"the owner sees a live answer return"* — not
a test, because the seam's whole design is that the callable is bound at boot
and is therefore outside any tree check (critic §118.4). This script is the
command that produces that sighting, run by the owner on the Linux box.

**Labelled seam, RULES §11.** Everything printed under ``> ANSWER`` is the
provider's bytes, unmodified, exactly as the transport returned them. Everything
else on screen — the prompt, the source sentence, the headings — was composed by
this lane and is printed above the answer so the seam is visible before the
output rather than after someone asks.

⚠ **The prompt below is a STEP-1 THROWAWAY and is deliberately not the demo's.**
The demo's prompt is stored, dated and printable, shown in full to the room, and
it lands with step 3 (plan §0.5 item 2). It lives here rather than in
``dr_transport`` because no prompt words may live in that module — a guard pins
it.

⚠ **The owner's fixture (email B) is NOT used here.** Putting it in the tree is
part of step 3, and nothing is built past its step.

    ANTHROPIC_API_KEY=... PYTHONPATH=. python3 decision_records_demo/dr_transport_smoke.py

Exit 0 means an answer came back. Exit 2 means no credential in the
environment. Exit 1 means the call failed, and the reason is printed.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_records_demo.dr_transport import (  # noqa: E402
    TransportCallFailed,
    build_transport,
)

MODEL_ID = "claude-haiku-4-5-20251001"

#: Composed by this lane, for this script only. Not the demo's prompt.
SMOKE_PROMPT = (
    "Read the message below. Report only what it STATES, never a conclusion "
    "you drew from it. For each field, give the value and a verbatim quote "
    "from the message that contains it."
)

#: Composed by this lane. Not the owner's fixture.
SMOKE_SOURCE = (
    "The operator was taken to hospital from the scene and is expected to be "
    "off work for at least six weeks."
)

SMOKE_SCHEMA = {
    "fields": [
        {"name": "hospital_transfer", "value": "<what the message says>",
         "quote": "<verbatim from the message>"},
        {"name": "off_work_period", "value": "<what the message says>",
         "quote": "<verbatim from the message>"},
    ]
}


def _resolve(*, prompt_iri, prompt_version):
    return SMOKE_PROMPT


def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("no ANTHROPIC_API_KEY in the environment", file=sys.stderr)
        return 2

    print("== composed by this lane ==")
    print("model    :", MODEL_ID)
    print("prompt   :", SMOKE_PROMPT)
    print("source   :", SMOKE_SOURCE)
    print("schema   :", SMOKE_SCHEMA)
    print()

    transport = build_transport(
        api_key=key, model_id=MODEL_ID, resolve_prompt=_resolve
    )
    try:
        answer = transport(
            prompt_iri="prompt:drdemo/step1_smoke",
            prompt_version=1,
            source_text=SMOKE_SOURCE,
            extraction_schema=SMOKE_SCHEMA,
            timeout_s=30.0,
        )
    except TransportCallFailed as exc:
        print("> CALL FAILED")
        print(exc)
        print("cause:", repr(exc.__cause__))
        return 1

    print("> ANSWER — the provider's bytes, unmodified")
    print(answer)
    print()
    print("type returned:", type(answer).__name__,
          "(text, undecoded — S-2 decodes in mindsos_capacity.llm)")

    print()
    print("== conformance harness ==")
    try:
        from mindsos_capacity.llm.contract import verify_transport
    except ImportError:
        print("NOT RUN — mindsos_capacity.llm is absent from the core this "
              "branch pins, which is why plan §0.5 item 9 makes this the "
              "owner's evidence. Run this same command from the `main` "
              "checkout with this directory on PYTHONPATH and the report "
              "prints here.")
        return 0
    report = verify_transport(
        transport,
        prompt_iri="prompt:drdemo/step1_smoke",
        prompt_version=1,
        source_text=SMOKE_SOURCE,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
