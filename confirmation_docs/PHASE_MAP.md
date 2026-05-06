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
| **Phase rollback / supersession** | If Phase N+k reveals **(a) a regression in already-confirmed Phase N OR (b) a need for additive scope expansion to N**: tag `phase-NN-superseded` on main; rewrite the row in this map; open a new branch `phase-NN-v2`; tester reverts to `phase-(N-1)-confirmed` while v2 is built; on confirm, tag `phase-NN-v2-confirmed`. The original `phase-NN-confirmed` tag remains in history as evidence but is no longer the install target for that index. **Supersession trigger** ("regression" vs "expansion") is recorded free-form in the v2 confirmation doc's `tester_notes` field (TRIG-1; Phase 04-v2 lock 2026-05-04). **Confirmation doc:** v2 ships a sibling file `confirmation_docs/PHASE_NN_v2_CONFIRMED.md` (the original `PHASE_NN_CONFIRMED.md` stays untouched on disk, mirroring the tag-history rule). The release workflow derives the doc path from the tag's vsuffix. **Tarball naming:** `mindsos-phaseNN-v2.tar.gz` (vsuffix preserved). **Retention slot:** the (NN, vM) pair collapses to a single slot per phase NN — within the slot, the highest vM is the install target; lower vM tarballs evict immediately, regardless of the 5-phase window. **Letter sub-phases** (e.g. `05a` / `05b`) count as **separate slots** in the 5-phase retention window (T1 lock; Phase 05a/05b 2026-05-04). |
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
| 04 | L1 Schema — NodeType, EdgeType, opt-in strict ~~(SUPERSEDED by 04-v2)~~ | L1 | 02 |
| 04-v2 | L1 Schema — HyperEdgeType + type_name (additive expansion) | L1 | 02, 03 |
| 05a | L1 Metagraph port — Metagraph, MetaEdge, MetaHyperEdge (no CompositionalMetaEdge — dropped per N3-D; **ADR-0117 already Withdrawn here per round-1 P3**) **[CONFIRMED 2026-05-05]** | L1 | 03, 04-v2 |
| 05b | L1 IntergraphEdge (binary 1-1) + MetagraphSchema + MetaEdgeType + MetaHyperEdgeType + IntergraphEdgeType + compositional flag (NEW CODE; ADR-0148 first draft; **ADR-0117 already Withdrawn in 05a — 05b skips that flip**; `_compositional` reserved key + `Metagraph.mint_id` deferred from 05a per P6/P7) | L1 | 05a |
| 05c | L1 IntergraphHyperEdge (n-ary, NOT 1-1) + IntergraphHyperEdgeType (NEW CODE; ADR-0148 amended) | L1 | 05b |
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

**Total: 42 phases.** Two integration phases (26, 32). Eight phases carry **NEW CODE** beyond repackaging (05b, 05c, 24, 33, 34, 35, 36, 37). Phase 04 is Superseded by 04-v2 (slot collapsed); Phase 05 is split into 05a / 05b / 05c (three sub-phase slots, CASC-1 strict-sequential per the supersession-policy letter-sub-phases rule in §1).

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

### Phase 04 — L1 Schema (NodeType, EdgeType, opt-in strict)  [SUPERSEDED BY 04-v2 — 2026-05-04]

  **Status:** **Superseded by Phase 04-v2** (additive scope expansion: HyperEdgeType + HyperEdge.type_name + state-file v=2→v=3 + Schema state-file v=1→v=2). Original `phase-04-confirmed` tag remains in git history as evidence; install target for slot 04 is now `phase-04-v2-confirmed`. Original tarball asset evicts to "source-rebuild required" placeholder per (NN, vM) collapse policy. Original confirmation doc `PHASE_04_CONFIRMED.md` stays untouched on disk; v2 ships sibling `PHASE_04_v2_CONFIRMED.md`.

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

