"""Phase 11 — Loader policy + schema migration scanner (ADR-0134).

Test tiers (see ``confirmation_docs/PHASE_11_DESIGN_LOG.md`` §7 file
ledger for design rationale):

* :mod:`tests.phase_11.test_load_report_shape` — Tier 1: LoadReport
  + MetagraphLoadReport dataclass surface.
* :mod:`tests.phase_11.test_loader_policy_unit` — Tier 2: policy
  resolver + per-distinct-type WARN bookkeeping unit tests.
* :mod:`tests.phase_11.test_loader_policy_integration` — Tier 3:
  warn/error/ignore × schema-attached/unattached × env-var.
* :mod:`tests.phase_11.test_loader_backward_compat` — Tier 4:
  existing `load_graph`/`load_metagraph` signatures unchanged.
* :mod:`tests.phase_11.test_migrate_from_unit` — Tier 5: scanner
  per kind × element type, summary + each modes.
* :mod:`tests.phase_11.test_migrate_from_metagraph` — Tier 6:
  per-Metagraph dispatch + name-mismatch policy warning.
* :mod:`tests.phase_11.test_cli_migrate_check` — Tier 7: CLI
  migrate-check verb + mutex flags + exit codes.
* :mod:`tests.phase_11.test_cli_load_unknown_edges` — Tier 8: CLI
  `load --unknown-edges` flag + drop-count surfaces.
* :mod:`tests.phase_11.test_rel_type_validation_regression` —
  Tier 9: 5-10 adversarial ADR-0021 regex regression inputs.
* :mod:`tests.phase_11.test_adr_0134_amendments` — Tier 10:
  ADR file contains §amendment-1 + §amendment-2 sentinel text.
* :mod:`tests.phase_11.test_doctor_phase11` — Tier 11: phase
  string ↔ version ↔ image tag self-consistency.
* :mod:`tests.phase_11.test_phase_map_risks_obsolete` — Tier 12:
  PHASE_MAP §Phase 11 row Risks marked OBSOLETE.
* :mod:`tests.phase_11.test_sentinel_paths_includes_migration` —
  Tier 13: sentinel_paths.py includes Phase 11 modules; excludes
  docs surfaces (PB-16 / feedback_sentinel_paths_runtime_only.md).
* :mod:`tests.phase_11.test_confirm_phase_regex_regression` —
  Tier 14: regex matches both framed + bare pytest summary forms
  (PB-33 / B-10-T6 lock).
"""
