"""Per-process skill activation (Phase 50 — ADR-0183 §6 stage 2).

Capacities are per-process in-memory (design log §0.1-2): an installed
skill's durable footprint is its L2 content + install record; its L3
registrations must be re-run every process start. A **free function**
per the Phase 44 CR-3/PB-38 precedent — not a ``MindsOSServer`` method.

v1 caller: the ``mindsos skill activate`` CLI verb (R1 PB-4 — flag/verb
over server-startup hook until a server consumer exists).
"""

from __future__ import annotations

import importlib
from typing import Any, List, Tuple

from .records import latest_records_by_bundle


def apply_installed_skills(cl: Any, kl: Any) -> Tuple[str, ...]:
    """Re-run the L3 installer entry points of every ``installed`` bundle.

    Walks the latest record per bundle, ``seq``-ascending — install
    order, which already satisfies ``requires_bundles`` ordering because
    preflight enforced dependencies at install time (a required bundle
    always carries an earlier ``seq``). Uninstalled / failed bundles are
    skipped (ADR-0183 §8 step 4). Installer idempotency is the builtins
    triple — re-running on a fresh process installs; on a warm layer
    no-ops.

    Returns the activated bundle names, activation order.
    """
    latest = latest_records_by_bundle(kl)
    ordered = sorted(
        (view for view in latest.values() if view.status == "installed"),
        key=lambda v: v.seq,
    )

    activated: List[str] = []
    for view in ordered:
        for spec in view.value.get("l3_installers") or []:
            module_name, func_name = spec.split(":", 1)
            fn = getattr(importlib.import_module(module_name), func_name)
            fn(cl)
        activated.append(view.bundle_name)
    return tuple(activated)


__all__ = ["apply_installed_skills"]
