"""ALS subsystem registry (ADR / Chat A D9.1).

L4-owned registry of ALS subsystem registrations. The dataclass shape is
the Chat A D9.1 contract; all IRIs point to L3 capabilities. The v0
catalog is **empty** — the concrete 10-subsystem catalog (D9.2) lands
when WSD installation ships. Global aggregation has no L4 home (D9.4 →
L0 admin); this is registration + lookup only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple


@dataclass
class ALSSubsystemRegistration:
    parameter_set_iri: str
    signal_sources: Tuple[Tuple[str, float], ...]
    update_mechanisms: Dict[str, str]
    validation_methods: Tuple[str, ...]
    audit_policy: str
    eligible_audit_scopes: FrozenSet[str]


_VALID_AUDIT_POLICIES = frozenset(
    {"auto-apply", "batched-summary", "individual-review"}
)


class ALSSubsystemRegistry:
    def __init__(self) -> None:
        self._subsystems: Dict[str, ALSSubsystemRegistration] = {}

    def register(self, key: str, registration: ALSSubsystemRegistration) -> None:
        if registration.audit_policy not in _VALID_AUDIT_POLICIES:
            raise ValueError(
                f"invalid audit_policy {registration.audit_policy!r}; "
                f"expected one of {sorted(_VALID_AUDIT_POLICIES)}"
            )
        if key in self._subsystems:
            raise ValueError(f"ALS subsystem {key!r} already registered")
        self._subsystems[key] = registration

    def get(self, key: str) -> ALSSubsystemRegistration:
        return self._subsystems[key]

    def keys(self) -> Tuple[str, ...]:
        return tuple(self._subsystems.keys())

    def __len__(self) -> int:
        return len(self._subsystems)


__all__ = ["ALSSubsystemRegistry", "ALSSubsystemRegistration"]
