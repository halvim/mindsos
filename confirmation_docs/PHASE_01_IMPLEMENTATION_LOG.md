# Phase 01 — Implementation Log

> Curated record of the Phase 01 design + implementation session
> (2026-05-03 chat). Captures locked decisions, bug ledger, files
> touched, tests added, residual concerns, and the tester checklist.
> Read in conjunction with `PHASE_MAP.md` Phase 01 row + the eventual
> `PHASE_01_CONFIRMED.md`. This file is implementation history; the
> CONFIRMED doc is the CI-recognised artifact.

---

## 1. Charter

Phase 01 = **tooling infrastructure**. Per-phase row scope (refined
in this session, locked in `PHASE_MAP.md` §4):

- GitHub Actions CI on push to `phase-*` branches: build + cumulative
  `pytest tests/` + `mkdocs build`.
- GitHub Actions Release on tag `phase-NN-confirmed`: build + test +
  tarball + GitHub Release with assets + retention prune of older
  tarballs.
- `mindsos confirm-phase` CLI wrapper to assemble
  `PHASE_NN_CONFIRMED.md` from a tester-filled notes file.
- mkdocs build verification.
- `doctor --self-test` extended with `[ci.required_workflows]` parity
  check and compose image-tag drift detection.

Net-new code; no domain-layer (L0–L3) changes.

---

## 2. Locked decisions (final, post-iteration)

