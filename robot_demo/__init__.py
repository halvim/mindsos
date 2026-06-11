"""robot_demo — the MindsOS Robot Demo (consumer of the shipped stack).

Self-contained umbrella for the demo: ``backend/`` (the runtime package),
``tests/`` (scenario tests, outside the MindsOS cumulative gate),
``docs/`` (what/why/how), ``deploy/`` (compose overlay + Linux test
runner). Imports downward into ``mindsos_*`` only; nothing in the domain
stack imports this (ADR-0010).

Entry point: ``python -m robot_demo.backend.main``.
See ``robot_demo/README.md`` and ``confirmation_docs/ROBOT_DEMO_MINDSOS_PLAN.md``.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0-dm1"
