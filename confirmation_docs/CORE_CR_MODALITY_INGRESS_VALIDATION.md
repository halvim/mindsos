# CORE CHANGE REQUEST — validate the modality against the declared ingress

**Filed:** 2026-07-15 · joint arc1+arc3 core chat
**Consumer of record:** arc1 (D1.2 `arc.raw_text` modality + D1.3 `arc.text_space_split`)
**Status:** proposed — NOT built. Needs owner approval before any code.
**Version impact:** none. `core_version` stays `phase50` (additive, non-phase feat).

---

## The defect

`interpret()` uses `modality` for **one thing only** — the `{modality -> Phase1Profile}`
table lookup (`mindsos_intelligence/phase_1.py:211-212`). It then takes the ingress
DataState from the *selected process capacity's declaration*, not from the modality:

```python
# phase_1.py:211-223 (verbatim)
if profile is None and modality is not None:
    profile = (getattr(dispatcher, "modality_profiles", None) or {}).get(modality)
if profile is None:
    profile = getattr(dispatcher, "phase1_profile", None)

process_iri = _slot(profile, "process", PROCESS_IRI)
ingress_ds = dispatcher.capacity_layer.get_declaration(process_iri).inputs[0]
env: dict = {ingress_ds: value}
```

Nothing checks that `modality == ingress_ds`. ADR-0197 defines modality as *"the ingress
DataState IRI naming the input's type (the capacity-selection key)"* — so the two are
**contractually the same thing**, and the code never enforces it.

### Failure mode A — silent v0 fiction (the dangerous one)

Stamp a modality with **no** table entry (typo, unregistered profile, boot-order bug):

1. `profile = table.get(modality)` -> `None`
2. `profile = dispatcher.phase1_profile` -> `None`
3. **All four slots fall back to v0** (`_slot` returns the default when `profile is None`)
4. `process.identity` seeds `env = {phase1.raw_input: value}`
5. `hint.global` -> `{}`; `decision.derive_goal` -> `{"goal": "v0:trivial-goal"}`;
   `decision.map_to_task_pattern` -> `task-pattern:v0:trivial`, confidence **1.0**
6. The real-consumer validation at `:236` is gated on `profile is not None and
   profile.map is not None` -> **skipped entirely**

Result: a wrong modality returns a **confident trivial answer** instead of an error.
No exception, no log, no dont-know.

### Failure mode B — mislabel

Profile found, but its `process` cap declares a different ingress. `env` is seeded
consistently from the declaration, so nothing breaks — the `modality` is simply a lie
recorded on the envelope. Declared != actual.

---

## The fix

One check covers both modes. Insert after `ingress_ds` is resolved (`phase_1.py:222`):

```python
process_iri = _slot(profile, "process", PROCESS_IRI)
ingress_ds = dispatcher.capacity_layer.get_declaration(process_iri).inputs[0]
if modality is not None and modality != ingress_ds:
    raise InterpretationError(
        f"modality {modality!r} selected process {process_iri!r} whose declared "
        f"ingress is {ingress_ds!r}; ADR-0197 defines the modality AS the ingress "
        f"DataState (no profile registered for this modality?)"
    )
env: dict = {ingress_ds: value}
```

Mode A raises because the v0 fallback's `ingress_ds` (`phase1.raw_input`) != the stamped
modality. Mode B raises directly.

## Why this is additive-inert

- `modality is None` -> **no check**. Every existing caller is unaffected: core's tests
  pass raw values, arc1 passes a raw string (`arc_intake.py:185`), arc3 does not call
  `interpret()` at all (verified: zero hits in both repos for `InputEnvelope`).
- The all-v0 path is byte-identical.
- The only behaviour change is on a code path that today returns a fiction.

Clears the design-log §0 additive-inertness gate. Same class + precedent as **ADR-0200**
(`reads_mm` gates `mm_handle`): enforce an already-declared contract, zero core breakage.

## ADR

**Amend ADR-0197** (modality-aware input ingress) with an amendment recording that the
modality is enforced to equal the declared ingress DataState. No new ADR — this enforces
0197's own definition. Status stays Accepted; add to the amendment trail.

