# CORE CHANGE REQUEST — one unimportable skill must not brick the brain

**Filed:** 2026-07-15 · joint arc1+arc3 core chat
**Surfaced by:** `mindsos brain --user arc1` on the arc1-brain venv — `ModuleNotFoundError:
No module named 'mindsos_arc'`, raised out of `boot_brain` before the REPL starts.
**Status:** IMPLEMENTED (installed-skills path), 2026-07-16 — pending test run on a
3.11 env + owner review. Scope decision: installed-skills only; the learned-capacity
reactivation twin is DEFERRED (As-built §D). The proposal below is preserved as filed;
the **As-built addendum at the foot of this doc** records what actually shipped and where
it diverges.
**Version impact:** none. `core_version` stays `phase50` (additive, non-phase fix).

---

## The defect

`apply_installed_skills` imports and calls every installed bundle's L3 installer with **no
error handling** (`mindsos_server/skills/activation.py:39-46`, verbatim):

```python
activated: List[str] = []
for view in ordered:
    for spec in view.value.get("l3_installers") or []:
        module_name, func_name = spec.split(":", 1)
        fn = getattr(importlib.import_module(module_name), func_name)
        fn(cl)
    activated.append(view.bundle_name)
return tuple(activated)
```

`boot_brain` calls it unconditionally on the durable path (`mindsos_server/boot.py:138`).
So an install record naming a module that is not importable **in this process** raises
`ModuleNotFoundError` out of boot, and `mindsos brain` never starts.

### Why it is worse than it looks

1. **`installed-skills` is GLOBAL.** `_installed_skills_graph` walks
   `kl.global_metagraph()` (`records.py:53-58`). One bad record blocks **every user** —
   changing `--user` does not help.
2. **The venv, not the DB, decides importability.** A bundle installed from one venv/repo
   lane (here: the `mindsos_arc` packaging lane) is recorded Globally in Falkor, but the
   module only exists where it was pip-installed. Any *other* checkout that boots against
   the same Falkor inherits a fatal record it never created. `arc1-brain` contains zero
   references to `mindsos_arc` (verified: repo-wide grep, 0 hits).
3. **It contradicts the system's own principle.** MindsOS's stated posture is honest
   don't-know by construction. An absent skill is the textbook don't-know: report it,
   skip it, run everything else. Today it is a traceback.
4. **Recovery requires the CLI that the crash does not block** — `mindsos skill uninstall
   <name> --flush` works only because it is a separate command. Had this been wired into a
   server-startup hook (ADR-0183 §6 stage 2 anticipates that), the system would be
   unrecoverable without DB surgery.

## Reproduction

Any Falkor DB with an `installed` record whose `l3_installers` names a module absent from
the booting venv:

```
mindsos brain --user <any>          # ModuleNotFoundError out of boot.py:138
mindsos brain --user <any> --ephemeral   # OK — client is None skips activation (boot.py:119-127)
```

## Proposed fix

Make activation resilient at boot, strict on explicit invocation:

```python
def apply_installed_skills(cl, kl, *, strict: bool = True):
    ...
    for view in ordered:
        try:
            for spec in view.value.get("l3_installers") or []:
                module_name, func_name = spec.split(":", 1)
                fn = getattr(importlib.import_module(module_name), func_name)
                fn(cl)
        except (ImportError, AttributeError) as exc:
            if strict:
                raise
            log.warning(
                "skill %r not activated: %s (%s). The bundle's L3 installer is not "
                "importable in this process; its capacities are absent.",
                view.bundle_name, exc.__class__.__name__, exc,
            )
            skipped.append((view.bundle_name, str(exc)))
            continue
        activated.append(view.bundle_name)
```

- `boot_brain` (`boot.py:138`) passes **`strict=False`** — a brain boots with what it has.
- `mindsos skill activate` keeps the **default `strict=True`** — an explicit activate that
  cannot activate should fail loudly.

## Why this is additive-inert

`strict=True` is the default, so every existing call site is byte-identical. The only
behaviour change is at `boot.py:138`, which is exactly the reported bug. Clears the
design-log §0 additive-inertness gate.

## Scope of the catch — deliberate

Catch **`ImportError` / `AttributeError` only** — the "bundle is not present here" case,
where nothing was registered and skipping leaves a clean layer.

Do **not** catch exceptions raised from `fn(cl)` itself. An installer that raises midway
has already partially registered capacities; swallowing that would leave the layer in an
undefined half-state, which is worse than refusing to boot. A broken installer is a
genuine hard failure.

