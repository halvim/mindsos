---
title: DataState naming convention with realm sub-namespace
status: Accepted
date: 2026-06-01
layer: L3
aliases: [reframe-D48, L3-24, datastate-taxonomy]
---

# ADR-0158: DataState naming convention with realm sub-namespace

**Status:** Accepted

**Date:** 2026-06-01

## Context

Phase 27–33 shipped DataStates use the form `datastate:<name>` (2 colon-segments; no `mindsos:` prefix). Shipped examples follow a `<realm>.<name>` dot-prefix convention without formal ratification:

- `datastate:text.raw`, `datastate:text.tokens`, `datastate:text.sentences` (Phase 31 builtins).
- `datastate:mm.composite_instance` (Phase 33 write capacity).
- `datastate:problem_trace.record` (Phase 30 ProblemTraceRecord).

Chat A R6 (D48) directional intent: catalog NLU, code, marker, and bridge DataStates with naming conventions and reserved realms. Chat B D-B42 references `data_state_type_iri: IRI` field on DataStateInstance — D48 must produce an IRI form D-B42 consumes. ADR-0157 (D46) pre-locks `DS_UNHANDLED_INPUT` to a marker sub-namespace — D48 must accommodate.

The R0 framing for D48 directly cataloging NLU + code + bridge entries was rejected as scope creep — domain-specific catalogs belong to WSD installation chat (NLU), code-skill installation chat (code), and adapter family chat (bridges). ADR-0158 locks naming convention + reserved realm enumeration + marker family v1 entry; concrete realm catalogs ship downstream.

## Decision

**IRI form:** `datastate:<realm>.<name>` — 2 colon-segments with realm as dot-prefix within the name segment. No `mindsos:` prefix. Matches shipped Phase 27–33 form verbatim. Zero retroactive migration of shipped DataStates.

**Reserved v1 realm enumeration (9 realms):**

| Realm | Status at v1 | Owner |
|---|---|---|
| `core` | reserved (empty) | future ADR amendment |
| `marker` | partial (`DS_UNHANDLED_INPUT` via ADR-0157) | standard registration; markers added per-need |
| `bridge` | reserved (form pattern documented, no shipped entry) | adapter family chat |
| `text` | shipped (Phase 31) | already done |
| `mm` | shipped (Phase 33) | already done |
| `problem_trace` | shipped (Phase 30) | already done |
| `nlu` | reserved | WSD installation chat |
| `code` | reserved | code-skill installation chat |
| `dream` | reserved (L3-51) | dream family chat |

Realm-name constants ship in `mindsos_capacity/identifiers.py`:

```python
REALM_CORE = "core"
REALM_MARKER = "marker"
REALM_BRIDGE = "bridge"
REALM_TEXT = "text"
REALM_MM = "mm"
REALM_PROBLEM_TRACE = "problem_trace"
REALM_NLU = "nlu"
REALM_CODE = "code"
REALM_DREAM = "dream"

RESERVED_REALMS: frozenset[str] = frozenset({
    REALM_CORE, REALM_MARKER, REALM_BRIDGE,
    REALM_TEXT, REALM_MM, REALM_PROBLEM_TRACE,
    REALM_NLU, REALM_CODE, REALM_DREAM,
})
```

`mindsos_capacity/family_rules.py` (ADR-0157) imports `REALM_MARKER` and uses it directly; the prior `MARKER_NAMESPACE` alias is dropped.

**Single-dot at v1; multi-dot deferred to v1.5+.** Sub-namespacing within a realm (`nlu.framenet.frame_instances`) requires ADR-0158 amendment. v1 names parse cleanly as `<realm>.<single-segment-name>`.

**Strict-by-default realm validation + admin opt-in.** `CapacityLayer.register_datastate(...)` raises `CapacityRegistrationError` on unrecognized realm; admin extension path is `register_datastate(..., allow_new_realm=True)`. ~10 LOC validator at `capacity_layer.py:199-261`:

```python
def register_datastate(self, datastate, *, session=None, allow_new_realm=False):
    name = datastate.name
    if "." not in name:
        raise CapacityRegistrationError(
            f"DataState name {name!r} missing realm prefix; expected '<realm>.<name>'"
        )
    realm, suffix = name.split(".", 1)
    if "." in suffix:
        raise CapacityRegistrationError(
            f"DataState name {name!r} has multi-dot; v1 allows single-dot only"
        )
    if realm not in RESERVED_REALMS and not allow_new_realm:
        raise CapacityRegistrationError(
            f"Realm {realm!r} not in reserved set {sorted(RESERVED_REALMS)}; "
            f"pass allow_new_realm=True for admin extension"
        )
    if realm not in RESERVED_REALMS and allow_new_realm:
        log.info(f"Admin extension: registering DataState in new realm {realm!r}")
    # existing register logic continues
```

