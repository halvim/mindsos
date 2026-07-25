# Rename Execution Plan: top-level "task" -> "Request"

Status: DECISIONS FINAL (2026-07-25). READY TO EXECUTE at a quiet point, from a
DEDICATED rename chat/branch — NOT the arc1+arc3 core-rules chat, and NOT while
in-flight branches are unmerged.

## Decision recap (user-approved)
- Current top-level "task" concept -> **Request** everywhere. NO reference to
  "task" may denote a Request, at ANY level — code symbols AND wire/IRI
  vocabulary.
- "task" is reserved for the future recursive Task unit (any pipeline node); it
  has ZERO current code footprint, so this rename is a uniform task->request
  purge, and the Task concept is a later ADDITION.
- `task_pattern` -> `request_pattern` (and role `task-patterns` ->
  `request-patterns`): APPROVED.

## Two risk classes, sequenced as two PRs

### R1 — Python symbols (safe, core, mechanical)
Rename code identifiers; no emitted/persisted value changes:
- `task_id`->`request_id`, `task_run`/`TaskRun`->`request_run`/`RequestRun`,
  `task_input`/`task_input_ref`->`request_input`/`request_input_ref`
- `ROLE_TASK_PATTERNS` -> `ROLE_REQUEST_PATTERNS` (symbol name only; value is R2)
- attrs/params/locals denoting the top-level unit
Guardrail: rename by symbol, not blind text. Leave `request_cancel` (unrelated).
Gate-greenable on its own.

### R2 — Wire / IRI / ontology vocabulary (RISKY; changes identifiers)
Rename the string VALUES. Each becomes part of emitted or persisted identifiers,
so this class changes stored data and breaks exact-IRI tests:
- knowledge role value `"task-patterns"` -> `"request-patterns"` — a
  bootstrapped, dual-scope, PERSISTED role. Forms pattern IRIs
  (`task-patterns-<v>:pattern:<id>`), has a schema builder, a prefix parser, a
  bootstrap ordering dependency, and Episodes cite its IRIs. Renaming ORPHANS
  any persisted patterns (Global bootstrap + arc Local corpus).
- `"taskinput:"` ref prefix -> `"requestinput:"`
- task-id VALUES `f"task-{seq}"` -> `f"request-{seq}"` (land inside every
  instance IRI `#<id>.<run>.<seq>`)
- `raw_task` datastate type -> `raw_request`  **(see brain coordination)**
- ~27 test files hard-code these literals -> update fixtures in lockstep.

### BLOCKER before R2 — migration decision (owed)
Persisted stores (Local task-patterns corpus, Episodes, capacity graphs) carry
old-vocabulary IRIs. Choose:
- **Clean break** — wipe Local stores + re-bootstrap. Recommended (pre-production;
  no data to preserve). Cheap.
- **Migration pass** — rewrite persisted corpora/Episode IRIs. Only if real data
  must survive.

### Brain coordination (R2 cannot be core-only)
`raw_task` appears as `datastate:arc.raw_task` — it is ARC (brain)-owned, not
core. Per chat rules, brains change from their own chats. So `raw_task ->
raw_request` is flipped by arc/demos IN LOCKSTEP with the core R2 PR; the
core rename PR alone cannot complete R2.

## Execution recipe (run fresh at execution time; do not pre-freeze a file list)
1. Confirm no in-flight branches unmerged; start from green `main`.
2. Branch `chore/rename-task-to-request`.
3. R1 symbol renames, package-by-package (intelligence -> capacity -> knowledge
   -> core -> projects), gate after each package. Land R1 PR.
4. Apply the migration decision. R2 vocabulary + schema keys + prefix parsers +
   bootstrap + 27 test fixtures; coordinate arc/demos `raw_task` flip. Land R2 PR.
5. Full gate green.

## Verification = definition of done
- Gate fully green after each PR.
- `grep -ri "task"` in core shows no remaining reference that means a Request
  (only the future Task-unit vocabulary, once added).
- R1: no emitted/persisted identifier changed. R2: identifiers changed
  deliberately + stores migrated/reset + arc in lockstep.

## Timing / ownership
- ~48 code files + ~106 docs; a bad parallel neighbor. Land at a quiet point,
  after current pushes merge, as its own dedicated chat/branch with clean history
  and tight build -> Mac-commit -> Linux-gate loops.
