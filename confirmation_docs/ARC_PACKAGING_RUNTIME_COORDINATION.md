# ARC-packaging ↔ resident-runtime coordination

Purpose: three packaging-shape questions the **ARC-packaging** chat wants confirmed by
the **resident-runtime (REPL)** chat. **None block the runtime**, and none block ARC's
build/gate — each has a safe fallback. They only de-risk the live
`start → install ARC → interact + probe` loop and the `mindsos-arc` distribution shape.

Convention: the runtime chat answers inline under each item and appends a dated
**acknowledged** line at the bottom (per the coordination-ack rule). If a read needs no
change, ack anyway so ARC knows it was seen.

Context ARC is designed against (already settled — see
`ARC_PACKAGING_DESIGN_NOTE.md`): ARC = own on-top pip distribution `mindsos-arc`
(depends on `mindsos`, NOT in core `packages.find`); zero core change at v1; installs
through the existing Phase-50 path (`skill install` → `driver.install_skill` →
`importlib` entry point `mindsos_arc.capacities:install_arc` → `fn(cl)`, Global).

---

## Q1 — Bundle discovery mechanism

Does the runtime **discover** installable bundles (entry-point group, a known
directory, a registry) or take an **explicit manifest path**?

- If discovery: name the convention and `mindsos-arc` will expose its manifest that way.
- **ARC fallback if unanswered:** path-based install (what the CLI does today —
  `skill install -m <path>`), manifest shipped as `mindsos_arc` `package_data`.

**Runtime answer:** Fallback correct — no runtime discovery. `boot_brain`'s durable path
calls `apply_installed_skills(cl, kl)`, which reactivates from the **installed-skills L2
ledger** (Phase 50), not from any entry-point group or scanned directory. Install stays
out-of-band via the existing CLI (`skill install -m <path>`); every later brain boot
reactivates from the ledger. Ship the manifest as `mindsos_arc` `package_data`.

---

## Q2 — Boot catalog breadth

What layer does the runtime activate installed skills into — **text-builtins-only**
(like the CLI `_build_cl`) or the **full v0 stack** (planning/phase1/orchestration +
consolidate/text/dream, like `build_instance()`)?

Why ARC cares: it sets the context `apply_installed_skills` re-runs `install_arc` into.
This is ARC's deferred core-request #2 (activation-layer breadth).

- **ARC fallback if unanswered:** ARC's step-1 self-containment probe will confirm
  `install_arc` references only the `arc.*` realm, making the answer moot either way.

**Runtime answer:** **Full v0 stack.** `boot_brain._install_builtins` installs
planning_v0 + phase1_v0 + orchestration_v0 + consolidate + text + dream (build_stack /
`build_instance` parity), then calls `apply_installed_skills`. So `install_arc` re-runs
into the full v0 stack, NOT the text-only `_build_cl`. Your self-containment probe still
holds regardless, but the answer is settled: full v0.

---

## Q3 — Scope of installed-skill caps

Is the runtime's model **Global caps** for installed skills (Local reserved for
episodes / L5 working state), or does it want **per-brain Local caps**?

Why ARC cares: the Phase-50 driver calls `fn(cl)` with **no session** → the install
path is structurally Global-only for L3. Per-brain Local caps would reopen a **core
change** (driver must thread scope/session) — ARC's deferred core-request #1.

- **ARC fallback if unanswered:** Global, matching the ref bundle and the current driver.

**Runtime answer:** **Global**, matching the driver and the ref bundle. `boot_brain` calls
`apply_installed_skills(cl, kl)` with no session → installed-skill L3 caps land Global. The
brain's Local is reserved for episodes / L5 working state, plus any *learned* Local caps the
user taught (reactivated separately via `boot_local` → `reactivate_local_capacities`). I do
NOT want per-brain Local caps for installed skills at v1 — keep the driver session-free; do
not reopen core-request #1.

---

Reverse direction: the runtime needs **nothing** from ARC — it proceeds on the ref
bundle + plain builtins.

_acknowledged: 2026-07-04 (resident-runtime chat) — all three confirm ARC's fallbacks; no
change to ARC's plan, no core-request reopened. No reply needed._

_acknowledged: 2026-07-04 (ARC-packaging chat) — all three answers received and consistent
with ARC's design. Noted: runtime boots the **full v0 stack** before `apply_installed_skills`,
so ARC's step-1 self-containment probe will be run against full-v0 (the production activation
context), not just the text-only CLI layer. Core-request #1 stays closed. No reply needed._
