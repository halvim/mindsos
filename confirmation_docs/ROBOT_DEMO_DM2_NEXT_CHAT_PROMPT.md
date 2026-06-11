# Robot Demo — DM-2 next-chat prompt

We are building the MindsOS Robot Demo. Design and the MindsOS-integration plan are settled — do not re-litigate. **DM-1 (deployment + bootstrap) is SHIPPED and verified green on the Linux server.** This chat executes **DM-2 (L2 initial knowledge + device-type skill bundles + per-device Falkor persistence).**

## Read first, in this order — the prompt deliberately does NOT repeat what's in these files
1. `CLAUDE.md` (root) — the 5-layer stack + working conventions.
2. `confirmation_docs/ROBOT_DEMO_MINDSOS_PLAN.md` — the build plan. §0 decisions (esp. P-1 per-device topology, P-5 no live Global writes, P-8 DeviceProfile) and §10/§11 pushback resolutions are **binding**. DM-2 = the §8 "DM-2" row; content specs in §3 (Global seeds), §3.3 (Local seeds), §3.4 (skill-bundle vehicle), §4.0 (DataStates), §7 (gap table G-2…G-11).
3. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` — the decision/pushback record. Read Rounds 2.5–9 and §6–§9. Carried into DM-2 specifically: **PB-J** (per-device named Falkor load-or-mint helper — deferred from DM-1), **PB-K** (`capacity-gaps` recorded in each device's Local, not Global), **P2** (`promoted-pipelines` has no Local storage tier → learned composites live in Local `capacity-state`), **PB-V** (clear stale sessions before login). DM-1 grounded facts (builtin-catalog install fns, lazy `local_metagraph` auto-create, the read-only `mm_handle`) are recorded there — reuse, don't rediscover.
4. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` §0a + §5 — canonical model + the two frozen contracts (Pipeline artifact; body-model / embodiment graph). Reference only; no scenario work in DM-2.
5. `robot_demo/` — the shipped DM-1 code. Read `robot_demo/docs/DM1_DEPLOYMENT.md` (architecture + bootstrap walkthrough), `robot_demo/backend/{bootstrap,brain,profiles}.py`, and `robot_demo/deploy/README.md` (how to build/run/test on the Linux server). DM-2 extends this package — the `# DM-2`/`# DM-3` stub markers in `bootstrap.py` show exactly where.

## DM-2 scope (plan §8 "DM-2" + the carried-forward decisions above)
- **§4.0 DataStates** (realm `robot`) registered via the bundle `allow_new_realm`.
- **Three skill bundles (§3.4)** — `demo-world`, `demo-patterns`, `demo-capacities` — installed Global per device through the real Phase-50 `install_skill` gate, **selected by `DeviceProfile.device_type`** (P-8 device-type-exclusive install, F7): a `core` bundle to all four, type-specific bundles only to their matching device. Selection logic lives in `robot_demo` (`profiles.py` already declares `bundle_names`).
- **Local seeds (§3.3)** per brain via `make_writeable(kl, session)` — the F4-min embodiment subgraph inside `capacity-state`.
- **Per-device Falkor persistence (PB-J)** — replace DM-1's fresh in-memory Globals with the per-device named load-or-mint helper (mint → set the per-device metagraph name → persist; reload via `find_by_name`). This is the DM-2 deliverable explicitly deferred from DM-1; the shipped `bootstrap_kl_from_falkordb` is single-Global-by-name and unusable as-is.
- **G-5 episode→Falkor flush probe** — wire the flush and verify round-trip via the Phase-50 `_value_json` node-value codec (ADR-0182); fall back to in-memory episodes if it resists, and document.

## Gate (plan §8 "DM-2")
Bundles install idempotently; seeds are visible (query the per-device KL); an episode round-trips Falkor (or the fallback is documented); the DM-1 bootstrap smoke stays green (4 device-instances, 4 Episodes, idempotent re-boot). Extend `robot_demo/tests/` and the Linux runner `robot_demo/deploy/run_linux_tests.sh`.

## Do-nots
No L3 demo capacities / body adapter / live motion / sim / bus / UI (DM-3+). **Zero `mindsos_*` edits** (additive registration only — hard rule, plan §9.1). No git mutations from the Cowork sandbox (Mac commits only). Do not edit `HANDOFF.md` or other files that hold other chats' uncommitted parked work.

## Conventions
Critical-design-reviewer posture per the project instructions. Record every decision/pushback in `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` from day one; any net-new MindsOS feature → a new `Fn` in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`; update `ROBOT_DEMO_STATUS.md` at the milestone. Pair-execution (Cowork ↔ Mac ↔ Linux): the sandbox is Python 3.10 — it can validate the L2/L3/L4 core with duck sessions + `tomli`, but NOT `mindsos_server` (needs 3.12); the authoritative gate runs on the Linux server via the deploy overlay. The demo owns its Dockerfile (`FROM mindsos:<phase>-prod`) and reuses the root `falkordb`. DM-1 is headless; the first browser-linked live test is DM-4.

**Before writing code:** reanalyze the DM-2 plan, list your pushbacks with options and your choice, and restate DM-2's deliverables + gates.
