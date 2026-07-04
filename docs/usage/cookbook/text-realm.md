---
title: Text realm — vertical slice
last_confirmed_phase: 38
---

# Text realm — vertical slice

This cookbook walks an end-to-end **read-side** scenario through all
four shipped layers: Server (L0) → Core (L1) → Knowledge (L2) →
Capacity (L3). It transcribes the Phase 32 Integration B scenario
into prose. Run it to see how the layers compose when a user takes a
piece of raw text and pulls tokens out the other side.

## What this cookbook does and does not do

**Does:** Walks the read-side path — admin bootstrap, login, KL
bootstrap + import a tiny text-domain fixture, build an in-process
`CapacityLayer`, install the shipped text builtins, find a pipeline
from raw text to tokens, invoke the pipeline via CLI, tail the
problem-trace, logout, query the audit log.

**Does not:** Demonstrate Local-write end-to-end. The shipped
`capacity:consolidate:mm` write capacity targets the user's in-memory
Local metagraph; without `FalkorDBLocalPersister` (unshipped at
Phase 36), writes evaporate on CLI exit. The Local-write cookbook
flow ships as a unit with the L4 session orchestrator + Falkor-backed
Local persister — see [What's new in v4](../../getting-started/whats-new-v4.md)
for the L4 carry-forward list.

## Prerequisites

- A running `falkordb` sidecar (the docker-compose default).
- The `mindsos` image built (`docker compose --profile cli build mindsos`).
- A working dir for `MINDSOS_SERVER_DB` + `HOME` (use a fresh
  `tmp_path` per scenario if you're scripting against this).

This cookbook drives the system through `docker compose run --rm
mindsos <verb>` style invocations; substitute your own shell harness
if you prefer.

## Seed text

The fixture used throughout is the three-word string `"the cat sat"`.
That's deliberately small — the goal is to make the layer
composition visible, not to demonstrate large-corpus throughput. The
shipped `capacity:perception:text.space_split` capacity takes raw
text and returns a list of whitespace-split tokens; with this seed
the expected output is `["the", "cat", "sat"]`.

## Step-by-step

### 1. Bootstrap the admin user

```
$ mindsos server bootstrap admin
<stdin: enter a password — e.g., "adminpw">
```

This creates the admin user in `server.db`, hashes the password via
Argon2id, and emits a structured audit row (`EVT_BOOTSTRAP`).
Exit 0 on success; exit 1 if an admin already exists (Phase 20's
idempotency guard).

### 2. Login as admin

```
$ mindsos server login admin
<stdin: same password>
```

This authenticates, issues a session, and writes the plaintext
token to `~/.mindsos/token` mode 0600. Emits `EVT_LOGIN`.
`--print-token` also echoes the token to stdout for shell pipelines:

```
$ TOKEN=$(mindsos server login admin --print-token < password.txt)
```

### 3. Bootstrap the Knowledge Layer from FalkorDB + import the text fixture

This step has no CLI verb today (the cookbook scenario uses the
Python API directly; a shipped admin CLI for arbitrary importers
is L4/L5 scope). The Python pattern mirrors Phase 26b's
canonical-pair bootstrap:

```python
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.persistence.metagraph_repository import MetagraphRepository
from mindsos_server.persistence import bootstrap_global_pair_from_falkordb
from tests.phase_32.fixtures._text_importer import TextFixtureImporter

client = FalkorClient(FalkorConfig.from_env())
try:
    canonical_kl, _ = bootstrap_global_pair_from_falkordb(client)
    TextFixtureImporter().run(canonical_kl.global_metagraph())
    MetagraphRepository(client).persist(canonical_kl.global_metagraph())
finally:
    client.close()
```

`TextFixtureImporter` writes one `Frame` node into the `concepts`
role-graph — minimal but enough to drive the rest of the slice.

### 4. Bootstrap the Capacity Layer (Global + admin's Local)

```python
from mindsos_capacity import CapacityLayer

layer = CapacityLayer()                 # constructor builds Global
_ = layer.local_metagraph("admin")      # lazily creates admin's Local
```

`CapacityLayer.bootstrap_*` is **not** a classmethod; the constructor
is the bootstrap. `local_metagraph(user_id)` is lazy — first access
creates the per-user Local metagraph and auto-ensures the named
Local role-graphs (`episodic_memories` + `capacity-state`, plus the
Phase-43+ dual-scope roles) per ADR-0044 (§am-3 rename).

### 5. Install the text capacities

```python
from mindsos_capacity.builtins.text import install_text_capacities

install_text_capacities(layer)
install_text_capacities(layer)          # idempotent — second call is a no-op
```

This registers `capacity:perception:text.space_split` plus two
DataStates (`datastate:text.raw` + `datastate:text.tokens`) in
`layer`. Idempotency is the Phase 31 R1-PB-12 contract.

### 6. Find a pipeline from raw text to tokens

In-process via Python:

```python
from mindsos_capacity import find_pipeline
from mindsos_capacity.builtins.text import DS_RAW_TEXT, DS_TOKENS

pipeline = find_pipeline(
    layer,
    start_datastate=DS_RAW_TEXT,
    target_datastate=DS_TOKENS,
)
# pipeline.steps == [Step(capacity_iri="capacity:perception:text.space_split", ...)]
```

Or via the CLI smoke (note: today the `mindsos capacity find` verb
builds a **fresh empty layer** — it doesn't auto-install builtins
the way `invoke` does. So the CLI form is a negative-path smoke as
written):

```
$ mindsos capacity find \
    --start datastate:text.raw \
    --target datastate:text.tokens \
    --json
# exit 1 — PipelineNotFoundError against the empty CLI layer
# {"error": "PipelineNotFoundError", "message": "no pipeline ..."}
```

A positive-path CLI `find` (matching `invoke`'s auto-install
ergonomics) is a carry-forward — see the
[What's new in v4](../../getting-started/whats-new-v4.md) deferral
list.

### 7. Invoke the pipeline via CLI

Write the input JSON to a temp file:

```
$ cat > /tmp/invoke_input.json <<EOF
{"datastate:text.raw": "the cat sat"}
EOF

$ mindsos capacity invoke capacity:perception:text.space_split \
    --input-file /tmp/invoke_input.json \
    --json
```

Expected envelope:

```json
{
  "success": true,
  "outputs": {"datastate:text.tokens": ["the", "cat", "sat"]},
  "duration_ms": 0.123,
  "trace": {},
  "error": null,
  "signals": []
}
```

`invoke`'s `_construct_invoke_layer` auto-installs the text builtins
into a fresh in-memory `CapacityLayer` for the duration of the CLI
invocation, then exits. The layer is not persisted; rerunning the
command rebuilds it from scratch.

### 8. Tail the problem-trace

```
$ mindsos capacity problem-trace tail --json
# []
```

Empty — the previous `invoke` succeeded, and the CLI's
`_construct_global_layer` (for `problem-trace tail`) is a fresh
sink that didn't see step 7's invoke (subprocess isolation).

### 9. Logout

```
$ mindsos server logout
```

Emits `EVT_LOGOUT`. Removes `~/.mindsos/token`.

### 10. Re-login and query the audit log

`query-audit` requires `CAN_QUERY_AUDIT`, so re-login first:

```
$ mindsos server login admin
<stdin: password>

$ mindsos server query-audit --json
```

The audit table should show:

| event | count |
|---|---|
| `EVT_BOOTSTRAP` | 1 |
| `EVT_LOGIN`     | 2 |
| `EVT_LOGOUT`    | 1 |

`EVT_AUDIT_QUERY` is filtered from this call's own SELECT result per
Phase 21's read-then-write ordering (the audit row for this very
query lands *after* the SELECT returns, so it doesn't appear in its
own result set).

## What's been demonstrated

You drove a piece of raw text through:

- **L0 (Server)** — auth, sessions, audit, capability gating
- **L1 (Core)** — Graph + Node primitives backing the role-graphs
- **L2 (Knowledge)** — KL + role-graph bootstrap from FalkorDB +
  importer (the text fixture)
- **L3 (Capacity)** — DataStates + Capacity + pipeline finder +
  invoke runtime

The exact same scenario lives in `tests/phase_32/test_integration_b.py`
as 11 step helpers + one `test_integration_b` scenario. If you
script against this cookbook, point your assertions at the same
audit shape + envelope shape and you have a regression test for the
read-side vertical slice.

## What's next

- The Local-write equivalent (memory consolidation through
  `capacity:consolidate:mm`) ships with the L4 session orchestrator —
  see [What's new in v4](../../getting-started/whats-new-v4.md) for
  the deferral list.
- More text builtins (`text.sentence_split`, future `text.lowercase`,
  etc.) plus the `--install-builtins=<family>` CLI flag are L4
  follow-up scope.
- Read [Capacity overview](../capacity/overview.md) for the underlying
  L3 model. Read [Knowledge overview](../knowledge/overview.md) for
  the L2 model.

## Reference: the Phase 32 integration test

Source: `tests/phase_32/test_integration_b.py`. 11 step helpers map
1-1 to the steps above; assertions match the envelope + audit
counts. The test is the load-bearing smoke target for this cookbook
— if the cookbook prose drifts from the test, the test wins.
