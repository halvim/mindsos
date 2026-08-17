"""S127 re-check at demo/dr-transport 18b68a0 — the property under the REAL
opener, (b)'s build-time refusal, and the new guard's claim on the SUCCESS door.

Run from a checkout of that branch:
    PYTHONPATH=. python scripts/critic/probe_scrub_property_v2.py

Supersedes probe_scrub_property.py, whose case B used an http:// endpoint and
whose case C used a schemeless one — 18b68a0 refuses BOTH at build time, which
is condition (b) working. Case B here goes over https:// to a refused local
port, so the real urllib path still runs with no network.

Composed by the critic: the sentinel key, the schema, the endpoints, the
recording opener. The scrub, the validation, urllib and the traceback behavior
are the tree's and CPython's. Repr-only; verdicts in coordination S129."""
import json

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
    out = []
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
                    out.append((type(link).__name__, frame.f_code.co_name,
                                name, type(val).__name__, roads))
            tb = tb.tb_next
    return out


print("== raw output below this line ==")

for label, endpoint in (("schemeless", "api.anthropic.com/v1/messages"),
                        ("http", "http://api.anthropic.com/v1/messages"),
                        ("empty", "")):
    try:
        build_transport(resolve_api_key=lambda: KEY, model_id="m",
                        resolve_prompt=resolver, tool_name="t",
                        tool_description="d", endpoint=endpoint)
        print(repr(("build_" + label, "ACCEPTED")))
    except ValueError as exc:
        print(repr(("build_" + label, "REFUSED", str(exc))))

live = build_transport(resolve_api_key=lambda: KEY, model_id="m",
                       resolve_prompt=resolver, tool_name="tool",
                       tool_description="d",
                       endpoint="https://127.0.0.1:9/v1/messages")
try:
    live(prompt_iri="p", prompt_version=1, source_text="s",
         extraction_schema=SCHEMA, timeout_s=2.0)
except TransportCallFailed as exc:
    rows = [r for r in hits(exc) if r[1] != "<module>"]
    print(repr(("B_real_urllib_https_refused (module-constant rows filtered):", rows)))


class Recording:
    """Captures the composed Request and answers with a forced tool reply."""

    def __init__(self):
        self.request = None

    def __call__(self, request, **kwargs):
        self.request = request

        class _R:
            status = 200

            def read(self):
                return json.dumps({"content": [
                    {"type": "tool_use", "name": "tool", "input": {"fields": []}}
                ]}).encode("utf-8")

        return _R()


recording = Recording()
answered = build_transport(resolve_api_key=lambda: KEY, model_id="m",
                           resolve_prompt=resolver, tool_name="tool",
                           tool_description="d", opener=recording)
returned = answered(prompt_iri="p", prompt_version=1, source_text="s",
                    extraction_schema=SCHEMA, timeout_s=1.0)
print(repr(("success_door_returned:", returned)))
print(repr(("success_door_request_headers:", dict(recording.request.headers),
            "unredirected:", dict(recording.request.unredirected_hdrs),
            "key_present:", KEY in repr(recording.request.headers)
            + repr(recording.request.unredirected_hdrs))))
