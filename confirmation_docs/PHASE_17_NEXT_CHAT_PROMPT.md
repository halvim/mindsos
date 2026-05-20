══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 17 (L2 versioning + breadcrumbs)
══════════════════════════════════════════════════════════════════════
Project: MindsOS — folder `halvim_mindsos/` under `/Layered Intelligence/`.
Branch off `main` tip — Phase 16's squash-merge SHA should sit at
`origin/main` HEAD (Phase 15b's `ec94565` immediately under it).
Verify with:
    git fetch origin && git log --oneline origin/main | head -3
If line 1 is not `Phase 16 — L2 admin similarity surface ...`,
STOP and resolve.

ROLE: Critical design reviewer + implementer. Follow project-level
CLAUDE.md skeptical-default + terse + pros/cons + alternatives
behavior. Phase 17 scope per PHASE_MAP §17 is "L2 active-version
queries + map-of-versions per role + PROMOTED breadcrumb in views"
— deps Phase 14 only.
══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order; READ THE FILES — do not guess from
training):
══════════════════════════════════════════════════════════════════════
1. `MEMORY.md` (auto-loaded). Every `feedback_*` entry is a hard rule.
   Pay special attention for Phase 17:
   * `feedback_pre_impl_probe_check_existing_modules.md` — grep for
     versioning surface (`active_version`, `step(..., version=)`,
     `MetagraphView.with_version`, `breadcrumb`) BEFORE agreeing
     scope as net-new. Phase 14 PB-15 deferred `step()`'s `version=`
     kwarg to Phase 17 — so the carry-forward IS net-new, but probe
     the rest of the surface.
   * `feedback_phase_baseline_literal_audit.md` — Phase 17 is the first
     version bump since Phase 16 (`+phase16 → +phase17`).
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_release_tag_after_squash_merge_only.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
2. Memory entries:
   * `project_mindsos_phase_15a_implemented.md` — Phase 15a context.
   * `project_mindsos_phase_15b_shipped.md` — Phase 15b design-only
     reframe (no version bump).
   * `project_mindsos_phase_16_implemented.md` (created at Phase 16
     ship time) — Phase 16's read-only similarity surface; ADR-0144
     §amendment-1 partial-flip mechanism; PHASE_MAP §23/§24 cascade.
3. `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md`:
   * §0 Scope at chat-open — the architectural-contradiction reframe.
   * §1 Round 1 PB-1c — the read-only narrow that defers
     `mindsos_admin/promotion.py` to Phase 24.
   * §3 Cross-chat dependencies — what Phase 17 inherits (nothing
     forward-cited from 16; 17 is independent of the similarity
     surface).
4. `halvim_mindsos/confirmation_docs/PHASE_MAP.md`:
   * §0 (load-bearing read rule), §1 (settled cross-cutting decisions).
   * §Phase 17 row — primary scope.
   * §Phase 15a + §Phase 16 rows (the two prior phases per §0).
   * §Phase 24 row — the Phase 16-deferred promotion entry-point;
     Phase 17 does NOT touch this.
5. ADRs (in `/Layered Intelligence/docs/decisions/adr/`):
   * ADR-0010 (layer isolation).
   * ADR-0017 — schema strictness opt-in (relevant if Phase 17 reads
     schema version metadata).
   * ADR-0042 §amendment-1 + §amendment-2 — first-install sequences
     unchanged at Phase 17.
   * ADR-0044 — memories Local-per-user (relevant if version-routing
     touches Local).
   * ADR-0149 — strict=False L2 default + 2-week tightening rule.
   * ADR-0051 — PROMOTED ref_type breadcrumb (Phase 17 surfaces in
     views).
   * ADR-0138 (Proposed) — KL drops write API.
══════════════════════════════════════════════════════════════════════
PHASE 17 SCOPE — high-level (PHASE_MAP §17 is authoritative)
══════════════════════════════════════════════════════════════════════
Per PHASE_MAP §17: "L2 active-version query; map of versions per role;
PROMOTED breadcrumb in views." Deps: Phase 14 only.

