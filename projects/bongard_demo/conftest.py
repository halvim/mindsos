"""Make the ``bongard`` demo package importable under pytest.

The demo lives under ``projects/bongard_demo/`` (not in the installed
``mindsos_*`` set), so add this directory to ``sys.path`` for the test
session. Gate with:

    docker compose -p mindsos-bongard --profile test run --rm --build \
        mindsos-test pytest projects/bongard_demo
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
