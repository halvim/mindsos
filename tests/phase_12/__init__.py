"""Phase 12 — L2 Identifiers + role IRIs + REF_TYPES.

Test surface designed per PHASE_12_DESIGN_LOG.md §PB-15 (revised by
PB-20 builder count + PB-22 roles verb add).

Tiers:

* `test_builders_happy` — 14 builder happy-path + alignment_role +
  user_id charset enforcement + capacity_snapshot embedded-colon.
* `test_parser` — parse_iri edge cases + 14 builder round-trips +
  is_version_qualified_iri matrix + adversarial regex.
* `test_ref_types_and_roles` — REF_TYPES self-consistency + ref-key
  helpers + role constants + ADR sentinels.
* `test_knowledge_cli` — `mindsos knowledge iri build|parse|validate`
  + `ref-types --list` + `roles --list`.
* `test_doctor_phase12` — 4-pkg version-string parity.
* `test_image_completeness_phase12` — sentinel-paths includes the 3
  new mindsos_knowledge modules.
* `test_import_isolation` — mindsos_knowledge does NOT import
  mindsos_cli / mindsos_server (PB-18 lock).
"""
