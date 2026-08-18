"""S136.2(E): what the shipped transport does when a provider fails
MID-RESPONSE rather than before it.

Run from a checkout of demo/decision-records at dr-routing-policy-confirmed:
    PYTHONPATH=. python scripts/critic/probe_midresponse.py

Composed by the critic: the three failing openers (truncated body, connection
killed mid-read, 429). The classification is the tree's. This closes the
CLASSIFICATION half of the never-watched-a-real-failure gap; the PAGE half
still needs step 3. Repr-only; verdicts in coordination S137."""
from decision_records_demo.dr_transport import build_transport, TransportCallFailed

SCHEMA = {"type": "object", "properties": {"fields": {}}}


def resolver(*, prompt_iri, prompt_version):
    return "PROMPT"


class Resp:
    def __init__(self, body, status=200):
        self.status = status
        self._body = body

    def read(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def call(opener):
    transport = build_transport(resolve_api_key=lambda: "k", model_id="m",
                                resolve_prompt=resolver, tool_name="tool",
                                tool_description="d", opener=opener)
    return transport(prompt_iri="p", prompt_version=1, source_text="s",
                     extraction_schema=SCHEMA, timeout_s=1.0)


CASES = {
    "truncated_body":
        lambda request, **kw: Resp(b'{"content":[{"type":"tool_'),
    "connection_killed_mid_read":
        lambda request, **kw: Resp(ConnectionResetError("peer reset mid-body")),
    "429_with_retry_after":
        lambda request, **kw: Resp(b'{"error":{"type":"rate_limit_error"}}', status=429),
}

print("== raw output below this line ==")
for label, opener in CASES.items():
    try:
        print(repr((label, "RETURNED", call(opener))))
    except TransportCallFailed as exc:
        print(repr((label, "RAISED", type(exc).__name__, str(exc),
                    "cause:", type(exc.__cause__).__name__ if exc.__cause__ else None)))
