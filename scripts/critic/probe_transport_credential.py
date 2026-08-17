"""Probe 122.7-cred: the credential guard walks str() over the __cause__/
__context__ chain. Does the key survive the ONE hop it does not walk —
traceback frame locals?

Runs against the ship extract (demo/dr-transport db96f2b):
    PYTHONPATH=. python scripts/critic/probe_transport_credential.py
Composed by the critic: the fake raising opener and the sentinel key. The
frame-locals exposure is the tree's. Repr-only; verdict in coordination S123."""
from decision_records_demo.dr_transport import build_transport, TransportCallFailed

KEY = "sk-ant-SECRET-0000"

def resolver(*, prompt_iri, prompt_version):
    return "PROMPT"

def boom(request, **kw):
    raise RuntimeError("connection reset by peer")

def chain(exc):
    seen = []
    while exc is not None and exc not in seen:
        seen.append(exc)
        exc = exc.__cause__ or exc.__context__
    return seen

t = build_transport(api_key=KEY, model_id="m", resolve_prompt=resolver,
                    tool_name="tool", tool_description="d", opener=boom)

print("== raw output below this line ==")
try:
    t(prompt_iri="p", prompt_version=1, source_text="s",
      extraction_schema={"type": "object"}, timeout_s=1.0)
except TransportCallFailed as exc:
    print(repr(("guard_checks__str_chain_hits:",
                [type(l).__name__ for l in chain(exc) if KEY in str(l)])))
    tb_hits = []
    for link in chain(exc):
        tb = link.__traceback__
        while tb is not None:
            for name, val in list(tb.tb_frame.f_locals.items()):
                try:
                    if KEY in str(val):
                        tb_hits.append((type(link).__name__,
                                        tb.tb_frame.f_code.co_name, name))
                except Exception:
                    pass
            tb = tb.tb_next
    print(repr(("guard_does_NOT_check__traceback_frame_locals_hits:", tb_hits)))
