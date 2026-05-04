# MindsOS PHASE_MAP

**Authoritative phased test-rollout plan for L0–L3.** Frozen 2026-05-02.

L4 (Intelligence) and L5 (Mental Model) are explicitly **out of scope**. The FOL layer is also deferred. A separate follow-up plan will cover them.

---

## 0. How a phase chat reads this file (load-bearing rule)

To prevent context bloat as phases compound, every phase chat reads:

1. **§1** (settled cross-cutting decisions).
2. **Its own row** in §3 / §4 / §5.
3. **The two prior phase rows** (for transitive dependency context).
4. **The most recent `confirmation_docs/PHASE_<N-1>_CONFIRMED.md`** only — not the full historical chain.
5. **Only the docs paths named in its own row**, not the full `docs/` tree.

Phase chats do **not** re-read older confirmation docs unless explicitly debugging a regression that traces to one. PHASE_MAP itself is the durable contract; confirmation docs are point-in-time evidence.

---

## 1. Settled cross-cutting decisions

| Topic | Decision |
|---|---|
| Repackage vs rewrite | Repackage existing code; net-new code allowed only where an ADR is locked-but-not-coded (called out per phase). |
| Tester driver | New package `mindsos_cli` (Typer/Click). Sane defaults; every command supports `--json`; errors to stderr; non-zero exit on failure. |
| Distribution | Docker Compose: one `mindsos` image (multi-stage, slim, base pinned by SHA256 digest) + one `falkordb` sidecar (version-pinned). Source-only primary install. Hybrid fallback: `docker save` tarballs attached to GitHub Releases (5-phase rolling window). |
| Repo + registry | `halvim/mindsos` (lowercased). **No GHCR.** GitHub Releases hold tarballs. |
| CI | GitHub Actions, `GITHUB_TOKEN` only. Push to `phase-*` branch → in-container test suite. Tag `phase-NN-confirmed` → build + test + create Release with tarball + Dockerfile snapshot + lockfile snapshot + checksums; release body auto-generated from the confirmation doc. Retention prunes tarballs older than 5 most-recent confirmed phases. |
| Branching | Branch `phase-NN` off main → PR → squash merge → tag `phase-NN-confirmed`. `latest` follows the most recent confirmed phase. |
| **Phase rollback / supersession** | If Phase N+k reveals a regression in already-confirmed Phase N: tag `phase-NN-superseded` on main; rewrite the row in this map; open a new branch `phase-NN-v2`; tester reverts to `phase-(N-1)-confirmed` while v2 is built; on confirm, tag `phase-NN-v2-confirmed`. The original `phase-NN-confirmed` tag remains in history as evidence but is no longer the install target for that index. **Confirmation doc:** v2 ships a sibling file `confirmation_docs/PHASE_NN_v2_CONFIRMED.md` (the original `PHASE_NN_CONFIRMED.md` stays untouched on disk, mirroring the tag-history rule). The release workflow derives the doc path from the tag's vsuffix. **Tarball naming:** `mindsos-phaseNN-v2.tar.gz` (vsuffix preserved). **Retention slot:** the (NN, vM) pair collapses to a single slot per phase NN — within the slot, the highest vM is the install target; lower vM tarballs evict immediately, regardless of the 5-phase window. |
| Per-phase workflow | (a) [Mac] implement on `phase-NN` (branch off `origin/main`, **never** off the prior phase's branch); (b) [Linux] in-container automated tests green via `docker compose run --rm mindsos-test pytest tests/`; (c) [Linux] tester does manual CLI exploration; (d) [Linux] tester runs `mindsos confirm-phase --init-notes NN` (Phase 02+) or `--init-notes phase-NN` (Phase 01) or hand-fills the markdown template (Phase 00) — the wrapper preflights `doctor --self-test` and aborts on drift; (e) [Linux] tester reviews and edits the resulting `confirmation_docs/PHASE_NN_CONFIRMED.md`; (f) [Mac] phase chat updates `docs/` mkdocs source + this map's row for phase NN+1; (g) **[Mac] verify `notes-phase-NN.md` AND `confirmation_docs/PHASE_NN_CONFIRMED.md` are tracked + committed** (untracked files are silently dropped at squash-merge — Phase 01 hit a `release.yml` "Verify confirmation doc exists" failure for exactly this reason); (h) [Mac/Linux] tester pushes branch + opens PR; (i) merge → [Mac, on `main`] tag from the squash-merged commit, **not from the phase-NN branch**; push tag → CI builds Release. |
| Two-machine workflow (Mac + Linux) | Code is edited on Mac (Claude sessions live there). In-container tests, manual CLI exploration, `confirm-phase`, and tag-and-push run on a separate Linux box. Sync is git push/pull (the Mac never sees Linux's filesystem and vice-versa). Recipes in this repo tag steps `[Mac]` or `[Linux]` explicitly. `confirm-phase` runs from a Python ≥ 3.12 venv on the Linux host (`pip install -e .` inside `halvim_mindsos/.venv`), **not** via `docker compose run` — the prod container has no `git`, no `docker` CLI, and no docker socket. |
| `doctor --self-test` checks | (1) Python runtime version vs `[runtime.python] version`; (2) `requirements.txt` sha256 vs `[lockfile] requirements_txt_sha256`; (3) FalkorDB reachability + version vs `[runtime.falkordb] version`; (4) `[ci] required_workflows` files exist + non-empty + parse-shaped (Phase 01+); (5) `^\s*image:\s*mindsos:phase<NN>-<stage>` literals in `docker-compose.yml` match `[mindsos] phase` (Phase 01+); (6) **version-string parity across `[mindsos] version`, `pyproject.toml [project] version`, and `mindsos_cli/__init__.py:__version__`** (Phase 02+). Drift in any of these exits non-zero. |
| Confirmation doc as artifact | The confirmation doc is **a markdown template the tester can edit by hand**. The `mindsos confirm-phase` wrapper (Phase 01+) generates a draft from the template; the tester reviews, possibly edits, and commits. **CI does NOT validate the doc's structure** beyond "exists and non-empty" — keeping the doc human-authoritative, not tool-authoritative. |
| Confirmation doc schema (template fields) | `phase_number`, `phase_title`, `git_sha`, `image_build_hash`, `falkordb_version`, `automated_test_summary` (count + suite hash), `tester_notes`, `timestamp_utc`, `mkdocs_pages_updated`. |
| Failure path | Tester does NOT run `confirm-phase`; describes problem; phase chat iterates; or abandon → close branch, rewrite map row. |
| Tests in-container | `docker compose run --rm mindsos-test pytest tests/` (cumulative, all phases) is the canonical pass criterion. (`mindsos-test` is the test-stage image from the multi-stage Dockerfile; it adds pytest to the `prod` runtime. The slim `mindsos` runtime image contains no test deps.) Host-side runs allowed for dev iteration but do not count. From Phase 02 onward, `docker compose run --rm mindsos <subcommand>` works directly (no doubled `mindsos`) — compose overrides the entrypoint to `["/usr/local/bin/entrypoint.sh", "mindsos"]` so the gosu privilege drop still happens before the binary runs. **Breaking change vs Phase 01:** the doubled form `docker compose run --rm mindsos mindsos <subcommand>` is broken (Typer reads the second `mindsos` as a subcommand). The `mindsos-test` service keeps the bare entrypoint so `pytest …` runs unprefixed. |
| CLI backward compat | Breaking changes between phases allowed; documented in version notes. |
| Test layout | Existing `tests/`, `tests_l3/`, `tests_server/` preserved. Phase-specific tests live in `tests/phase_NN/`. Pre-existing tests must continue to pass on every phase. |
| Reproducibility | Base image pinned by SHA256 digest; `requirements.txt` via `pip-compile --generate-hashes`; FalkorDB image pinned; multi-stage build; no build tools in final layer. |
| Logs / data | Host-mounted volumes from Phase 00 (paths set in phase chat). |
| Linux + Compose v2 | `docker compose` (v2 syntax). |
| Conflict resolution in source docs | Most recent date wins by default. Surface to **Open Questions** only when a newer doc silently contradicts an explicit earlier lock/invariant. |
| Foundations-first grouping | Independents share a phase; dependents go in the next phase. |
| **Integration phases are an exception to the foundations-first rule** | Phases 26 and 32 are convergence points that depend on **all prior shipped phases**. They add no new feature; they catch cross-phase regressions via one scripted scenario. |
| Mkdocs page evolution | A doc page may be touched by multiple phases. Each phase only **amends** the slice it owns; final-pass review is at Phase 38. Pages carry a `last_confirmed_phase: NN` front-matter field (stored, not rendered) so a future audit can identify pages whose evolution stalled. |
| Out of scope | L4 + L5 + FOL + 7 L4 critique pushes + 5 L1 design-critique pushes (latter mostly addressed by L1 redesign locks). |

---

## 2. Per-phase row schema

```
### Phase NN — <Title>

  **Status:** Pending | In progress | Confirmed | Superseded | Abandoned
  **Branch:** phase-NN
  **Tag on confirm:** phase-NN-confirmed
  **Depends on:** <list of phase NNs that must be Confirmed first>
  **Layer(s):** <L0 / L1 / L2 / L3 / cross>
  **Net-new code?:** No (repackage only) | Yes (specify what)
  **Features in scope (capability-level — implementation chosen by phase chat):**
    - <terse capability list>
  **Modules touched (best-effort; phase chat finalises):**
    - <package/module list>
  **Automated tests (location + intent — names chosen by phase chat):**
    - tests/phase_NN/ — <what they verify>
  **Confirmation command (Phase 01+):**
    `mindsos confirm-phase --phase NN --notes-file notes.md`
    (Phase 00 only: tester writes the confirmation doc by hand from the template.)
  **Pass criterion (what the tester verifies):**
    - <bulleted, terse>
  **Risks / known issues to watch:**
    - <bulleted>
  **Doc sections this phase confirms (mkdocs paths):**
    - docs/<...>.md — <one-line slice description>
  **Breaking changes from prior phase:**
    - <list, or "none">
```

---

## 3. Phase index

| # | Title | Layer | Deps |
|---|---|---|---|
| 00 | Runtime infrastructure — image + Compose + base CLI | cross | — |
| 01 | Tooling infrastructure — CI workflows, retention, `confirm-phase` wrapper, mkdocs verify | cross | 00 |
| 02 | L1 Identity — IRIs, IdentityRegistry, IdStrategy | L1 | 01 |
| 03 | L1 Graph elements — Graph, Node, Edge, HyperEdge | L1 | 02 |
| 04 | L1 Schema — NodeType, EdgeType, opt-in strict | L1 | 02 |
| 05 | L1 Metagraph elements — Metagraph, MetaEdge, MetaHyperEdge, CompositionalMetaEdge | L1 | 03 |
| 06 | L1 Instancing — `mindsos_instances` package | L1 | 03, 05 |
| 07 | L1 Persistence — Client, FalkorClient, InMemoryClient, AsyncClient, repositories, WAL, indexes, OCC | L1 | 03, 04, 05, 06 |
| 08 | L1 Reconstruction — loaders, streaming loader, refresh | L1 | 07 |
| 09 | L1 XRef — primitive, repository, loader, ref:global cutover | L1 | 07, 08 |
| 10 | L1 Snapshot + soft-delete + RemovalImpact | L1 | 07, 08 |
| 11 | L1 Cypher builders + integrity scanner + schema migration | L1 | 07 |
| 12 | L2 Identifiers + role IRIs + REF_TYPES | L2 | 02 |
| 13 | L2 Schemas — alignment, lexicon, ontology, concepts | L2 | 04, 12 |
| 14 | L2 KnowledgeLayer + role-graph bootstrap (Global + Local) + MetagraphView (read-only) | L2 | 05, 07, 08, 12, 13 |
| 15 | L2 Importers — DOLCE, OEWN, FrameNet, Alignments | L2 | 13, 14 |
| 16 | L2 Promotion machinery | L2 | 14 |
| 17 | L2 Versioning + breadcrumbs | L2 | 14 |
| 18 | Server: user store + auth | L0 | 07 |
| 19 | Server: sessions | L0 | 18 |
| 20 | Server: bootstrap CLI + admin reset + last-admin protection | L0 | 19 |
| 21 | Server: audit log | L0 | 19 |
| 22 | Server: admin ops | L0 | 19, 21 |
| 23 | Server: promotion lock + MetagraphSnapshot rollback | L0 | 10, 16, 19 |
| 24 | Server: per-user transactional promotion (ADR-0118 full impl). **NEW CODE.** | L0 | 23 |
| 25 | Server: SessionProtocol seam in L2 + hydrate/extract hooks | cross | 14, 19 |
| **26** | **Integration A — L0+L1+L2 end-to-end scripted scenario** | cross | 02–25 |
| 27 | L3 DataStates + capacity primitives | L3 | 02, 05, 06 |
| 28 | L3 12 categories + dual metagraph + role-graph bootstrap + capability gate | L3 | 14, 25, 27 |
| 29 | L3 Discovery + Constraints | L3 | 28 |
| 30 | L3 Pipeline finder + invoke runtime + ProblemTraceRecord | L3 | 27, 28, 29 |
| 31 | L3 Residents + built-in text capacities + pathfinding | L3 | 30 |
| **32** | **Integration B — L0+L1+L2+L3 read-side end-to-end scripted scenario** | cross | 02–31 |
| 33 | L3 write capacities — 5 categories (ADR-0145). **NEW CODE.** | L3 | 25, 30, 31 |
| 34 | L3 symmetric write contract (ADR-0146). **NEW CODE.** | L3 | 33 |
| 35 | L3 per-flow build pattern (ADR-0147). **NEW CODE.** | L3 | 34 |
| 36 | L2 hybrid validators home (ADR-0139). **NEW CODE.** | L2 | 35 |
| 37 | Server-owns-importers (ADR-0144). **NEW CODE.** | L0 + L2 | 15, 36 |
| 38 | End-to-end vertical slice — text-realm + code-slice cookbook | cross | all |

**Total: 39 phases (00 through 38).** Two of them (26, 32) are integration / regression-catching phases. Six (24, 33, 34, 35, 36, 37) carry **NEW CODE** beyond repackaging.

---

## 4. Phases 00–03 — full detail

(Implementation-specific decisions — exact CLI verbs, file paths, library choices — are deliberately **not** committed in this map. The phase chat picks them when it begins, refines its row, then implements.)

### Phase 00 — Runtime infrastructure

  **Status:** In progress (refining + implementing — this chat, 2026-05-03)
  **Branch:** phase-00
  **Tag on confirm:** phase-00-confirmed
  **Depends on:** —
  **Layer(s):** cross
  **Net-new code?:** Yes — `mindsos_cli` package skeleton, `pyproject.toml`, `Dockerfile`, `entrypoint.sh`, `docker-compose.yml`, `mindsos_cli/manifest.toml`, `requirements.in`, `tools/lock.sh`, `mkdocs.yml`, two stub doc pages, `confirmation_docs/_template.md`, `.gitignore`, minimal `README.md`.

  **Locked decisions (this chat — 2026-05-03):**
    - **FalkorDB image:** `falkordb/falkordb:v4.18.3@sha256:30c530c193ac48cb6ea8c6cae745f793d2c098a0a138f7b3e46c1d90848845ba`.
    - **Python image:** `python:3.12.3-slim-bookworm@sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63`. Overrides §9's original `3.11-slim-bookworm` recommendation to match tester's host Python and reduce debugging surface.
    - **Multi-stage Dockerfile:** stages `base` → `prod` (slim runtime, no test deps) → `test` (extends `base`, adds pytest + dev deps). Compose declares both `mindsos` (target=prod) and `mindsos-test` (target=test) services. Canonical pytest invocation: `docker compose run --rm mindsos-test pytest tests/phase_NN`.
    - **Container user:** UID/GID `1000` named `mindsos`. `entrypoint.sh` chowns mounted volumes on first run (idempotent), then drops privileges via `gosu`.
    - **Volume host paths (relative to repo root):** `./.mindsos/falkordb-data/` (FalkorDB persistence), `./.mindsos/logs/` (CLI logs). Both gitignored.
    - **Lockfile generation:** `requirements.in` shipped (CLI deps only — no full-repo surface yet). `tools/lock.sh` runs `pip-compile --generate-hashes` *inside the pinned Python image* to produce `requirements.txt` with bit-identical hashes. Tester runs `tools/lock.sh` once on the Linux box; resulting `requirements.txt` is committed.
    - **Canonical truth file:** `mindsos_cli/manifest.toml` is the hand-maintained source of truth for runtime pins (FalkorDB digest, Python digest, version strings, requirements.txt sha256). Dockerfile / compose / requirements are checked *against* the manifest by `mindsos doctor --self-test` — any drift exits non-zero.
    - **mkdocs scaffolded here:** minimal `mkdocs.yml` + `docs/getting-started/install.md` + `docs/dev/repo-layout.md` so Phase 01's `mkdocs build --quiet` verification has something to verify.

  **Features in scope (capability-level):**
    - A `mindsos` Docker image (multi-stage, slim, base pinned by SHA256 digest, non-root user UID 1000).
    - A `docker-compose.yml` running `mindsos` alongside a pinned `falkordb` sidecar with healthcheck, plus a `mindsos-test` service for the test image.
    - Host-mounted volumes at `./.mindsos/falkordb-data/` and `./.mindsos/logs/`; entrypoint chowns on first run.
    - `mindsos_cli` package skeleton exposing four base commands:
        * version reporter (semantic version + git SHA + image build hash).
        * help reporter (top-level + per-subcommand).
        * doctor: end-to-end smoke check — pings FalkorDB, prints all pinned versions and the lockfile hash.
        * doctor self-test: drift detection — exits non-zero if any pin diverges from `mindsos_cli/manifest.toml`.
    - `requirements.in` (CLI deps) + `tools/lock.sh` (generates locked `requirements.txt` with hashes inside the pinned Python image).
    - `mindsos_cli/manifest.toml` — canonical truth file.
    - `confirmation_docs/_template.md` — markdown template the Phase 00 tester fills by hand to produce `PHASE_00_CONFIRMED.md`.
    - mkdocs scaffold (`mkdocs.yml` + 2 stub pages) so Phase 01's mkdocs verification has a tree.

  **Modules touched:**
    - `mindsos_cli/` (new package skeleton): `__init__.py`, `__main__.py`, `app.py`, `manifest.toml`, `commands/__init__.py`, `commands/version.py`, `commands/doctor.py`.
    - `pyproject.toml` (new — declares `mindsos_cli` as the installable package; entry point `mindsos`).
    - `Dockerfile`, `entrypoint.sh`, `docker-compose.yml`.
    - `requirements.in`, `tools/lock.sh` (and, post-tester-run, `requirements.txt`).
    - `mkdocs.yml`, `docs/getting-started/install.md`, `docs/dev/repo-layout.md`.
    - `confirmation_docs/_template.md`, `confirmation_docs/PHASE_MAP.md` (refined here).
    - `.gitignore`, `README.md`.

  **Automated tests:**
    - `tests/phase_00/` — version command exits 0 and prints semver+SHA; doctor reports both pinned versions against a running `falkordb`; doctor self-test passes against the canonical manifest; compose stack reaches healthy.

  **Confirmation command:**
    Phase 00 has no `confirm-phase` wrapper yet. Tester copies `confirmation_docs/_template.md` → `confirmation_docs/PHASE_00_CONFIRMED.md`, fills the fields by hand, commits.

  **Pass criterion:**
    - On a clean Linux box: `git pull` of `phase-00` + `tools/lock.sh` (one-time) + `docker compose up -d` succeeds.
    - `docker compose run --rm mindsos-test pytest tests/phase_00` is green.
    - `docker compose run --rm mindsos doctor` exits 0 and reports both pinned versions.
    - `docker compose run --rm mindsos doctor --self-test` exits 0.
    - Tester is satisfied that the runtime is reproducible (same digests in, same image out).

  **Risks / known issues to watch:**
    - FalkorDB and Python base images are both pinned by digest above — `compose pull` is bit-identical to the originally locked images.
    - `pip-compile --generate-hashes` is run inside the pinned Python image (via `tools/lock.sh`) so resolved versions and hashes match what `pip install` will produce inside the build.
    - `entrypoint.sh` chowns the mounted volumes; if the tester's host UID isn't 1000, files inside `.mindsos/` will appear owned by a numeric UID 1000 outside the container. Documented in `docs/getting-started/install.md`.
    - Phase 00 has no CI yet (CI lands in Phase 01); the tester is the only verifier.

  **Doc sections this phase confirms:**
    - `docs/getting-started/install.md` — Docker quickstart slice (stub here, fleshed out in 01).
    - `docs/dev/repo-layout.md` — `mindsos_cli/`, `confirmation_docs/`, `tools/`, `.mindsos/` mentions.

  **Breaking changes from prior phase:** none (first phase).

---

### Phase 01 — Tooling infrastructure

  **Status:** In progress (refining + implementing — this chat, 2026-05-03)
  **Branch:** phase-01
  **Tag on confirm:** phase-01-confirmed
  **Depends on:** 00
  **Layer(s):** cross
  **Net-new code?:** Yes — GitHub Actions workflows (`phase-ci.yml`, `release.yml`), retention pruning step (inline in `release.yml`, no separate Python script), `mindsos confirm-phase` subcommand, manifest-driven `[ci.required_workflows]` parity check in `doctor --self-test`, mkdocs build CI step.

  **Locked decisions (this chat — 2026-05-03):**
    - **`confirm-phase` execution model:** runs **on the host**, shells out to `docker compose run --rm mindsos-test pytest tests/` (cumulative — runs every `tests/phase_NN/` dir present, not just the current one). Captures pytest's terminal summary line via `--json-report --json-report-file=-` (pytest-json-report plugin added to `requirements-test.in`). Falls back to text-summary parsing if the plugin import fails. Computes `suite_hash` as `sha256` of the sorted concatenation of every `tests/phase_NN/**/*.py` file's contents. Reads `git_sha` from `git rev-parse HEAD`. Reads `image_build_hash` from `docker inspect --format='{{.Id}}' mindsos:phase{NN}-prod` (the tag is derived from `[mindsos] phase` in `manifest.toml`, so the chat that opens phase NN bumps that single value).
    - **`--phase` argument:** required positional value, must match `[mindsos] phase` in manifest. Mismatch is an error (prevents tester from accidentally generating Phase 02 doc on a Phase 01 branch).
    - **`--skip-tests` flag:** emergency hand-write path. Skips the docker run, writes the doc with `automated_test_summary` blank-but-marked-skipped. Documented in `docs/dev/release.md`.
    - **Notes file format:** plain markdown. Tester fills two human-authored fields only: `phase_title` and `tester_notes`. `mkdocs_pages_updated` is auto-derived from `git diff --name-only main..HEAD -- 'docs/'`. All other schema fields are auto-populated. Wrapper writes the assembled doc to `confirmation_docs/PHASE_NN_CONFIRMED.md` (overwrites if present, with a stderr warning).
    - **`--init-notes phase-NN`:** writes `notes-phase-NN.md` (in `cwd` by default; `--out PATH` overrides). Content is a copy of `confirmation_docs/_template_notes.md` with `NN` substituted.
    - **CI workflow trigger:** `phase-ci.yml` triggers on `push` to `refs/heads/phase-*` (single-segment match — also matches `phase-00-v2` per the rollback policy in §1).
    - **CI workflow steps:** checkout → docker compose build mindsos-test → docker compose run --rm mindsos-test pytest tests/ → install pinned mkdocs ad-hoc (`pip install --user 'mkdocs==1.6.1'` — single workflow step, NOT in `requirements-test.in`, so the slim runtime image stays slim) → `mkdocs build --quiet`. No layer caching for v1 (cold builds ~2 min; revisit if slow).
    - **Release workflow trigger:** `release.yml` triggers on `push` to tags matching `refs/tags/phase-*-confirmed`.
    - **Release workflow steps:** checkout the tagged ref (fetch-depth=1 is sufficient — the tag already points to the commit with `PHASE_NN_CONFIRMED.md`) → build prod image → build test image + run tests/ → `docker save mindsos:phaseNN-prod | gzip > mindsos-phaseNN.tar.gz` → compute SHA256 of tarball → assemble release notes from the confirmation doc → `gh release create phase-NN-confirmed --title "Phase NN — <title>" --notes-file <body>` → `gh release upload` for: tarball, `Dockerfile`, `requirements.txt`, `requirements-test.txt`, `checksums.txt` (sha256 of the four prior files) → run retention prune step.
    - **Retention pruning:** lists all `phase-NN-confirmed` AND `phase-NN-vM-confirmed` releases; selection logic delegated to `mindsos_cli/_retention.py` (host-unit-tested). Per supersession policy in §1: tags collapse by phase NN — within a slot, the highest vM is the install target and older vMs evict immediately; across slots, the 5 highest-numbered slots' install targets keep their tarball, the rest evict. For each evicted tag, replaces (`gh release upload --clobber`) the tarball asset (named `mindsos-phaseNN.tar.gz` or `mindsos-phaseNN-vM.tar.gz` matching the tag) with a 1-line text file containing "source-rebuild required — outside 5-phase retention window". Uses `--clobber` to swap content; never deletes a Release. Idempotent.
    - **`gh release create` body:** the release body IS `confirmation_docs/PHASE_NN_CONFIRMED.md` verbatim (capped at GitHub's 125000-char limit; all phase docs will be far under).
    - **GITHUB_TOKEN scope:** `contents: write` declared at **job-level** in `release.yml` (workflow-scope stays default `contents: read`); `phase-ci.yml` runs at default `contents: read`. No `id-token` or `packages` scopes.
    - **Manifest extension:** add `[ci]` section with `required_workflows = [".github/workflows/phase-ci.yml", ".github/workflows/release.yml"]` and `mkdocs_version = "1.6.1"`. `doctor --self-test` reads this list, asserts each file exists, is non-empty, and has top-level `on:` and `jobs:` keys (regex check tolerates quoted YAML keys: `on:`, `'on':`, `"on":`). Bumps `[mindsos] phase = "01"`, `version = "0.0.0+phase01"`. `requirements_txt_sha256` does NOT change (mkdocs is workflow-installed, not test-image-installed; PyYAML adds to `requirements-test.in` so the test-image lockfile is regenerated — but `requirements.txt` is unchanged, so the manifest's tracked sha is unchanged).
    - **Compose image-tag parity check:** `doctor --self-test` scans `docker-compose.yml` for every `mindsos:phaseNN-<stage>` literal and asserts the NN matches `[mindsos] phase`. Catches partial bumps (e.g., manifest at phase 02 but compose still references `phase01-test`). Implemented in `mindsos_cli/commands/doctor.py` via `_COMPOSE_IMAGE_RE`.
    - **`confirm-phase` always rebuilds the test image:** `_run_tests` shells out with `docker compose run --build`. Layer-cached so the cost is small (<5s for source-only edits); guarantees the doc records the current code's results, not a stale image's. `--skip-tests` bypasses the build entirely.

  **Features in scope (capability-level):**
    - GitHub Actions CI on push to `phase-*` branches: build image, run cumulative `pytest tests/`, build mkdocs.
    - GitHub Actions Release on tag `phase-NN-confirmed`: build + test + tarball + Release with assets + retention prune of older tarballs.
    - Tarball retention: keep the tarball asset for the 5 most-recent confirmed phases; older Releases survive with the asset replaced by a placeholder.
    - `mindsos confirm-phase --init-notes phase-NN` writes a notes-template file the tester fills.
    - `mindsos confirm-phase --phase NN --notes-file <PATH>` reads the notes, runs the cumulative test suite, writes `confirmation_docs/PHASE_NN_CONFIRMED.md`. `--skip-tests` available for emergency hand-write.
    - mkdocs build verification: `mkdocs build --quiet` runs in CI and must exit 0.
    - `doctor --self-test` extended to verify `[ci.required_workflows]` files exist + non-empty + parse-shaped.

  **Modules touched:**
    - `.github/workflows/phase-ci.yml` (new).
    - `.github/workflows/release.yml` (new — includes retention prune step inline).
    - `mindsos_cli/commands/confirm_phase.py` (new).
    - `mindsos_cli/app.py` (wire confirm-phase in).
    - `mindsos_cli/manifest.toml` (bump `[mindsos] phase` + `version`; add `[ci]` section).
    - `mindsos_cli/__init__.py` (bump `__version__`).
    - `mindsos_cli/commands/doctor.py` (extend `--self-test` with `[ci.required_workflows]` check).
    - `Dockerfile` (bump `mindsos:phase01-prod` / `mindsos:phase01-test` ARG default tag references; if any).
    - `docker-compose.yml` (bump `image: mindsos:phase01-{prod,test}`).
    - `confirmation_docs/_template_notes.md` (new).
    - `requirements-test.in` (add `pytest-json-report` pin); tester re-runs `tools/lock.sh` to regenerate `requirements-test.txt`.

  **Automated tests:**
    - `tests/phase_01/test_init_notes.py` — `confirm-phase --init-notes phase-99 --out <tmp>` writes a non-empty file with both `phase_title` and `tester_notes` markers.
    - `tests/phase_01/test_confirm_phase.py` — `--phase 01 --notes-file <fixture> --skip-tests --out <tmp>` writes a confirmation doc with all 9 schema fields populated; `--phase 02` (mismatched manifest) errors and exits non-zero; produced doc is structurally identical to a fixture copy of `PHASE_00_CONFIRMED.md` (same field names, in order).
    - `tests/phase_01/test_workflows_present.py` — both workflow files exist, are non-empty, contain `on:` and `jobs:` keys; release.yml mentions `gh release create` and the retention prune step; YAML parses cleanly via `yaml.safe_load` (pyyaml is a transitive dep of mkdocs/typer; if not present, fall back to a regex shape check).
    - `tests/phase_01/test_mkdocs_buildable.py` — runs `mkdocs build --quiet` against `mkdocs.yml` in a tmpdir; assert `site/index.html` exists. Skipped with reason if `mkdocs` import fails (e.g., not installed in test image — phase 01 keeps mkdocs out of the test image deliberately, so this test runs only in CI where mkdocs is installed ad-hoc OR locally if the dev has it).
    - `tests/phase_01/test_doctor_workflow_check.py` — `doctor --self-test --json` succeeds on phase-01 (workflows present); when one workflow file is renamed (via tmp setup with monkeypatched repo_root), self-test reports the missing workflow as a failure.
    - `tests/phase_01/test_retention_logic.py` — pure-Python unit test of the retention-window selection function (extracted to `mindsos_cli/_retention.py` so it's host-testable without needing GitHub).

  **Confirmation command:**
    `mindsos confirm-phase --phase 01 --notes-file notes-phase-01.md`
    First phase to exercise the wrapper end-to-end. Fallback: tester hand-edits the produced doc, or invokes with `--skip-tests` and copies `_template.md` manually.

  **Pass criterion:**
    - Push to `phase-01` branch triggers `phase-ci.yml`; build + tests + mkdocs all green.
    - Tag `phase-01-confirmed` triggers `release.yml`; a GitHub Release exists with: `mindsos-phase01.tar.gz`, `Dockerfile`, `requirements.txt`, `requirements-test.txt`, `checksums.txt`. SHA256 of each asset matches `checksums.txt`.
    - Retention step logs the 5-phase window logic; with only Phase 01 confirmed, log says `evicted=[] kept=[01]` and exits 0.
    - `mindsos confirm-phase --init-notes phase-02 --out /tmp/notes-02.md` produces a non-empty notes file (forward-compat smoke).
    - `docker compose run --rm mindsos doctor --self-test` exits 0; with one workflow file deleted on disk, exits non-zero with a structured failure pointing at the missing workflow.
    - `mkdocs build --quiet` exits 0 (broken cross-links remain non-fatal per `strict: false`).
    - All `tests/phase_00/` + `tests/phase_01/` tests pass in-container.

  **Risks / known issues to watch:**
    - **GH Actions slow-build:** No build cache means every `phase-*` push spends ~2 min on `pip install`. Acceptable for v1; add `actions/cache` keyed on `requirements*.txt` sha if it becomes painful.
    - **Retention idempotency:** `gh release upload --clobber` is idempotent; the prune step re-runs safely. But two tag pushes within the same minute could race. Accepted — single-developer repo.
    - **`gh` CLI auth:** GH-hosted runners pre-authenticate `gh` via `GITHUB_TOKEN`; no PAT needed.
    - **`pytest-json-report` adds a test-image dep:** lockfile (`requirements-test.txt`) regenerated and committed. Phase 01 confirmation doc must record the new sha and that `requirements_txt_sha256` (manifest field) is unchanged because that field tracks runtime, not test, deps.
    - **`confirm-phase` fragility:** if it ships broken, tester falls back to copying `confirmation_docs/_template.md` and hand-filling the same fields they did for Phase 00. Document this fallback in `docs/dev/release.md`.
    - **Image-tag bump per phase is one-line manual edit:** introduces a per-phase ritual that's easy to forget; `doctor --self-test` doesn't currently check tag consistency between compose and manifest. Consider adding such a check in a later phase if drift bites.
    - **Test image does NOT contain mkdocs.** Phase 01's mkdocs build is a CI-only step (workflow installs mkdocs ad-hoc). Local-dev mkdocs builds require `pip install mkdocs==1.6.1` on the host. Trade-off: keeps test image lean, at the cost of local-dev parity with CI for the mkdocs check.

  **Doc sections this phase confirms:**
    - `docs/dev/release.md` — new; full tag-driven Release flow, retention policy, fallback paths.
    - `docs/dev/contributing.md` — new; branching policy + per-phase workflow.
    - `docs/dev/repo-layout.md` — amend; mention `.github/workflows/`.
    - `docs/dev/conventions.md` — new; `--json` everywhere, exit codes, errors-to-stderr rule.
    - `docs/dev/testing.md` — new; in-container = canonical.

  **Breaking changes from prior phase:** none (additive tooling).

---

### Phase 02 — L1 Identity

  **Status:** In progress
  **Branch:** phase-02
  **Tag on confirm:** phase-02-confirmed
  **Depends on:** 01
  **Layer(s):** L1
  **Net-new code?:** **Yes (limited).** Repackages existing UUID/IdStrategy/IdentityRegistry primitives from `mindsos_core/models/identity.py` into the halvim_mindsos working tree. Net-new: (1) `mindsos identity` CLI subcommand surface; (2) entrypoint rework (compose override) to drop the doubled-`mindsos` invocation; (3) `doctor --self-test` extension for version-string drift across manifest / pyproject / `__init__.py`; (4) `confirm-phase` preflights `doctor --self-test`; (5) image-completeness regression test (φ-class guard against the Phase 01 Dockerfile-COPY drift). **IRI parsing is explicitly out of scope** — Core treats `node_id` as opaque per ADR-0035 and `docs/concepts/identity.md`; IRI parse lands in Phase 12 (L2 Identifiers + role IRIs + REF_TYPES) where role/source/version semantics live.

  **Features in scope (capability-level):**
    - `mindsos identity mint --strategy {uuid4|uuid5|iri} [--kind KIND] [--seed JSON|@FILE]` mints a fresh id under the chosen `IdStrategy`. No silent default — `--strategy` is required (per ADR-0131 and the row's risk note that the CLI must not default-pin a strategy).
    - `mindsos identity registry [--scope NAME] [--register ID]... [--list] [--state-file PATH]` exercises the `IdentityRegistry` — register ids, list contents, detect duplicates, with cross-invocation persistence via a JSON state file (default `~/.mindsos/identity-registry-<scope>.json`). The state-file approach is debug-only, not a substitute for a metagraph-scoped registry; it ships so the tester can reproduce the duplicate-rejection path interactively.
    - `mindsos identity strategies` enumerates the three shipped strategies with one-line descriptions (machine-readable `--json`).
    - Every subcommand supports `--json` (CommonMark prose for human mode).

  **Modules touched:**
    - **Repackaged into `halvim_mindsos/`:** `mindsos_core/__init__.py`, `mindsos_core/exceptions.py` (slim — only `CoreError`, `IdentityError`; the rest land with their feature phases), `mindsos_core/models/__init__.py`, `mindsos_core/models/identity.py`. No logic change vs the parent project's `mindsos_core/models/identity.py` — same `generate_uuid`, `IdStrategy`, `UUID4Strategy`, `UUID5FromContentStrategy`, `IRIPassthroughStrategy`, `NAMESPACE_MINDSOS`, `IdentityRegistry`.
    - **New:** `mindsos_cli/commands/identity.py` (Typer subcommand group), wired in `mindsos_cli/app.py`.
    - **Edited:** `mindsos_cli/commands/doctor.py` (new `_check_version_strings` extension), `mindsos_cli/commands/confirm_phase.py` (preflight + `--init-notes NN` shape — bare phase number, parity with `--phase NN`; `phase-NN` form remains a parse-accepted alias for backward compat).
    - **Edited (entrypoint rework):** `docker-compose.yml` (the `mindsos` service gets `entrypoint: ["/usr/local/bin/entrypoint.sh", "mindsos"]`; `mindsos-test` keeps the default), `mindsos_cli/manifest.toml` ([mindsos] phase + version), `pyproject.toml` (version + description), `mindsos_cli/__init__.py` (`__version__`).
    - **Preserved test from parent project:** `tests/unit/__init__.py` + `tests/unit/test_identity.py` (verbatim — exercises `IdentityRegistry`, `generate_uuid`, `IdentityError`).

  **Automated tests:**
    - `tests/phase_02/test_identity_mint.py` — mint with each strategy; `--strategy` required (no default); UUID5-from-content deterministic for the same seed; IRI-passthrough rejects empty/non-string.
    - `tests/phase_02/test_identity_registry.py` — register/list round-trip; duplicate rejection with structured error; cross-invocation persistence via state file.
    - `tests/phase_02/test_identity_strategies.py` — `strategies` lists all three with stable IRIs; `--json` shape.
    - `tests/phase_02/test_doctor_version_drift.py` — self-test catches mismatched `[mindsos] version` / `pyproject.toml` / `__init__.py:__version__`.
    - `tests/phase_02/test_confirm_phase_preflight.py` — preflight aborts on `doctor --self-test` failure unless `--skip-tests`.
    - `tests/phase_02/test_image_completeness.py` — sentinel files (`.github/workflows/phase-ci.yml`, `docker-compose.yml`, `confirmation_docs/_template_notes.md`, `mindsos_core/models/identity.py`) exist at `MINDSOS_REPO_ROOT` (=/app inside the container). Guards against future Dockerfile-COPY drift (Phase 01 §10.1 / φ).
    - `tests/unit/test_identity.py` — preserved from the parent project; runs cumulatively.

  **Confirmation command:**
    `mindsos confirm-phase --phase 02 --notes-file notes-phase-02.md`
    (Init shape changes: `--init-notes 02` is the new canonical form; `--init-notes phase-02` still parses for backward compat.)

  **Pass criterion:**
    - Tester can mint a UUID4 id and verify uniqueness across two invocations.
    - Tester can mint a UUID5 id with a given seed and reproduce it bit-identical from a second machine.
    - Tester can mint an IRI-passthrough id and have the IRI-passthrough strategy reject `--seed '{}'` (no `iri` key).
    - Tester can register two ids; the second collision exits non-zero with a structured error.
    - `docker compose run --rm mindsos identity strategies --json` works **without** the doubled `mindsos`.
    - `mindsos doctor --self-test` exits 0 against a clean checkout; exits non-zero if any of the three version strings drift.
    - `mindsos confirm-phase --phase 02 --notes-file notes-phase-02.md` runs `doctor --self-test` first; aborts on drift unless `--skip-tests`.
    - All Phase 02 + Phase 01 + Phase 00 + `tests/unit/test_identity.py` pass cumulatively in-container.

  **Risks / known issues to watch:**
    - Entrypoint rework: `docker compose run --rm mindsos sh` no longer drops to a shell (entrypoint forces `mindsos` prefix). Mitigation: tester uses `docker compose run --rm --entrypoint /bin/bash mindsos`. Documented in `docs/dev/conventions.md`.
    - `mindsos identity registry` state-file persistence is debug-only and **not** a replacement for the metagraph-scoped registry that Phase 05 will exercise. Tester should not build mental model of "registries are global" from this command.
    - `IdStrategy` is pluggable per ADR-0131; the CLI must not silently default-pin a strategy — `--strategy` is required.
    - The version-string drift check parses `mindsos_cli/__init__.py` with a regex (`__version__\s*=\s*["']([^"']+)["']`), not by importing — avoids side-effects but tolerates only the literal-string form. Phase chat must keep `__version__` as a plain string.
    - Repackaging only the identity slice of `mindsos_core` means later phases will append (Phase 03 brings Graph/Node/Edge, Phase 05 brings Metagraph, etc.). Each append must update `mindsos_core/__init__.py` exports and `[tool.setuptools.packages.find] include` if a new sub-package is added.

  **Doc sections this phase confirms:**
    - `docs/concepts/identity.md` — full (matches the parent project's text; the IRI section explicitly notes IRI parsing is L2 / Phase 12).
    - `docs/api/core/identity-registry.md` — partial (intro slice + IdStrategy enumeration; full registry semantics in Phase 05 once Metagraph ships).
    - `docs/decisions/adr/0035-uuid-generation-non-deterministic.md` — confirmed against shipped behaviour.
    - `docs/decisions/adr/0131-pluggable-id-strategy.md` — confirmed against shipped behaviour.
    - `docs/dev/contributing.md` — adds Python ≥ 3.12 host requirement section (was implicit; now explicit per Phase 01 §10.3).
    - `docs/dev/conventions.md` — adds entrypoint rework note + sh-debug pattern.

  **Breaking changes from prior phase:**
    - **`docker compose run --rm mindsos <subcommand>`** is now the only form. The Phase 01 form `docker compose run --rm mindsos mindsos <subcommand>` is **broken** in Phase 02 — the compose entrypoint prepends `mindsos`, so the doubled invocation becomes `mindsos mindsos <subcommand>` to the binary, and Typer reads the second `mindsos` as a subcommand and fails with `No such command 'mindsos'`. Tester recipes carrying the doubled form forward from Phase 01 must be updated.
    - `mindsos confirm-phase --init-notes NN` is the new canonical shape; `--init-notes phase-NN` remains parse-accepted.
    - `mindsos doctor --self-test` now requires version-string parity. A checkout with mismatched `[mindsos] version` / `pyproject.toml` / `__init__.py:__version__` that passed self-test in Phase 01 will fail in Phase 02.

  **Phase 01 §6 deferral triage (decided in this phase):**
    - **ζ** (preflight self-test in confirm-phase) — **landed**.
    - **F** (init-notes vs --phase arg shape inconsistency) — **landed** (`--init-notes NN`, with `phase-NN` alias).
    - **ee** (Python ≥ 3.12 host requirement docs) — **landed** in `docs/dev/contributing.md`.
    - **gg** (φ-class image-completeness regression guard) — **landed** as `tests/phase_02/test_image_completeness.py`.
    - **η** (`--no-build` flag for `confirm-phase`) — **further deferred**. No friction observed yet; revisit if rebuild cost becomes load-bearing.
    - **H** (`_run_tests` 600s timeout configurability) — **further deferred**. No friction observed yet; revisit if a phase legitimately needs > 600s of test runtime.
    - **D** (cumulative `pytest tests/` runtime explosion) — remains targeted at ~Phase 14.

---

### Phase 03 — L1 Graph elements

  **Status:** Pending
  **Branch:** phase-03
  **Tag on confirm:** phase-03-confirmed
  **Depends on:** 02
  **Layer(s):** L1
  **Net-new code?:** **Yes (limited).** Repackages `mindsos_core/models/{graph,node,edge}.py` (note: `HyperEdge` lives in `edge.py` next to `Edge` in the parent project — there is no separate `hyperedge.py`) plus `mindsos_core/cypher/identifiers.py` (load-bearing for ADR-0021). Net-new beyond repackage: (1) `mindsos graph` Typer subcommand surface; (2) `mindsos_cli/state.py` — JSON state-file persistence at `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json` (parity with Phase 02 identity-registry pattern); (3) `tests/_shared/sentinel_paths.py` — extracts Phase 02's `_SENTINEL_PATHS` to a growing shared list every phase appends to (avoids per-phase duplication of the φ-class image-completeness test framework); (4) `mindsos_core/exceptions.py` extension with `SchemaError` + `CypherError` (the Schema *machinery* still defers to Phase 04; only the exception classes ship in 03 because `HyperEdge.__post_init__` and `validate_edge_type_identifier` raise them).

  **Slim-port deferral list (locked in this row so future phase chats don't re-discover):**
    - **`Schema` typing** + `validate_user_properties` / `validate_namespaced_properties` calls inside `Graph.add_*` → **Phase 04** (Schema). Phase 03 `add_*` methods take `properties` as a plain dict, no validation beyond `dict(...)` defensive copy.
    - **Graph-level `properties` bag** (ADR-0130, PHASE_MAP §7 Q4 unresolved) → **Phase 05 or 10** per the open question. Slim Phase 03 `Graph.__init__` drops the `properties` parameter entirely.
    - **`_version` field** on Node / Edge (ADR-0127 OCC) → **Phase 07**.
    - **`deprecated_at` / `disputed_at`** fields + `iter_edges(include_deprecated=...)` + `deprecate_edge` / `undeprecate_edge` / `dispute_edge` / `undispute_edge` (ADR-0133) → **Phase 10**. Datetime import drops from `edge.py` accordingly.
    - **`_restore_node` / `_restore_edge` / `_restore_hyperedge`** (private reconstruction helpers) → **Phase 08**. Phase 03 state-file rehydration uses the *public* `add_*(node_id=...)` / `add_edge(..., edge_id=...)` API instead.
    - **`update_node_properties` / `update_edge_properties`** → **Phase 04** (their guards depend on Schema validation; without it they're a thin `dict.update`). Omitted from Phase 03 entirely; tester rebuilds via `reset` + re-add.
    - **Pre-existing `tests/unit/test_graph.py`** (imports `Schema` / `NodeType` / `EdgeType` / `PropertyShapeError` / `UnknownTypeError`) → **Phase 04**, ported alongside Schema. Phase 03 ships only `tests/phase_03/`. The Phase 03 row's prior bullet "Pre-existing `tests/unit/test_graph.py` continues to pass" is **dropped**.
    - **ADR-0023 confirmation** (two-step writes merge-then-set) → **Phase 07** (the ADR is about Cypher write semantics; Phase 03 has zero Cypher writes). Removed from Phase 03's confirmed-doc list.

  **Features in scope (capability-level):**
    - `mindsos graph create --name <NAME> [--role ROLE]` — creates an empty Graph and writes the initial state file. Re-running with the same `--name` errors (use `reset` to clear). `--graph-id` is **not** exposed (reconstruction-only; Phase 08). `<NAME>` is validated against `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`; rejects with exit 2 + structured error otherwise (prevents accidental path traversal like `--name "foo/bar"` writing outside `$MINDSOS_STATE_DIR`).
    - `mindsos graph inspect --name <NAME>` — counts of nodes / edges / hyperedges + role + graph_id; `--json` for machine-readable. The "attached schema" bullet from the original row drops since Schema is Phase 04.
    - `mindsos graph add-node --name <NAME> <VALUE> --type <TYPE> [--prop k=v]... [--node-id IRI]` — `--node-id` is exposed for tester-driven IRI passthrough (parity with Phase 02 mint and required for the dup-id pass criterion). **`<VALUE>` parses with the same JSON-then-string-fallback rule as `--prop`:** try `json.loads(value)`; on `JSONDecodeError`, treat as literal string. So `add-node 42 ...` → int, `add-node '{"k":"v"}' ...` → dict, `add-node Alice ...` → string.
    - `mindsos graph add-edge --name <NAME> --source <ID> --target <ID> --type <REL_TYPE> [--label LABEL] [--prop k=v]... [--edge-id ID]` — `--type` is validated by `validate_edge_type_identifier` per ADR-0021.
    - `mindsos graph add-hyperedge --name <NAME> --member <ID> [--member <ID>]... [--label LABEL] [--prop k=v]... [--hyperedge-id ID]` — repeated singular `--member` flag (parity with Phase 02's `identity registry --register a --register b` pattern; better than comma-separated when ids contain commas or other special chars). Empty member set raises `SchemaError`; member ordering canonicalised by sorted `node_id` strings before serialization (exists-or-doesn't-exist tests rely on this).
    - `mindsos graph list-nodes / list-edges / list-hyperedges --name <NAME>` — `--json` aware.
    - `mindsos graph list` — enumerates every `graph-*.json` in `$MINDSOS_STATE_DIR`; reports name, role, graph_id, and counts per graph. `--json` aware. Useful tester-discovery surface (parity with the spirit of Phase 02's `identity registry --list`).
    - `mindsos graph reset --name <NAME> | --all` — deletes the named state file or every `graph-*.json` in `$MINDSOS_STATE_DIR`. Refuses with exit 2 if neither flag is given (explicit intent required; no accidental wipes). The original row's `mindsos doctor` warning option is **dropped** — `--reset` is the only mechanism.
    - `--prop k=v` JSON value parsing: try `json.loads(v)`; on `JSONDecodeError`, fall back to string. `--prop count=42` → int, `--prop tags='["a","b"]'` → list, `--prop active=true` → bool, `--prop name=Alice` → string. Tested.
    - Cross-invocation persistence: state file at `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json` (parity with Phase 02's identity-registry-`<scope>`.json). Each CLI invocation reloads, mutates, writes back. Same `compose run --rm` gotcha as Phase 02 — documented; mitigation = bind-mount or run from host venv.
    - Edge / HyperEdge serialization: store endpoints by `node_id` strings (`source_id`/`target_id` for Edge; sorted list of `member_ids` for HyperEdge). Rehydrate by lookup in the graph's `nodes` dict before constructing the Edge/HyperEdge object.

  **Modules touched:**
    - **Repackaged into `halvim_mindsos/`:** `mindsos_core/models/{graph,node,edge}.py` (HyperEdge ships in `edge.py` per parent layout); `mindsos_core/cypher/__init__.py` + `mindsos_core/cypher/identifiers.py` (new top-level subdirectory — must extend `[tool.setuptools.packages.find].include` with `mindsos_core.cypher` per Phase 02 §3.2 lesson). All imports stripped per the deferral list above.
    - **Edited:** `mindsos_core/exceptions.py` (add `SchemaError`, `CypherError`); `mindsos_core/__init__.py` (export `Graph`, `Node`, `Edge`, `HyperEdge`, `SchemaError`, `CypherError`, `validate_edge_type_identifier`, `validate_label_identifier`); `mindsos_core/models/__init__.py` (re-export the new model classes for ergonomics).
    - **New:** `mindsos_cli/commands/graph.py` — Typer subcommand group with `register_graph_app(app)` (parity with Phase 02's `register_identity_app`); wired into `mindsos_cli/app.py`. `mindsos_cli/state.py` — pure-function (de)serialization helpers (`load_graph_state`, `save_graph_state`, `state_file_path`, `iter_state_files`, `delete_state_file`).
    - **New shared test infrastructure:** `tests/_shared/__init__.py`, `tests/_shared/sentinel_paths.py` — module exposes `SENTINEL_PATHS: list[Path]` (cumulative across phases). Phase 02's existing `tests/phase_02/test_image_completeness.py` migrates to import from the shared module; the test continues to live in `tests/phase_02/` (file boundary preserved per "phase tests live in `tests/phase_NN/`" rule); Phase 03 adds an extension parametrised over the new entries.
    - **Edited (per-phase ritual):** `docker-compose.yml` (image tags `phase02-*` → `phase03-*`); `mindsos_cli/manifest.toml` (`[mindsos] phase` + `version`); `pyproject.toml` (`[project] version` + `description` only — `[tool.setuptools.packages.find].include` already uses `mindsos_core*` wildcard which auto-covers the new `mindsos_core.cypher` subpackage; no edit needed); `mindsos_cli/__init__.py` (`__version__`); `mkdocs.yml` — **`Usage` is a brand-new top-level nav section, inserted between `Concepts` and `API`**; sub-section `Core` containing `Building graphs`. Concepts gets `Graphs and metagraphs`. API > Core gets `Graph`, `Node`, `Edge`, `HyperEdge`. New top-level `Changelog` section appended last with `CHANGELOG.md` entry. Phase 04+ append Usage leaves (Schema, Persistence, etc.) and a `Knowledge` sub-section in their own time.
    - **Unchanged:** `requirements.in` / `requirements.txt` (no new runtime deps — Phase 03's graph primitives are stdlib-only). `requirements_txt_sha256` field in `manifest.toml` therefore stays put. Same for `requirements-test.txt` (no new test deps).
    - **Dockerfile:** verifying COPY of `mindsos_core/cypher/` is covered by the existing `COPY mindsos_core` in both prod + test stages (Phase 02 already copies `mindsos_core` wholesale); the image-completeness sentinel-list extension catches drift if a future Dockerfile edit fragments the COPY.

  **Automated tests (location + intent):**
    - `tests/phase_03/test_graph_create.py` — Graph creation; default UUID4 graph_id; `--role` round-trip; second `create` with same `--name` errors with structured `IdentityError`-style diagnostic.
    - `tests/phase_03/test_graph_inspect.py` — counts after CRUD; `--json` shape stable.
    - `tests/phase_03/test_graph_add_node.py` — happy path; explicit `--node-id`; duplicate explicit `--node-id` exits 1 with `IdentityError`; `--prop` JSON parsing across int / list / bool / string-fallback.
    - `tests/phase_03/test_graph_add_edge.py` — happy path; missing source / target → `IdentityError` exit 1; lowercase rel-type (`works_at`) → `CypherError` exit 1 (ADR-0021); `--edge-id` explicit.
    - `tests/phase_03/test_graph_add_hyperedge.py` — N-member happy path; empty `--members` → `SchemaError` exit 1; member ordering canonicalised by sorted `node_id` (assert state file's `member_ids` is sorted regardless of input order); `--hyperedge-id` explicit.
    - `tests/phase_03/test_graph_reset.py` — `--name` deletes the named file; `--all` deletes every `graph-*.json` under `$MINDSOS_STATE_DIR`; neither → exit 2 with usage error.
    - `tests/phase_03/test_graph_state_persistence.py` — round-trip across multiple subprocess invocations (mocked via `MINDSOS_STATE_DIR=tmp_path`); load → mutate → save → reload yields identical state.
    - `tests/phase_03/test_graph_cypher_validation.py` — direct unit tests of `validate_edge_type_identifier` / `validate_label_identifier` (cypher safety regex coverage).
    - `tests/phase_03/test_image_completeness_phase03.py` — parametrised over the *Phase 03 additions* to `SENTINEL_PATHS` (`mindsos_core/models/{graph,node,edge}.py`, `mindsos_core/cypher/__init__.py`, `mindsos_core/cypher/identifiers.py`).
    - `tests/phase_03/conftest.py` — imports `_run_cli` from `tests/_shared/cli.py` (extracted in this phase per appendix #7). Adds an **autouse fixture** that sets `MINDSOS_STATE_DIR` to `tmp_path` (function-scoped) for every test in the package — prevents leakage between developer's actual `~/.mindsos/graph-*.json` files and test runs. ~5 LOC fixture.
    - **Phase-agnostic test pattern** (Phase 02 §3.13): any test that needs "what phase am I" reads `[mindsos] phase` from `manifest.toml` at runtime; canonical helper at `tests/phase_01/test_confirm_phase.py:_current_phase`.

  **Confirmation command:**
    `mindsos confirm-phase --phase 03 --notes-file notes-phase-03.md`

  **Pass criterion:**
    - Tester builds a small graph (≥ 3 nodes, ≥ 2 edges, ≥ 1 hyperedge) incrementally across multiple `mindsos graph add-*` invocations, then `inspect` reports the expected counts. (Multi-invocation works from host venv where `--rm` doesn't destroy the state file; documented compose `--rm` gotcha.)
    - Adding a duplicate node id (explicit `--node-id`) exits non-zero with structured `IdentityError`.
    - Adding an edge with an invalid Cypher rel-type (e.g. lowercase `--type works_at`) exits non-zero with structured `CypherError` per ADR-0021.
    - `mindsos graph reset --name <NAME>` clears state; subsequent `inspect` reports node/edge/hyperedge counts of zero (or "graph not found", phase chat picks consistent semantics during impl).
    - `mindsos graph reset` (no flag) exits 2 with a usage error.
    - All Phase 03 + Phase 02 + Phase 01 + Phase 00 tests pass cumulatively in-container. Expected count: prior 108 + Phase 03 ~30 = ~138 + 1 skipped (`test_mkdocs_buildable.py`).

  **Risks / known issues to watch:**
    - **State-file leak between independent test runs** — mitigated via `MINDSOS_STATE_DIR=tmp_path` env override in `tests/phase_03/conftest.py` + tester's `reset --name | --all`. The original "doctor warning" risk-line is dropped; `--reset` is the only mechanism.
    - **HyperEdge member canonicalisation** — sorted `node_id` list locked in both `add_hyperedge` (in-memory) AND state-file (de)serializer; both paths tested; existence test (`is hyperedge {a,b,c} present?`) is sort-invariant by construction.
    - **`--prop k=v` JSON parsing edge cases** — `--prop name=Alice` parses as string (json.loads fails on bare `Alice`), `--prop count=42` parses as int, `--prop active=true` parses as bool. The fall-back rule must NOT swallow malformed JSON like `--prop tags='[bad'` — that should error with a clear message, not silently become the literal string. Phase chat to decide where to draw the line; tested either way.
    - **Compose `--rm` gotcha** — same as Phase 02 identity registry. Tester recipes: persistent demos run from host venv (`pip install -e .` per Phase 02 §8 step 9) OR via bind-mount (`-v ~/.mindsos:/root/.mindsos`); single-invocation demos use chained flags within one `compose run`.
    - **Slim-port stripping is a real diff vs parent** (per the deferral list above). Phase 04+ chats must re-add the deferred surface as their feature rolls in. The deferral list is the contract.

  **Doc sections this phase confirms:**
    - `docs/concepts/graphs-and-metagraphs.md` — **(new, partial)** — Graph + atomic elements; metagraph framing held for Phase 05.
    - `docs/usage/core/building-graphs.md` — **(new, full)**.
    - `docs/api/core/graph.md` — **(new, full)**.
    - `docs/api/core/node.md` — **(new, full)**.
    - `docs/api/core/edge.md` — **(new, full)**.
    - `docs/api/core/hyperedge.md` — **(new, full)** — keeps its own page even though `HyperEdge` ships in `edge.py` (doc/code boundary intentionally diverges for reader ergonomics).
    - `docs/changelog/CHANGELOG.md` — **(new)** — single append-only file per PHASE_MAP §6 ("each phase appends a 'Phase NN' line; final pass at 38"). Phase 03 creates the file and **backfills** Phase 00 / 01 / 02 entries (3 lines, derived from each phase's CONFIRMED doc title) + appends the Phase 03 entry. Phase 04+ append one line each.
    - **ADR-0014** (layer boundary core-only) — **(referenced; ADR file not yet ported to slim repo — confirmed against shipped behaviour only; ADR text remains in parent project pending Phase 38 consolidation)**.
    - **ADR-0021** (cypher rel-type validation) — **(referenced; ADR file not yet ported to slim repo — confirmed against shipped behaviour only)** — load-bearing for the invalid-rel-type pass criterion.
    - **ADR-0023** (two-step writes merge-then-set) — **slipped to Phase 07** (Cypher writes ship there; nothing in Phase 03 to validate against).

  **Breaking changes from prior phase:**
    - **`mindsos_core` exports grow** — `Graph`, `Node`, `Edge`, `HyperEdge`, `SchemaError`, `CypherError`, `validate_edge_type_identifier`, `validate_label_identifier` added to `__all__`. Code importing the *parent* project's full `mindsos_core` and relying on `Graph.properties`, `Node._version`, `Edge.deprecated_at` / `disputed_at`, `Graph._restore_*`, or `Graph.update_*_properties` will not find them in the slim Phase 03 surface — those land in their respective later phases per the deferral list. Document in `docs/changelog/phase-03.md`.
    - **State-file conventions:** `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json`. Tester must `mindsos graph reset --name <NAME>` (or `--all`) between independent runs.
    - **`tests/_shared/`** is now part of the test layout. Phase 04+ contributing to `SENTINEL_PATHS` extend the list there, not in `tests/phase_NN/test_image_completeness.py`.

  **Final amendments (locked in this Phase 03 chat, 2026-05-04 — 15 items):**
    1. **Cumulative test count baseline corrected.** Phase 02 tester-measured `117 + 1 skipped` is canonical (PHASE_02_CONFIRMED.md line 49) — not the `108` in PHASE_02_IMPLEMENTATION_LOG §6 (under-count: the impl log treated parametrised cases as 1 entry each). Phase 03 expected: **117 + ~34 in `tests/phase_03/` + 5 new sentinels at `tests/test_image_completeness.py` + ~6 in `tests/phase_03/test_state.py` + 1 in `tests/phase_03/test_graph_list.py` ≈ ~163 + 1 skipped.** **In-process / subprocess split (parity with Phase 02):** Mac dev sandbox runs in-process tests via `typer.testing.CliRunner`; ~6–8 subprocess CLI tests skip on Mac (Python 3.10 sandbox can't `pip install -e .` against `requires-python = ">=3.12"`) and run only in the test image. All ~163 pass in-container.
    2. **`inspect` / `add-*` against a missing state file** → exit 1 with structured error: `Graph '<name>' not found at <path>; create it first with 'mindsos graph create --name <name>'`.
    3. **Malformed `--prop` JSON value** (e.g. `--prop tags='[bad'`) → falls back to literal string `[bad`. Document as known limitation in `building-graphs.md`. Simplest rule wins: `try json.loads(v); except JSONDecodeError: v = literal_string`.
    4. **State-file schema versioning.** Top-level JSON object includes `"_state_version": 1`. Phase 07+ may bump on shape change; loaders gate on it. Cheap insurance now, expensive retrofit later.
    5. **State-file atomic write.** Write to `<path>.tmp` then `os.replace(<path>.tmp, <path>)`. Mid-write Ctrl-C cannot corrupt the canonical file. ~3 lines in `mindsos_cli/state.py:save_graph_state`.
    6. **Image-completeness test relocates** to `tests/test_image_completeness.py` (root, single parametrised test over the cumulative `SENTINEL_PATHS` list). `tests/phase_02/test_image_completeness.py` is **removed** in the Phase 03 commit. Mutating an already-tagged Phase 02 file is the normal cross-phase refactor pattern; the `phase-02-confirmed` tag stays pointing at history.
    7. **`_run_cli` env-merge helper extracts** from `tests/phase_02/conftest.py` to `tests/_shared/cli.py`. Both Phase 02 and Phase 03 conftests import directly from shared (`from tests._shared.cli import _run_cli`); the leading-underscore signals private convention so no re-export shim needed. The Phase 02 conftest's existing function definition is replaced by the import line.
    8. **`mindsos_core/__init__.py:__all__` Phase 03 additions explicit.** 8 new entries: `"SchemaError"`, `"CypherError"`, `"Graph"`, `"Node"`, `"Edge"`, `"HyperEdge"`, `"validate_edge_type_identifier"`, `"validate_label_identifier"`. Cumulative total: 17.
    9. **`mindsos graph create --name <NAME>` over an existing state file** → raises **`IdentityError`** (reusing the existing exception class — no new `StateError` class) with message: `Graph '<NAME>' already exists at <path>; use 'mindsos graph reset --name <NAME>' to clear.` CLI exits 1.
    10. **HyperEdge state-file canonicalisation rule pinned exactly:** `member_ids = sorted(node.node_id for node in he.nodes)`. In-memory `he.nodes` remains `Set[Node]` (unchanged from parent). Two state files of the same hyperedges produce byte-identical JSON modulo property-dict ordering.
    11. **`--prop k=v` parsing.** Split on first `=` only (`k, v = arg.split("=", 1)`). Empty key → exit 2 with usage error. Empty value (`--prop k=`) → empty-string property (json.loads("") raises → fall-back yields `""`).
    12. **NEW — `tests/phase_03/test_state.py`** adds direct unit tests of `mindsos_cli/state.py` functions (`load_graph_state`, `save_graph_state`, `state_file_path`, `iter_state_files`, `delete_state_file`, atomic-write contract, corrupt-file handling). ~6 tests. Cheaper to debug pure-function failures than subprocess-CLI failures. Folded into the count above.
    13. **NEW — `mindsos_cli/state.py` errors are plain Python exceptions.** Corruption raises `RuntimeError`; missing file lets `FileNotFoundError` propagate. The CLI command layer wraps with `typer.Exit(1)` + stderr structured message. **No new `StateError` class** in `mindsos_core.exceptions` — keeps the exception hierarchy aligned with Phase 02's "CoreError → IdentityError" tightness, plus only the two new domain classes (`SchemaError`, `CypherError`) ride in.
    14. **NEW — Concurrent `mindsos graph add-*` race documented as known issue.** Two simultaneous CLI invocations against the same state file race (no advisory lock). Phase 02 J-02 deferral rationale carries forward: acceptable, debug-only, single-tester surface. Phase 07's persistence layer ships proper concurrency control. Added to "Risks / known issues to watch."
    15. **NEW — `Dockerfile` comment update.** Lines 70–71 and 101–103 reference `tests/phase_02/test_image_completeness.py` as the sentinel-list owner. Phase 03 amends both COPY-block comments to point at `tests/test_image_completeness.py` + `tests/_shared/sentinel_paths.py`. Trivially small but failure-mode-relevant: comments mislead future debuggers if not updated.
    16. **NEW — Docstring updates in slim `mindsos_core`.** `mindsos_core/__init__.py:1` ("MindsOS Core Layer — slim Phase 02 surface"), `mindsos_core/exceptions.py:1` ("Phase 02 slim"), `mindsos_core/models/__init__.py:1` ("Phase 02 ships only identity primitives") all reference Phase 02 in their opening docstrings. Phase 03 ritual updates each to a Phase 03-aware text describing the expanded surface (identity + graph elements + cypher safety) and the deferral list above. Implementation-time edit; verified during `mindsos doctor --self-test` only insofar as `__version__` parity is checked (docstrings are not lint-gated).
    17. **NEW — Phase 01/02 deferral carry-forward.** `η` (`--no-build` flag for `confirm-phase`), `H` (`_run_tests` 600s timeout configurability), `D` (cumulative `pytest tests/` runtime explosion targeted at ~Phase 14) — **all three remain deferred in Phase 03.** No friction observed yet; revisit if a Phase 03+ rebuild cost or test runtime becomes load-bearing. `J-02` and `K-02` (identity-registry concurrency / gitignore) — Phase 03 graph state-file inherits both deferrals (acceptable: debug-only, single-tester surface).
    18. **NEW — `mindsos graph list` discovery subcommand.** Enumerates `${MINDSOS_STATE_DIR}/graph-*.json`; reports name + role + graph_id + counts per graph; `--json` aware. ~15 LOC + 1 test. Tester-discovery surface; parity with the spirit of Phase 02's `identity registry --list`. Folded into the test count above.
    19. **NEW — CLI exit code policy (locked, parity with Phase 02).** Exit `1` for domain errors (`IdentityError`, `SchemaError`, `CypherError`, malformed state file diagnosed via `RuntimeError`). Exit `2` for usage errors (missing required arg, malformed flag, empty `--prop` key, `reset` with neither `--name` nor `--all`, `--seed` JSON parse failure). Phase 02's `mindsos identity` CLI already follows this; Phase 03 graph CLI conforms.
    20. **NEW — Doc inventory: every Phase 03 doc page is a NEW file.** None exist in the slim repo today (verified). `(new)` / `(amend)` markers added to the "Doc sections this phase confirms" list above for clarity at the Phase 38 final-pass review.
    21. **NEW — `mkdocs.yml` nav entries.** Phase 02 added Concepts + API entries for identity. Phase 03 appends nav entries under Concepts (`graphs-and-metagraphs`), Usage / Core (`building-graphs`), API / Core (`graph`, `node`, `edge`, `hyperedge`), and a Changelog section if not yet present (`phase-03`). Folded into "Modules touched > Edited (per-phase ritual)" above.
    22. **NEW — `requirements.in` / `requirements.txt` / `requirements-test.txt` unchanged.** Phase 03's graph primitives + state-file (de)serialization use only stdlib (`json`, `os`, `pathlib`). `manifest.toml`'s `requirements_txt_sha256` therefore stays put — `doctor --self-test` lockfile drift check unaffected.
    23. **NEW — `mindsos_core/cypher/__init__.py` exports match parent's identifier-only set.** Phase 03 ships: `EDGE_TYPE_IDENTIFIER_RE`, `validate_edge_type_identifier`, `validate_label_identifier`. `LABEL_IDENTIFIER_RE` is **defined but NOT in `__all__`** (matches parent `mindsos_core/cypher/__init__.py` exactly). Builders (`build_create_node`, `build_create_edge`, etc.) ship in **Phase 11**; Phase 03's `cypher/__init__.py` imports only from `identifiers.py`. The slim cypher package has no `builders.py` file in Phase 03.
    24. **NEW — Small in-row locks folded silently (no separate adjudication; pinned for impl-time clarity):**
        - `mindsos_cli/state.py:state_file_path(name)` does the **`<name>` regex validation centrally** (raises `ValueError` if `name` violates `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`). CLI layer catches and exits 2. Avoids duplicating the regex check at every call site (CLI, future Phase 07 importers, tests).
        - `mindsos graph list` output is **sorted by name** for deterministic CI / golden-output diffs.
        - **Cypher rel-type rejection covers both lowercase AND mixed-case** (`works_at`, `Works_At`, `WORKS_at` — all rejected per the strict-uppercase regex `^[A-Z][A-Z0-9_]{0,63}$`). The pass-criterion test in `tests/phase_03/test_graph_cypher_validation.py` parametrises over all three.
        - **`mindsos_cli/state.py` function signatures pinned:**
            - `state_dir() -> Path`
            - `state_file_path(name: str) -> Path` (validates name)
            - `load_graph_state(name: str) -> dict`
            - `save_graph_state(name: str, state: dict) -> None` (atomic via `<path>.tmp` + `os.replace`)
            - `iter_state_files() -> Iterator[Path]`
            - `delete_state_file(name: str) -> None`
          All consume / return primitives + `Path` + plain `dict`; **no `Graph`-typed I/O at this layer** — the CLI command layer does the `Graph` ↔ `dict` (de)serialization. Keeps `mindsos_cli/state.py` pure-function and easy to unit-test directly (per `tests/phase_03/test_state.py` in appendix #12).
        - **`pyproject.toml [tool.setuptools.packages.find].include` already uses `mindsos_core*` wildcard** (verified 2026-05-04 in this Phase 03 chat) — no edit needed for the new `mindsos_core.cypher` subpackage; auto-covered. Reverses the earlier appendix #2 / "Edited" claim that pyproject needs editing for the package include.
    25. **NEW — `Graph` slim-port method inventory (explicit, locks the strip).** The slim Phase 03 `mindsos_core/models/graph.py` ships exactly:
        - `__init__(name, *, role=None, graph_id=None, identity=None) -> None` — drops `schema`, `properties` params.
        - `add_node(value, type_name, *, properties=None, node_id=None) -> Node` — no schema validation; `properties` is a defensive `dict(properties or {})`.
        - `add_edge(source, target, type_name, *, label=None, properties=None, edge_id=None) -> Edge` — calls `validate_edge_type_identifier(type_name)` (ADR-0021); no schema validation of source/target types.
        - `add_hyperedge(nodes, *, label=None, properties=None, edge_id=None) -> HyperEdge` — empty members → `SchemaError` (via `HyperEdge.__post_init__`).
        - `remove_node(node_id, *, cascade=True) -> None`
        - `remove_edge(edge_id) -> None`
        - `remove_hyperedge(edge_id) -> None`
        - `__repr__`
        
        **Dropped from parent's graph.py (per deferral list):** `iter_edges` / `iter_hyperedges` / `get_edges_for_node` (Phase 10 — soft-delete iterators); `deprecate_edge` / `undeprecate_edge` / `dispute_edge` / `undispute_edge` (Phase 10); `update_node_properties` / `update_edge_properties` (Phase 04); `_restore_node` / `_restore_edge` / `_restore_hyperedge` (Phase 08); `_validated_node_properties` / `_validated_edge_properties` (Phase 04 — schema-aware property validation).
    26. **NEW — Slim-port dataclass field strips (explicit):**
        - `Node` keeps: `value`, `type_name`, `node_id`, `properties`. **Drops** `_version` (ADR-0127 OCC, Phase 07).
        - `Edge` keeps: `source`, `target`, `type_name`, `label`, `edge_id`, `properties`. **Drops** `deprecated_at`, `disputed_at` (ADR-0133, Phase 10) → also drops `from datetime import datetime` import.
        - `HyperEdge` keeps: `nodes`, `label`, `edge_id`, `properties`. **Drops** `deprecated_at`, `disputed_at`.
    27. **NEW — `_state_version` contract on load (forward + backward compat).** `load_graph_state` enforces:
        - **Future versions rejected:** if `_state_version > 1` → raise `RuntimeError("State file <path> has _state_version=<N>; this CLI supports v1. Run a newer mindsos to read this file.")`. CLI exits 1.
        - **Missing field rejected:** if `_state_version` key is absent → raise `RuntimeError("State file <path> missing required field '_state_version'.")`. CLI exits 1. (Strict — lenient handling encourages drift across phases.)
        - **Equal version (v1) accepted:** normal load path.
        Phase 07+ may bump `_state_version` and add backward-compat read paths there; Phase 03 sets the strict contract so future phase chats inherit explicit version awareness.
    28. **NEW — State-file list ordering pinned for byte-stable output.** All three top-level arrays sorted by id before serialization:
        - `nodes` sorted by `node_id`
        - `edges` sorted by `edge_id`
        - `hyperedges` sorted by `edge_id` (members within each hyperedge already sorted by `node_id` per item #10).
        Same rule applied to CLI list output: `mindsos graph list-nodes / list-edges / list-hyperedges` sort by id (matches state-file order; deterministic for golden-diff CI). Reduces noise in tester's `cat <state-file>` inspections; insertion-order changes don't break diffs without semantic change.
    29. **NEW — State-file JSON v1 schema pinned (avoids Phase 07+ drift).**
        ```json
        {
          "_state_version": 1,
          "graph_id": "<uuid4>",
          "name": "<name>",
          "role": "<role-or-null>",
          "nodes": [
            {"node_id": "<id>", "value": <any-json>, "type_name": "<type>", "properties": {}}
          ],
          "edges": [
            {"edge_id": "<id>", "source_id": "<node-id>", "target_id": "<node-id>",
             "type_name": "<type>", "label": "<label-or-null>", "properties": {}}
          ],
          "hyperedges": [
            {"edge_id": "<id>", "member_ids": ["<sorted-node-id>", ...],
             "label": "<label-or-null>", "properties": {}}
          ]
        }
        ```
        `member_ids` is always sorted (item #10). `value` is any JSON type per item #m above. Phase 07+ may bump `_state_version` if shape changes; loaders gate on it (item #4).

---

## 5. Phases 04–38 — skeleton rows

Each row is intentionally terse. The phase chat reads it, refines its scope, and updates the row before implementing.

### Phase 04 — L1 Schema (NodeType, EdgeType, opt-in strict)

  **Deps:** 02, 03. **Layer:** L1. **Net-new?** Repackage; **schema state-file format is genuinely net-new** (parent has no equivalent), inherited via Phase 03 state.py precedent. Plus three net-new CLI commands (`schema create/...`, `graph attach-schema`, `graph detach-schema`, `graph set-prop`) that are pure Phase 04 surface — no parent code to repackage.
  **Foundations-first note:** Original PHASE_MAP §3 listed deps as `02` per foundations-first rule (Schema is a sibling primitive). Refined to `02, 03` because Phase 04 closes 4 entries from the Phase 03 deferral appendix (Schema typing on `Graph.__init__`, `validate_user_properties` helper, `update_*_properties`, `tests/unit/test_graph.py` port) AND adds `schema_name` reference to the graph state file — both transitively depend on Phase 03 having shipped. Phase 03 shipped first only for tester-flow continuity.

  **Features (capability-level — phase chat refined 2026-05-04, locked across 5 design rounds):**
    - Declare a `Schema` (`mindsos schema create --name X [--strict]`).
    - Declare `NodeType` / `EdgeType` with the full 8-variant `PropertyType` vocabulary (STRING / INT / FLOAT / BOOL / LIST_STRING / LIST_INT / LIST_FLOAT / LIST_BOOL).
    - Inspect / list / reset schemas (parity with Phase 03 graph subcommands).
      `reset --name X` and `reset --all` BOTH walk every `graph-*.json` and refuse with exit 1 if any graph references a schema being deleted; `--force` overrides (resulting graphs need `mindsos graph detach-schema` to recover).
    - Attach a schema to an existing graph (`mindsos graph attach-schema --name <GRAPH> --schema <SCHEMA>`); also attachable at create time (`mindsos graph create --name X --role ontology --schema <SCHEMA>`).
    - **Eager attach validation** — every existing node + edge re-validated against the schema; first violation prints structured error including the offending element id + exits 1 (no `--force` escape hatch). **Re-attach is permitted** — JSON output includes `previous_schema`; new schema replaces old after eager re-validation.
    - **Empty-strict-schema warning** — attaching a strict schema with zero NodeTypes emits a stderr warning (the graph cannot accept any further node adds).
    - Detach schema from a graph (`mindsos graph detach-schema --name <GRAPH>`). Operates on raw JSON — works EVEN WHEN the referenced schema state file has been deleted (primary recovery path for dangling references). Exits 1 if no schema currently attached.
    - Schema-validated property updates (`mindsos graph set-prop --name <GRAPH> (--node-id ID | --edge-id ID) --prop k=v [--prop k2=v2 ...] [--replace]`).
      Default merge; `--replace` swaps the bag entirely BUT preserves `ref:*` cross-graph reference keys (user-supplied `ref:*` values overwrite existing on collision). NOTE: Phase 04 has NO CLI path to drop a `ref:*` key — recovery via hand-edit, or future Phase 09 XRef migration.
    - All existing `add-node` / `add-edge` flows route through schema validation when a schema is attached (transparent, no opt-in).

  **Modules touched:**
    - `mindsos_core/schema/{__init__,types,schema,validation}.py` — slim port of parent (defer `validate_namespaced_properties` to Phase 05/10).
    - `mindsos_core/exceptions.py` — adds `PropertyShapeError`, `UnknownTypeError` (both inherit `CoreError`).
    - `mindsos_core/__init__.py` — exports `Schema`, `NodeType`, `EdgeType`, `PropertyType`, `PropertyShapeError`, `UnknownTypeError`, `validate_user_properties`, `RESERVED_PROPERTY_KEYS`, `REF_PROPERTY_PREFIX` (~9 new names; cumulative ~26).
    - `mindsos_core/models/graph.py` — restores `schema: Optional[Schema] = None` ctor param + per-add validation hooks; adds `update_node_properties` / `update_edge_properties` (no `_version` bump — Phase 07 OCC ships that). Adds `_validate: bool = True` kwarg to `add_node` / `add_edge` / `add_hyperedge`; rehydration uses `_validate=False` to tolerate Phase 03 v=1 state files with reserved-key or non-primitive properties (Phase 03 had no `validate_user_properties` enforcement). Schema-level checks (type registration, strict PropertyType maps) ALWAYS run regardless.
    - `mindsos_cli/commands/schema.py` — new Typer subapp; `_state_to_schema` wraps `PropertyType(v)` in try/except → RuntimeError (corrupt vocab UX); `reset_cmd` adds orphan check + `--force` flag.
    - `mindsos_cli/commands/graph.py` — extends with `attach-schema`, `detach-schema`, `set-prop`, `--schema` flag on `create`. `_graph_to_state` writes v=2; `_state_to_graph` calls `add_*` with `_validate=False`. `attach-schema` per-element try/except → element id in error message; allows re-attach with `previous_schema` in JSON; empty-strict-schema warning. `set-prop` flag rename `--node` → `--node-id` / `--edge` → `--edge-id`; `--replace` preserves `ref:*` keys (user values win on collision). `detach-schema` operates on raw JSON dict (bypasses `_state_to_graph` so it works on dangling references).
    - `mindsos_cli/state.py` — adds `schema_file_path` / `save_schema_state` / `load_schema_state` / `iter_schema_files` / `delete_schema_state_file`. **Bumps graph state-file format from v=1 to v=2** (adds optional `schema_name` field). Splits version constants per-kind: `GRAPH_STATE_VERSION = 2`, `SCHEMA_STATE_VERSION = 1`; `STATE_VERSION` kept as backward-compat alias = `GRAPH_STATE_VERSION`. `_load_state_file` accepts `max_version` kwarg. v=1 → v=2 migration is one-way: first Phase 04 mutation upgrades the file; Phase 03 binary then refuses with the existing strict-version contract.
    - `mindsos_cli/app.py` — `register_schema_app` wired.
    - `Dockerfile` — prod + test stages COPY `mindsos_core/schema/` + `mindsos_cli/commands/schema.py`.
    - `tests/_shared/sentinel_paths.py` — `+5` entries.

  **Persistence layout:**
    - `${MINDSOS_STATE_DIR}/schema-<name>.json` (own state file, parity with `graph-<name>.json` / `identity-registry-<name>.json`).
    - Schema state-file v=1 JSON shape (`SCHEMA_STATE_VERSION = 1`):
      ```json
      {"_state_version": 1, "name": "<n>", "strict": false,
       "node_types": [{"name", "property_types": {"k": "<PropertyType.value>"}, "description"}],
       "edge_types": [{"name", "allowed_sources": [...sorted], "allowed_targets": [...sorted],
                       "property_types": {"k": "<PropertyType.value>"}, "description"}]}
      ```
      Top-level lists sorted by name (byte-stable); atomic write via `<path>.tmp` + `os.replace`.
    - **Graph state-file v=2 JSON shape (`GRAPH_STATE_VERSION = 2` — Phase 04 BUMP from v=1):**
      ```json
      {"_state_version": 2,
       "graph_id": "<uuid4>", "name": "<n>", "role": "<role-or-null>",
       "schema_name": "<schema-name-or-null>",
       "nodes": [...], "edges": [...], "hyperedges": [...]}
      ```
      Phase 04 binary accepts both v=1 (legacy, no `schema_name` field — loader treats missing as `null`) and v=2 (current); writes v=2 on every save. **v=1 → v=2 migration is one-way**: first Phase 04 mutation upgrades the file; Phase 03 binary then refuses with the existing strict-version contract.
    - Graph state-file `schema_name` field: when set, loader resolves to `schema-<name>.json` and rebuilds the Schema in memory. Missing referenced schema → standard load fails (exit 1); recovery via `mindsos graph detach-schema` (raw-JSON path bypasses schema rehydration).

  **Automated tests (location + intent):**
    - `tests/phase_04/` — schema CRUD; eager attach validation against pre-existing nodes; set-prop merge / replace; strict-mode property type matching across all 8 variants; non-strict mode permits any primitive; edge with disallowed source/target type rejected; schema state-file round-trip; graph state-file `schema_name` round-trip.
    - `tests/unit/test_graph.py` — ported back from parent (14 of 15 tests; `test_restore_node_registers_provided_id` ships with `@pytest.mark.skip(reason="_restore_node lands in Phase 08")`).

  **Pass criterion:**
    - Tester can declare a strict schema, attach it to a graph with existing data — first violation rejects (exit 1, structured error including the offending element id); clean data attaches successfully.
    - `mindsos graph set-prop` round-trips through schema validation (rejects type mismatches under strict mode).
    - `mindsos graph detach-schema` recovers a graph from a deleted-schema dangling reference.
    - `mindsos schema reset --name X` refuses with exit 1 when graphs reference X; `--force` overrides.
    - All 8 PropertyType variants round-trip in strict mode.
    - **Cumulative tests pass: ≥ Phase 03 baseline (189 passed + 1 skipped) + Phase 04 added test files; tester records the post-collection actual count in `PHASE_04_CONFIRMED.md` `tester_notes` (sandbox-measured: 380 collected, 339 in-process pass + 40 subprocess fail-on-3.10 + 1 skipped + 1 redis collection error → expected in-container 379 passed + 2 skipped, where the 2 skips are existing `test_mkdocs_buildable.py` and new `test_restore_node_registers_provided_id`).

  **Risks / known issues to watch:**
    - Schema state-file persistence is net-new design (parent has no analogue). Phase 04 accepts the precedent set by Phase 03 (state.py), but later phases (Phase 07 real persistence) will need to migrate or supersede this format.
    - **v=1 → v=2 graph state-file migration is one-way.** Phase 04 binary touching a Phase 03 v=1 file upgrades it to v=2 on first mutation; Phase 03 binary then refuses to read it (strict-version contract). Phase 04 supersession requires `rm -rf ~/.mindsos/graph-*.json` OR manual JSON downgrade (`_state_version: 1`, drop `schema_name`); recovery procedure documented in `docs/usage/core/schema.md` Migration section.
    - **Phase 03 v=1 graphs with reserved-key or non-primitive properties tolerated on load.** Phase 03 had no `validate_user_properties` enforcement, so a Phase 03 graph could contain `{"id": "evil"}` etc. Phase 04 rehydration uses `_validate=False` to load such graphs cleanly. **Mutations on those properties surface the violation** (default merge fails because `validate_user_properties` runs on the full merged candidate); recovery via `set-prop --replace`, which strips reserved keys via the validated candidate bag (and preserves `ref:*` keys).
    - **`set-prop --replace` cannot drop `ref:*` keys.** Pick D unconditionally preserves them across replace. If a tester needs to drop a ref, recovery is via hand-edit OR future Phase 09 XRef migration. Documented asymmetry; refs are linkage metadata with semantic significance — making them harder to drop is a feature.
    - Eager attach validation crosses CLI/persistence boundaries: a schema attach that succeeds on a fresh graph but fails after a hand-edit of the graph state file could leave the graph state file with a stale `schema_name`. Acceptable: hand-edits are out-of-contract. Recovery via `mindsos graph detach-schema` (raw-JSON path).
    - `update_node_properties` does NOT bump `_version` (Phase 07 OCC owns that). The Phase 04 tests must NOT assert any version field on Node — preserves Phase 03 slim-port (Node has no `_version`).
    - **Empty strict schema attached to a graph rejects all subsequent `add-node` calls** (because `Schema.require_node_type` fails for any type_name). Phase 04 emits a stderr warning at attach time when the schema is strict AND has zero NodeTypes; the docs cover the footgun.

  **Doc sections this phase confirms:**
    - `docs/usage/core/schema.md` — full (NEW).
    - `docs/api/core/schema.md` — full (NEW).
    - `docs/api/core/types.md` — full (NEW; covers `NodeType` / `EdgeType` / `PropertyType`).
    - `docs/usage/core/building-graphs.md` — amended with schema attach / set-prop section.
    - `docs/changelog/CHANGELOG.md` — Phase 04 entry appended.
    - ADR-0017 — referenced by number; ADR file ports in Phase 38 (locked precedent).

  **Breaking changes from prior phase:**
    - `Graph.__init__` regains `schema` keyword param. Existing callers pass nothing → backward-compatible default `None` (non-strict, no validation hooks). No CLI breakage.

  **Final amendments (2026-05-04 — phase chat locks across 5 design rounds):**
    1. Slim port of `mindsos_core/schema/{__init__,types,schema,validation}.py` from parent. `validate_namespaced_properties` deferred to Phase 05/10 (graph-level property bag).
    2. `Schema` ctor stays parent-shape: `__init__(*, strict: bool = False)`. State-file basename is the identity; no `name` field added to the class.
    3. Full 8-variant `PropertyType` enum ported (no subset — splitting forward-debts to Phase 05+).
    4. Two new exceptions (`PropertyShapeError`, `UnknownTypeError`) inherit `CoreError`. Existing `SchemaError` (Phase 03 stub) keeps current raise sites; Phase 04 adds property-shape via `PropertyShapeError`, type-vocabulary via `UnknownTypeError`.
    5. Schema attach: **eager validation** of every node + edge + hyperedge; first violation → exit 1 with structured error including the offending element id (Pick B); schema NOT attached. **Re-attach permitted**: new schema replaces old after eager re-validation; JSON output reports `previous_schema` (Pick N4 + NEW4). **Empty-strict-schema warning** at attach time (Pick G).
    6. `mindsos graph set-prop` shape: single command, `--node-id | --edge-id` mutex flag (Pick I — renamed from `--node`/`--edge` for parity with `add-node --node-id`), repeatable `--prop k=v`, `--replace` flag. **`--replace` preserves `ref:*` keys** (Pick D); user-supplied `ref:*` values overwrite existing on collision (Pick N5). NO CLI path to drop a `ref:*` key in Phase 04 (Pick NEW6 deferred to Phase 09).
    7. **Graph state-file format BUMPED to v=2** (Pick A + P1). Phase 03 wrote v=1; Phase 04 reads both v=1 (legacy, no `schema_name` field) and v=2; writes v=2 on every save. v=1 → v=2 migration is one-way (Pick N3 risk). Per-kind version constants split: `GRAPH_STATE_VERSION = 2`, `SCHEMA_STATE_VERSION = 1`.
    8. Schema state-file v=1 schema pinned (item above under Persistence layout). NEW2: corrupt `PropertyType` vocab → RuntimeError → exit 1 with structured error.
    9. **`Graph.add_*` gain `_validate: bool = True` kwarg** (Pick NEW1). Rehydration (`_state_to_graph`) calls with `_validate=False` to tolerate Phase 03 v=1 files with reserved-key / non-primitive properties (Phase 03 didn't enforce). Schema-level checks always run; only `validate_user_properties` is gated by the kwarg. Mutations keep default `_validate=True`; recovery from poisoned legacy nodes via `set-prop --replace`.
    10. **`mindsos graph detach-schema`** ships in Phase 04 (Pick E + N1 + N6). Operates on raw JSON (bypasses schema rehydration) so it works on graphs with dangling schema references — primary recovery path. Exits 1 if no schema attached. Always upgrades the file to v=2 on write.
    11. **`mindsos schema reset` orphan check + `--force`** (Pick F + NEW3). Both `--name X` and `--all` walk every `graph-*.json` checking `schema_name`; refuse with exit 1 if any references exist; `--force` overrides (resulting graphs need `detach-schema` to recover; warning emitted on stderr).
    12. Carry-over deferrals from Phase 03 row that Phase 04 closes:
        - `Schema` typing on `Graph.__init__` — restored.
        - `validate_user_properties` helper — ported.
        - `update_node_properties` / `update_edge_properties` — added (no `_version` bump).
        - `tests/unit/test_graph.py` — ported (14 of 15; 1 skip for `_restore_node`).
    13. Carry-forward deferrals (do NOT close in Phase 04):
        - Graph `properties` bag (ADR-0130) — Phase 05/10.
        - Node `_version` OCC (ADR-0127) — Phase 07.
        - Edge / HyperEdge `deprecated_at` / `disputed_at` (ADR-0133) — Phase 10.
        - `Graph._restore_*` reconstruction helpers — Phase 08 (will subsume the Phase 04 `_validate=False` kwarg pattern).
        - Phase 01/02 deferrals (η, H, D, J-02, K-02) — defer further; no Phase 04 friction.
        - Q13 intergraph edge — Phase 05 chat adjudicates; Phase 04 does not touch.
        - `set-prop` ref-drop UX gap (Pick NEW6) — Phase 09 XRef migration owns proper ref management.
    14. `pyproject.toml [tool.setuptools.packages.find].include` already wildcards `mindsos_core*` — covers new `mindsos_core.schema` subpackage; no edit needed.
    15. `Dockerfile` COPY both new modules in prod stage AND test stage. Sentinel-paths additions ensure image-completeness regression test catches drift.
    16. `requirements.{in,txt}` / `requirements-test.txt` — unchanged (stdlib-only; schema (de)serialization uses `json`).
    17. `mindsos graph list` and `mindsos schema list` DELIBERATELY bypass `load_*_state`'s strict version check (Pick P3 — comment in code). Inclusive listing is correct for read-only enumeration; mutating commands DO use the strict loader.
    18. Phase 03 tests `test_state_file_has_state_version` and `test_load_future_state_version_rejected` updated to reference `state_mod.GRAPH_STATE_VERSION` (rather than hard-coded `1`). Per PHASE_MAP §1 "Breaking changes between phases allowed" — the v=1 → v=2 bump is a deliberate breaking change; Phase 03 tests evolve to assert the current contract.

### Phase 05 — L1 Metagraph elements

  **Deps:** 03. **Layer:** L1. **Net-new?** No (modulo Q13 below — if greenlit, intergraph edge primitive is **NEW CODE**).
  **Features:** Metagraph CRUD; place a Graph inside a Metagraph; binary MetaEdge; n-ary MetaHyperEdge; CompositionalMetaEdge unwrap.
  **Design question to adjudicate before implementing (§7 Q13 — full analysis at `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md`):** Should L1 ship a fourth edge primitive — node↔node across graphs *inside* one metagraph — alongside the three existing graph-spanning constructs (MetaEdge / MetaHyperEdge / XRef)? Phase 05 chat MUST surface this to the user before writing Metagraph code; default = defer (status-quo: alignments-as-graph reification). If greenlit, draft an ADR + scope a feature increment to Phases 05 (primitive), 07 (persistence — `OWNS` ownership decision), 10 (snapshot scope), 11 (Cypher builders).
  **Tests:** metagraph-wide IdentityRegistry shared across contained Graphs (ADR-0020); CompositionalMetaEdge cardinality.
  **Risks:** Phase 03's graph CLI must not bypass metagraph-wide registry. Q13 adjudication blocking.
  **Docs:** `docs/concepts/graphs-and-metagraphs.md`, `docs/usage/core/metagraphs.md`, ADRs 0020 / 0117. (If Q13 greenlit: new ADR + `docs/concepts/intergraph-edges.md`.)

### Phase 06 — L1 Instancing (`mindsos_instances`)

  **Deps:** 03, 05. **Layer:** L1. **Net-new?** No (per ADR-0132 the package is shipped; only CLI glue is new).
  **Features:** ElementInstance with sparse overrides; CompositeInstance bundle-level overrides (no propagation); lazy materialisation.
  **Tests:** override semantics (ADR-0025/0026); materialisation determinism.
  **Risks:** ADR-0132 backward-compat shim must keep working for any imports from `mindsos_core` of instancing classes.
  **Docs:** `docs/concepts/instancing.md`, ADRs 0015/0019/0025/0026/0132.

### Phase 07 — L1 Persistence

  **Deps:** 03, 04, 05, 06. **Layer:** L1. **Net-new?** Partial — verifies coverage of W1–W6 mitigations (WAL, indexes, AsyncClient, OCC) per ADRs 0121–0127.
  **Features:** save graph; save metagraph; client diagnose; integrity verify.
  **Tests:** save → reload via Phase 08; WAL replay after simulated crash; OCC rejects stale write; AsyncClient round-trips off the main thread.
  **Risks:** WAL semantics across phase rollbacks (a phase rollback may leave WAL entries on disk).
  **Docs:** `docs/usage/core/persistence.md`, ADRs 0030/0121/0122/0123/0126/0127.

### Phase 08 — L1 Reconstruction (loaders, streaming, refresh)

  **Deps:** 07. **Layer:** L1. **Net-new?** No.
  **Features:** load graph; load metagraph (full + streaming per ADR-0124); refresh.
  **Tests:** save+load round-trip; streaming load against a 10k-node fixture stays under a memory budget; refresh after external mutation reflects the change.
  **Risks:** lazy-Local-hydration interaction (ADR-0125) — `refresh` must respect LRU eviction.
  **Docs:** `docs/usage/core/persistence.md`, ADRs 0124/0125.

### Phase 09 — L1 XRef (cross-metagraph refs)

  **Deps:** 07, 08. **Layer:** L1. **Net-new?** Mostly no — XRef primitive shipped; **but** ADR-0142 (XRef cutover for `ref:global`) requires migration of legacy `ref:global_*` properties — that part is **NEW CODE** if any legacy refs exist in fixtures.
  **Features:** XRef CRUD; one-shot migration from legacy `ref:` properties.
  **Tests:** XRef round-trip; migration preserves role; legacy properties not duplicated.
  **Risks:** migration path must be reversible or audited.
  **Docs:** `docs/concepts/references.md`, ADRs 0128/0142.

### Phase 10 — L1 Snapshot + soft-delete + RemovalImpact

  **Deps:** 07, 08. **Layer:** L1. **Net-new?** Soft-delete partial (ADR-0133 properties exist; full enforcement may be NEW CODE).
  **Features:** snapshot take + restore (in-process only per ADR-0028); deprecate / dispute element with reason; removal-impact report.
  **Tests:** snapshot → mutate → restore; deprecated nodes still queryable but flagged; RemovalImpact correct on a 3-deep fixture.
  **Risks:** soft-delete read-path enforcement scope is an open question (§7).
  **Docs:** `docs/usage/core/snapshots.md`, ADRs 0027/0028/0129/0130/0133/0135.

### Phase 11 — L1 Cypher builders + integrity scanner + schema migration

  **Deps:** 07. **Layer:** L1. **Net-new?** No.
  **Features:** cypher-build debug; integrity verify with report; schema-migrate dry-run vs apply (ADR-0134).
  **Tests:** rel-type validation enforced (ADR-0021); integrity scanner detects 3 seeded violations; migration dry-run vs apply.
  **Risks:** schema migration is invasive — must be reversible or guarded by snapshot.
  **Docs:** `docs/api/core/cypher.md`, ADRs 0021/0022/0023/0123/0134.

### Phase 12 — L2 Identifiers + role IRIs + REF_TYPES

  **Deps:** 02. **Layer:** L2. **Net-new?** No.
  **Features:** L2-aware IRI parse (extends Phase 02); IRI build by role; REF_TYPES list.
  **Tests:** dolce / oewn / framenet / alignment IRI builders round-trip; REF_TYPES parity test against L3 (ADR-0067).
  **Risks:** REF_TYPES extension recipe (ADR-0047) must not be loosened.
  **Docs:** `docs/api/knowledge/identifiers.md`, `ref-types.md`, ADRs 0045/0047/0067.

### Phase 13 — L2 Schemas

  **Deps:** 04, 12. **Layer:** L2. **Net-new?** No.
  **Features:** show role schema; validate role-graph against schema.
  **Tests:** alignment / lexicon / ontology / concepts schemas validate respective fixtures.
  **Risks:** schema changes are breaking; anchor each role-schema's contract in a confirmation fixture.
  **Docs:** `docs/usage/knowledge/overview.md`, role-specific pages.

### Phase 14 — L2 KnowledgeLayer + role-graph bootstrap + MetagraphView

  **Deps:** 05, 07, 08, 12, 13. **Layer:** L2. **Net-new?** Partial — `MetagraphView` read-only enforcement per ADR-0141; if any write methods leaked, removing them is NEW CODE.
  **Features:** Global + Local bootstrap; ensure-role-graph idempotent; read-only view.
  **Tests:** memories live in Local (ADR-0044); MetagraphView has no public write methods.
  **Risks:** ADR-0044 must be honoured by bootstrap.
  **Docs:** `docs/usage/knowledge/overview.md`, `global-local.md`, ADRs 0042/0043/0044/0141.

### Phase 15 — L2 Importers (DOLCE, OEWN, FrameNet, Alignments)

  **Deps:** 13, 14. **Layer:** L2. **Net-new?** No (locations may move in Phase 37 but stay in L2 for this phase).
  **Features:** import each source; report counts.
  **Tests:** small fixture per importer; counts match; identifiers match ADR-0045 builders.
  **Risks:** importer dataset versions must be pinned per phase.
  **Docs:** `docs/knowledge-sources/*.md`.

### Phase 16 — L2 Promotion machinery

  **Deps:** 14. **Layer:** L2. **Net-new?** No (verify which of `promotion.py` / `promotion_v2.py` is canonical — see §7 open question).
  **Features:** list candidates; emit similarity report (content-hash report_id, ADR-0052); execute promote with optional force.
  **Tests:** baseline similarity heuristic deterministic (ADR-0055); promote refuses without report unless `--force` (ADR-0049); per-candidate atomic rollback (ADR-0053).
  **Risks:** keep this phase pure-KL (no auth gate); the Server gate goes in Phase 23.
  **Docs:** ADRs 0049–0056.

### Phase 17 — L2 Versioning + breadcrumbs

  **Deps:** 14. **Layer:** L2. **Net-new?** No.
  **Features:** active-version query; map of versions per role; PROMOTED breadcrumb in views.
  **Tests:** version-qualified IRI parsing; PROMOTED ref preserved through promotion (ADR-0051).
  **Risks:** ADR-0142 (XRef cutover, Phase 09) interacts with breadcrumbs.
  **Docs:** `docs/usage/knowledge/versioning.md`, ADR-0051.

### Phase 18 — Server: user store + auth

  **Deps:** 07. **Layer:** L0. **Net-new?** No.
  **Features:** user create / list / verify; capability assignment per role.
  **Tests:** password verification; argon2id hashing; unknown user fails with structured error.
  **Risks:** prohibited-action policy: CLI must NEVER read passwords from arguments — `--password-stdin` only.
  **Docs:** `docs/usage/server/auth.md`, ADR-0003.

### Phase 19 — Server: sessions

  **Deps:** 18. **Layer:** L0. **Net-new?** No.
  **Features:** login (returns opaque token); whoami; logout; refuse-concurrent-login (ADR-0005).
  **Tests:** sliding TTL refresh on use; absolute TTL hard-stop; concurrent login rejected; self-evict via repeated credentials.
  **Risks:** token storage on the host filesystem — phase chat picks (in-memory only with `--token` argument, or restricted-perms volume).
  **Docs:** `docs/usage/server/sessions.md`, ADRs 0002/0005.

### Phase 20 — Server: bootstrap CLI + admin reset + last-admin protection

  **Deps:** 19. **Layer:** L0. **Net-new?** No.
  **Features:** first-admin bootstrap; reset-admin recovery; last-admin removal blocked.
  **Tests:** bootstrap idempotent; reset-admin rotates credentials; last-admin removal refuses.
  **Docs:** `docs/usage/server/bootstrap.md`, ADR-0012.

### Phase 21 — Server: audit log

  **Deps:** 19. **Layer:** L0. **Net-new?** No.
  **Features:** audit query (since/until/user/event); audit stats; capability-gated.
  **Tests:** every login/logout/bootstrap emits an audit record; non-admin rejected.
  **Docs:** `docs/usage/server/audit.md`, ADR-0013.

### Phase 22 — Server: admin ops

  **Deps:** 19, 21. **Layer:** L0. **Net-new?** No.
  **Features:** admin user mgmt; kill session; cross-user read with refcount-install (ADR-0008).
  **Tests:** non-admin call rejected; cross-user read leaves no flush behind; kill-session immediate.
  **Risks:** admin actions cross the privacy boundary; audit must be exhaustive.
  **Docs:** `docs/usage/server/sessions.md`, ADR-0008.

### Phase 23 — Server: promotion lock + MetagraphSnapshot rollback

  **Deps:** 10, 16, 19. **Layer:** L0. **Net-new?** No.
  **Features:** promotion orchestration under GLOBAL_PROMOTE_LOCK with snapshot-rollback on failure.
  **Tests:** concurrent promotes serialise; failure mid-promote restores from snapshot; non-CAN_PROMOTE caller rejected.
  **Risks:** snapshot scope narrowed to release-ship per ADR-0129 — Phase 23 must respect, not widen.
  **Docs:** `docs/usage/server/promotion.md`, ADRs 0006/0007/0129.

### Phase 24 — Server: per-user transactional promotion (full ADR-0118 implementation)

  **Deps:** 23. **Layer:** L0. **Net-new?** **Yes.** Full ADR-0118 model beyond the vertical slice: STRUCTURE/SUBGRAPH/PIPELINE proposers (currently NotImplementedError); RELEASE_SHIP_LOCK; release manifest in `version_db/`; per-user transactional model.
  **Features:** propose-for-promotion (ATOM + STRUCTURE + SUBGRAPH + PIPELINE); release create from manifest; release ship under RELEASE_SHIP_LOCK.
  **Tests:** all four kinds proposable; release-ship atomicity across multiple atoms; rollback on partial failure; pending_global buffer survives restart.
  **Risks:** ADRs 0113–0117 / 0119 / 0120 are reserved but not drafted (§7); phase chat must draft them as part of this phase.
  **Docs:** `docs/usage/server/promotion.md`, ADRs 0113–0120 (drafted in this phase), ADR-0118 confirmed.

### Phase 25 — Server: SessionProtocol seam in L2 + hydrate/extract hooks

  **Deps:** 14, 19. **Layer:** cross. **Net-new?** No.
  **Features:** L2 accepts session via SessionProtocol duck-typing; install/extract hooks driven by login/logout.
  **Tests:** capability parity (ADR-0041); hydration on login; extraction on logout; ADR-0042 hooks fire in correct order.
  **Risks:** L2 must not import `mindsos_server` (ADR-0010) — parity test enforces.
  **Docs:** `docs/usage/server/auth.md`, ADRs 0010/0038/0040/0041/0042.

### Phase 26 — Integration A: L0+L1+L2 end-to-end scripted scenario

  **Deps:** 02–25 (every prior shipped phase). **Layer:** cross. **Net-new?** No (composes shipped pieces).
  **Scope (deliberately narrow — one scripted scenario, no feature additions):**
    1. Bootstrap server (Phase 20).
    2. Create one user (Phase 18); login (Phase 19) and capture token.
    3. Bootstrap KL Global + Local for that user (Phase 14, 25).
    4. Import a 10-row fixture into Global (Phase 15).
    5. Walk the role-graph via MetagraphView; assert expected counts.
    6. Logout.
    7. Audit query confirms each step emitted a record (Phase 21).
  **Tests:** one end-to-end test that runs the script in a clean container; golden-output diff on every assertion; same script via the CLI is the tester's manual confirmation.
  **Pass criterion:** scenario runs in under N seconds (set in phase chat); golden outputs stable across re-runs.
  **Risks:** scope creep — Phase 26 is regression-catching, not feature-adding. If a scenario step needs a new CLI flag, it's a regression in an earlier phase, not a new phase-26 feature.
  **Docs:** none new; this phase amends `docs/usage/cookbook/` only as a scaffolding placeholder for Phase 38.

### Phase 27 — L3 DataStates + capacity primitives

  **Deps:** 02, 05, 06. **Layer:** L3. **Net-new?** No.
  **Features:** DataState define with shape; Capacity / Monitor / Adapter define; IRI form `capacity:<category>:<name>` enforced.
  **Tests:** strict_compatible / list_of_compat / opaque_tag round-trip; stable IRIs (ADR-0066); REF_TYPES shared with L2 (ADR-0067).
  **Docs:** `docs/usage/capacity/data-states.md`, ADRs 0062/0063/0066/0067.

### Phase 28 — L3 12 categories + dual metagraph + role-graph bootstrap + capability gate

  **Deps:** 14, 25, 27. **Layer:** L3. **Net-new?** No.
  **Features:** L3 Global + Local bootstrap; ensure-category-graph; CAN_WRITE_GLOBAL gate (ADR-0078).
  **Tests:** Local-wins lookup (ADR-0061); 12 categories registered; capability-string parity with server (ADR-0078).
  **Risks:** bootstrap carve-out (ADR-0080) must not regress.
  **Docs:** `docs/usage/capacity/overview.md`, `categories.md`, ADRs 0061/0064/0065/0078/0080/0085.

### Phase 29 — L3 Discovery + Constraints

  **Deps:** 28. **Layer:** L3. **Net-new?** No.
  **Features:** auto-discover TYPE_COMPAT (ADRs 0069/0086); constraint add for the 5 admin-authored kinds (ADRs 0070/0092).
  **Tests:** auto-discovered marked `discovered_automatically=True`; rediscover-all preserves manual edges; CONSTRAINT typed correctly (constraint_kind property, ADR-0068).
  **Docs:** ADRs 0068/0069/0070/0086/0092.

### Phase 30 — L3 Pipeline finder + invoke runtime + ProblemTraceRecord

  **Deps:** 27, 28, 29. **Layer:** L3. **Net-new?** No.
  **Features:** BFS pipeline find (ADR-0071); invoke returns InvocationResult; failures emit ProblemTraceRecord (ADR-0072); problem-trace tail.
  **Tests:** shortest path; invoke returns failed=True without raising; ProblemTraceSink captures.
  **Risks:** ADR-0071 deliberately ignores constraints in finder — L4-style filtering not in scope here.
  **Docs:** `docs/usage/capacity/retrieval.md`, ADRs 0071/0072/0074.

### Phase 31 — L3 Residents + built-in text capacities + pathfinding

  **Deps:** 30. **Layer:** L3. **Net-new?** No.
  **Features:** resident start / list (descriptive only, no thread spawn — ADR-0073); install text builtins (raw text / tokens / sentences + space/sentence split); install pathfinding.
  **Tests:** resident registration is descriptive; text capacities round-trip; pathfinding shortest paths.
  **Docs:** `docs/usage/capacity/reactive-resident.md`, ADRs 0073/0088/0099/0100.

### Phase 32 — Integration B: L0+L1+L2+L3 read-side end-to-end scripted scenario

  **Deps:** 02–31 (every prior shipped phase). **Layer:** cross. **Net-new?** No.
  **Scope (deliberately narrow):**
    1. Phase 26 baseline (server bootstrap, user, login, KL bootstrap + import).
    2. L3 Global + Local bootstrap (Phase 28).
    3. Register a built-in text capacity (Phase 31).
    4. Find a pipeline raw-text → tokens (Phase 30).
    5. Invoke the pipeline on a one-sentence fixture; assert output shape.
    6. Tail the problem-trace; assert empty.
    7. Logout; audit confirms all steps recorded.
  **Tests:** one end-to-end test that runs the script; golden-output diff.
  **Pass criterion:** scenario runs deterministically; golden outputs stable.
  **Risks:** same as Phase 26 — no scope creep. Failure here means a regression in Phases 02–31, not a need for new Phase 32 features.
  **Docs:** none new (scaffolding for Phase 38 vertical slice).

### Phase 33 — L3 write capacities (ADR-0145)

  **Deps:** 25, 30, 31. **Layer:** L3. **Net-new?** **Yes — five write categories** (consolidate, trace, promote, author, state). Currently no L3 write capacities exist.
  **Features:** five write capacities; each calls `KLWriteHandle` (Phase 34 wires the actual handle; this phase ships capacities with the stub still raising contract-typed errors).
  **Tests:** each write capacity registers in the right category with stable IRI; stub failure raises a contract-typed error, not a leaky `NotImplementedError`.
  **Risks:** order — capacities exist before the handle they call works.
  **Docs:** `docs/usage/capacity/categories.md` (write-side section), ADR-0145.

### Phase 34 — L3 symmetric write contract (ADR-0146)

  **Deps:** 33. **Layer:** L3. **Net-new?** **Yes.**
  **Features:** `KLWriteHandle.write_and_validate(...)` becomes functional; every write capacity submits through the handle; symmetric invocation contract.
  **Tests:** each write category exercises the handle; failure path emits ProblemTraceRecord (consistent with ADR-0072).
  **Risks:** idempotency / retry semantics of `KLWriteHandle` (ADR-0143) need pinning here.
  **Docs:** ADRs 0143/0146.

### Phase 35 — L3 per-flow build pattern (ADR-0147)

  **Deps:** 34. **Layer:** L3. **Net-new?** **Yes.**
  **Features:** `KLWriteHandle.graph()` applies per-flow validators; concrete builder per write category.
  **Tests:** per-flow validator runs before commit; mismatched flow-vs-category rejected.
  **Docs:** ADR-0147.

### Phase 36 — L2 hybrid validators home (ADR-0139)

  **Deps:** 35. **Layer:** L2. **Net-new?** **Yes — `mindsos_knowledge/validators.py` does not yet exist.** Splits validation into structural (L1, exists) + semantic (L2, new).
  **Features:** validators run with scope structural / semantic / both; semantic validator per role.
  **Tests:** semantic catches a seeded violation that structural misses; both run via Phase 35's `write_and_validate`.
  **Docs:** ADR-0139.

### Phase 37 — Server-owns-importers (ADR-0144)

  **Deps:** 15, 36. **Layer:** L0 + L2. **Net-new?** **Yes — relocation.** Importers move from `mindsos_knowledge/importers/` to `mindsos_server/importers/` (or sibling).
  **Features:** server-side import each source; deprecated L2 path emits warning then is removed.
  **Tests:** golden-output diff vs Phase 15; audit records emitted under server's gate.
  **Risks:** import paths in third-party callers (none expected).
  **Docs:** `docs/knowledge-sources/*.md` (location update), ADR-0144.

### Phase 38 — End-to-end vertical slice

  **Deps:** all prior. **Layer:** cross. **Net-new?** No (composes shipped pieces).
  **Features:** cookbook text-realm + code-slice end-to-end via CLI through L0 → L1 → L2 → L3.
  **Tests:** golden-output for both cookbook flows; runs in under N seconds against the test fixture.
  **Pass criterion:** the vertical slice that lives today across `tests/` produces the same artefacts via the CLI — no surprises. Final mkdocs pass: lift `strict: true` if all broken links are gone, and a final review of every page's `last_confirmed_phase` front-matter for orphans.
  **Docs:** `docs/usage/cookbook/text-realm.md`, `nlu-slice.md`, `code-slice.md` — full.

---

## 6. Doc-to-phase map

For every existing doc-tree entry, the phase that confirms it. A page touched by multiple phases is **amended** (not finalised) by each; the `last_confirmed_phase` front-matter field tracks the latest. Final review at Phase 38.

### Get Started

| Page | Confirms in phase |
|---|---|
| `docs/index.md` | 38 |
| `docs/getting-started/install.md` | 00 + 01 |
| `docs/getting-started/quickstart.md` | 03 |
| `docs/getting-started/first-graph.md` | 03 |
| `docs/getting-started/first-metagraph.md` | 05 |
| `docs/getting-started/first-mental-model.md` | **out of scope** (L5) |
| `docs/getting-started/whats-new-v4.md` | 38 |
| `docs/getting-started/facts-and-figures.md` | 38 |

### Concepts

| Page | Confirms in phase |
|---|---|
| `docs/concepts/layers.md` | 38 |
| `docs/concepts/graphs-and-metagraphs.md` | 03 + 05 |
| `docs/concepts/identity.md` | 02 |
| `docs/concepts/instancing.md` | 06 |
| `docs/concepts/references.md` | 09 |
| `docs/concepts/memory-tiers.md` | **out of scope** |
| `docs/concepts/capacity-vs-intelligence.md` | 27 + 30 |
| `docs/concepts/global-local.md` | 14 |
| `docs/concepts/release-model.md` | 24 |
| `docs/concepts/society-of-mind.md` | 38 |
| `docs/concepts/glossary.md` | 38 |

### Usage / Core (L1)

| Page | Confirms in phase |
|---|---|
| `docs/usage/core/building-graphs.md` | 03 |
| `docs/usage/core/metagraphs.md` | 05 |
| `docs/usage/core/schema.md` | 04 |
| `docs/usage/core/persistence.md` | 07 + 08 |
| `docs/usage/core/snapshots.md` | 10 |

### Usage / Knowledge (L2)

| Page | Confirms in phase |
|---|---|
| `docs/usage/knowledge/overview.md` | 14 |
| `docs/usage/knowledge/global-local.md` | 14 |
| `docs/usage/knowledge/writing.md` | 16 (promotion writes); 33–35 (L3 write side) |
| `docs/usage/knowledge/walking.md` | 14 |
| `docs/usage/knowledge/versioning.md` | 17 |
| `docs/usage/knowledge/alignments.md` | 15 |
| `docs/usage/knowledge/memories.md` | **out of scope** |

### Usage / Capacity (L3)

| Page | Confirms in phase |
|---|---|
| `docs/usage/capacity/overview.md` | 27 + 28 |
| `docs/usage/capacity/categories.md` | 28 + 29 |
| `docs/usage/capacity/data-states.md` | 27 |
| `docs/usage/capacity/building.md` | 27 + 28 |
| `docs/usage/capacity/reactive-resident.md` | 31 |
| `docs/usage/capacity/retrieval.md` | 30 |
| `docs/usage/capacity/promotion.md` | 23 + 24 (server side); 33–35 (L3 write side) |

### Usage / Intelligence + Mental Model

**All `docs/usage/intelligence/*.md` and `docs/usage/mental-model/*.md` are out of scope.** They remain `tag: design` until the L4/L5 follow-up plan ships.

### Usage / Server

| Page | Confirms in phase |
|---|---|
| `docs/usage/server/overview.md` | 18 + 19 |
| `docs/usage/server/bootstrap.md` | 20 |
| `docs/usage/server/sessions.md` | 19 + 22 |
| `docs/usage/server/auth.md` | 18 + 25 |
| `docs/usage/server/promotion.md` | 23 + 24 |
| `docs/usage/server/audit.md` | 21 |

### Usage / Cookbook

| Page | Confirms in phase |
|---|---|
| `docs/usage/cookbook/text-realm.md` | 38 |
| `docs/usage/cookbook/nlu-slice.md` | 38 |
| `docs/usage/cookbook/code-slice.md` | 38 |

### API Reference

API pages map 1:1 to the phase that ships their corresponding code surface. Each phase confirms the API pages it touches.

### Decisions / ADRs

| ADR range | Confirms in phase |
|---|---|
| 0001–0013 (Server originals) | 18 (0001 fact); 0002 / 0005 in 19; 0003 in 18; 0004 in 07 + 18; 0006 / 0007 in 23; 0008 in 22; 0009 in 16; 0010 in 25; 0011 in 07; 0012 in 20; 0013 in 21 |
| 0014–0024 (L1 originals) | 0014 in 03; 0015 / 0019 / 0025 / 0026 in 06; 0016 in 09 (XRef supersession noted); 0017 in 04; 0018 in 07; 0020 in 05; 0021 in 03 + 11; 0022 / 0023 in 07; 0024 in 10 |
| 0027–0037 | 0027 / 0028 / 0029 in 10; 0030 in 07; 0031 / 0032 in 08; 0033 in 10; 0034 in 09; 0035 in 02; 0036 in 07; 0037 in 06 |
| 0038–0057 (L2) | 0038–0042 in 25; 0043 in 14; 0044 in 14; 0045 / 0047 in 12; 0046 in 18; 0048 in 14; 0049–0056 in 16; 0057 in 13 |
| 0060–0100 (L3) | 0060 / 0084 in 27 + 28; 0061 / 0064 / 0065 / 0085 in 28; 0062 / 0063 / 0066 in 27; 0067 in 12; 0068–0070 / 0086 / 0092 in 29; 0071 / 0072 / 0074 in 30; 0073 / 0088 / 0100 in 31; 0075 / 0076 in 28; 0077–0081 in 25 (cross with 28); 0082 / 0083 / 0094 / 0095 / 0096 / 0097 — L4 implications **out of scope**; only the L3 surface they imply ships; 0091 / 0098 / 0099 in 31; 0093 in 27 |
| 0118 | 24 |
| 0121–0137 (L1 redesign) | 0121 in 07; 0122 in 07; 0123 in 07 + 11; 0124 in 08; 0125 in 08; 0126 in 07; 0127 in 07; 0128 in 09; 0129 in 10; 0130 in 10 (or 05 if property bag lands earlier); 0131 in 02; 0132 in 06; 0133 in 10; 0134 in 11; 0135 in 10; 0136 in 18; 0137 in 23 + 24 |
| 0138–0144 (L2 closure) | 0138 in 14 (verify removed); 0139 in **36 — NEW CODE**; 0140 in 36 (constraints on writes); 0141 in 14; 0142 in 09; 0143 in 34; 0144 in **37 — NEW CODE** |
| 0145–0147 (L3 write side) | 0145 in **33 — NEW CODE**; 0146 in **34 — NEW CODE**; 0147 in **35 — NEW CODE** |

### Knowledge Sources

| Page | Confirms in phase |
|---|---|
| `docs/knowledge-sources/*.md` | 15 (location); 37 (location update on relocation) |

### Developer Guide / Changelog

| Page | Confirms in phase |
|---|---|
| `docs/dev/contributing.md` | 01 (release flow + branching policy) |
| `docs/dev/repo-layout.md` | 00 + 01 (`mindsos_cli`, `confirmation_docs/`, workflows); 06 (`mindsos_instances`); 37 (importer relocation) |
| `docs/dev/conventions.md` | 01 (CLI conventions) |
| `docs/dev/testing.md` | 01 (in-container = canonical) |
| `docs/dev/internals/*.md` | each per its layer's phase block |
| `docs/dev/handoffs/*.md` | each per its layer's phase block |
| `docs/dev/recipes/*.md` | the phase that introduces the surface being recipe-d |
| `docs/dev/release.md` | 01 |
| `docs/dev/coordinated-changes/*.md` | historical archive — confirmed once at 38 |
| `docs/changelog/*.md` | each phase appends a "Phase NN" line; final pass at 38 |

---

## 7. Open questions

These require user adjudication before the affected phase chat can proceed.

1. **`promotion.py` vs `promotion_v2.py` canonicalisation.** Both files exist in `mindsos_knowledge/`. **Affects Phase 16.** Question: which is canonical, and is the other deprecated?

2. **ADRs 0113–0117 / 0119 / 0120 reserved but undrafted.** **Affects Phase 24.** Recommend the phase chat draft them as part of the phase. Confirm or specify alternative.

3. **Soft-delete read-path enforcement (ADR-0133).** Property keys exist; runtime filtering not confirmed. **Affects Phase 10.** Question: do queries hide deprecated nodes by default, or is soft-delete advisory only?

4. **Property-bag on Metagraph / Graph (ADR-0130).** Memory says locked; code inventory does not directly confirm a `properties` dict on Metagraph/Graph. **Affects Phase 05 or 10.** Question: implementation extent? *(2026-05-04 — Phase 03 chat narrowed: Phase 03 row explicitly defers the Graph-level `properties` bag — slim `Graph.__init__` Phase 03 signature drops the `properties` parameter. Question now narrows to Phase 05 or 10; no Phase 03 interaction.)*

5. **Mkdocs `strict: false` policy.** 55 broken cross-links per `docs/_inbox/LINK_TODO.md`. The plan repairs links per page touched. Question: lift to `strict: true` at end of Phase 38 (default), or earlier?

6. **L3 ADRs 0082 / 0083 (Proposed but unbuilt).** Out of scope per L4 boundary, but Phase 33's `KLWriteHandle.promote()` cannot fully wire transitive promotion without 0083. Recommend: leave Phase 33 with atomic-per-capacity promotion and defer transitive to L4/L5 plan. Confirm.

7. **CLI session-state mechanism (Phase 03).** ~~The phase chat picks; if the choice has cross-phase impact, it surfaces here.~~ **Resolved 2026-05-04** — Phase 03 chat picked **JSON state file** at `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json`, parity with Phase 02's identity-registry pattern. Includes `_state_version: 1` field for forward-compat. Atomic write via `<path>.tmp` + `os.replace`. Same compose `--rm` gotcha as Phase 02 (state vanishes between containerised invocations; mitigation = host venv or bind-mount). See Phase 03 row Final amendments items 4, 5, 7.

8. **FOL layer placement, definitively.** Default = clean defer. Question: any portion in this plan's tail (e.g. as a Phase 39 capacity-design preview)? Recommend no.

9. **`_source_backup/` retention.** Currently kept as read-only reference. Question: keep, or delete during Phase 38?

10. **`docs/_inbox/LINK_TODO.md` and the 55 broken cross-links.** Many broken links may belong to L4/L5 design pages (out of scope). Question at Phase 38: remove `LINK_TODO.md` and accept residual broken links on out-of-scope pages, or block on fixing them?

11. **`docs/concepts/capacity:retrieval` (ADR-0097) scope.** Marked partial in code inventory. Question: Phase 30 confirms 0097 only at the level the BFS finder satisfies, deferring richer retrieval to L4/L5 plan?

12. **`mindsos_contracts` package (L2 critique §5.2).** Continuation handoff recommended; closure handoff deferred. Code inventory shows no such package. Question: accept the deferral as permanent for this plan?

13. **Intergraph edge primitive (raised by user 2026-05-04, in Phase 03 chat).** Should L1 ship a fourth edge primitive — node↔node *across graphs but inside one metagraph* — distinct from the three existing graph-spanning constructs (`MetaEdge` graph↔graph binary, `MetaHyperEdge` graph↔...↔graph n-ary, `XRef` node↔node *across metagraphs*)? **Affects Phase 05** (the natural design slot — Metagraph context exists; persistence implications scoped before Phase 07). Status-quo alternative: alignments-as-a-graph (3rd-party reification node carrying refs to both endpoints, what L2 does today). Pushbacks recorded against adding the primitive: no Cypher `OWNS` home, snapshot scope breaks per-graph locality, schema validation has two competing schemas, OCC/WAL ownership becomes ambiguous, migration cost across DOLCE/OEWN/FrameNet/Alignments importers (Phase 15). **Full analysis + options + pushbacks + concrete asks: `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md`.** **Phase 05 chat must adjudicate before implementing Metagraph elements.**

---

## 8. Doc-contradictions audit (newer-wins by default)

Resolved by newer-date precedence; logged for transparency.

1. **L2 write API.** Pre-2026-04-22 docs describe `KnowledgeLayer.add_local_node(...)` etc. ADR-0138 (L2 closure) drops the write API. **Resolution:** newer wins. Phase 14 verifies absence; Phase 16 / 33–35 own the new write surfaces.

2. **Six meta-pipelines vs two (L4 critique).** Out of scope — L4. Logged for follow-up plan.

3. **MetagraphSnapshot scope.** ADR-0007 had broad scope. ADR-0129 narrows to release-ship only. **Resolution:** narrowed scope is current. Phases 10, 23, 24 enforce.

4. **Promotion cascade / transactional model.** Old L3 handoff §5 frames as UX problem. Appendix C (post-pivot) resolves via release model. **Resolution:** Appendix C is current. ADR-0118 / Phase 24 implement.

5. **Importer location.** L2 docs put importers in `mindsos_knowledge/`. ADR-0144 moves them to Server. **Resolution:** ADR-0144 is current; Phase 37 relocates.

6. **Instancing package location.** Old L1 handoff puts instancing inside `mindsos_core`. ADR-0132 moves to sibling `mindsos_instances`. **Resolution:** ADR-0132 is current; backward-compat re-exports keep old imports working through the v4–v5 transition.

7. **L3 fixed-not-learned.** ADR-0060 stands; L4 owns learned state. No conflict.

---

## 9. Prerequisites for the user (before Phase 00 begins)

- [ ] Confirm `halvim/mindsos` exists on GitHub (lowercased) and is empty or near-empty.
- [ ] Delete the GHCR PAT (no longer needed).
- [ ] Tester's Linux box has Docker (Compose v2), git, and `python3 ≥ 3.11` available.
- [ ] Tester has SSH key on GitHub (or accepts HTTPS with a `repo`-only PAT).
- [x] **FalkorDB image pinned** (Phase 00 chat, 2026-05-03): `falkordb/falkordb:v4.18.3@sha256:30c530c193ac48cb6ea8c6cae745f793d2c098a0a138f7b3e46c1d90848845ba`.
- [x] **Python image pinned** (Phase 00 chat, 2026-05-03): `python:3.12.3-slim-bookworm@sha256:afc139a0a640942491ec481ad8dda10f2c5b753f5c969393b12480155fe15a63`. Overrides the original `3.11-slim-bookworm` recommendation in this section to match tester's host Python (3.12.3) and reduce debug-time surface area.

---

*End of PHASE_MAP.md. Phase chats refine and append; never silently overwrite.*
