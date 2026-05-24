"""Phase 26b golden-output normalizer.

Per Phase 26b design log R0-PB-11 (b) + R4-PB-3 (a) — minimum strip-set
(UUID + ISO TS + INT TS-shaped field values). Expand during impl if
new ephemera surface.
"""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
_ISO_TS_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?"
)
_INT_TS_RE = re.compile(
    r'"(ts|proposed_at|shipped_at|created_at)"\s*:\s*\d+'
)


def normalize(text: str) -> str:
    """Strip ephemeral content for stable golden-output diff."""
    text = _UUID_RE.sub("<UUID>", text)
    text = _ISO_TS_RE.sub("<TS>", text)
    text = _INT_TS_RE.sub(r'"\1": <TS_INT>', text)
    return text
