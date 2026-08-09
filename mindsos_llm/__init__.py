"""``mindsos_llm`` — the external-model consultation substrate.

**This package holds no cognition.** It is transport, configuration,
recording and replay for consulting an external language model, and
nothing else. The *reading* — deciding what a document says, judging
whether a reading is admissible, declining when it is not — is L3
cognition and lives in the ``comprehension.*`` capacity family
(``mindsos_capacity/builtins/comprehension_v0.py``). The split follows
the standing rule that capacities are cognition and everything they run
on is substrate.

**Layering.** ``mindsos_llm`` imports no other ``mindsos_*`` package.
``mindsos_capacity`` does not import it either: a capacity body reaches
the LLM only through ``context.llm``, a narrowed capability the L4
dispatcher injects, exactly as ``context.writeable`` is injected for
write-bodies (ADR-0180). The body never holds a client, credentials or a
session. The boundary payload is a plain ``Mapping``, so neither package
depends on the other's types.

**Injection is declared, not ambient.** ``dispatch.build_context``
injects ``llm`` only when the capacity declaration sets
``consults_llm=True`` — the same discipline ``reads_mm`` established
for the MM handle (ADR-0200 C3). A capacity that has not declared that
it consults a model cannot reach one, and which capacities may is
readable off the registry.

**Three modes, and the graph always says which.** :class:`LiveLLM` calls
a real model through a deployment-supplied transport (no vendor SDK ships
here). :class:`CapturingLLM` wraps a live run and saves the answers, which
is how a recorded set is produced. :class:`RecordedLLM` replays a saved
set for the test suite, which has no network. Every reading is stamped
``recorded: True|False``, so a Record can never present a replayed
reading as a live one.

**Replay exists for the gate, not for the demo.** :class:`~mindsos_llm.replay.RecordedLLM`
answers from a recorded response set and **raises** on a miss rather
than falling through to a live call. Every reading carries
``recorded: True|False`` into the grounding graph, so a Record can never
present a replayed reading as a live one.
"""

from __future__ import annotations

from .exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    LLMError,
    RecordedResponseMiss,
)
from .live import CapturingLLM, LiveLLM, Transport
from .recording import RecordingStore, request_key
from .replay import RecordedLLM

__version__ = "0.0.0+phase50"

__all__ = [
    "CapturingLLM",
    "LLMCallBudgetExceeded",
    "LLMCallFailed",
    "LLMError",
    "LiveLLM",
    "Transport",
    "RecordedResponseMiss",
    "RecordingStore",
    "RecordedLLM",
    "request_key",
]
