# Robot Demo — DM-1 Build Chat (next-chat prompt)

Paste the block below to start the DM-1 chat. Supersedes `ROBOT_DEMO_BUILD_NEXT_CHAT_PROMPT.md` (stale; stub-era).

---

We are building the **MindsOS Robot Demo**. Design AND the MindsOS-integration plan are settled — do not re-litigate. This chat executes **DM-1** (deployment + bootstrap) of the plan.

**Read first, in this order:**
1. `HANDOFF.md` + `CLAUDE.md` (root) — canonical entry points + working conventions.
2. `confirmation_docs/ROBOT_DEMO_MINDSOS_PLAN.md` — **the build plan. §0 decisions and §10 pushback resolutions are binding.** This chat = §8 DM-1.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — current workstream state.
4. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` §0a + §5 — the canonical model + the two frozen contracts (only as reference; no scenario work in DM-1).

**DM-1 scope (plan §1):**
- New top-level `demo_backend/` package skeleton (consumer package; imports downward; zero edits to `mindsos_*` — that is a hard rule, plan §9.1).
- `docker-compose.yml` `demo-backend` service + `mindsos[demo]` extras group.
- `bootstrap.py`: admin bootstrap → 4 users (`mgr`,`arm1`,`arm2`,`conv`) → Global KL from Falkor-or-fresh → 4 CapacityLayers (builtin bootstrap) → 4 IntelligenceLayers started (`dream_interval_s=None`) → smoke: one trivial `run_lifecycle` per brain, 4 Episodes consolidate.
- Idempotent re-boot; `reset.py` stub honoring G-11 (run_id-scoped wipe; restart-based reset).
- **Measurements (DM-1 gates):** Mac Mini RAM under full stack; sim-jitter proxy under synthetic 4-brain load (PB-E).
- **Probes to run and record (feed DM-4 decisions):** (a) does `register_capacity(if_exists="upsert")` cleanly shadow the v0 catalog names per-CL (G-1)? (b) what write surface does `CapacityContext.mm_handle` expose for chain artifacts (PB-B)? (c) does `promoted-pipelines` per-NodeType storage_mode admit a Local tier (§4.3 asterisk)?

**Do-nots:** no L2 seeds / L3 demo capacities / bus / sim wiring (DM-2+); no UI; no `mindsos_*` package edits; no git mutations from the sandbox (Mac commits only — standing rule).

**Conventions:** critical-design-reviewer posture; start `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` (decision/pushback record from day one); update `ROBOT_DEMO_STATUS.md` at milestone; new net-new MindsOS features → `Fn` entries in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`; pair-execution pattern (Cowork ↔ Mac ↔ Linux) for anything touching the server.

Confirm you've read the files and restate DM-1's deliverables + gates before writing code.
