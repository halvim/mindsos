# Robot Demo — MindsOS Integration Design Log

**Started:** 2026-06-10 (Cowork, DM-1 chat). Decision/pushback record for the MindsOS-integration build of the robot demo. Companion to `ROBOT_DEMO_MINDSOS_PLAN.md` (the plan) — this log captures what changed *during* build and why. Critical-design-reviewer posture: every entry is flaw → options → chosen.

Pair-execution pattern (Cowork ↔ Mac ↔ Linux) applies to anything touching the server. No git mutations from the sandbox (Mac commits only).

---

## DM-1 — Deployment + bootstrap

### §1. Grounded probe results (read shipped code, did not run yet)

The plan's three DM-1 probes, answered by reading the shipped surfaces:

- **Probe (a) — `register_capacity(if_exists="upsert")` shadow per-CL (G-1).** Signature confirmed: `register_capacity(self, declaration, *, session=None, ref_to_global=None, ref_type=None, extra_properties=None, if_exists: Literal["raise","upsert"]="raise")` (`mindsos_capacity/capacity_layer.py:275`). Surface exists. **Open at build:** does `upsert` re-emit the `PRODUCES`/`CONSUMES` IntergraphEdges, or only swap the implementation callable? Verify at first demo registration (DM-4).

- **Probe (b) — `CapacityContext.mm_handle` write surface for chain artifacts (PB-B).** **Answer: NONE.** `mm_handle` is the `MMHandle` Protocol = 4 *read* methods only (`get_or_instantiate`, `find_instances_by_type`, `produces_of`, `consumes_of`; `mindsos_capacity/context.py:51`). Worse, `ChainArtifactWriter` is constructed *inside* `Orchestrator.run_lifecycle` and handed only to the phase functions — a capacity body never receives it (`mindsos_intelligence/orchestrator.py:132`). **Consequence:** §5.2 option-3 (demo capacities author the chain via `mm_handle`) **cannot be built** without editing `mindsos_intelligence` (forbidden, §9.1) → **deleted from the plan.**
  - **Good news (decides PB-B):** `phase_1.run` dispatches by fixed IRI and emits artifacts *from the dispatched capacity's outputs* — `writer.emit_hint_set(hints)` and `writer.emit_mapping_result(…, mapping["task_pattern_iri"], mapping["mapping_confidence"])` (`mindsos_intelligence/phase_1.py:43-72`). So **same-name override (§5.2 option-1) produces honest chains with zero domain edits, and is the only honest path.** Constraint: demo Phase-1 logic must register under the *literal* IRIs the phases dispatch — `capacity:process:identity`, `capacity:hint:global`, `capacity:decision:derive_goal`, `capacity:decision:map_to_task_pattern` — not the prettier `perception.ingest_order` names in §4.3. §4.3/§5.2 IRI naming to be reconciled in DM-4. (Plan-2 phases `plan_construction`/`execution` dispatch IRIs not yet traced — DM-4.)

- **Probe (c) — `promoted-pipelines` per-NodeType Local tier (§4.3 asterisk).** **Answer: NO.** Per-NodeType `storage_mode` is Global-only at v1 (Phase 43 / ADR-0151); promoted-pipelines NodeTypes ship `INLINE`, no per-user Local option (`mindsos_knowledge/schemas/promoted_pipelines.py`). **The §4.3 asterisk stands** — learned composites go to Local `capacity-state` as a `LearnedComposite` NodeType, name-mirrored only. "Delete this asterisk" branch removed.

### §2. Round-2.5 pushbacks (confirmed by the user 2026-06-10)

Adversarial re-read of §1 (deployment/bootstrap) against shipped code. All accepted.

