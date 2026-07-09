"""Lightweight structural check over a capacity catalog.

A record-less catalog is the set of capacities + DataStates + the
``PRODUCES`` / ``CONSUMES`` bipartite wiring already present in a live
:class:`~mindsos_capacity.views.CapacityLayerView`. This module computes
the structural x-ray that needs no install manifest and no code scan:

* **source** — a capacity CONSUMES a DataState that nothing PRODUCES; a
  pipeline entry point (e.g. raw text supplied by the user).
  Informational — without a manifest it is indistinguishable from a
  missing producer, so it is NOT flagged as a defect.
* **sink (terminal producer)** — a capacity PRODUCES a DataState that
  nothing CONSUMES; a legitimate terminal write (e.g. ``consolidate``
  writing the Local / MM). Informational.
* **orphan DataState** — a DataState with neither producer nor consumer;
  dead weight wired to nothing. The one verdict that flips ``ok``.

Manifest-aware real-defect detection (schema drift, code-scan via
``__module__``, install-record reconciliation) is the skill-verify
engine's job and lands in a later chat; this is the record-less subset
that home shares.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .views import CapacityLayerView

#: ``(capacity_iri, datastate_iri)`` pairs.
Pair = Tuple[str, str]


@dataclass
class CatalogReport:
    """Outcome of :func:`catalog_check`."""

    capacities: int
    datastates: int
    sources: List[Pair] = field(default_factory=list)
    sinks: List[Pair] = field(default_factory=list)
    orphans: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when no orphan DataState is present.

        Sources and sinks are informational (indistinguishable from
        legitimate entry points / terminal writes without a manifest);
        only an orphan — a DataState wired to nothing — flips ``ok``.
        """
        return not self.orphans


def catalog_check(view: CapacityLayerView) -> CatalogReport:
    """Compute the structural x-ray over ``view``.

    Pure and read-only — walks the bipartite ``PRODUCES`` / ``CONSUMES``
    edges via the view's producer/consumer accessors. Deterministic
    ordering (sorted) so callers can diff reports.
    """
    caps = list(view.iter_capacities())
    datastates = list(view.iter_datastates())

    # Producer / consumer counts per DataState IRI.
    ds_iris = [d.node_id for d in datastates]
    produced = {iri: len(view.producers_of(iri)) for iri in ds_iris}
    consumed = {iri: len(view.consumers_of(iri)) for iri in ds_iris}

    sources: List[Pair] = []
    sinks: List[Pair] = []
    for cap in caps:
        cap_iri = cap.node_id
        for ds_iri in view.inputs_of(cap_iri):
            # Consumed with zero producers -> a pipeline entry point.
            if produced.get(ds_iri, 0) == 0:
                sources.append((cap_iri, ds_iri))
        for ds_iri in view.outputs_of(cap_iri):
            # Produced with zero consumers -> a terminal sink.
            if consumed.get(ds_iri, 0) == 0:
                sinks.append((cap_iri, ds_iri))

    orphans = [iri for iri in ds_iris if produced.get(iri, 0) == 0 and consumed.get(iri, 0) == 0]

    return CatalogReport(
        capacities=len(caps),
        datastates=len(datastates),
        sources=sorted(sources),
        sinks=sorted(sinks),
        orphans=sorted(orphans),
    )


__all__ = ["CatalogReport", "catalog_check", "Pair"]
