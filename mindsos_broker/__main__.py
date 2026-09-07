"""``python -m mindsos_broker`` — run the reference broker.

Configuration is environment only, and that is deliberate: a command line ends
up in shell history and in a process listing, and this is the one program in
the tree that is meant to be near a credential.

* ``MINDSOS_BROKER_VENDOR`` — default ``anthropic``.
* ``MINDSOS_BROKER_UPSTREAM`` — default: the vendor adapter's own endpoint.
* ``MINDSOS_BROKER_CREDENTIAL_HEADER`` — default: the vendor adapter's own
  credential header. ⚠ Both defaults are **read from the adapter**, never
  copied here: a wire detail with two homes drifts, and the adapter is the home.
* ``MINDSOS_BROKER_CREDENTIAL_VAR`` — the environment variable holding the
  credential. Required, and read **per request**, not at startup, so rotating
  it does not need a restart.
* ``MINDSOS_BROKER_PORT`` — default 0, meaning "pick a free one and print it".
* ``MINDSOS_BROKER_HOST`` — default ``127.0.0.1``. Change it only if you mean
  to run a credential-adding proxy reachable from your network.

The URL is printed on stdout so it can be pasted into a client configuration.
"""

from __future__ import annotations

import os
import sys

from mindsos_llm import adapters

from .reference import BrokerConfig, serve


def main(argv: list[str] | None = None) -> int:
    del argv
    vendor_id = os.environ.get("MINDSOS_BROKER_VENDOR", "anthropic")
    adapter = adapters.get(vendor_id)
    upstream = os.environ.get("MINDSOS_BROKER_UPSTREAM") or adapter.ENDPOINT
    header = os.environ.get(
        "MINDSOS_BROKER_CREDENTIAL_HEADER"
    ) or adapter.CREDENTIAL_HEADER
    var = os.environ.get("MINDSOS_BROKER_CREDENTIAL_VAR")
    if not var:
        print(
            "MINDSOS_BROKER_CREDENTIAL_VAR must name the environment variable "
            "holding the credential",
            file=sys.stderr,
        )
        return 2

    config = BrokerConfig(
        upstream_endpoint=upstream,
        credential_header=header,
        # Per request, and closed over the NAME rather than the value —
        # ``mindsos_llm.credential_kinds.env``'s argument, obeyed here.
        fetch_credential=lambda: os.environ[var],
        vendor_id=vendor_id,
    )
    server, url = serve(
        config,
        host=os.environ.get("MINDSOS_BROKER_HOST", "127.0.0.1"),
        port=int(os.environ.get("MINDSOS_BROKER_PORT", "0")),
    )
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover - the entry point itself
    raise SystemExit(main(None))
