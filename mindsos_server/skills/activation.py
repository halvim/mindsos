"""Per-process skill activation (Phase 50 — ADR-0183 §6 stage 2).

Capacities are per-process in-memory (design log §0.1-2): an installed
skill's durable footprint is its L2 content + install record; its L3
registrations must be re-run every process start. A **free function**
per the Phase 44 CR-3/PB-38 precedent — not a ``MindsOSServer`` method.

Resilience contract (ADR-0183 §am-2 — skill-activation resilience CR).
Activation is **best-effort at boot** and **strict on explicit
invocation**. Each bundle is processed in two phases:

* **resolve** — import + attribute-lookup of every L3 installer entry
  point (no side effects on ``cl``), via
  :func:`mindsos_server.skills.entry_points.resolve_entry_point`. A
  resolve failure means the bundle is *absent in this process* — the
  common cross-venv/lane case: a bundle recorded Globally in Falkor whose
  module was pip-installed only in another checkout. Nothing was
  registered, so the bundle is skipped cleanly.
* **apply** — call each installer ``fn(cl)``. A mid-apply failure may
  leave the bundle *partially* registered; there is **no** per-bundle
  rollback (none exists in the layer — a partial registration is repaired
  by the next process's idempotent ``if_exists='upsert'`` re-run, the
  house recovery grain). The bundle is skipped and reported, flagged as
  possibly partially registered.

With ``strict=True`` (the default — every pre-existing call site is
byte-identical) either failure re-raises: an explicit ``mindsos skill
activate`` that cannot activate must fail loudly. ``boot_brain`` passes
``strict=False`` so one absent or broken bundle never bricks the brain.

Skips are **process-local**: a module missing in *this* venv says nothing
about the bundle's validity elsewhere, so they are reported (via
:class:`ActivationReport` and a ``log.warning``) and never written back to
the durable, Global record, which stays ``installed``.

v1 explicit caller: the ``mindsos skill activate`` CLI verb (R1 PB-4 —
flag/verb over server-startup hook until a server consumer exists);
``boot_brain`` is the resilient caller.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, List, Tuple

from .entry_points import EntryPointError, resolve_entry_point
from .records import latest_records_by_bundle

log = logging.getLogger(__name__)


class ActivationReport(tuple):
    """Activated bundle names — **is** a ``tuple`` of them, activation
    order — carrying an additional ``skipped`` roster.

    Iterating / equality / ``len`` behave exactly like the historical
    ``Tuple[str, ...]`` return, so pre-existing callers that treated the
    result as a tuple of activated names are unchanged (additive-inert).
    ``skipped`` is a tuple of ``(bundle_name, reason)`` pairs for bundles
    that did not (fully) activate.
    """

    _skipped: Tuple[Tuple[str, str], ...]

    def __new__(
        cls,
        activated: Iterable[str] = (),
        skipped: Iterable[Tuple[str, str]] = (),
    ) -> "ActivationReport":
        self = super().__new__(cls, tuple(activated))
        self._skipped = tuple(skipped)
        return self

    @property
    def activated(self) -> Tuple[str, ...]:
        """The activated bundle names (same as iterating ``self``)."""
        return tuple(self)

    @property
    def skipped(self) -> Tuple[Tuple[str, str], ...]:
        """``(bundle_name, reason)`` for each bundle that did not activate."""
        return self._skipped

    def __repr__(self) -> str:  # pragma: no cover — cosmetic
        return (
            f"ActivationReport(activated={tuple(self)!r}, "
            f"skipped={self._skipped!r})"
        )


def apply_installed_skills(
    cl: Any, kl: Any, *, strict: bool = True
) -> ActivationReport:
    """Re-run the L3 installer entry points of every ``installed`` bundle.

    Walks the latest record per bundle, ``seq``-ascending — install order,
    which already satisfies ``requires_bundles`` ordering because preflight
    enforced dependencies at install time (a required bundle always carries
    an earlier ``seq``, and the reverse-dependency uninstall guard keeps it
    so). Uninstalled / failed bundles are skipped (ADR-0183 §8 step 4).
    Installer idempotency is the builtins triple — re-running on a fresh
    process installs; on a warm layer no-ops.

    ``strict=True`` (default) re-raises on the first resolve/apply failure —
    an explicit activate that cannot activate fails loudly. ``strict=False``
    (``boot_brain``) skips-and-reports so a single absent or broken bundle
    never bricks boot.

    Returns an :class:`ActivationReport` — a tuple of the activated bundle
    names (activation order) plus a ``skipped`` roster.
    """
    latest = latest_records_by_bundle(kl)
    ordered = sorted(
        (view for view in latest.values() if view.status == "installed"),
        key=lambda v: v.seq,
    )

    activated: List[str] = []
    skipped: List[Tuple[str, str]] = []
    for view in ordered:
        specs = view.value.get("l3_installers") or []
        # ── resolve: import + getattr, no side effects on cl ──────────
        try:
            fns = [resolve_entry_point(spec) for spec in specs]
        except EntryPointError as exc:
            if strict:
                raise
            log.warning(
                "skill %r not activated: %s — its L3 installer is not "
                "importable in this process; its capacities are absent.",
                view.bundle_name,
                exc,
            )
            skipped.append((view.bundle_name, f"unresolved: {exc}"))
            continue
        # ── apply: may partially register; no rollback exists ─────────
        try:
            for fn in fns:
                fn(cl)
        except Exception as exc:  # noqa: BLE001 — resilience contract
            if strict:
                raise
            log.warning(
                "skill %r failed during activation (%s: %s); it may be "
                "partially registered and is repaired on the next boot's "
                "idempotent re-run.",
                view.bundle_name,
                exc.__class__.__name__,
                exc,
            )
            skipped.append(
                (view.bundle_name, f"apply-failed (possibly partial): {exc}")
            )
            continue
        activated.append(view.bundle_name)
    return ActivationReport(activated, skipped)


__all__ = ["ActivationReport", "apply_installed_skills"]
