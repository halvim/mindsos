"""Phase 44 import warm-up.

Load ``mindsos_admin`` before any test module imports ``mindsos_server``
so the pre-existing ``mindsos_server.admin`` <-> ``mindsos_server.persistence``
<-> ``mindsos_admin`` import cycle resolves under isolated collection
(``pytest tests/phase_44/``). In the full suite the server-phase
conftests (e.g. phase_24) already warm this order; phase_44 had none.
Importing ``mindsos_admin`` first lets ``admin.py`` finish defining
``admin_tx`` before ``mindsos_admin.promotion`` imports it. See
``PHASE_44_DESIGN_LOG.md`` §7.
"""

from __future__ import annotations

import importlib

importlib.import_module("mindsos_admin")