- **P1 (= PB-B resolution):** `mm_handle` read-only → §5.2 option-3 dead; option-1 (same-name override under literal v0 IRIs) is mandatory and honest. Net-new finding → **Fn candidate** (chain-artifact authorship seam for consumers).
- **P2:** promoted-pipelines no Local tier → §4.3 asterisk stands (Local `capacity-state` `LearnedComposite`).
- **P3:** `if_exists="upsert"` present; edge re-emission to verify at DM-4.
- **P4 (superseded by Round-3 PB-J):** originally "use `bootstrap_kl_from_falkordb` not the pair helper." Round-3 changes the KL story (per-device) — see PB-J. The pair helper (`bootstrap_global_pair_from_falkordb`) is still wrong for the demo (it returns canonical+pending for the pivot-release flow, not Global+Locals).
- **P5:** **Orchestrator wiring is net-new and unspecified in the plan.** `IntelligenceLayer` exposes no `run_lifecycle` and no Orchestrator; `il.mm` exists only after `il.start()`. Consumer must build `Orchestrator(L4Dispatcher(cl, session=session, kl=kl), il.mm)` *after* start and run it via `il.enqueue(lambda: orch.run_lifecycle(task_input, task_id=…))` (runs on a worker thread). **Choice:** a `Brain` struct in `bootstrap.py` holds `(session, kl, cl, il, orch)`; smoke enqueues + `future.result()` to exercise the real worker-pool path the RAM/jitter gate measures.
- **P6:** "idempotent re-boot" needs get-or-create existence guards — `insert_user` raises on duplicate (UNIQUE). **Choice:** query-then-insert for admin + 4 users; pin `server.db` to the named volume so identities survive restart.
- **P7:** DM-1 jitter gate had no pass criterion. **Choice (provisional):** proxy = a busy stepping thread at 50 Hz + 4 ILs looping enqueued trivial lifecycles; **gate = p99 step interval ≤ 2× nominal at 50 Hz**, AND record the full distribution. Real bar lands in DM-3 with the actual MuJoCo loop (synthetic numbers won't transfer).
- **P8 (scope guard):** §1.3 steps 4–6 (bundles, Local seeds, demo L3 installers) are DM-2/DM-3. DM-1 `bootstrap.py` ships labeled no-op stubs for those steps; only admin + 4 users + per-device KL + 4 builtin CLs + 4 ILs + smoke are live.
- **P9:** real `login()`/`insert_user` sessions, not `Session.for_testing` — the whole P-1 rationale is that Local/Global/`writeable` are *real*, and the gate reads `session.capabilities`. Demo-fixed passwords in compose env.

### §3. Round-3 — per-device-instance architecture (user request 2026-06-10)

**Request:** future MindsOS installs per device type (computer/phone/robot), knows "where" it is, and installs device-type-exclusive capacities. Showcase by giving each of the 4 brains (mgr/arm1/arm2/conv) **individual Global/Local L2, L3, L4** — co-resident on the Linux server, sharing resources.

**Scoping clarification (PB-I):** L3 is already per-instance (per-brain CapacityLayer, P-4); L4 is already per-instance (per-brain IntelligenceLayer). **The only real change is L2:** replace the one shared `KnowledgeLayer` (1 Global + 4 Locals) with **4 independent `KnowledgeLayer`s** (each own Global + own Local), one Server process / one FalkorDB. Server stays shared (it is the runtime envelope, *not* on the layer-composition axis per CLAUDE.md) → one `server.db`, real auth/sessions/audit, real `writeable` gate. Cheaper than P-1 feared: single process ⇒ no cross-process Global sync; the bus already carries the only cross-instance traffic (peer transfer).

- **PB-J — shipped load-or-mint is single-Global-by-name.** `bootstrap_kl_from_falkordb` hardcodes `_GLOBAL_METAGRAPH_NAME`; `KnowledgeLayer.bootstrap()` has no name param → 4 persisted Globals collide on `find_by_name`. FalkorDB *can* hold 4 distinctly-named Globals (docstring: "all Metagraphs coexist, keyed by metagraph_id"). Options: (a) per-device named load-or-mint helper in `demo_backend` (mint → set metagraph name → persist; load by name); (b) DM-1 uses 4 fresh **in-memory** Globals (no persist), defer named Falkor round-trip to DM-2; (c) edit `mindsos_*` — violates §9.1. **Chosen: (b) for DM-1, (a) for DM-2.** Keeps the smoke off the naming/idempotency risk; named persistence built+tested in DM-2 with the G-5 episode-flush probe. **Build-time verify:** is `global_metagraph().name` settable without breaking the 6 ensured role-graphs / `find_by_name` idempotency.
- **PB-K — `capacity-gaps` is Global-tier; brains can't write it live (pre-existing defect).** §3.1's "beats 1 & 5 write capacity-gaps (Global) live" fails the `writeable` gate for a normal brain session (`CAN_WRITE_GLOBAL` = admin) in *both* models. **Chosen:** gaps go to each device's **Local** `capacity-state` (§4.1 already does the Local write); Manager aggregates via `comms.report`; drop the Global capacity-gaps write. Dissolves a latent P-5 contradiction.
- **PB-L — beat-4 peer transfer becomes genuinely cross-installation.** arm1's KL Local → arm2's KL Local = two independent installs sharing a learned skill over the bus. Strengthens the thesis; no mechanism change (F1-min already = receiver-writes-own-Local). **Chosen:** adopt; narration → "across installations."
- **PB-M — "knows where it is" = a `demo_backend` DeviceProfile driving Phase-50 bundle selection (net-new → F7).** `device_type` string per instance (real hardware detection is future). Profile → bundle map: `core`→all 4, `arm-suction`→arm1, `arm-jaw`→arm2, `conveyor`→conv, `manager`→mgr. Mechanism = shipped Phase-50 install; selection logic = `demo_backend`. **Chosen:** `device_type` field on a `DeviceInstance` struct + selection map in `demo_backend`; manifest-level device gating filed as **F7** for future MindsOS. DM-1 only plumbs the field; selective install lands DM-2/DM-3.
- **PB-N — RAM gate budgets 4 Globals, not 1.** Minor (demo Globals small). **Chosen:** record the 4-KL footprint in the DM-1 measurement; no threshold change.

**Net effect on the plan:** P-1 revised (per-device 4 KLs); new P-8 (device profile); §1.1 diagram + §1.3 bootstrap updated; capacity-gaps re-homed to Local (PB-K); F7 added. Zero `mindsos_*` edits. Open build-time verifications: PB-J name-settability; P3 upsert edge re-emission; P5 Orchestrator wiring confirmation against Phase-47 tests.

### §4. Round-4 — Docker/build + smoke grounding (2026-06-10)

Read the shipped `Dockerfile` + `docker-compose.yml` + the consolidation path. Findings:

- **PB-O (HIGH) — `mindsos[demo]` extras are inert.** `prod` stage = `pip install --require-hashes -r requirements.txt` then `pip install --no-deps .` → a `pyproject.toml` extras group is never installed. Options: (a) add demo deps to the core lockfile (pollutes everyone with MuJoCo); (b) new hash-pinned `requirements-demo.txt` + `demo` stage `FROM prod`; (c) drop hash-pinning (breaks supply-chain discipline). **Chosen: (b).** Replaces §1.2's extras mechanism.
- **PB-P (MED) — `demo_backend`/`sim`/`web` not COPYed into any image.** The `prod` stage COPYs an explicit package list excluding them. **Chosen:** the new `demo` stage adds `COPY demo_backend` (DM-1) + `COPY sim`/`COPY web` (DM-3); `demo-backend` compose service uses `entrypoint: ["/usr/local/bin/entrypoint.sh"]` + `command: python -m demo_backend.main`. Verify `entrypoint.sh` passes an arbitrary command through the gosu drop. `falkordb` healthcheck (`redis-cli ping`) + `prod` target both confirmed present — the rest of §1.2 stands.
- **PB-Q (MED) — smoke can silently skip consolidation.** `consolidation_enabled(dispatcher)` (`mindsos_intelligence/consolidation.py:28`) returns False (skip, not fail) unless `consolidate:mm` is registered AND a KL is bound; docstring explicitly names "the v0 orchestrator smoke" as a graceful-skip case. Both conditions hold for us (`consolidate` ∈ `FUNCTIONAL_CATEGORIES`, line 139 of `identifiers.py` ✓; we bind `kl` ✓), so consolidation will be *enabled* — but a wiring regression would yield a green lifecycle with 0 Episodes. **Chosen:** smoke asserts `consolidation_enabled(dispatcher) is True` per brain before the run + asserts the Episode after; folds into the P5 Orchestrator-wiring confirmation (Phase-48/49 assert in-memory Episode consolidation).
- **PB-R (LOW) — DM-1 idempotency gate is thin.** Per-device KLs are in-memory at DM-1 (PB-J) → reboot idempotency only exercises `server.db` user get-or-create. **Chosen:** state the scope; full KL load-or-mint idempotency drill at DM-2.

**Still zero `mindsos_*` edits** (the Dockerfile/compose/requirements changes are build-config, not domain code). New build-time verifications: `entrypoint.sh` command pass-through; `requirements-demo.txt` hash-compile (mujoco wheels); `global_metagraph().name` settability (PB-J); `upsert` edge re-emission (P3).

### §5. Round-5 — bootstrap prerequisites (2026-06-10)

Read `mindsos_server/_schema.py` + `_db.py` + `KnowledgeLayer.local_metagraph`.

- **PB-S (HIGH, blocker) — server.db schema init omitted.** §1.3 step 1 created the admin without first creating the auth tables. Entry: `mindsos_server._schema.init_or_migrate(conn)` (`_schema.py:345`; forward-only `CREATE TABLE IF NOT EXISTS` for users/sessions/audit + `schema_version`). **Chosen:** new bootstrap **step 0** — open a conn via the `_db.py` context manager (WAL + `foreign_keys=ON` + `busy_timeout=5000`), call `init_or_migrate`, before any `insert_user`. Idempotent → also satisfies re-boot. Folded into §1.3.
- **PB-T (LOW, resolved) — Local consolidation target.** `KnowledgeLayer.local_metagraph(user_id)` (`knowledge_layer.py:242`) lazily auto-creates the Local with `episodic_memories` + `capacity-state` ensured (per `__init__.py` ADR-0042 PB-9). The smoke's normal-user consolidate has a valid write target with no explicit Local minting. **Chosen:** bootstrap pre-touches each device's Local (`kl.local_metagraph(brain_user_id)`) defensively so wiring problems surface at boot, not mid-smoke.
- **PB-U (resolved → discipline) — sqlite threading.** `_db.py:95` opens short-lived, context-managed, per-call conns (`isolation_level="DEFERRED"`, default `check_same_thread=True`, WAL + `busy_timeout=5000`). No long-lived conn shared across worker threads. **Chosen:** `demo_backend` follows the same per-operation-conn discipline; runtime audit writes on worker threads each open their own conn (WAL handles concurrency). Verify only if a runtime write path is found reusing a bootstrap-thread conn.

**Assessment:** reanalysis is at diminishing returns — PB-S is the last plan-level omission found; the remaining unknowns are build-time verifications (listed across §§3–5), answerable only by running code. Recommend opening the DM-1 build.

---

### §6. DM-1 build (2026-06-10) — code landed, gates pending Mac run

Built `demo_backend/` (consumer package, zero `mindsos_*` edits) + build config + `tests_demo/`. **Sandbox-validated the full per-device core** (Python 3.10 + `tomli`, duck sessions): 4 independent KLs → 4 CLs (builtin catalog) → 4 IntelligenceLayers started → Orchestrator per brain → `il.enqueue(run_lifecycle)` on the worker pool → **4 Episodes consolidate**, `consolidation_enabled` True for all, per-device Local isolation confirmed (mgr-only run leaves the other 3 Locals empty). `tests_demo`: **4 passed, 1 skipped** (real-server test skips on 3.10).

Grounded-at-build confirmations:
- **PB-J** — `global_metagraph().name` IS settable (per-device KL naming works).
- **PB-Q** — `consolidate` ∈ `FUNCTIONAL_CATEGORIES`; the smoke asserts `consolidation_enabled` per brain (no silent skip).
- **P5** — wiring confirmed against `tests/phase_47/_fixtures.py` + `tests/phase_49/integration_c.py`: `Orchestrator(L4Dispatcher(cl, session, kl), il.mm)` built after `il.start()`; run via `il.enqueue`.
- **PB-P** — `entrypoint.sh` execs `gosu mindsos "$@"` → the demo command passes through the privilege drop. Verified.
- **Builtin catalog** = `install_planning_v0 + install_phase1_v0 + install_orchestration_v0 + install_consolidate_capacities + reset_v0_verdicts` (the shipped builtin install fns; NOT `create_global`).

Files (after the Round-6 restructure below): `robot_demo/backend/{__init__,profiles,brain,bootstrap,main,__main__,reset,measure}.py`; `robot_demo/requirements-demo.in`; Dockerfile `demo` stage (`FROM prod`, COPYs `robot_demo/`); `robot_demo/deploy/docker-compose.demo.yml` overlay (reuses root `falkordb`); `robot_demo/tests/{__init__,conftest,test_dm1_bootstrap}.py`.

### §7. Round-6 — repo restructure + docs + deploy (2026-06-10)

User asks: (1) docs for what/why/how; (2) consolidate the demo into one repo folder; (3) a separate folder on the Linux server; (4) Linux testing. Decisions (user-approved): umbrella **`robot_demo/`** with package **`robot_demo.backend`** (renamed from top-level `demo_backend`); **reuse the existing `falkordb`** (overlay merged with the root compose, not a separate instance).

- Moved `demo_backend/`→`robot_demo/backend/`, `tests_demo/`→`robot_demo/tests/`, `requirements-demo.in`→`robot_demo/`. Added `robot_demo/__init__.py`. Test imports → `robot_demo.backend.*`. Re-validated in sandbox: **4 passed / 1 skipped**, all backend modules import, YAML + `bash -n` clean.
- Dockerfile `demo` stage now COPYs `robot_demo/` + runs `python -m robot_demo.backend.main`; the root `docker-compose.yml` demo-backend service was **reverted** — the service lives in `robot_demo/deploy/docker-compose.demo.yml` as an overlay (`docker compose -f docker-compose.yml -f robot_demo/deploy/docker-compose.demo.yml`), reusing root `falkordb`, with demo-scoped data under `./.mindsos-demo/`.
- The Dockerfile `demo` stage **must** stay in the root Dockerfile (build context = repo root to reach `mindsos_*`).
- Docs: `robot_demo/README.md` (what/why/how + topology), `robot_demo/docs/DM1_DEPLOYMENT.md` (architecture + bootstrap walkthrough + run matrix), `robot_demo/deploy/README.md` (server runbook).
- Linux testing: `robot_demo/deploy/run_linux_tests.sh` — preflight → `pip-compile` the hash-pinned lockfile → build `demo` image → **container bootstrap smoke** (real server, 4 brains, 4 Episodes) → idempotent re-boot → in-container RAM+jitter; optional host pytest (`RUN_PYTEST=1`). The container smoke is the authoritative gate (self-contained; no host Python deps).
- **DM-1 is headless** — no browser-linked test yet; the first is DM-4. Flag the user when a live/browser step is reached.

Pending on the Mac/3.12 host is unchanged (pip-compile, the gate run, measurements) — now via `bash robot_demo/deploy/run_linux_tests.sh`.

### §8. Round-7 — Dockerfile decoupling (separate-repo question, 2026-06-10)

User asked whether the demo needs a **separate repo** given the Dockerfile coupling. Decision: **stay in-repo, but the demo owns its Dockerfile.** Reasoning: the demo imports `mindsos_server` *private* internals (`_db.open_db`, `_schema.init_or_migrate`, `users._insert_first_admin`, `_argon2.PRODUCTION_PARAMS`) and co-evolves with freshly-shipped phases — a versioned repo boundary would make those imports brittle and lag HEAD, and a split would need wheel/registry publishing that doesn't exist yet. The actual smell (a demo stage inside the *core* Dockerfile) is removed without a split.

- **Reverted** the `demo` stage from the repo-root `Dockerfile` (now demo-free, with a one-line pointer).
- **Added** `robot_demo/deploy/Dockerfile`: `FROM ${MINDSOS_BASE:-mindsos:phase51-prod}` + demo deps + `robot_demo/`. Build context = repo root (to COPY `robot_demo/`).
- **Overlay** `build:` → `dockerfile: robot_demo/deploy/Dockerfile` + `MINDSOS_BASE` arg (no more `target: demo`).
- **Build order** (run_linux_tests.sh step 2): `docker compose --profile cli build mindsos` (base prod image) → then build `demo-backend`.
- **Revisit a repo split** at demo-v1-stable; the precondition is a **public** mindsos bootstrap API so the demo stops importing server privates. Tracked as a follow-up (no Fn — it's a packaging decision, not a MindsOS feature).

Net: core Dockerfile untouched by the demo; demo image explicitly version-pins its base. Still zero `mindsos_*` edits.

**Pending on the Mac/Linux 3.12 host (pair-execution):**
1. `pip-compile --generate-hashes -o requirements-demo.txt requirements-demo.in` (MuJoCo wheels; the `demo` build needs the `.txt`).
2. Run the real-server gate: `pytest tests_demo/ -m integration` (real `insert_user`/`login` + `init_or_migrate`; asserts 4 Episodes + idempotent re-boot).
3. `python -m demo_backend.measure` → record RAM (4-Global footprint, PB-N) + jitter p99 vs 2× nominal (P7).
4. `DEMO_BOOTSTRAP_ONLY=1 docker compose up --build demo-backend` → DM-1 gate: 4 brains start, 4 Episodes, idempotent re-boot.
5. P3 (`upsert` edge re-emission) stays open → DM-4.

Still **zero `mindsos_*` edits**; commits are Mac-only (standing rule).

---

### §9. Live-run fixes (Linux, 2026-06-11)

First container bootstrap on the Linux gate host surfaced one real defect (caught by the smoke, as designed):

- **PB-V — `login()` enforces one active session per user; bootstrap wasn't idempotent against a persisted `server.db`.** On a re-boot (or any run against an existing `./.mindsos-demo/server-db` volume) `login()` raised `AlreadyLoggedInError` ("use logout or kill_my_own_sessions"). **Fix:** `_login_all` calls the shipped self-recovery valve `kill_my_own_sessions(conn, user_id, password)` before each `login`, then commits. This clears the prior process's stale session and is exactly what makes the P6 idempotent-re-boot gate meaningful (vs. wiping the volume). No `mindsos_*` edit — consumer-side only.

**DM-1 GATE GREEN ON LINUX (2026-06-11).** Mac Mini, real 3.12 prod image, real `mindsos_server` bootstrap: 4 device-instances boot → 4/4 Episodes consolidate → **idempotent re-boot verified** (two consecutive `DEMO_BOOTSTRAP_ONLY=1` runs, both `exit=0`, the second on the existing `server.db`). Measurements: **RAM 38.3 MB** full 4-brain stack (35.5 MB baseline → +2.8 MB; 4 in-memory Globals are negligible, PB-N). **Jitter** (synthetic 50 Hz proxy under 4-brain load): n=396, p50 20.00 ms, **p99 20.08 ms**, max 20.17 ms vs 20.00 nominal — PASS (provisional bar p99 ≤ 40 ms; real bar at DM-3). One live fix landed (PB-V); zero `mindsos_*` edits. **DM-1 done.**

## DM-1 build status

- [x] `demo_backend/` skeleton package (profiles, brain, bootstrap, main, reset, measure)
- [x] `docker-compose.yml` `demo-backend` service + `demo` Dockerfile stage + `requirements-demo.in` (PB-O/PB-P — replaces the inert extras group)
- [x] `bootstrap.py` (schema init → admin → 4 users → login → 4 per-device in-memory KLs → 4 builtin CLs → 4 ILs started → Orchestrator per brain → smoke ×4) — **core sandbox-validated**
- [x] `reset.py` stub (G-11 restart reset; run-scoped wipe body deferred to DM-2)
- [x] `tests_demo/` scenario (4 passed / 1 integration-skip in sandbox)
- [x] RAM + jitter-proxy measurements — **Linux, 2026-06-11: RAM 38.3 MB, jitter p99 20.08 ms PASS**
- [x] real-server gate + docker build/up + `requirements-demo.txt` compile — **Linux, 2026-06-11: green, idempotent re-boot verified (PB-V fix)**