*Open question for the owner:* is that split right, or should a mid-installer failure also
be survivable (requiring per-bundle rollback, which does not exist today)?

## Reporting the skips

The current signature returns `Tuple[str, ...]` (activated names). Skips need to reach the
operator — a `log.warning` alone is invisible in a REPL.

*Open question for the owner:* pick one —
- **(a)** keep `Tuple[str, ...]`, log only. Zero caller churn, weakest visibility.
- **(b)** return `ActivationReport(activated: Tuple[str,...], skipped: Tuple[Tuple[str,str],...])`.
  Two in-repo callers to touch (`boot.py:138` ignores the return; the `skill activate`
  verb, `mindsos_cli/commands/skill.py:223`, renders it). Best visibility; the brain can
  print a startup banner naming unactivated bundles.

Recommend **(b)** — an unactivated skill is exactly the kind of thing the operator must be
told about, and silent degradation is the failure mode this CR exists to remove.

## Does the record vocabulary already cover this?

The docstring says *"Uninstalled / failed bundles are skipped (ADR-0183 §8 step 4)"*, and
`SkillRecordView` carries a `status` field (`records.py:40-48`), filtered at `:35` on
`status == "installed"`. That `failed` status is an **install-time** state. This CR does
**not** propose writing `failed` back at activation time — activation is per-process and
the record is durable + Global; a module missing in *this* venv says nothing about the
bundle's validity elsewhere. Skips are process-local and reported, not persisted.

## Tests

Extend the Phase-50 skill suite:

1. Record with `l3_installers` naming a nonexistent module, `strict=False` → returns,
   bundle in `skipped`, other bundles still activated, layer usable.
2. Same record, `strict=True` → raises `ModuleNotFoundError` (pins today's behaviour).
3. Module exists, attribute does not → same two cases.
4. `boot_brain` with a broken record on the durable path → REPL boots (regression test for
   this report).
5. Happy path unchanged — all bundles activate, `skipped` empty.

## Blast radius

`mindsos_server/skills/activation.py` (+ `boot.py:138` one kwarg; + the `skill activate`
verb render if option (b)). No schema change, no role/category/count change, no ADR
decision reversal.

## ADR

**Amend ADR-0183** (skill bundle install lifecycle) recording that per-process activation
is best-effort at boot and strict on explicit `skill activate`, and that activation
failures are process-local and never written back to the durable record.

## Operator workaround until this lands

```bash
mindsos skill list                        # find the bundle
mindsos skill uninstall <name> --flush    # deprecate; --flush persists, or it returns on restart
mindsos brain --user arc1
```
`uninstall` deprecates (never deletes) and flips `status` off `"installed"`, which
`activation.py:35` already filters. `--ephemeral` also boots, but skips Falkor entirely.

---

# AS-BUILT ADDENDUM (2026-07-16)

Reviewed across multiple skeptical passes; the implementation diverges from the proposal
above in four deliberate ways. Records the resolution of both open questions.

## A. Resolve / apply split — the proposal's catch scope was too narrow AND self-contradictory

The proposal caught `(ImportError, AttributeError)` around a block that **included**
`fn(cl)`, so it would have swallowed an installer raising those types mid-registration —
contradicting its own "do not catch `fn(cl)`" prose. It also missed a malformed
`l3_installers` spec (`ValueError` from `split`) — the exact corrupt-Global-record case the
CR exists to survive.

As built, each bundle is processed in two phases with different failure semantics:

- **resolve** — `import` + `getattr` of every installer, via the new shared
  `mindsos_server/skills/entry_points.py::resolve_entry_point`, which raises a neutral
  `EntryPointError` for *every* "not resolvable here" cause (malformed spec, unimportable
  module, missing attribute, non-callable). No side effects on `cl`. A resolve failure ⇒
  skip the bundle cleanly (nothing was registered).
- **apply** — call each `fn(cl)`, **outside** the resolve `try`.

The driver's `_resolve_entry_point` now delegates to the same shared resolver and re-raises
`SkillInstallError`, so install-time behaviour (failed-record on resolve error) is unchanged.

## B. Open question 1 (catch `fn(cl)`?) — RESOLVED: yes, at boot; leave-partial, no rollback

The proposal left `fn(cl)` failures fatal. **Rejected.** For a Global record, re-raising on a
mid-apply failure re-introduces the headline harm (one bad record bricks every user) for any
importable-but-broken installer. There is no per-bundle rollback in the layer, and the whole
system's recovery grain is idempotent `if_exists="upsert"` re-run (see
`capacity_layer.register_capacity`, `driver` S8). So at boot (`strict=False`) an apply
failure is **skipped, reported, and left partially registered** — repaired by the next boot's
upsert. The skip reason is tagged `apply-failed (possibly partial)` so it is distinguishable
from a clean `unresolved:` skip. On explicit `skill activate` (`strict=True`, default) both
resolve and apply failures re-raise — fail loud.

