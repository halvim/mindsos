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
bullet to `covered by` the new test in the same commit — or, when the test is written under the
exact name the ADR cites, replace the bullet with a note that the citation now resolves (the
guard reddens on a listed path that exists).

| Id | ADR | Behaviour with no test | Note | State |
|---|---|---|---|---|
| ATG-1 | ADR-0041 | Knowledge-layer capability constants equal the server's (parity) | The module was never built: ADR-0138 removed KL's capability checks, so there is nothing to compare. ADR-0041 is now Superseded by ADR-0138; the always-skipping KL subtest was deleted. | OUT(ADR-0041 superseded by ADR-0138 - KL consults no capability) |
| ATG-2 | ADR-0114 | `release_update` turns an `EmptyComparisonError` from the audit gate into a FAILED row with manifest forensics | `mindsos_server/release.py` handles it; phase_16 tests only that similarity raises. Written as `tests/phase_24/test_release_update_empty_comparison_propagates.py` (the name ADR-0114 cites); each of its three claims observed RED under a designated mutation. | DONE(4dd08b6) |
