"""Phase 04-v2 — SENT-1: sentinel `"UNSPECIFIED"` passes the cypher rel-type regex.

Adversarial-round-1 surfaced this conflict: the original `_unspecified`
sentinel (lowercase) failed the `^[A-Z][A-Z0-9_]{0,63}$` regex from
ADR-0021. SENT-1 lock chose `UNSPECIFIED` (uppercase) precisely because
it's a valid cypher rel-type. This test pins the property.
"""

from __future__ import annotations

from mindsos_core import validate_edge_type_identifier


def test_unspecified_sentinel_passes_cypher_regex():
    """The SENT-1 sentinel must satisfy ADR-0021's cypher rel-type regex."""
    # Should not raise.
    validate_edge_type_identifier("UNSPECIFIED")
