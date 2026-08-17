"""Probe 119.4: a MODEL-formatted (non-ISO) as_of through the REAL
policy_lookup_v0 exception routing.

Runs against origin/main ead3bd1:
    PYTHONPATH=. python scripts/critic/probe_model_asof.py
The fake kl view supplies one real-shaped edition node; edition_in_force and
the impl's exception routing are the tree's. Fixture dates COMPOSED by the
critic. Repr-only; verdicts in coordination S120."""
from types import SimpleNamespace
from mindsos_capacity.builtins.policy_lookup_v0 import (
    build_policy_limit_lookup, PolicyStoreUnreachableError,
)

EDITION = SimpleNamespace(properties={
    "policy_id": "drdemo.dwelling_limit", "version": "2023.1",
    "in_force_from": "2023-01-01", "in_force_to": "2023-12-31",
    "stated_value": 350000, "text": "The dwelling coverage limit is 350,000.",
})
view = SimpleNamespace(iter_nodes=lambda role, type_=None: [EDITION])
kl = SimpleNamespace(global_view=lambda: view)

cap = build_policy_limit_lookup(
    name="drdemo.dwelling_limit_lookup",
    policy_id="drdemo.dwelling_limit",
    source_identity_phrase="the dwelling-coverage limit policy",
    question="What dwelling coverage limit was in force on {as_of}?",
    limit_datastate_iri="datastate:drdemo.dwelling_limit",
    as_of_datastate_iri="datastate:drdemo.assessed_as_of",
)

print("== raw output below this line ==")
for label, as_of in (("iso_control", "2023-06-01"),
                     ("model_prose_date", "July 3rd, 2023"),
                     ("model_iso_slash", "2023/06/01")):
    try:
        out = cap.implementation(context=SimpleNamespace(kl=kl),
                                 **{"datastate:drdemo.assessed_as_of": as_of})
        rec = out.get("datastate:drdemo.dwelling_limit_origin") or {}
        print(repr(("[" + label + "]", "value:", out["datastate:drdemo.dwelling_limit"],
                    {"admitted": rec.get("admitted"), "refusal_reason": rec.get("refusal_reason")})))
    except PolicyStoreUnreachableError as exc:
        print(repr(("[" + label + "]", "RAISED PolicyStoreUnreachableError",
                    "reason_token:", getattr(exc, "REASON", None), "str:", str(exc))))
