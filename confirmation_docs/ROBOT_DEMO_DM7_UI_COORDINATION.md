# DM-7 — UI coordination: making teach / transfer / cooperate visible

**Branch note.** This is the `demo/robot`-side handoff. The canonical
`ROBOT_DEMO_UI_BACKEND_COORDINATION.md` lives on `robot-demo-animation` and is
not on this branch; fold this in there when the branches reconcile. Named
distinctly on purpose to avoid a merge collision.

**Bottom line.** All three DM-7 beats are **backend-live** and ride the
**existing `state` + `message` frames** (WS-contract §2.2 / §2.4). No new frame
types. What's missing is **UI-side**: command triggers for two commands not in
the contract, plus two small semantic decisions. Source of truth:
`robot_demo/backend/wiring.py` `on_command`.

Frame brain-ids are the contract ids (`mgr`/`a1`/`a2`/`conv`) — backend
device-ids `arm1`/`arm2` are aliased by the frame layer (`BRAIN_ALIAS`).

---

## 1. Commands the UI must send (browser → server)

These extend WS-contract §4. Frame shape unchanged: `{type:"command", name, args}`.

| `name` | args | trigger | notes |
|---|---|---|---|
| `teach` | `{scope:"a1"\|"a2"}` | Teach ▸ Capture | **Contract drift:** backend **ignores** the §4 `{skill, blocks}` payload — it always teaches the canonical *box-workaround* on the named arm (default `a1`). Send `scope`; `skill`/`blocks` are inert. |
| `transfer` | `{scope:"a1"\|"a2"}` (alias `from`) | Teach ▸ Transfer | **New, not in §4.** `scope` = source arm; the peer is auto-resolved to the other arm. |
| `cooperate` | `{item:"box1"}` (alias name `carrier_box`) | Cooperate / carrier-box button | **New, not in §4.** Runs the manager's multi-leaf carrier-box Plan. |

---

## 2. What each beat emits (so the UI knows what to render)

### `teach` — beat 2
- `message`: `user → a{n}` — "taught a new skill (box-workaround)"
- `state`: card `a{n}` → `intent:"Learn box-workaround"`, `decision:"skill acquired — stored locally"`, `chain:3`, `active:true`, `caps:[["box-workaround","learned"]]`; `title:"Skill taught"`, `narr:…`

One card lights, one `learned` badge appears.

### `transfer` — beat 4 (spans TWO cards)
- sender `a{src}`: `message` `a{src} → a{peer}` "sharing a learned skill (box-workaround)" + `state` `intent:"Share skill to peer"`, `decision:"transferring box-workaround → Arm2"`, `chain:4`, `active:true`; `title:"Peer transfer"`.
- receiver `a{peer}` (fires from the bus `share` handler): `message` `a{src} → a{peer}` "shared a learned skill (box-workaround)" + `state` `intent:"Learn box-workaround from peer"`, `decision:"skill received — stored locally"`, `chain:3`, `active:true`, `caps:[["box-workaround","learned"]]`.

**UI must update both the sender and receiver cards** within this beat (the
receiver state arrives a moment after the sender, on the bus thread).

### `cooperate` / `carrier_box` — beat 3
- `state` `mgr`: "Plan cooperation" → "Decompose cooperation" (`decision:"3 steps: load → bridge → receive"`) → "Cooperation complete" (`chain:5`, `active:false`); titles `Carrier-box order` / `Carrier-box cooperation` / `Reported`.
- `message`: `mgr → a1` "load cargo into the carrier", `mgr → conv` "carry the carrier across the gap", `mgr → a2` "receive cargo from the carrier".

**Visibility gap (decision owed, §3):** during cooperation only the **`mgr`
card** gets `state` frames; `a1`/`a2`/`conv` get inter-brain `message` lines but
**no per-card `state`** (no `active` ring, no decision text). On camera the arm
cards stay idle while the messages scroll. If you want the arm/conveyor cards to
animate through load → bridge → receive, backend must emit per-device `state`
frames inside `_carrier_box_cooperate` — easy add, just say so.

The real 3-leaf decompose **is** in the Mode-A export
(`reasoning.pipelines==3` / `milestones==4`) if the UI renders the plan tree
from an `export_state` snapshot.

---

## 3. Decisions owed by the UI chat

1. **Peer-receive badge:** backend emits `"learned"` on the receive path;
   WS-contract §2.2's example uses `"inherited"` for a transferred skill. Pick
   one. If you want to distinguish operator-taught vs peer-received on screen,
   backend will emit `inherited` on receive — confirm and I'll change it.
