"""``mindsos_capacity.llm`` — the external-model client.

**This subpackage holds no cognition.** It is transport typing,
configuration, decoding, recording and replay for consulting an external
language model, and nothing else. The *reading* — deciding what a
document says, judging whether a reading is admissible, declining when it
is not — is L3 cognition and lives in the ``comprehension.*`` capacity
family (``mindsos_capacity/builtins/comprehension_v0.py``). Capacities
are cognition; everything they run on is substrate.

**Where it lives, and why here rather than a top-level package**
(coordination §87 placement ruling, critic §88 Q4). It is a client for an
outside service, and the client for the OTHER outside service lives
inside a package too (``mindsos_core/persistence/client.py``). Its one
consumer is a capacity body, and the factory for the other capability
injected onto ``CapacityContext`` — ``make_writeable`` (ADR-0180) —
already lives in ``mindsos_capacity/context.py``. Being a subpackage also
puts it automatically inside the architecture guards' package tuples
rather than requiring six hand edits to be seen by them.

**Promotion trigger, stated so the next reader does not have to judge:**
a consumer outside the capacity layer, or a vendor dependency arriving.
Either reopens placement — ``git mv`` plus the 9-site new-top-level-
package checklist (PHASE_27 PB-29).

**Injection is DECLARED, not ambient.** ``dispatch.build_context``
injects ``llm`` only when the capacity declaration sets
``consults_llm=True`` — the discipline ``reads_mm`` established for the
MM handle (ADR-0200 C3). A capacity that has not declared it consults a
model cannot reach one, and which capacities may is readable off the
registry rather than inferred from a category. A body never holds a
client, credentials or a session.

**Three modes, and the graph always says which.** :class:`LiveLLM` calls
a real model through a deployment-supplied transport (no vendor SDK ships
here). :class:`CapturingLLM` wraps a live run and saves the answers, which
is how a recorded set is produced. :class:`RecordedLLM` replays a saved
set for the gate, which has no network, and RAISES on a miss rather than
falling through to a live call. Every reading is stamped
``recorded: True|False`` into the grounding graph, so a Record can never
present a replayed reading as a live one.

**Failures are classified, not collapsed** — see :mod:`.exceptions`. An
outage is a stop, an undecodable answer is a refusal, a forbidden return
is a deployment bug, and no ``str(exc)`` here carries a provider's words.

:mod:`.contract` ships the transport contract as a harness a deployment
can run against its own live transport.
"""

from __future__ import annotations

from .contract import TransportReport, verify_transport
from .exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    LLMError,
    MalformedResponse,
    RecordedResponseMiss,
    TransportContractError,
)
from .live import CapturingLLM, LiveLLM, Transport, decode_response
from .recording import RecordingStore, request_key
from .replay import RecordedLLM

__all__ = [
    "CapturingLLM",
    "LLMCallBudgetExceeded",
    "LLMCallFailed",
    "LLMError",
    "LiveLLM",
    "MalformedResponse",
    "RecordedLLM",
    "RecordedResponseMiss",
    "RecordingStore",
    "Transport",
    "TransportContractError",
    "TransportReport",
    "decode_response",
    "request_key",
    "verify_transport",
]
