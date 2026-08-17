"""Probe 122.7 forcing + Mapping-return: can any reply shape reach `return
answer` carrying what the caller did not ask for?

Runs against the ship extract (demo/dr-transport db96f2b):
    PYTHONPATH=. python scripts/critic/probe_transport_forcing.py
Envelopes composed by the critic; routing is the tree's. Repr-only; verdict
in coordination S123."""
import json
from decision_records_demo.dr_transport import build_transport, TransportCallFailed

def resolver(*, prompt_iri, prompt_version):
    return "PROMPT"

class Resp:
    def __init__(self, payload, status=200):
        self.status = status
        self._b = json.dumps(payload).encode()
    def read(self):
        return self._b

def call(payload, schema={"type": "object"}):
    def op(request, **kw):
        return Resp(payload)
    t = build_transport(api_key="k", model_id="m", resolve_prompt=resolver,
                        tool_name="tool", tool_description="d", opener=op)
    return t(prompt_iri="p", prompt_version=1, source_text="s",
             extraction_schema=schema, timeout_s=1.0)

print("== raw output below this line ==")
extra = {"content": [{"type": "tool_use", "name": "tool",
         "input": {"fields": [{"name": "x", "value": "v", "quote": "q"}],
                   "SECRET_INJECTED": "model added this", "confidence": 0.99}}]}
print(repr(("extra_keys_passthrough:", call(extra))))

two = {"content": [
    {"type": "tool_use", "name": "tool", "input": {"first": True}},
    {"type": "tool_use", "name": "tool", "input": {"second": True}}]}
print(repr(("two_tool_blocks_returns:", call(two))))

for label, payload in (
    ("wrong_tool_name", {"content": [{"type": "tool_use", "name": "other", "input": {"x": 1}}]}),
    ("non_mapping_input", {"content": [{"type": "tool_use", "name": "tool", "input": ["a"]}]}),
):
    try:
        print(repr((label + ":", call(payload))))
    except TransportCallFailed as e:
        print(repr((label + " RAISES:", str(e)[:50])))
