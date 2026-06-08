# Phase 45 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L3 — dream family ratification (Rail D)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 45 (Rail D) ratifies and ships the L3 dream family per ADR-0162 +
Chat B D-B5..B9 / L3-51. Combined design+ship under the Phase 44 option-C
precedent: DREAM_FAMILY_CHAT saturated R0->R3 (4 rounds, parity-clean,
one R3 correction to the sentinel chain-parent), then implemented.

WHAT SHIPPED
- mindsos_capacity/builtins/dream.py (NEW): three directive-emitter
  capacities -- dream.maintenance (execution_policy=replay_recorded),
  dream.exploration (re_execute_capacities), dream.retry
  (re_execute_capacities + replan-injection). DreamExecutionPolicy
  (2-value enum), DreamDirective + ReplanInjectionDirective, 2 DataStates
  (dream.task_ref, dream.directive), 3 factories, idempotent
  install_dream_capacities (DataStates-first, partial-state detection).
- mindsos_capacity/capacity.py: DreamCapacity(_CapacityBase) subclass
  (execution_policy + entry_point fields; to_properties override;
  node_kind REACTIVE), alongside Monitor/Adapter. Top-level __all__
  117 -> 118.
- mindsos_capacity/identifiers.py: CATEGORY_DREAM = "dream". Deliberately
  NOT in FUNCTIONAL_CATEGORIES -- the family installs lazily via
  ensure_category_graph (text.* precedent), so create_global is unchanged.
- ADR-0162 (Accepted, with §Implementation (Phase 45) footer);
  docs/concepts/dream.md + mkdocs nav.
- 9-surface version bump 44 -> 45 (manifest phase+version, pyproject,
  7 __version__, docker-compose phase45 tags) -- first slot to exceed the
  high-water mark, so a real bump (contrast 40/41/42).
- Export-slate sentinel flips: count 117 -> 118 (phase_29/31/33/34),
  version phase44 -> phase45 (phase_30/31/34).
- tests/phase_45/ (5 files): maintenance, exploration, retry,
  signal_provenance, adr_amendment_sentinels.

KEY DECISIONS (consumer discipline)
- Directive-emitter contract (S1): dream bodies have NO v1 L3 consumer
  (the L4 dream loop is Phase 46/47, the L5 hookup Phase 48). Bodies emit
  a DreamDirective; the MM deep-copy + live re-execution + ALS signal
  firing are L4/L5 and OUT OF SCOPE here. Same pattern as iter_monitors /
  bipartite walk / CapacityContext.
- Replan-injection (S4): dream.retry, on a failed episode, emits a
  populated ReplanInjectionDirective (replan_level=taskrun); the L4 loop
  performs the actual replan. Non-failed / missing episode -> None
  (OPTIONAL_RETURN dont-know).
- Pre-provisioned surfaces needed ZERO edits: FAMILY_RULES["dream"]
  (OPTIONAL_RETURN, Phase 42), REALM_DREAM (Phase 40), and the
  family_rule_for category fall-through all already resolve dream caps
  correctly.
- dream_source_episode_iri ships as a directive field (provenance); live
  signal tagging is Phase 48.

GATE
Cumulative (Linux docker, full suite): 3694 passed / 9 skipped / 0 failed
in 31:56. mkdocs non-strict build clean (pre-existing carry-forward
warnings only; ADR-0156/PB-16 scope). Manual smokes: doctor --self-test
green at phase45; dream install + introspect + retry-replan-injection
invoke verified.

OUT OF SCOPE (carried to convergence)
L4 dream-cycle timer + MM deep-copy + live re-execution + ALS wiring
(Phase 46/47/48); hybrid execution policy + cross-level entry-points (v2);
invoke->CapacityContext plumbing for dream bodies (Phase 46 PB-23).
No L0 capability/roster change this phase.

CEREMONY
Tag phase-45-confirmed at the confirm-artifacts commit (the
PHASE_45_CONFIRMED.md-bearing commit), NOT the squash -- release.yml
requires the confirmation doc at the tagged commit (Phase 42 lesson).
Fix the Linux git config identity before the confirm commit.