| # | Decision | Where it lives |
|---|---|---|
| 2.1 | `confirm-phase` runs **on the host**, shells out to `docker compose run --build --rm -T mindsos-test pytest tests/`. | `mindsos_cli/commands/confirm_phase.py:_run_tests` |
| 2.2 | Pytest summary parsed via single regex table; `error`/`errors` matched once via `errors?\b`. | `_SUMMARY_KW_PATTERNS` |
| 2.3 | Notes parser only recognises `phase_title` + `tester_notes` as section delimiters; inner H2 inside `tester_notes` stays in body. | `_NOTES_FIELD_NAMES`, `_parse_notes` |
| 2.4 | `--phase NN` must match `[mindsos] phase` in manifest; mismatch errors. | `confirm_phase` body |
| 2.5 | `--skip-tests` flag for emergency hand-write path. | `confirm_phase` body |
| 2.6 | Notes file: tester fills only `phase_title` + `tester_notes`; everything else auto-derived. | `_template_notes.md` |
| 2.7 | CI workflow trigger: `push` on `refs/heads/phase-*`. | `.github/workflows/phase-ci.yml` |
| 2.8 | CI runs **cumulative** `pytest tests/` (every shipped phase's tests). | phase-ci.yml |
| 2.9 | mkdocs installed ad-hoc in CI (`pip install mkdocs==<pin>`); NOT in test image. | phase-ci.yml + manifest `[ci] mkdocs_version` |
| 2.10 | Release trigger: tags matching `phase-*-confirmed` (incl. `phase-NN-vM-confirmed`). | release.yml `on:` |
| 2.11 | Release body = verbatim `confirmation_docs/PHASE_NN_CONFIRMED.md`. v2 supersessions read `PHASE_NN_vM_CONFIRMED.md` (sibling file; original kept untouched). | release.yml `confirmdoc` step |
| 2.12 | Tarball name = `mindsos-phaseNN.tar.gz` for v1; `mindsos-phaseNN-vM.tar.gz` for vM>=2. | release.yml `tarball` step |
| 2.13 | Retention: highest vM per slot is install target; older vMs evict immediately; 5 highest slots' install targets keep tarball, rest evict. | `mindsos_cli/_retention.py` |
| 2.14 | Retention prune calls Python heredoc that imports the unit-tested `_retention.select_retention`; bash exports `ALL_TAGS` so the child Python sees it via `os.environ`. | release.yml retention step |
| 2.15 | `gh release upload --clobber` swaps tarball asset content for evicted releases; never deletes a Release. | release.yml |
| 2.16 | GitHub permissions: `contents: write` declared at **job level** in `release.yml`; `phase-ci.yml` runs at default `contents: read`. | both workflows |
| 2.17 | Manifest extension: `[ci] required_workflows` + `mkdocs_version`. `doctor --self-test` reads + asserts both shape + presence. | `mindsos_cli/manifest.toml` + `doctor.py` |
| 2.18 | Workflow shape check uses regex tolerant to quoted YAML keys (`on:`, `'on':`, `"on":`, `on  :`). | `_yaml_top_keys` in doctor.py |
| 2.19 | Compose image-tag drift check: every `^\s*image:\s*mindsos:phaseNN-<stage>` literal in `docker-compose.yml` must match `[mindsos] phase`. Anchored to image: lines so comments + doc strings can't false-positive. | `_COMPOSE_IMAGE_RE` in doctor.py |
| 2.20 | β resolution: v2 confirmation doc lives at `PHASE_NN_v2_CONFIRMED.md` (sibling file); original `PHASE_NN_CONFIRMED.md` kept untouched on disk, mirroring tag-history-preserved policy. | PHASE_MAP §1 supersession bullet + release.yml |
| 2.21 | `confirm-phase` always rebuilds the test image (`docker compose run --build`); layer-cached. `--skip-tests` bypasses both build and run. | confirm_phase.py |

---

## 3. Bug ledger

Eleven bugs surfaced + fixed during this session. Each row: ID,
symptom, root cause, fix location, test coverage, systemic verdict.

| ID | Symptom | Root cause | Fix | Test | Systemic? |
|---|---|---|---|---|---|
| **A** | Pytest summary's `errors` line counted twice (`failed` increments once, `count` increments twice) | Regex pass for both `error` and `errors` keywords; `\b` boundary after `error` matches inside `errors` | `_SUMMARY_KW_PATTERNS` table; single `errors?\b` pattern; `errored` handled once | `test_pytest_summary_*` x6 | yes — every phase 01–38 |
| **B** | Tester writing `## Background` inside `tester_notes` silently truncates the rest of their notes | Parser treated every H2 as a new section delimiter | `_NOTES_FIELD_NAMES` sentinel set; only `phase_title` + `tester_notes` start sections | `test_parse_notes_inner_h2_*` x4 | yes — every phase 01–38 |
| **C** | Retention regex didn't recognise `phase-NN-vM-confirmed`; supersessions silently invisible | Regex `^phase-[0-9]+-confirmed$` was single-segment | Regex extended; per-slot v-collapse before window selection in `select_retention` | `test_supersession_*` x4 + workflow regex | yes — every phase rollback |
| **α** | Retention step's Python heredoc would `KeyError` on `os.environ["ALL_TAGS"]` | Bash `ALL_TAGS=...` not exported; child python doesn't see it | `export ALL_TAGS=...` in retention step | `test_release_yaml_parses_and_has_required_steps` asserts `^\s*export ALL_TAGS=` | yes — every release |
| **β** | v2 confirmation doc path undefined; release.yml would 404 on first supersession | PHASE_MAP §1 silent on doc location | Decision: **option 2** = sibling file `PHASE_NN_vM_CONFIRMED.md`; original kept on disk. Workflow doc-lookup honours vsuffix. | release.yml `confirmdoc` step | conditional — fires only on supersession |
| **γ** | PHASE_MAP Phase 01 row's retention prose described "5 most-recent confirmed phases" without supersession behavior | Doc drift after fix C | Updated retention bullet to describe per-slot v-collapse | n/a (doc) | local to row |
| **G** | Tester edits test file, forgets to rebuild, `confirm-phase` records stale results | `_run_tests` ran without `--build` | `--build` flag added | n/a (rebuild verified by phase-ci.yml's first run) | yes — every phase 01–38 |
| **I** | `release.yml` `permissions: contents: write` at workflow scope; broader than necessary | Initial draft put permissions top-level | Moved to `jobs.release.permissions` | `test_release_yaml_parses_and_has_required_steps` asserts job-scope + NOT workflow-scope | yes — every release |
| **J** | Workflow shape check used `line.startswith("on:")`; would silently miss `'on':` quoted form | Line-prefix string match too narrow | Regex `^(['"]?)(?P<key>[a-z_]+)\1\s*:` with `re.MULTILINE` | `test_yaml_top_keys_*` x5 | yes — every self-test |
| **E** | Phase tag drift between manifest `[mindsos] phase` and compose `image:` literals; no drift check | Two sources of truth, manually kept in sync | New `_COMPOSE_IMAGE_RE` + check in `doctor --self-test` | `test_self_test_fails_on_compose_phase_drift` + 6 regex unit tests | yes — pays back from Phase 02 |
| **ε** | Compose drift check would false-positive on comment lines mentioning old phase tags | Regex matched anywhere in file | Anchored to `^\s*image:\s*` with `re.MULTILINE` | `test_compose_image_re_ignores_*` x4 | yes — permanent |

Net: 11 fixes; 10 systemic (apply to all future phases); 1 conditional (β fires only on supersession events).

---

## 4. Files added / modified

### Added

```
.github/workflows/phase-ci.yml
.github/workflows/release.yml
mindsos_cli/_retention.py
mindsos_cli/commands/confirm_phase.py
confirmation_docs/_template_notes.md
confirmation_docs/PHASE_01_IMPLEMENTATION_LOG.md   <- this file
docs/dev/release.md
docs/dev/contributing.md
docs/dev/conventions.md
docs/dev/testing.md
tests/phase_01/__init__.py
tests/phase_01/conftest.py
tests/phase_01/test_init_notes.py
tests/phase_01/test_confirm_phase.py
tests/phase_01/test_confirm_phase_internals.py
tests/phase_01/test_workflows_present.py
tests/phase_01/test_doctor_workflow_check.py
tests/phase_01/test_retention.py
tests/phase_01/test_mkdocs_buildable.py
```

### Modified

```
confirmation_docs/PHASE_MAP.md           — Phase 01 row refined; §1 supersession rule extended
mindsos_cli/__init__.py                  — version bump 0.0.0+phase00 → 0.0.0+phase01
mindsos_cli/manifest.toml                — phase 00 → 01; added [ci] section
mindsos_cli/app.py                       — wired confirm-phase
mindsos_cli/commands/doctor.py           — workflow shape check + compose drift check
docker-compose.yml                       — image tags phase00 → phase01
pyproject.toml                           — version + description bump
mkdocs.yml                               — added 4 dev-guide nav entries
docs/dev/repo-layout.md                  — amended for Phase 01 layout
requirements-test.in                     — added PyYAML pin
```

### Tester regenerates (via `tools/lock.sh`)

```
requirements-test.txt                    — PyYAML transitively pulled in
```

`requirements.txt` is **unchanged** (no new runtime deps in Phase 01).

---

## 5. Tests added

36 Phase 01 tests across 6 files. Host-runnable: 30 (verified green
in this sandbox). Subprocess-only (require `mindsos` installed in
PATH, i.e. test image): 6.

| File | Tests | What |
|---|---|---|
| `test_retention.py` | 14 | Tag parsing (canonical + supersession); window selection; v-collapse semantics |
| `test_confirm_phase_internals.py` | 10 | Pytest summary parser (fix A); notes parser sentinel set (fix B) |
| `test_workflows_present.py` | 6 | YAML parses; `on`/`jobs` keys; release.yml has `gh release create`, retention prune, `phase-*-confirmed` trigger, **job-scope permissions (fix I)**, **`export ALL_TAGS` (fix α)** |
| `test_doctor_workflow_check.py` | 11 | self-test workflow check; `_yaml_top_keys` regex (fix J) x5; `_COMPOSE_IMAGE_RE` (fixes E + ε) x6 |
| `test_init_notes.py` | 4 | `--init-notes` shape; mutually exclusive flags |
| `test_confirm_phase.py` | 5 | Doc generation; mismatched manifest rejection; phase-00 schema parity |
| `test_mkdocs_buildable.py` | 1 | mkdocs build smoke (skipped on host without mkdocs) |

---

## 6. Residual concerns (deferred)

These were surfaced during review and consciously deferred. They do
**not** block Phase 01 push.

| ID | Issue | Plan |
|---|---|---|
| **ζ** | `confirm-phase` doesn't preflight `doctor --self-test`; drift can still slip into a confirmation doc | Phase 02: either fold preflight into `confirm-phase` (subset, no FalkorDB ping) OR add a "preflight self-test" step to PHASE_MAP §1 per-phase workflow |
| **η** | `--build` is unconditional; no opt-out except `--skip-tests` | Defer; flag if rebuild cost ever pinches |
| **θ** | Phase 01 row's "Locked decisions" block ~32 lines; approaching unwieldy | Observation only; no fix |
| **F** | `--init-notes phase-NN` vs `--phase NN` arg-shape inconsistency (one with prefix, one bare) | Phase 02 — bundle with L1 Identity CLI work |
| **H** | `_run_tests` 600s timeout hard-coded | Phase 02 (or whenever it pinches); add `[ci] confirm_phase_timeout_s` to manifest |
| **D** | Cumulative `pytest tests/` is unbounded | ~Phase 14 trigger; split into rolling 3-phase window for push CI, full suite for release CI |
| **K** | Stuck `.git/*.lock` files in this sandbox blocked git ref ops | Tester's local cleanup (not a code bug) |

---

## 7. Tester checklist

See **§ Tester checklist** in the chat alongside this log, or refer
to the chat transcript. Reproduced here for durability:

1. Clean `.git/*.lock` files on host (one-time).
2. `cd halvim_mindsos`; verify branch state.
3. `tools/lock.sh` to regenerate `requirements-test.txt`.
4. `git add -A && git commit -m "Phase 01 — Tooling infrastructure"`.
5. `docker compose build mindsos mindsos-test`.
6. `docker compose up -d falkordb`.
7. `docker compose run --rm mindsos-test pytest tests/ -v` — must be green.
8. `docker compose run --rm mindsos doctor` — sanity.
9. `docker compose run --rm mindsos doctor --self-test` — must exit 0.
10. Manually exercise `mindsos confirm-phase --init-notes phase-99`.
11. Generate `PHASE_01_CONFIRMED.md` via the wrapper:
    - `mindsos confirm-phase --init-notes phase-01`
    - Edit `notes-phase-01.md` (fill `phase_title` + `tester_notes`)
    - `mindsos confirm-phase --phase 01 --notes-file notes-phase-01.md`
    - Review `confirmation_docs/PHASE_01_CONFIRMED.md`; hand-edit if needed.
12. Optional: `pip install mkdocs==1.6.1 && mkdocs build --quiet` on host.
13. `git add confirmation_docs/PHASE_01_CONFIRMED.md && git commit`.
14. `git push origin phase-01`.
15. CI runs on push — wait green.
16. Open PR, review, squash-merge to main.
17. `git checkout main && git pull && git tag phase-01-confirmed && git push origin phase-01-confirmed`.
18. Release workflow runs on tag — verify GitHub Release created with all assets + checksums.
19. After confirm: any refinements observed during steps 5–18 → file
    in `tester_notes` of `PHASE_01_CONFIRMED.md` (overwriting if
    needed) before commit.

---

## 8. Decision references

- `confirmation_docs/PHASE_MAP.md` Phase 01 row — locked decisions
  table is the canonical contract; this log is supporting evidence.
- `confirmation_docs/PHASE_MAP.md` §1 supersession bullet — extended
  in this session to specify v2 doc path + tarball naming +
  retention-slot semantics.
- `confirmation_docs/PHASE_00_CONFIRMED.md` — schema reference
  (Phase 01 wrapper produces structurally identical docs).

---

## 9. State at end of session

- 30/30 host-runnable Phase 01 tests green.
- 6/6 subprocess-only tests written (run in test image only).
- All Phase 00 tests still pass (verified in last green run).
- YAML files parse under PyYAML.
- `mindsos_cli/manifest.toml` consistent with `docker-compose.yml`
  for Phase 01.
- Stuck `.git/*.lock` files prevent git commit from this sandbox;
  tester clears them on host before commit.
- No further pushbacks from the design reviewer agent on this branch.
