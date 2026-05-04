"""Tomli shim for host-side Python 3.10 / 3.11 test runs.

Production code targets Python 3.12 (test image), where ``tomllib`` is
stdlib. When tests run host-side on Python 3.10/3.11, this shim aliases
the ``tomli`` backport as ``tomllib`` so imports succeed. Harmless on
3.12+ — the conditional skips entirely.

Import this module from any conftest that transitively imports
``mindsos_cli.commands.confirm_phase`` (which imports ``tomllib``).

Originally lived at module-level in ``tests/phase_02/conftest.py``;
extracted in Phase 03 so Phase 03+ conftests can share.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    try:
        import tomli as _tomli_shim
        sys.modules.setdefault("tomllib", _tomli_shim)
    except ImportError:
        pass
