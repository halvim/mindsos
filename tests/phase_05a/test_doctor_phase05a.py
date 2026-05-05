"""Phase 05a — doctor self-test recognises phase05a image tags."""

from __future__ import annotations

import re

from mindsos_cli.commands.doctor import _COMPOSE_IMAGE_RE


def test_compose_image_re_recognises_phase05a():
    """_COMPOSE_IMAGE_RE matches `mindsos:phase05a-prod` (letter sub-phase form)."""
    body = "    image: mindsos:phase05a-prod\n"
    matches = list(_COMPOSE_IMAGE_RE.finditer(body))
    assert len(matches) == 1
    assert matches[0].group("phase") == "05a"
    assert matches[0].group("stage") == "prod"


def test_compose_image_re_recognises_phase05a_test():
    body = "    image: mindsos:phase05a-test\n"
    matches = list(_COMPOSE_IMAGE_RE.finditer(body))
    assert len(matches) == 1
    assert matches[0].group("phase") == "05a"
    assert matches[0].group("stage") == "test"
