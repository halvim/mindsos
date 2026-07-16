"""Shared L3 installer entry-point resolution (Phase 50 — ADR-0183).

An installer entry point is a ``"package.module:function"`` string that
resolves, over release-shipped modules only (R2-3; no bundle-path code
loading), to the callable that performs a bundle's L3 registration.

Two consumers resolve entry points and must agree on *what counts as
unresolvable*:

* the install **driver** (install time), which wraps a resolve failure
  in :class:`SkillInstallError` and appends a ``failed`` record;
* per-process **activation** (boot / ``skill activate``), which treats a
  resolve failure as "the bundle is absent in this process" — the clean
  don't-know case — and skips it.

Keeping the resolver here, raising a **neutral** :class:`EntryPointError`,
lets each caller adapt the outcome to its own contract without duplicating
the ``split`` / ``import_module`` / ``getattr`` logic (previously copied in
both ``driver._resolve_entry_point`` and ``activation``).
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


class EntryPointError(Exception):
    """A ``"module:function"`` spec did not resolve to a callable.

    Covers every "not resolvable here" cause — malformed spec, an
    unimportable module (``ImportError`` / ``ModuleNotFoundError``), a
    missing attribute, or a non-callable target — so callers can catch a
    single type. The originating exception is chained (``__cause__``).
    """


def resolve_entry_point(spec: str) -> Callable[..., Any]:
    """Resolve ``"package.module:function"`` to its callable.

    Raises:
        EntryPointError: the spec is malformed, its module is not
            importable in this process, the attribute is absent, or the
            resolved object is not callable.
    """
    if not isinstance(spec, str) or spec.count(":") != 1:
        raise EntryPointError(
            f"installer entry point {spec!r} is not 'module:function'"
        )
    module_name, func_name = spec.split(":", 1)
    if not module_name or not func_name:
        raise EntryPointError(
            f"installer entry point {spec!r} is not 'module:function'"
        )
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise EntryPointError(
            f"installer entry point {spec!r}: module {module_name!r} is not "
            f"importable in this process ({exc.__class__.__name__}: {exc})"
        ) from exc
    fn = getattr(module, func_name, None)
    if fn is None or not callable(fn):
        raise EntryPointError(
            f"installer entry point {spec!r} did not resolve to a callable"
        )
    return fn


__all__ = ["EntryPointError", "resolve_entry_point"]
