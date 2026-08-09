"""Errors raised by the LLM substrate."""

from __future__ import annotations


class LLMError(Exception):
    """Base class for every llm-substrate failure."""


class RecordedResponseMiss(LLMError):
    """A replayed reading was requested and no recorded response matched.

    Deliberately fatal. A replay store that silently fell through to a
    live provider — or to a fabricated answer — would let a Decision
    Record present an unrecorded reading as a recorded one. A miss is a
    configuration error in the demo set, not a don't-know about the
    world, so it is raised rather than returned as a decline.
    """


class LLMCallFailed(LLMError):
    """A live model call failed.

    Not retried, and never answered from a saved response instead: a
    silent fallback would let a run present a stale reading as a fresh
    one. The caller decides what a failed case means.
    """


class LLMCallBudgetExceeded(LLMError):
    """A dispatcher's ``max_calls`` ceiling was reached."""
