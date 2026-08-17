"""Pre-build design probe on coordination S124: does moving the credential out
of `transport`'s locals take it off the traceback road, and does the proposed
unasked-key predicate hold on a schema that declares no `properties`?

Runs anywhere with stdlib only (it simulates the proposed shape rather than
importing it — the ship does not exist yet):
    python scripts/critic/probe_124_design.py
Composed by the critic: the sentinel key, the simulated helper split, the three
schemas. The Request/traceback behavior is CPython's. Repr-only; verdicts in
coordination S125.

NOTE the first output row is this probe's own module-level KEY constant, not a
finding about the mechanism — the load-bearing row is the `transport_sim` frame
holding a Request whose repr hides the key and whose `.headers` does not."""
import urllib.request

KEY = "sk-ant-SECRET-0000"


def build_request(resolve_api_key, endpoint):
    api_key = resolve_api_key()           # local of THIS frame only
    return urllib.request.Request(
        endpoint, data=b"{}", method="POST",
        headers={"content-type": "application/json", "x-api-key": api_key})


def transport_sim():
    request = build_request(lambda: KEY, "https://api.anthropic.com/v1/messages")
    raise RuntimeError("connection reset by peer")   # `request` is a live local


print("== raw output below this line ==")
try:
    transport_sim()
except RuntimeError as exc:
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        for name, val in list(frame.f_locals.items()):
            try:
                as_str = str(val)
            except Exception:
                as_str = ""
            hit_str = KEY in as_str
            hit_attr = False
            for attr in ("headers", "_Request__headers", "header_items"):
                try:
                    got = getattr(val, attr, None)
                    got = got() if callable(got) else got
                    if got is not None and KEY in str(got):
                        hit_attr = True
                except Exception:
                    pass
            if hit_str or hit_attr:
                print(repr((frame.f_code.co_name, name, type(val).__name__,
                            "in_str(local):", hit_str, "in_attr:", hit_attr,
                            "str(local):", as_str[:60])))
        tb = tb.tb_next


def unasked_keys(schema, answer):
    """S124.2's predicate as described: top-level keys not in declared properties."""
    declared = set((schema.get("properties") or {}).keys())
    return sorted(set(answer) - declared)


ANSWER = {"fields": [{"name": "x", "value": "v", "quote": "q"}]}
for label, schema in (
    ("schema_with_properties",
     {"type": "object", "properties": {"fields": {}}, "required": ["fields"]}),
    ("schema_without_properties", {"type": "object"}),
    ("schema_using_ref_only", {"$ref": "#/defs/x"}),
):
    print(repr((label, "unasked_keys_computed:", unasked_keys(schema, ANSWER))))
