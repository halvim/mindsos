"""S125.1's property against the BUILT transport (demo/dr-transport 73ed0df).

Run from a checkout of that branch:
    PYTHONPATH=. python scripts/critic/probe_scrub_property.py

For every link in the exception chain, every frame local of every traceback:
is the credential reachable through repr / vars() / header_items() — the three
roads the shipped guard itself walks? Three configurations: (A) the injected
fake opener the guard uses, (B) the REAL urllib opener against a refused local
port (no network needed), (C) an endpoint Request() rejects, which raises
BEFORE the try/finally that scrubs.

Composed by the critic: the sentinel key, the schema, the three endpoints. The
scrub, urllib and the traceback behavior are the tree's and CPython's.
NOTE the ('<module>', 'KEY', 'str') rows are this probe's own module constant,
not a finding about the mechanism. Repr-only; verdicts in coordination S127."""
from decision_records_demo.dr_transport import build_transport, TransportCallFailed

KEY = "sk-ant-SECRET-PROBE-0000"
SCHEMA = {"type": "object", "properties": {"fields": {"type": "array"}}}


def resolver(*, prompt_iri, prompt_version):
    return "PROMPT"


def chain(exc):
    seen = []
    while exc is not None and exc not in seen:
        seen.append(exc)
        exc = exc.__cause__ or exc.__context__
    return seen


def hits(exc):
    found = []
    for link in chain(exc):
        tb = link.__traceback__
        while tb is not None:
            frame = tb.tb_frame
            for name, val in list(frame.f_locals.items()):
                roads = []
                try:
                    if KEY in repr(val):
                        roads.append("repr")
                except Exception:
                    pass
                try:
                    if KEY in str(vars(val)):
                        roads.append("vars")
                except Exception:
                    pass
                try:
                    items = getattr(val, "header_items", None)
                    if items and KEY in str(items()):
                        roads.append("header_items")
                except Exception:
                    pass
                if roads:
                    found.append((type(link).__name__, frame.f_code.co_name,
                                  name, type(val).__name__, roads))
            tb = tb.tb_next
    return found


print("== raw output below this line ==")


def boom(request, **kw):
    raise RuntimeError("connection reset by peer")


t = build_transport(resolve_api_key=lambda: KEY, model_id="m",
                    resolve_prompt=resolver, tool_name="tool",
                    tool_description="d", opener=boom)
try:
    t(prompt_iri="p", prompt_version=1, source_text="s",
      extraction_schema=SCHEMA, timeout_s=1.0)
except TransportCallFailed as exc:
    print(repr(("A_injected_opener_raises:", hits(exc))))

t2 = build_transport(resolve_api_key=lambda: KEY, model_id="m",
                     resolve_prompt=resolver, tool_name="tool",
                     tool_description="d",
                     endpoint="http://127.0.0.1:9/v1/messages")
try:
    t2(prompt_iri="p", prompt_version=1, source_text="s",
       extraction_schema=SCHEMA, timeout_s=2.0)
except TransportCallFailed as exc:
    print(repr(("B_real_urllib_refused:", hits(exc))))

t3 = build_transport(resolve_api_key=lambda: KEY, model_id="m",
                     resolve_prompt=resolver, tool_name="tool",
                     tool_description="d",
                     endpoint="api.anthropic.com/v1/messages")
try:
    t3(prompt_iri="p", prompt_version=1, source_text="s",
       extraction_schema=SCHEMA, timeout_s=1.0)
except TransportCallFailed as exc:
    print(repr(("C_raised_TransportCallFailed:", hits(exc))))
except Exception as exc:
    print(repr(("C_escaped_as:", type(exc).__name__, str(exc)[:60], hits(exc))))
