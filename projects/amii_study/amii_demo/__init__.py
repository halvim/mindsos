"""Shared runnable core for the MindsOS × Amii live demo.

Single source of truth imported by the guard test, the live demo, and the
on-device profiler — so the demo surface has ONE place to maintain against
the core API. A drift in core then breaks one file, caught by the guard
test, instead of silently rotting several copies.
"""
