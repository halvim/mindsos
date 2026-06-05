"""Phase 40 — L3 X1: family-specific dont-know contracts (ADR-0157) +
DataState realm naming convention (ADR-0158).

Test modules:

* ``test_family_rules_lookup`` — two-level prefix lookup + 5-shape catalog
  + permissive default + malformed-input raise (PB-5).
* ``test_realm_validation`` — strict-by-default realm validation at
  ``register_datastate``; ``allow_new_realm`` opt-in; bare / multi-dot /
  unknown-realm rejection.
* ``test_ds_unhandled_input_defined`` — DS_UNHANDLED_INPUT constant value +
  realm + registerable-via-validator (no bootstrap node at v1, PB-6).
* ``test_adr_amendment_sentinels`` — ADR-0157 + ADR-0158 ratified-text
  presence; chain link from Phase 39.
* ``test_confirm_phase_dag`` — confirm-phase high-water-mark acceptance
  under the rail DAG (PB-2; ``_phase_exceeds_manifest``).
"""
