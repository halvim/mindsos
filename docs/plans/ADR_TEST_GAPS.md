# ADR test gaps — decisions whose cited test was never written

**Owns:** the list of Accepted-ADR behaviours that an ADR cites a test for, where no test in
this repo covers that behaviour. Created 2026-09-15 by doc-fix mechanism #4.

**Where the rows come from.** Each Accepted ADR that cites a test file which does not exist
carries an amendment titled *test citations not in this repo*, giving every dead path exactly
one disposition: `covered by` an existing test, `retired`, or `untested — filed as` a row
below. `tests/architecture/test_adr_test_citations.py` fails if an ADR files a gap id that is
not a row here.

**State** is exactly one of `TODO`, `DONE(<sha>)`, `OUT(<reason>)` (RULES §5).
Closing a row: write the test (or record why not), set the state, and change that ADR's
bullet to `covered by` the new test in the same commit.

| Id | ADR | Behaviour with no test | Note | State |
|---|---|---|---|---|
| ATG-1 | ADR-0041 | Knowledge-layer capability constants equal the server's (parity) | Not a test to write yet: `mindsos_knowledge/capabilities.py` is not in this tree, so the parity subtest in `tests/phase_18/test_capabilities_parity.py` skips. The ADR describes a module that does not exist — decide whether the decision or the tree is wrong first. | TODO |
| ATG-2 | ADR-0114 | `release_update` turns an `EmptyComparisonError` from the audit gate into a FAILED row with manifest forensics | `mindsos_server/release.py` handles it; phase_16 tests only that similarity raises. | TODO |
