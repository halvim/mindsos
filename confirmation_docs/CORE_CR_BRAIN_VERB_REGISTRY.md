# CORE CHANGE REQUEST — skill-declared brain verbs (consume `[l4].slots`)

**Filed:** 2026-07-17 · joint arc1+arc3 core chat
**Consumer of record:** arc1 (D1.1 shape A — `arc solve task 7`); arc3 next (own verb)
**Status:** ✅ MERGED to main — PR #54 (rebase-merged, 2026-07-18), main tip `619b007`; recorded as **ADR-0183 §am-3**; final Linux gate 4248/0. See **Outcome (as built)** below.
**Version impact:** none expected. `core_version` stays `phase50` (CLI + an L4 read of an
already-persisted manifest field; no domain surface).

---

## Outcome (as built — 2026-07-18)

**Merged to main** via PR #54 (rebase-merged, main tip `619b007`; final Linux gate 4248/0);
recorded as **ADR-0183 §am-3**. Landed as the top of the 4-CR train (dataset #53 → CR#3 #51
→ CR#4 #52 → this #54), each rebased onto the prior + gate-green before merge.
Changes vs the proposal below:

- **D-1 preflight `verb-conflict` — DROPPED.** Putting the builtin-verb set in
  `preflight.py` (`mindsos_server`) would couple it to `BrainREPL` (`mindsos_cli`) — a
  `server→cli` dependency, or a drift-prone duplicate list (the drift the ADR-status gate
  exists to prevent). Instead the REPL drops builtin-shadowed verbs at construction
  (runtime-authoritative, and it also catches builtins added *after* a Skill was
  installed). An optional CLI-side install pre-check is **deferred** (Option 3).
  `preflight.py` was not touched — so the "Blast radius" below overstates it.
- **D-2 collision — first-wins**, on both verb *and* modality, by install `seq` (matches
  preflight's IRI-collision precedent). Modality collisions are guarded too — the CR named
  only verbs.
- **`pending_confirmation` (ADR-0196) surfaced**, and `run_lifecycle` raises caught, so a
  mis-registered skill can't crash the REPL — the CR's `_run_skill_verb` sketch had
  neither.
- **Open question resolved:** one-brain-one-Falkor (arc1/arc3 on separate instances); the
  collision guards still apply *within* a single instance that hosts several Skills.

Blast radius as shipped: `mindsos_server/boot.py` + `mindsos_cli/commands/brain.py` only
(no `preflight.py`, no manifest field, no schema/record migration). Tests:
`tests/resident_brain/test_skill_verbs.py` (12 unit) + `test_skill_verb_durable.py`
(`@integration`, live Falkor).

---

## The defect

`BrainREPL` dispatches verbs by attribute lookup on itself (`mindsos_cli/commands/brain.py:70`,
verbatim):

```python
verb, args = tokens[0], tokens[1:]
handler = getattr(self, f"_do_{verb}", None)
if handler is None:
    return f"unknown verb: {verb!r} (try 'help')"
```

**Verbs are hardcoded methods. An installed Skill cannot contribute one.** So a Skill's
entry point can only be reached through the generic `task` verb, which is itself unusable
for a Skill (below).

### `task` cannot carry a Skill's input

```python
# brain.py:617-622 (verbatim)
def _do_task(self, args):
    text = " ".join(args)
    outcome = self.stack.orch.run_lifecycle({"text": text})
    return f"task: {outcome.status}"
```

Two hard blocks:

1. **No `InputEnvelope`** → `modality=None` → ADR-0197 legacy path. A Skill that declares
   an ingress modality can never be routed to.
2. **`{"text": text}`** — a dict, not the Skill's declared ingress shape.

And since ADR-0197 Amendment 1 shipped, `modality not in dispatcher.modality_profiles`
**raises** (*"unroutable modality"*) and no longer falls back to the construction-bound
profile. So there is no path from `mindsos brain` to a Skill's lifecycle at all.

## The hook already exists and is unread

`SkillManifest` carries **`l4_slots: Mapping[str, Any]`** (`manifest.py:63`), parsed from
`[l4].slots` (`manifest.py:165-168`), and written into the durable install record
(`driver.py:143`: `"l4_slots": dict(manifest.l4_slots)`).

**Repo-wide grep: nothing reads it.** It is a shipped, persisted, generic L4 extension
point with no consumer — exactly this CR's shape. No new manifest field, no schema change,
no record migration.

## Proposed

### 1. Manifest — declare the verb + the Phase-1 binding as data

```toml
[l4.slots]
verb                     = "arc"
modality                 = "datastate:arc.raw_text"
process                  = "capacity:perception:arc.text_space_split"
hint                     = "capacity:hint:arc"
map                      = "capacity:decision:arc_map"
resolve_target_datastate = "datastate:arc.raw_task"
```

### 2. `boot_brain` — build the modality table from the records

After `apply_installed_skills`, read each installed record's `l4_slots` and construct:

```python
modality_profiles = {
    slots["modality"]: Phase1Profile(
        process=slots.get("process"),
        hint=slots.get("hint"),
        derive_goal=slots.get("derive_goal"),
        map=slots.get("map"),
        resolve_target_datastate=slots.get("resolve_target_datastate"),
    )
    for slots in (r.value.get("l4_slots") or {} for r in installed_records)
    if slots.get("modality")
}
dispatcher = L4Dispatcher(cl, session=session, kl=kl, modality_profiles=modality_profiles)
```

This also closes **arc1 D1.13** — the brain never constructs a dispatcher with
`phase1_profile=`; the table is built from the manifests.

### 3. `BrainREPL` — a verb table, checked after builtins

```python
handler = getattr(self, f"_do_{verb}", None)
if handler is not None:
    return handler(args)
slots = self._skill_verbs.get(verb)          # {verb -> l4_slots}
if slots is not None:
    return self._run_skill_verb(slots, args)
return f"unknown verb: {verb!r} (try 'help')"
```

```python
def _run_skill_verb(self, slots, args):
    outcome = self.stack.orch.run_lifecycle(
        InputEnvelope(value=" ".join(args),
                      modality=slots["modality"],
                      source="brain-cli"))
    return f"{outcome.status}"
```

`help` lists builtin verbs plus the installed skill verbs.

## Key property — the verb is DATA, not a callable

A Skill declares a **verb name + a modality + four capacity IRIs**. It does **not** inject
a callable into the REPL. Core builds the envelope and calls `run_lifecycle`; the Skill's
behaviour is reached only through its registered capacities via the L4 dispatcher.

This is the difference between an extension point and arbitrary code in the REPL namespace,
and it is why the collision rule below is a naming question rather than a security one.

## Design decisions

**D-1 — Builtins win.** `getattr` is checked first; a skill verb named `ls`/`save`/`task`
is unreachable. **Reject at install-time preflight** (`preflight.py`) with a
`verb-conflict` rejection naming the builtin, rather than installing a dead verb. Preflight
already rejects `realm-conflict` the same way; this follows that precedent.

**D-2 — Skill-vs-skill collision.** Two installed Skills declaring `verb = "arc"` →
preflight rejects the second (the first is already recorded). *Owner: confirm — or should
the later install win, mirroring `_declarations` last-registration-wins?*

**D-3 — `modality` is optional in slots.** A Skill with no `modality` contributes no verb
and no profile entry. Keeps `l4_slots` usable for future L4 bindings.

**D-4 — Unresolvable slots.** If `slots["process"]` names a capacity absent from the layer
(its installer was skipped — CR#3 `strict=False`), the profile would be built against a
missing IRI and fail at first use with ADR-0197's Mode-B raise. **Skip the verb** for any
bundle in `Stack.activation.skipped`, and say so in `help`. *This is why CR#3 must land
first.*

## Ordering

**CR#3 (activation resilience) is a hard prerequisite.** This CR makes the bundle path the
normal route for both brains, and D-4 depends on `Stack.activation.skipped` — which CR#3
introduces.

## Tests

1. Manifest with `[l4.slots] verb/modality/process/...` → parsed, persisted, and read back
   at boot into `modality_profiles`.
2. `arc solve task 7` → `run_lifecycle` receives an `InputEnvelope` with
   `modality == datastate:arc.raw_text`.
3. Skill verb colliding with a builtin → preflight rejects (`verb-conflict`).
4. Two skills, same verb → second install rejected (pending D-2).
5. Bundle in `activation.skipped` → its verb is absent; `help` reports it.
6. `l4_slots` absent / no `modality` → no verb, no profile entry, `task` unchanged.
7. Existing `task`/`invoke`/`execute` verbs byte-identical.

## Blast radius

`mindsos_cli/commands/brain.py` (verb table + `_run_skill_verb` + `help`),
`mindsos_server/boot.py` (build `modality_profiles` from records),
`mindsos_server/skills/preflight.py` (verb-conflict check). No manifest field, no schema,
no record migration, no `__all__` delta.

## ADR

**Amend ADR-0183** recording that `[l4].slots` is consumed at boot: it binds a Skill's
brain verb, its ingress modality, and its Phase-1 capacity slots. Cross-ref ADR-0195
(`Phase1Profile`) + ADR-0197 (modality ingress).

## Why core and not the brain

`BrainREPL` is core's. Every Skill — arc1, arc3, bongard — needs the same seam, and today
none of them can reach `run_lifecycle` from the brain at all.

## Open question for the owner

**Two brains, one Falkor?** `installed-skills` is Global (`records.py:53-58`), so if arc1
and arc3 share a Falkor instance, both verbs and both modality profiles appear in either
brain. arc3's own doc pins a separate instance (`arc3-falkordb`, :6380), which makes this
moot — but the design should say whether "two brains" means "two Falkors" or whether one
brain legitimately holds several Skills.
