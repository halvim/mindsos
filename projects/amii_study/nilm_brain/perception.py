"""Perception family — the §2 interpretation boundary.

`parse_raw` is the one perception capacity: it turns the raw submetered
record into the three floor atoms (voltage, current, time) using given
channel metadata. This is the interpretation boundary — below it, values are
representation-relative readings, not interpretations.

Body contract (verified against core `call_capacity`): inputs arrive as
`**kw` keyed by **DataState IRI**; the body returns an explicit
`{output_iri: value}` dict. `context` is accepted and ignored.
"""

from __future__ import annotations

import numpy as np

from mindsos_capacity import Capacity, CATEGORY_PERCEPTION

from .ontology import RAW_DATA, FS, CHANNEL_MAP, VOLTAGE, CURRENT, TIME


def _parse_raw(**kw):
    raw = kw[RAW_DATA.iri]
    fs = kw[FS.iri]
    cmap = kw[CHANNEL_MAP.iri]
    arr = np.asarray(raw, dtype=float)
    volt = arr[:, cmap["voltage"]]
    cur = arr[:, cmap["current"]]
    time = np.arange(len(arr)) / float(fs)
    return {VOLTAGE.iri: volt, CURRENT.iri: cur, TIME.iri: time}


def register_perception(cl, session):
    caps = [
        Capacity(
            name="parse_raw", category=CATEGORY_PERCEPTION,
            inputs=(RAW_DATA.iri, FS.iri, CHANNEL_MAP.iri),
            outputs=(VOLTAGE.iri, CURRENT.iri, TIME.iri),
            implementation=_parse_raw,
            description="raw_data -> {voltage, current, time} (the §2 interpretation boundary)",
        ),
    ]
    for c in caps:
        cl.register_capacity(c, session=session, if_exists="upsert")
    return [c.iri for c in caps]
