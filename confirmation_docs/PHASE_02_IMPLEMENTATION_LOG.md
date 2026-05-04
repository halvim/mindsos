# Phase 02 — Implementation Log

> Curated record of the Phase 02 design + implementation session
> (2026-05-04). Captures locked decisions, the IRI scope adjudication,
> bug ledger, files touched, tests added, residual concerns, and the
> tester checklist. Read in conjunction with `PHASE_MAP.md` Phase 02
> row + the eventual `PHASE_02_CONFIRMED.md`.

---

## 1. Charter

Phase 02 = **L1 Identity** (UUID generation + IdStrategy +
IdentityRegistry repackaged behind a `mindsos identity` CLI surface).
Per-phase row scope (refined in this session, locked in
`PHASE_MAP.md` §4):

- Slim `mindsos_core/` repackage from the parent project — only the
  identity slice (the remainder lands phase-by-phase).
- `mindsos identity {strategies, mint, registry}` Typer subcommand
  group; every command is `--json` aware; `--strategy` is required on
  `mint` (no silent default — ADR-0131).
- Entrypoint rework: drop the doubled `mindsos` invocation by overriding
  the compose entrypoint on the `mindsos` service.
- `doctor --self-test` extension: version-string drift across `[mindsos]
  version`, `pyproject.toml [project] version`, and
  `mindsos_cli/__init__.py:__version__`. Plus a new `--static-only` flag
  that skips the FalkorDB-reachability ping (used by the Phase 02
  preflight on the host venv where the compose service name `falkordb`
  isn't resolvable).
- `confirm-phase` preflights `doctor --self-test --static-only` (ζ from
  Phase 01 §6 deferral).
- `--init-notes NN` is the new canonical shape; `--init-notes phase-NN`
  remains a parse-accepted alias (F from Phase 01 §6 deferral).
- Image-completeness regression test (`tests/phase_02/test_image_completeness.py`)
  to guard against the φ-class Dockerfile-COPY drift Phase 01 hit during
  tester run (gg from Phase 01 §6 deferral).

**IRI parsing is explicitly out of scope** for Phase 02. Surfaced and
adjudicated at the start of the session — the Phase 02 row originally
mentioned IRI parsing, but `mindsos_core` has no IRI parser today (only
UUID/IdStrategy/IdentityRegistry), and ADR-0035 + `docs/concepts/identity.md`
both say Core treats `node_id` as opaque. Decision: drop IRI parse from
Phase 02; it lands in Phase 12 (L2 Identifiers + role IRIs + REF_TYPES).

---

## 2. Scope adjudications (decided at the top of the session)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 2.1 | Phase 02 IRI parser scope | **Drop entirely.** Phase 02 = mint / registry / strategies only. | ADR-0035: "Core keeps UUID4. Determinism is delegated to higher layers that own the content." `docs/concepts/identity.md`: "The Core Layer does not enforce any IRI format." Phase 12 owns IRI parse. |
| 2.2 | Entrypoint rework approach | **Override compose entrypoint to `["/usr/local/bin/entrypoint.sh", "mindsos"]`** on the `mindsos` service; keep bare entrypoint on `mindsos-test`. | Cleanest UX. Preserves gosu privilege drop + bind-mount chown. `mindsos-test` still runs `pytest` unprefixed. Tester gets `compose run --rm --entrypoint /bin/bash mindsos` for sh debug. |
| 2.3 | Doctor preflight: how to skip FalkorDB ping | **New `--static-only` flag** on `doctor`. Preflight invokes `doctor --self-test --static-only --json`. | Confirm-phase runs on Linux host venv where compose service name `falkordb` isn't resolvable. Static drift is what preflight cares about; FalkorDB reachability is already covered by the in-container test suite. |
| 2.4 | `--init-notes` arg shape | **Bare `NN` canonical** (parity with `--phase NN`). `phase-NN` remains a parse-accepted alias. | F from Phase 01 §6 deferral. Cheap consistency win; alias preserves muscle memory. |
| 2.5 | Phase 01 §6 deferral triage | **Land in Phase 02:** ζ, F, ee, gg. **Further defer:** η, H. | Cheap fold-ins now; η and H show no friction yet. |

---

## 3. Locked decisions (final, post-iteration)

| # | Decision | Where it lives |
|---|---|---|
| 3.1 | Slim `mindsos_core` package — exports `IdentityError`, `CoreError`, `generate_uuid`, `IdStrategy`, `UUID4Strategy`, `UUID5FromContentStrategy`, `IRIPassthroughStrategy`, `NAMESPACE_MINDSOS`, `IdentityRegistry`. | `mindsos_core/__init__.py`, `mindsos_core/exceptions.py`, `mindsos_core/models/__init__.py`, `mindsos_core/models/identity.py` |
| 3.2 | `[tool.setuptools.packages.find]` extends to include `mindsos_core*`. | `pyproject.toml` |
| 3.3 | `mindsos identity strategies [--json]` enumerates the three IdStrategy implementations with stable JSON shape (name, class, deterministic, ignores_content, description). | `mindsos_cli/commands/identity.py:strategies_cmd` |
| 3.4 | `mindsos identity mint --strategy {uuid4|uuid5|iri} [--kind KIND] [--seed JSON|@PATH] [--json]` mints an id. `--strategy` is required (exits 2 with structured error if missing). UUID5 without seed exits 1 (IdentityError from the strategy itself). IRI with empty/non-string `iri` exits 1. | `mindsos_cli/commands/identity.py:mint_cmd` |
| 3.5 | `mindsos identity registry [--scope NAME] [--register ID...] [--list] [--clear] [--state-file PATH] [--json]` exercises an `IdentityRegistry` with cross-invocation persistence via JSON state file. Default state-dir is `$MINDSOS_STATE_DIR` else `~/.mindsos/`. | `mindsos_cli/commands/identity.py:registry_cmd` |
| 3.6 | Compose `mindsos` service overrides entrypoint to `["/usr/local/bin/entrypoint.sh", "mindsos"]`. `mindsos-test` keeps the default. Image tag bumped to `mindsos:phase02-{prod,test}`. | `docker-compose.yml` |
| 3.7 | `doctor --static-only` skips FalkorDB ping when combined with `--self-test`. Static drift checks (workflows, compose tags, version strings, lockfile sha) still run. | `mindsos_cli/commands/doctor.py:doctor` |
| 3.8 | `doctor --self-test` adds version-string parity check across `[mindsos] version` / `pyproject.toml [project] version` / `mindsos_cli/__init__.py:__version__`. Init-version parsed by regex (anchored start-of-line) — no runtime import. | `mindsos_cli/commands/doctor.py:_read_pyproject_version`, `_read_init_version`, `_VERSION_LITERAL_RE` |
| 3.9 | `confirm-phase` preflights `doctor --self-test --static-only --json` via subprocess (`sys.executable -m mindsos_cli ...`). Failure aborts with non-zero exit and prints the captured output to stderr. `--skip-tests` bypasses both preflight and `_run_tests`. | `mindsos_cli/commands/confirm_phase.py:_preflight_self_test` |
| 3.10 | `--init-notes NN` accepts bare phase number; `phase-NN` remains a parse-accepted alias. Error message lists both. | `mindsos_cli/commands/confirm_phase.py:_init_notes` |
| 3.11 | `tests/phase_02/test_image_completeness.py` parametrises over a list of sentinel files that MUST be reachable from `MINDSOS_REPO_ROOT`. Adding a new static input that the CLI reads at runtime requires (a) a Dockerfile COPY in both prod and test stages and (b) appending the path to `_SENTINEL_PATHS` in this test. | `tests/phase_02/test_image_completeness.py` |
| 3.12 | `tests/phase_02/conftest.py:_run_cli` **merges** the parent process env with any caller-supplied `env=`, instead of replacing. Required so subprocess CLI tests inherit `PATH`/`HOME` while still overriding `MINDSOS_STATE_DIR`. | `tests/phase_02/conftest.py` |
| 3.13 | Per-phase ritual: bump `[mindsos] phase` + `[mindsos] version` in manifest, `[project] version` + `[project] description` in pyproject, `__version__` in `mindsos_cli/__init__.py`, every `mindsos:phaseNN-*` literal in compose. `doctor --self-test` catches drift in any of the four. | manifest.toml, pyproject.toml, mindsos_cli/__init__.py, docker-compose.yml |
| 3.14 | PHASE_MAP §1 amendments: (a) "Per-phase workflow" row tagged `[Mac]`/`[Linux]` for every step; (b) commit-before-PR rule for notes file + CONFIRMED doc; (c) new "Two-machine workflow" row; (d) new "`doctor --self-test` checks" row enumerating the six categories; (e) "Tests in-container" row notes the entrypoint rework. | `confirmation_docs/PHASE_MAP.md` §1 |

---

## 4. Bug ledger

No production bugs surfaced during this session — Phase 02 is cleaner
than Phase 01 because the design questions were adjudicated up front
(IRI scope, entrypoint, preflight behaviour) before any code was written.

The one ambiguity caught in review:

| ID | Symptom | Root cause | Fix |
|---|---|---|---|
| **A** | First draft of `tests/phase_02/conftest.py:_run_cli` replaced subprocess env with caller's dict, so `env={"MINDSOS_STATE_DIR": ...}` lost `PATH` and `HOME`. | Default `subprocess.run(env=...)` semantics: when set, it replaces wholesale. | Merge `os.environ` with caller-supplied `env`. Captured in 3.12 above. Phase 01 had the same gotcha (test files that needed PATH had to add it manually). |

---

## 5. Files added / modified

### Added (Phase 02)

```
mindsos_core/__init__.py
mindsos_core/exceptions.py
mindsos_core/models/__init__.py
mindsos_core/models/identity.py
mindsos_cli/commands/identity.py
docs/concepts/identity.md
docs/api/core/identity-registry.md
tests/unit/__init__.py
tests/unit/test_identity.py                 (preserved verbatim from parent project)
tests/phase_02/__init__.py
tests/phase_02/conftest.py
tests/phase_02/test_identity_strategies.py
tests/phase_02/test_identity_mint.py
tests/phase_02/test_identity_registry.py
tests/phase_02/test_doctor_version_drift.py
tests/phase_02/test_image_completeness.py
tests/phase_02/test_confirm_phase_preflight.py
confirmation_docs/PHASE_02_IMPLEMENTATION_LOG.md   <- this file
```

### Modified

```
confirmation_docs/PHASE_MAP.md   — §1 amendments + Phase 02 row refined
mindsos_cli/__init__.py          — version 0.0.0+phase01 → 0.0.0+phase02
mindsos_cli/manifest.toml        — phase 01 → 02; version bumped
mindsos_cli/app.py               — wired register_identity_app
mindsos_cli/commands/doctor.py   — --static-only flag; version-string drift check; helpers
mindsos_cli/commands/confirm_phase.py — preflight self-test; --init-notes NN parity
docker-compose.yml               — image tags phase01 → phase02; entrypoint override on mindsos service
pyproject.toml                   — version + description bumped; mindsos_core* added to packages.find
Dockerfile                       — COPY mindsos_core in both prod and test stages
mkdocs.yml                       — added Concepts + API nav entries
docs/dev/contributing.md         — Mac/Linux split + commit-before-PR + Python 3.12 host setup
docs/dev/conventions.md          — entrypoint rework note + identity command examples
docs/dev/repo-layout.md          — mindsos_core slim package + tests/phase_02 + tests/unit
```

`requirements.in` / `requirements.txt` — **unchanged** (no new runtime
deps in Phase 02; the slim mindsos_core has no third-party deps).

---

## 6. Tests added

40 new Phase 02 tests across 6 files + 6 preserved unit tests.
Host-runnable on the Mac sandbox during this session (Python 3.10 with
`tomli` shim): 34 / 40 — the remaining 6 require the `mindsos` console
script on PATH, which Python 3.10 can't `pip install -e .` against (the
package's `requires-python = ">=3.12"`). All 6 have been hand-verified
in-process via `typer.testing.CliRunner` and will run green in the
test image (Python 3.12).

| File | Tests | What |
|---|---|---|
| `tests/phase_02/test_identity_strategies.py` | 3 | `strategies` enumerates uuid4/uuid5/iri; JSON shape; human text mentions all three |
| `tests/phase_02/test_identity_mint.py` | 12 | `--strategy` required (exit 2); UUID4 mints distinct ids; UUID5 deterministic for same seed; UUID5 changes when kind changes; UUID5 requires seed (exit 1); IRI passthrough returns supplied IRI; IRI falls back to UUID4 without seed; IRI rejects empty IRI (exit 1); invalid `--strategy` name (exit 2); `--seed` must be JSON object (exit 2); invalid JSON (exit 2) |
| `tests/phase_02/test_identity_registry.py` | 6 | Round-trip register/list; duplicate exits non-zero; clear empties; explicit `--state-file` override; no action exits 2; corrupt state file diagnosed |
| `tests/phase_02/test_doctor_version_drift.py` | 7 | `_read_pyproject_version` happy + missing + invalid TOML; `_read_init_version` happy + no version + multiple versions + indented (class-body) form |
| `tests/phase_02/test_image_completeness.py` | 15 (parametrised) | 15 sentinel files exist + non-zero on disk |
| `tests/phase_02/test_confirm_phase_preflight.py` | 6 | Preflight helper success / failure / missing-executable; `--init-notes` accepts bare NN, legacy phase-NN, rejects others |
| `tests/unit/test_identity.py` (preserved) | 6 | UUID uniqueness; register + contains; duplicate raises; unregister idempotent; replace atomicity; replace swap |

Cumulative test count after Phase 02 (in-container): expected **62 +
40 + 6 = 108 tests** (62 from Phase 00+01, 40 new Phase 02, 6 preserved
unit). Confirmation pending tester run on Linux box.

---

## 7. Residual concerns (deferred)

| ID | Issue | Plan |
|---|---|---|
| **η** | `--build` is unconditional in `confirm-phase`'s `_run_tests`; no opt-out except `--skip-tests`. | Defer. No friction observed yet. Revisit if rebuild cost ever pinches. |
| **H** | `_run_tests` 600s timeout hard-coded. | Defer. Revisit if a phase legitimately needs >600s of test runtime (likely Phase 26 / 32 integration). |
| **D** | Cumulative `pytest tests/` is unbounded. | Targeted at ~Phase 14 — split into rolling 3-phase window for push CI, full suite for release CI. |
| **I-02** | The init-version regex matches the **first** start-of-line `__version__ = "..."` literal in `mindsos_cli/__init__.py`. A docstring with `__version__ = '...'` at column 0 would false-positive. Highly unlikely (docstrings start with `"""`), but the regex is line-based and not AST-based. | Defer. Move to AST parsing if a real false-positive surfaces. The current regex tolerates the realistic forms (assignment with leading whitespace as in class bodies is correctly excluded). |
| **J-02** | `mindsos identity registry`'s state file is **not** locked. Two concurrent `--register` invocations can race. | Acceptable — debug-only surface, single-tester usage. Phase 05+ ships the real metagraph-scoped registry under proper concurrency control. |
| **K-02** | The `mindsos identity registry` state file at `~/.mindsos/identity-registry-<scope>.json` is not gitignored. If a tester accidentally creates it inside the repo working tree (e.g., via `--state-file ./registry.json`), `git status` will show it. | Acceptable — `--state-file` is an explicit override; the default location is outside the repo. |

---

## 8. Tester checklist

1. **[Mac]** Pull main, branch off `origin/main` (NOT off phase-01):
   ```sh
   git fetch origin
   git checkout main
   git pull
   git checkout -b phase-02 origin/main
   ```
2. **[Mac]** Verify version strings are aligned:
   ```sh
   grep -n version mindsos_cli/manifest.toml pyproject.toml mindsos_cli/__init__.py
   ```
   All three should show `0.0.0+phase02`.
3. **[Mac]** Verify compose image tags:
   ```sh
   grep "image: mindsos:" docker-compose.yml
   ```
   Both should show `mindsos:phase02-prod` / `mindsos:phase02-test`.
4. **[Mac]** Commit + push.
5. **[Linux]** Pull, build images:
   ```sh
   git pull
   docker compose build mindsos mindsos-test
   ```
6. **[Linux]** Bring up FalkorDB:
   ```sh
   docker compose up -d falkordb
   ```
7. **[Linux]** Run cumulative tests in-container (canonical pass criterion):
   ```sh
   docker compose run --rm mindsos-test pytest tests/ -v
   ```
   Expect 108 passed + 1 skipped (`test_mkdocs_buildable.py` skips —
   mkdocs isn't in the test image).
8. **[Linux]** Manual exploration — verify the entrypoint rework works without doubled `mindsos`:
   ```sh
   docker compose run --rm mindsos doctor                          # no doubled mindsos
   docker compose run --rm mindsos identity strategies             # no doubled mindsos
   docker compose run --rm mindsos identity strategies --json
   docker compose run --rm mindsos identity mint --strategy uuid4 --json
   docker compose run --rm mindsos identity mint --strategy uuid5 --seed '{"v":"x"}' --json
   docker compose run --rm mindsos identity mint --strategy iri --seed '{"iri":"oewn-2024:synset:01-n"}' --json
   docker compose run --rm mindsos identity registry --scope demo --register a --register b --list --json
   docker compose run --rm mindsos identity registry --scope demo --register a   # duplicate → exit 1
   docker compose run --rm mindsos doctor --self-test
   ```
   **Note (correction to original draft):** the legacy doubled form
   `docker compose run --rm mindsos mindsos <subcommand>` is **broken**
   in Phase 02. The compose entrypoint prepends `mindsos`, so the
   doubled invocation becomes `mindsos mindsos <subcommand>` to the
   binary; Typer reads the second `mindsos` as a subcommand and fails
   with `No such command 'mindsos'`. Treat this as a deliberate
   breaking change; update any recipe carrying the doubled form
   forward from Phase 01.
9. **[Linux]** Set up the host venv (one-time per machine, Phase 02 onward):
   ```sh
   cd halvim_mindsos
   python3 --version          # must be 3.12+
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   mindsos doctor --self-test --static-only --json | python3 -m json.tool
   ```
10. **[Linux]** Generate the confirmation doc:
    ```sh
    source .venv/bin/activate
    export FALKORDB_HOST=localhost   # or unset; preflight uses --static-only
    mindsos confirm-phase --init-notes 02
    ${EDITOR:-nano} notes-phase-02.md   # fill phase_title + tester_notes
    mindsos confirm-phase --phase 02 --notes-file notes-phase-02.md
    ```
    Watch the preflight log output. If `doctor --self-test --static-only`
    fails, fix drift and re-run.
11. **[Linux]** Review `confirmation_docs/PHASE_02_CONFIRMED.md`; hand-edit if needed.
12. **[Mac]** Verify the working tree is clean and the doc + notes are tracked:
    ```sh
    git status                                      # nothing untracked under confirmation_docs/ or repo root
    git ls-files confirmation_docs/PHASE_02_CONFIRMED.md notes-phase-02.md
    ```
13. **[Mac]** Add + commit + push:
    ```sh
    git add confirmation_docs/PHASE_02_CONFIRMED.md notes-phase-02.md
    git add -A
    git commit -m "Phase 02 — L1 Identity (UUID / IdStrategy / IdentityRegistry + identity CLI)"
    git push -u origin phase-02
    ```
14. **[Mac]** Open PR against `main`. CI runs `phase-ci.yml` (in-container
    pytest + mkdocs build). Wait green.
15. **[Mac]** Squash-merge the PR.
16. **[Mac]** Tag the squash-merge commit on **main** (not on the
    phase-02 branch — Phase 01 hit a force-rebase issue from this exact
    mistake):
    ```sh
    git checkout main
    git pull
    git tag phase-02-confirmed
    git push origin phase-02-confirmed
    ```
17. CI runs `release.yml`. Verify the GitHub Release exists with the
    expected assets (tarball + Dockerfile + requirements*.txt +
    checksums.txt) and verify SHA256:
    ```sh
    curl -L -o checksums.txt https://github.com/halvim/mindsos/releases/download/phase-02-confirmed/checksums.txt
    # and the assets…
    shasum -a 256 -c checksums.txt   # macOS
    # sha256sum -c checksums.txt     # Linux
    ```

---

## 9. Decision references

- `confirmation_docs/PHASE_MAP.md` Phase 02 row — locked decisions
  table is the canonical contract; this log is supporting evidence.
- `confirmation_docs/PHASE_MAP.md` §1 — Mac/Linux split, commit-before-PR
  rule, `doctor --self-test` six-check enumeration, entrypoint rework
  note in "Tests in-container" row.
- `confirmation_docs/PHASE_01_IMPLEMENTATION_LOG.md` §6, §10 — the
  deferrals + post-checklist discoveries this phase landed.
- `docs/decisions/adr/0035-uuid-generation-non-deterministic.md` — the
  load-bearing ADR for the IRI-out-of-scope decision (2.1).
- `docs/decisions/adr/0131-pluggable-id-strategy.md` — the ADR for the
  three IdStrategy implementations.

---

## 10. State at end of session

- **Host-runnable subset (Mac sandbox during this session, Python 3.10
  with tomli shim): 34/40 Phase 02 tests + 6 preserved unit tests + 42
  of 47 Phase 00+01 host-runnable tests.** The 5+6 = 11 sandbox failures
  are **all** environment-specific:
    - Phase 02: 6 subprocess CLI tests can't find `mindsos` on PATH
      because Python 3.10 can't `pip install -e .` against a
      `requires-python = ">=3.12"` package.
    - Phase 00+01: 5 doctor tests have the same root cause.
  - In-process verification via `typer.testing.CliRunner` exercised every
    subcommand path (strategies, mint with each strategy, mint without
    strategy, mint with bad seed, registry register / list / clear /
    duplicate / corrupt) — all behaved as specified.
  - Production test image (Python 3.12) will run all 108 tests.
- All version strings aligned (manifest, pyproject, `__init__.py`).
  `doctor --self-test --static-only` reports "ok" on this clean checkout
  modulo the runtime python-version drift (3.10 sandbox vs 3.12
  manifest), which is expected and not a code defect.
- `git status` is clean save for the Phase 02 changes themselves;
  tester pushes from the Mac after committing.
- `[Mac]` work is complete. Tester executes §8 from step 1 onwards.
