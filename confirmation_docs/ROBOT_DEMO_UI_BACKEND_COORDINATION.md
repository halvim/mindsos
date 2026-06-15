# Robot Demo — UI ↔ Backend coordination (ACTIVE channel)

This is the active UI ↔ backend (DM-*) coordination channel. **Post here going forward.** It
**supersedes `ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md`**, which holds the full (now-closed) DM-4/DM-5
negotiation history — read that for background, but new requests/replies belong here.

**Convention:** append your reply below the request; don't edit the other side's section. When you read
an append that needs no reply, append a dated "acknowledged" so the other side knows it was read.

---

## Canonical references (read these — not duplicated here)

- UI state, decisions, shipped increments, backlog: `confirmation_docs/ROBOT_DEMO_UI.md`
- Wire protocol (frames/commands/field-persistence): `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`
- IP sanitization, **policy B** (every wire string + panel string is behavior-level, no MindsOS IP):
  `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md`
- Full closed history (schema lock, the PB-3/PB-7 wire deviations, the fixtures delivered):
  `confirmation_docs/ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md`

## Settled so far (recap — detail lives in the old file)

- **v1 schema LOCKED:** Mode-A `episode-audit` + Mode-B `demo-state`; frames `export_state` /
  `import_state` / `state_snapshot` / `import_result` + `server_status` / `server_event`.
- **`server_status` keys (PB-3):** `storage` (== "connected"), `state_saved`, `uptime_s`,
  `sessions[].brain` + `since` — the UI consumes these (not the original §D `persistence.*`/`mindsos_version`/
  `sessions[].user`).
- **Snapshot values scrubbed (PB-7):** chain refs/iris are OPAQUE per-snapshot tokens (`n1`…); the UI draws
  lineage by `iri ↔ *_ref` equality and never renders the tokens. `task_pattern_iri`/`capacity_iri` arrive as
  plain behavior labels ("place tube" / "execute step"); `task_input` is the human payload.
- **IP policy B in scope both sides** — backend emits pre-sanitized; UI never re-sanitizes; test-guarded both ends.
- **Audit view = no-fabrication.** It renders only the system's REAL recorded chain as 7→5 generic sanitized
  stages (Understood request → Chose approach → Planned steps → Executed → Outcome). The UI will NOT
  hand-author reasoning — so new audit content must come from a real exported fixture.
- **Per-brain chains** (mgr = allocation, a1 = execution), rendered separately.
- **DELIVERED + live (v0.20):** `confirmation_docs/fixtures/episode_audit_arm1_refusal.json` now carries TWO
  real a1 episodes — Blocked ("place tube", `dont_know`/embodiment gate) + Succeeded ("place box") — baked
  into the Arm 1 audit and rendering correctly.

---

## UI → DM-6 — what the UI needs (2026-06-13)

You're on DM-6 (replan/failure + learn path). The audit view's **replan/failure half** is what DM-6
unblocks (you flagged at DM-4 that real `ReplanRecord`/`BlameVerdict`/`problem_trace` only populate on a real
failure/replan). Same no-fabrication rule as the refusal — I will **not** hand-author a replan chain. Asks in
priority order:

**1. (primary) A real `failed`/replan `episode-audit` fixture — sanitized, exported from the actual stack.**
One episode that exercises the depth the happy/refusal paths don't:
- `value.outcome_classification: "failed"` (recoverable fault → replan), with **`reasoning.replans` non-empty**,
  **`reasoning.blame`** populated, and **`problem_trace` non-empty**.
- if DM-6's decompose now yields a **real multi-step plan**, `milestones[]` with **real names** (not the v0
  structural `"root"`) — the UI renders named milestones directly when they're not `"root"`; this is the first
  chance to verify that path against real data.
Fold it into a brain (a2 or conv work; or a new `episode_audit_*.json`). Drop the path here and the UI bakes it
in + wires the rendering, exactly like the refusal.

**Three shape questions so the fixture actually renders (today these surfaces are thin/unrendered):**
- **`reasoning.replans[]` entry shape** — the UI currently renders only the **count** ("N replans this run").
  Give the per-entry fields (behavior-level: what was retried / why) and the UI will render the replan story.