Likely surfaces:
* `KnowledgeLayer.active_version(role) -> str` — version selector.
* `KnowledgeLayer.versions(role) -> list[str]` — map of versions.
* `MetagraphView.step(..., version=str | None)` kwarg — Phase 14
  PB-15 carry-forward.
* PROMOTED breadcrumb visibility in `MetagraphView` reads — surfaced
  via a flag or default-included.
* CLI: `mindsos knowledge versions [--role R]` + `mindsos knowledge
  active-version --role R` (Phase 14 PB-13 carry-forward).
══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope):
══════════════════════════════════════════════════════════════════════
1. **Version representation.** IRI-suffixed roles (e.g.,
   `ontology@dolce-dul-4.1`) vs separate `version` property on
   role-graphs vs metagraph-level version map. Phase 12 IRI builders
   already encode version in the IRI tail — what's the canonical
   source-of-truth at Phase 17?
2. **Active-version selection.** First by import order? Latest by
   semver? Admin-configurable? Implicit per role-graph?
3. **`step(version=)` semantics under version-active routing.** Does
   `version=None` mean "use active" or "use any"? What about cross-
   metagraph step?
4. **Breadcrumb surfacing.** PROMOTED nodes hidden by default in
   views? Surfaced with a tag? Filter via kwarg?
5. **Multi-version coexistence.** Can a Global hold `ontology@4.1`
   AND `ontology@4.2` simultaneously? If yes, version-active routing
   becomes load-bearing. If no, Phase 17 is mostly metadata.
══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE (pointers to memory; do not restate):
══════════════════════════════════════════════════════════════════════
* Branch: `phase-17` off `origin/main` tip.
* `notes-phase-17.md` at repo root; `mindsos confirm-phase
  --init-notes 17` ONLY ONCE.
* Pre-build test image; timeout 1800s.
* Version bump `+phase16 → +phase17` across 5 packages; manifest
  `phase = "17"`; image tags `mindsos:phase17-{prod,test}`.
* No 7-site new-top-level-package checklist (Phase 17 likely extends
  existing `mindsos_knowledge/` package; subpackage additions get
  sentinel entries but no Dockerfile COPY changes).
* Tag `phase-17-confirmed` AFTER squash-merge.
══════════════════════════════════════════════════════════════════════
FIRST RESPONSE IN THE NEW CHAT SHOULD:
══════════════════════════════════════════════════════════════════════
1. Confirm cited files read; report any missing.
2. Verify `git log --oneline origin/main | head -3` shows Phase 16's
   squash-merge SHA at tip.
3. Run the pre-impl probe per
   `feedback_pre_impl_probe_check_existing_modules.md`:
       grep -rnE "active_version|with_version|active-version|breadcrumb" \
           mindsos_knowledge/ mindsos_core/ mindsos_cli/ 2>/dev/null
       grep -nE "def step" mindsos_knowledge/metagraph_view.py 2>/dev/null
   Report findings. If anything already exists beyond the Phase 14
   PB-15 carry-forward, surface as a reframe pushback before agreeing
   scope.
4. Surface 1–3 pre-design pushbacks from the candidates above.
5. Ask the single highest-value missing-constraint question.
DO NOT start writing code in the first response. Design first,
sign-off, then implement. Phase 16's 5-round pushback ledger is the
shape this project favours — don't rush past architectural decisions.
══════════════════════════════════════════════════════════════════════
HANDOFF EXIT CRITERIA:
══════════════════════════════════════════════════════════════════════
Phase 17 squash-merges to main; `phase-17-confirmed` tag pushed AFTER
merge per `feedback_release_tag_after_squash_merge_only.md`;
`release.yml` runs; GitHub Release created. Downstream Phase 18
(Server: user store + auth) opens from
`confirmation_docs/PHASE_18_NEXT_CHAT_PROMPT.md` (Phase 17 writes it).
══════════════════════════════════════════════════════════════════════
