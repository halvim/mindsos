"""``mindsos_llm`` — the external-model client.

**This package holds no cognition.** It is transport typing,
configuration, decoding, recording and replay for consulting an external
language model, and nothing else. The *reading* — deciding what a
document says, judging whether a reading is admissible, declining when it
is not — is L3 cognition and lives in the ``comprehension.*`` capacity
family (``mindsos_capacity/builtins/comprehension_v0.py``). Capacities
are cognition; everything they run on is substrate.

**Where it lives, and why it moved here** (ADR-0210, owner ruling
2026-09-02). This shipped as ``mindsos_capacity/llm/`` and that placement
stated its own expiry: *"a consumer outside the capacity layer, or a
vendor dependency arriving. Either reopens placement."* **Both arrived** —
a second project needs a quote-verified document reader, and an adapter
that speaks a provider's wire protocol now ships in core — so the trigger
fired as written and the package was promoted rather than argued about.

**It is SUBSTRATE FOR THE WHOLE STACK, which is the real reason for the
move.** Calling a model is not L3-private: L0 owns the user's vendor
choice, credential level, mode and credential custody; this package owns
the wire; L3 mints one capacity per reading; L2 Local holds prompt
versions and the pointer to a recorded set; L5 holds the answers. A home
under ``mindsos_capacity`` misdescribed all of that.

⚠ **Being top-level costs what the old docstring said it would.** As a
subpackage this code sat inside the architecture guards' package tuples
for free; it now has to be listed in each by hand, and
``tests/phase_28/test_import_isolation_phase_28.py`` lost its ``llm``
entry in the move. That guard is re-established, WIDER, at
``tests/llm_seam/test_import_isolation_mindsos_llm.py`` — read its
docstring before adding an import here.

⚠ **This package NEVER imports ``mindsos_server``** (ADR-0010 §I-S1, and
ADR-0210 §7c). L0 holds the credential; L0 **pushes** a resolver callable
in at client construction. The module that makes the network call is
therefore structurally unable to read the store the credential came from,
and that is a security property, not a layering nicety.

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

#: Release-train marker. Every manifest-listed package carries the same
#: string; the doctor parity loop asserts it (tests/phase_18).
__version__ = "0.0.0+phase50"

from . import adapters
from . import credential_kinds
from .contract import TransportReport, verify_transport
from .credentials import (
    LEVEL_NEVER_KNOWN,
    LEVEL_NEVER_STORED,
    LEVEL_SHORT_LIVED,
    LEVELS,
    CredentialUnavailable,
    Resolver,
    static_resolver,
)
from .exceptions import (
    LLMCallBudgetExceeded,
    LLMCallFailed,
    LLMError,
    MalformedResponse,
    RecordedResponseMiss,
    TransportContractError,
    TransportSignatureError,
)
from .live import CapturingLLM, LiveLLM, Transport, decode_response
from .recorded_sets import ImportedSet, RecordedSetRefused, export_set, import_set
from .recording import RecordingStore, request_key
from .replay import RecordedLLM

__all__ = [
    "LEVELS",
    "LEVEL_NEVER_KNOWN",
    "LEVEL_NEVER_STORED",
    "LEVEL_SHORT_LIVED",
    "CapturingLLM",
    "CredentialUnavailable",
    "ImportedSet",
    "Resolver",
    "LLMCallBudgetExceeded",
    "LLMCallFailed",
    "LLMError",
    "LiveLLM",
    "MalformedResponse",
    "RecordedLLM",
    "RecordedResponseMiss",
    "RecordedSetRefused",
    "RecordingStore",
    "Transport",
    "TransportContractError",
    "TransportReport",
    "TransportSignatureError",
    "adapters",
    "credential_kinds",
    "decode_response",
    "export_set",
    "import_set",
    "request_key",
    "static_resolver",
    "verify_transport",
]
