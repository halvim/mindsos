"""``mindsos_broker`` — the reference credential broker, and why it is not core.

**What this package is.** A small program the user runs. It holds the vendor
credential, accepts a request that MindsOS composed and did not sign, adds the
credential, forwards it upstream, and returns what came back. That is credential
level 2 (ADR-0210): *never known* — the credential does not reach MindsOS at all.

⚠ **It is a SEPARATE TOP-LEVEL PACKAGE, and that is the security property
rather than tidiness.** ``mindsos_llm`` is designed to be structurally unable
to hold a credential: L0 pushes a callable in, the header helper always
returns, the composed request is scrubbed in a ``finally``. A module that
deliberately *does* hold a key has no business inside that package, however
carefully it is written — and the separation is not a comment here, it is
enforced: ``mindsos_broker`` is one of ``FORBIDDEN_ROOTS`` in
``tests/llm_seam/test_import_isolation_mindsos_llm.py``, so **no module in
``mindsos_llm`` may import this package**. The dependency runs one way only:
the broker imports the contract, the contract never imports the broker.

**Why core ships one at all** (ADR-0210 decision 9). *An option in a picker
that nothing implements is dead.* A contract with no implementer is a shape
nobody has proved fits, and level 2 would be a sentence in a document. This
package is the first implementer, it is the worked example a deployment copies
for its own secret manager, and it is what lets the guards exercise a brokered
call over a **real socket with the default opener** rather than asserting the
property in the one configuration where it holds.

**What it deliberately does not do.** It does not log a request body, it does
not read the upstream error body back to the caller, it does not retry, and it
does not rewrite the body it was handed. Each of those is a rule
``mindsos_llm.seam`` already states for a transport, and a broker sitting in
the middle of the call is bound by them for the same reasons.

Run it with ``python -m mindsos_broker``; see
``docs/usage/runtime/llm-broker-contract.md`` for the wire and the environment.
"""

from __future__ import annotations

__version__ = "0.0.0+phase50"

from .reference import BrokerConfig, build_handler_class, serve

__all__ = ["BrokerConfig", "build_handler_class", "serve", "__version__"]
