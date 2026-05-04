---
title: IdentityRegistry — API
tag: shipped (partial — Phase 02 introduction)
last_confirmed_phase: 02
source: mindsos_core/models/identity.py
---

# IdentityRegistry — API (Phase 02 introduction)

`IdentityRegistry` lives at `mindsos_core.IdentityRegistry`. Phase 02
ships only the registry primitive itself + the three `IdStrategy`
implementations. The full metagraph-scoped semantics (registry shared
across contained graphs, replace-with-conflict during reconstruction,
etc.) land with Phase 05 (`Metagraph` + `MetaEdge` +
`MetaHyperEdge`).

## Construction

```python
from mindsos_core import IdentityRegistry

reg = IdentityRegistry()  # empty
```

The registry stores ids as `str` only. There is no namespace,
prefix-validation, or shape-check at this layer — Core treats every id
as opaque.

## Methods

| Method                          | Effect                                                       |
|---------------------------------|--------------------------------------------------------------|
| `register(uid: str)`            | Register `uid`. Raises `IdentityError` on duplicate.         |
| `unregister(uid: str)`          | Remove `uid`. No-op if not present.                          |
| `replace(old_id, new_id)`       | Atomic swap. Raises `IdentityError` if `new_id` is taken.    |
| `clear()`                       | Drop every id. Primarily for tests.                          |
| `contains(uid)` / `uid in reg`  | Membership test.                                             |
| `len(reg)`                      | Cardinality.                                                 |
| `reg.ids` (property)            | **Defensive copy** of the registered set.                    |

`__slots__ = ("_ids",)`. The internal store is a `Set[str]`. The
`replace` operation is atomic: if `new_id` is already registered (and
distinct from `old_id`), nothing changes and the registry raises rather
than silently corrupting.

## IdStrategy (Protocol)

```python
@runtime_checkable
class IdStrategy(Protocol):
    def generate(self, kind: str, content: Optional[Dict[str, Any]] = None) -> str: ...
```

Three implementations:

```python
from mindsos_core import (
    UUID4Strategy,
    UUID5FromContentStrategy,
    IRIPassthroughStrategy,
    NAMESPACE_MINDSOS,
)

UUID4Strategy().generate("node")
# → "fc1d…6e8e" (random)

UUID5FromContentStrategy().generate("node", {"value": "concept-A"})
# → deterministic UUID5 under NAMESPACE_MINDSOS

IRIPassthroughStrategy().generate("node", {"iri": "oewn-2024:synset:01-n"})
# → "oewn-2024:synset:01-n"

IRIPassthroughStrategy().generate("node")  # no iri key
# → falls back to UUID4Strategy (configurable via `fallback=...`)
```

`UUID5FromContentStrategy` raises `IdentityError` when `content` is
`None` (it has nothing to hash). `IRIPassthroughStrategy` raises
`IdentityError` when `content["iri"]` is empty or non-string.

## Thread safety

The registry is **not** thread-safe. Concurrent `register` calls from
different threads on the same `IdentityRegistry` may race. In
production, the metagraph orchestration layer (Phase 07+) serialises
writes; the registry itself is only ever called from the write path.

## CLI surface (Phase 02)

```sh
docker compose run --rm mindsos identity mint --strategy uuid4 --json
docker compose run --rm mindsos identity mint --strategy uuid5 --seed '{"value":"x"}' --json
docker compose run --rm mindsos identity mint --strategy iri  --seed '{"iri":"oewn-2024:synset:01-n"}' --json

docker compose run --rm mindsos identity registry --scope demo --register id-a --json
docker compose run --rm mindsos identity registry --scope demo --register id-b --json
docker compose run --rm mindsos identity registry --scope demo --list --json
docker compose run --rm mindsos identity registry --scope demo --register id-a   # duplicate → exit 1

docker compose run --rm mindsos identity strategies --json
```

The CLI's `registry` subcommand persists state to a JSON file
(`$MINDSOS_STATE_DIR/identity-registry-<scope>.json`, default
`~/.mindsos/identity-registry-<scope>.json`). This is **debug only** and
not a metagraph-scoped registry; Phase 05 will exercise the real
semantics.

## What lands later

| Capability                                     | Phase |
|------------------------------------------------|-------|
| Metagraph-shared registry across contained graphs | 05 |
| `replace(old, new)` during reconstruction       | 08 |
| Persistence-side lifecycle hooks (WAL, OCC)     | 07 |

---

See also: [Identity and IRIs](../../concepts/identity.md) — the
conceptual overview, including why IRIs are an importer convention
(Phase 12) rather than a Core primitive.
