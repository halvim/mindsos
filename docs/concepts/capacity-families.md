# Capacity families and dont-know contracts

L3 capacities are grouped into **families** by their IRI prefix. A
capacity IRI has the form `capacity:<category>:<name>`, where `name`
follows the `<family>.<subname>` convention for method libraries (e.g.
`capacity:agglomeration:combination.bayesian`). The family determines
how a capacity signals "I cannot handle this input" — its **dont-know
contract**.

Phase 40 (X1) ships two settled decisions: family-specific dont-know
contracts (ADR-0157) and the DataState realm naming convention
(ADR-0158).

## Dont-know contracts are family-specific

There is no universal dont-know method on every capacity. A
`scoring.attention_score → int` capacity and a `validate.xref →
ValidationResult` capacity express "dont-know" in type-natural but
different ways. ADR-0157 catalogs five shapes:

| Shape | Meaning |
|---|---|
| `DATASTATE_MARKER` | DataState-producing families return the `DS_UNHANDLED_INPUT` sentinel. |
| `OPTIONAL_RETURN` | Families returning `Optional[T]` use `None`. |
| `VERDICT` | Families returning verdict objects carry an explicit dont-know channel (e.g. `ReplanVerdict.decision="abort"`). |
| `VALIDATION_RESULT` | `validate.*` returns `ValidationResult(valid=False, reasons=[...])`. |
| `NO_DONT_KNOW` | The function is total over its domain; dont-know is impossible. `predicate.*` default. |

The mapping lives in `mindsos_capacity/family_rules.py` as the
`FAMILY_RULES` table, resolved by `family_rule_for(capacity_iri)`.

### Two-level lookup

`family_rule_for` resolves a rule by trying the **name prefix** first,
then the **category**, then a permissive `DATASTATE_MARKER` default:

1. Name prefix — handles method libraries:
   `capacity:agglomeration:combination.bayesian` → `combination` →
   `OPTIONAL_RETURN`.
2. Category — handles top-level families:
   `capacity:scoring:attention_score` → `scoring` → `OPTIONAL_RETURN`.
3. Default — well-formed but unkeyed categories resolve to
   `DATASTATE_MARKER` with an info log. A malformed IRI raises
   `ValueError`.

The rule is implicit from the prefix; there is no per-capacity
registration field.

## DataState realm naming

DataState IRIs use the form `datastate:<realm>.<name>` — two
colon-segments with the realm as a dot-prefix inside the name segment.
This matches the shipped Phase 27–33 form verbatim, so no DataState was
migrated.

Nine realms are reserved at v1:

| Realm | Status |
|---|---|
| `core` | reserved (empty) |
| `marker` | partial — `DS_UNHANDLED_INPUT` ships here |
| `bridge` | reserved (adapter family chat) |
| `text` | shipped (Phase 31) |
| `mm` | shipped (Phase 33) |
| `problem_trace` | shipped (Phase 30) |
| `nlu` | reserved (WSD installation) |
| `code` | reserved (code-skill installation) |
| `dream` | reserved (dream family) |

`CapacityLayer.register_datastate` is **strict by default**: it rejects
a name without a realm prefix, a multi-dot name (single-dot only at v1),
and an unrecognized realm. Admin extensions pass `allow_new_realm=True`
to register into a new realm.

## The unhandled-input marker

`DS_UNHANDLED_INPUT = "datastate:marker.unhandled_input"` is the marker
realm's v1 entry, exported from `family_rules.py`. DataState-producing
capacities return it instead of emitting junk on uninterpretable input;
the L4 substrate (Phase 46+) treats it as the dont-know signal for the
`DATASTATE_MARKER` family.

## References

- ADR-0157 — L3 capacity dont-know contracts are family-specific.
- ADR-0158 — DataState naming convention with realm sub-namespace.
