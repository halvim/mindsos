══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 25 DESIGN (Phase 24 just shipped on phase-24
branch; awaiting tag + cumulative-tests verify on Linux Docker; design-
chat does NOT need to wait — Phase 24 substrate is locked at the
implementation chat's commits)
══════════════════════════════════════════════════════════════════════
Phase 25 absorbs the substantive deferrals that Phase 24's narrow
admin-direct-ATOM scope pushed forward. Read this prompt + the
required reading list, run the pre-impl probe, and start the design
discussion. Aim for ~25-40 picks across 5 rounds (Phase 22's 27 +
Phase 24's 28 original bracket the typical density; the deferral
absorption load is modest).
Project: MindsOS — folder `halvim_mindsos/` under `/Layered Intelligence/`.
Branch off `origin/main` tip (the Phase 24 squash, TBD SHA, on top of
`c78146c` Phase 23 retirement on top of `c25a1bc` Phase 22). Tag
`phase-24-confirmed` resolves to the most recent code phase.
══════════════════════════════════════════════════════════════════════
PHASE 25 SCOPE — ENUMERATED DEFERRALS
══════════════════════════════════════════════════════════════════════
**1. Source-user-Local promotion path** (admin-on-behalf-of-user).
ADR-0118 §am1 deferred this to Phase 25 alongside cross-user read
substrate per ADR-0008 §am1. Phase 24's `propose_for_promotion`
raises `NotImplementedError` when `PromotionItem.source_user_id is not
None`. Phase 25 ships:
   * The Phase 24 propose dispatch branch (replaces the `NotImplemented`
     raise).
   * Source user's Local node(s) **frozen** (uneditable; still
     readable by source user). `EVT_DRAFT_FROZEN` audit event fires.
   * On admin reject: source draft **unfrozen** + `EVT_DRAFT_UNFROZEN`
     audit row.
   * `frozen_user_local_node_id` column in `pending_mutations` (ships
     at v4 NULL at Phase 24; populated at v1 source-user path here).
**2. Lazy per-user migration** (ADR-0118 §"Decision" §3 + ADR-0120
contract). Phase 24 ships the ``releases.manifest_json.rewrite_map``
shape (empty `{}` at admin-direct ATOM). Phase 25 populates +
consumes it.
   * `MindsOSServer.start_session(user_id)` (NEW class) walks
     `last_synced_release_id < current_release_id` and applies the
     rewrite map per release per ADR-0120's `apply_rewrite_map`
     contract.
   * `mindsos_knowledge/migration.py::apply_rewrite_map` ships — KL's
     handler implementation. Idempotent per ADR-0120 §1 contract.
   * `EVT_MIGRATION_APPLIED` + `EVT_MIGRATION_FAILED` audit constants
     ship (deferred 2 of 4 EVT_* from Phase 24).
   * ADR-0120 Status flips Proposed → Accepted (KL is first
     implementation per ADR-0120 §3 table).
**3. `MindsOSServer` orchestrator class** (Phase 19 PB-2 + Phase 22
PB-1 deferral + Phase 24 design log §3 forward-dep). NEW Phase 25
module wiring login → session_from_token → cross-user read +
migration.
**4. `LocalPersister` + `LocalPersisterProtocol`** (Phase 19 PB-2
deferral + ADR-0011 §am1). NEW Phase 25 module — per-user Local
metagraph persistence to FalkorDB. NOTE: Phase 24's Z21(b) defers
FalkorDB persistence for Global to Phase 26; Phase 25 likely also
defers Local FalkorDB persistence to Phase 26 — OR Phase 25 wires
both. **Design question for Phase 25 design chat.**
**5. Cross-user read substrate** (ADR-0008 §am1 + ADR-0006 §am1's
`UserMutexRegistry` first consumer). NEW `read_other_local()`
context manager — refcounted transient install per ADR-0008.
`CAN_READ_OTHER_LOCALS` capability declared at Phase 18 gets its
first consumer here.
**6. `EVT_DRAFT_FROZEN` + `EVT_DRAFT_UNFROZEN` audit constants** (2
of 4 deferred EVT_* from Phase 24 design log PB-11(a)).
**7. `CAN_READ_PENDING_GLOBAL` capability** if Phase 25 ships a
pending-Global direct-read consumer (e.g., admin pending-inspection
verb). Phase 24 design log PB-23(a) deferred to "first direct-read
consumer phase" — could be Phase 25 or v2.
══════════════════════════════════════════════════════════════════════
INHERITED SUBSTRATE FROM PHASE 24 (load-bearing context)
══════════════════════════════════════════════════════════════════════
* **ADR-0114 §3 SHIPPED `manifest_json.rewrite_map`** is the lazy-
  migration consumer contract. Phase 25 populates it (source_local_
  node_id → canonical_global_node_id mapping); Phase 24 ships empty
  `{}` at admin-direct.
* **ADR-0120 contract is locked** (Proposed at Phase 24; consumer
  ships at Phase 25). `apply_rewrite_map(local_metagraph, rewrite_
  map, release_id, audit_writer) -> RewriteResult` per layer.
