---
title: Pluggable IdStrategy on Metagraph
status: Proposed
date: 2026-04-27
layer: L1
amends: [0035]
---

# ADR-0131: Pluggable `IdStrategy` on `Metagraph`

**Status:** Proposed

**Date:** 2026-04-27

**Amends:** ADR-0035 (UUIDs are non-deterministic — kept as default; alternative strategies become opt-in).

**Related:** ADR-0118 (per-user transactional promotion — auto-upgrade contract requires id stability). ADR-0114 [Reserved] (release manifest + version DB — keys versions by `(node_id, version)`).

## Context

`mindsos_core.identity.generate_uuid()` mints a fresh UUID4 on every call. The non-determinism is paid for by every higher layer:

- **Tests.** Goldens require id-stubbing or assertions that ignore ids.
- **KL importers.** Stable IRIs (`oewn-2024:synset:02086723-n`) are minted upstream and used as `node_id`, side-stepping `generate_uuid` entirely. The relationship between IRI and UUID is informal — IRIs go in the `node_id` slot when the importer chooses, UUIDs otherwise.
- **L3 derivations.** Re-running an idempotent derivation produces a new id-set; output diff is impossible without ID stubs.
- **Cloning.** Copying a metagraph gives every node a new UUID; no "preserve mapping" helper.

The pivot's auto-upgrade contract (ADR-0118 + `docs/concepts/references.md` § "Ref auto-upgrade under release model") commits to **node id stability across content mutations**. Cross-graph refs resolve by node id; the version DB keys versions on `node_id`. Content-addressable IDs (UUID5 from canonical content) would change with content and break ref stability — they're constrained out.

But: a pluggable strategy that *defaults* to UUID4 (status quo) and *allows* opt-in alternatives (UUID5 from content for tests/derivations; passthrough for IRI minted upstream) costs little and unlocks all three of the above tax categories.

## Decision

Introduce a pluggable `IdStrategy` Protocol on `Metagraph`:

```python
from typing import Protocol

class IdStrategy(Protocol):
    """Strategy for minting new node/edge/hyperedge ids inside a Metagraph."""

    def generate(self, kind: str, content: dict | None = None) -> str:
        """Mint a new id.

        kind: one of "node" | "edge" | "hyperedge" | "graph" | "metaedge"
              | "metahyperedge" | "instance" | "composite".
        content: dict of canonical content for content-addressable strategies;
                 None for strategies that ignore content (e.g. UUID4).
        """
```

Three reference strategies ship in `mindsos_core.identity`:

```python
class UUID4Strategy:
    """Default. Non-deterministic UUID4 per call. Matches existing behaviour."""
    def generate(self, kind: str, content: dict | None = None) -> str:
        return str(uuid.uuid4())


class UUID5FromContentStrategy:
    """Deterministic UUID5 derived from canonical content. Opt-in.
    Useful for tests, idempotent derivations, content-addressable nodes."""

    NAMESPACE = uuid.UUID("a4b3...mindsos-fixed-namespace...")

    def generate(self, kind: str, content: dict | None = None) -> str:
        if content is None:
            raise IdStrategyError(f"UUID5FromContentStrategy requires content for kind={kind}")
        canonical = json.dumps({"kind": kind, "content": content}, sort_keys=True, default=str)
        return str(uuid.uuid5(self.NAMESPACE, canonical))


class IRIPassthroughStrategy:
    """Wraps another strategy; if the caller supplies content with an `iri` key,
    use it directly. Otherwise delegate. Useful for KL importers."""

    def __init__(self, fallback: IdStrategy):
        self.fallback = fallback

    def generate(self, kind: str, content: dict | None = None) -> str:
        if content and "iri" in content:
            return str(content["iri"])
        return self.fallback.generate(kind, content)
```

**Wiring on Metagraph:**

```python
@dataclass
class Metagraph:
    ...
    id_strategy: IdStrategy = field(default_factory=UUID4Strategy)
```

Default behaviour is unchanged — `Metagraph()` constructs a `Metagraph` with `UUID4Strategy()`. All existing calls continue to work.

**Where it's used:**

`Graph.add_node`, `Graph.add_edge`, `Graph.add_hyperedge`, `Metagraph.add_metaedge`, `Metagraph.add_metahyperedge`, `Metagraph.instantiate_*`, etc., all currently call `generate_uuid()`. They become:

```python
def add_node(self, value: str, type_name: str, properties: dict | None = None, *, _id: str | None = None) -> Node:
    if _id is None:
        content = {"value": value, "type_name": type_name, "properties": properties or {}}
        _id = self._metagraph.id_strategy.generate("node", content)
    ...
```

The `_id` parameter is private (underscored); the `_restore_*` factories continue to use it for reconstruction. Callers should not pass it directly.

**Existing UUIDs preserved when strategy changes.** Switching `mg.id_strategy` does not retroactively rename existing nodes. The strategy applies to **new** ids only. The IdentityRegistry continues to hold whatever ids exist.

**Test fixture:**

```python
# In a test:
mg = Metagraph(id_strategy=UUID5FromContentStrategy())
n1 = mg.graphs[0].add_node("alice", "Person")  # id is deterministic
n2 = mg.graphs[0].add_node("alice", "Person")  # SAME id — content matches
```

Tests can construct a deterministic Metagraph and rely on golden id values without mocking.

**KL coordination:**

KL's importers (DOLCE, OEWN, FrameNet, Alignments) currently mint stable IRIs and store them as `node_id`. Under this ADR, they switch to:

