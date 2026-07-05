# ARC packaging — CONFIRMED 2026-07-04

ARC packaged as an on-top installable intelligence. NOT part of core (no
mindsos wheel change, no phase number, no version bump).

Shipped (arc-solver, arc_dist/): own distribution `mindsos-arc` (own pyproject,
install_requires=mindsos) holding `mindsos_arc/{capacities,grids,solver}.py` +
`bundle/manifest.toml` (L3-only: 32 caps / 39 datastates, realm `arc`, entry
point `mindsos_arc.capacities:install_arc`; L2/L4 empty). Installs through the
Phase-50 skill path unchanged.

Gate (Linux, py3.11): `arc_dist/tests` 6 passed — manifest↔installer parity +
warm-layer idempotency + real install_skill/activate e2e.

Key: install_arc made warm-layer idempotent (builtins-triple); manifest roster
generated from the live catalog (gen_manifest.py) + parity test guards drift;
self-contained in the `arc` realm (no core datastate dependency).

Deferred (core-requests, not done): Local-scope caps (driver passes no session →
Global-only); in-place upgrade (v2). Live start→install→probe loop consumes the
resident-runtime REPL chat. Note: install_requires="mindsos" is nominal (mindsos
not on PyPI) — on-top install is local/editable; gate runs via PYTHONPATH.