* **`UserMutexRegistry`** declared at Phase 24's `mindsos_server/
  locks.py` (no consumer at Phase 24); first consumer is Phase 25's
  `read_other_local()` per ADR-0006 §am1.
* **`pending_mutations.frozen_user_local_node_id`** column ships at
  Phase 24 v4 schema NULL-only; populated by Phase 25's source-user
  propose path.
* **`pending_mutations.source_user_id`** column ships at Phase 24 v4
  schema NULL-only; populated by Phase 25's source-user propose path.
* **Phase 24's Z21(b) FalkorDB persistence deferral** — if Phase 25
  is in-memory-only too, Local Metagraphs would be lost on CLI
  restart. Either Phase 25 ships FalkorDB Local persistence (and
  potentially Global too — collapse Phase 26 forward), OR Phase 25
  also defers + relies on payload_json equivalent for Local. **Open
  design question.**
══════════════════════════════════════════════════════════════════════
REQUIRED READING
══════════════════════════════════════════════════════════════════════
1. `MEMORY.md` — pay attention to the new `project_mindsos_phase_24_
   implemented` entry that summarizes the 44-pick ledger.
2. `halvim_mindsos/confirmation_docs/PHASE_24_DESIGN_LOG.md` §1 Round 0
   PB-Z1..Z22 + §3 forward dependencies + §4 ADR delta + §6 out-of-
   scope (these are the Phase 25 inputs).
3. ADRs at parent root:
   * ADR-0008 + §am1 (cross-user reads + Phase 25 first consumer).
   * ADR-0011 + §am1 (LocalPersister + Phase 25 first consumer).
   * ADR-0042 + §am1 + §am2 (KL install/extract hooks + first-install
     sequences).
   * ADR-0118 + §am1 + §am2 (Phase 24 model + Z21 Phase 26 deferral
     clause).
   * ADR-0120 (cross-layer rewrite handler contract; first consumer
     ships at Phase 25).
   * ADR-0125 + §Proposed (lazy local hydration with LRU eviction;
     Phase 25 may flip Accepted if it wires hydration).
   * ADR-0040 (SessionProtocol — KL-side seam first consumer at
     Phase 25).
   * ADR-0006 + §am1 (per-user mutex first consumer).
4. PIVOT §7.3 (lazy migration mechanism) + §7.4 (move semantics) +
   §7.6 (full audit event slate).
══════════════════════════════════════════════════════════════════════
KEY DESIGN QUESTIONS FOR PHASE 25 DESIGN CHAT
══════════════════════════════════════════════════════════════════════
**A. FalkorDB Local persistence — ship at Phase 25 or defer with
Global to Phase 26?** If Phase 25 ships SourceUser-source path +
lazy migration but Local Metagraphs are in-memory only, server
restart loses user Locals (much worse than losing Global because
Local content is user-authored). Two-store-write pattern from Phase
24 (SQLite + in-memory) needs an equivalent for Local: either
FalkorDB wiring at Phase 25, OR a per-user SQLite ledger
(`local_drafts` table?) that rehydrates Local on session start.
**B. `MindsOSServer` class shape** — minimal (`start_session` +
`installed_locals` dict) OR full (lazy hydration + LRU eviction per
ADR-0125)? Phase 24 doesn't have a long-lived server process; Phase
25's first-consumer status for several substrates may force the
question. ADR-0125 is Proposed; Phase 25 may flip it.
**C. Cross-user read mutex acquisition contract** — `read_other_
local(target_user)` context manager refcount semantics per ADR-0008
§"Decision" `InstallRecord` shape; `transient=True` flag prevents
flush on teardown.
**D. Source-user-Local propose two-store contract** — Phase 25's
extended propose writes to (i) SQLite pending_mutations + (ii)
in-memory pending_global Metagraph + (iii) **freezes** the source
user's Local node (sets `_frozen=True` property?). The freeze
mechanism is unstated; Phase 25 design chat locks it.
**E. ADR-0007 was already Superseded at Phase 24 ship**. ADR-0024
(Capacity-layer L3 alias) supersession promise stays open per ADR-
0118 §"Coordinated changes" §"ADR-0024 unchanged" — L3 capacity-
promote is post-Phase-25 anyway, so no action at Phase 25 on this.
**F. ADR-0144 §am2 EmptyComparisonError contract** — Phase 24's
release-ship audit gate propagates per ADR-0144 §am2 default. Phase
25's source-user propose path may need its own degenerate-pair
contract since freezing-then-promoting touches more refs.
══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════
Follow the strict picks-per-pushback format per `feedback_pushback_
format_with_picks.md`. Every pushback ends with "Pick:" line; final
"Picks summary" table at end of each round. No filler. Skeptical
posture; surface real load-bearing gaps. Phase 24's Round 0
demonstrated that pre-impl re-analysis can surface load-bearing
substrate issues even after a 28-pick design lock — Phase 25 design
chat should similarly allow space for a Round 0 re-analysis pass
after the main rounds lock.
ADR Status pre-flip convention per Phase 24's Z6(c) lock: ADR Status
flips happen at design pass (in the YAML frontmatter), not at impl
PR. If scope drifts mid-impl, walk back via §amN amendment.
══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════
1. Confirm required-reading files read (terse list).
2. Run pre-impl probe to confirm Phase 24 substrate is intact:
   ```
   cd halvim_mindsos
   git log --oneline -5
   grep -n "CAN_PROPOSE_MUTATION\|CAN_APPROVE_RELEASE" mindsos_server/capabilities.py
   ls mindsos_admin/promotion.py mindsos_admin/audit_gate.py
   ls mindsos_server/release.py mindsos_server/locks.py
   grep -n "_SCHEMA_VERSION" mindsos_server/_schema.py
   ```
3. Surface 3-5 highest-value design questions for the Phase 25
   design chat (the 6 above + any new ones from probe).
4. Ask ONE missing-constraint question to start Round 1.
══════════════════════════════════════════════════════════════════════
