"""11 ALS subsystem registration skeletons (Chat A D9.2 + Chat B D-B52).

v1 ALS has 11 subsystems (Chat A's 10 + Chat B #11 planning-decomposition
calibration). Phase 47 registers them as skeletons — empty signal-source
weights, empty update-mechanism + validator pointers — into an
``ALSSubsystemRegistry``. Filling the concrete mechanism +
validator catalogs is unbuilt CORE work (RULES §8). Audit policies per the D9.2 table.
"""

from __future__ import annotations

from typing import Tuple

from .als_registry import ALSSubsystemRegistration, ALSSubsystemRegistry

#: (key, audit_policy) per Chat A D9.2 + Chat B D-B52.
ALS_SUBSYSTEM_SKELETONS: Tuple[Tuple[str, str], ...] = (
    ("wsd-candidate-scorer", "individual-review"),
    ("fol-rule-confidences", "individual-review"),
    ("promoted-pipelines-confidence", "batched-summary"),
    ("pipeline-finding-parameters", "batched-summary"),
    ("task-shape-recognition-priors", "individual-review"),
    ("goal-verification-thresholds", "individual-review"),
    ("class-generalization-materialization-policy", "auto-apply"),
    ("per-hierarchy-class-generalization-weights", "batched-summary"),
    ("sense-correlations", "auto-apply"),
    ("priority-scorer-attention-score", "batched-summary"),
    ("planning-decomposition-calibration", "batched-summary"),
)


def _skeleton(key: str, audit_policy: str) -> ALSSubsystemRegistration:
    return ALSSubsystemRegistration(
        parameter_set_iri=f"learned-parameters:{key}",
        signal_sources=(),
        update_mechanisms={},
        validation_methods=(),
        audit_policy=audit_policy,
        eligible_audit_scopes=frozenset({"local"}),
    )


def register_als_subsystems(registry: ALSSubsystemRegistry) -> ALSSubsystemRegistry:
    """Register the 11 ALS subsystem skeletons into ``registry``."""
    for key, audit_policy in ALS_SUBSYSTEM_SKELETONS:
        registry.register(key, _skeleton(key, audit_policy))
    return registry


__all__ = ["ALS_SUBSYSTEM_SKELETONS", "register_als_subsystems"]