## C. Open question 2 (reporting) — RESOLVED: option (b), made additive-inert

`apply_installed_skills` now returns `ActivationReport(activated, skipped)`. To keep every
pre-existing caller and the three `TestActivation` assertions **byte-identical**,
`ActivationReport` **subclasses `tuple`** and *is* the tuple of activated names (equality,
iteration, `join`, `len` unchanged); `.skipped` — a tuple of `(bundle_name, reason)` — is
additive. `boot_brain` passes `strict=False`, logs each skip at WARNING, and carries the
report on `Stack.activation` (a new field, default `None`) for a future REPL banner. The
`skill activate` verb renders skips and gains `--best-effort` (resilient diagnosis; default
stays strict → non-zero exit on the first failure).

## D. Scope — learned-capacity reactivation twin DEFERRED (new finding)

The learned-capacity reactivation path (`local_boot.reactivate_local_capacities` →
`mindsos_capacity.reactivate_from_descriptors` → `build_declaration`) crashes out of boot the
same way. But a trace found **no production code registers a reactivation factory** — every
`register_reactivation_factory` call in the repo is in tests. So the learned crash is
**dormant because the feature is unwired**, not merely unhardened; a durable Local carrying a
reactivatable descriptor would already crash today for lack of a factory. Hardening that path
now would **silently swallow the missing factory-registration wiring** — the very
silent-degradation failure mode this CR removes. DEFERRED until factory registration is wired
into resident-brain boot. Tracked as a follow-up.

## Follow-ups within the installed-skills path

- **Advisory capacity verification** — LANDED 2026-07-16. After a bundle's installers run
  clean, `_warn_missing_declared_capacities` warns (log-only, in `activation.py`) if the
  record's declared `l3_capacities` are absent from `cl` — catching an installer that
  succeeded but did not register its declared surface. Reads `cl._capacity_index` (as
  preflight does), never raises, and never changes activation classification; a bundle whose
  installer registers a different set than it declares (rare) is a tolerable false positive.
- **Builtins alignment for `skill activate`** — LANDED 2026-07-16. `boot._install_builtins`
  is now public `install_brain_builtins`; `skill activate` builds its `cl` via a new
  `_build_brain_cl` using that full builtin set, so it faithfully rehearses boot (`skill
  install` keeps the text-only `_build_cl`).

## Files touched

New: `mindsos_server/skills/entry_points.py`,
`tests/phase_50/test_skill_activation_resilience.py`.
Edited: `mindsos_server/skills/activation.py` (rewrite + advisory capacity verify),
`mindsos_server/skills/__init__.py` (exports),
`mindsos_server/skills/driver.py` (shared resolver),
`mindsos_server/boot.py` (`strict=False`, WARNING log, `Stack.activation`; `_install_builtins`→public `install_brain_builtins`),
`mindsos_cli/commands/skill.py` (report render + `--best-effort`; `_build_brain_cl` for full-builtin activate).
No schema / role / category / count change; no ADR decision reversal.

## ADR

Formal **ADR-0183 §am-2** amendment (activation is best-effort at boot, strict on explicit
`skill activate`; failures are process-local and never written back) still OWED as a separate
edit — held out of this change because ADR files are gated by
`tests/test_adr_status_consistency.py` and warrant their own commit.

## Verification status

`py_compile` clean on all six code files; `ActivationReport` tuple semantics unit-checked
standalone. Full `pytest` **not run here** — the connected Linux workspace is Python 3.10
(the code needs 3.11+ `datetime.UTC`) with no pytest and no network to install one. Run on a
3.11 env:

```bash
python -m pytest tests/phase_50/test_skill_activation_resilience.py \
                 tests/phase_50/test_skill_install_driver.py::TestActivation -q
# regression sweep:
python -m pytest tests/phase_50 tests/f9 tests/composition_lifecycle -q
```