2. **`learn` flag chip:** the teach/transfer `state` frames don't set
   `flags:["learn"]` today (the flag is defined in §2.2). Want the chip lit
   during these beats? Trivial backend add.
3. **Cooperation per-arm cards:** see §2 — emit per-device `state` during the
   carrier-box handoff, or leave it as mgr-narration + messages?
4. **Beat indexing:** `hello.beats_total` is 7 (the scripted sequence). These
   three are **interactive commands**, not scripted beats. Confirm the UI treats
   them as out-of-band (derives its own beat index from frame order, per §2.2)
   rather than expecting them in the 7-beat count.

---

## 4. Not in scope / no backend dependency

- `promo` flag — irrelevant to DM-7 (Local-only teach/transfer; no Global
  promotion on stage, by design).
- No new frame types, no `resolve`/`graph` producers needed for these beats.

---

## 5. UI answers (2026-06-22)

Answering the four §3 decisions, plus **two new backend asks** that surfaced from
the v0.26 timeline reanalysis.

**A1 (§3.1) — Peer-receive badge → `inherited`, NOT `learned`.** The caps badge
vocabulary already reserves `inherited` for a transferred skill, and the baked
beat-4 scenario uses it (`a2: [["hand-off","inherited"]]`). Emitting `learned` on
the receive path contradicts shipped vocabulary and erases the operator-taught vs
peer-received distinction the teach→transfer story exists to show. **Please emit
`inherited` on the receive path.**

**A2 (§3.2) — `learn` flag chip → YES, set `flags:["learn"]`** on the teach and
transfer `state` frames (both sender and receiver). The UI routes a `learn` flag to
the **Pipeline** section (`FLAG_SECTION`, and the timeline's `tlDecisionSection`),
so without it the learning event is invisible per-section. Trivial backend add per
your note.

**A3 (§3.3) — Cooperation per-arm cards → YES, emit per-device `state`** for
`a1`/`a2`/`conv` through load → bridge → receive inside `_carrier_box_cooperate`.
Arm cards sitting idle while only `mgr` animates, during the one beat whose entire
purpose is showing cooperation, is a demo-killer. Decision/intent text per leg is
enough; doesn't need to be elaborate.

**A4 (§3.4) — Beat indexing → the UI derives its own index from frame order**,
confirmed. BUT see **A5** — we are NOT treating these as throwaway out-of-band
extras on a fixed 7. They are first-class beats in the canonical demo arc.

### New backend asks (from the v0.26 timeline reanalysis)

**A5 — `cbeat` must NOT overshoot on titled interactive frames.** The teach/
transfer/cooperate `state` frames carry `title`, and the shipped `cbeat` contract
(advisory global storyline beat) "advances only on a true *titled* transition" — so
as written they would push `cbeat` past `beats_total` and re-introduce the exact
overshoot `cbeat` was added to kill. **Decision (UI side): these commands are
first-class beats in the canonical happy-path demo sequence.** So: `beats_total`
should reflect the full happy-path count (scripted + the in-order teach/transfer/
cooperate), and `cbeat` advances through them normally. Off-script (user replays
`teach`, skips `cooperate`) the UI will degrade the counter gracefully (running
count, no denominator) — no backend action needed for that. **Action for backend:
include these beats in whatever drives `beats_total`/`cbeat` so the happy-path
counter is correct; don't emit a `cbeat` that exceeds `beats_total` on the happy
path.**

**A6 — Vocabulary must match the baked sanitized labels.** The backend currently
teaches/shares **`box-workaround`** and runs a **`carrier-box`** cooperation; the
baked (user-approved, IP-policy-B sanitized) scenario uses **`hand-off`**,
**`place-in-cell`**, **`stage-on-belt`**. Same beats 2/3/4, different words — a
presenter switching mock→live would see the skill rename mid-demo. The mock is the
reviewed canon. **Please emit the baked sanitized labels** (and run any cooperation
leg/skill strings through IP policy B; canonical map in
`ROBOT_DEMO_IP_SANITIZATION.md`, currently on `robot-demo-animation`). If the
`carrier-box` 3-leaf plan is genuinely a different mechanic than the baked beat-3
belt-hand, flag it and we'll reconcile the scenario rather than just relabel.

> These answers are `demo/robot`-side. Fold into the canonical
> `ROBOT_DEMO_UI_BACKEND_COORDINATION.md` when the branches reconcile.
