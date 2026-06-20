"""Device profiles — the "MindsOS knows where it is" substrate (P-8, F7).

Each device-instance boots from a :class:`DeviceProfile` carrying its
``device_type``. In future MindsOS the type is detected from the host
(computer / phone / robot); for the demo it is a static per-instance
declaration. The profile selects the device-type-exclusive content to
install (skill bundles in DM-2, embodied capacities in DM-3).

DM-1 only plumbs the field + the per-device KL name. The
``bundle_names`` / ``embodied`` lists are declared here but consumed
later (DM-2/DM-3) — the selective install is NOT wired at DM-1.

See the design log §3 (PB-M) and F7 in
``DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class DeviceProfile:
    """A device-type declaration + its install selection.

    Attributes:
        device_id: stable per-instance id == the brain's Server user_id
            (``mgr`` / ``arm1`` / ``arm2`` / ``conv``).
        device_type: the type that drives capability provisioning
            (``manager`` / ``arm-suction`` / ``arm-jaw`` / ``conveyor``).
        kl_name: the per-device Global metagraph name (PB-J — distinct
            per device so 4 Globals can coexist in one FalkorDB at DM-2;
            at DM-1 the KLs are in-memory and this is clarity-only).
        max_workers: IntelligenceLayer worker-pool size (mgr 2; arms +
            conveyor 1 — keep small under the single-process GIL, PB-E).
        bundle_names: skill bundles to install for this device type
            (DM-2; ``core`` installs everywhere). Declared, not consumed
            at DM-1.
        embodied: embodied-capacity install hooks (DM-3). Declared only.
    """

    device_id: str
    device_type: str
    kl_name: str
    max_workers: int = 1
    bundle_names: Tuple[str, ...] = field(default_factory=tuple)
    embodied: Tuple[str, ...] = field(default_factory=tuple)


#: The four demo device-instances. ``core`` is the common bundle every
#: device installs; the type-specific bundle installs only on its match
#: (DM-2 — selective install logic lives here in demo_backend, not in the
#: shipped Phase-50 driver).
DEVICE_PROFILES: Dict[str, DeviceProfile] = {
    "mgr": DeviceProfile(
        device_id="mgr",
        device_type="manager",
        kl_name="global::mgr",
        max_workers=1,  # DM-6 PB-T56.5: single-flight so the reroute fault stash is race-free
        bundle_names=("core", "manager"),
        embodied=(),  # no body
    ),
    "arm1": DeviceProfile(
        device_id="arm1",
        device_type="arm-suction",
        kl_name="global::arm1",
        max_workers=1,
        bundle_names=("core", "arm-suction"),
        embodied=("a1.move_to", "a1.suction_set", "a1.pick", "a1.place_at_cell"),
    ),
    "arm2": DeviceProfile(
        device_id="arm2",
        device_type="arm-jaw",
        kl_name="global::arm2",
        max_workers=1,
        bundle_names=("core", "arm-jaw"),
        embodied=("a2.move_to", "a2.jaw_set", "a2.pick", "a2.place_at_cell"),
    ),
    "conv": DeviceProfile(
        device_id="conv",
        device_type="conveyor",
        kl_name="global::conv",
        max_workers=1,
        bundle_names=("core", "conveyor"),
        embodied=("conv.run", "conv.stop", "conv.stage_at"),
    ),
}

#: Boot/dispatch order — manager last so the embodied brains are up
#: before the manager could (DM-4+) dispatch to them.
DEVICE_ORDER: List[str] = ["arm1", "arm2", "conv", "mgr"]


__all__ = ["DeviceProfile", "DEVICE_PROFILES", "DEVICE_ORDER"]