```python
mg = create_global(id_strategy=IRIPassthroughStrategy(fallback=UUID4Strategy()))
g = ensure_role_graph(mg, ROLE_LEXICON)
g.add_node("alice", "Person", properties={"iri": "oewn-2024:synset:02086723-n"})
# ↑ id is "oewn-2024:synset:02086723-n" because IRIPassthroughStrategy reads the iri key
```

This formalises the relationship between IRI and `node_id` that today is informal. The `iri` content-key convention is documented in `docs/concepts/identity.md`.

## Rationale

UUID4 stays as default — auto-upgrade contract requires id stability across content mutation, and content-addressable can't satisfy that as a default. But UUID4-only is a tax on tests, derivations, and importers. The tax has three forms:

1. **Test goldens.** Pluggable strategy lets tests opt into determinism without monkey-patching.
2. **Derivation idempotency.** L3 derivation pipelines that compute "if input is the same, output id should be the same" can opt into `UUID5FromContentStrategy` for the derivation's output graph.
3. **Importer formalisation.** KL importers' "use IRI as node_id" pattern becomes a documented strategy rather than a special case in every importer.

The pivot's auto-upgrade contract is preserved because individual nodes can mix strategies — a Local Metagraph with `UUID4Strategy` (the default) for user-authored drafts, and a Global Metagraph with `IRIPassthroughStrategy` for imported content. Auto-upgrade resolves by stable `node_id` regardless of how that id was minted.

The alternative strategies are *opt-in*. No layer's existing behaviour changes if it doesn't construct a Metagraph with a non-default strategy. The cost of the change is ~80 LOC in `mindsos_core.identity` plus threading the `id_strategy` parameter through the few existing call sites that mint ids.

## Consequences

**Good:**

- Tests can construct deterministic Metagraphs without monkey-patching `generate_uuid`.
- L3 derivations claim idempotency via `UUID5FromContentStrategy`.
- KL importers use `IRIPassthroughStrategy` instead of stuffing IRI into `node_id` ad-hoc.
- The relationship between IRI and `node_id` becomes a documented strategy, not a special case.
- Content-addressable IDs are available where they're safe (idempotent derivations) without forcing them where they break (auto-upgrade-ed content).

**Tradeoffs:**

- Six call sites in Core mint ids today; all gain a strategy lookup. Hot-path cost is one method call per id (negligible).
- One new Protocol + three reference implementations + one new public field on `Metagraph`. Moderate API surface growth, justified by usage.
- Content-addressable strategies have a collision concern in principle (two different "alice" Persons in different parts of the metagraph would collide under `UUID5FromContentStrategy`). Mitigation: `IdStrategy.generate` receives `kind` and the full content dict; content should be unique enough to disambiguate. Documentation calls this out and recommends including provenance keys (`graph_id`, `created_by`, etc.) in the content for content-addressable contexts.
- KL importers' migration: they currently set `node_id = iri` directly. Switching to `IRIPassthroughStrategy` means importers no longer pass `node_id`; they pass `iri` in `content`. One coordinated KL change. Backward-compat: the `_id` private parameter still works for `_restore_*` paths.

**Coordinated changes:**

- ADR-0035 status flips to **Amended** (not Superseded — UUID4 remains the default).
- `mindsos_core/identity.py` — refactor `generate_uuid()` into `UUID4Strategy().generate(...)`; add `UUID5FromContentStrategy`, `IRIPassthroughStrategy`, `IdStrategy` Protocol.
- `mindsos_core/models/metagraph.py` — add `id_strategy` field; thread through factories.
- `mindsos_core/models/graph.py`, `models/edge.py`, etc. — switch from `generate_uuid()` to `self._metagraph.id_strategy.generate(kind, content)`.
- KL importers (`mindsos_knowledge/importers/*.py`) — switch to `IRIPassthroughStrategy`; remove ad-hoc `node_id=iri` usage.
- `docs/concepts/identity.md` — documents the strategy taxonomy and IRI convention.
- Tests gain a fixture `deterministic_metagraph()` that constructs a `Metagraph(id_strategy=UUID5FromContentStrategy())`.

## Alternatives considered

1. **Keep UUID4 only (ADR-0035 status quo).** Rejected — every consumer keeps paying the tax. Tests work around with monkey-patching; KL importers work around with `node_id=iri`; L3 derivations can't claim idempotency.
2. **Switch default to content-addressable (UUID5 from content).** Rejected — auto-upgrade contract requires id stability across mutation; content-addressable changes id with content, breaks refs.
3. **Hybrid default per kind (UUID4 for new nodes; content-addressable for derived nodes).** Rejected — implementation complexity high; "which kind is derived?" is a moving question; the pluggable strategy gets the same effect more cleanly.
4. **Inject ids at every call site (no Strategy).** Rejected — every call site has to know its content; the Strategy abstraction centralises the policy and lets reasonable defaults work without thought.

## Implementation references

- New module: `mindsos_core/identity/strategy.py` (Protocol + 3 implementations).
- Existing module: `mindsos_core/identity.py` becomes the public re-export.
- `mindsos_core/models/metagraph.py` — `id_strategy` field; default factory returns `UUID4Strategy()`.
- Six call sites in Core that mint ids.
- KL importer updates: `mindsos_knowledge/importers/dolce.py`, `oewn.py`, `framenet.py`, `alignments.py`.
- `docs/concepts/identity.md` — strategy taxonomy + IRI convention.
- `tests/unit/core/test_id_strategy.py` — new file, ~12 tests.
- `tests/conftest.py` — add `deterministic_metagraph` fixture.

ADR moves from Proposed to Accepted when code lands and `docs/concepts/identity.md` reflects the decision.
