# Internals — Phase-1 interpretation seam + modality ingress

How task input is interpreted, and how to add a new input **modality**. Covers
the ADR-0195 interpretation seam and the ADR-0197 modality-aware ingress that
sits on top of it.

**Code:** `mindsos_intelligence/phase_1.py` (`interpret`), `.../ingress.py`
(`InputEnvelope`), `.../dispatch.py` (`L4Dispatcher`), and the Phase-1 catalogs
`mindsos_capacity/builtins/phase1_v0.py` (the placeholder fallback) and
`.../phase1_text.py` (the worked text modality).

## The two axes

- **Modality** = the *type* of the input (text / image / action). It drives
  **which capacities interpret the input**. A modality *is* the identity of the
  ingress DataState (`text.raw`, `image.raw`, …) — there is no separate modality
  enum.
- **Source** = which button / channel / API produced the input. It is
  **provenance only** and must never influence capacity selection.

`interpret()` takes either a raw value (legacy path → all-v0, unchanged) or an
`InputEnvelope`:

```python
from mindsos_intelligence import InputEnvelope

InputEnvelope(value="solve this", modality="datastate:text.raw", source="cli")
```

The boundary that admits the input **stamps** the modality — *declared by the
source* (the UI knows it fired an action; do not sniff bytes).

## Selection

Which body runs each of the four steps (`process` → `hint` → `derive_goal` →
`map`) is a **`Phase1Profile`** — a per-consumer selection of capacity IRIs.
Every slot is optional; an unset slot falls back to the shipped v0 placeholder.

Profiles are chosen with this precedence (`phase_1.interpret`):

1. an explicit `profile=` argument (an interpretation-only consumer, e.g. arc);
2. else the dispatcher's `{modality → Phase1Profile}` table, keyed by the
   stamped modality (ADR-0197);
3. else the dispatcher's construction-bound `phase1_profile` (ADR-0195);
4. else all-v0.

```python
L4Dispatcher(
    capacity_layer, session=session, kl=kl,
    modality_profiles={ "datastate:text.raw": text_profile },
)
```

## The interpret contract — environment-threaded spine

`interpret` does **not** hardcode the inter-step DataStates. It threads a
`{DataState IRI → value}` environment: it seeds `{<process cap's declared input>
: value}`, and for each step passes `{ds: env[ds] for ds in selected_cap.inputs}`
then merges the step's outputs back. Two consequences you must design for:

- **Every step capacity declares its own inputs/outputs by DataState**, and
  input validation is **strict** (`capacity._validate_inputs`: missing-required
  *and* no-unexpected). A step whose declared input was not produced upstream
  raises `InterpretationError` (a mis-wired profile). So a modality's downstream
  bodies must consume whatever its `process` step produced — you cannot feed
  `text.tokens` to a body that declares `phase1.structured_input`.
- The all-v0 path is **byte-identical**: the v0 caps declare exactly
  `phase1.raw_input → phase1.structured_input → …`, so a `None`-table /
  `None`-profile dispatcher runs the original Phase-47 flow unchanged.

## Recipe — add a modality

1. **Ingress DataState.** Reuse an existing family's raw DataState (text reuses
   `text.raw`) or register a new one. Its IRI is the modality key.
2. **`process` capacity.** `ingress DS → structured DS`. Reuse a shipped
   capacity where one exists (text reuses `text.space_split`: `text.raw →
   text.tokens`).
3. **`hint` / `derive_goal` / `map` bodies** that consume the modality's
   *structured* DataState (for text, `text.tokens`). Keep them trivial unless a
   real consumer needs more — a real consumer (arc) supplies its own.
4. **`Phase1Profile`** naming those IRIs (unset slots fall back to v0).
5. **Register** the profile in the dispatcher's `modality_profiles` table keyed
   by the ingress DataState IRI, and stamp inputs with `InputEnvelope(value,
   modality=<ingress DS IRI>, source=…)`.

Register the catalog (capacities + DataStates) at bootstrap; **selection is per
input, not per install** — runtime skill-install is a different machine.

## Worked example — text

`mindsos_capacity/builtins/phase1_text.py` is the reference. It wires the
shipped `text.space_split` as the text `process` step (so `text.tokens` becomes
the text modality's structured input) and adds trivial token-consuming
`hint` / `derive_goal` / `map` bodies:

```python
from mindsos_capacity.builtins.phase1_text import (
    install_phase1_text, TEXT_MODALITY_DS,
    TEXT_PROCESS_IRI, TEXT_HINT_IRI, TEXT_DERIVE_GOAL_IRI, TEXT_MAP_IRI,
)
from mindsos_intelligence import Phase1Profile, L4Dispatcher, InputEnvelope, interpret

install_phase1_text(cl)                       # process reuses text.space_split
text_profile = Phase1Profile(
    process=TEXT_PROCESS_IRI, hint=TEXT_HINT_IRI,
    derive_goal=TEXT_DERIVE_GOAL_IRI, map=TEXT_MAP_IRI,
)
d = L4Dispatcher(cl, session=None, kl=kl,
                 modality_profiles={TEXT_MODALITY_DS: text_profile})
interpret(d, InputEnvelope(value="hello world", modality=TEXT_MODALITY_DS))
# → structured_input == ["hello", "world"]; hints == {"n_tokens": 2}
```

`image` / `action` are **contract-only extension points**: the type + selection
contract exists, but no bodies ship until a consumer needs them (RULES §8).

## Gotchas

- **A real `map` slot triggers the map-target-resolves check.** `interpret`
  verifies the returned `task_pattern_iri` resolves in the `task-patterns`
  role-graph (Local → Global). A consumer authors its pattern in its own Local
  scope; a Global demonstration must register the pattern (see the text test
  fixture). The all-v0 path skips this — its trivial pattern is not KL-registered
  and the check is gated on a supplied `map` slot.
- **`source` never selects.** It is carried for provenance only; interpretation
  is identical regardless of source.
- **Reference `resolve` is not a slot.** When a hint reports an indirect
  `reference_kind`, it is composed by `find_pipeline` (ADR-0156) from that
  DataState type to the profile's `resolve_target_datastate` — see ADR-0195.

## See also

- Concept: [Task lifecycle](../../concepts/task-lifecycle.md) (Phase 1).
- ADRs: [0195](../../decisions/adr/0195-phase1-interpretation-seam.md) (seam),
  [0197](../../decisions/adr/0197-modality-aware-input-ingress.md) (modality
  ingress), [0156](../../decisions/adr/0156-l3-bipartite-topology-reframe.md)
  (bipartite `find_pipeline`).
