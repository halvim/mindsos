"""Phase 46 — cooperative cancellation framework (ADR-0167)."""

from __future__ import annotations

from mindsos_capacity.context import CancelToken as CancelTokenProtocol
from mindsos_intelligence.cancellation import CancelToken, CancelTokenView


def test_concrete_token_satisfies_l3_protocol():
    tok = CancelToken()
    assert isinstance(tok, CancelTokenProtocol)


def test_request_cancel_sets():
    tok = CancelToken()
    assert tok.is_set() is False
    tok.request_cancel()
    assert tok.is_set() is True


def test_view_is_read_only_and_polls():
    tok = CancelToken()
    view = tok.view()
    assert isinstance(view, CancelTokenView)
    assert view.is_set() is False
    tok.request_cancel()
    assert view.is_set() is True
    assert not hasattr(view, "request_cancel")