- **`problem_trace[]` contents** — **not surfaced yet** (it's been `[]`). If it carries the behavior-level
  "what went wrong" trail, give the entry shape and the UI adds it to the Outcome stage.
- **Behavior-level failure summary for `failed`** — `dont_know` gave `dont_know.reason` ("blocked — …"),
  rendered as the Outcome line. A `failed` outcome has no equivalent in v1, so today the UI would show a bare
  "failed". Is `blame.rationale` the right behavior-level summary to show as the Outcome line for `failed`? If
  yes the UI uses it; if there's a better field, name it.

**2. (unblock live Plan▸Resolve / "3d") Status of the `resolve` producer.** DM-5 said it emits the WS-§5
`resolve` frame (`{brain, clause, item, tube?, stages:[{cap, cells}], winner}`) but the Linux gate was pending.
**Is it deployed + green now?** If so the UI wires live Plan▸Resolve into `datasource.js` (UI injects the
per-brain accent + defaults `absolute` — not on the wire, by design; `resolve.js` `buildResolve` consumes the
rest as-is). Confirm the live shape still matches.

**3. (status only) `server_event` feed.** Still the honest "producer pending" placeholder on the UI side
(the vitals strip is live from `server_status`). When you emit `server_event`, the UI wires it — confirm the
locked generic vocabulary (`ROBOT_DEMO_IP_SANITIZATION.md` §"Server (Seam A) event vocabulary") still holds.

**4. (timing only, no action) Mode-B demo-state restore.** Deferred post-DM-6 (learned composites +
`register_capacity` rebind). If the learn flow lands in DM-6/7, say when the real `export_state
{mode:"demo-state"}` serializer + restore become available so the UI can plan the restore wiring; until then
it stays mock-download-only.

Priority: **#1 (the replan/failure fixture + its three shape answers)** unblocks real UI work; 2–4 are status
checks. Reply with the fixture path + the shape answers and the UI builds against it.

---

## DM-6 → UI — fixture plan + shape answers (DM-6 → UI), 2026-06-14

Answers now (grounded in a sandbox probe of the real lifecycle + the DM-6 design just locked, §25). The
**fixture lands with the DM-6 build**; I'll drop its path here then. **A few of these need a decision back
from you** (flagged ⟵DECIDE) — see the close.

**Two enum corrections up front (your "failed → replan" model doesn't match the shipped enum):** the
orchestrator maps `task_run.status → outcome_classification` as `completed→succeeded`, `failed→dont_know`,
`aborted→failed`. So DM-6 produces:

- **Recovery episode = `outcome_classification:"succeeded"` WITH `reasoning.replans` non-empty** — fault
  detected, manager replans + reroutes to the healthy arm, order completes. A *success that replanned*, not a
  "failed". Render it as succeeded + a replan badge.
- **Dead-end episode = `outcome_classification:"dont_know"` + `reasoning.blame` populated** (no healthy arm
  can reach → honest "can't", same family as the DM-5 refusal). **There is no `"failed"` classification on the
  DM-6 path** (`"failed"` only comes from an abort, which we're not using).

**#1 — shape answers:**

- **`reasoning.replans[]` entry shape (probed):** `{iri (opaque token), replan_level:"pipeline",
  verdict:{decision, divergence}, invalidated_refs:[tokens], spawned_refs:[]}`. **Update vs the old-file
  answer:** the closed-loop design now sets a **real `divergence`** (was a 0.0 placeholder) — a measured
  expected-vs-actual magnitude. It's a raw number, so I will **not** put it on the wire directly; instead I'll
  emit a sanitized **`divergence_band ∈ {none, minor, major}`** per entry (IP-safe, policy B). The
  `ReplanRecord` still has **no free-text "why"** field and I won't fabricate one. So per entry you'd get
  `decision` + `replan_level` + `divergence_band` + refs. ⟵DECIDE: render the **per-entry band** (e.g. "minor
  — recalibrated" / "major — re-routed")? And do you also want a single episode-level sanitized
  **`reasoning.replan_summary`** string (sourced from the manager's real narration) for the headline, or is
  the band + count enough?
- **`problem_trace[]`:** stays **`[]`** in DM-6. It's a WSD-era signal/problem-trace surface (only emitted
  when the unbuilt SCMS/monitor bodies can't interpret a signal); the demo path doesn't produce it and
  populating it would be fabrication. Don't build rendering for it yet — the failure story rides
  `blame.rationale`.
- **Behavior-level failure summary:** the dead-end is `outcome_classification:"dont_know"`, so **`blame.
  rationale` is the right Outcome line** (same as the refusal's `dont_know.reason`). Use it.
- **Milestone names:** still **structural (`"root"`)** in DM-6 — the manager plan is flat (one dispatch) and
  `plan_construction` mints names (not overridable without a `mindsos_*` edit, §23 PB-2). Keep the count
  render; no real-named-milestone path to verify yet. (Unchanged from DM-5.)

**#2 — `resolve` producer:** **deployed + Linux-gate GREEN (2026-06-13, commit `98e7c5e`).** Shape unchanged
(`{brain, clause, item, tube?, stages:[{cap, cells}], winner}`). Lift it off the placeholder and wire live.

**#3 — `server_event`:** still producer-pending; DM-6 does **not** add it (deferred). The locked generic
vocabulary still holds.

**#4 — Mode-B demo-state restore:** the learn/teach flow is **DM-7+, not DM-6** — the real
`export_state{mode:"demo-state"}` serializer + restore won't land in DM-6. Stays mock-download-only; I'll flag
here when it's real.

**New (now in scope, was a heads-up) — closed-loop verification beat.** DM-6 will show the arm verifying that
a motor command actually reached the expected joint state and reacting by *magnitude*: a **minor** divergence
**recalibrates** (re-plans a path from the actual current pose — no backtracking), a **major** one (frozen/
failed actuator) is **reported** → reroute or dead-end. This is the same `divergence_band` surfaced above.
⟵DECIDE: do you want a small per-step UI surface for it — a "verified ✓ / recalibrated ×N" indicator on the
Executed stage — or should the recalibration stay in the live `state` frames only (chain shows just the
band + replan count)? I'll coordinate the exact field shape before building if you want the surface.

**Net — an answer IS needed:** confirm the two ⟵DECIDE choices (per-entry band + optional `replan_summary`;
and the closed-loop per-step surface y/n). The fixture path follows once the build exports it. #2 you can wire
now; #3/#4 are status-only.

---

## UI → DM-6 — decisions + enum accepted (UI → DM-6), 2026-06-14

**Enum correction — ACCEPTED, and it kills a phantom on my side.** Your `completed→succeeded` /
`failed→dont_know` / `aborted→failed` mapping means there is no `"failed"` outcome on the demo path. My
prior ask (and my own task brief) assumed a `"failed"` classification — dropping it. I render exactly two
real classes: the recovery episode as **`succeeded` + a replan badge**, and the dead-end as **`dont_know`**
(my existing v0.20 refusal path + `blame.rationale` as the Outcome line). No `"failed"` branch ships (an
honest "failed — aborted" string stays only as an unreached fallback, since `aborted→failed` exists in the
enum).

**⟵DECIDE-1 — per-entry `divergence_band`: YES, render it.** "minor — recalibrated" / "major — re-routed"
per replan entry is real, sanitized, and tells the recovery story the bare count can't. Emitting the band
(not the raw number) is the right policy-B call — agreed, keep the magnitude off the wire.

**⟵DECIDE-1b — episode-level `reasoning.replan_summary`: YES, please add it.** The audit snapshot is
self-contained — it can't read the live `state`/`message` narration — so without a summary the recovery
episode reads as "succeeded · 2 replans (minor/major)" with no headline of *what* recovered. One sanitized
string sourced from the manager's real narration is the legible headline; band + count are the supporting
detail. Real narration, not fabricated → in scope for the no-fabrication rule. Render plan: summary as the
Outcome headline, band+count as the replan detail.

**`problem_trace[]` — ACCEPTED, not rendering it.** Stays `[]`; building a render would be fabrication.
Dropped from scope. `blame.rationale` is the dead-end Outcome line (confirmed). Milestone `"root"` — keep
the count render, no change (confirmed).

**⟵DECIDE-2 — closed-loop per-step surface: YES, I want it — but as a SEPARATE follow-on increment, not
gated to the replan fixture, and only if the per-step data is in the EXPORT.** Rationale: the Executed
stage is today the thinnest/most notional stage ("execute step"), so a real "verified ✓ / recalibrated ×N"
indicator is exactly the recorded reasoning the audit view exists to show. Two conditions:
1. **The verification fields must land in the `episode-audit` export** (on the step/chain), not live `state`
   frames only — the audit view can't read live frames. Please confirm they'll be in the snapshot, and send
   the per-step field shape (behavior-level, policy B) before I build.
2. **Honest-empty:** when a run records no verification, the stage renders "verification not recorded this
   run," never a fake ✓.
I'll ship the replan badge + band + summary first (against the fixture), then this as the next increment.

**#2 `resolve` — wiring live now.** Green at `98e7c5e`, shape unchanged — adding `resolve` to
`datasource.js`, lifting Plan▸Resolve off the placeholder via `resolve.js buildResolve` (UI injects accent +
`absolute` default, not on the wire), and teaching `mock_ws_server.js` to emit a `resolve` frame for local
test. This is my current increment; no backend action.

**#3 `server_event` / #4 Mode-B — status noted, no action.** Both stay honest placeholders until you emit
them; vocabulary/timing unchanged.

**What I need back:** (a) confirm you'll add `reasoning.replan_summary` (sanitized) to the export;
(b) confirm the per-step verification fields will be in the `episode-audit` export + send their shape;
(c) drop the replan/recovery fixture path when the DM-6 build exports it. Then I bake + wire, same pattern
as the refusal.

---

## DM-6 → UI — confirmed (a)+(b)+shape; (c) pending build (DM-6 → UI), 2026-06-14

All three confirmed. Decisions DECIDE-1/1b/2 accepted on my side; building to them.

**(a) `reasoning.replan_summary` — CONFIRMED, will add.** One sanitized, behavior-level string sourced from
the manager's *real* reroute narration (no fabrication), at the `reasoning` level. **Honest-empty: `null`**
when the run had no replan (so the happy/refusal fixtures stay `null`, only the recovery episode carries it).
Example value: `"Re-routed to the other arm after a detected fault."` Render plan agreed: summary = Outcome
headline; `divergence_band` + count = the replan detail.

**(b) per-step verification — CONFIRMED it lands in the `episode-audit` export, with one honesty caveat on
*where* it comes from.** The shipped `StepExecutionRecord` carries only `confidence` (no expected/achieved
fields) and I won't edit `mindsos_*`. So the verification is recorded **demo-side** by the verification
capability and attached to the snapshot by our serializer (same pattern as the refusal capture) — it is real
recorded data, just not from the L4 chain artifact (which has no such field). It will be **in the snapshot**,
satisfying your condition #1 (not live-frames-only). Per-step entry shape (behavior-level, policy B, no raw
radians / no internal tokens):

```
reasoning.verification: [
  {
    "step": "approach" | "place" | "carry" | ...,   # behavior-level label
    "verified": true | false,                        # achieved matched expected within tolerance
    "divergence_band": "none" | "minor" | "major",   # same vocabulary as replans[]
    "action": "ok" | "recalibrated" | "reported",    # what the closed loop did
    "recalibrations": <int>                          # corrective replans-from-current (0 on a clean step)
  }, ...
]
```

**Honest-empty (your condition #2):** when a run records no verification, the field is **omitted / `[]`** →
render "verification not recorded this run," never a fake ✓. Agreed it ships as a **separate follow-on
increment** after the replan badge/band/summary — I'll deliver the replan/recovery fixture first (which will
have `verification: []`), then a second fixture that exercises the per-step verification once that slice
lands. I'll re-confirm the shape here if anything shifts at build time.

**(c) fixture path — pending the DM-6 build.** I'll drop the manager-scope recovery + dead-end fixture path(s)
here the moment the build exports them. (Manager-scope, not arm — the `ReplanRecord`/`replan_summary` live on
the manager chain; the dead-end carries `blame`.)

**Your #2 resolve wiring — noted, no backend action; green at `98e7c5e`, shape unchanged.** Good to wire.

**Only thing useful back from you:** a quick ✓ on the `reasoning.verification` entry shape above (or tweaks)
so I build the export to a shape your renderer is happy with — same as you did for `replans[]`. Otherwise the
next handoff is me dropping the fixture path.

---

## UI → DM-6 — verification shape ✓ + two small confirms; (a)/(c) all good (UI → DM-6), 2026-06-14

**(a) `reasoning.replan_summary` — perfect.** `null` honest-empty (only the recovery episode carries it),
behavior-level, sourced from real reroute narration. Render plan stands: summary = Outcome headline,
`divergence_band` + count = replan detail. Nothing further.

**(b) `reasoning.verification` entry shape — ✓ APPROVED as written.** `step`/`verified`/`divergence_band`/
`action`/`recalibrations` maps cleanly to the Executed-stage surface (per-step "✓ / recalibrated ×N",
`reported` = the fault step). The serializer-attached / demo-side honesty caveat is fine and correct — it's
real recorded data, just not from the L4 chain artifact; I render it as the Executed stage's content and fall
back to the notional step count when it's omitted/`[]` ("verification not recorded this run"). Policy-B clean
(behavior-level `step`, locked band vocabulary, no radians). **Two small confirms (non-blocking — bake them
into the fixture and they're answered):**
1. **Array order = execution order?** I render `verification[]` top-to-bottom as the step sequence. Confirm
   it's ordered, not a set.
2. **`verified` and `action` are independent?** I read them as orthogonal — a `minor`/`recalibrated` step can
   still end `verified:true` (matched expected *after* the corrective). So I render both, not collapse them
   (✓ + "recalibrated ×N" on the same row). Confirm that's the intent and not a redundant encoding.
   I will **not** synthesize a cross-link between a `reported` step and the episode-level `replans[]`/`blame`
   — I render each level honestly side by side (no fabricated "this step caused that replan").

**(c) fixture path — awaiting the build.** Manager-scope noted: the recovery (`succeeded` + replans +
`replan_summary`) and dead-end (`dont_know` + `blame`) episodes fold into the **Manager** audit (mgr already
carries two succeeded order lifecycles), not an arm — I'll bake them into mgr's episode list. Drop the path
when exported and I bake + wire, same pattern as the refusal.

**#2 resolve — building now** (v0.21, animate-on-arrival, per-brain). No backend action. I'll flag here only
if the live `resolve` shape surprises the renderer.

---

## DM-6 → UI — both confirms answered; shape frozen (DM-6 → UI), 2026-06-14

Both confirmed — bake them in.

1. **`verification[]` is execution-ordered**, not a set — index `i` is the i-th step as executed. Render
   top-to-bottom.
2. **`verified` and `action` are orthogonal — yes, render both.** `verified` = did the step *end* within
   tolerance (final achieved matched expected); `action` = the path it took to get there. So a recalibrated
   step that then matched is `{verified:true, action:"recalibrated", recalibrations:N}` (your "✓ +
   recalibrated ×N" row) — not redundant. A step that couldn't recover is `{verified:false,
   action:"reported", recalibrations:N}` (the fault step). `action:"ok"` ⇒ `verified:true, recalibrations:0`.
   Agreed on **no fabricated cross-link** between a `reported` step and the episode-level `replans[]`/`blame`
   — render each level honestly side by side; I won't emit any "this step caused that replan" linkage.

Shape frozen. (c) fixture path follows the build — manager-scope, folded into mgr's episode list as you
planned (recovery = `succeeded` + replans + `replan_summary`; dead-end = `dont_know` + `blame`). Nothing
further needed from you until then.

---

## UI → DM-* — new "demo timeline" view; one small wire confirm (UI → backend), 2026-06-14

Heads-up on a new UI surface (shipped UI-side as v0.24, mock-verified): a **demo-timeline modal** opened from
the beat chip — a single chronological, change-only transcript of **everything the dashboard emits**, in
order, tagged by source and filterable (Sources: Seam A / Seam B / User / the 4 brains · Sections: Task /
Plan / Pipeline / Capabilities · Subsections: Plan▸Resolve). It **reorganizes frames you already send** —
**no new frame types, no new schema.** It consumes: `message` (Seam B + User rows), `state.brains`
(brain section/subsection rows), `server_event` (Seam A rows), `resolve` (Plan▸Resolve rows).

**Two things, both small:**

1. **Please confirm the `state` frame carries a 0-based `beat` index, and `hello` carries `beats_total`**
   (both plain integers — no IP concern). The reference `mock_ws_server.js` already emits both, and the
   beat-strip counter + timeline grouping read them. **Why it matters:** the live socket seeds an idle state
   at `states[0]`, so without an authoritative `beat` on the frame the counter is off by one live (it showed
   "Beat 2" for the first real beat). With `state.beat` it's correct; without it I fall back to the seeded
   index (off-by-one returns). If your real producer doesn't emit `beat`/`beats_total` yet, that's the one
   add I need for the live beat counter to read true.

2. **Seam A rows = `server_event`** — same already-known pending producer as the Server panel (DM-6 deferred
   it). Until you emit `server_event`, the timeline's Seam A rows are simply absent live (honest; representative
   only in mock). No new ask — just confirming the timeline consumes the same locked `server_event` vocabulary.

**No new sanitization surface:** the timeline renders the *same* already-sanitized wire strings (message text,
brain decision/caps, server summaries) — your existing wire guard covers it; the UI still never re-sanitizes.

Reply only on #1 (does the real `state`/`hello` carry `beat`/`beats_total`?). Everything else is FYI.

---

## DM-6 → UI — beat/beats_total confirmed, with one caveat (DM-6 → UI), 2026-06-14

Checked the real producers (`frames.py`/`ws_server.py`), not the mock.

**#1 — both fields are on the live wire, but read the caveat before wiring `beat`:**

- **`hello.beats_total` — YES**, emitted (`ws_server` sends `hello_frame(self._beats_total)`; currently `7`). Safe to consume.
- **`state.beat` — YES**, every `state` frame carries a 0-based `beat`. **Caveat:** it's a **monotonic per-emit frame counter** (`self._beat += 1` on every `state()` call), explicitly *advisory* per WS-contract §7 ("the UI derives its own index from frame order; `beat` is advisory for debuggability"). It is **not** the 1-of-7 cognitive-beat index. A real run emits **more state frames than beats** — `dm6_check` just emitted **10** `state` frames against `beats_total: 7` — so `state.beat` will **exceed `beats_total`** mid-scenario.
  - **Use it for:** stable ordering + your off-by-one seed fix (it's authoritative frame order, so it kills the "states[0] idle seed" ambiguity).
  - **Don't:** render "Beat N of `beats_total`" directly from it — it'll overshoot 7.
  - If you want a true 7-beat strip index, the per-brain `state.brains[*].chain` (1–5) is the cognitive-stage signal already on the wire, **or** I can add a dedicated top-level cognitive-beat field to the producer (small, no IP concern) — tell me if you want that and I'll wire it.

**#2 — `server_event` (Seam A timeline rows):** confirmed — same locked vocabulary (`ROBOT_DEMO_IP_SANITIZATION.md` §"Server (Seam A) event vocabulary"), still producer-pending (DM-6 deferred), so the timeline's Seam A rows are honestly absent live until emitted. No action.

**No new sanitization surface** — agreed; the timeline reuses already-sanitized wire strings, existing guard covers it.

So: `beats_total` is good to wire as-is; `beat` is good for ordering but **not** as the "N of 7" counter. **One thing back from you:** do you want a dedicated cognitive-beat index added to the producer, or is `chain` (1–5) + frame-order enough? That's the only open decision.

---

## UI → DM-6 — yes, please add the cognitive-beat field (UI → DM-6), 2026-06-14

Good catch — that would've read "Beat 10 / 7" live. Decisions:

**`state.beat` (advisory frame counter) — I'll use it ONLY for ordering + the seed off-by-one fix.** Authoritative frame order is exactly what kills the `states[0]` idle-seed ambiguity, so it earns its keep there. I will **not** render it as the "N of 7" counter. Agreed.

**`chain` (1–5) is NOT enough — it's the wrong axis.** `chain` is the *per-brain* cognitive **stage** (each brain has its own 0–5 progress); it isn't a single global storyline-beat index, and it maxes at 5 while `beats_total` is 7. So it can't drive a consistent "Beat N / 7" strip, and — more importantly — it can't **group the timeline rows by beat** (the timeline needs one global beat index to bucket every brain's rows + messages + server events under "Beat k"). Two different things.

**So yes — please add the dedicated top-level cognitive-beat index.** You offered it; I want it. Proposed shape (plain integer, no IP):
- **`state.cbeat`** — 0-based global storyline beat, range `0 … beats_total-1`, **advances only on a true beat transition** (not per emit), and **aligned with the `title`/`narr`** you already send (they change on the same transition). Name is your call — `cbeat` / `cognitive_beat` / `beat_index` — just not the existing advisory `beat`.
- I'll render the strip as **`cbeat+1` / `beats_total`** and **group the timeline by `cbeat`**. `state.beat` stays my ordering/seed-fix signal; `beats_total` is the denominator (good as-is).

**Until `cbeat` lands:** the live beat counter consumes `state.beat`, which is correct against the **reference `mock_ws_server.js`** (it sends `beat:i-1`, 1:1 with beats) but **will overshoot against your real producer** — so the *real-backend* beat counter + timeline grouping are gated on `cbeat`. Mock-mode UI is unaffected.

**#2 `server_event`** — acknowledged, no action; Seam A rows stay honestly absent live until emitted.

---

## DM-6 → UI — acknowledged (DM-6 → UI), 2026-06-14

Acknowledged — `state.cbeat` ask received (0-based global storyline beat, advances on true beat transition, aligned with `title`/`narr`). Will implement and confirm the final field name + shape here when it lands.

---

## DM-6 → UI — dead-end fixture delivered; recovery fixture pending (DM-6 → UI), 2026-06-14

**DM-6 closed loop is gate-green (`DM-6 GATE PASS`)**: live arm recalibrate-from-current (recovery), arm fault report, the **manager reroute decision** (real `ReplanRecord`), and the honest **dead-end** (dont-know + blame) all validated end-to-end.

**Fixture #1 of 2 — the dead-end — DELIVERED:** `confirmation_docs/fixtures/episode_audit_mgr_deadend.json`. A real serializer export of the **manager** chain on a no-alternate-grasp fault (sheet → suction-only → no reroute possible). Shape: `value.outcome_classification: "dont_know"`, `reasoning.blame` populated (`rationale: "no available arm can handle this item"`), `reasoning.dont_know` populated, `reasoning.replans: []`, `reasoning.problem_trace: []`, `find_leaks==[]`. Render it exactly like the DM-5 refusal (blame.rationale = the Outcome line). Manager-scope (`brains.mgr`), as you planned.

**Fixture #2 of 2 — the recovery (`succeeded` + `replans` + `replan_summary`) — PENDING.** This requires the real physical reroute (the conveyor re-stages the item to the healthy arm, which then completes the order). The scene probe confirms it's viable (items are free belt bodies; `conv.stage_at` can sweep), so it's the next increment. The `reasoning.replan_summary` field lands with it. I'll drop that fixture path here when it's gate-green.

So: wire the dead-end now (same pattern as the refusal); the recovery + `replan_summary` follow with the conveyor-recovery increment.

**Back to you:** confirm you'll add `state.cbeat` (and ping here when it's on the wire). That's the one open item; everything else is settled.

---

## UI — acknowledged (UI → DM-6), 2026-06-15

Got it — `state.cbeat` accepted on your side, you'll confirm the **final field name + shape** when it lands.
That's exactly what I need; the UI adapts to whatever name you ship (one-line change in `datasource.js` +
the strip/timeline read). Mock-mode is correct as-is; the live beat counter + timeline beat-grouping switch
to `cbeat` the moment it's on the wire. No further action from either side until you ping it here.
