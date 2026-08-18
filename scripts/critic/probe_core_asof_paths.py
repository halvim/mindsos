"""Stage-2 on feat/policy-as-of-not-a-date (67e4021), Q2: enumerate every date
path through policy_lookup_v0 and RUN each one.

Run from a checkout of that branch:
    PYTHONPATH=. python scripts/critic/probe_core_asof_paths.py

Twelve paths: six asker-side as_of shapes, two store-side bounds, no-edition,
ambiguous, store-unreadable and no-KL. Composed by the critic: the fake view,
the edition props and the twelve inputs. Every classification, reason and raise
is the tree's. Repr-only; verdicts in coordination S146."""
from types import SimpleNamespace

from mindsos_capacity.builtins.policy_lookup_v0 import build_policy_limit_lookup


def edition(**over):
    props = {"policy_id": "p", "version": "v1", "in_force_from": "2023-01-01",
             "in_force_to": "2023-12-31", "stated_value": 350000, "text": "t"}
    props.update(over)
    return SimpleNamespace(properties=props)


def capacity():
    return build_policy_limit_lookup(
        name="probe_lookup", policy_id="p",
        source_identity_phrase="the probe policy",
        question="What limit was in force on {as_of}?",
        limit_datastate_iri="datastate:probe.limit",
        as_of_datastate_iri="datastate:probe.as_of")


def run(label, as_of, nodes, kl_raises=False, no_kl=False):
    view = SimpleNamespace(iter_nodes=lambda role, type_=None: nodes)

    def global_view():
        if kl_raises:
            raise RuntimeError("store down")
        return view

    kl = None if no_kl else SimpleNamespace(global_view=global_view)
    try:
        out = capacity().implementation(context=SimpleNamespace(kl=kl),
                                        **{"datastate:probe.as_of": as_of})
        record = out.get("datastate:probe.limit_origin") or {}
        print(repr((label, "RETURNED value:", out["datastate:probe.limit"],
                    "reason:", record.get("refusal_reason"),
                    "env_fault:", record.get("environment_fault"),
                    "detail:", (record.get("refusal_detail") or "")[:70])))
    except Exception as exc:
        print(repr((label, "RAISED", type(exc).__name__,
                    "REASON attr:", getattr(exc, "REASON", None),
                    str(exc)[:70])))


print("== raw output below this line ==")
run("iso_ok", "2023-06-01", [edition()])
run("asof_not_a_date", "June 3rd", [edition()])
run("asof_slashes", "2023/06/01", [edition()])
run("asof_None", None, [edition()])
run("asof_int", 20230601, [edition()])
run("asof_empty", "", [edition()])
run("stored_from_malformed", "2023-06-01", [edition(in_force_from="01/01/2023")])
run("stored_to_malformed", "2023-06-01", [edition(in_force_to="31-12-2023")])
run("no_edition_covers", "2019-06-01", [edition()])
run("ambiguous", "2023-06-01", [edition(), edition(version="v2")])
run("store_unreadable", "2023-06-01", [edition()], kl_raises=True)
run("no_kl_at_all", "2023-06-01", [edition()], no_kl=True)
