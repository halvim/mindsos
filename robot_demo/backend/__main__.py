"""``python -m demo_backend`` → the DM-1 bootstrap entrypoint."""

from __future__ import annotations

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
