"""demo_backend — the Robot Demo runtime envelope (DM-1 skeleton).

A *consumer* of the MindsOS stack (like ``mindsos_cli``): it imports
downward into the domain layers and is never imported by them (ADR-0010).
It is NOT a ``mindsos_*`` domain package and ships no ADRs.

Topology (plan P-1, Round-3): one process hosts **four independent
MindsOS device-instances** (mgr, arm1, arm2, conv), each with its own
``KnowledgeLayer`` (Global + Local L2) + ``CapacityLayer`` (L3) +
``IntelligenceLayer`` (L4), bootstrapped from a ``DeviceProfile`` (P-8).
The Server (auth/sessions/audit) is shared.

DM-1 scope: deployment + bootstrap + smoke only. No L2 seeds, L3 demo
capacities, bus, sim, or UI (those are DM-2+). See
``confirmation_docs/ROBOT_DEMO_MINDSOS_PLAN.md`` §8 (DM-1) +
``ROBOT_DEMO_MINDSOS_DESIGN_LOG.md``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0-dm1"