## Tests

Extend the existing `tests/modality_ingress/` suite (5 tests today):

1. `modality` stamped + matching profile -> passes, unchanged outputs.
2. `modality` stamped + **no** table entry -> raises `InterpretationError` (today: returns
   `task-pattern:v0:trivial` at confidence 1.0 — pin the old behaviour as the regression
   this closes).
3. `modality` stamped + profile whose `process` declares a different ingress -> raises.
4. `modality=None` (raw value) -> unchanged, no check.

## Blast radius

One file (`mindsos_intelligence/phase_1.py`), one insert, ~5 lines. No export change,
no `__all__` delta, no role/category/count change, no schema touch.

## Why core and not the brain

Without it, **every** Local brain writes the same boot-time check over its own
`modality_profiles` table. The selection key belongs to core's contract; core should
enforce it. arc1 is the first consumer to stamp a modality, which is why it surfaces now.

## Open question for the owner

Should a stamped modality with no registered profile be an **error** (this proposal) or a
**deliberate fallback** to the construction-bound/v0 profile? This CR assumes error — a
modality is a claim about the input's type, and silently reinterpreting it as something
else is the fiction. If fallback is wanted, the check narrows to mode B only.


---

## As-built addendum — SHIPPED 2026-07-16 (supersedes "proposed" above)

**Status: SHIPPED to main** — merge `c9cd0e3` (`228e81d..c9cd0e3`); full
containerized gate **4201 passed / 0 failed**. Recorded as **ADR-0197
Amendment 1**. `core_version` stays `phase50`.

The shipped fix **differs from the proposal above** — three corrections found
during review:

- **Not the single `modality != ingress_ds` check.** That conflated the two
  failure modes and false-raised on a legitimate config (a stamped non-raw
  modality with the `process` slot unset -> v0 identity ingress `raw_input`).
  Shipped as **two split guards** in the selection path instead: **Mode A** =
  `modality not in dispatcher.modality_profiles` -> raise (`"unroutable
  modality"`), and it does **not** fall back to the construction-bound profile;
  **Mode B** = after resolving the selected profile's process,
  `ingress != modality` -> raise (`"requires them equal"`).
- **Open question RESOLVED = error (raise), not fallback.** A stamped modality
  is a claim about the input's type; silently reinterpreting it as `v0:trivial`
  is the fiction. The construction-bound `phase1_profile` fallback now serves
  the `modality=None` legacy path **only**.
- **"Additive-inert" claim RETRACTED.** The change reverses shipped, tested
  behaviour: `test_unknown_modality_falls_back_to_v0` asserted the v0 fallback
  as intended. It was **inverted** to `test_unknown_modality_raises_not_v0`, and
  `test_modality_routes_to_wrong_ingress_raises` added (`tests/modality_ingress`
  5 -> 6). So this is a **policy reversal carried by the ADR amendment**, NOT a
  design-log §0 additive-inertness enforcement.

**No new verdict type.** `interpret` already raises `InterpretationError` for
its dont-know-class conditions (unresolvable `map`, below-threshold confidence;
ADR-0157 family dont-know discipline). `run_lifecycle` maps the raise to a
terminal `TaskOutcome.status = dont_know`. Raising IS the graceful path.

**CR self-contradiction noted:** the proposal claimed both "arc1 is the first
consumer to stamp a modality" and "zero `InputEnvelope` hits in both repos." The
second held — **no live consumer stamps a modality yet**, so this is pre-emptive
hardening: correct, but not the live-bug the proposal implied.

**Deferred (designed, not built):** boot-time `validate_modality_table()`
(fail-at-CI vs the shipped fail-at-first-use Mode-B guard); killing the
v0-trivial default / mandatory boundary stamping; threading
`DontKnowReason.UNHANDLED_INPUT` into the raise for richer L4 telemetry.

**Docs updated:** ADR-0197 (Amendment 1), `docs/dev/internals/phase1-ingress.md`
(selection order + gotcha), `docs/concepts/task-lifecycle.md` (one clause),
`mindsos_intelligence/phase_1.py` (interpret docstring + comment), STATE.json
(recent entry).
