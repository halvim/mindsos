"""L2 references — the known patterns observations are matched against (§8).

References = L2 knowledge. This library is what grows additively (the
leaf-learning); the L3 capacities and L4 pipelines stay fixed. A
**request_reference** verdict asks to add a new entry here.

v0 holds only the *given* domain reference (`cycle_reference`). Taught
disturbances / appliance signatures are added here later, each as one new
reference — that adding **is** the leaf-learning. Persisting them as durable
L2 ``learned-parameters`` nodes is v1 (arc3 B6: L2 is the layer that works).

These are plain values seeded into the pipeline blackboard as the
`cycle_reference` / `known_references` DataStates. The sinusoid basis lives
here (in the reference), NOT baked into `fit_reference` — the capacity reads
`reference["form"]` and builds the basis from it.
"""

from __future__ import annotations

from typing import Dict, List


def cycle_reference() -> Dict:
    """The given domain reference: a grid cycle is a sinusoid at ~f0.

    `fit_reference` reads `form` to choose its basis; `name` is what the
    verdict reports as the reference that was matched.
    """
    return {"name": "cycle_reference", "form": "sinusoid",
            "params": ["DC", "a", "b"]}


def known_references() -> List[Dict]:
    """The reference library. v0 = just the given cycle reference.

    The request_reference loop only becomes meaningful once this holds
    enough references that a novel observation is genuinely "none of these".
    """
    return [cycle_reference()]
