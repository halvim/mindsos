"""Shared test infrastructure across phase_NN test packages.

Phase 03 introduces this package to extract:

* ``cli.py`` — the ``_run_cli`` env-merge subprocess helper, originally
  in ``tests/phase_02/conftest.py`` (Phase 02 §3.12 / Bug A fix).
* ``sentinel_paths.py`` — cumulative ``SENTINEL_PATHS`` list driving the
  image-completeness regression test at ``tests/test_image_completeness.py``.
  Each phase appends its new files here.

Phase 04+ append further shared helpers as cross-phase patterns emerge.
"""