**Marker family v1 entry locked:** `DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"` (ADR-0157 ships this constant via `family_rules.py`). Future markers (`timeout`, `aborted`, etc.) added via standard registration when first consumer surfaces.

**Bridge family form documented in prose only.** No shipped placeholder entry. ADR text documents `datastate:bridge.<purpose>` as the form pattern (purpose freeform; not enforced); adapter family chat registers concrete bridges at authoring time. Illustrative-only example: `datastate:bridge.nl_to_code_search_spec`.

**Cataloging responsibility split (documented in §appendix):**

- `nlu` realm → WSD installation chat (per chat brief inheriting WSD source materials).
- `code` realm → code-skill installation chat (future).
- `bridge` realm → adapter family chat (cross-realm capability author).
- `marker` realm → standard registration path; ADR-0157 ships v1 entry; future markers added per-need.
- `text` / `mm` / `problem_trace` realms → already shipped; no new authoring required at v1.
- `dream` realm → reserved for L3-51 (`dream.*` family) authoring; empty at v1.
- `core` realm → reserved; ADR amendment required to populate.

## Consequences

**Good:**

- Zero retroactive migration of shipped Phase 27–33 DataStates.
- Strict-by-default validation prevents realm typos (foot-gun reduced); admin extension path explicit.
- `data_state_type_iri: IRI` (Chat B D-B42) accepts the realm-tiered form without amendment.
- ADR-0157's marker namespace alignment satisfied via `REALM_MARKER` constant; no IRI placeholder drift.

**Cost:**

- 9 module-level constants added to `identifiers.py` + 1 `RESERVED_REALMS` frozenset.
- `register_datastate` validator adds ~10 LOC + new `allow_new_realm` kwarg.
- Sub-realm namespacing (`nlu.framenet.frame_instances`) deferred to v1.5; if WSD/code-skill installation chat hits the cap, that triggers an ADR-0158 amendment.

## Alternatives considered

1. **4-segment colon form** (`mindsos:datastate:<realm>:<name>`) — rejected: forces retroactive migration of all 5 shipped DataStates + their references in capacity-MM + ProblemTraceRecord + Chat B D-B42 consumers. The realm tier already exists in the shipped form using `.` as separator.

2. **Flat (no realm sub-namespace)** — rejected: realm distinction is structurally meaningful (drives dont-know family rule via ADR-0157 prefix-lookup) + drives admin tooling discoverability.

3. **Ship concrete NLU + code + bridge catalog in ADR-0158** — rejected: domain semantics belong to domain installation chats; pre-locking NLU/code IRIs preempts downstream domain authors.

## Sequencing

Ship phase **X1** — bundled with ADR-0157 (family-specific dont-know contracts). Shared `identifiers.py` realm constants + shared family_rules.py module. Smallest scope; saturates at R4.

## R0 probe set (required before ship R1)

1. Phase 27–33 actually-shipped DataState IRIs — verified flat 2-segment + realm-as-dot-prefix form (confirmed via repo probe 2026-06-01).
2. ADR-0150 §82 alignment naming convention — DWF chat reconciliation pending (HANDOFF §6.3); confirm no conflict with realm-tiered DataState form.
3. Phase 12 role IRI conventions — confirm realm-tiered DataState form is consistent with role IRI patterns (no clash expected; different prefixes: `role:*` vs `datastate:*`).
4. `register_datastate` current validation logic lift cost for realm-tier check.
5. `mindsos_capacity/identifiers.py` existing DS_* constants — count for any retroactive rename (zero expected per probe).
6. WSD `coordinated_change_L3` DataState references — confirm `DS_SENSE_DISTRIBUTIONS` etc. fit `nlu:` realm form.
7. `_DATASTATE_NAME_RE` regex pattern — confirm allows `realm.name` form + whether multi-dot is regex-allowed (PB-D48-8 strict validator catches multi-dot at register-time regardless).
8. Phase 12 + ADR-006 capacity_iri form — confirm no clash with `datastate:` prefix.
9. Shipped test DataState registrations — verify all use `realm.name` form (no bare-name registrations that would break under strict validator).

## Rationale

Per-decision rationale, 4-round saturation history (2 reversals R2 surfaced by probe of actual shipped form, 1 reversal R3, 0 reversals R4), and the IRI-form pick reanalysis at `docs/_workbench/L1_L3_REFRAME_DECISIONS.md` §D48.