### Phase 04-v2 — L1 Schema (HyperEdgeType — additive scope expansion)

  **Status:** Pending (in design — refining + locking — this chat 2026-05-04, post 5-round adversarial pass).
  **Branch:** phase-04-v2
  **Tag on confirm:** phase-04-v2-confirmed
  **Supersession trigger:** **expansion** (per supersession-policy amendment). Round-7 adjudication of MC-2 (override "drop MetaHyperEdgeType correction") + user override "we should add hyperedgeType as well (patch phase 04)" — symmetric typed-hyperedge surface required so 05b's MetaHyperEdgeType has a parent precedent.
  **Depends on:** 02, 03. (Per supersession policy: starts from Phase 03 baseline; tester reverts to phase-03-confirmed while v2 is built. Implementation carries forward Phase 04's locked decisions PLUS this row's amendments.)
  **Layer(s):** L1
  **Net-new?:** **Yes (limited).** Adds `HyperEdgeType` dataclass to `mindsos_core/schema/types.py`; adds `Schema.hyperedge_types` map + `add_hyperedge_type` / `require_hyperedge_type` / `validate_hyperedge_properties` methods; adds `HyperEdge.type_name: str` field (required); extends `Graph.add_hyperedge(type_name=...)` (required) + `Graph.update_hyperedge_properties` + cypher rel-type validation. CLI: `mindsos schema add-hyperedge-type`, `mindsos graph add-hyperedge --type T` (required), `mindsos graph update-hyperedge-type` (UHT-1), `mindsos graph set-prop --hyperedge-id` (mutex extension). State-file: `GRAPH_STATE_VERSION = 3` (was 2); `SCHEMA_STATE_VERSION = 2` (was 1); cumulative migration (read v=1 ∪ v=2 ∪ v=3 graphs and v=1 ∪ v=2 schemas; write highest).

  **Locked decisions (round-7 + 5 adversarial rounds — 2026-05-04):**

    - **MC-2** — `HyperEdgeType` shipped (rejected MC-1 "drop MetaHyperEdgeType correction"); MetaHyperEdgeType in 05b inherits the parent.
    - **HET-1** — `HyperEdgeType.allowed_member_types: list[str]` (every member's `type_name` must be in the set; no cardinality bounds; symmetric across all members; empty list permitted per AME-1).
    - **MIG-1** — Graph state-file v=2 → v=3 one-way migration (mirror of Phase 04's v=1 → v=2). Pre-v=3 hyperedges receive `type_name="UNSPECIFIED"` on first read; strict-mode rejects until re-saved with a valid type via `update-hyperedge-type` (UHT-1) or recreated.
    - **SS-1** — Schema state-file v=1 → v=2 one-way migration (adds `hyperedge_types` map). 04-v2 binary tolerates v=1 read (treats missing field as empty list); writes v=2 on every save.
    - **PA-1** — ADR-0017 amended in place (no new ADR-0150). Amendment text in this row's appendix; ADR file edit deferred to Phase 38 per locked precedent.
    - **CASC-1** — Strictly sequential cascade: 04-v2 confirmed → 05a row refinement starts → 05a confirmed → 05b row refinement starts → 05b confirmed.
    - **SENT-1** — Sentinel literal is `"UNSPECIFIED"` (uppercase; satisfies cypher rel-type regex per ADR-0021). Original adversarial-round-1 surfacing of the cypher-regex conflict closed.
    - **UHT-1** — `mindsos graph update-hyperedge-type --hyperedge-id ID --type T` ships in 04-v2 (asymmetric — Edge.type_name and Node.type_name remain immutable; legacy-migration recovery path only).
    - **WARN-2** — Empty-strict warning condition unchanged from Phase 04 (warn iff zero NodeTypes); does NOT extend to HyperEdgeType emptiness.
    - **AME-1** — Empty `allowed_member_types: []` permitted on `add-hyperedge-type` (mirrors `EdgeType` precedent).
    - **VERSTR-1** — Python version literal `0.0.0+phase04.v2` (PEP 440 local version with period separator).
    - **TRIG-1** — Supersession trigger recorded free-form in `tester_notes`; no new schema field.

  **Features in scope (capability-level — locked):**

    - `HyperEdgeType(name, allowed_member_types, property_types, description)` dataclass exported from `mindsos_core.schema`.
    - `Schema.add_hyperedge_type(hyperedge_type)` registration; `Schema.require_hyperedge_type(name)` lookup; `Schema.validate_hyperedge_properties(type_name, properties)` strict-mode property check.
    - `Schema.validate_hyperedge(type_name, member_type_names)` validates `type_name` exists + every `member_type_name` is in `allowed_member_types` (when non-empty) — checked at `Graph.add_hyperedge` time when schema attached.
    - `HyperEdge.type_name: str` field (required); cypher rel-type validation per ADR-0021 at `__post_init__`.
    - `Graph.add_hyperedge(nodes, type_name=..., ..., _validate=True)` — `type_name` becomes required; `_validate=False` rehydration tolerates legacy hyperedges with sentinel `UNSPECIFIED`.
    - `Graph.update_hyperedge_properties(edge_id, properties, *, replace=False)` — symmetric with Phase 04 `update_node_properties` / `update_edge_properties`; no `_version` bump (ADR-0127 / Phase 07 owns).
    - `Graph.update_hyperedge_type(edge_id, new_type_name)` — UHT-1 recovery path; cypher regex validation; schema validation if attached.
    - `mindsos schema add-hyperedge-type --schema X --type-name T --allowed-member <T>... [--prop-type k=v] [--description STR]` — repeated `--allowed-member` flag; mirrors `add-edge-type`.
    - `mindsos graph add-hyperedge --name <GRAPH> --type <REL_TYPE> --member <ID> [--member <ID>...] [--label LABEL] [--prop k=v]... [--hyperedge-id ID]` — `--type` becomes required; cypher regex on `--type`.
    - `mindsos graph update-hyperedge-type --name <GRAPH> --hyperedge-id <ID> --type <NEW_TYPE>` — UHT-1.
    - `mindsos graph set-prop --hyperedge-id <ID> --prop k=v ...` — mutex extends to `--node-id | --edge-id | --hyperedge-id`; `--replace` preserves `ref:*`.
    - `mindsos schema inspect --json` output now includes `hyperedge_types`.
    - `mindsos schema add-hyperedge-type` JSON output mirrors `add-edge-type`.
    - Empty-strict warning at attach time when `strict=True AND zero NodeTypes` (WARN-2 — unchanged from Phase 04).
    - Eager attach validation extends — every Node, then every Edge, then every HyperEdge (in that order); first violation prints structured error including offending element id; attach refused; state-file unchanged.

  **Modules touched (locked):**

    - `mindsos_core/schema/types.py` — `HyperEdgeType` dataclass added; `__all__` extends.
    - `mindsos_core/schema/schema.py` — `_hyperedge_types: Dict[str, HyperEdgeType]`; `add_hyperedge_type` / `require_hyperedge_type` / `validate_hyperedge_properties` / `validate_hyperedge` methods; `_check_property_types` reused for hyperedge scope.
    - `mindsos_core/schema/validation.py` — no change (RESERVED_PROPERTY_KEYS already covers `type_name` at top-level reservation; `hyperedge_id` already covered by `edge_id` precedent — confirmed: NO new reserved-key entries).
    - `mindsos_core/schema/__init__.py` — re-export `HyperEdgeType`.
    - `mindsos_core/models/edge.py` — `HyperEdge.type_name: str` field (required); cypher rel-type validation in `__post_init__`; comment block updated for ADR-0017 / Phase 04-v2.
    - `mindsos_core/models/graph.py` — `add_hyperedge` signature gains required `type_name`; `update_hyperedge_properties` added; `update_hyperedge_type` added (UHT-1); eager attach validation extends to hyperedges; `_validated_hyperedge_properties` helper.
    - `mindsos_core/__init__.py` — re-export `HyperEdgeType`; cumulative ~27.
    - `mindsos_cli/commands/schema.py` — `add-hyperedge-type` subcommand; `_schema_to_state` writes `hyperedge_types`; `_state_to_schema` reads `hyperedge_types` (treats missing as empty list for v=1 backward-compat); `inspect_cmd` JSON includes `hyperedge_types`.
    - `mindsos_cli/commands/graph.py` — `add-hyperedge` `--type <REL_TYPE>` required; `update-hyperedge-type` subcommand; `set-prop` mutex extends; `_graph_to_state` writes v=3 (hyperedge entry includes `type_name`); `_state_to_graph` reads v=1/v=2/v=3 (populates `type_name="UNSPECIFIED"` for missing).
    - `mindsos_cli/state.py` — `GRAPH_STATE_VERSION = 3`; `SCHEMA_STATE_VERSION = 2`; `STATE_VERSION = GRAPH_STATE_VERSION` alias maintained.
    - `mindsos_cli/manifest.toml` — `[mindsos] phase = "04-v2"`; `version = "0.0.0+phase04.v2"`.
    - `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase04.v2"`.
    - `pyproject.toml` — `version = "0.0.0+phase04.v2"`; description bumped.
    - `docker-compose.yml` — `image: mindsos:phase04-v2-prod` / `mindsos:phase04-v2-test`.
    - `Dockerfile` — comment lines bumped (Phase 04 → Phase 04-v2 references; HyperEdgeType note in COPY block).
    - `mindsos_cli/commands/doctor.py` — `_COMPOSE_IMAGE_RE` regex extension to recognize `phaseNN-vM-<stage>` literal (one-line); phase-string parser tolerance extension `\d{2}([a-z]|-v\d+)?`.
    - `mindsos_cli/commands/confirm_phase.py` — accepts `--phase 04-v2` / `--init-notes 04-v2`; backward-compat alias `--init-notes phase-04-v2`.
    - `tests/_shared/sentinel_paths.py` — **no new entries** (HyperEdgeType lives inside existing files).

  **Persistence layout (locked):**

    - **Graph state-file v=3 JSON shape** (extends v=2 with hyperedge `type_name`):
      ```json
      {"_state_version": 3,
       "graph_id": "<uuid4>", "name": "<n>", "role": "<role-or-null>",
       "schema_name": "<schema-name-or-null>",
       "nodes": [...],
       "edges": [...],
       "hyperedges": [{"edge_id": "...", "type_name": "<UPPER>",
                       "member_ids": [...sorted by node_id],
                       "label": "...", "properties": {...}}]}
      ```
      Top-level lists byte-stable sorted; atomic write via `<path>.tmp + os.replace` (Phase 03/04 inherited).
    - **Schema state-file v=2 JSON shape** (extends v=1 with `hyperedge_types`):
      ```json
      {"_state_version": 2, "name": "<n>", "strict": false,
       "node_types": [...sorted by name],
       "edge_types": [...sorted by name],
       "hyperedge_types": [{"name": "<n>", "allowed_member_types": [...sorted],
                            "property_types": {"k": "<PropertyType.value>"},
                            "description": "<text-or-null>"}]}
      ```
      04-v2 binary tolerates v=1 reads (missing `hyperedge_types` treated as empty list); writes v=2 on every save.
    - **Cumulative migration on graph state-file:** 04-v2 binary reads v=1 ∪ v=2 ∪ v=3 (one-pass: populate `schema_name=null` for v=1 default per Phase 04 pattern; populate hyperedge `type_name="UNSPECIFIED"` for v=1/v=2 default); first mutation writes v=3.
    - **Strict version contract:** Phase 03 binary loading v=3 file rejects (same `this CLI supports vN` message as Phase 04 v=1→v=2). Recovery: hand-edit JSON downgrade (drop `hyperedge.type_name` fields, drop `schema_name`, set `_state_version: 1`).

  **Automated tests (location + intent — locked):**

    - `tests/phase_04_v2/` — ~30 tests:
      - `test_hyperedge_type.py` (3) — class round-trip, immutable frozen dataclass, default empty `allowed_member_types`.
      - `test_schema_add_hyperedge_type.py` (5) — happy path, JSON output, cypher regex on type-name, empty allowed-member (AME-1), --prop-type all 8 PropertyType variants.
      - `test_graph_add_hyperedge_type.py` (3) — `add-hyperedge --type T` required; cypher regex enforcement; schema validation when attached.
      - `test_state_v3_round_trip.py` (3) — v=3 file shape, byte-stable sort, atomic write.
      - `test_legacy_v1_v2_migration.py` (4) — v=1 graph load+populate UNSPECIFIED; v=2 graph load+populate UNSPECIFIED; first-mutation upgrades to v=3; v=2 schema load+empty `hyperedge_types`.
      - `test_sentinel_unspecified.py` (1) — `validate_edge_type_identifier("UNSPECIFIED")` passes.
      - `test_update_hyperedge_type.py` (5) — happy path, cypher regex on new type, schema validation rejection, no-op idempotent (UNSPECIFIED→UNSPECIFIED), missing hyperedge_id.
      - `test_attach_schema_hyperedge_eager.py` (3) — eager validation order (node→edge→hyperedge); first violation surfaces hyperedge_id; attach refused leaves file unchanged.
      - `test_set_prop_hyperedge.py` (3) — mutex extension; `--replace` ref:* preservation; reserved-key rejection.
    - **Audit pass (pre-implementation):** review every `tests/phase_04/test_state*.py` for hard-coded `2` constants; update to use `state_mod.GRAPH_STATE_VERSION`. Symmetric with Phase 04 B-04-prev fix. Lock as pre-implementation task.

  **Confirmation command:**
    `mindsos confirm-phase --phase 04-v2 --notes-file notes-phase-04-v2.md`
    (Init shape: `--init-notes 04-v2` is canonical; `--init-notes phase-04-v2` parses for backward-compat. Manifest stores `[mindsos] phase = "04-v2"`.)

  **Pass criterion:**

    - Tester can declare a HyperEdgeType with `--allowed-member`s; attach to a strict schema; `add-hyperedge --type T` validates against allowed members.
    - Empty `--allowed-member` list permitted (AME-1) — under non-strict accepts any member; under strict rejects all.
    - `update-hyperedge-type` recovers a legacy hyperedge from `UNSPECIFIED` to a valid type; validates against schema if attached.
    - Phase 03 v=1 graph loads cleanly under 04-v2; hyperedges show `type_name=UNSPECIFIED`; first mutation upgrades file to v=3.
    - Phase 04 v=2 graph loads cleanly under 04-v2; same upgrade path on first mutation.
    - `set-prop --hyperedge-id ID --prop k=v` round-trips through schema validation.
    - All Phase 03 + Phase 04 + Phase 04-v2 tests pass cumulatively in-container (`tests/`).
    - **Cumulative tests pass: ≥ Phase 04 baseline (379+2) + ~30 Phase 04-v2 added; tester records actual count in `PHASE_04_v2_CONFIRMED.md`** (sandbox-projected: ~409 + 2 skipped in-container).

  **Risks / known issues to watch:**

    - **v=2 → v=3 graph state-file migration is one-way.** 04-v2 binary touching a Phase 04 v=2 file upgrades on first mutation; Phase 04 binary then refuses with `this CLI supports v2` strict-version contract. **Recovery:** `rm -rf ~/.mindsos/graph-*.json` OR hand-edit JSON downgrade (drop `hyperedge.type_name` fields, set `_state_version: 2`). Documented in `docs/usage/core/schema.md` Migration section.
    - **v=1 → v=2 schema state-file migration is one-way** (parallel risk class).
    - **UNSPECIFIED sentinel under strict mode** — legacy hyperedges hit eager validation if a strict schema is attached without an `UNSPECIFIED` HyperEdgeType. Tester opts into the "escape hatch" pattern: `mindsos schema add-hyperedge-type --schema X --type-name UNSPECIFIED --allowed-member ...` (allowed_member_types covering legacy member types). Documented in `docs/usage/core/schema.md` Migration section.
    - **`add-hyperedge --type` is a CLI-breaking change.** Phase 03 invocations without `--type` no longer parse. Documented in Breaking Changes; tester updates scripts.
    - **Asymmetry note:** `update-hyperedge-type` (UHT-1) ships solely as legacy-migration recovery; Edge.type_name and Node.type_name remain immutable post-create (no `update-edge-type` / `update-node-type` ships). Documented in row appendix.
    - **Sentinel `UNSPECIFIED` is a tester-visible literal in inspect output** — under non-strict, the literal appears as `type_name`. Tester may mistake for a real type. Documented in user prose.
    - **J-02 carry-forward** — no advisory locks on state files; debug-only single-tester surface. Phase 07 persistence ships proper concurrency control.

  **Doc sections this phase confirms:**

    - `docs/usage/core/schema.md` — amended with HyperEdgeType section + Migration section v=2→v=3 entry + UNSPECIFIED sentinel semantics + UHT-1 recovery + escape-hatch pattern. `last_confirmed_phase: 04-v2`.
    - `docs/api/core/types.md` — amended with HyperEdgeType API + AME-1 empty-list semantic. `last_confirmed_phase: 04-v2`.
    - `docs/api/core/hyperedge.md` — amended with `type_name` field + UHT-1 path. `last_confirmed_phase: 04-v2`.
    - `docs/api/core/schema.md` — amended with `add_hyperedge_type` / `validate_hyperedge_properties` / `validate_hyperedge` methods. `last_confirmed_phase: 04-v2`.
    - `docs/changelog/CHANGELOG.md` — Phase 04-v2 entry appended.
    - ADR-0017 — amended in place per PA-1 (text in this row appendix; file edit Phase 38).

  **Breaking changes from Phase 04:**

    - `Graph.add_hyperedge(nodes, ...)` Python signature gains required `type_name`. Existing Phase 04 callers without `type_name` raise `TypeError`. Phase 04-v2 row appendix lists this and the CLI break together.
    - `mindsos graph add-hyperedge --name X --member ID` (no `--type`) no longer parses; tester scripts add `--type T`.
    - Graph state-file v=2 → v=3 + Schema state-file v=1 → v=2 (both one-way; documented above).

  **Final amendments (2026-05-04 — phase chat locks across rounds 0-7 + 5 adversarial rounds):**

    1. **MC-2** — HyperEdgeType ships in 04-v2 (NOT Phase 10 deferral). Reason: 05b's MetaHyperEdgeType needs a parent HyperEdgeType precedent for symmetric typed-hyperedge surface across L1.
    2. **HET-1** — `allowed_member_types: list[str]` only; no cardinality / per-position constraints. Mirrors EdgeType simplicity.
    3. **MIG-1** — Graph state-file v=2 → v=3 one-way migration. Pre-v=3 hyperedges receive `type_name="UNSPECIFIED"` on first read; strict-mode rejects until re-saved.
    4. **SS-1** — Schema state-file v=1 → v=2 one-way migration; symmetric with MIG-1.
    5. **PA-1** — ADR-0017 amended in place (no new ADR-0150). Amendment text below; file edit Phase 38.
    6. **CASC-1** — Strictly sequential cascade 04-v2 → 05a → 05b. PAR-1 lock.
    7. **SENT-1** — Sentinel literal `"UNSPECIFIED"` (uppercase; satisfies cypher rel-type regex per ADR-0021). Adversarial round 1 surfaced the regex conflict; locked here.
    8. **UHT-1** — `update-hyperedge-type` CLI ships in 04-v2 (asymmetric — Edge/Node type_name remain immutable). Adversarial round 1 derived consequence.
    9. **WARN-2** — Empty-strict warning unchanged from Phase 04 (warn iff zero NodeTypes); does NOT extend to HyperEdgeType emptiness. Self-correction of round-7 lock that would have regressed Phase 04 condition.
    10. **AME-1** — Empty `allowed_member_types: []` permitted; mirrors EdgeType precedent.
    11. **VERSTR-1** — Python version literal `0.0.0+phase04.v2` (PEP 440 local-version with period separator).
    12. **TRIG-1** — Supersession trigger free-form in `tester_notes`; no new schema field.
    13. **SUPER-§1-EXT** — PHASE_MAP §1 supersession-policy amendment extends to additive scope expansion. Letter sub-phases count as separate slots in the 5-phase retention window.
    14. Eager attach validation order: every Node → every Edge → every HyperEdge. First violation surfaces element id; attach refused; state-file unchanged. Phase 04 pattern extended.
    15. `_validate=False` rehydration kwarg extends to `Graph.add_hyperedge` for v=1/v=2 backward-compat (legacy hyperedges populated with sentinel UNSPECIFIED tolerate validation).
    16. JSON-then-string `--prop k=v` parsing inherited from Phase 03/04. Same fallback for `--prop-type k=v` (PropertyType vocabulary).
    17. `set-prop` 3-way mutex `--node-id | --edge-id | --hyperedge-id` (extends Phase 04's 2-way); detect-after-parse pattern; click.UsageError on ambiguity; `--replace` preserves `ref:*`.
    18. `update-hyperedge-type` JSON output: `{previous_type_name, new_type_name, hyperedge_id}` (mirrors Phase 04 attach-schema's `previous_schema` reporting).
    19. No-op idempotent `update-hyperedge-type` (UNSPECIFIED→UNSPECIFIED) exits 0; writes file (timestamp updates; content byte-stable). Phase 04 set-prop pattern.
    20. Pre-implementation audit: every `tests/phase_04/test_state*.py` reviewed for hard-coded `_state_version: 2` constants; updated to use `state_mod.GRAPH_STATE_VERSION` dynamically. Symmetric with Phase 04 B-04-prev fix.
    21. `mindsos graph list` and `mindsos schema list` continue to bypass strict version check (Phase 04 P3 inherited); `_state_version` field shown per row in human/JSON output.
    22. Image tags `mindsos:phase04-v2-prod` / `mindsos:phase04-v2-test`. `_COMPOSE_IMAGE_RE` extension recognizes `phaseNN-vM-<stage>`. `confirm-phase --phase` parser accepts `04-v2` / `phase-04-v2`.
    23. `requirements.{in,txt}` / `requirements-test.txt` unchanged (stdlib-only). `pyproject.toml [tool.setuptools.packages.find].include = ["mindsos_cli*", "mindsos_core*"]` already covers (no new sub-packages).
    24. **No carry-forward closure** — none of Phase 04's residual concerns (M-04 through R-04) target 04-v2; Q13 closes in 05b; ADR-0117 status flip happens in 05a; all unchanged here.
    25. **Phase 04 GitHub Release body unchanged** (verbatim copy of `PHASE_04_CONFIRMED.md`); only the tarball asset replaced by 1-line "source-rebuild required" placeholder per (NN, vM) eviction policy.
    26. **`PHASE_04_CONFIRMED.md` stays untouched** as historical record. Supersession annotation lives in PHASE_MAP §3 / §5 only. v2 ships sibling `PHASE_04_v2_CONFIRMED.md`.
    27. `tests/_shared/sentinel_paths.py` unchanged (HyperEdgeType lives inside existing `mindsos_core/schema/types.py`; `update-hyperedge-type` lives inside existing `mindsos_cli/commands/graph.py`).
    28. `mkdocs.yml` nav unchanged (no new pages; existing pages amended).
    29. `docs/dev/release.md` / `docs/dev/contributing.md` / `docs/dev/conventions.md` unchanged in 04-v2; sub-phase / v-suffix mention deferred to Phase 38 final pass (DOCREL-2).
    30. `confirmation_docs/_template.md` and `_template_notes.md` unchanged (TRIG-1 free-form in existing `tester_notes` field).

  **ADR-0017 amendment text (PA-1; deferred to Phase 38 file edit):**

  > **2026-05-04 amendment (Phase 04-v2):** ADR-0017 schema vocabulary extended. Original vocabularies: `NodeType`, `EdgeType`. Added: `HyperEdgeType` — n-ary edge type whose constraint surface is `allowed_member_types: list[str]` (every member's `type_name` must be in the set; no cardinality bounds; symmetric across all members; empty list permitted per AME-1, mirroring `EdgeType` precedent). Schema validation extends: under a strict attached schema, `HyperEdge.type_name` must exist in the schema's `hyperedge_types` AND every member node's `type_name` must be in `allowed_member_types`. The `Graph.add_hyperedge` API gains a required `type_name: str` parameter (cypher rel-type validation per ADR-0021 applies). Graph state-file format bumps from v=2 to v=3 (one-way migration mirroring Phase 04's v=1→v=2 pattern); pre-v=3 hyperedges receive `type_name="UNSPECIFIED"` on first read — sentinel literal chosen to satisfy ADR-0021's cypher rel-type regex (SENT-1 lock) — and trigger strict-mode rejection until re-saved with a valid type via `mindsos graph update-hyperedge-type` (UHT-1) or recreated. Schema state-file format bumps from v=1 to v=2 to carry the `hyperedge_types` map.

---

### Phase 05 — L1 Metagraph elements [SPLIT 2026-05-04 / 2026-05-05]

  **Status:** **Split into 05a + 05b + 05c** (G2 lock 2026-05-04; further split P2-B 2026-05-05 — see `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md` §8). See sibling rows below.

  **Q13 closed:** the original "should L1 ship a fourth edge primitive" question is GREENLIT and resolved into two primitives (`IntergraphEdge` binary in 05b + `IntergraphHyperEdge` n-ary in 05c). Canonical design at `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`.

---

### Phase 05a — L1 Metagraph port (Metagraph + MetaEdge + MetaHyperEdge)

  **Status:** Pending (in design — refining + locking — this chat 2026-05-05, post 4 reanalysis rounds).
  **Branch:** phase-05a
  **Tag on confirm:** phase-05a-confirmed
  **Depends on:** 03, 04-v2.
  **Layer(s):** L1.
  **Net-new?:** **Yes (limited).** New `mindsos metagraph` CLI subapp (~14 subcommands); new `metagraph-<n>.json` state-file format (v=1, no precedent); new `metagraph_name` back-pointer field on graph state file (v=3 → v=4 cumulative migration); `mindsos graph detach-metagraph` recovery command. Code-side: slim port of `Metagraph` + `MetaEdge` + `MetaHyperEdge` from parent `mindsos_core/models/metagraph.py`; `MetaHyperEdge.type_name: str` is a parent-code addition (per pre-lock C / Push C2 — symmetric with HyperEdge after Phase 04-v2). **CompositionalMetaEdge dropped** (per N3-D). **No IntergraphEdge / IntergraphHyperEdge** (deferred to 05b / 05c). **No MetagraphSchema** (deferred to 05b).

  **Locked decisions (4 reanalysis rounds — 2026-05-05):**

    - **B2** — Graph state-file v=3 → v=4 cumulative one-way migration (mirror of Phase 04-v2's v=2 → v=3 pattern). New optional field `metagraph_name: str | null`. Pre-v=4 graph files load with `metagraph_name=null` default.
    - **C2** — `MetaHyperEdge.type_name: str` required (cypher rel-type regex per ADR-0021); MetaEdge.type_name already required in parent code (no change). **No UNSPECIFIED sentinel** (no legacy data exists; symmetric reasoning fails).
    - **E2** — CASC-1 strict-sequential cascade: 04-v2 → 05a → 05b → 05c. **Plus 05b dry-run appendix** in this row §6 (below) — pre-resolves 05b decisions that could retroactively wish for 05a changes.
    - **N1-A1** — Ship `Metagraph.properties: Dict[str, Any]` (ADR-0130 property bag) in 05a; supersedes ADR-0029 (`:MetagraphSettings`). State-file v=1 includes `properties` field from day one.
    - **N1-A2** — **Strip backward-compat aliases** (`Metagraph._kl_active_graph_ids`, `Metagraph.user_id`) from slim port. No L2/Server consumer in 05a; aliases re-added in Phase 14 / Phase 18 when their consumers ship.
    - **N2-B** — Keep `MetaEdge.deprecated_at` / `disputed_at` / `MetaHyperEdge.deprecated_at` / `disputed_at` fields on dataclass (default `None`). **No CLI surface for soft-delete in 05a** (no `deprecate-metaedge`, no `include_deprecated` iterator filtering). Phase 10 wires the CLI + filtering.
    - **N3-D** — `CompositionalMetaEdge` dropped from 05a slim port. Compositional concept moves to `compositional: bool` flag on intergraph primitives (05b / 05c). ADR-0117 stays Reserved through 05a; Withdrawn in 05b.
    - **N4-A** — Slim `Metagraph.remove_graph(graph_id, *, cascade=True)` — cascades incident metaedges/metahyperedges, raises `IdentityError` on unknown graph, no `RemovalImpact` return, no `force=True` flag, no XRef / `ref:*` walking. Phase 09 / Phase 10 add full ADR-0135 `RemovalImpact` machinery.
    - **N6** — `MetaEdge.type_name: str` required (parent shape; no change needed).
    - **N7-A** — `mindsos metagraph add-graph` refuses with structured error if the target graph already has `metagraph_name` back-pointer set (graph is metagraph-owned). Tester runs `metagraph remove-graph` on the prior owner first, OR `mindsos graph detach-metagraph` if the prior owner's state file is missing (DM-A recovery path).
    - **Q1-B** — Separate `mindsos metagraph set-prop` subcommand (2-way mutex `--metaedge-id | --metahyperedge-id`); does NOT extend `mindsos graph set-prop`. Subapp boundary respected.
    - **Q2** — `mindsos metagraph` subcommand list locked: `create / inspect / list / reset / add-graph / remove-graph / add-metaedge / remove-metaedge / add-metahyperedge / remove-metahyperedge / set-prop / list-metaedges / list-metahyperedges`. Plus **CR-A**: `create --name X [--metagraph-id ID] [--prop k=v]...` accepts properties at creation (mirrors Phase 03 / 04 `add-*` precedent).
    - **Q3-A** — MetaHyperEdge `member_graphs` JSON serialization sorts by `graph_name` (string sort) for byte-stable output.
    - **Q4-B** — Standalone `mindsos graph inspect <G>` on a metagraph-owned graph shows contents WITH stderr warning; mutations (`add-node`, `add-edge`, `set-prop`, etc.) on metagraph-owned graphs **refuse** with structured error pointing to `mindsos metagraph ...` subapp.
    - **Q5-A** — Eager identity-collision check on `metagraph add-graph`: walk all currently-contained graphs' element ids; raise `IdentityError` on collision (matches parent code in-memory `add_graph` semantics).
    - **Q6-A** — `metagraph reset --name X` and `--all` walk every `graph-*.json`; refuse with exit 1 if any graph references a metagraph being deleted; `--force` strips back-pointers from referenced graphs (warning emitted on stderr).
    - **R3-B** — Strip `CompositionalImmutableError`, `RemoveGraphBlockedError`, `XRefIntegrityError` from `mindsos_core/exceptions.py` slim port. 05b adds `CompositionalImmutableError` back (consumer: `IntergraphEdge.compositional`); Phase 09 adds `XRefIntegrityError`; Phase 10 adds `RemoveGraphBlockedError`.
    - **DM-A** — `mindsos graph detach-metagraph --name <G>` ships in 05a as the recovery path for dangling `metagraph_name` back-pointer (symmetric with Phase 04's `graph detach-schema`). Raw-JSON path bypasses metagraph load. Exits 1 if no back-pointer set.

  **Features in scope (capability-level — locked):**

    - `Metagraph(name, *, identity=None, metagraph_id=None, properties=None, id_strategy=None)` constructor (ADR-0130 property bag accepted; ADR-0131 IdStrategy parametric).
    - `Metagraph.add_graph(graph) -> Graph` — unifies graph's IdentityRegistry into metagraph's; ADR-0020 enforcement; ADR-0138 INFO log on non-empty registry unification; eager id-collision check Q5-A; refuse if graph already has `metagraph_name` back-pointer (N7-A).
    - `Metagraph.remove_graph(graph_id, *, cascade=True)` — slim per N4-A.
    - `Metagraph.add_metaedge(source, target, type_name, *, label=None, properties=None) -> MetaEdge`.
    - `Metagraph.remove_metaedge(edge_id) -> None`.
    - `Metagraph.add_metahyperedge(graphs, *, type_name, label=None, properties=None) -> MetaHyperEdge` — `type_name` keyword-required (CLI surfaces it as required).
    - `Metagraph.remove_metahyperedge(edge_id) -> None`.
    - `Metagraph.iter_metaedges()`, `Metagraph.iter_metahyperedges()` — no `include_deprecated` kwarg in 05a (Phase 10 adds).
    - `Metagraph.update_metaedge_properties(edge_id, properties, *, replace=False)` — symmetric with Phase 04's `update_node/edge/hyperedge_properties`; no `_version` bump.
    - `Metagraph.update_metahyperedge_properties(...)` — same.
    - `Metagraph.mint_id(kind, content=None) -> str` — ADR-0131 helper (parent code line 442).
    - `Metagraph.__repr__` — slimmed (no XRef / instance / composite counts).
    - **CLI** — `mindsos metagraph` subapp with subcommands per Q2 + CR-A.
    - **CLI** — `mindsos graph detach-metagraph --name <G>` (DM-A).
    - **State files** — `metagraph-<n>.json` v=1 (new format) + `graph-<n>.json` v=3 → v=4 cumulative migration adding `metagraph_name` back-pointer.
    - **Doctor self-test extension** — recognize `mindsos:phase05a-prod` / `phase05a-test` image tags (regex extension to handle letter-suffix without v-prefix).

  **Modules touched (locked):**

    - `mindsos_core/models/metagraph.py` — slim port from parent. **Strips:** XRef methods (`add_xref` / `iter_xrefs` / `remove_xref` / `_verify_xref_target`), instancing methods (all 7 `instantiate_*` + `compose` + `_register_instance` + `remove_instance` + `_attach_instance` + `_attach_composite`), `element_instances` / `composite_instances` dicts, `xrefs` / `_xrefs_by_source` / `_xrefs_by_target` dicts, `RemovalImpact` class, `_compute_removal_impact`, `verify_invariants`, `_restore_metaedge` / `_restore_metahyperedge` / `_attach_graph`, `deprecate_metaedge` / `deprecate_metahyperedge`, `_kl_active_graph_ids` / `user_id` aliases (N1-A2), `CompositionalMetaEdge` class (N3-D). **Keeps:** `Metagraph.__init__` (with `properties` per N1-A1), `add_graph` / `remove_graph` (slim N4-A), `add_metaedge` / `remove_metaedge`, `add_metahyperedge` (with required `type_name` per C2) / `remove_metahyperedge`, `mint_id`, `__repr__` (slimmed), `MetaEdge` dataclass (with dormant soft-delete fields per N2-B), `MetaHyperEdge` dataclass (with new required `type_name` field).
    - `mindsos_core/exceptions.py` — strip `CompositionalImmutableError` / `RemoveGraphBlockedError` / `XRefIntegrityError` (R3-B). Re-shipped by 05b / 09 / 10 respectively.
    - `mindsos_core/__init__.py` — exports `Metagraph` + `MetaEdge` + `MetaHyperEdge` + `RemovalImpact` removed (Phase 10 adds back).
    - `mindsos_cli/commands/metagraph.py` — **NEW file**. Typer subapp; all subcommands per Q2 + CR-A.
    - `mindsos_cli/commands/graph.py` — extends with `detach-metagraph` subcommand (DM-A); `add-node` / `add-edge` / `add-hyperedge` / `set-prop` / `update-*` mutation commands gain the metagraph-owned check (Q4-B refuse-on-mutation); `inspect` gains the warn-and-show behavior (Q4-B); `_state_to_graph` reads v=1 ∪ v=2 ∪ v=3 ∪ v=4 (populates `metagraph_name=null` for missing); `_graph_to_state` writes v=4.
    - `mindsos_cli/state.py` — `GRAPH_STATE_VERSION = 4` (was 3). New `METAGRAPH_STATE_VERSION = 1`. New helpers: `metagraph_file_path` / `save_metagraph_state` / `load_metagraph_state` / `iter_metagraph_files` / `delete_metagraph_state_file`.
    - `mindsos_cli/app.py` — `register_metagraph_app` wired.
    - `mindsos_cli/manifest.toml` — `[mindsos] phase = "05a"`; `version = "0.0.0+phase05a"`.
    - `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05a"`.
    - `pyproject.toml` — version + description bumped.
    - `docker-compose.yml` — `mindsos:phase05a-prod` / `mindsos:phase05a-test` image tags.
    - `Dockerfile` — comment lines bumped (Phase 04-v2 → Phase 05a references); COPY block adds `mindsos_cli/commands/metagraph.py`.
    - `mindsos_cli/commands/doctor.py` — `_COMPOSE_IMAGE_RE` regex extends to recognize `phaseNN<letter>-<stage>` form (without v-prefix). Extension: `phase\d{2}([a-z]|-v\d+)?-(prod|test)`. (Phase 04-v2 covered `-vM` form; 05a covers letter form.)
    - `mindsos_cli/commands/confirm_phase.py` — accepts `--phase 05a` / `--init-notes 05a`. Backward-compat alias `phase-05a` per Phase 04-v2 pattern.
    - `tests/_shared/sentinel_paths.py` — **+1 entry**: `mindsos_cli/commands/metagraph.py`.

  **Persistence layout (locked):**

    - **Metagraph state-file v=1 JSON shape** (NEW format):
      ```json
      {"_state_version": 1,
       "metagraph_id": "<uuid4>", "name": "<n>",
       "properties": {"k": "<value>"},
       "contained_graphs": ["<graph-name>", ...],
       "metaedges": [
         {"edge_id": "...", "source_graph": "<gname>", "target_graph": "<gname>",
          "type_name": "<UPPER>", "label": "<text-or-null>", "properties": {...}}
       ],
       "metahyperedges": [
         {"edge_id": "...", "type_name": "<UPPER>",
          "member_graphs": [...sorted by graph_name],
          "label": "<text-or-null>", "properties": {...}}
       ]}
      ```
      Top-level lists byte-stable sorted (contained_graphs by name; metaedges by edge_id; metahyperedges by edge_id). Atomic write via `<path>.tmp + os.replace` (Phase 03 / 04 / 04-v2 inherited). `properties` allowed empty `{}`. Soft-delete fields (`deprecated_at` / `disputed_at`) NOT serialized in 05a (always `None`); Phase 10 adds optional fields with v=1 → v=2 metagraph state-file bump.
    - **Graph state-file v=4 JSON shape** (extends v=3 with `metagraph_name` back-pointer):
      ```json
      {"_state_version": 4,
       "graph_id": "<uuid4>", "name": "<n>", "role": "<role-or-null>",
       "schema_name": "<schema-name-or-null>",
       "metagraph_name": "<metagraph-name-or-null>",
       "nodes": [...], "edges": [...], "hyperedges": [...]}
      ```
    - **Cumulative migration on graph state-file:** 05a binary reads v=1 ∪ v=2 ∪ v=3 ∪ v=4 (one-pass: populate `schema_name=null` for v=1 default; populate hyperedge `type_name="UNSPECIFIED"` for v=1/v=2 default; populate `metagraph_name=null` for v=1/v=2/v=3 default); first mutation writes v=4.
    - **Strict version contract:** Phase 04-v2 binary loading v=4 file rejects (`this CLI supports v3` message). Recovery: hand-edit JSON downgrade (drop `metagraph_name` field, set `_state_version: 3`). Documented in `docs/usage/core/metagraphs.md` Migration section.
    - **Schema state-file unchanged from Phase 04-v2** (v=2; no MetagraphSchema until 05b).

  **Automated tests (location + intent — locked):**

    - `tests/phase_05a/` — ~35 tests:
      - `test_metagraph_create.py` (4) — fresh metagraph, with properties via CR-A `--prop`, with `--metagraph-id`, idempotent JSON output.
      - `test_metagraph_add_graph.py` (6) — happy path; ADR-0020 unification (ADR-0138 INFO log fires); identity-collision check Q5-A; refuse on already-owned (N7-A); back-pointer written to graph state file; multiple-graphs-in-metagraph round-trip.
      - `test_metaedge.py` (4) — add with required type_name, cypher regex enforcement, `--prop` populates properties bag, source/target validation.
      - `test_metahyperedge.py` (5) — add with required `--type`, cypher regex, `member_graphs` byte-stable sort by name (Q3-A), `--prop` populates, member-must-be-in-metagraph validation.
      - `test_metagraph_state_v1.py` (3) — v=1 round-trip, byte-stable sort, atomic write.
      - `test_metagraph_set_prop.py` (3) — Q1-B 2-way mutex, `--replace` preserves `ref:*`, reserved-key rejection.
      - `test_metagraph_remove_graph.py` (3) — slim N4-A: cascade incident metaedges/metahyperedges; clears back-pointer on removed graph; raises `IdentityError` on unknown graph_id.
      - `test_metagraph_reset.py` (3) — orphan check Q6-A, `--force` strips back-pointers, `--all` symmetric.
      - `test_graph_state_v4.py` (3) — back-pointer round-trip; cumulative migration v=1/v=2/v=3 → v=4 first-mutation; v=5 future-version refused.
      - `test_graph_inspect_metagraph_owned.py` (2) — Q4-B warn-and-show on read.
      - `test_graph_mutation_metagraph_owned.py` (3) — Q4-B refuse-on-mutation (`add-node`, `add-edge`, `set-prop` each).
      - `test_graph_detach_metagraph.py` (3) — DM-A happy path, dangling-back-pointer recovery, exit-1-if-no-back-pointer.
      - `test_doctor_phase05a.py` (1) — image-tag regex covers `phase05a-prod`.
    - **Audit pass (pre-implementation):** every `tests/phase_03/` / `tests/phase_04/` / `tests/phase_04_v2/test_state*.py` reviewed for hard-coded `_state_version: 3` constants; updated to use `state_mod.GRAPH_STATE_VERSION` dynamically. Symmetric with 04-v2 B-04-prev fix. Lock as pre-implementation task.

  **Confirmation command:**
    `mindsos confirm-phase --phase 05a --notes-file notes-phase-05a.md`
    (Init shape: `--init-notes 05a` is canonical; backward-compat alias `phase-05a`. Manifest stores `[mindsos] phase = "05a"`.)

  **Pass criterion:**

    - Tester can create a metagraph, add 2-3 graphs to it, add metaedges + metahyperedges with required type_name, set properties on metaedges, list contents, and `inspect` round-trips state.
    - `metagraph add-graph` refuses on already-owned graph (N7-A); `metagraph remove-graph` clears back-pointer; tester can re-add to a different metagraph after removal.
    - `mindsos graph inspect <G>` on metagraph-owned graph WARNS but shows contents; `mindsos graph add-node <G>` on metagraph-owned graph REFUSES with pointer to `mindsos metagraph` subapp (Q4-B).
    - `mindsos graph detach-metagraph` recovers a graph from a deleted-metagraph dangling back-pointer (DM-A).
    - `metagraph reset` orphan check refuses with exit 1 when graphs reference target; `--force` strips back-pointers (Q6-A).
    - Phase 04-v2 v=3 graph loads cleanly under 05a; first mutation upgrades file to v=4.
    - All Phase 03 + Phase 04 + Phase 04-v2 + Phase 05a tests pass cumulatively in-container.
    - **Cumulative tests pass: ≥ Phase 04-v2 baseline (412 + 2 skipped) + ~35 Phase 05a added; tester records actual count in `PHASE_05a_CONFIRMED.md`** (sandbox-projected: ~447 + 2 skipped).

  **Risks / known issues to watch:**

    - **v=3 → v=4 graph state-file migration is one-way.** 05a binary touching a Phase 04-v2 v=3 file upgrades on first mutation; Phase 04-v2 binary then refuses with `this CLI supports v3` message. Recovery: hand-edit JSON downgrade (drop `metagraph_name`, set `_state_version: 3`) OR `rm -rf ~/.mindsos/graph-*.json`. Documented in `docs/usage/core/metagraphs.md` Migration section.
    - **Standalone graph CLI on metagraph-owned graphs is mutation-blocked.** Tester running `mindsos graph add-node` on a metagraph-owned graph hits a refusal (Q4-B). Recovery: route mutations through `mindsos metagraph`-subapp equivalents OR `mindsos graph detach-metagraph` if they want to mutate independently.
    - **Identity-collision footgun on metagraph load**: if two contained graphs were independently mutated to share an element id (both have node id `bar`), the metagraph load fails. Recovery: hand-edit one graph's id OR re-create. ADR-0020 unification at metagraph load time enforces.
    - **Eager identity-collision check Q5-A is O(N)** over all contained graphs' element ids. Acceptable for single-tester debug use; Phase 07 ships indexed lookup if perf becomes an issue.
    - **`metagraph reset --force` strips back-pointers from all referenced graphs** but does not unify identity registries back to standalone form (in-memory unification was metagraph-scoped; per-graph registry rebuilds on next standalone load). Footgun if a previously-collided id pair survives in two graphs that are now standalone.
    - **No advisory locks on state files** (J-02 carry-forward). Concurrent CLI invocations have race conditions; Phase 07 ships proper concurrency control.
    - **No CLI to delete a single metaedge that lacks a metaedge_id**: tester needs `list-metaedges --json` to find ids first. Symmetric asymmetry with Phase 04 hyperedges.

  **Doc sections this phase confirms:**

    - `docs/concepts/graphs-and-metagraphs.md` — amended with Metagraph + MetaEdge + MetaHyperEdge sections + Metagraph-owned-graph semantics + back-pointer + recovery patterns. `last_confirmed_phase: 05a`.
    - `docs/usage/core/metagraphs.md` — full (NEW). Covers all `mindsos metagraph` subcommands + state-file Migration v=3→v=4 + back-pointer + detach-metagraph recovery + Q4-B mutation-refuse semantics + Q5-A collision check + Q6-A reset orphan check. `last_confirmed_phase: 05a`.
    - `docs/getting-started/first-metagraph.md` — full (NEW). Quickstart walkthrough.
    - `docs/api/core/metagraph.md` — full (NEW). API reference.
    - `docs/api/core/metaedge.md` — full (NEW).
    - `docs/api/core/metahyperedge.md` — full (NEW).
    - `docs/changelog/CHANGELOG.md` — Phase 05a entry appended.
    - **ADR-0020** confirmed (metagraph-wide IdentityRegistry).
    - **ADR-0117** stays Reserved (CompositionalMetaEdge dropped per N3-D; Withdrawn flip happens in 05b).
    - **ADR-0029** Superseded by ADR-0130 (property bag in 05a). Annotation block added; file edit deferred to Phase 38.
    - **ADR-0130** Accepted (property bag on Metagraph shipped; Graph property bag deferred to Phase 10 per N1 distinction).

  **Breaking changes from Phase 04-v2:**

    - `Graph` state file v=3 → v=4 (one-way; documented above).
    - `mindsos graph add-node` / `add-edge` / `add-hyperedge` / `set-prop` / `update-*` REFUSE on metagraph-owned graphs (Q4-B). Tester scripts using these on graphs that get added to metagraphs need to switch to `mindsos metagraph` subapp.
    - `mindsos graph inspect <G>` on metagraph-owned graph emits stderr warning (still exits 0; output still shown — Q4-B).

  **Final amendments (2026-05-05 — locked across 4 reanalysis rounds):**

    1. **B2** — graph state-file v=4 with `metagraph_name` back-pointer.
    2. **C2** — MetaHyperEdge.type_name required; no UNSPECIFIED sentinel for metagraph-level edges.
    3. **E2** — CASC-1 strict-sequential + 05b dry-run appendix (see §6 below).
    4. **N1-A1** — Ship `Metagraph.properties` in 05a; supersedes ADR-0029.
    5. **N1-A2** — Strip `_kl_active_graph_ids` and `user_id` aliases.
    6. **N2-B** — Soft-delete fields kept dormant; no CLI in 05a.
    7. **N3-D** — CompositionalMetaEdge dropped from 05a.
    8. **N4-A** — Slim `remove_graph`; no RemovalImpact.
    9. **N6** — MetaEdge.type_name required (already in parent; no change).
    10. **N7-A** — Refuse on already-owned `add-graph`.
    11. **Q1-B** — Separate `mindsos metagraph set-prop` subcommand.
    12. **Q2 + CR-A** — Subcommand list locked; `create` accepts `--prop` at create time.
    13. **Q3-A** — `member_graphs` sorted by `graph_name`.
    14. **Q4-B** — Standalone-graph CLI: warn-and-show on read; refuse on mutation.
    15. **Q5-A** — Eager identity-collision check on `metagraph add-graph`.
    16. **Q6-A** — `metagraph reset` orphan check; `--force` strips back-pointers.
    17. **R3-B** — Strip exception classes from slim port (`CompositionalImmutableError`, `RemoveGraphBlockedError`, `XRefIntegrityError`).
    18. **DM-A** — `mindsos graph detach-metagraph` ships in 05a.
    19. Eager-attach validation order from Phase 04 (Node → Edge → HyperEdge) extends per-graph; metagraph add-graph identity-collision check (Q5-A) runs FIRST before any other validation.
    20. JSON-then-string `--prop k=v` parsing inherited from Phase 03 / 04 / 04-v2.
    21. Pre-implementation audit: every `tests/phase_03/` / `tests/phase_04/` / `tests/phase_04_v2/` test file reviewed for hard-coded `_state_version: 3` constants; updated to use `state_mod.GRAPH_STATE_VERSION` dynamically (symmetric with Phase 04 B-04-prev / Phase 04-v2 audit).
    22. Image tags `mindsos:phase05a-prod` / `mindsos:phase05a-test`; `_COMPOSE_IMAGE_RE` regex extension to recognize `phase\d{2}([a-z]|-v\d+)?-(prod|test)`. `confirm-phase --phase` parser accepts `05a` / `phase-05a`.
    23. `requirements.{in,txt}` / `requirements-test.txt` unchanged (stdlib-only). `pyproject.toml` package wildcards already cover new files.
    24. **No carry-forward closure** — Phase 04 §7 deferrals (M-04 through R-04) and Phase 04-v2 §7 deferrals (A-04-v2 through D-04-v2) all stay carry-forward. Q13 closes via the 05b/05c split (canonical at `INTERGRAPH_EDGES_DESIGN.md`).
    25. **Phase 04-v2 GitHub Release body unchanged**; tarball asset survives in 5-phase retention window.
    26. `confirmation_docs/PHASE_04_v2_CONFIRMED.md` stays untouched as historical record. 05a ships sibling `PHASE_05a_CONFIRMED.md`.
    27. `tests/_shared/sentinel_paths.py` adds **+1 entry** (`mindsos_cli/commands/metagraph.py`).
    28. `mkdocs.yml` nav: adds entries for new pages (`docs/usage/core/metagraphs.md`, `docs/getting-started/first-metagraph.md`, `docs/api/core/metagraph.md`, `docs/api/core/metaedge.md`, `docs/api/core/metahyperedge.md`).
    29. `docs/dev/release.md` / `docs/dev/contributing.md` / `docs/dev/conventions.md` unchanged in 05a; sub-phase / letter-suffix mention deferred to Phase 38 final pass.
    30. `confirmation_docs/_template.md` and `_template_notes.md` unchanged.

  **Round 1-4 implementation-chat amendments (2026-05-05; 19 picks accepted by user; canonical reasoning + bug ledger at `confirmation_docs/PHASE_05a_IMPLEMENTATION_LOG.md`):**

    31. **P1** — soft-delete fields STRIPPED from MetaEdge / MetaHyperEdge in 05a (overrides N2-B). Phase 10 lands the substrate uniformly across all 4 edge variants per SOFT_DELETE_AUDIT_NOTE recommendation.
    32. **P2** — Q4-B mutation refusals on `mindsos graph` for metagraph-owned graphs include stderr suggestion of the equivalent `mindsos metagraph ...` invocation.
    33. **P3** — ADR-0117 status flips Reserved → **Withdrawn in 05a** (one phase earlier than original CASC-1 placement; code drops the `CompositionalMetaEdge` class in 05a, ADR matches reality).
    34. **P4** — test plan expanded from ~35 to ~63 (then ~99 final with edge-case coverage; user lock "test budget not a concern").
    35. **P5** — `mindsos metagraph reset --force` and `--all` require `--yes` (destructive-command discipline).
    36. **P6** — defer `_compositional` reserved-key addition to 05b alongside the actual flag (avoid dead code in 05a; supersedes the §6 dry-run "05a adds proactively" item).
    37. **P7** — defer `Metagraph.mint_id` to 05b (no 05a consumer; lands with IntergraphEdge factory).
    38. **P8** — `@dataclass(kw_only=True)` on MetaEdge + MetaHyperEdge. Resolves the field-ordering bug introduced by P1 + adding required `type_name` to MetaHyperEdge after a defaulted `graphs` field.
    39. **P9** — `__post_init__` cypher rel-type regex (ADR-0021) on **both** edge types. Closes the dataclass-boundary validation gap on MetaEdge (parent had no `__post_init__`).
    40. **P10** — `mindsos metagraph inspect` + `list` JSON shapes locked. inspect: `{name, metagraph_id, properties, contained_graphs, counts{graphs,metaedges,metahyperedges}, _state_version, state_file}`. list: `{state_dir, metagraphs:[{name, metagraph_id, contained_graphs_count, metaedges_count, metahyperedges_count, _state_version, path}]}`.
    41. **P11** — `Metagraph.add_metaedge(source_graph_id: str, target_graph_id: str, type_name, ...)` takes graph_id STRINGS (not Graph objects). `add_metahyperedge(graph_ids: List[str], ...)` symmetric. Persistence stores graph **names** (CLI translates name→id at boundary; one source of truth: name-keyed JSON).
    42. **P12 / P14** — per-file migration chain modules at `mindsos_cli/migrations/{__init__,graph,schema,metagraph}.py`. Each module exports `MIGRATIONS: List[Callable[[dict], dict]]` and `migrate(state) -> dict`. `state.py`'s `_load_state_file` becomes `_load_and_migrate` calling the per-kind chain. Replaces inline switch statements that grew O(N) per phase. Sentinel paths +4 entries.
    43. **P13** — `RESERVED_PROPERTY_KEYS` (in `mindsos_core/schema/validation.py`) extended with metagraph-structural keys: `_state_version`, `contained_graphs`, `metaedges`, `metahyperedges`, `metagraph_name`. **Deliberately EXCLUDED**: `name` and `properties` (would break existing Phase 04 `test_legacy_node_set_prop_replace_recovers` which uses `name=Alice` as a node property).
    44. **P15** — `add_metaedge` refuses self-loop (`source_graph_id == target_graph_id`). `add_metahyperedge` refuses < 2 members; duplicates within members rejected. Both raise `SchemaError`. Symmetric with INTERGRAPH_EDGES_DESIGN cardinality discipline.
    45. **P16** — `add_graph` invariants locked: `g.identity is mg.identity` post-call (shared reference, not clone); `g.id_strategy` is **untouched** (mixed-strategy metagraphs supported — a metagraph can contain graphs with UUID4 + IRIPassthrough simultaneously). Documented in `docs/concepts/graphs-and-metagraphs.md` and tested.
    46. **P17** — `mindsos metagraph set-prop --on-metagraph` marker flag operates on the metagraph's own ADR-0130 property bag. 3-way mutex `--on-metagraph | --metaedge-id | --metahyperedge-id`. Provides a CLI path for ADR-0130 mid-life updates (not just at create time per CR-A).
    47. **P18** — `metagraph add-graph` two-file write order: graph state file (back-pointer set) FIRST, then metagraph state file. On metagraph-save failure, graph has dangling back-pointer — recovery via DM-A (`mindsos graph detach-metagraph`).
    48. **P19** — `Metagraph.remove_graph(graph_id) -> None` is single-behavior always-cascade. Drops the `cascade` parameter, the `force` flag, and the `RemovalImpact` return entirely from the parent shape (overrides the original N4-A which kept the `cascade=True` parameter unspecified). Phase 10 reintroduces the full ADR-0135 surface.

  **Test fixes for migration-chain semantics (mandated by P12/P14 + amendment 21 audit):**

    49. `tests/phase_03/test_state.py:test_save_and_load_round_trip` — assertion updated to expect migrated dict (v=1 → v=4 with `schema_name=None` + `metagraph_name=None` defaults).
    50. `tests/phase_04/test_state.py:test_save_then_load_schema_state_round_trip` — assertion updated for v=1 → v=2 schema chain (adds `hyperedge_types: []`).
    51. `tests/phase_04/test_state.py:test_graph_state_file_v1_accepts_optional_schema_name` — assertion updated for migrated dict.
    52. `tests/phase_04/test_state.py:test_graph_state_file_v1_legacy_phase_03_loads` — assertion updated; on-disk file unchanged check preserved.
    53. `tests/phase_04/test_state.py:test_graph_state_file_v2_round_trip` — literal `loaded["_state_version"] == 2` removed; dynamic-only.
    54. `tests/phase_04/test_state.py:test_graph_state_v3_round_trip` — same.
    55. `tests/phase_04/test_state.py:test_graph_state_v4_refused` → renamed to `test_graph_state_future_version_refused`; uses `state_mod.GRAPH_STATE_VERSION + 1` instead of literal 4.
    56. `tests/phase_04/test_state.py:test_graph_state_version_constants_split` — `GRAPH_STATE_VERSION == 4`; `METAGRAPH_STATE_VERSION == 1` added.
    57. `tests/phase_04_v2/test_state_v3_round_trip.py:test_v3_hyperedge_carries_type_name` — literal `_state_version == 3` removed.

  **§6 — 05b dry-run appendix (E2 lock; pre-resolves 05b decisions that could retroactively wish for 05a changes):**

    - **05b will add `intergraph_edges` array + optional `schema_name` field** to metagraph state file → bump v=1 → v=2. **05a's v=1 shape is forward-compat:** missing fields default to empty/null. No 05a change needed.
    - **05b's `IntergraphEdgeType` schema validation** uses Phase 04's `PropertyType` 8-variant vocabulary + new `allowed_source_graphs` / `allowed_target_graphs` constraints. **No 05a change needed** (PropertyType already shipped).
    - **05b's `MetagraphSchema`** is attached to Metagraph similarly to how Phase 04's `Schema` attaches to Graph. **05a's `Metagraph` constructor does NOT yet accept a `schema` parameter** — 05b adds it. Tester scripts in 05a don't use `--schema` on `mindsos metagraph create`.
    - **05b's `compositional: bool` flag on `IntergraphEdge`** persists as `_compositional` reserved property. ~~**05a adds `_compositional` to `RESERVED_PROPERTY_KEYS` set proactively**~~ — **superseded by P6 (round 1 amendment)**: 05b adds the reserved-key entry alongside the actual flag implementation. Adding a NEW reserved key is not a breaking change (no extant data uses `_compositional`), so atomicity in 05b is preferable to dead code in 05a.
    - **05c's `compositional` flag immutability semantics** (raises `CompositionalImmutableError`) apply equally to `Metagraph.remove_graph` cascade — if a removed graph had compositional intergraph edges incident on it, removal must propagate the error. **05a's slim `remove_graph` is forward-compat:** it cascades incident metaedges/metahyperedges only (no intergraph edges in 05a). 05b/05c add the intergraph-edge cascade. No 05a change needed.
    - **05b/05c's CLI `--compositional` flag (R2-A)** is a top-level boolean; no 05a action needed.

  **ADR-0020 amendment text (2026-05-05; deferred to Phase 38 file edit):**

  > **2026-05-05 amendment (Phase 05a):** Confirmed in slim CLI surface. `Metagraph` owns one shared `IdentityRegistry`; `add_graph` unifies the graph's registry into the metagraph's; ADR-0138 INFO log fires on non-empty unification. CLI surface (`mindsos metagraph add-graph`) enforces eager id-collision check (Q5-A) before unification. Symmetric for the 05a slim port; behavior matches parent code line 504 onward.

  **ADR-0029 supersession annotation text (2026-05-05; deferred to Phase 38 file edit):**

  > **2026-05-05 supersession (Phase 05a):** ADR-0029 (`:MetagraphSettings` JSON singletons) marked **Superseded by ADR-0130** (Metagraph property bag). Phase 05a ships `Metagraph.properties: Dict[str, Any]` per ADR-0130; the `:MetagraphSettings` mechanism is no longer used. Existing `kl:active_graph_ids` workaround migrates to `mg.properties["kl:active_graph_ids"]` when L2 lands in Phase 14.

  **ADR-0130 acceptance text (2026-05-05; deferred to Phase 38 file edit):**

  > **2026-05-05 acceptance (Phase 05a):** ADR-0130 status flips Proposed → Accepted. `Metagraph.properties: Dict[str, Any]` shipped in 05a slim port; namespaced keys (`kl:`, `server:`, `l3:`, `l4:`, `l5:`); validated via existing `validate_namespaced_properties` (Phase 04). Graph-level property bag (`Graph.properties`) deferred to Phase 10 (separate v=4 → v=5 graph state-file bump avoided in 05a per N1 distinction).

---

### Phase 05b — L1 IntergraphEdge (binary) + IntergraphEdgeType + MetagraphSchema container

  **Status:** Pending (refines after 05a confirms; CASC-1; row LOCKED 2026-05-05 across 6 reanalysis rounds).
  **Branch:** phase-05b
  **Tag on confirm:** phase-05b-confirmed
  **Depends on:** 05a.
  **Layer(s):** L1.
  **Net-new?:** **Yes (substantial).** New `IntergraphEdge` primitive class + factory + persistence + CLI; new `MetagraphSchema` container class; new `IntergraphEdgeType` schema vocabulary; new `mindsos metagraph-schema` top-level CLI subapp; new `metagraph-schema-<n>.json` state-file kind (v=1); metagraph state-file v=1 → v=2 cumulative one-way migration (adds `intergraph_edges` + `schema_name`); 5 new subcommands on `mindsos metagraph` subapp (add-intergraph-edge / remove-intergraph-edge / list-intergraph-edges / attach-schema / detach-schema); 4-way mutex on `set-prop` (extends 05a's 3-way per P17). ADR-0148 first draft (intergraph edge family). ADR-0014 amended (Core primitive list extends with IntergraphEdge). **ADR-0117 already Withdrawn in 05a per round-1 P3 — 05b skips that flip.**

  **Scope narrowed (Pushback 1-C, round 1 lock):** 05b ships `IntergraphEdge` primitive + `IntergraphEdgeType` vocabulary + `MetagraphSchema` container ONLY. **`MetaEdgeType` + `MetaHyperEdgeType` are deferred to 05c** (alongside `IntergraphHyperEdge` + `IntergraphHyperEdgeType` for symmetric typed-edge surface across the metagraph in one phase).

  **Carry-forward from 05a deferrals (round-1 P6 + P7 amendments):**
    - **`_compositional` reserved-key addition** lands in 05b alongside the actual flag implementation (P6 deferred from 05a). Added to `RESERVED_PROPERTY_KEYS` in `mindsos_core/schema/validation.py` AT THE SAME COMMIT as the `compositional: bool` flag on `IntergraphEdge`.
    - **`Metagraph.mint_id(kind, content)`** — ADR-0131 helper. P7 deferred from 05a (no consumer in 05a). Lands here as the IntergraphEdge factory's id-minting path. Slim port from parent `mindsos_core/models/metagraph.py:442`.

  **Locked decisions (6 reanalysis rounds — 2026-05-05; 34 numbered pushbacks; 4 future-work entries filed at `_source_backup/root/mindsos_future_plans.md`):**

    - **Pushback 1-C** — 05b scope narrows to IntergraphEdge primitive + IntergraphEdgeType vocab + MetagraphSchema container ONLY. MetaEdgeType + MetaHyperEdgeType deferred to 05c.
    - **Pushback 2-A** — `compositional: bool` is a top-level dataclass field on `IntergraphEdge` AND a top-level field in `intergraph_edges[]` dict in metagraph state-file v=2. The reserved key `_compositional` is added to `RESERVED_PROPERTY_KEYS` to prevent user-property collision with the future Phase 07 Cypher emit (which uses `_compositional` as a Cypher property on the anchor-node Pattern B).
    - **Pushback 3-A** — New top-level subapp `mindsos metagraph-schema` (parallel to `mindsos schema`) ships in 05b. Bindings via `mindsos metagraph attach-schema --name MG --schema MS` / `detach-schema --name MG`.
    - **Pushback 4-A** — `IntergraphEdgeType.allowed_source_graphs: frozenset[str]` and `allowed_target_graphs: frozenset[str]` are ROLE-based (validate against `Graph.role`). Empty frozenset = any role accepted (matches `EdgeType.allowed_sources` / `allowed_targets` empty-set semantics). `Graph.role=None` is unmatchable when constraint is non-empty.
    - **Pushback 5-A** — `MetagraphSchema.strict: bool = False` mirrors Phase 04 `Schema.strict` exactly: gates property-type validation only. Type-existence (`require_intergraph_edge_type`) is mandatory whenever a MetagraphSchema is attached, regardless of `strict`.
    - **Pushback 6-A** — Compositional immutability has NO escape hatch in 05b. Tester recovery for a compositional-cascade-wedged metagraph: `mindsos metagraph reset --name MG --force --yes` (full destroy and rebuild). Documented in Risks. Future-work option C ("`demote-intergraph-edge` to flip `True → False`") is rejected per design §4.3 invariant.
    - **Pushback 7-A** — Eager attach validation: `attach_schema(MS)` walks every existing `intergraph_edge`, schema-validates each (type-existence + role/name + property-typing if strict); first violation raises with offending edge_id, no mutation. Atomic precheck contract (Pushback 29-A).
    - **Pushback 8-A** — 05c becomes the new heavyweight (3 *EdgeTypes + IntergraphHyperEdge + n-ary enforcement + 2 state-file bumps). Accept rather than re-supersede 05a (cost too high; 05a is `phase-05a-confirmed` + GitHub Released 2026-05-05).
    - **Pushback 9-A** — Eager attach validates only against vocabularies the schema carries. In 05b (only IntergraphEdgeType), existing metaedges/metahyperedges are NOT validated; tester must re-attach in 05c when MetaEdgeType / MetaHyperEdgeType vocabularies arrive.
    - **Pushback 10-A** — `MetagraphSchema(strict=False)` constructor ships from day one. State-file v=1 carries `strict: <bool>` field; rehydration via `MetagraphSchema(strict=state.get("strict", False))`.
    - **Pushback 11-A** — `MetagraphSchema` is reusable across N metagraphs; lives at `metagraph-schema-<name>.json`; metagraph state-file v=2 carries `schema_name: str | null` reference (mirror Phase 04 graph schema).
    - **Pushback 12-A** — One MetagraphSchema attached at most per metagraph; attach-while-attached refuses with `IdentityError: detach first`. Detach is non-destructive (clears `schema_name`; intergraph_edges and their type_names unchanged).
    - **Pushback 13-A** — `add_intergraph_edge` source/target node-existence check is single: `source_node_id in source_graph.nodes` (and same for target). Belt-and-suspenders `mg.identity` check redundant per ADR-0020 unified registry; dropped.
    - **Pushback 14-A** — `IntergraphEdge.edge_id` is ALWAYS minted via `mg.mint_id("intergraph_edge")` which delegates to `mg.id_strategy`. ADR-0131 pluggability story uniform.
    - **Pushback 15-B** — Module file layout: NEW files `mindsos_core/models/intergraph_edge.py` (model + helpers) and `mindsos_core/schema/metagraph_schema.py` (schema container). `IntergraphEdgeType` lives in existing `mindsos_core/schema/types.py` next to `NodeType` / `EdgeType` / `HyperEdgeType`. `Metagraph` factory methods stay in `mindsos_core/models/metagraph.py` (extend by ~150 lines).
    - **Pushback 16-A** — 14-step validation order at `add_intergraph_edge` locked in code-comment + row appendix (below). Documented for future cascade rows.
    - **Pushback 17-A** — `Metagraph.remove_graph` runs an atomic precheck pass: walks all incident intergraph_edges; if ANY has `compositional=True` → raise `CompositionalImmutableError` with offending edge_id BEFORE any mutation. State unchanged on raise.
    - **Pushback 18-A** — `RESERVED_PROPERTY_KEYS` extends with `intergraph_edges` (top-level metagraph state v=2 field) AND `schema_name` (top-level metagraph state v=2 field; also already top-level on graph state v=2 from Phase 04 — reserving in 05b creates a Phase 04→05b backward-compat subtlety, but theoretical zero-incidence; accepted for consistency).
    - **Pushback 19-B** — Eager attach emits stderr warning when schema references roles that no contained graph satisfies: `warning: schema 'X' references roles {set} not satisfied by any contained graph; intergraph edges of types using these constraints will refuse until matching graphs are added.` Non-blocking.
    - **Pushback 20-A** — `mindsos metagraph-schema reset` orphan check mirrors 05a Q6-A + Phase 04 schema reset: `--name X` walks every `metagraph-*.json`; refuses with exit 1 if any has `schema_name == X`; `--force --yes` strips back-pointers from referenced metagraphs (warning to stderr) then deletes; `--all` symmetric.
    - **Pushback 22-A** — `IntergraphEdge.compositional` immutability enforced via `__setattr__` override on the dataclass. Post-`__post_init__` write to `compositional` raises `CompositionalImmutableError`. Other field mutations (`label`, `properties` via `update_intergraph_edge_properties`) work normally. ~15 LOC + 2 tests.
    - **Pushback 23-A** — Schema mutation while attached: stderr warning at `mindsos metagraph-schema add-intergraph-edge-type` listing every metagraph currently attached. Documented in Risks as carry-forward Phase 04 footgun.
    - **Pushback 24-hybrid** — Empty MetagraphSchema attach: succeeds with stderr warning ("no IntergraphEdgeType entries; attach validates nothing"). Pre-existing intergraph_edges with type_name not in vocab → in strict mode REFUSE attach (Phase 04 precedent); in non-strict, succeed silently.
    - **Pushback 25-A** — `Graph.role` mutability is doc-convention-immutable; no `__setattr__` enforcement in 05b (would trigger Phase 03 retroactive supersession; cost too high). Schema validation against role is point-in-time at attach + each `add_intergraph_edge`. Filed Pushback 25-B as future work (`_source_backup/root/mindsos_future_plans.md` — "Schema invariant enforcement").
    - **Pushback 26-A** — Detach-then-attach incompatible schema: refuse cleanly per Pushback 7-A eager-validation contract. Tester recovery is manual (`remove-intergraph-edge` for each offender, or reset for compositional-blocked cases). `--check-only` dry-run flag deferred to Phase 11 (ADR-0134 schema-migrate territory).
    - **Pushback 27-A** — `mindsos metagraph set-prop` mutex extends from 05a's 3-way (`--on-metagraph | --metaedge-id | --metahyperedge-id`) to 4-way by adding `--intergraph-edge-id`. When `compositional=True` on the targeted intergraph_edge, `set-prop` refuses with `CompositionalImmutableError` per design §4.3.
    - **Pushback 28-A + DMS-A** — Stale `schema_name` recovery: subsequent schema-needing operation on a metagraph whose `schema_name` references a missing schema state file refuses with structured pointer to recovery. Recovery via `mindsos metagraph detach-schema --name MG` — implemented as a unified command with internal raw-JSON fallback (DMS-A): try normal detach (load schema → clear reference); on schema-missing → fall through to raw-JSON path (operate on metagraph state file directly, bypass schema rehydration), clear `schema_name`. Single tester verb, two failure modes.
    - **Pushback 29-A** — Attach atomicity contract: `Metagraph.attach_schema(MS, *, schema_name)` runs precheck pass over all intergraph_edges; first violation raises with offending edge_id; NO mutation to metagraph state file or in-memory metagraph on failure. On all-pass, sets `mg.schema_name = MS.name`, caches `mg.schema = MS instance`, writes state file once. Mirrors Phase 04 graph attach-schema atomicity.
    - **Pushback 30-A** — `mindsos metagraph attach-schema --json` shape: `{metagraph: <name>, previous_schema: <name|null>, new_schema: <name>, validated_intergraph_edges: <count>}`. Mirror Phase 04 graph attach-schema shape with the 05b-specific count field added.
    - **Pushback 31-A** — `IntergraphEdge.label` is set-at-create only (matches 05a metaedge / metahyperedge precedent). No `update-intergraph-edge-label` CLI verb in 05b. Tester recovery: `remove-intergraph-edge` then `add-intergraph-edge --intergraph-edge-id <orig-id>`. Filed Pushback 31-B as future work.
    - **Pushback 32-A + 32-D** — `Metagraph.attach_schema(schema: MetagraphSchema, *, schema_name: str)` — explicit keyword name (model layer decoupled from `state_mod`). Re-attach with same `schema_name` runs FRESH eager validation (NOT silent no-op); raises if schema-mutation drift surfaces; on all-pass, idempotent at state-file level. Supersedes Pushback 12-A's "idempotent re-attach = no-op" framing.
    - **Pushback 33-A** — `mindsos metagraph` subapp will hit ~18 subcommands after 05b, ~22 after 05c, ~30+ after Phase 10. 05b accepts the flat surface; documented in Risks. Filed Pushback 33-B (CLI two-level reorg) as future work.
    - **Pushback 34-A + filing as 34-B** — No `remove-intergraph-edge-type` CLI verb in 05b (would create asymmetry with Phase 04 graph-schema vocabularies that also lack `remove-*-type`). Tester recovery: `mindsos metagraph-schema reset --name MS --force --yes`. Filed Pushback 34-B (symmetric backfix across all schema kinds) as future work.

  **Features in scope (capability-level — locked):**

    - `IntergraphEdge` dataclass — `@dataclass(kw_only=True)` (P8 pattern); fields per design §2.1 (10-field spec, soft-delete substrate dormant per Pushback-9 / SOFT_DELETE_AUDIT_NOTE deferral to Phase 10):
      - `source_graph_id: str` (required; must be contained graph ≠ target_graph_id).
      - `source_node_id: str` (required; must exist in `source_graph.nodes`).
      - `target_graph_id: str` (required).
      - `target_node_id: str` (required; must exist in `target_graph.nodes`).
      - `type_name: str` (required; ADR-0021 cypher rel-type regex enforced at `__post_init__`).
      - `compositional: bool = False` (immutable post-create per Pushback 22-A `__setattr__` override).
      - `edge_id: str = field(default_factory=...)` — auto-minted via `mg.mint_id("intergraph_edge")` when factory called; field carries default for direct-construction paths (rehydration/tests).
      - `label: Optional[str] = None`.
      - `properties: Dict[str, Any] = field(default_factory=dict)` — namespaced; reserved-key-aware via `validate_user_properties(scope="intergraph_edge")`.
      - Soft-delete fields `deprecated_at` / `disputed_at` — NOT shipped in 05b (per P1 + SOFT_DELETE_AUDIT_NOTE; lands uniformly across all 4 edge variants in Phase 10).
      - `__post_init__` runs ADR-0021 cypher rel-type regex (P9 pattern); `__setattr__` enforces `compositional` immutability (Pushback 22-A); `__hash__` and `__eq__` by `edge_id`; `__repr__` slimmed.
    - `IntergraphEdgeType` frozen dataclass — fields:
      - `name: str` (required; ADR-0021 regex; `__post_init__` validates).
      - `allowed_source_types: FrozenSet[str] = frozenset()` (Node type_name; empty = any).
      - `allowed_target_types: FrozenSet[str] = frozenset()` (Node type_name; empty = any).
      - `allowed_source_graphs: FrozenSet[str] = frozenset()` (Graph.role; empty = any; `role=None` unmatchable when non-empty per Pushback 4-A).
      - `allowed_target_graphs: FrozenSet[str] = frozenset()` (Graph.role; empty = any).
      - `property_types: Dict[str, PropertyType] = field(default_factory=dict)` (Phase 04 8-variant vocab).
      - `description: Optional[str] = None`.
    - `MetagraphSchema` class — basename-keyed (no `name` field; mirror Phase 04 Schema):
      - `__init__(*, strict: bool = False)` constructor (Pushback 5-A + 10-A).
      - `_intergraph_edge_types: Dict[str, IntergraphEdgeType]` storage.
      - `add_intergraph_edge_type(iet: IntergraphEdgeType)` — refuses on duplicate name (`UnknownTypeError`); per Pushback 23-A, prints stderr warning listing attached metagraphs (which the CLI populates by walking metagraph files; the model layer just provides the API).
      - `require_intergraph_edge_type(name: str) -> IntergraphEdgeType`.
      - `intergraph_edge_types` property → `Mapping[str, IntergraphEdgeType]` (defensive copy).
      - `validate_intergraph_edge(type_name, source_type_name, target_type_name, source_role, target_role)` → enforces allowed_*_types + allowed_*_graphs (empty = any).
      - `validate_intergraph_edge_properties(type_name, properties)` → strict-only property-type check (Pushback 5-A).
    - `Metagraph.add_intergraph_edge(source_graph_id, source_node_id, target_graph_id, target_node_id, type_name, *, label=None, properties=None, compositional=False, edge_id=None) -> IntergraphEdge` — 14-step validation order (appendix §A below). Returns the constructed edge after registration in `mg.identity`.
    - `Metagraph.remove_intergraph_edge(edge_id) -> None` — refuses with `CompositionalImmutableError` if `compositional=True`; otherwise unregisters from `mg.identity` and removes from `mg.intergraph_edges`.
    - `Metagraph.update_intergraph_edge_properties(edge_id, properties, *, replace=False) -> IntergraphEdge` — refuses with `CompositionalImmutableError` if `compositional=True`; otherwise merges (default) or replaces; mirror of 05a's `update_metaedge_properties`.
    - `Metagraph.iter_intergraph_edges() -> Iterator[IntergraphEdge]` — no `include_deprecated` kwarg in 05b (Phase 10 adds).
    - `Metagraph.attach_schema(schema: MetagraphSchema, *, schema_name: str) -> MetagraphSchema` — eager validation pass (Pushback 7-A + 9-A + 17-A + 19-B + 24-hybrid + 29-A + 32-D). Returns the schema instance for chaining; sets `mg.schema_name = schema_name` and `mg.schema = schema`.
    - `Metagraph.detach_schema() -> Optional[str]` — clears `mg.schema_name` to `None` and `mg.schema` to `None`; returns previous schema_name (or `None` if not attached); refuses if no schema attached with `IdentityError` (Pushback 32-D carry-forward).
    - `Metagraph.remove_graph(graph_id) -> None` — extends 05a's slim cascade (P19) with the Pushback 17-A precheck pass for compositional intergraph_edges. Cascade order: precheck (raise on first compositional incident) → cascade-remove non-compositional incident metaedges + metahyperedges + intergraph_edges → unregister graph's owned ids → delete graph entry.
    - `Metagraph.mint_id(kind: str, content: Optional[str] = None) -> str` — ADR-0131 helper; delegates to `self.id_strategy.mint(kind, content)`; defaults to UUID4 via `UUID4Strategy` (already locked in 05a P16).
    - `Metagraph.schema: Optional[MetagraphSchema]` — in-memory cached instance (set by `attach_schema`; cleared by `detach_schema`).
    - `Metagraph.schema_name: Optional[str]` — persisted reference.
    - `Metagraph.intergraph_edges: Dict[str, IntergraphEdge]` — in-memory storage keyed by `edge_id`.
    - **CLI** — `mindsos metagraph` subapp adds 5 subcommands (Pushback 27-A 4-way mutex on existing `set-prop`):
      - `add-intergraph-edge --name MG --source-graph G --source-node N --target-graph G --target-node N --type T [--label L] [--prop k=v]... [--compositional] [--intergraph-edge-id ID] [--json]`.
      - `remove-intergraph-edge --name MG --intergraph-edge-id ID [--json]`.
      - `list-intergraph-edges --name MG [--json]`.
      - `attach-schema --name MG --schema MS [--json]` — refuses if another schema attached (per Pushback 12-A + 32-A); eager validation (per 7-A + 9-A); structured JSON output per Pushback 30-A.
      - `detach-schema --name MG [--json]` — DMS-A unified command: try normal detach, on schema-missing fall through to raw-JSON path; refuses with exit 1 if no schema attached (Pushback 32-D / 28-A).
      - `set-prop` extends to 4-way mutex: `(--on-metagraph | --metaedge-id | --metahyperedge-id | --intergraph-edge-id) --prop k=v ... [--replace]` (Pushback 27-A).
    - **CLI** — NEW top-level `mindsos metagraph-schema` subapp (Pushback 3-A) with subcommands:
      - `create --name MS [--strict] [--json]`.
      - `inspect --name MS [--json]`.
      - `list [--json]`.
      - `reset (--name MS | --all) [--force] [--yes] [--json]` — orphan check (Pushback 20-A).
      - `add-intergraph-edge-type --schema MS --type-name T [--allowed-source-type NT]... [--allowed-target-type NT]... [--allowed-source-graph ROLE]... [--allowed-target-graph ROLE]... [--prop-type k=PT]... [--description STR] [--json]` — emits stderr warning listing attached metagraphs per Pushback 23-A.
    - **State files**:
      - `metagraph-<n>.json` v=1 → v=2 cumulative one-way migration: adds `intergraph_edges: []` (default) and `schema_name: null` (default). Loaders accept v=1 ∪ v=2; writers emit v=2.
      - `metagraph-schema-<n>.json` v=1 — NEW state-file kind. Migration chain at `mindsos_cli/migrations/metagraph_schema.py` (empty in 05b).
    - **Doctor self-test extension** — None (05a's `phase\d{2}([a-z]|-v\d+)?-(prod|test)` regex already covers `phase05b-prod` / `phase05b-test`).

  **Modules touched (locked):**

    - `mindsos_core/models/intergraph_edge.py` — **NEW file**. `IntergraphEdge` dataclass + `__setattr__` immutability override + helpers.
    - `mindsos_core/models/metagraph.py` — extends with `add_intergraph_edge` / `remove_intergraph_edge` / `update_intergraph_edge_properties` / `iter_intergraph_edges` / `attach_schema` / `detach_schema` / `mint_id` factory methods; extends `remove_graph` cascade with Pushback 17-A precheck for compositional intergraph_edges; adds `intergraph_edges` / `schema` / `schema_name` instance state.
    - `mindsos_core/schema/metagraph_schema.py` — **NEW file**. `MetagraphSchema` class + validators.
    - `mindsos_core/schema/types.py` — extends with `IntergraphEdgeType` frozen dataclass.
    - `mindsos_core/schema/validation.py` — extends `RESERVED_PROPERTY_KEYS` with `_compositional` (P6 carry-forward) + `intergraph_edges` (Pushback 18-A) + `schema_name` (Pushback 18-A).
    - `mindsos_core/exceptions.py` — re-adds `CompositionalImmutableError` (R3-B from 05a stripped it; 05b puts it back).
    - `mindsos_core/__init__.py` — re-exports `IntergraphEdge`, `IntergraphEdgeType`, `MetagraphSchema`, `CompositionalImmutableError`.
    - `mindsos_core/schema/__init__.py` — re-exports `IntergraphEdgeType`, `MetagraphSchema`.
    - `mindsos_cli/commands/metagraph.py` — extends with 5 new subcommands + 4-way set-prop mutex; extends `inspect` / `list` JSON shapes (P10 amendment) with `intergraph_edges` count + `schema_name` field.
    - `mindsos_cli/commands/metagraph_schema.py` — **NEW file**. Typer subapp; 5 subcommands (create / inspect / list / reset / add-intergraph-edge-type).
    - `mindsos_cli/state.py` — adds `METAGRAPH_SCHEMA_STATE_VERSION = 1` + `metagraph_schema_file_path` / `iter_metagraph_schema_files` / `load_metagraph_schema_state` / `save_metagraph_schema_state` / `delete_metagraph_schema_state_file` helpers.
    - `mindsos_cli/migrations/metagraph.py` — adds `_v1_to_v2(state)` step (sets `intergraph_edges: []` + `schema_name: None` defaults); `CURRENT_VERSION = 2`.
    - `mindsos_cli/migrations/metagraph_schema.py` — **NEW file**. Empty `MIGRATIONS = []`; `CURRENT_VERSION = 1`.
    - `mindsos_cli/app.py` — `register_metagraph_schema_app` wired.
    - `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05b"`.
    - `mindsos_cli/manifest.toml` — `[mindsos] phase = "05b"`; `version = "0.0.0+phase05b"`.
    - `pyproject.toml` — version + description bumped.
    - `docker-compose.yml` — image tags `mindsos:phase05b-prod` / `mindsos:phase05b-test`.
    - `Dockerfile` — comment lines bumped (Phase 05a → Phase 05b references); COPY block reaches new `mindsos_core/models/intergraph_edge.py`, `mindsos_core/schema/metagraph_schema.py`, `mindsos_cli/commands/metagraph_schema.py`, `mindsos_cli/migrations/metagraph_schema.py` via existing wildcards.
    - `tests/_shared/sentinel_paths.py` — **+4 entries**: `mindsos_core/models/intergraph_edge.py`, `mindsos_core/schema/metagraph_schema.py`, `mindsos_cli/commands/metagraph_schema.py`, `mindsos_cli/migrations/metagraph_schema.py`.

  **Persistence layout (locked):**

    - **Metagraph state-file v=2 JSON shape** (extends v=1 with `intergraph_edges` + `schema_name`):
      ```json
      {"_state_version": 2,
       "metagraph_id": "<uuid4>", "name": "<n>",
       "properties": {"k": "<value>"},
       "schema_name": "<schema-name-or-null>",
       "contained_graphs": ["<graph-name>", ...],
       "metaedges": [...],
       "metahyperedges": [...],
       "intergraph_edges": [
         {"edge_id": "...",
          "source_graph": "<gname>", "source_node": "<node-id>",
          "target_graph": "<gname>", "target_node": "<node-id>",
          "type_name": "<UPPER>",
          "compositional": <bool>,
          "label": "<text-or-null>", "properties": {...}}
       ]}
      ```
      Top-level lists byte-stable sorted (intergraph_edges by edge_id; consistent with metaedges / metahyperedges from 05a). Atomic write via `<path>.tmp + os.replace`.
    - **MetagraphSchema state-file v=1 JSON shape** (NEW file kind):
      ```json
      {"_state_version": 1,
       "name": "<n>", "strict": <bool>,
       "intergraph_edge_types": [
         {"name": "<UPPER>",
          "allowed_source_types": [...sorted],
          "allowed_target_types": [...sorted],
          "allowed_source_graphs": [...sorted],
          "allowed_target_graphs": [...sorted],
          "property_types": {"k": "<PropertyType.value>"},
          "description": "<text-or-null>"}
       ]}
      ```
      Top-level list byte-stable sorted by `name`. Atomic write.
    - **Cumulative migration on metagraph state-file:** 05b binary reads v=1 ∪ v=2 (one-pass: populate `intergraph_edges=[]` + `schema_name=None` for v=1 default); first mutation writes v=2.
    - **Strict version contract:** Phase 05a binary loading v=2 file rejects (`this CLI supports v1` message). Recovery: hand-edit JSON downgrade (drop `intergraph_edges` + `schema_name` fields, set `_state_version: 1`).
    - **Graph state-file unchanged in 05b** — still v=4 (IntergraphEdges live on metagraph, not graph).

  **Automated tests (location + intent — locked; test budget unlimited per `feedback_test_budget_unlimited.md`):**

    - `tests/phase_05b/` — projected ~120-150 tests across ~12 files; final count whatever coverage requires:
      - `test_intergraph_edge.py` — dataclass kw_only, post_init regex, `__setattr__` compositional immutability (Pushback 22-A), edge_id auto-mint, label round-trip, properties round-trip, source≠target enforcement, source/target node existence checks (Pushback 13-A).
      - `test_intergraph_edge_type.py` — frozen dataclass, ADR-0021 regex on name, 8 PropertyType variants, role-based allowed_source/target_graphs, empty-set semantics (Pushback 4-A).
      - `test_metagraph_schema.py` — strict/non-strict modes, add_intergraph_edge_type happy + duplicate refusal, state-file round-trip, N-metagraphs-share-one-schema reuse (Pushback 11-A).
      - `test_metagraph_schema_attach.py` — happy path, eager validation skips metaedges/metahyperedges (Pushback 9-A), role-mismatch attach succeeds with stderr warning (Pushback 19-B), one-attached-at-most refusal (Pushback 12-A), detach clears + re-attach is fresh validation (Pushback 32-D), atomic precheck on failure (Pushback 29-A), Pushback 30-A JSON shape.
      - `test_compositional.py` — flag immutability via `__setattr__` (Pushback 22-A), factory accepts compositional=True, compositional edge refuses remove + set-prop (design §4.3), `remove_graph` cascade precheck (Pushback 17-A) atomic refusal, non-compositional cascade-removes cleanly.
      - `test_intergraph_edge_state_v2.py` — state-file v=2 round-trip with intergraph_edges + schema_name, byte-stable sort, atomic write.
      - `test_metagraph_migration_v1_to_v2.py` — v=1 load+populate intergraph_edges=[] + schema_name=null, first mutation upgrades to v=2, idempotent on v=2, forward-version v=3 refused.
      - `test_metagraph_schema_state_v1.py` — schema state-file shape, byte-stable sort, atomic write.
      - `test_cli_intergraph_edge.py` — add-intergraph-edge happy + --compositional flag, remove refuses on compositional, set-prop --intergraph-edge-id (Pushback 27-A 4-way mutex), list-intergraph-edges JSON shape, role-based schema rejection, properties round-trip, edge-id override.
      - `test_cli_metagraph_schema.py` — create / inspect / list / reset orphan check / reset --force --yes / add-intergraph-edge-type / attach-schema / detach-schema (DMS-A raw-JSON path).
      - `test_mint_id.py` — UUID4 default + custom IdStrategy delegation, mixed-strategy metagraph round-trip.
      - `test_reserved_keys.py` — `_compositional` rejected as user property, `intergraph_edges` rejected, `schema_name` rejected.
      - `test_validation_order.py` — Pushback 16-A 14-step order; tests fail with the most specific first violation.
      - `test_dms_a.py` — stale `schema_name` recovery via unified detach-schema fallback (Pushback 28-A).
    - **Audit pass (pre-implementation):** review every `tests/phase_05a/test_state*.py` for hard-coded `_state_version: 1` (metagraph) constants; update to use `state_mod.METAGRAPH_STATE_VERSION` dynamically. Symmetric with 05a P14 / 04-v2 audit. Lock as pre-implementation task.

  **Confirmation command:**
    `mindsos confirm-phase --phase 05b --notes-file notes-phase-05b.md`
    (Init shape: `--init-notes 05b` is canonical; backward-compat alias `phase-05b` per 04-v2 / 05a pattern. Manifest stores `[mindsos] phase = "05b"`.)

  **Pass criterion:**

    - Tester can create a metagraph schema (`metagraph-schema create`), add an IntergraphEdgeType with role-based source/target constraints, attach to a metagraph (`metagraph attach-schema`), add an intergraph edge between two contained graphs that satisfies the role constraints, and observe round-trip persistence at metagraph state v=2.
    - Tester sees structured refusal when add-intergraph-edge violates type-existence (no schema match) / role mismatch (graph role not in `allowed_source_graphs`) / cypher regex (lowercase type) / self-graph (source == target).
    - Tester sees `CompositionalImmutableError` on attempts to remove or set-prop on a compositional intergraph edge; tester can recover only via `mindsos metagraph reset --name MG --force --yes` (per Pushback 6-A).
    - Tester sees atomic refusal when `metagraph remove-graph` would orphan a compositional intergraph edge (Pushback 17-A); state file unchanged on raise.
    - Tester sees stderr warning when attach-schema succeeds with role gaps (Pushback 19-B); same warning when add-intergraph-edge-type runs while schema is attached to N metagraphs (Pushback 23-A).
    - Tester recovers stale `schema_name` reference via `mindsos metagraph detach-schema --name MG` (DMS-A; works even when schema state file is missing).
    - Phase 05a v=1 metagraph state file loads cleanly under 05b binary; first mutation upgrades to v=2.
    - All Phase 03 + Phase 04 + Phase 04-v2 + Phase 05a + Phase 05b tests pass cumulatively in-container.
    - **Cumulative tests pass: ≥ Phase 05a baseline (528 + 2 skipped) + ~120-150 Phase 05b added; tester records actual count in `PHASE_05b_CONFIRMED.md`** (sandbox-projected: ~648-678 + 2 skipped).

  **Risks / known issues to watch:**

    - **v=1 → v=2 metagraph state-file migration is one-way.** 05b binary touching a Phase 05a v=1 file upgrades on first mutation; Phase 05a binary then refuses with `this CLI supports v1` message. Recovery: hand-edit JSON downgrade (drop `intergraph_edges` + `schema_name`, set `_state_version: 1`).
    - **Schema mutation while attached** is a documented carry-forward footgun (Pushback 23-A). Adding a new IntergraphEdgeType to a schema attached to N metagraphs does NOT trigger re-validation; existing intergraph_edges retain their type_names. Tester must re-attach to surface drift.
    - **Compositional cascade wedges metagraphs** (Pushback 6-A + 17-A): a compositional intergraph_edge cannot be removed; if its source or target graph needs removal, metagraph is wedged. Recovery is full reset (`mindsos metagraph reset --name MG --force --yes`) — tester loses all metagraph contents.
    - **`Graph.role` mutation post-attach** drifts schema validation silently (Pushback 25-A). Doc-convention immutable; no `__setattr__` enforcement in 05b. Tester scripts mutating role programmatically void the schema validation invariant.
    - **`mindsos metagraph` subapp size** grows to ~18 subcommands after 05b; 22+ after 05c; 30+ after Phase 10 (Pushback 33-A). Filed as future work (Pushback 33-B in `_source_backup/root/mindsos_future_plans.md`).
    - **No `remove-intergraph-edge-type` verb** (Pushback 34-A); typo recovery requires `mindsos metagraph-schema reset --name MS --force --yes` and full vocabulary rebuild. Filed as future work (Pushback 34-B).
    - **No `update-intergraph-edge-label` verb** (Pushback 31-A); label-typo recovery requires remove-and-re-add with `--intergraph-edge-id <orig>` override. Filed as future work (Pushback 31-B).
    - **Stale `schema_name` reference** if tester deletes a `metagraph-schema-X.json` state file by hand: subsequent schema-needing operation refuses with structured pointer to `mindsos metagraph detach-schema --name MG`; DMS-A recovery (Pushback 28-A) clears the stale reference via raw-JSON path.
    - **Cross-metagraph intergraph edges are out-of-contract** (XRef = Phase 09). Per ADR-0020, each metagraph has its own IdentityRegistry; an `add_intergraph_edge` call with a node_id from a different metagraph fails identity lookup.
    - **J-02 carry-forward** — no advisory locks on state files; debug-only single-tester surface. Phase 07 ships proper concurrency.

  **Doc sections this phase confirms:**

    - `docs/concepts/intergraph-edges.md` — full (NEW). `last_confirmed_phase: 05b`. Concept overview; cat=c+a+t example reserved for 05c (when IntergraphHyperEdge ships); 05b focuses on binary 1-1 case.
    - `docs/usage/core/metagraph-schema.md` — full (NEW). `last_confirmed_phase: 05b`. Covers `mindsos metagraph-schema` subapp + attach/detach + role-based constraints + Pushback-23 mutation footgun + reset orphan check.
    - `docs/usage/core/metagraphs.md` — amended (Phase 05a baseline) with intergraph-edge subcommands + DMS-A recovery + 4-way set-prop mutex + state-file v=1→v=2 migration. `last_confirmed_phase: 05b`.
    - `docs/api/core/intergraph-edge.md` — full (NEW). API reference. `last_confirmed_phase: 05b`.
    - `docs/api/core/metagraph-schema.md` — full (NEW). API reference. `last_confirmed_phase: 05b`.
    - `docs/api/core/metagraph.md` — amended (Phase 05a baseline) with new factory methods + attach_schema / detach_schema / mint_id / extended remove_graph cascade. `last_confirmed_phase: 05b`.
    - `docs/changelog/CHANGELOG.md` — Phase 05b entry appended.
    - `mkdocs.yml` — nav entries for new pages.
    - **ADR-0148** drafted (full text in row appendix §B below; file edit Phase 38).
    - **ADR-0014** amended (full amendment text in row appendix §C below; file edit Phase 38).
    - **ADR-0117** status edit deferred to Phase 38 per locked precedent — annotation says **Withdrawn in 05a**, not 05b.
    - **ADR-0131** confirmed (mint_id ships; pluggable IdStrategy reaches its first non-uuid consumer — IntergraphEdge factory).

  **Breaking changes from Phase 05a:**

    - `Metagraph` state-file v=1 → v=2 (one-way; documented above).
    - `mindsos metagraph set-prop` mutex extends from 3-way to 4-way (Pushback 27-A); tester scripts using only 05a's 3-way are forward-compatible (the 4th option is additive); error message text changes.
    - `mindsos metagraph inspect --json` shape gains `counts.intergraph_edges` field + `schema_name` field (additive; tester scripts reading the 05a shape continue to work).
    - `mindsos metagraph list --json` shape gains `intergraph_edges_count` + `schema_name` per entry (additive).
    - `mindsos metagraph remove-graph --json` gains `cascaded_intergraph_edges` field (additive).
    - New top-level subapp `mindsos metagraph-schema` registered (no conflict with existing surface).

  **Final amendments (2026-05-05 — locked across 6 reanalysis rounds; 34 numbered pushbacks):**

    1. **Pushback 1-C** — 05b scope narrowed to IntergraphEdge primitive + IntergraphEdgeType + MetagraphSchema container; MetaEdgeType + MetaHyperEdgeType deferred to 05c.
    2. **Pushback 2-A** — `compositional` top-level dataclass field; `_compositional` reserved key for future Cypher emit.
    3. **Pushback 3-A** — New `mindsos metagraph-schema` subapp + `attach-schema` / `detach-schema` on `metagraph`.
    4. **Pushback 4-A** — `allowed_source_graphs` / `allowed_target_graphs` ROLE-based; `role=None` unmatchable when constraint non-empty.
    5. **Pushback 5-A** — `MetagraphSchema.strict` mirrors Phase 04 `Schema.strict` (gates property typing only).
    6. **Pushback 6-A** — No escape hatch for compositional cascade; tester recovery is full reset.
    7. **Pushback 7-A** — Eager attach validation; first violation raises with offending edge_id.
    8. **Pushback 8-A** — 05c becomes the heavyweight; accept rather than re-supersede 05a.
    9. **Pushback 9-A** — Eager attach validates only against vocabularies the schema carries; metaedges/metahyperedges not validated in 05b.
    10. **Pushback 10-A** — `MetagraphSchema(strict)` ships from day one in state file.
    11. **Pushback 11-A** — `MetagraphSchema` reusable across N metagraphs; basename-keyed state file.
    12. **Pushback 12-A** — One MetagraphSchema attached per metagraph; attach-while-attached refuses.
    13. **Pushback 13-A** — Single source/target node existence check; redundant `mg.identity` check dropped.
    14. **Pushback 14-A** — `IntergraphEdge.edge_id` minted via `mg.mint_id` always; ADR-0131 uniform.
    15. **Pushback 15-B** — New files `intergraph_edge.py` + `metagraph_schema.py`; `IntergraphEdgeType` in existing `types.py`.
    16. **Pushback 16-A** — 14-step validation order locked in code-comment + appendix §A.
    17. **Pushback 17-A** — `remove_graph` atomic precheck for compositional intergraph_edges.
    18. **Pushback 18-A** — `RESERVED_PROPERTY_KEYS` extended with `intergraph_edges` + `schema_name`.
    19. **Pushback 19-B** — Eager attach emits stderr warning on role-mismatch; non-blocking.
    20. **Pushback 20-A** — `metagraph-schema reset` orphan check mirrors 05a Q6-A.
    21. **Pushback 22-A** — `__setattr__` override on `IntergraphEdge` for `compositional` immutability.
    22. **Pushback 23-A** — Schema mutation while attached: stderr warning carry-forward Phase 04 footgun.
    23. **Pushback 24-hybrid** — Empty MetagraphSchema attach: succeeds with warning + strict-mode add-time refusal.
    24. **Pushback 25-A** — `Graph.role` doc-convention immutable; 25-B filed future work.
    25. **Pushback 26-A** — Detach-then-attach incompatible schema: refuse cleanly per 7-A.
    26. **Pushback 27-A** — 4-way mutex on `set-prop` (extends 05a 3-way).
    27. **Pushback 28-A + DMS-A** — Stale `schema_name` recovery via unified `detach-schema` with raw-JSON fallback.
    28. **Pushback 29-A** — Eager attach atomicity contract; state unchanged on raise.
    29. **Pushback 30-A** — `attach-schema --json` shape with `validated_intergraph_edges` count.
    30. **Pushback 31-A** — Label set-at-create only; 31-B filed future work.
    31. **Pushback 32-A + 32-D** — `attach_schema(schema, *, schema_name)` model API; re-attach is fresh validation.
    32. **Pushback 33-A** — `mindsos metagraph` subapp accepts flat surface; 33-B filed future work.
    33. **Pushback 34-A + filing** — No `remove-*-type` in 05b; 34-B filed future work for symmetric backfix.
    34. Test budget: unlimited per `feedback_test_budget_unlimited.md` (2026-05-05 lock); ~120-150 sandbox projection; final count whatever coverage requires.

  **§A — 14-step validation order at `Metagraph.add_intergraph_edge` (Pushback 16-A; appendix lock):**

    1. `source_graph_id` must be a key in `mg.graphs` → else `IdentityError`.
    2. `target_graph_id` must be a key in `mg.graphs` → else `IdentityError`.
    3. `source_graph_id != target_graph_id` → else `SchemaError("source and target must be different graphs")`.
    4. `source_node_id` must be a key in `mg.graphs[source_graph_id].nodes` → else `IdentityError` (single check per Pushback 13-A).
    5. `target_node_id` must be a key in `mg.graphs[target_graph_id].nodes` → else `IdentityError`.
    6. `type_name` must satisfy ADR-0021 cypher rel-type regex — enforced at `IntergraphEdge.__post_init__` after dataclass instantiation (P9 pattern); raises `CypherError`.
    7. `validate_user_properties(properties or {}, scope="intergraph_edge")` → reserved-key + primitive-only check; raises `PropertyShapeError`.
    8. (if `mg.schema is not None`) `mg.schema.require_intergraph_edge_type(type_name)` → raises `UnknownTypeError` if vocab missing.
    9. (if attached) `mg.schema.validate_intergraph_edge(type_name, source_node.type_name, target_node.type_name, source_graph.role, target_graph.role)` → raises `UnknownTypeError` if any constraint fails (allowed_source_types / allowed_target_types / allowed_source_graphs / allowed_target_graphs).
    10. (if attached and `mg.schema.strict`) `mg.schema.validate_intergraph_edge_properties(type_name, properties)` → raises `PropertyShapeError`.
    11. `edge_id = mg.mint_id("intergraph_edge")` (or use caller-supplied `edge_id` if not None — same unregister-and-re-register dance as 05a metaedge override).
    12. Construct `IntergraphEdge(...)` (dataclass `__post_init__` runs cypher regex + `_initialized = True` for `__setattr__` override).
    13. `mg.identity.register(edge_id)` → raises `IdentityError` on collision.
    14. `mg.intergraph_edges[edge_id] = edge`. Return edge.

  **§B — ADR-0148 first draft (full text; file edit Phase 38):**

  > **ADR-0148: Intergraph Edge family**
  >
  > **Status:** Accepted (Phase 05b first draft 2026-05-05; amendment in Phase 05c for `IntergraphHyperEdge`).
  >
  > **Context.** L1 Core ships node-level edge primitives within a single Graph (`Edge` for binary, `HyperEdge` for n-ary, both Phase 03) and graph-level edge primitives within a single Metagraph (`MetaEdge` for binary, `MetaHyperEdge` for n-ary, both Phase 05a). Cross-metagraph node references (`XRef`) ship in Phase 09. The remaining gap is **node-level edges that span graphs within a single metagraph** — needed for use cases like (a) lexical-to-conceptual alignment (lexicon-graph node `cat` → concepts-graph node `Cat#1`), (b) compositional identity (word-graph `cat` decomposed into letter-graph `c`+`a`+`t`), (c) cross-graph relational data without graph-level reification. ADR-0117's original `CompositionalMetaEdge` (a graph-level subclass) was withdrawn in Phase 05a (round-1 P3 amendment) because graph-level binding can't carry the node-level identity that the cat=c+a+t use case requires.
  >
  > **Decision.** Introduce two new L1 primitives:
  >
  > - **`IntergraphEdge`** (Phase 05b, this ADR's first draft) — binary, 1-to-1, node↔node across two graphs in one metagraph. Owned by the metagraph (not by either graph); registered in the metagraph's `IdentityRegistry` (ADR-0020); persisted in metagraph state file. Required fields: `source_graph_id`, `source_node_id`, `target_graph_id`, `target_node_id`, `type_name` (cypher rel-type per ADR-0021). Optional: `label`, `properties` (namespaced bag), `compositional: bool` (default False).
  >
  > - **`IntergraphHyperEdge`** (Phase 05c, this ADR amended) — n-ary anchors + members, NOT 1-to-1 (cardinality enforcement at API boundary). Asymmetric: anchors are the "identity-bearing" side; members the "constituent" side. Same compositional flag. Same metagraph ownership.
  >
  > Both primitives carry an immutable-post-create `compositional: bool` flag. When `compositional=True`:
  > (a) the edge cannot be removed (`remove_*_edge` raises `CompositionalImmutableError`);
  > (b) properties cannot be mutated (`update_*_edge_properties` raises);
  > (c) deprecation (Phase 10) raises;
  > (d) `Metagraph.remove_graph` cascade refuses if any incident edge is compositional (atomic precheck);
  > (e) the flag itself cannot be flipped at runtime (`__setattr__` enforcement).
  >
  > Schema validation lives in a metagraph-attached `MetagraphSchema` (also introduced in 05b). The schema carries `IntergraphEdgeType` (and in 05c, `IntergraphHyperEdgeType`) vocabularies with role-based graph constraints (`allowed_source_graphs` / `allowed_target_graphs` against `Graph.role`) plus type-based node constraints (`allowed_source_types` / `allowed_target_types` against `Node.type_name`) plus property-type maps. Validation is point-in-time at attach + each `add_intergraph_edge`.
  >
  > Persistence (Phase 07): Cypher Pattern B (anchor-node pattern) — the IntergraphEdge is materialized as `(:IntergraphEdge {edge_id, type_name, properties..., _compositional})` connected to source/target node anchors via typed relationships (`:SOURCE` / `:TARGET` for binary; `:ANCHOR` / `:MEMBER` for n-ary). Owned by `(:Metagraph)` via `:OWNS`. OCC: two-lock canonical ordering for binary; n-lock for n-ary (sort by `graph_id` string, acquire in order, release in reverse). Implementation deferred to Phase 07; 05b/05c lock the contract.
  >
  > **Consequences.**
  >
  > - L1 ships 6 edge primitives total: `Edge`, `HyperEdge` (within Graph); `MetaEdge`, `MetaHyperEdge` (between Graphs in Metagraph); `IntergraphEdge`, `IntergraphHyperEdge` (between Nodes across Graphs in Metagraph). XRef (Phase 09) adds the 7th (between Nodes across Metagraphs).
  > - Compositional invariant is strong: tester recovery for a wedged metagraph requires full reset.
  > - `MetagraphSchema` is the new schema home; reuse across metagraphs by name reference (mirror Phase 04 graph schema). Schema mutation while attached carries Phase 04 footgun (re-attach to validate drift).
  > - `Metagraph.mint_id` lands as the IntergraphEdge factory's id-minting path; ADR-0131 pluggable IdStrategy reaches its first non-uuid consumer.
  > - Persistence layer (Phase 07) gains 2 new node labels (`:IntergraphEdge`, `:IntergraphHyperEdge`) and the canonical-ordered-lock contract.
  >
  > **Supersedes:** ADR-0117 (`CompositionalMetaEdge`, Withdrawn in Phase 05a per round-1 P3).
  >
  > **Related:** ADR-0014 (Layer boundary, amended in 05b to extend Core's primitive list), ADR-0020 (unified IdentityRegistry), ADR-0021 (cypher identifier safety), ADR-0027 / ADR-0028 (Snapshot scope), ADR-0029 (superseded by ADR-0130 in 05a), ADR-0130 (property bag on Metagraph + Graph), ADR-0131 (pluggable IdStrategy).
  >
  > **Canonical design:** `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`.

  **§C — ADR-0014 amendment text (full; file edit Phase 38):**

  > **2026-05-05 amendment (Phase 05b):** L1 Core's primitive list extends with `IntergraphEdge` (binary, 1-to-1, node↔node across graphs in one metagraph) per ADR-0148 first draft. The amendment establishes that L1 owns the binary intergraph primitive at the model layer (`mindsos_core/models/intergraph_edge.py`); schema validation lives in a new `MetagraphSchema` container (`mindsos_core/schema/metagraph_schema.py`) that attaches to a metagraph by name reference and is reusable across N metagraphs (mirror Phase 04 graph schema). The 05c amendment to this ADR-0014 entry will add `IntergraphHyperEdge` (n-ary) once that primitive ships.

  **§D — 05c dry-run appendix (pre-resolves 05c decisions that could retroactively wish for 05b changes):**

    - **05c will add `intergraph_hyperedges` array to metagraph state file** → bump v=2 → v=3. **05b's v=2 shape is forward-compat:** missing field defaults to empty array. No 05b change needed.
    - **05c's `IntergraphHyperEdgeType` schema vocabulary** + **05c's `MetaEdgeType` + `MetaHyperEdgeType` vocabularies** all add to MetagraphSchema. State file v=1 → v=2 in 05c. **05b's MetagraphSchema v=1 shape is forward-compat:** missing fields default to empty arrays. No 05b change needed.
    - **05c's `compositional` cascade** through `Metagraph.remove_graph` extends to `IntergraphHyperEdge`. **05b's precheck pass** (Pushback 17-A) iterates `mg.intergraph_edges` only; 05c extends to also iterate `mg.intergraph_hyperedges`. No 05b change needed (additive in 05c).
    - **05c's n-lock canonical ordering** for n-ary intergraph hyperedges generalizes 05b's two-lock-for-binary contract. Both lock the contract; Phase 07 implements both. No 05b change needed.
    - **05c's `IntergraphHyperEdge.compositional`** flag is the same `_compositional` reserved key as 05b. **05b's reserved-key addition** (P6 carry-forward) covers both. No 05b change needed.
    - **05c MAY surface a tester pain about `mindsos metagraph` subapp size** (Pushback 33-A); if so, the future-work entry (Pushback 33-B) escalates as candidate for promotion at that point.

---

### Phase 05c — L1 IntergraphHyperEdge (n-ary) + IntergraphHyperEdgeType

  **Status:** Pending (refines after 05b confirms; CASC-1).
  **Branch:** phase-05c
  **Tag on confirm:** phase-05c-confirmed
  **Depends on:** 05b.
  **Layer:** L1.
  **Net-new?:** **Yes.** New `IntergraphHyperEdge` primitive (asymmetric anchors + members; n-ary; NOT 1-to-1) + factory + persistence + CLI; `IntergraphHyperEdgeType` schema vocabulary added to `MetagraphSchema`; ADR-0148 amended.

  **Features (preview — full row refinement happens in 05c chat):**
    - `Metagraph.add_intergraph_hyperedge(...)` factory with `compositional: bool = False` flag and cardinality enforcement (anchors ≥ 1, members ≥ 1, NOT 1-1).
    - `IntergraphHyperEdge` dataclass with 9 fields per `INTERGRAPH_EDGES_DESIGN.md` §2.2.
    - `IntergraphHyperEdgeType` schema vocabulary with `allowed_anchor_types` / `allowed_member_types` / `allowed_anchor_graphs` / `allowed_member_graphs` / `ordered: bool` fields.
    - CLI: `mindsos metagraph add-intergraph-hyperedge` with `--anchor <G>/<N>` repeatable + `--member <G>/<N>` repeatable + `--compositional` flag.
    - `Metagraph.remove_graph` cascade extended to incident IntergraphHyperEdges (refuses if any compositional).
    - State files: metagraph state v=2 → v=3 (adds `intergraph_hyperedges`); MetagraphSchema state-file v=1 → v=2 (adds `intergraph_hyperedge_types` map).

  **Reads:** `INTERGRAPH_EDGES_DESIGN.md` §1 / §2.2 / §3 / §4.2 / §4.3 / §5 / §6 (CLI 05c section) / §7 (cat=c+a+t example is the motivating use case) / §9 (ADR-0148 amendment) / §10 / §11.

  **Risks:** anchor-member overlap detection must be efficient under large compositions; n-lock canonical ordering deadlock-avoidance correctness needs explicit testing under concurrent writes (Phase 07-relevant; 05c can ship in-memory only).

  **Docs:** `docs/concepts/intergraph-edges.md` (amended for n-ary), `docs/usage/core/metagraph-schema.md` (amended for `IntergraphHyperEdgeType`), `docs/api/core/intergraph-hyperedge.md` (NEW), ADR-0148 (amended; file edit Phase 38).

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
| `docs/getting-started/first-metagraph.md` | 05a |
| `docs/getting-started/first-mental-model.md` | **out of scope** (L5) |
| `docs/getting-started/whats-new-v4.md` | 38 |
| `docs/getting-started/facts-and-figures.md` | 38 |

### Concepts

| Page | Confirms in phase |
|---|---|
| `docs/concepts/layers.md` | 38 |
| `docs/concepts/graphs-and-metagraphs.md` | 03 + 05a (+ 05b / 05c amend for intergraph edges) |
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
| `docs/usage/core/metagraphs.md` | 05a |
| `docs/concepts/intergraph-edges.md` | 05b (+ 05c amend for n-ary) |
| `docs/usage/core/metagraph-schema.md` | 05b (+ 05c amend for `IntergraphHyperEdgeType`) |
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
| 0014–0024 (L1 originals) | **0014 in 03** (amended in 05b for IntergraphEdge / IntergraphHyperEdge primitives — text in 05b row appendix; file edit Phase 38); 0015 / 0019 / 0025 / 0026 in 06; 0016 in 09 (XRef supersession noted); 0017 in 04; 0018 in 07; **0020 confirmed in 05a** (amendment text drafted; file edit Phase 38); 0021 in 03 + 11; 0022 / 0023 in 07; 0024 in 10 |
| 0027–0037 | 0027 / 0028 in 10; **0029 Superseded by 0130 in 05a** (annotation text in 05a row appendix; file edit Phase 38); 0030 in 07; 0031 / 0032 in 08; 0033 in 10; 0034 in 09; 0035 in 02; 0036 in 07; 0037 in 06 |
| 0038–0057 (L2) | 0038–0042 in 25; 0043 in 14; 0044 in 14; 0045 / 0047 in 12; 0046 in 18; 0048 in 14; 0049–0056 in 16; 0057 in 13 |
| 0060–0100 (L3) | 0060 / 0084 in 27 + 28; 0061 / 0064 / 0065 / 0085 in 28; 0062 / 0063 / 0066 in 27; 0067 in 12; 0068–0070 / 0086 / 0092 in 29; 0071 / 0072 / 0074 in 30; 0073 / 0088 / 0100 in 31; 0075 / 0076 in 28; 0077–0081 in 25 (cross with 28); 0082 / 0083 / 0094 / 0095 / 0096 / 0097 — L4 implications **out of scope**; only the L3 surface they imply ships; 0091 / 0098 / 0099 in 31; 0093 in 27 |
| **0117** | **Reserved through 05a; Withdrawn in 05b** (originally graph-level CompositionalMetaEdge; concept moves to `compositional: bool` flag on `IntergraphEdge` / `IntergraphHyperEdge` per ADR-0148; canonical at `INTERGRAPH_EDGES_DESIGN.md`) |
| 0118 | 24 |
| 0121–0137 (L1 redesign) | 0121 in 07; 0122 in 07; 0123 in 07 + 11; 0124 in 08; 0125 in 08; 0126 in 07; 0127 in 07; 0128 in 09; 0129 in 10; **0130 Accepted in 05a** (Metagraph property bag shipped per N1-A1; Graph property bag deferred to Phase 10); 0131 in 02; 0132 in 06; 0133 in 10; 0134 in 11; 0135 in 10; 0136 in 18; 0137 in 23 + 24 |
| 0138–0144 (L2 closure) | 0138 in 14 (verify removed); 0139 in **36 — NEW CODE**; 0140 in 36 (constraints on writes); 0141 in 14; 0142 in 09; 0143 in 34; 0144 in **37 — NEW CODE** |
| 0145–0147 (L3 write side) | 0145 in **33 — NEW CODE**; 0146 in **34 — NEW CODE**; 0147 in **35 — NEW CODE** |
| **0148 (NEW; intergraph edge family)** | **drafted + Accepted in 05b** (`IntergraphEdge` binary + compositional flag); **amended in 05c** (`IntergraphHyperEdge` n-ary). Canonical spec at `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`. ADR file edit Phase 38 per locked precedent. |

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

2. **ADRs 0113–0116 / 0119 / 0120 reserved but undrafted.** **Affects Phase 24.** Recommend the phase chat draft them as part of the phase. Confirm or specify alternative. *(2026-05-05 update: ADR-0117 removed from this list — to be Withdrawn in Phase 05b per the intergraph edge design refinement; canonical at `INTERGRAPH_EDGES_DESIGN.md`.)*

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

13. ~~**Intergraph edge primitive (raised by user 2026-05-04, in Phase 03 chat).**~~ **CLOSED 2026-05-04 (Phase 05 design chat) + refined 2026-05-05 (Phase 05a chat).** GREENLIT as **two primitives**: `IntergraphEdge` (binary 1-1, ships in 05b) + `IntergraphHyperEdge` (n-ary, NOT 1-1, ships in 05c). Both carry `compositional: bool` flag (immutable post-create) for identity-bearing composition (cat=c+a+t use case). All §4 concerns (OWNS / snapshots / schema / OCC / migration / existing constructs) resolved. **Canonical design: `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`.** Future chats read that file directly; do not consult older Q13 framing.

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
