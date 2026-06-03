"""Phase 39 — L2 ``memories`` → ``episodic_memories`` atomic rename.

Per ADR-0044 §amendment-3 + ADR-0150 §amendment-4 + ADR-0146
§amendment-3 + L2_CHAT_DECISIONS D-L2-16/D-L2-17/D-L2-25.

This package ships 7 test modules per Phase 39 design log §2:

* ``test_rename_atomic`` — grep-zero retired-name surface assertions.
* ``test_alignment_canonical`` — ADR-0154 + D-L2-1 ``:`` separator.
* ``test_episode_memory_iri_builders`` — 2 new builders + charset.
* ``test_iri_builders_registry_shape`` — tuple-key + 3 entries.
* ``test_schema_shape`` — Episode + Memory NodeTypes only.
* ``test_check_rename_state_script`` — detector tool contract.
* ``test_adr_amendment_sentinels`` — ADR-0044/0146/0150 amendment
  presence; sentinel chain root for the post-housekeeping era.
"""
