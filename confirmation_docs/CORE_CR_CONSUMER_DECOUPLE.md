# CORE CR — core stops naming its external consumer

**Branch:** `feat/core-dr-decouple` off `origin/main` `85e123c`. **Owner rulings:** 2026-09-27.
**Guard:** `tests/architecture/test_core_names_no_consumer.py`.

## Why

The external demo is built as a USER of MindsOS: its own repository, core installed by tag
(RULES §1). Core named it anyway — in comments of eleven `mindsos_*` modules, a test package
named after it, the ADRs, RULES/HANDOFF/BRANCHES/CLAUDE.md, five confirmation docs and the live
queue in `STATE.json`. The dependency ran backwards in prose. This CR removes every mention and
adds the guard that keeps it out.

## What changed

1. **Code — comments and docstrings only.** Every mention in `mindsos_*` was prose; each now states
   the general need ("a printed run record"). No behaviour change.
2. **Tests.** The package moved whole to `tests/run_records/` (its shared fixtures and driver are
   imported by most of its files, so a per-capacity split would duplicate them).
   `_dr_driver` → `_run_driver`, `_dr_fixtures` → `_fixtures`, `DecisionRecordRun` → `RecordRun`,
   `decision_record_plan` → `record_plan`, `run_decision_record` → `run_record`, one test renamed
   (`test_every_record_capacity_declares_one`). The tests themselves are unchanged.
3. **Docs, history included** (owner ruling D1-b): ADRs 0150, 0201 am-4/am-5, 0207, 0208, 0210 and
   the ADR index, the confirmation records, RULES, HANDOFF, BRANCHES, CLAUDE.md, `projects/README.md`,
   the LLM plan and the LLM seam manual. RULES passages are restated for "an external consumer"
   (D3-a).
4. **Five consumer documents left core** (D2-a) for the consumer's own repository, and
   `tools/claim_inventory.py` no longer lists two of them as live plans.
5. **`STATE.json`** (D4-c): the `demos` entry for the consumer and the 20 queue items about the
   consumer's own code moved to the consumer's repository. The 12 items that are core work but
   carried the consumer's prefix were renamed (prefix dropped) and reworded; 19 core items were
   reworded. `recent[]` is a log and is left as written.

## Not affected

The consumer installs core from a tag; `main` moving does not change what it runs.

## Gate

Full core gate on the Linux box; the collect-only test-id diff shows only the moved package and the
one renamed test; the new guard's mutation (re-adding the name in one core comment) is observed RED.
