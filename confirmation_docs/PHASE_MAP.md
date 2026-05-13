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
| 05b | L1 IntergraphEdge (binary 1-1) + MetagraphSchema + IntergraphEdgeType + compositional flag (NEW CODE; ADR-0148 first draft; **ADR-0117 already Withdrawn in 05a — 05b skips that flip**; `_compositional` reserved key + `Metagraph.mint_id` deferred from 05a per P6/P7; **MetaEdgeType + MetaHyperEdgeType deferred to 05c per Pushback 1-C, then further deferred to 05d per 05c P1-B**) | L1 | 05a |
| 05c | L1 IntergraphHyperEdge (n-ary, NOT 1-1) + IntergraphHyperEdgeType + replace-only update verb (NEW CODE; ADR-0148 amended for n-ary; **scope narrowed per 05c P1-B — meta-vocabs moved to 05d**) | L1 | 05b |
| 05d | L1 MetaEdgeType + MetaHyperEdgeType vocab (NEW CODE; deferred from 05b/c per Pushback 1-C and 05c P1-B; ADR-0017 amended; **MetaEdge.type_name field audit per 05c P3 may trigger 05a-v2 if absent**) | L1 | 05c |
| 06 | L1 Instancing — `mindsos_instances` package | L1 | 03, 05d |
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

**Total: 43 phases.** Two integration phases (26, 32). Nine phases carry **NEW CODE** beyond repackaging (05b, 05c, 05d, 24, 33, 34, 35, 36, 37). Phase 04 is Superseded by 04-v2 (slot collapsed); Phase 05 is split into 05a / 05b / 05c / 05d (four sub-phase slots, CASC-1 strict-sequential per the supersession-policy letter-sub-phases rule in §1).

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

### Phase 05c — L1 IntergraphHyperEdge (n-ary) + IntergraphHyperEdgeType + replace-only update verb

  **Status:** Pending (refines after 05b confirms; CASC-1; row LOCKED 2026-05-06 across 4 reanalysis rounds).
  **Branch:** phase-05c
  **Tag on confirm:** phase-05c-confirmed
  **Depends on:** 05b.
  **Layer(s):** L1.
  **Net-new?:** **Yes (substantial).** New `IntergraphHyperEdge` primitive class + factory + persistence + CLI; new `IntergraphHyperEdgeType` schema vocabulary on `MetagraphSchema`; new `update-intergraph-hyperedge` CLI verb (replace-only, anchors/members/properties); 5-way mutex on `set-prop` (extends 05b's 4-way per P10-C carry-forward); metagraph state-file v=2 → v=3 cumulative one-way migration (adds `intergraph_hyperedges`); metagraph-schema state-file v=1 → v=2 cumulative one-way migration (adds `intergraph_hyperedge_types`); ADR-0148 amendment for n-ary primitive (full text in row appendix §B); ADR-0014 second amendment (full text in row appendix §C).

  **Scope narrowed (05c P1-B, round 1 lock):** 05c ships `IntergraphHyperEdge` primitive + `IntergraphHyperEdgeType` vocabulary + `update_intergraph_hyperedge` factory + 4 CLI verbs ONLY. **`MetaEdgeType` + `MetaHyperEdgeType` deferred to 05d** (pre-existing 05b Pushback 1-C deferral re-routed past 05c). Reasoning: cumulative scope of fusing 4 deliverables into one row produces an outsized blast radius vs. the cleaner 05c-narrow + 05d-meta-vocabs cascade.

  **Carry-forward from 05b deferrals (none this round):** 05b shipped completely against its locked row (no carry-forwards open for 05c).

  **Locked decisions (4 reanalysis rounds — 2026-05-06; 20 numbered pushbacks; 2 future-work entries filed at `_source_backup/root/mindsos_future_plans.md`):**

    - **P1-B** — 05c scope narrows to IntergraphHyperEdge primitive + IntergraphHyperEdgeType vocab + replace-only update verb. MetaEdgeType + MetaHyperEdgeType deferred to 05d (own row, own state-file v=2→v=3 bump on metagraph-schema).
    - **P2-refined** — `IntergraphHyperEdge.compositional` is a top-level dataclass field (mirror 05b's IntergraphEdge.compositional). `__setattr__` override blocks `compositional` always (immutable post-create); blocks `anchors` / `members` / `properties` only when `compositional=True`. Non-compositional hyperedges support anchor/member/properties mutation via factory methods (`update_intergraph_hyperedge` for structural; `set-prop` for properties). Factory uses `object.__setattr__` to bypass the runtime block on legitimate mutations. Tuple-conversion of `anchors` and `members` at `__post_init__` regardless of compositional flag (eliminates list-mutation hole even for non-compositional).
    - **P3** — Pre-implementation audit of `MetaEdge.type_name` field existence on 05a. **DEFERRED to 05d.** 05c does NOT touch metaedges/metahyperedges or their type-name fields. 05d row carries the audit task; if absent, 05d triggers a separate consideration (additive expansion vs 05a-v2 supersession decision) at that phase chat.
    - **P4-A** — CLI uses **paired flags** for anchor/member specification: `--anchor-graph G --anchor-node N` (repeatable; paired by parsing index — first `--anchor-graph` pairs with first `--anchor-node`, etc.). Symmetric for `--member-graph` / `--member-node`. Mismatched counts (e.g., 3 `--anchor-graph` flags + 2 `--anchor-node` flags) refuse with structured error before any mutation. No slash-separator (`G/N`) or colon-separator (`G:N`) form — both ambiguous when graph names contain those characters.
    - **P5-refined / P9-A** — `IntergraphHyperEdgeType.ordered: bool` is type-driven set-vs-list semantic. `ordered=True` → list semantics (preserve insertion order; allow duplicates within a side). `ordered=False` → set semantics (canonicalize at construction: sort lexicographically by `(graph_id, node_id)` then dedup; refuse on duplicate input only when explicitly conflicting with cardinality post-dedup). **No-schema default**: when no MetagraphSchema attached OR no IntergraphHyperEdgeType registered for the type_name, treat as `ordered=True` (permissive list semantics; no canonicalization). Re-attach with conflicting `ordered` setting refuses per Pushback 7-A eager-validation contract (carry-forward from 05b).
    - **P6-A** — Re-attach validation drift in 05c: 05b-attached MetagraphSchemas had only `IntergraphEdgeType` vocab. 05c eager-attach extends to walk `intergraph_hyperedges` IN ADDITION to `intergraph_edges` (which 05b walked). Metaedges + metahyperedges remain skipped (Push9-A from 05b carry-forward; expires in 05d when MetaEdgeType vocab arrives). Tester upgrading from 05b to 05c with attached metagraphs: re-attach surfaces drift if any existing intergraph_hyperedges (none possible since 05b didn't ship the primitive — this entry is forward-looking for 05c-internal re-attach cycles).
    - **P7-A** — Test budget: unlimited per `feedback_test_budget_unlimited.md`. Row records intent only; final count whatever coverage requires; tester records actual at `PHASE_05c_CONFIRMED.md`.
    - **P8-A** — `compositional=True` + `ordered=False` combination refused at `add_intergraph_hyperedge` validation step 8.5: after schema type-existence lookup, before cardinality check. Raises `SchemaError("compositional hyperedges require ordered=True types")`. Compositional implies identity-bearing composition (cat=c+a+t — order matters); set semantics (`ordered=False`) is incompatible with that invariant. Refusal at construction-time, NOT at type-construction (the same type can serve both compositional and non-compositional callers).
    - **P10-C** — Single replace-only `update_intergraph_hyperedge` factory + CLI verb. Replaces `anchors` AND `members` AND `properties` atomically (all three required-or-optional with replace semantics; no patch). Refuses if `compositional=True` (`CompositionalImmutableError`). Re-runs full validation order on the replacement values. Tester ergonomics: to add one anchor, list all + the new one. CLI signature: `update-intergraph-hyperedge --name MG --intergraph-hyperedge-id ID [--anchor-graph G --anchor-node N]... [--member-graph G --member-node N]... [--prop k=v]... [--json]`.
    - **P11→P13-B** — Symmetric `update_intergraph_edge_endpoints` factory + CLI verb on the binary `IntergraphEdge` primitive REJECTED for 05c. Cost of triggering 05b-v2 supersession (cascade reorder, tester reverts to 05a, tarball eviction, two implementation cycles in this chat) judged disproportionate to the symmetry benefit when the existing remove + add `--intergraph-edge-id <orig>` workaround already preserves edge_id stability. Documented in 05b CHANGELOG amendment (this chat ships the doc edit) + filed as new future-work entry "Discoverable endpoint-update verb for IntergraphEdge" alongside Pushback 31-B.
    - **P12-A** — Schema-mutation-while-attached footgun for `IntergraphHyperEdgeType.ordered` flag: carry-forward of 05b Pushback 23-A pattern. Stderr warning at `metagraph-schema add-intergraph-hyperedge-type` listing every metagraph currently attached. `IntergraphHyperEdgeType` itself is a frozen dataclass, so direct mutation is blocked; only `add-*-type` re-add (with new ordered value) drifts the type. Risks section documents.
    - **P14-A** — 16-step validation order at `Metagraph.add_intergraph_hyperedge` (appendix §A below; canonicalize-BEFORE-cardinality enforced).
    - **P15-A** — 05d row stub authored alongside 05c row in this chat (full row text, not just §3 index entry). Visible dependency chain for next chat.
    - **P16-A** — Strict version contract on metagraph-schema state-file: 05c binary supports v=1 ∪ v=2; rejects v=3 with `this CLI supports v2` structured message. Recovery via hand-edit JSON downgrade. Mirrors 05b §D metagraph state-file precedent. Also applies to metagraph state-file: 05c binary supports v=2 ∪ v=3; rejects v=4 (when Phase 10 lands soft-delete) with structured message.
    - **P17-A** — 05c is the LAST metagraph state-file bump until Phase 10 (snapshot + soft-delete adds `deprecated_at` / `disputed_at`). 05d adds nothing to metagraph state-file; meta-vocabs live in metagraph-schema state-file only. Predictable migration chain through Phase 09.
    - **P18-A** — `IntergraphHyperEdgeType.ordered` field default = `True` (overrides design doc §3.3's stated `False` default). Consistency with no-schema default (P9-A); permissive; matches the cat=c+a+t motivating example; tester opts INTO set semantics via explicit `--unordered` (or `--ordered=false`) flag.
    - **P19-A** — `update_intergraph_hyperedge` that would collapse to 1-1 cardinality (e.g., `[a,b]+[c,d]` → `[a]+[b]`) **REFUSES** per cardinality check (NOT 1-1 rule). No in-place hyperedge→edge "downgrade" — tester recovery is `remove-intergraph-hyperedge` + `add-intergraph-edge` (loses edge_id stability across the type boundary). Filed as future-work entry "In-place hyperedge→edge downgrade with edge_id stability".
    - **P20-A** — `update_intergraph_hyperedge` under detached schema: validates against current state only (structural checks: cardinality, overlap, regex; NO schema-type / role / property-type validation since no schema attached). Edge stays in store; subsequent re-attach runs eager validation per 05b Pushback 7-A. No `_schema_at_construction` field on edges; no historical schema lineage. Mirrors 05b's `update_intergraph_edge_properties` precedent.
    - **Smaller items folded** (locked without separate pushback numbers): `mint_id("intergraph_hyperedge")` per 05b Pushback 14-A precedent; `__setattr__` immutability override per 05b Pushback 22-A pattern; `remove_graph` precheck pass extends to walk BOTH `mg.intergraph_edges` AND `mg.intergraph_hyperedges` per 05b Pushback 17-A pattern; `RESERVED_PROPERTY_KEYS` extends with `intergraph_hyperedges` (top-level metagraph state v=3 field) per 05b Pushback 18-A pattern; single-step `_v2_to_v3` migration on metagraph state-file (sets `intergraph_hyperedges: []` default); single-step `_v1_to_v2` migration on metagraph-schema state-file (sets `intergraph_hyperedge_types: []` default); `type_name` set-at-create only on `IntergraphHyperEdge` (mirror 05b Pushback 31-A); no `update-intergraph-hyperedge-label` standalone verb (label included in replace-only update); no `remove-intergraph-hyperedge-type` verb (mirror 05b Pushback 34-A; future-work 34-B already filed covers this case symmetrically); doctor `--self-test` regex unchanged (05a's `phase\d{2}([a-z]|-v\d+)?-(prod|test)` already covers `phase05c-prod` / `phase05c-test`); `mindsos metagraph` subapp accepts ~26 subcommands flat surface (33-B future-work continues to absorb the deferral); test fixture reuse from `tests/_shared/`; CLI repeatable-flag pairing semantics by index (mismatched counts refuse).

  **Features in scope (capability-level — locked):**

    - `IntergraphHyperEdge` dataclass — `@dataclass(kw_only=True)`; fields per `INTERGRAPH_EDGES_DESIGN.md` §2.2 (9-field spec, soft-delete substrate dormant per 05b precedent + Phase 10 deferral):
      - `anchors: Tuple[Tuple[str, str], ...]` (required; n ≥ 1; converted to tuple-of-tuples at `__post_init__`).
      - `members: Tuple[Tuple[str, str], ...]` (required; m ≥ 1; converted to tuple-of-tuples at `__post_init__`).
      - `type_name: str` (required; ADR-0021 cypher rel-type regex enforced at `__post_init__`; set-at-create only).
      - `compositional: bool = False` (immutable post-create per `__setattr__` override).
      - `edge_id: str = field(default_factory=...)` — auto-minted via `mg.mint_id("intergraph_hyperedge")` when factory called; field carries default for direct-construction paths (rehydration/tests).
      - `label: Optional[str] = None`.
      - `properties: Dict[str, Any] = field(default_factory=dict)` — namespaced; reserved-key-aware via `validate_user_properties(scope="intergraph_hyperedge")`.
      - Soft-delete fields `deprecated_at` / `disputed_at` — NOT shipped in 05c (lands uniformly across all 5 edge variants in Phase 10 per SOFT_DELETE_AUDIT_NOTE precedent).
      - `__post_init__` runs: tuple-conversion of anchors/members; ADR-0021 cypher rel-type regex on `type_name`; cardinality check (n ≥ 1, m ≥ 1, NOT 1-1); anchor-member overlap check (no `(graph_id, node_id)` pair in both sides); sets `_initialized = True` for `__setattr__` gate.
      - `__setattr__` override:
        - `compositional` → always raise `CompositionalImmutableError` post-init.
        - `anchors` / `members` / `properties` → raise `CompositionalImmutableError` if `self.compositional is True` AND `_initialized` is True. Otherwise allow (factory uses `object.__setattr__` for bypass on legitimate mutations).
        - All other fields (`edge_id`, `type_name`, `label`, soft-delete) → raise on post-init mutation (set-at-create).
      - `__hash__` and `__eq__` by `edge_id`.
      - `__repr__` slimmed (anchors/members shown by count, not full dump).
    - `IntergraphHyperEdgeType` frozen dataclass — fields:
      - `name: str` (required; ADR-0021 regex; `__post_init__` validates).
      - `allowed_anchor_types: FrozenSet[str] = frozenset()` (Node type_name; empty = any).
      - `allowed_member_types: FrozenSet[str] = frozenset()` (Node type_name; empty = any).
      - `allowed_anchor_graphs: FrozenSet[str] = frozenset()` (Graph.role; empty = any; `role=None` unmatchable when non-empty per 05b Pushback 4-A precedent).
      - `allowed_member_graphs: FrozenSet[str] = frozenset()` (Graph.role; empty = any).
      - `ordered: bool = True` (P18-A; permissive default; opt-in to set semantics via `--unordered`).
      - `property_types: Dict[str, PropertyType] = field(default_factory=dict)` (Phase 04 8-variant vocab).
      - `description: Optional[str] = None`.
    - `MetagraphSchema` extension — adds:
      - `_intergraph_hyperedge_types: Dict[str, IntergraphHyperEdgeType]` storage.
      - `add_intergraph_hyperedge_type(iht: IntergraphHyperEdgeType)` — refuses on duplicate name (`UnknownTypeError`); stderr warning per 05b Pushback 23-A pattern listing attached metagraphs.
      - `require_intergraph_hyperedge_type(name: str) -> IntergraphHyperEdgeType`.
      - `intergraph_hyperedge_types` property → `Mapping[str, IntergraphHyperEdgeType]` (defensive copy).
      - `validate_intergraph_hyperedge(type_name, anchor_type_names, member_type_names, anchor_roles, member_roles)` → enforces allowed_*_types + allowed_*_graphs (empty = any).
      - `validate_intergraph_hyperedge_properties(type_name, properties)` → strict-only property-type check (mirror 05b Pushback 5-A).
    - `Metagraph.add_intergraph_hyperedge(anchors, members, type_name, *, label=None, properties=None, compositional=False, intergraph_hyperedge_id=None) -> IntergraphHyperEdge` — 16-step validation order (appendix §A below). Returns the constructed hyperedge after registration in `mg.identity`. `anchors` and `members` parameters accept `List[Tuple[str, str]]` or `Tuple[Tuple[str, str], ...]`; canonicalized to tuple-of-tuples.
    - `Metagraph.remove_intergraph_hyperedge(intergraph_hyperedge_id) -> None` — refuses with `CompositionalImmutableError` if `compositional=True`; otherwise unregisters from `mg.identity` and removes from `mg.intergraph_hyperedges`.
    - `Metagraph.update_intergraph_hyperedge(intergraph_hyperedge_id, *, anchors=None, members=None, properties=None, replace_properties=False) -> IntergraphHyperEdge` — replace-only structural update (P10-C). Refuses with `CompositionalImmutableError` if `compositional=True`. Re-runs full 16-step validation on resolved values (any field passed as `None` retains current value; non-`None` replaces). On validation failure, atomic rollback (no in-memory mutation). `replace_properties=False` (default): merge current + new. `replace_properties=True`: replace entire properties dict. Mutex semantic distinct from `set-prop` mutex.
    - `Metagraph.iter_intergraph_hyperedges() -> Iterator[IntergraphHyperEdge]` — no `include_deprecated` kwarg in 05c (Phase 10 adds).
    - `Metagraph.attach_schema` extension (carry-forward 05b Pushback 7-A + 9-A + 17-A + 19-B + 24-hybrid + 29-A + 32-D) — eager validation pass extends to walk `intergraph_edges` (already from 05b) AND `intergraph_hyperedges` (NEW in 05c). Metaedges + metahyperedges still skipped (Push9-A carry-forward; expires in 05d).
    - `Metagraph.remove_graph` cascade — extends 05b's slim cascade with the precheck pass extension: walks BOTH `mg.intergraph_edges` AND `mg.intergraph_hyperedges`; raise `CompositionalImmutableError` on first compositional incident (intergraph_edge OR intergraph_hyperedge), structured error includes edge_kind + edge_id; state unchanged on raise.
    - `Metagraph.intergraph_hyperedges: Dict[str, IntergraphHyperEdge]` — in-memory storage keyed by `intergraph_hyperedge_id`.
    - **CLI** — `mindsos metagraph` subapp adds 4 new subcommands + extends `set-prop` to 5-way mutex:
      - `add-intergraph-hyperedge --name MG [--anchor-graph G --anchor-node N]... [--member-graph G --member-node N]... --type T [--label L] [--prop k=v]... [--compositional] [--intergraph-hyperedge-id ID] [--json]` (paired-flags parsing per P4-A).
      - `remove-intergraph-hyperedge --name MG --intergraph-hyperedge-id ID [--json]`.
      - `update-intergraph-hyperedge --name MG --intergraph-hyperedge-id ID [--anchor-graph G --anchor-node N]... [--member-graph G --member-node N]... [--prop k=v]... [--replace-properties] [--json]` (replace-only per P10-C; refuses if compositional).
      - `list-intergraph-hyperedges --name MG [--json]`.
      - `set-prop` 5-way mutex extension: `(--on-metagraph | --metaedge-id | --metahyperedge-id | --intergraph-edge-id | --intergraph-hyperedge-id) --prop k=v ... [--replace]`. When `compositional=True` on a targeted intergraph_hyperedge, refuses with `CompositionalImmutableError`.
    - **CLI** — `mindsos metagraph-schema` subapp adds 1 new subcommand:
      - `add-intergraph-hyperedge-type --schema MS --type-name T [--allowed-anchor-type NT]... [--allowed-member-type NT]... [--allowed-anchor-graph ROLE]... [--allowed-member-graph ROLE]... [--ordered/--unordered] [--prop-type k=PT]... [--description STR] [--json]` — `--ordered/--unordered` defaults to `--ordered` (P18-A); emits stderr warning listing attached metagraphs per 05b Pushback 23-A precedent.
    - **State files**:
      - `metagraph-<n>.json` v=2 → v=3 cumulative one-way migration: adds `intergraph_hyperedges: []` (default). Loaders accept v=2 ∪ v=3; writers emit v=3.
      - `metagraph-schema-<n>.json` v=1 → v=2 cumulative one-way migration: adds `intergraph_hyperedge_types: []` (default). Loaders accept v=1 ∪ v=2; writers emit v=2.
    - **Doctor self-test extension:** None (05a's regex covers `phase05c-prod` / `phase05c-test`).

  **Modules touched (locked):**

    - `mindsos_core/models/intergraph_hyperedge.py` — **NEW file**. `IntergraphHyperEdge` dataclass + `__setattr__` immutability override + helpers + tuple-conversion at `__post_init__`.
    - `mindsos_core/models/metagraph.py` — extends with `add_intergraph_hyperedge` / `remove_intergraph_hyperedge` / `update_intergraph_hyperedge` / `iter_intergraph_hyperedges` factory methods; extends `remove_graph` cascade precheck to walk `mg.intergraph_hyperedges`; extends `attach_schema` eager pass to walk hyperedges; adds `intergraph_hyperedges` instance state.
    - `mindsos_core/schema/metagraph_schema.py` — extends with `add_intergraph_hyperedge_type` / `require_intergraph_hyperedge_type` / `validate_intergraph_hyperedge` / `validate_intergraph_hyperedge_properties` methods + `_intergraph_hyperedge_types` storage.
    - `mindsos_core/schema/types.py` — extends with `IntergraphHyperEdgeType` frozen dataclass.
    - `mindsos_core/schema/validation.py` — extends `RESERVED_PROPERTY_KEYS` with `intergraph_hyperedges` (top-level metagraph state v=3 field) + `intergraph_hyperedge_types` (top-level metagraph-schema state v=2 field).
    - `mindsos_core/__init__.py` — re-exports `IntergraphHyperEdge`.
    - `mindsos_core/schema/__init__.py` — re-exports `IntergraphHyperEdgeType`.
    - `mindsos_cli/commands/metagraph.py` — extends with 4 new subcommands (add/remove/update/list intergraph-hyperedge) + 5-way set-prop mutex; extends `inspect` / `list` JSON shapes (additive — `counts.intergraph_hyperedges` + `intergraph_hyperedges_count` per entry); extends `remove-graph --json` with `cascaded_intergraph_hyperedges` field.
    - `mindsos_cli/commands/metagraph_schema.py` — extends with `add-intergraph-hyperedge-type` subcommand + `inspect --json` shape additive (`intergraph_hyperedge_types: [...]`).
    - `mindsos_cli/state.py` — bumps `METAGRAPH_STATE_VERSION = 3` + `METAGRAPH_SCHEMA_STATE_VERSION = 2`.
    - `mindsos_cli/migrations/metagraph.py` — adds `_v2_to_v3(state)` step (sets `intergraph_hyperedges: []` default); `CURRENT_VERSION = 3`.
    - `mindsos_cli/migrations/metagraph_schema.py` — adds `_v1_to_v2(state)` step (sets `intergraph_hyperedge_types: []` default); `CURRENT_VERSION = 2`.
    - `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05c"`.
    - `mindsos_cli/manifest.toml` — `[mindsos] phase = "05c"`; `version = "0.0.0+phase05c"`.
    - `pyproject.toml` — version + description bumped.
    - `docker-compose.yml` — image tags `mindsos:phase05c-prod` / `mindsos:phase05c-test`.
    - `Dockerfile` — comment lines bumped (Phase 05b → Phase 05c references); COPY block reaches new `mindsos_core/models/intergraph_hyperedge.py` via existing wildcards.
    - `tests/_shared/sentinel_paths.py` — **+1 entry**: `mindsos_core/models/intergraph_hyperedge.py`.
    - `_source_backup/root/mindsos_future_plans.md` — **+2 entries**: "Discoverable endpoint-update verb for IntergraphEdge" (P11→P13-B retreat); "In-place hyperedge→edge downgrade with edge_id stability" (P19-A).

  **Persistence layout (locked):**

    - **Metagraph state-file v=3 JSON shape** (extends v=2 with `intergraph_hyperedges`):
      ```json
      {"_state_version": 3,
       "metagraph_id": "<uuid4>", "name": "<n>",
       "properties": {"k": "<value>"},
       "schema_name": "<schema-name-or-null>",
       "contained_graphs": ["<graph-name>", ...],
       "metaedges": [...],
       "metahyperedges": [...],
       "intergraph_edges": [...],
       "intergraph_hyperedges": [
         {"intergraph_hyperedge_id": "...",
          "anchors": [["<gname>", "<node-id>"], ...],
          "members": [["<gname>", "<node-id>"], ...],
          "type_name": "<UPPER>",
          "compositional": <bool>,
          "label": "<text-or-null>", "properties": {...}}
       ]}
      ```
      Top-level `intergraph_hyperedges` array byte-stable sorted by `intergraph_hyperedge_id`. Within each entry: `anchors` and `members` arrays preserve construction-order (post-canonicalization at `add_*` time — for `ordered=True` types, that's insertion order; for `ordered=False` types, that's sorted+deduped). Atomic write via `<path>.tmp + os.replace`.
    - **MetagraphSchema state-file v=2 JSON shape** (extends v=1 with `intergraph_hyperedge_types`):
      ```json
      {"_state_version": 2,
       "name": "<n>", "strict": <bool>,
       "intergraph_edge_types": [...],
       "intergraph_hyperedge_types": [
         {"name": "<UPPER>",
          "allowed_anchor_types": [...sorted],
          "allowed_member_types": [...sorted],
          "allowed_anchor_graphs": [...sorted],
          "allowed_member_graphs": [...sorted],
          "ordered": <bool>,
          "property_types": {"k": "<PropertyType.value>"},
          "description": "<text-or-null>"}
       ]}
      ```
      Top-level `intergraph_hyperedge_types` array byte-stable sorted by `name`. Atomic write.
    - **Cumulative migration on metagraph state-file:** 05c binary reads v=2 ∪ v=3 (one-pass: populate `intergraph_hyperedges=[]` for v=2 default); first mutation writes v=3.
    - **Cumulative migration on metagraph-schema state-file:** 05c binary reads v=1 ∪ v=2 (one-pass: populate `intergraph_hyperedge_types=[]` for v=1 default); first mutation writes v=2.
    - **Strict version contract (P16-A):** Phase 05b binary loading v=3 metagraph file rejects (`this CLI supports v2` message). Phase 05b binary loading v=2 metagraph-schema file rejects (`this CLI supports v1` message). Recovery: hand-edit JSON downgrade.
    - **Graph state-file unchanged in 05c** — still v=4 (no graph-level changes).

  **Automated tests (location + intent — locked; test budget unlimited per `feedback_test_budget_unlimited.md`):**

    - `tests/phase_05c/` — projected test files (final count whatever coverage requires; tester records actual at `PHASE_05c_CONFIRMED.md`):
      - `test_intergraph_hyperedge.py` — dataclass kw_only, post_init regex on type_name, tuple-conversion at __post_init__, cardinality enforcement (n≥1, m≥1, NOT 1-1), anchor-member overlap forbidden, duplicates within a side allowed for ordered=True, `__setattr__` compositional immutability, `__setattr__` anchors/members/properties immutability when compositional=True, intergraph_hyperedge_id auto-mint, label round-trip, properties round-trip.
      - `test_intergraph_hyperedge_type.py` — frozen dataclass, ADR-0021 regex on name, 8 PropertyType variants, role-based allowed_anchor/member_graphs, type-based allowed_anchor/member_types, ordered field default True (P18-A), empty-set semantics.
      - `test_metagraph_schema_intergraph_hyperedge.py` — add_intergraph_hyperedge_type happy + duplicate refusal, validate_intergraph_hyperedge happy + role/type mismatch, validate_intergraph_hyperedge_properties strict-only.
      - `test_metagraph_attach_hyperedge_validation.py` — eager attach validates intergraph_edges (carry-forward) AND intergraph_hyperedges (new); metaedges/metahyperedges still skipped (Push9-A carry-forward); compositional+ordered=False existing edge refuses re-attach (P9-A drift refusal).
      - `test_compositional_hyperedge.py` — compositional flag immutability via `__setattr__`, factory accepts compositional=True only with ordered=True types (P8-A refusal at step 8.5), compositional hyperedge refuses remove + update + set-prop, `remove_graph` cascade precheck atomic refusal (extends 05b's pattern to walk hyperedges), error message includes edge_kind for both edge variants.
      - `test_ordered_canonicalization.py` — ordered=True preserves insertion + allows duplicates (cat=letter case), ordered=False sort+dedup at construction (canonicalization step in 16-step order), ordered=False with conflicting cardinality post-dedup raises 1-1 SchemaError (P14-A canonicalize-before-cardinality), ordered=True hyperedge round-trip preserves order, ordered=False hyperedge round-trip preserves canonicalized order.
      - `test_update_intergraph_hyperedge.py` — replace-only anchors+members+properties (P10-C), refuse if compositional, atomic rollback on validation failure, cardinality re-check on update (P19-A: 1-1 collapse refused), schema re-validation under attached schema, no-schema-attached update validates structurally only (P20-A), replace_properties=False merges, replace_properties=True replaces.
      - `test_intergraph_hyperedge_state_v3.py` — metagraph state-file v=3 round-trip with intergraph_hyperedges, byte-stable sort, atomic write, anchors/members preserved post-canonicalization.
      - `test_metagraph_migration_v2_to_v3.py` — v=2 load+populate intergraph_hyperedges=[] default, first mutation upgrades to v=3, idempotent on v=3, forward-version v=4 refused (P16-A strict version contract).
      - `test_metagraph_schema_state_v2.py` — schema state-file v=2 shape with intergraph_hyperedge_types, byte-stable sort, atomic write.
      - `test_metagraph_schema_migration_v1_to_v2.py` — v=1 load+populate intergraph_hyperedge_types=[] default, first mutation upgrades to v=2, idempotent on v=2, forward-version v=3 refused.
      - `test_cli_intergraph_hyperedge.py` — add-intergraph-hyperedge happy + paired-flags pairing by index + mismatched-counts refusal (P4-A) + --compositional flag, remove refuses on compositional, update with replace-only semantics (P10-C), list-intergraph-hyperedges JSON shape, role-based schema rejection, properties round-trip, intergraph-hyperedge-id override.
      - `test_cli_metagraph_schema_hyperedge.py` — add-intergraph-hyperedge-type with --ordered (default) and --unordered, schema mutation warning (P12-A), inspect --json shape gains intergraph_hyperedge_types.
      - `test_cli_set_prop_5way.py` — 5-way mutex on set-prop (--on-metagraph | --metaedge-id | --metahyperedge-id | --intergraph-edge-id | --intergraph-hyperedge-id), refusal on multiple flags, refusal on compositional intergraph-hyperedge.
      - `test_validation_order_hyperedge.py` — P14-A 16-step order; canonicalization-before-cardinality catches dedup-collapse-to-1-1; compositional+ordered=False refusal at step 8.5; first-failure most-specific error.
      - `test_remove_graph_cascade_hyperedge.py` — remove_graph precheck walks intergraph_edges + intergraph_hyperedges, atomic refusal on first compositional incident across both edge types, error message includes edge_kind.
      - `test_reserved_keys_hyperedge.py` — `intergraph_hyperedges` rejected as user property, `intergraph_hyperedge_types` rejected.
    - **Audit pass (pre-implementation):** review every `tests/phase_05b/test_state*.py` and `tests/phase_05a/test_state*.py` for hard-coded `_state_version: 2` (metagraph) and `_state_version: 1` (metagraph-schema) constants; update to use `state_mod.METAGRAPH_STATE_VERSION` / `state_mod.METAGRAPH_SCHEMA_STATE_VERSION` dynamically. Symmetric with 05a P14 / 04-v2 / 05b audit. Lock as pre-implementation task.

  **Confirmation command:**
    `mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md`
    (Init shape: `--init-notes 05c` is canonical; backward-compat alias `phase-05c` per 04-v2 / 05a / 05b pattern. Manifest stores `[mindsos] phase = "05c"`.)

  **Pass criterion:**

    - Tester can add an `IntergraphHyperEdgeType` to a metagraph schema with role-based anchor/member constraints + ordered/unordered semantic, attach to a metagraph (re-attach if previously attached in 05b), add an intergraph hyperedge with paired-flag CLI form satisfying the type constraints, observe round-trip persistence at metagraph state v=3 + metagraph-schema state v=2.
    - Tester sees structured refusal when add-intergraph-hyperedge violates: type-existence (no schema match), role mismatch (graph role not in `allowed_anchor_graphs` / `allowed_member_graphs`), type mismatch (node type not in `allowed_anchor_types` / `allowed_member_types`), cypher regex (lowercase type), cardinality (1-1 input redirected to IntergraphEdge), anchor-member overlap, compositional+ordered=False combination (P8-A refusal at step 8.5), paired-flag mismatch (e.g., 3 `--anchor-graph` flags + 2 `--anchor-node` flags refused per P4-A).
    - Tester sees `CompositionalImmutableError` on attempts to remove or set-prop or update on a compositional intergraph hyperedge; recovery only via `mindsos metagraph reset --name MG --force --yes` (carry-forward 05b Pushback 6-A).
    - Tester sees atomic refusal when `metagraph remove-graph` would orphan a compositional intergraph_hyperedge OR intergraph_edge; structured error includes edge_kind + edge_id; state file unchanged on raise.
    - Tester can `update_intergraph_hyperedge` with new anchors+members+properties (replace-only); validation re-runs full 16-step order; failure leaves edge unchanged; success replaces atomically.
    - Tester sees update refusal when result would collapse to 1-1 cardinality (P19-A no in-place hyperedge→edge downgrade).
    - Tester sees stderr warning when add-intergraph-hyperedge-type runs while schema is attached to N metagraphs (P12-A; carry-forward 05b Pushback 23-A).
    - Phase 05b v=2 metagraph state file loads cleanly under 05c binary; first mutation upgrades to v=3.
    - Phase 05b v=1 metagraph-schema state file loads cleanly under 05c binary; first mutation upgrades to v=2.
    - All Phase 03 + Phase 04 + Phase 04-v2 + Phase 05a + Phase 05b + Phase 05c tests pass cumulatively in-container.
    - Cumulative tests pass: ≥ Phase 05b baseline (740 + 2 skipped) + 05c additions; tester records actual count in `PHASE_05c_CONFIRMED.md` (no projection per `feedback_test_budget_unlimited.md`).

  **Risks / known issues to watch:**

    - **v=2 → v=3 metagraph state-file migration is one-way.** 05c binary touching a Phase 05b v=2 file upgrades on first mutation; Phase 05b binary then refuses with `this CLI supports v2` message. Recovery: hand-edit JSON downgrade (drop `intergraph_hyperedges` field, set `_state_version: 2`).
    - **v=1 → v=2 metagraph-schema state-file migration is one-way.** Same pattern as above.
    - **Schema mutation while attached** (P12-A) carries 05b Pushback 23-A footgun: adding a new IntergraphHyperEdgeType to a schema attached to N metagraphs does NOT trigger re-validation; existing intergraph_hyperedges retain their type_names. Tester must re-attach to surface drift.
    - **`ordered` flag flip on existing IntergraphHyperEdgeType** (via reset+rebuild) creates silent re-canonicalization wedge: existing hyperedges canonicalized under `ordered=True` are NOT re-canonicalized when type's `ordered` flips to False. Re-attach refuses if drift surfaces (P9-A); Push20-A `metagraph-schema reset` is the recovery.
    - **Compositional+ordered=False at construction is refused** (P8-A) — but a non-compositional hyperedge created under `ordered=True` cannot retroactively become compositional even if the type's `ordered` flag is preserved (compositional is set-at-create immutable; `update_intergraph_hyperedge` cannot flip it). Tester recovery: remove + add with compositional=True.
    - **Update under detached schema** (P20-A): structural-only validation; no schema/role/property-type check. Subsequent re-attach surfaces drift per Push7-A.
    - **`Graph.role` mutation post-attach** drifts schema validation silently (carry-forward 05b Pushback 25-A). Doc-convention immutable; no `__setattr__` enforcement in 05c. Future-work 25-B remains filed.
    - **`mindsos metagraph` subapp size** grows to ~26 subcommands after 05c (P10-C single combined update verb prevented further bloat); ~30+ after Phase 10. Future-work 33-B remains filed.
    - **No `remove-intergraph-hyperedge-type` verb** (mirror 05b Pushback 34-A); typo recovery requires `mindsos metagraph-schema reset --name MS --force --yes` and full vocabulary rebuild. Future-work 34-B already covers this case symmetrically.
    - **Stale `schema_name` reference** carry-forward of 05b Pushback 28-A + DMS-A.
    - **Cross-metagraph intergraph hyperedges are out-of-contract** (XRef = Phase 09).
    - **05b CHANGELOG amendment lands in this chat** documenting the discoverable-endpoint-update workaround for IntergraphEdge (P13-B retreat); no 05b code changes; new future-work entry filed.
    - **J-02 carry-forward** — no advisory locks on state files; debug-only single-tester surface. Phase 07 ships proper concurrency.

  **Doc sections this phase confirms:**

    - `docs/concepts/intergraph-edges.md` — amended (Phase 05b baseline) for n-ary primitive + cat=c+a+t example + ordered semantic + compositional+ordered=False refusal. `last_confirmed_phase: 05c`.
    - `docs/usage/core/metagraph-schema.md` — amended (Phase 05b baseline) with `IntergraphHyperEdgeType` vocabulary + `add-intergraph-hyperedge-type` CLI + `--ordered/--unordered` flag + Push12-A schema-mutation footgun. `last_confirmed_phase: 05c`.
    - `docs/usage/core/metagraphs.md` — amended (Phase 05b baseline) with intergraph-hyperedge subcommands + paired-flag CLI form + 5-way set-prop mutex + state-file v=2→v=3 migration + replace-only update. `last_confirmed_phase: 05c`.
    - `docs/api/core/intergraph-hyperedge.md` — full (NEW). API reference. `last_confirmed_phase: 05c`.
    - `docs/api/core/metagraph-schema.md` — amended (Phase 05b baseline) with new factory methods. `last_confirmed_phase: 05c`.
    - `docs/api/core/metagraph.md` — amended (Phase 05b baseline) with new factory methods + extended remove_graph cascade + extended attach_schema. `last_confirmed_phase: 05c`.
    - `docs/changelog/CHANGELOG.md` — Phase 05c entry appended; **05b entry amended** with discoverable-endpoint-update workaround note (P13-B retreat).
    - `mkdocs.yml` — nav entry for new `docs/api/core/intergraph-hyperedge.md`.
    - **ADR-0148** amended (full text in row appendix §B below; file edit Phase 38).
    - **ADR-0014** amended for the second time (full amendment text in row appendix §C below; file edit Phase 38).
    - **ADR-0017** unchanged in 05c (05d row carries the amendment for MetaEdgeType / MetaHyperEdgeType vocab).

  **Breaking changes from Phase 05b:**

    - `Metagraph` state-file v=2 → v=3 (one-way; documented above).
    - `MetagraphSchema` state-file v=1 → v=2 (one-way; documented above).
    - `mindsos metagraph set-prop` mutex extends from 4-way to 5-way; tester scripts using 05b's 4-way are forward-compatible (the 5th option is additive); error message text changes.
    - `mindsos metagraph inspect --json` shape gains `counts.intergraph_hyperedges` field (additive; tester scripts reading the 05b shape continue to work).
    - `mindsos metagraph list --json` shape gains `intergraph_hyperedges_count` per entry (additive).
    - `mindsos metagraph remove-graph --json` gains `cascaded_intergraph_hyperedges` field (additive).
    - `mindsos metagraph-schema inspect --json` shape gains `intergraph_hyperedge_types` array (additive).

  **Final amendments (2026-05-06 — locked across 4 reanalysis rounds; 20 numbered pushbacks):**

    1. **P1-B** — 05c scope narrowed; meta-vocabs deferred to 05d.
    2. **P2-refined** — `__setattr__` immutability scoped: compositional always; anchors/members/properties only when compositional=True. Tuple-conversion at `__post_init__` regardless of compositional flag.
    3. **P3** — MetaEdge.type_name field audit deferred to 05d.
    4. **P4-A** — Paired CLI flags (`--anchor-graph` / `--anchor-node` repeatable, paired by index).
    5. **P5-refined** — `ordered: bool` is type-driven set-vs-list; True = list semantics; False = sort+dedup at construction.
    6. **P6-A** — 05c eager-attach extends to walk intergraph_hyperedges; metaedges/metahyperedges still skipped (05d expiry).
    7. **P7-A** — Test budget unlimited; no projection.
    8. **P8-A** — Compositional+ordered=False refused at validation step 8.5.
    9. **P9-A** — No-schema default = ordered=True; refuse-on-drift via Push7-A.
    10. **P10-C** — Single replace-only `update_intergraph_hyperedge` verb covering anchors+members+properties.
    11. **P11→P13-B** — No 05b-v2 supersession for symmetric `update-intergraph-edge`; document workaround + file as future-work.
    12. **P12-A** — Schema-mutation footgun for `ordered` flip carries forward 05b Pushback 23-A pattern.
    13. **P14-A** — 16-step validation order with canonicalization-before-cardinality.
    14. **P15-A** — 05d row stub authored alongside this row.
    15. **P16-A** — Strict version contract on both state files.
    16. **P17-A** — 05c is last metagraph state-file bump until Phase 10.
    17. **P18-A** — `IntergraphHyperEdgeType.ordered` default = True (override design doc §3.3).
    18. **P19-A** — Update refusal on 1-1 cardinality collapse; future-work entry filed.
    19. **P20-A** — Update under detached schema validates structurally only.
    20. **Smaller items folded** — mint_id, __setattr__ pattern, remove_graph precheck extension, RESERVED_PROPERTY_KEYS, single-step migrations, set-at-create fields, no remove-*-type, doctor regex unchanged, flat CLI surface accepted, fixture reuse, paired-flag pairing semantics.

  **§A — 16-step validation order at `Metagraph.add_intergraph_hyperedge` (P14-A; appendix lock):**

    1. For each `(graph_id, _)` in `anchors`: `graph_id` must be a key in `mg.graphs` → else `IdentityError`.
    2. For each `(graph_id, _)` in `members`: `graph_id` must be a key in `mg.graphs` → else `IdentityError`.
    3. For each `(graph_id, node_id)` in `anchors`: `node_id` must be a key in `mg.graphs[graph_id].nodes` → else `IdentityError`.
    4. For each `(graph_id, node_id)` in `members`: `node_id` must be a key in `mg.graphs[graph_id].nodes` → else `IdentityError`.
    5. `type_name` must satisfy ADR-0021 cypher rel-type regex — enforced at `IntergraphHyperEdge.__post_init__` after dataclass instantiation; raises `CypherError`.
    6. (if `mg.schema is not None`) `mg.schema.require_intergraph_hyperedge_type(type_name)` → raises `UnknownTypeError` if vocab missing. Extract `type.ordered` for next step.
    7. **Canonicalize** (P14-A): if `type.ordered is False` (or no schema attached but caller passed via type defaulting — N/A in this code path; `ordered=True` default applies), preserve insertion order. If `type.ordered is False`, sort `anchors` lexicographically by `(graph_id, node_id)` then dedup; same for `members`. Result: canonical anchors/members tuples.
    8. **Cardinality check** on canonical anchors/members: `len(canonical_anchors) ≥ 1`, `len(canonical_members) ≥ 1`, `len(canonical_anchors) > 1 OR len(canonical_members) > 1` (NOT 1-1) — else `SchemaError("use IntergraphEdge for 1-to-1")`.
    9. **Anchor-member overlap check**: no `(graph_id, node_id)` pair in both canonical_anchors and canonical_members → else `SchemaError("anchor-member overlap forbidden")`.
    10. **P8-A refusal**: if `compositional is True` AND `type.ordered is False` → `SchemaError("compositional hyperedges require ordered=True types")`.
    11. `validate_user_properties(properties or {}, scope="intergraph_hyperedge")` → reserved-key + primitive-only check; raises `PropertyShapeError`.
    12. (if attached) `mg.schema.validate_intergraph_hyperedge(type_name, anchor_type_names, member_type_names, anchor_roles, member_roles)` → raises `UnknownTypeError` if any constraint fails.
    13. (if attached and `mg.schema.strict`) `mg.schema.validate_intergraph_hyperedge_properties(type_name, properties)` → raises `PropertyShapeError`.
    14. `intergraph_hyperedge_id = mg.mint_id("intergraph_hyperedge")` (or use caller-supplied if not None — same unregister-and-re-register dance as 05a metaedge override).
    15. Construct `IntergraphHyperEdge(...)` with canonical anchors/members tuples (dataclass `__post_init__` runs cypher regex + tuple-conversion + cardinality + overlap rechecks for direct-construction safety + sets `_initialized = True` for `__setattr__` override).
    16. `mg.identity.register(intergraph_hyperedge_id)` → raises `IdentityError` on collision. `mg.intergraph_hyperedges[intergraph_hyperedge_id] = hyperedge`. Return hyperedge.

    **Update path** (`Metagraph.update_intergraph_hyperedge`): runs steps 1-13 on the resolved replacement values (any field passed as `None` retains current value); skips steps 14 (mint id) and 16 (register); replaces tuple in-place via `object.__setattr__` on existing edge (step 15 modified to set `anchors`/`members`/`properties` on the existing instance rather than constructing a new one). Atomic: failure at any step leaves edge unchanged.

  **§B — ADR-0148 amendment text (full; file edit Phase 38):**

  > **2026-05-06 amendment (Phase 05c):** L1 Core's intergraph-edge family extends with `IntergraphHyperEdge` (n-ary anchors + members; NOT 1-to-1; cardinality enforced at API boundary) per the canonical design at `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md` §2.2 / §4.2 / §7. The hyperedge primitive is owned by the metagraph (not by either contained graph), registered in the metagraph's unified `IdentityRegistry` (ADR-0020), and persisted in the metagraph state file at the v=3 shape (added in this phase). Compositional immutability extends symmetrically to the n-ary case via `__setattr__` override on `IntergraphHyperEdge.compositional` (and on `anchors` / `members` / `properties` when `compositional=True`); non-compositional hyperedges support replace-only structural mutation via `Metagraph.update_intergraph_hyperedge`. Schema validation is metagraph-scoped via `IntergraphHyperEdgeType` (added to `MetagraphSchema` in this phase), with role-based graph constraints (`allowed_anchor_graphs` / `allowed_member_graphs` against `Graph.role`), type-based node constraints (`allowed_anchor_types` / `allowed_member_types` against `Node.type_name`), property-type maps, and an `ordered: bool = True` flag (P18-A default) controlling list-vs-set semantics: `ordered=True` preserves insertion order and allows duplicates within a side (cat=c+a+t case); `ordered=False` canonicalizes at construction (sort+dedup). Compositional+ordered=False is refused at the API boundary (P8-A — compositional implies identity-bearing composition; set semantics is incompatible). Persistence (Phase 07): n-ary Cypher Pattern B with `:ANCHOR` / `:MEMBER` typed relationships per anchor/member; OCC via n-lock canonical ordering (sort by `graph_id` string, acquire in order, release in reverse). Implementation deferred to Phase 07; 05c locks the contract.

  **§C — ADR-0014 second amendment text (full; file edit Phase 38):**

  > **2026-05-06 amendment (Phase 05c):** L1 Core's primitive list extends further with `IntergraphHyperEdge` (n-ary, NOT 1-to-1) per ADR-0148 amendment. Together with the 05b first amendment (which added `IntergraphEdge`), Core now ships six edge primitives: `Edge` and `HyperEdge` (within Graph, Phase 03); `MetaEdge` and `MetaHyperEdge` (between Graphs in Metagraph, Phase 05a); `IntergraphEdge` and `IntergraphHyperEdge` (between Nodes across Graphs in Metagraph, Phases 05b / 05c). XRef (Phase 09) will add the 7th. The amendment establishes that L1 owns the n-ary intergraph primitive at the model layer (`mindsos_core/models/intergraph_hyperedge.py`); schema validation lives in the existing `MetagraphSchema` container (extended in this phase with `IntergraphHyperEdgeType` vocabulary). The 05d amendment to this ADR-0014 entry will note `MetaEdgeType` + `MetaHyperEdgeType` vocab additions once those land.

  **§D — 05d dry-run appendix (pre-resolves 05d decisions that could retroactively wish for 05c changes):**

    - **05d will add `meta_edge_types` + `meta_hyperedge_types` arrays to MetagraphSchema state file** → bump v=2 → v=3. **05c's v=2 shape is forward-compat:** missing fields default to empty arrays. No 05c change needed.
    - **05d's `MetaEdge.type_name` field audit (P3 deferred):** if 05a's MetaEdge dataclass shipped without `type_name`, 05d adds the field as `Optional[str] = None` with rehydration tolerance for legacy entries. **05c does NOT touch metaedges; no interaction.**
    - **05d's eager-attach extension** to walk metaedges + metahyperedges (Push9-A from 05b expires in 05d). **05c's eager-attach pass** iterates intergraph_edges + intergraph_hyperedges only; 05d extends to also iterate metaedges + metahyperedges. No 05c change needed (additive in 05d).
    - **05d's CLI verbs** (`add-meta-edge-type` + `add-meta-hyperedge-type` on `metagraph-schema` subapp) carry the same Push12-A schema-mutation-footgun pattern as 05c's `add-intergraph-hyperedge-type`. No 05c change needed.
    - **05d's `RESERVED_PROPERTY_KEYS` extension** with `meta_edge_types` + `meta_hyperedge_types` (top-level metagraph-schema state v=3 fields). **05c's reserved-key addition** of `intergraph_hyperedge_types` is consistent with this pattern. No 05c change needed.

---

### Phase 05d — L1 MetaEdgeType + MetaHyperEdgeType vocab + eager-attach extension

  **Status:** Row LOCKED 2026-05-07 across 7 reanalysis rounds. Rounds 1–6 (M1–M7 meta-plan + P1–P30 design picks) at `confirmation_docs/PHASE_05d_DESIGN_LOG.md`. Round 7 (implementation-chat re-analysis pass; P31–P44 reverse-or-refine prior locks) at `confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md` §1. **Material rewrites in round 7:** P31 A drops the fingerprint mechanism entirely (and its `--accept-vocab-change` flag, metagraph state-file bump, validate `vocab_fingerprint_match` field, and instance-graph forward-compat assertion); P32 A adds `--schema MS` opt-in to `validate`; P39 A makes empty-vocab + non-strict eager-attach skip silently; P41 A splits exit code 2 into 2/3; P42 C lands a one-line ADR pointer instead of inline amendments; P44 A inverts the §C validation order to mirror the actual 05b precedent.
  **Branch:** phase-05d
  **Tag on confirm:** phase-05d-confirmed
  **Depends on:** 05c.
  **Layer(s):** L1.
  **Net-new?:** **Yes (small).** Two new vocab dataclasses (`MetaEdgeType` + `MetaHyperEdgeType`); 4-method extension to `MetagraphSchema`; eager-attach walk extended; 1 new CLI verb (`validate`) + 2 new `add-*-type` verbs; one schema state-file bump (v=2 → v=3). NO metagraph state-file bump (P31 A). NO new state-tracking pattern.

  **P3 audit RESOLVED 2026-05-07:** `MetaEdge.type_name: str` already present at `mindsos_core/models/metagraph.py:136` (required, ADR-0021 regex via `__post_init__`); `MetaHyperEdge.type_name: str` at `:180`. No dataclass expansion; no rehydration tolerance; no 05a-v2 supersession. 05d ships pure-vocab additions on top of an already-typed primitive.

  **Carry-forward from 05c deferrals (all resolved in this row):**
    - MetaEdgeType + MetaHyperEdgeType (deferred from 05b Pushback 1-C → 05c P1-B → 05d).
    - MetaEdge.type_name field audit (P3 deferred from 05c) — RESOLVED above.
    - Eager-attach extension to walk metaedges + metahyperedges (Push9-A from 05b expires here).

  **CRITICAL primitive distinction (load-bearing):** `MetaHyperEdge` connects GRAPHS with **NO graph repetition** (uniqueness enforced at `metagraph.py:194`). `IntergraphHyperEdge` connects NODES across graphs with repetition allowed (cat=c+a+t / "letter" compositional case). The 05c P18-A `ordered=True` rationale applies ONLY to `IntergraphHyperEdgeType` — NOT to `MetaHyperEdgeType`. Reference: memory `reference_mindsos_four_edge_primitives.md`.

  **Features:**

    **A. New vocab dataclasses (`mindsos_core/schema/types.py`):**

    - `MetaEdgeType` (frozen dataclass): fields `name: str`, `allowed_source_graphs: FrozenSet[str] = frozenset()`, `allowed_target_graphs: FrozenSet[str] = frozenset()`, `property_types: Dict[str, PropertyType] = {}`, `description: Optional[str] = None`. `name` validated against ADR-0021 cypher rel-type regex at registration. Empty frozenset on any allowed-* axis means "any" (mirrors `EdgeType` precedent). `Graph.role=None` is unmatchable when `allowed_*_graphs` is non-empty (Python set semantics). Mirrors 05b `IntergraphEdgeType` minus `allowed_*_types` (metaedges connect graphs, not nodes).

    - `MetaHyperEdgeType` (frozen dataclass): fields `name: str`, `allowed_member_graphs: FrozenSet[str] = frozenset()`, `property_types: Dict[str, PropertyType] = {}`, `description: Optional[str] = None`. **NO `ordered` field (P1 C lock).** Rationale: `MetaHyperEdge.graph_ids` is uniqueness-enforced at `metagraph.py:194`; the 05c P18-A "ordered=True permits duplicates" rationale collapses for graph-set semantics. Cardinality (n≥2) is enforced at the primitive (`metagraph.py:188-192`); type vocab adds role/property constraints only.

    **B. `MetagraphSchema` extension (`mindsos_core/schema/metagraph_schema.py`):**

    - `_meta_edge_types: Dict[str, MetaEdgeType] = {}` + `_meta_hyperedge_types: Dict[str, MetaHyperEdgeType] = {}` storage.
    - `add_meta_edge_type(met) -> MetaEdgeType` — registers; raises `UnknownTypeError` on duplicate name within MetaEdgeType vocab; raises `CypherError` on regex violation.
    - `require_meta_edge_type(name) -> MetaEdgeType` — lookup or raise `UnknownTypeError`. **Cross-vocab same-name informational hint (P38 B):** when name missing in MetaEdgeType but present in IntergraphEdgeType vocab, error message states "Name 'X' is registered in IntergraphEdgeType but not in MetaEdgeType." — information only, no editorial recommendation. Symmetric for MetaHyperEdge.
    - `validate_meta_edge(type_name, source_graph_role, target_graph_role)` — type-existence + role constraints. Always runs (independent of `strict`).
    - `validate_meta_edge_properties(type_name, properties)` — strict-only property-type checks (Phase 04 precedent: early-return when `not self.strict`).
    - Symmetric `add_meta_hyperedge_type` / `require_meta_hyperedge_type` / `validate_meta_hyperedge(type_name, member_graph_roles)` / `validate_meta_hyperedge_properties`.
    - **4-vocab Cypher namespace policy (P2 A):** the same `name` MAY appear in all four vocabularies (`IntergraphEdgeType`, `IntergraphHyperEdgeType`, `MetaEdgeType`, `MetaHyperEdgeType`). Mirrors 05c lock at `metagraph_schema.py:119-128`. Phase 11 schema-migrator owns deferred cross-vocab collision flagging (filed as future-work).

    **C. `Metagraph.add_metaedge` / `add_metahyperedge` validation order (P44 A — mirrors actual 05b `add_intergraph_edge` precedent at `metagraph.py:735-798`):**

    Order for `add_metaedge` when schema attached:
      1. `source_graph_id in self.graphs` (raise `IdentityError` else).
      2. `target_graph_id in self.graphs` (raise `IdentityError` else).
      3. `source_graph_id != target_graph_id` (raise `SchemaError` else; existing P15 self-loop refusal).
      4. `validate_user_properties` (reserved-key + `metaedge` scope).
      5. (if `self.schema is not None`) `schema.require_meta_edge_type(type_name)`.
      6. (if attached) `schema.validate_meta_edge(type_name, source_role, target_role)`.
      7. (if attached and `schema.strict`) `schema.validate_meta_edge_properties(type_name, properties)`.
      8. `self.identity.register(...)` then construct `MetaEdge(...)` (cypher regex fires in `__post_init__`).

    `add_metahyperedge` order: (1) member-containment loop → (2) `validate_user_properties` → (3) (if schema) `require_meta_hyperedge_type` → (4) (if attached) `validate_meta_hyperedge(member_roles)` → (5) (if attached and strict) `validate_meta_hyperedge_properties` → (6) construct `MetaHyperEdge(...)` (n≥2 + uniqueness + regex enforced via `__post_init__`).

    **Empty-vocab semantics on add (P39 A — preserves precedent asymmetry):** `require_meta_edge_type` raises on empty vocab regardless of `strict`. Operator workaround: detach schema, add metaedge, re-attach (eager-attach is permissive on empty vocab — see §D); or register the `MetaEdgeType` first and then add the metaedge.

    **D. Eager-attach extension (`Metagraph.attach_schema`):**

    Walks metaedges + metahyperedges for the first time (Push9-A from 05b expires). Iteration order is implementation-detail (P3 C); contract is "atomic precheck, refuses on first violation, error message names the offender unambiguously."

    **Empty-vocab semantics on eager-attach (P39 A — mirrors 05b/05c "Pushback 24-hybrid" precedent for `IntergraphEdgeType`):**
      - Empty `MetaEdgeType` vocab + non-strict + existing metaedges → **skip the metaedge walk silently**. Symmetric for `MetaHyperEdgeType`. Closes 05c-migration regression vector: 05c metagraphs migrate to 05d schemas with empty `meta_edge_types: []` and re-attach must succeed (or eager-attach refuses every existing metaedge).
      - Empty vocab + strict + existing metaedges → fail (vocab-existence is the strict invariant; consistent with 05b/05c precedent for `IntergraphEdgeType`).
      - Non-empty vocab → walk every metaedge / metahyperedge: `require_meta_*_type` then `validate_meta_*` (always) then `validate_meta_*_properties` (strict only — P13 A).

    NO fingerprint computation (P31 A); no consent flag; no state mutation beyond `self.schema = schema; self.schema_name = schema_name` on all-pass.

    **E. Drift narrative (reframed per M7):**

    Re-attach drift = "metaedge `type_name` not registered in `MetaEdgeType` vocab" (vocab-gap), NOT field-absence. Recovery: populate the schema vocab with the missing `MetaEdgeType` / `MetaHyperEdgeType` entries, THEN re-attach. **No "non-strict attach" recovery (P4 A):** `MetagraphSchema.strict` gates property-type validation only; it cannot bypass eager-attach vocab-gap refusal. (Empty-vocab + non-strict pass-silently per §D is precedent-consistent and is NOT a "non-strict bypass" — it is the empty-vocab grandfathering rule.)

    **F. State-file version bump (P31 A — single bump only; metagraph state-file untouched):**

    - **Metagraph-schema state file v=2 → v=3:** adds `meta_edge_types: []` + `meta_hyperedge_types: []` default arrays. `_v2_to_v3` is a single-step append; defensive null→[] normalization for malformed inputs. Per-file migration chain extended at `mindsos_cli/migrations/metagraph_schema.py`.
    - **Metagraph state file stays at v=3.** No fingerprint, no `--accept-vocab-change`, no metagraph migration step (P31 A removed the entire mechanism).

    **G. CLI surface:**

    - `mindsos metagraph-schema add-meta-edge-type --schema MS --type-name T [--allowed-source-graph ROLE]... [--allowed-target-graph ROLE]... [--prop-type k=PT]... [--description STR] [--json]` — registers a `MetaEdgeType`. P29 A: `--json` parity with 05c add verbs.
    - `mindsos metagraph-schema add-meta-hyperedge-type --schema MS --type-name T [--allowed-member-graph ROLE]... [--prop-type k=PT]... [--description STR] [--json]` — symmetric. **No `--ordered/--unordered` flag** (P1 C dropped the field).
    - `mindsos metagraph-schema validate --metagraph MG [--schema MS] [--json]` (P9 B + P32 A — NEW VERB): walk-only validation. Default resolves schema via `MG.schema_name`; **`--schema MS` opt-in (P32 A)** validates `MG` against the explicit `MS` (state-only; doesn't mutate `MG.schema_name` or `MG.schema`). Empty-vocab semantics mirror eager-attach (P39 A — non-strict + empty vocab passes silently). Exit codes (P41 A): **0 pass; 1 violation; 2 resource-not-found (schema or metagraph); 3 no-usable-schema (neither attached nor `--schema` supplied).** `--json` shape (P40 A — fingerprint field dropped per P31 A): `{ "passed": bool, "schema_name": str, "metagraph_name": str, "violations": [{"primitive": "MetaHyperEdge", "edge_id": "...", "type_name": "X", "rule": "allowed_member_graphs", "detail": "..."}, ...] }`.
    - `mindsos metagraph attach-schema` is **unchanged** in 05d (no `--accept-vocab-change` flag — P31 A removed the consent mechanism).
    - **Schema-mutation footgun (P8 A):** `add-meta-edge-type` / `add-meta-hyperedge-type` reuse `_find_attached_metagraphs` helper at `mindsos_cli/commands/metagraph_schema.py:171`; emit verbatim 05c warning "Schema 'X' is currently attached to N metagraph(s): [...]; mutations apply lazily but will surface at next attach validation."

    **H. ADR pointer edits (P42 C):** Add a one-line pointer at the top of `docs/decisions/adr/0014-layer-boundary-core-only.md` and `docs/decisions/adr/0017-schema-strictness-opt-in.md`: "*See `confirmation_docs/PHASE_MAP.md` §5 for amendments through Phase 05d.*" Closes the discoverability gap for filename-search readers without breaking the deferred-full-transcription precedent (full text still ships in Phase 38). The pointer is added to BOTH files in 05d's PR even though it covers 05b/05c amendments too — single landing point.

  **Reads:**
    - `confirmation_docs/PHASE_05d_DESIGN_LOG.md` — rounds 1–6 pick log (M1–M7 + P1–P30).
    - `confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md` — round 7 pick log (P31–P44; load-bearing for the row's current shape).
    - memory `reference_mindsos_four_edge_primitives.md` — primitive distinction.
    - `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md` §3.3 — analogous role-based constraint surface.
    - 05b row §A and `metagraph.py:735-798` — actual 05b `add_intergraph_edge` validation order (the precedent §C mirrors per P44 A).
    - 05c row §A — schema-mutation footgun model; `_find_attached_metagraphs` helper.
    - `mindsos_core/models/metagraph.py` (`MetaEdge:116`, `MetaHyperEdge:162`); `mindsos_core/schema/types.py` (existing `IntergraphEdgeType:107`, `IntergraphHyperEdgeType:149`); `mindsos_core/schema/metagraph_schema.py`; `mindsos_core/models/graph.py:94` (`role: Optional[str]`).

  **Risks:**
    - **05c-migration: 05c metagraphs with metaedges + 05c schemas migrating to v=3 (gaining empty `meta_edge_types: []`).** P39 A's empty-vocab pass-silently rule on eager-attach is the closing mechanism. Tester verifies: attach a 05c-shipped metagraph (with metaedges) to a 05c-shipped schema migrated to v=3 (no `MetaEdgeType` registered) under non-strict — must succeed.
    - **add-vs-attach asymmetry on empty vocab.** `add_metaedge` raises on empty vocab; eager-attach passes silently. Documented in §C and §D. Operator workaround for "I have a schema attached but vocab is empty and I want to add a metaedge": detach → add → re-attach. Mirrors the 05b/05c precedent for IntergraphEdgeType.
    - **Schema-mutation footgun extends** to MetaEdgeType / MetaHyperEdgeType (P8 A — same stderr warning).
    - **Cross-vocab name collisions** allowed (P2 A); Phase 11 owns deferred flagging (future-work).

  **Tests (no budget cap per `feedback_test_budget_unlimited.md`):** projected coverage spans new dataclass construction + cypher regex; schema registration verbs; validation paths (type-existence, role constraints, property types); eager-attach extension (non-empty vocab pass, vocab-gap refusal, empty-vocab + non-strict pass-silently per P39 A, empty-vocab + strict refusal); add-metaedge / add-metahyperedge validation order per P44 A; add-on-empty-vocab raises; `validate` verb (pass, violation, schema-not-attached → exit 3, schema-not-found → exit 2, metagraph-not-found → exit 2, `--schema MS` opt-in path, `--json` shape per P40 A); migration v=2→v=3 schema (idempotency on re-load, defensive null→[] normalization); cross-vocab informational hint per P38 B in error message. Migrate hard-coded schema-side `_state_version` constants in `tests/phase_05c/test_state_v3_round_trip.py` (4 sites per P43 audit) to dynamic `ms_migrations.CURRENT_VERSION` form.

  **Docs:** `docs/usage/core/metagraph-schema.md` (amended for MetaEdgeType + MetaHyperEdgeType + `validate` verb); `docs/api/core/metagraph-schema.md` (amended); `docs/changelog/CHANGELOG.md` (Phase 05d entry); ADR-0014 + ADR-0017 pointer lines per §H + P42 C.

  **Future-work entries filed (P24 B carry-forward; P33 A removes the instance-graph forward-compat assertion from the row but keeps the future-work entry):**
    - **(i) Instance-graph role mutability (Phase 06)** — when Phase 06 ships `mindsos_instances`, the row must lock whether instance-graphs preserve their source graph's `role` immutably or permit override. 05d does NOT pre-bind this; vocab validation reads `Graph.role` from whichever Graph object is in the metagraph regardless of base-vs-instance. **RESOLVED 2026-05-11 in Phase 06 row-refinement chat: M6 A + P1 A locked option (a) immutable** (instance-graphs propagate `Graph.role` as read-only mirror; override attempts raise). No state-file change. See Phase 06 row §B (per-subclass allow-list — `GraphInstance` ships with empty scope, role excluded).
    - **(ii) Phase 11 cross-vocab name-collision flagging** — same `name` registered in `MetaEdgeType` AND `IntergraphEdgeType` (or any cross-vocab pair) is allowed at registration; Phase 11 schema-migrator should optionally flag these collisions for review.

### Phase 06 — L1 Instancing (`mindsos_instances`) — sibling package with 8 instance subclasses + cascade-observer

  **Status:** Row LOCKED 2026-05-11 across 6 design rounds + 1 implementation round-7 pass. Meta-plan picks (M1–M6) + design picks (P1–P44; 2 user overrides at P13 B + P24 B) at `confirmation_docs/PHASE_06_DESIGN_LOG.md`. **Round-7 reanalysis pass (P45–P65) ran BEFORE any code landed**, per 05d precedent — 21 numbered pushbacks (`confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` §1) reshaped the row before implementation. **Material reshapes from initial stub:** ADR-0132's "move from Core" framing struck (P2 A); 4-verb CLI (P38 A); per-subclass structural override allow-list (P29 C + P36 A); cascade-delete observer in `mindsos_core` (P31 A). **Round-7 reshapes:** ADR file edits deferred to Phase 38 per cascade precedent (P45 B); ID derivation drops overrides-hash (P46 C); bifurcated override-validation routing (P64 A); endpoint-resolution walk in materialise (P58 A); SubGraphInstance cascade routing (P59 A); atomic Core observer (P65 A); GraphInstance materialise = full clone (P54 B); composite JSON wraps asdict with canonicalize (P63 A); package-integration checklist (P62 A); CLI exit codes (P53 A).
  **Branch:** phase-06
  **Tag on confirm:** phase-06-confirmed
  **Depends on:** 05d (last in 05 cascade per CASC-1 strict-sequential).
  **Layer(s):** L1.
  **Net-new?:** **Yes (medium).** New sibling package `mindsos_instances/` (8 subclasses + ElementRegistry + materialise machinery + canonicalize utility); small `mindsos_core` hook for remove-observer (~15 LOC); ADR-0132 amended inline; ADR-0037 status flip; stale ADR-0024 reference fixed; new CLI subapp (`mindsos instances`) with 4 verbs. **No state-file bumps** (P8 B — persistence is Phase 07).

  **P2 audit RESOLVED 2026-05-11:** `mindsos_core/models/` has no `instance.py` (confirmed via Glob); `mindsos_core/__init__.py:54` is a deferral comment, not active code; no `Metagraph.instantiate_*` factory methods exist; no `:ElementInstance` references anywhere in Core. ADR-0132's "move from Core" framing was written assuming pre-redesign Core had instancing; current Core does not. **Phase 06 ships fresh code in `mindsos_instances/`; ADR-0132 amended inline per P2 A to strike the move framing and the deprecated re-export plan.**

  **Carry-forward from 05d:**
    - Instance-graph role mutability open question (filed at `_source_backup/root/mindsos_future_plans.md` per 05d round-7 P33 A) → RESOLVED in this row via M6 A + P1 A: **immutable role** (instance-graphs propagate `Graph.role` as a read-only mirror; override attempts raise).
    - Round-7 reshape precedent — implementation chat permitted to file P45+ if surface contradictions surface.

  **CRITICAL semantic (load-bearing per user P24 + P27):** instances are *live* references representing current component state. They cannot exist without a real component reference. Hard-delete of a template cascades into the registry (P24 B + P31 A); cascade is recursive through composites (P44 A). Override never writes back to template (ADR-0015 holds); the instance is *the* deviation. In practice components are deleted only by admin at release boundaries (per L0 server pivot RELEASE_SHIP_LOCK semantics) — cascade rarely fires at per-session runtime but is a correctness invariant.

  **Features:**

    **A. New sibling package `mindsos_instances/` (per ADR-0132 amended per P2 A):**

    Public API (`mindsos_instances/__init__.py`):
    ```python
    from mindsos_instances import (
        ElementInstance,
        NodeInstance, EdgeInstance, HyperEdgeInstance,
        SubGraphInstance, GraphInstance,
        MetaEdgeInstance, MetaHyperEdgeInstance,
        CompositeInstance,
        ElementRegistry,
        DanglingTemplateError, CompositeCycleError,
        CrossMetagraphCompositeError, SubGraphInvariantError,
        OverrideScopeError,
    )
    ```

    **B. Element instance subclasses (8) — `mindsos_instances/models/`:**

    Each subclass carries: `id: str` (from shared `IdentityRegistry`), `template_id: str` (ID-reference per P23 A), `metagraph_id: str` (registry routing), `overrides: dict` (validated per P17 A + P36 A), `KIND: ClassVar[str]` (P26 C class-level discriminator). All `kw_only=True` dataclasses.

    Each subclass also carries `_instance_seq: int` (round-7 P46 C — per-template per-metagraph sequence counter sourced from `mg.element_registry._next_seq_for(template_id)` at construction; used as the ID-derivation disambiguator in place of the original overrides-hash).

    Per-subclass `KIND` constants + override allow-list (P36 A + round-7 P48 A `label` additions + round-7 P60 A `graph_ids` rename):
    | Subclass | KIND | Allowed override keys |
    |---|---|---|
    | `NodeInstance` | `"node"` | user properties only |
    | `EdgeInstance` | `"edge"` | user properties + `source_id`, `target_id`, `label` |
    | `HyperEdgeInstance` | `"hyperedge"` | user properties + `member_ids` (set of node IDs), `label` |
    | `SubGraphInstance` | `"subgraph"` | `node_ids` (set), `edge_ids` (set) only — no user property bag (P13 B) |
    | `GraphInstance` | `"graph"` | empty override scope (no structural surface in Phase 06; user property bag is Phase 10) |
    | `MetaEdgeInstance` | `"metaedge"` | user properties + `source_graph_id`, `target_graph_id`, `label` |
    | `MetaHyperEdgeInstance` | `"metahyperedge"` | user properties + `graph_ids` (set), `label` |
    | `CompositeInstance` | `"composite"` | bundle-level user properties only (member-list mutation via dedicated API per P37 A) |

    **Universally forbidden override keys (round-7 P47 C — `source_id` redundancy removed):** `id`, `template_id`, `kind`, `metagraph_id`, `type_name` (Edge/HyperEdge/MetaEdge/MetaHyperEdge per P33 B). Raises `OverrideScopeError`. (The per-subclass allow-list above is authoritative for structural-field overrides; reserved field names like `source_id`/`label` are explicitly permitted only when they appear in a subclass's allow-list.)

    **Override-validation routing (round-7 P64 A — bifurcated):** override-dict splits at validation time into two buckets:
    1. **Structural bucket** — keys in the subclass's allow-list above. Typed-validated against the structural-field contract (string for ID-overrides; set/list for set-typed fields; primitive types for `label`).
    2. **User-property bucket** — keys NOT in the structural allow-list. Routes through `validate_user_properties(props, scope=KIND)` (Phase 04 surface; `scope` is a free-form str per `validation.py:145`).

    A key in `RESERVED_PROPERTY_KEYS` (`validation.py:34`) that lands in bucket 2 raises `OverrideScopeError`. The bifurcation lives in `mindsos_instances/models/_overrides.py`; Phase 04's `validate_user_properties` signature is unchanged.

    **Set-typed structural fields (round-7 P57 A — list→set coercion):** keys `member_ids` (HyperEdgeInstance), `node_ids`/`edge_ids` (SubGraphInstance), `graph_ids` (MetaHyperEdgeInstance) accept JSON list input + coerce to Python `set` / `frozenset` at override-set time. Duplicates dedup silently (matches Python set semantics).

    **SubGraphInstance invariant (P20 A — strict):** every edge in `edge_ids` must have BOTH endpoints in `node_ids`; every HyperEdge in `edge_ids` must have ALL members in `node_ids`. Enforced at construction via `SubGraphInvariantError`. Also enforced after each `set_override` mutation of `node_ids` or `edge_ids`.

    **C. ElementRegistry (`mindsos_instances/registry.py`) — in-memory only (P4 B + P8 B):**

    Per-metagraph registry. Attached to `Metagraph` via round-7 P49 A idempotent helper: `mindsos_instances.attach_registry(mg) -> ElementRegistry`. `Metagraph` itself has NO `element_registry` attribute set in Core (round-7 P49 B+A — Core/instances boundary preserved per ADR-0010). The helper installs the registry as `mg.element_registry` lazily on first call; subsequent calls return the same registry.

    API:
    - `add(instance: ElementInstance | CompositeInstance) -> None` — also calls `mg.identity.register(instance.id)` (P11 A shared registry).
    - `get(instance_id: str) -> ElementInstance | CompositeInstance`
    - `remove(instance_id: str) -> None` — fires recursive cascade through composites containing the removed instance (P44 A). **Round-7 P56 A:** also calls `mg.identity.unregister(instance_id)` after dict-delete (closes IdentityRegistry leak on cascade).
    - `iter(kind: Optional[str] = None) -> Iterator[...]` — `None` returns all (element instances + composites); kind-specific filtering uses class-level `KIND` constants per P26 C.
    - `_next_seq_for(template_id: str) -> int` (private, round-7 P46 C) — per-template monotonic counter; used by subclass `__init__` for the `_instance_seq` ID-derivation disambiguator.

    `add_member` (on `CompositeInstance`) — round-7 P55 A enforcement: raises `IdentityError` if `instance.id not in registry`. Closes the stale-ref bug-class (cascade-removed instances cannot be re-added to composites).

    Cross-metagraph composite members forbidden (P43 C + round-7 P50 A): `CompositeInstance.__init__` requires `metagraph_id` kw-only; `add_member` raises `CrossMetagraphCompositeError` if member's `metagraph_id` differs. Empty composites legal.

    Lifecycle (P35 A): Python ownership. While metagraph lives, registry lives, observer subscriptions remain active. Round-7 P52: no explicit teardown event exists — registry is GC'd when its owning metagraph is. Tests assert the registered-cascade-active behavior; no teardown/unsubscribe tests (the underlying API doesn't exist).

    **D. Canonicalization utility (`mindsos_instances/utils/canonicalize.py`):**

    Round-7 P46 C: original P11 A use ("include overrides hash in ID derivation") is dropped — `UUID5FromContentStrategy`'s docstring (`identity.py:86-92`) explicitly warns against content-addressable IDs for mutation-prone objects, and instance overrides ARE mutation. Instance IDs now derive via `mg.id_strategy.generate("instance", content={"template_id": tid, "instance_seq": next_seq})` — overrides do not participate.

    The canonicalize utility survives with two real consumers:
    1. **`set_override`-time validation** — comparison of new-override-bundle vs old-override-bundle for change-detection on mutable instances (Phase 06 in-memory use; Phase 07 persistence-layer extends).
    2. **Round-7 P63 A composite materialise JSON stability** — `dataclasses.asdict` on `HyperEdge` (with `Set[Node]` field) / `MetaHyperEdge` (with `FrozenSet[str]` field) produces non-deterministic list ordering; composite materialise wraps `asdict` output through canonicalize for stable JSON output (avoids golden-output test flakes).

    Rule (P34 B): sets → sorted lists; dicts → sorted-key JSON; recursive on nested structures; output is `json.dumps(canonical, sort_keys=True)`. ~30 LOC.

    **E. Materialise machinery (P6 A + P18 A + P40 A; round-7 P51 A + P54 B + P58 A + P63 A spec):**

    Signature: `instance.materialise(metagraph: Metagraph) -> Core-object | dict[str, ...]`. Returns:

    - **NodeInstance** → fresh `Node` with merged properties (template props ⊕ overrides). Fresh UUID per call.
    - **EdgeInstance** → fresh `Edge`. Endpoint resolution per round-7 P58 A: if override carries `source_id` and/or `target_id`, helper `mindsos_instances/_resolve.py::resolve_node(metagraph, node_id)` walks `metagraph.graphs.values()` for the override-id'd Node; raises `IdentityError` if not found in any contained Graph. Without endpoint override, the template Edge's `source` and `target` Node objects are used directly. `label` override per round-7 P48 A passes through structural bucket. `type_name` forbidden per P33 B. Fresh `edge_id` per call.
    - **HyperEdgeInstance** → fresh `HyperEdge`. Endpoint resolution: if override carries `member_ids` (set/list of node IDs per round-7 P57 A coercion), each ID resolves via `_resolve.resolve_node(metagraph, nid)`. Without override, template's `nodes: Set[Node]` is reused. Fresh `edge_id`.
    - **SubGraphInstance** (round-7 P51 A spec) → fresh `Graph`:
      - Fresh `IdentityRegistry` (independent of source metagraph's registry; matches "many cheap materialisations" intent from ADR-0019).
      - Nodes for `node_ids`: looked up in source `Graph` (by `template_id`); each cloned via `dataclasses.replace(orig_node, node_id=new_uuid)` with deep-copy of `properties`.
      - Edges for `edge_ids`: looked up in source `Graph`; cloned via `dataclasses.replace(orig_edge, edge_id=new_uuid, source=new_node_map[orig_edge.source.node_id], target=new_node_map[orig_edge.target.node_id])` with deep-copy of `properties`. HyperEdges symmetric.
      - `role` inherited from source graph (P1 A immutable).
      - No schema attached to the materialised Graph (attach is a separate concern).
      - Fresh `graph_id`.
    - **GraphInstance** (round-7 P54 B spec) → fresh `Graph` **full clone**: every node + edge + hyperedge of source Graph cloned with fresh IDs via the same `dataclasses.replace` pattern as SubGraphInstance materialise. Fresh `IdentityRegistry`. `role` inherited. Source's `properties` deep-copied. Audit-cleared use case: template-clone workflows (instantiate-graph-template → attach-elsewhere). GraphInstance's empty override scope (per §B) means materialise applies no overrides beyond the structural copy.
    - **MetaEdgeInstance** → fresh `MetaEdge`. Endpoint resolution: `source_graph_id`/`target_graph_id` overrides validated via `metagraph.graphs[gid]` direct lookup (Metagraph already keys graphs by id; no walk required). Raises `IdentityError` if unknown gid.
    - **MetaHyperEdgeInstance** → fresh `MetaHyperEdge`. `graph_ids` override (round-7 P60 A name + P57 A coercion) → each gid validated via `metagraph.graphs[gid]` direct lookup.
    - **CompositeInstance** → recursive tree wrapped under top-level shape (P18 A + P39 A; round-7 P63 A canonicalize wrap):
      ```
      {
        "kind": "composite",
        "id": "...",
        "metagraph_id": "...",
        "bundle_overrides": {<canonicalize(composite.bundle_overrides)>},
        "members": {member_id: <Core-object JSON-via-canonicalize(asdict) or recursive composite dict>}
      }
      ```
      Each element-instance member materialised independently (ADR-0026 — no propagation of `bundle_overrides`); `dataclasses.asdict` output is wrapped through canonicalize utility for stable JSON ordering of set-typed fields. Caller combines (P30 A — no auto-combine helper in Phase 06).

    Materialise does NOT re-validate against schema (P16 A — validation is attach-time concern, Phase 07). Materialise on instance with dangling template raises `DanglingTemplateError` (defense-in-depth; under normal cascade-observer operation the instance is removed before materialise can fire).

    **F. Cascade-delete observer hook in `mindsos_core` (~50 LOC; P31 A + round-7 P49 B + P56 A + P59 A + P65 A):**

    Round-7 P49 B+A — Core ships **plumbing only**; no import of `mindsos_instances` (preserves ADR-0010 boundary). Add observer-pattern extension to `Graph` (`remove_node` / `remove_edge` / `remove_hyperedge`) and `Metagraph` (`remove_graph` / `remove_metaedge` / `remove_metahyperedge` / `remove_intergraph_edge` / `remove_intergraph_hyperedge`):

    - `register_remove_observer(callback: Callable[[str], None]) -> ObserverHandle` on each — returns an opaque handle that callers retain for explicit unsubscribe if needed.
    - Each remove method runs the observer dispatch loop **atomically (round-7 P65 A)**: snapshot the to-be-removed entity (or referenced dict slot) → mutate → invoke registered callbacks with the removed id → on any callback exception, restore from snapshot + propagate the exception. State stays consistent across observer failures. ~10 LOC per remove method × 6 methods.
    - `mindsos_instances.attach_registry(mg)` (round-7 P49 A idempotent helper) constructs `ElementRegistry(mg)` which subscribes to the metagraph's remove events; routes by `template_id`. Core does not import `mindsos_instances`.

    Cascade chain on hard-remove of template T:
    1. Core remove method finds T; snapshots state; deletes T from its container dict; calls observer callbacks (round-7 P65 A — exception in any callback rolls back the snapshot and re-raises before subsequent callbacks).
    2. `element_registry` callback queries instances matching the removed id (round-7 P59 A — extended lookup):
       - element-instance subclasses where `template_id == removed.id` → cascade-remove;
       - `SubGraphInstance` whose `node_ids` or `edge_ids` contains `removed.id` → cascade-remove (closes the SubGraphInstance-stale-reference bug-class P59 surfaced).
    3. `registry.remove(instance_id)` (per match) does three things atomically: dict-delete from internal store; `mg.identity.unregister(instance_id)` (round-7 P56 A — closes IdentityRegistry leak); checks composites containing the removed instance; recursively removes them (P44 A); fires its own cascade for those composites.
    4. Depth bounded by composite-nesting depth (small).

    Observer exception semantics (round-7 P65 A): atomic — if any subscribed observer raises, the originating Core remove method rolls back its mutation and propagates the exception. The live-instance invariant (P24 B / P27) is not violated by observer-side failures.

    Soft-delete (Phase 10 `deprecated_at`/`disputed_at`) is orthogonal (P32 A); future-work entry tracks the eventual decision.

    **G. ADR amendments — DEFERRED to Phase 38 per cascade precedent (round-7 P45 B):**

    Audit run during round-7 confirms ADR files at `docs/decisions/adr/` do **not** exist on disk (verified via Glob — no `0132*`, `0014*`, `0015*`, etc. anywhere in the repo). 05d implementation log §70 documents the precedent: *"05b and 05c amendments are NOT on disk in those ADR files (they're deferred to Phase 38 per shipped precedent)."* P2 A's original "rewrite to match reality" justification is moot — there is no on-disk reality to rewrite. PHASE_MAP §5 row text stays canonical; Phase 38's full ADR-port batch absorbs the amendments below.

    Deferred to Phase 38:
    - ADR-0132 — material rewrite of Decision section per P2 A; status Proposed → Accepted on Phase 06 ship.
    - ADR-0037 — status flip Proposed → Superseded (by ADR-0132) per P19 A.
    - ADR-0015 / 0019 / 0025 / 0026 — pointer-line additions per 05d P42 C precedent.

    On-disk amendment that survives in this PR (the only one with a target that exists today):
    - **`mindsos_core/__init__.py:54`** — fix stale `ADR-0024 / ADR-0025` reference → `ADR-0015` per P19 A; update deferral comment to ship-status: `* element_instances / composite_instances (ADR-0015) — SHIPPED in Phase 06 via mindsos_instances package.`

    **H. CLI surface (4 verbs; M4 B + P38 A + P41 A + P42 A):**

    All verbs scope to one metagraph; require `--metagraph MG`; print JSON to stdout when `--materialise` is set; otherwise print the instance's JSON shape (no materialise).

    - `mindsos instances instantiate-node --metagraph MG --template-id NODE_ID [--override key=val]... [--materialise] [--json]` — creates a `NodeInstance`; if `--materialise` flag, prints materialised `Node` JSON via `dataclasses.asdict`.
    - `mindsos instances instantiate-edge --metagraph MG --template-id EDGE_ID [--override key=val]... [--materialise]` — symmetric for EdgeInstance.
    - `mindsos instances instantiate-hyperedge --metagraph MG --template-id HE_ID [--override key=val]... [--materialise]` — symmetric for HyperEdgeInstance.
    - `mindsos instances compose --metagraph MG --member-spec JSON [--member-spec JSON]... [--bundle-override key=val]... [--materialise]` — creates a `CompositeInstance` whose members are constructed from each `--member-spec` (inline JSON: `{"kind":"node","template_id":"N1","overrides":{...}}`). `--materialise` prints the composite materialise tree per §E.

    `--override key=val` value parsing (P42 A): JSON-fragment. `--override age=31` parses as integer 31. Strings need quoting: `--override name='"Alicia"'`. Lists: `--override member_ids='["N1","N2"]'`.

    No separate `materialise` verb (P38 A); no `set-override` verb (P12 B → flag-based).

    Single-call demonstration semantics (P12 B + P8 B): each CLI invocation creates instances in a fresh `element_registry`, optionally materialises, prints, and exits. No state-file persistence across calls; container `--rm` destroys the in-memory state cleanly.

    **CLI exit codes (round-7 P53 A — adopts 05d split):**
    - `0` — success.
    - `1` — invariant violation: `OverrideScopeError`, `SubGraphInvariantError`, `CompositeCycleError`, `CrossMetagraphCompositeError`, `DanglingTemplateError`.
    - `2` — resource-not-found: unknown `--metagraph` (state-file missing); unknown `--template-id` (`IdentityError` from endpoint-resolution walk or template lookup).
    - `3` — reserved (no Phase 06 use; preserved for cascade consistency with 05d's exit-code grammar).

    **I. State-file impact: NONE in Phase 06 (P8 B).**

    No new state file; no version bumps on metagraph/graph/schema state files. Instances live in-memory only. Persistence handed to Phase 07 (which lands `InstanceRepository` + `InstanceLoader`); MetagraphLoader extension point (`register_attach_handler`) lands in Phase 08.

    **J. Drift narrative + speculative-feature audit (M5 C):**

    Phase 06 ships 8 subclasses per ADR-0132 enumeration. M5 C audit per subclass:
    - `NodeInstance` / `EdgeInstance` / `HyperEdgeInstance`: concrete Phase 03 primitive consumers; CLI-exercised.
    - `CompositeInstance`: concrete (composite is the structural-deviation vehicle per P29 C).
    - `SubGraphInstance` (P13 B): concrete semantic locked (triple + invariant); library-tested.
    - `GraphInstance`: ships empty-scope; ADR-0132 enumeration justification + Phase 10 fills surface.
    - `MetaEdgeInstance` / `MetaHyperEdgeInstance`: structural endpoint override is the primary use case; library-tested.

    All 8 audit-cleared. No subclass deferred.

    **K. Package integration (round-7 P62 A — first top-level package addition since Phase 02):**

    `mindsos_instances/` is a new top-level Python package. The integration checklist:
    1. **`pyproject.toml`** — add `mindsos_instances` to the `[tool.setuptools.packages.find]` list (or equivalent `packages = [...]` field if hatchling-style).
    2. **`compose.yml`** — verify the `mindsos` service mount/build context picks up `mindsos_instances/` alongside `mindsos_core` and `mindsos_cli`; if explicit COPY directives exist in `Dockerfile`, add `mindsos_instances/`.
    3. **`mindsos_cli/doctor.py`** — extend the version-string-parity check to assert `mindsos_instances.__version__ == mindsos_core.__version__ == mindsos_cli.__version__` (Phase 02 introduced the parity gate; Phase 06 adds the third checked package). Doctor import-check confirms `import mindsos_instances` succeeds.
    4. **Version-string bump 4 sites** (`+phase05d` → `+phase06`): `mindsos_core/__init__.py:__version__`, `pyproject.toml`, `compose.yml`, manifest. **+1 new site** for `mindsos_instances/__init__.py:__version__`.

    Without this checklist explicit, the version-string-drift bug-class that bit 05a (5-site regex audit per `feedback_tag_regex_audit.md`) recurs.

  **Reads:**
    - `confirmation_docs/PHASE_06_DESIGN_LOG.md` — full pick log (M1–M6 + P1–P44; 2 user overrides flagged).
    - `confirmation_docs/PHASE_MAP.md` §1 — settled cross-cutting decisions.
    - `confirmation_docs/PHASE_MAP.md` §5 Phase 05d row + Phase 05c row — predecessors.
    - `confirmation_docs/PHASE_05d_CONFIRMED.md` `tester_notes` — most recent shipped phase.
    - `confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md` — round-7 reshape precedent.
    - `docs/decisions/adr/0015-instancing-model.md`, `0019-materialisation-is-lazy.md`, `0025-instance-overrides-via-ov-prefix.md`, `0026-composite-overrides-bundle-only.md`, `0132-instancing-moved-to-mindsos-instances.md` — instancing ADR set.
    - `docs/decisions/adr/0014-layer-boundary-core-only.md`, `0017-schema-strictness-opt-in.md` — pointer-line precedent from 05d.
    - `mindsos_core/models/graph.py`, `mindsos_core/models/node.py`, `mindsos_core/models/edge.py`, `mindsos_core/models/metagraph.py` — current Core primitive surfaces (audit confirmed: no instance.py; remove methods present and observer-hook-receptive).
    - `mindsos_core/schema/validation.py` — `RESERVED_PROPERTY_PREFIXES = ("ov__",)` already in place (Phase 04 lock); confirms ov__ reservation for Phase 07 serialization without new Phase 06 work.

  **Risks:**
    - **Cascade-observer attach timing (round-7 P49 B+A rewrite).** Core ships observer plumbing only; `mindsos_instances.attach_registry(mg)` is the caller-facing idempotent helper that constructs + attaches `ElementRegistry(mg)`. If the helper is not called before instances are created, `mg.element_registry` doesn't exist → instance construction fails (registry lookup raises). This is the intended failure mode — no silent registry-bypass possible. CLI `instantiate-*` verbs always call `attach_registry` as their first step.
    - **Recursive cascade depth.** Deeply-nested composites (>1000 levels) could hit Python's recursion limit. Mitigation: cycle detection (P25 A) prevents infinite recursion; nested-depth >100 is implausible per L4/L5 mental-model use cases. Convert to iterative if profile shows depth issues.
    - **Observer-callback exception atomicity (round-7 P65 A).** Each Core `remove_*` method runs `snapshot → mutate → call observers → on exception, restore + re-raise`. Implementation must ensure the snapshot/restore wraps the full remove operation. A bug in the wrap leaves state inconsistent on observer failure.
    - **CLI single-call demo + multi-step library workflows divergence.** Testers exercising CLI may form mental models that don't match library mutation API surface. Mitigation: `docs/concepts/instancing.md` documents both paths explicitly.
    - **JSON-fragment value parsing (P42 A) shell-quoting friction.** Recipe authors must quote string literals (`--override name='"Alicia"'`). Mitigation: examples in row recipes + future feedback memory if it hits twice.
    - **GraphInstance ships empty-scope (but P54 B materialise = full clone).** Audit cleared (P36 A future-work entry); reviewers may flag as "useless class" — but round-7 P54 B locks GraphInstance materialise as a full deep-copy clone, giving the subclass a real Phase 06 use even before Phase 10's property-bag override surface arrives.
    - **Endpoint-resolution walk cost (round-7 P58 A).** `_resolve.resolve_node(metagraph, node_id)` walks `metagraph.graphs.values()` — O(G×N) per resolution. Phase 06 single-call-demo scope absorbs the cost. Phase 07 persistence can add an indexed reverse-map if profile shows hotness.

  **Tests (no budget cap per `feedback_test_budget_unlimited.md`):**

  In-memory only (P8 B); no subprocess/CLI state-round-trip tests; no FalkorDB integration. Projected categories (round-7 P52/P59/P64 adjustments):
  - Subclass construction + invariants (per-subclass override allow-list enforcement per P64 A bifurcation, identity-field-rejection, type_name-rejection, kind constant presence, `_instance_seq` monotonicity per P46 C) — ~45 tests.
  - SubGraphInstance edge-validity invariant (strict pass/fail; structural override re-checks invariant) — ~15 tests.
  - Override mutation (set / clear / repeated set; reserved-key + ov__-prefix rejection in property bucket; structural-bucket bypass per P64 A) — ~25 tests.
  - Materialisation per subclass (type mapping per P6 A; fresh-UUID-per-call; structural fields appear in materialised object; user-property merge; round-7 P58 A endpoint resolution; round-7 P51 A SubGraphInstance copy; round-7 P54 B GraphInstance full clone; CompositeInstance tree per P18 A + P39 A + round-7 P63 A canonicalize-asdict) — ~50 tests.
  - Composite (mutability per P37 A; duplicates allowed; remove_member by occurrence; cycle detection P25 A; cross-metagraph rejection P43 C + round-7 P50 A required-metagraph_id; round-7 P55 A stale-ref rejection; round-7 P61 A bundle_overrides validation with `scope="composite"`) — ~30 tests.
  - Cascade observer (hard-remove on Graph triggers element_registry remove; recursive cascade through composites P44 A; round-7 P56 A mg.identity.unregister; round-7 P59 A SubGraphInstance referenced-element routing; round-7 P65 A atomic-rollback on observer exception) — **~30 tests; teardown/unsubscribe category struck per round-7 P52 A (no such API exists)**.
  - Canonicalize utility (set→sorted-list; recursive nesting; JSON output stability) — ~15 tests.
  - CLI (4 verbs × pass + override + materialise paths; JSON-fragment value parsing P42 A; list→set coercion per P57 A; compose inline JSON specs P41 A; error paths — unknown template ID, cross-metagraph, invalid override; exit-code split per round-7 P53 A) — ~30 tests.

  Projected total: ~240 net-new tests. In-container baseline 05d = 1013 → projected Phase 06 = ~1250 in-container + 2 skipped (continuity).

  Sandbox vs container split: subclass construction + override mutation + canonicalize + materialise structural correctness are sandbox-friendly (no FalkorDB, no subprocess). CLI tests require subprocess and run in-container only.

  **Docs:** `docs/concepts/instancing.md` (new or amended — concept page covering 8 subclasses + override allow-list + composite + cascade); `docs/api/instances/` (new section — per-subclass API reference + ElementRegistry + canonicalize); `docs/usage/core/instances.md` (CLI usage; recipe examples for JSON-fragment quoting); `docs/changelog/CHANGELOG.md` (Phase 06 entry); `mindsos_core/__init__.py:54` stale-reference fix (the only on-disk ADR-ref edit; ADR file edits themselves deferred to Phase 38 per round-7 P45 B).

  **Future-work entries filed (5 total — to be added to `_source_backup/root/mindsos_future_plans.md`):**
    - **(i) GraphInstance override surface** — when Phase 10 ships ADR-0130 (graph property bag), GraphInstance's allow-list amends to include graph-level user properties. Phase 10 row picks up this thread.
    - **(ii) Composite combine helper** — `mindsos_instances.combine_composite_into_graph(...)` (or equivalent) — revisit when L4 ships and the combination contract is concrete. P30 A locked caller-combines for Phase 06.
    - **(iii) Cross-metagraph composite members** — P43 C forbids in Phase 06. Revisit when L4/L5 demonstrates a concrete task-composite spanning multiple metagraphs; likely requires multi-metagraph cascade-observer coordination.
    - **(iv) Soft-delete × cascade-through-composites** — P32 A defers; Phase 10 row picks whether `deprecate_*` triggers partial-cascade (member-removal from composites) or stay-alive (composites preserved with deprecation-marker propagation).
    - **(v) Type-name override permission** — P33 B forbids in Phase 06. Revisit if L4/L5 surfaces a polymorphic-template use case where an instance legitimately needs a different `type_name` than its template.

### Phase 07 — L1 Persistence

  **Status:** Pending (post-design — addendum + design-review supplement folded 2026-05-13; awaiting implementation).
  **Branch:** phase-07
  **Tag on confirm:** phase-07-confirmed
  **Depends on:** 03, 04-v2, 05a, 05b, 05c, 05d, 06 (last in 06 cascade per CASC-1 strict-sequential).
  **Layer(s):** L1.
  **Net-new?:** **Partial.** Slim-port v3 baseline `mindsos_core/persistence/*` + `mindsos_core/reconstruction/graph_loader.py` + `mindsos_core/cypher/builders.py` + sibling-package `mindsos_instances/persistence/instance_repository.py`. NEW CLI subapp `mindsos persistence` (5 verbs). `falkordb` Python driver ALREADY pinned at `>=1.6.1,<2.0` in `requirements.in` (Phase 00 baseline; **no relock needed** per P46 A). NEW reserved-keys-in-FalkorDB convention: `_version: int = 1` field added to 9 dataclasses (Node per P26 A — Phase 03 stripped it; Edge, HyperEdge, MetaEdge, MetaHyperEdge, IntergraphEdge, IntergraphHyperEdge, ElementInstance, CompositeInstance gain it). `_version` ALREADY in `RESERVED_PROPERTY_KEYS` since Phase 04 at `schema/validation.py:54` (P38 A — no validation.py edit). `schema_name` persists as plain Cypher property on `:Metagraph` row using the existing dataclass field (P100 A — no rename, no underscore prefix). NO state-file bump (M0 B locked).

  **Locked decisions (4 meta-pick passes + 3 design rounds — 2026-05-12; addendum P26-P78 + design-review supplement P79-P100 folded 2026-05-13):**

    - **M0** — **Backend-only Phase.** JSON state files unchanged at v=4/v=2/v=1. `mindsos persistence sync --graph X` projects JSON contents → FalkorDB. Existing Phase 02-06 CLI verbs unchanged. JSON authoritative; FalkorDB projection (per ADR-0121).
    - **M1** — Slim-port v3 baseline modules. Each port strips fields/methods out-of-scope for Phase 07 (XRef → Phase 09; metagraph loader + streaming → Phase 08; soft-delete read-filter → Phase 10).
    - **M2** — Single Phase 07 (no 07a/07b split). Test budget per `feedback_test_budget_unlimited.md`.
    - **M3** — Flip ADRs 0122/0123/0126/0127 Proposed → Accepted **inline** with acceptance-criteria amendment per P27 C: *"Accepted when L1 mechanism ships + `core.md` documents it; consumer integration tracked separately."* ADR-0127 §"Repository API" amended per P28 B (L1 bumps always; OCC opt-in via `expected_version`; L0/L2 wraps with `MissingExpectedVersionError`). ADR-0123 DDL block rewritten per P89 A (relationship-index syntax for `:Edge`/`:MetaEdge`/`:IntergraphEdge`; final 14-index list per P95 B). Write `docs/dev/internals/core.md` "Persistence layer" section per P24 B.
    - **M16 (NEW per P37 A)** — Resync prerequisite SATISFIED 2026-05-12 (Phase 06 squash-merged at `557d55a` on `origin/main`; tag `phase-06-confirmed` pushed; `mindsos_instances/` present; `pyproject.toml packages.find` includes `mindsos_instances*`; Dockerfile COPY both stages). Phase 07 branch `phase-07` off post-merge main.
    - **M4** — Open-ended round count (closed at 3 design rounds + 4 meta-passes; pushback well dry per round-3 §4).
    - **M5** — OCC `_version` enforcement wires on `update_*_properties` per ADR-0127; opt-in via `expected_version` parameter (P7 C).
    - **M6** — Minimum scope: 5-bucket `verify_invariants` scanner unchanged from v3 + 3 CLI verbs (`diagnose` / `verify` / `inspect-state`).
    - **M7** — Mechanism only; no Global/Local policy. `expected_version` opt-in per call site.
    - **M8** — Trimmed reading scope.
    - **M9** — **Observer-driven persist** via single `after_persist(mg)` callback on `Metagraph`. Instances persist sibling-side; preserves Phase 06 P49 B Core/instances boundary.
    - **M10** — `tests/phase_07/` existing layout.
    - **M11** — `pytest.mark.integration` tag on FalkorDB-requiring tests; conftest registers marker.
    - **M12** — Bump `confirm-phase` timeout 600s → 900s (per `feedback_confirm_phase_timeout.md`; affects all phases).
    - **M13** — `persistence reset` deferred to Phase 11 entirely; replaced in 07 by `inspect-state` (P13 B rename).
    - **M14** — **Phase 07 strictly graph-scoped.** Ships single-Graph save+load round-trip. Metagraph sync AND metagraph load both deferred to Phase 08 (reverses Round-1 P3 B per P12 D).
    - **M15** — Per-test fresh FalkorDB graph (`test_<uuid_hex8>` naming).
    - **P16-pre** — Ship tombstone-WRITE primitives in 07; soft-delete READ-filter deferred to Phase 10.
    - **P1 C** — 5-verb subapp: `sync` / `load` / `diagnose` / `verify` / `inspect-state`. Bootstrap implicit on Client construction.
    - **P2 A** — Lazy bootstrap on `Client.__init__`; idempotent index creation.
    - **P3 B → P12 D** — `sync` graph-only too (metagraph-sync moves to Phase 08).
    - **P4 A** — Per-command connection lifecycle. Each CLI verb opens, runs, closes the FalkorDB connection.
    - **P5 C → P15 A** — Env-and-manifest hybrid for `FalkorConfig`; password env-only (security).
    - **P6 A** — Direct repository construction (`GraphRepository(client)`); caller manages client lifecycle.
    - **P7 C** — `_version` field always bumps on update; OCC enforcement opt-in via `expected_version` parameter; field-bump is invariant.
    - **P8 A → P9 C** — `_props_json` writer ships for Metagraph (per ADR-0130); skipped for Graph (Graph .properties deferred per PHASE_MAP §7 Q4).
    - **P10 A (amended P26 A)** — `_version: int = 1` field added to all 7 core element types (Node, Edge, HyperEdge, MetaEdge, MetaHyperEdge, IntergraphEdge, IntergraphHyperEdge — including Node per P26 A, which Phase 03 stripped from the slim).
    - **P11 A** — `_version` field on `ElementInstance` + `CompositeInstance` (cross-package — bumps `mindsos_instances` slim-port surface).
    - **P12 D** — Symmetric Phase 07 scope: both `sync` and `load` graph-only.
    - **P13 B** — `inspect-state` verb (renames the original `reset --dry-run`); read-only DB content lister.
    - **P14 A** — 3 distinct verbs (`inspect-state` / `diagnose` / `verify`) — audience clarity over surface savings.
    - **P15 A** — Manifest `[falkordb]` section holds `host` / `port` / `username` / `graph`; password env-only.
    - **P16 A** — Standard lockfile regen via `tools/lock.sh`; tester re-runs once.
    - **P17 C** — `load --graph X` default stdout summary; `--to-json` opt-in overwrites `~/.mindsos/graph-<name>.json`.
    - **P18 D** — `sync --graph X` additive default (MERGE-on-id); `--replace` opt-in performs DETACH DELETE + rewrite.
    - **P19 C** — `verify --source=memory|db`; default `memory`.
    - **P20 B → P41 B → P82 A** — `RaisesOnNthCall` test wrapper at Client surface; N counts whole `run_batch` events; refuses entire batch from statement N+1 (NOT a real mid-batch crash; ADR-0030 sequential-batch semantics make real mid-batch only testable via subprocess-crash fixture deferred to Phase 11). Test renamed to `test_whole_batch_refused`; mid-batch fidelity test deferred (P41 B + P82 A).
    - **P21 A (amended P84 B)** — Port 4 persistence exceptions at L1: `PersistenceError`, `IntegrityCheckError`, `OptimisticConcurrencyConflict`, `OptimisticConcurrencyExhausted`. `MissingExpectedVersionError` ships at L0/L2 with the Global-write policy wrapper (P84 B — exception lives next to its raiser; ADR-0127 §Implementation references amended one line).
    - **P22 C** — Test-side `tests/_shared/graph_equality.py:assert_graphs_equal` helper. Asserts client type at call site; raises loud `TypeError` if InMemoryClient passed (P32 A).
    - **P23 A / P34 / P16 A (amended P46 A)** — `falkordb` ALREADY pinned at `>=1.6.1,<2.0` in `requirements.in`; `requirements.txt` already locked at `==1.6.1` with hashes; manifest `requirements_txt_sha256` already set (not PENDING_LOCK). **No relock action needed.**
    - **P24 B + P29 A** — Single "Persistence layer" section in `docs/dev/internals/core.md` (NEW file + NEW `docs/dev/internals/` directory) with subsections per ADR concept (substrate / WAL / indexes / async / OCC).
    - **P25 A (amended P36 A)** — Eager sentinel-paths additions at row-implementation time; "~14" is approximation (actual ~20 entries; eager-add every new file at impl time).
    - **P50 B (new — WAL surface)** — `WriteAheadLog` ships context-manager API as primary surface: `with wal.entry(operation_id, kind, payload) as e: ...`. Raw `begin()` / `commit()` primitives still accessible for failure-injection tests.
    - **P39 A + P65 A → P80 A → P90 A → P100 A (final form)** — `MetagraphSchema` is NOT persisted as a labeled FalkorDB node. Schema reference encoded as a plain Cypher property `schema_name?` on the `:Metagraph` row, using the existing `mg.schema_name: Optional[str]` dataclass field (set during `attach_schema()` per Phase 05a-d). No `_schema_name` rename; no `RESERVED_PROPERTY_KEYS` edit; no `:MetagraphSchema` label; no `:HAS_SCHEMA` edge. Schema content stays JSON-authoritative.
    - **P49 A + P98 A (verify graph-scoped scanner)** — `verify --source=db --graph G` runs 3 of 5 buckets (`duplicate_ids` restricted to graph labels, `orphan_hyperedges`, `dangling_tombstones`); the 2 Metagraph-context buckets (`cross_graph_edges`, `orphan_metaedges`) report `[skipped — requires --source=memory --metagraph M]`. Sibling helper `verify_invariants_graph(graph) -> PartialIntegrityReport` ships in `mindsos_core/persistence/integrity.py`.
    - **P59 A** — Doctor `--self-test` FalkorDB-ping has 5-cell matrix (no-section / section-ok / refused / auth-fail / malformed) specified in `docs/usage/core/persistence.md`. P75 B collect-then-report posture (do not fail-fast).
    - **P64 A** — `mindsos persistence verify` exit codes: 0 clean, 1 CLI usage error, 2 system error (DB unreachable on `--source=db`), 3 drift. Mirrors Phase 05d split. `sync --replace` with uncommitted WAL refusal returns exit 2 per P91 A.
    - **P66 A** — `test_occ.py` split into `test_occ_unit.py` (InMemoryClient: OCC predicate emit + `_version` bump invariant + exception class shape) + `test_occ_integration.py` (`@pytest.mark.integration`: stale-write raises `OptimisticConcurrencyConflict`).
    - **P68 A + P89 A (Step 0 probes)** — Tester probes against live sidecar BOTH node-label form (`CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.id)`) AND relationship form (`CREATE INDEX IF NOT EXISTS FOR ()-[r:Edge]-() ON (r.id)`). Records support for each. ADR-0123 DDL rewritten to use the correct syntax per label-vs-relationship per ADR-0021.
    - **P85 B (load --to-json sibling path)** — `load --graph X --to-json` writes to `~/.mindsos/graph-<name>.fromdb.json` (NEW sibling path), NEVER overwrites the canonical `graph-<name>.json`. Preserves M0 B JSON authority; enables tester `diff` workflow.
    - **P86 B (Compose env minimal)** — Only `FALKORDB_PASSWORD` added to `docker-compose.yml` env for both services. `FALKORDB_USERNAME` and `FALKORDB_GRAPH` NOT added (FalkorDB-Redis auth has no username; graph is a per-call parameter, not a connection-time env).
    - **P91 A (--replace × WAL refusal)** — `sync --graph G --replace` refuses if uncommitted `:WALEntry` rows reference graph G; raises `PersistenceError` with operator guidance: *"Uncommitted WAL entries reference graph G; resolve or truncate WAL before --replace."* Exit code 2.
    - **P95 B (final index count = 14)** — `bootstrap` creates 14 indexes total: 10 node-label `id` indexes (`:Node`, `:HyperEdge`, `:Graph`, `:Metagraph`, `:MetaHyperEdge`, `:ElementInstance`, `:CompositeInstance`, `:Tombstone`, `:WALEntry`, `:IntergraphHyperEdge`) + 3 relationship-type `id` indexes (`:Edge`, `:MetaEdge`, `:IntergraphEdge`) + 1 hot-path `:Node {graph_id}` (persist-time check per ADR-0123 §2 uses this). Other hot-path indexes deferred to Phase 08.
    - **P96 A (persist + WAL + observer 4-step lock)** — `MetagraphRepository.persist(mg)` lifecycle: (1) Core writes anchors + elements (via `run_batch`); (2) WAL entries stamped `committed=true` (if WAL in use); (3) `after_persist(mg)` observers fire (instances persist sibling-side); (4) method returns. Observer failure leaves Core+WAL consistent; instances must replay via re-run (P33 A: MERGE-idempotent).
    - **P97 B (driver-exception narrow chained catch)** — `_props_json` write at `metagraph_repository.py` wraps in `try / except (redis.exceptions.ResponseError, falkordb.exceptions.FalkorDBError) as e:` and re-raises as `PersistenceError(f"_props_json write failed: {e}") from e`. Step 0 probe records actual driver exception class on oversized property write; pin tuple accordingly. NO size cap policy (per P83 C).
    - **P99 A (inspect-state Rich tables)** — `mindsos persistence inspect-state` uses Rich-formatted tables for human-readable default; `--json` opt-in for machine output. Matches Phase 02-06 list-verb precedent.

  **Features in scope (capability-level — locked):**

    - **`Client` Protocol** (`mindsos_core.persistence.Client`) — sync surface per ADR-0030: `run_query(query, params)` / `run_batch(statements)` / `close()`. No transactions, no async (parallel `AsyncClient` Protocol per ADR-0126).
    - **`FalkorClient`** — concrete sync impl backed by `falkordb` Python driver; lazy driver import; `PersistenceError` on connection failure.
    - **`InMemoryClient`** — call-recorder mock for unit tests. Records statements; doesn't execute Cypher. Used where round-trip fidelity is NOT required.
    - **`AsyncClient` Protocol** + **`ThreadPoolAsyncClient`** wrapper per ADR-0126; ~50 LOC; no current L1 consumer but ships now to prevent downstream layers from inventing their own.
    - **`bootstrap(client)`** — idempotent index creation per ADR-0123 amended (14 indexes per P95 B: 10 node-label `id` + 3 relationship-type `id` + 1 hot-path `:Node {graph_id}`). Fires lazily on first `FalkorClient.__init__` (P2 A); `InMemoryClient` no-ops bootstrap. Step 0 probe per P68 A + P89 A confirms FalkorDB v4.18.3 supports both `CREATE INDEX IF NOT EXISTS` forms.
    - **`GraphRepository`** — `persist(graph, *, metagraph_id=None)` + `update_*_properties(*, expected_version=None)` + `remove_*` tombstone-write primitives (P16-pre).
    - **`MetagraphRepository`** — `persist(metagraph)` orchestrates Core surface (anchor + `_props_json` per ADR-0130 + `schema_name?` plain property per P100 A + contained Graphs + MetaEdges + MetaHyperEdges). Fires `after_persist(mg)` observers per 4-step ordering per P96 A. **Programmatic-only in 07; no CLI verb consumes (P60 A); metagraph CLI sync/load deferred to Phase 08 per M14/P12 D.** `_props_json` write uses narrow chained catch per P97 B (no size cap per P83 C).
    - **`InstanceRepository`** (sibling `mindsos_instances.persistence`) — `persist_element_instance(...)` / `persist_composite_instance(...)`; subscribes via `Metagraph.register_persist_observer` at `attach_registry(mg)` time (extends Phase 06 P49 B idempotent helper).
    - **`WriteAheadLog`** + **`recover()`** + **`register_replayer`** per ADR-0122. Per-Metagraph `:WALEntry` sibling-graph store. Primary surface is context-manager API `with wal.entry(...) as e:` (P50 B); raw `begin()`/`commit()` accessible for failure-injection tests. Mechanism shipped; no L1 consumer (L0/L2 wire replayers later).
    - **OCC mechanism** (`_version` field on every element type + `expected_version` opt-in parameter on `update_*_properties`); raises `OptimisticConcurrencyConflict` on stale write. No Global/Local policy at L1 (M7). `MissingExpectedVersionError` lives at L0/L2 per P84 B.
    - **5-bucket integrity scanner** per ADR-0123: `verify_invariants(mg) -> IntegrityReport` (duplicate_ids / cross_graph_edges / orphan_hyperedges / orphan_metaedges / dangling_tombstones).
    - **Graph-scoped partial scanner** (P98 A): sibling `verify_invariants_graph(graph) -> PartialIntegrityReport` ships in `integrity.py` for `verify --source=db --graph G`. Returns 3 of 5 buckets (`duplicate_ids` restricted to graph labels, `orphan_hyperedges`, `dangling_tombstones`); CLI reports the other 2 as `[skipped — requires --source=memory --metagraph M]`.
    - **Single-Graph load** — `mindsos_core.reconstruction.graph_loader.load_graph(client, graph_id) -> Graph` (M14). Metagraph loader deferred to Phase 08.
    - **CLI `mindsos persistence` subapp (5 verbs):**
        * `sync --graph <NAME> [--replace]` — projects Graph contents JSON → FalkorDB; additive default (P18 D); `--replace` performs DETACH DELETE + rewrite. Refuses `--replace` if uncommitted `:WALEntry` rows reference target graph (P91 A; exit 2).
        * `load --graph <NAME> [--to-json]` — reconstructs Graph from FalkorDB; default stdout summary fixed shape per P52 A (P17 C); `--to-json` writes to **`~/.mindsos/graph-<name>.fromdb.json`** sibling path (P85 B) — NEVER overwrites canonical state file.
        * `diagnose` — connectivity + 14-index presence (per P95 B) + WAL uncommitted count. Read-only.
        * `verify [--metagraph M | --graph G] [--source=memory|db]` — 5-bucket scanner (full per `--source=memory`); 3-bucket partial scanner per P98 A when `--source=db --graph G`. Refuses `--source=db --metagraph M` (Phase 08 territory per P49 A). Source default `memory` (P19 C). Exit codes per P64 A.
        * `inspect-state` — lists current FalkorDB contents (graphs / metagraphs / instance counts); Rich-table default + `--json` opt-in (P99 A). Read-only.
    - **Doctor self-test extension** — when manifest `[falkordb]` section present, doctor pings DB; absence means "FalkorDB not configured" warning (not error). 5-cell error matrix per P59 A; collect-then-report per P75 B.

  **Modules touched (locked):**

    - `mindsos_core/persistence/__init__.py` — **NEW**. Exports Client, FalkorClient, InMemoryClient, QueryResult, AsyncClient, ThreadPoolAsyncClient, bootstrap, DEFAULT_INDEXES, GraphRepository, MetagraphRepository, WriteAheadLog, WALEntry, register_replayer, recover, IntegrityReport, verify_invariants.
    - `mindsos_core/persistence/client.py` — **NEW**. Slim port of v3 (Client Protocol + FalkorClient + InMemoryClient + QueryResult).
    - `mindsos_core/persistence/async_client.py` — **NEW**. Slim port of v3 (~50 LOC; AsyncClient Protocol + ThreadPoolAsyncClient).
    - `mindsos_core/persistence/bootstrap.py` — **NEW**. 14-index `DEFAULT_INDEXES` list per P95 B (10 node-label + 3 relationship + 1 hot-path `:Node {graph_id}`) + idempotent `bootstrap(client)` function. Uses `CREATE INDEX IF NOT EXISTS` per P42 B + P89 A.
    - `mindsos_core/persistence/graph_repository.py` — **NEW**. Slim port of v3; adds `expected_version` parameter on update methods per ADR-0127.
    - `mindsos_core/persistence/metagraph_repository.py` — **NEW**. Slim port of v3; strips direct InstanceRepository call (replaced by `after_persist` observer per M9 + P96 A 4-step ordering); strips XRef call (Phase 09 territory); writes `_props_json` for Metagraph per ADR-0130 (P9 C — skipped for Graph); writes `schema_name?` plain Cypher property per P100 A; `_props_json` write uses narrow chained catch per P97 B.
    - `mindsos_core/persistence/wal.py` — **NEW**. Slim port of v3 (WriteAheadLog + WALEntry + register_replayer + recover); primary surface is `with wal.entry(...) as e:` context-manager per P50 B.
    - `mindsos_core/persistence/integrity.py` — **NEW**. Slim port of v3 5-bucket scanner + sibling `verify_invariants_graph(graph) -> PartialIntegrityReport` per P98 A.
    - `mindsos_core/reconstruction/__init__.py` — **NEW**. Exports `load_graph`.
    - `mindsos_core/reconstruction/graph_loader.py` — **NEW**. Slim port from v3 single-graph reader; decodes `_props_json` on Graph anchor (no-op since P9 C skips writer; defensive read).
    - `mindsos_core/cypher/builders.py` — **NEW**. Slim port of v3 (~200 LOC). Builders take typed dataclasses (P58 B; no raw-dict path): `build_create_metagraph_anchor`, `build_create_graph_anchor`, `build_unwind_create_nodes/edges/hyperedges`, `build_create_tombstone`, `build_update_*_properties`, `build_remove_*`. Cypher rel-type validation per ADR-0021 single-source-of-truth at dataclass level.
    - `mindsos_core/config.py` — **NEW**. `FalkorConfig` dataclass + `from_env()` + `from_manifest()` classmethods (P5 → P15 hybrid; per-field env-then-manifest-then-default precedence per P67 A).
    - **Per-file `_version: int = 1` field additions (P10 A amended P26 A + P79 A actual layout):**
        * `mindsos_core/models/node.py` — Node gains `_version` (Phase 03 stripped; P26 A).
        * `mindsos_core/models/edge.py` — Edge **AND** HyperEdge dataclasses both gain `_version` (HyperEdge lives in `edge.py`, not a separate file).
        * `mindsos_core/models/metagraph.py` — MetaEdge **AND** MetaHyperEdge dataclasses both gain `_version` (both live in `metagraph.py`, not separate files).
        * `mindsos_core/models/intergraph_edge.py` — IntergraphEdge gains `_version`.
        * `mindsos_core/models/intergraph_hyperedge.py` — IntergraphHyperEdge gains `_version`.
    - `mindsos_core/models/metagraph.py` (additional) — adds `register_persist_observer(cb)` + `_persist_observers` list (mirror of Phase 06 `_remove_observers`); `MetagraphRepository.persist` fires per P96 A 4-step ordering. **Does NOT rename `schema_name` field** (P100 A — existing field used as-is).
    - `mindsos_core/exceptions.py` — adds 4 persistence exceptions at L1 per P84 B amendment: `PersistenceError`, `IntegrityCheckError`, `OptimisticConcurrencyConflict`, `OptimisticConcurrencyExhausted`. **`MissingExpectedVersionError` ships at L0/L2** with Global-write policy wrapper (not at L1).
    - **`mindsos_core/schema/validation.py` — NO EDIT** (P38 A + P100 A — `_version` already reserved at line 54; `schema_name` is a dataclass field not a user-bag key, so reserved-key rule does not apply).
    - `mindsos_core/__init__.py` — re-exports persistence symbols; `__version__` bumps to `"0.0.0+phase07"`.
    - `mindsos_instances/persistence/__init__.py` — **NEW**. Exports `InstanceRepository`.
    - `mindsos_instances/persistence/instance_repository.py` — **NEW**. Slim port of v3's instance_repository.
    - `mindsos_instances/registry.py` (existing) — `attach_registry(mg)` extends to register `after_persist` observer (idempotent per Phase 06 P49 B precedent).
    - `mindsos_instances/element_instance.py` + `composite_instance.py` — adds `_version: int = 1` field (P11 A).
    - `mindsos_instances/__init__.py` — `__version__` bumps to `"0.0.0+phase07"`.
    - `mindsos_cli/commands/persistence.py` — **NEW**. Typer subapp; 5 verbs (sync / load / diagnose / verify / inspect-state).
    - `mindsos_cli/commands/doctor.py` — extends `--self-test` with FalkorDB ping when `[falkordb]` manifest section present.
    - `mindsos_cli/commands/confirm_phase.py` — bumps `_CONFIRM_PHASE_TIMEOUT_SECONDS` from 600 → 900 (M12).
    - `mindsos_cli/app.py` — `register_persistence_app` wired.
    - `mindsos_cli/manifest.toml` — `[mindsos] phase = "07"`; `version = "0.0.0+phase07"`. NEW `[falkordb]` section: `host`, `port`, `graph` (NO `username` per P86 B — FalkorDB-Redis auth has no username concept). Password env-only per P15 A.
    - `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase07"`.
    - `mindsos_cli/app.py` — `register_persistence_app` wired; help text bump Phase 05b → Phase 07 (P63 A).
    - `pyproject.toml` — version + description bumped; **`packages.find` already covers `mindsos_instances*`** (P92 strike — Phase 06 backfilled at `557d55a`).
    - `docker-compose.yml` — image tags `mindsos:phase07-prod` / `mindsos:phase07-test`. Compose env adds ONLY `FALKORDB_PASSWORD: "${FALKORDB_PASSWORD:-}"` to both services per P86 B (existing `FALKORDB_HOST` + `FALKORDB_PORT` kept; NO `FALKORDB_USERNAME` / `FALKORDB_GRAPH`).
    - `Dockerfile` — comment lines bumped (Phase 06 → Phase 07). **`COPY mindsos_instances` already present in both stages** (P92 strike — Phase 06 backfilled).
    - **`.github/workflows/phase-ci.yml` — NO EDIT** (P87 A strike — `Bring FalkorDB up` step + healthcheck already present from prior phase; no Phase 07 amendment needed).
    - **`requirements.in` — NO EDIT** (P46 A — `falkordb>=1.6.1,<2.0` already pinned in Phase 00 baseline; `requirements.txt` already locked; manifest sha256 already set).
    - `tests/_shared/sentinel_paths.py` — **~20 entries** added eagerly at impl time (P25 A + P36 A): every new file path. Approximate count; eager-add every file as it lands.
    - `tests/_shared/falkordb_fixture.py` — **NEW**. Per-test fresh-FalkorDB-graph fixture (`test_<uuid_hex8>` naming per M15).
    - `tests/_shared/graph_equality.py` — **NEW**. `assert_graphs_equal(g1, g2)` walker (P22 C).
    - `tests/_shared/raises_on_nth_call.py` — **NEW**. Client wrapper test helper (P20 B).
    - `tests/conftest.py` — registers `pytest.mark.integration` marker.
    - `docs/dev/internals/core.md` — **NEW "Persistence layer" section** with 5 subsections (Substrate / WAL / Indexes / AsyncClient / OCC) per P24 B + M3 A.

  **Persistence layout (FalkorDB-side; backend addition):**

    - **Anchor pattern:** `(:Metagraph {id, name, _props_json, _version, schema_name?})` + `(:Graph {id, name, role, metagraph_id?, _version})` + `(:Tombstone {graph_id, element_id, element_kind, removed_at, removed_by?})` per-(graph, element) per P69 A.
    - **`schema_name` property** (P100 A) — encoded as plain Cypher property on `:Metagraph` row using the existing `mg.schema_name: Optional[str]` dataclass field. NO `:MetagraphSchema` labeled node; NO `:HAS_SCHEMA` edge; NO `_schema_name` rename. Schema content stays JSON-authoritative.
    - **Element labels** (10 node-labels + 3 relationship-types): `:Node` (label), `:HyperEdge`, `:MetaHyperEdge`, `:IntergraphHyperEdge`, `:Graph`, `:Metagraph`, `:ElementInstance`, `:CompositeInstance`, `:Tombstone`, `:WALEntry` are node labels; `:Edge`, `:MetaEdge`, `:IntergraphEdge` are relationship types per ADR-0021. Each row carries `_version: int = 1` (default).
    - **`_props_json` encoding** (ADR-0130): Metagraph `.properties` dict JSON-encoded onto single `_props_json` property on anchor row via `json.dumps(properties, sort_keys=True, ensure_ascii=False, separators=(",", ":"))` per P62 A. **No size cap** (P83 C); narrow chained driver-exception catch maps oversized writes to `PersistenceError` per P97 B. Graph `.properties` writer NOT shipped (P9 C; deferred per PHASE_MAP §7 Q4).
    - **Indexes** (per `bootstrap`; final count 14 per P95 B): 10 node-label `id` indexes + 3 relationship-type `id` indexes + 1 hot-path `:Node {graph_id}` (used by persist-time check per ADR-0123 §2). ADR-0123 DDL block rewritten inline per P89 A. Other hot-path indexes (`graph_id` on additional labels, `metagraph_id`) deferred to Phase 08 when streaming loader drives the scan needs.
    - **WAL sibling graph** (per ADR-0122): `(:WALEntry {operation_id, kind, payload_json, started_at, committed, committed_at, metagraph_id})` with `:IN_METAGRAPH` edge to anchor.
    - **MetagraphRepository.persist 4-step ordering** (P96 A): (1) Core writes anchors + elements via `run_batch`; (2) WAL entries stamped `committed=true` if WAL in use; (3) `after_persist(mg)` observers fire (instances persist sibling-side); (4) method returns. Observer failure leaves Core+WAL consistent; instances must replay via re-run (MERGE-idempotent per P33 A).
    - **JSON state files unchanged** (M0 B). `~/.mindsos/<kind>-<name>.json` at v=4/v=2/v=1 stay; NO bump. New sibling path `~/.mindsos/graph-<name>.fromdb.json` created by `load --to-json` per P85 B; canonical state file never overwritten.

  **Automated tests (location + intent — locked):**

    - `tests/phase_07/` — projected ~100-130 tests:
        * `test_client_inmemory.py` (~5) — call recording; batch sequencing; scripted result return; close idempotent.
        * `test_client_falkor.py` (~8, `@pytest.mark.integration`) — connect / run_query / run_batch / close lifecycle against live FalkorDB; lazy import failure path; bad config error message.
        * `test_async_client.py` (~5) — wraps sync; propagates exceptions; CancelledError propagates from `to_thread`; close awaits.
        * `test_bootstrap.py` (~6, `@pytest.mark.integration`) — idempotent; all 14 indexes present after first call (per P95 B count); second call no-ops; uses `CREATE INDEX IF NOT EXISTS` (P42 B); tests BOTH node-label and relationship-index forms per P89 A.
        * `test_graph_repository_persist.py` (~10, `@pytest.mark.integration`) — anchor + tombstone + UNWIND nodes + UNWIND edges grouped by type + UNWIND hyperedges; round-trip via `load_graph` + `assert_graphs_equal`.
        * `test_graph_repository_update.py` (~8) — `update_*_properties(expected_version=None)` bumps `_version` only; with stale `expected_version` raises `OptimisticConcurrencyConflict`; with correct `expected_version` succeeds + bumps.
        * `test_graph_repository_remove.py` (~5) — tombstone-write primitives; no read-filter applied (Phase 10 ships read-filter); removed-element still appears in subsequent reads.
        * `test_metagraph_repository_persist.py` (~10, `@pytest.mark.integration`) — Metagraph anchor + `_props_json` round-trip via direct FalkorDB query; `schema_name` plain-property round-trip (P100 A); MetaEdge / MetaHyperEdge writes via cypher rel-type validation; programmatic round-trip per P81 C; `after_persist(mg)` observer fires once per persist call per 4-step ordering (P96 A); `_props_json` oversized-write maps to `PersistenceError` via narrow chained catch (P97 B).
        * `test_metagraph_persist_observer.py` (~4) — `register_persist_observer` + `attach_registry` idempotence; instance persistence routes sibling-side via observer; observer exception propagates cleanly.
        * `test_instance_repository.py` (~8, `@pytest.mark.integration`) — port v3 instance persistence tests; ElementInstance + CompositeInstance round-trip; `_version` on each.
        * `test_wal.py` (~14, mixed) — begin / commit / list_uncommitted / gc; replayer registry; `recover()` calls registered replayers; context-manager API `with wal.entry(...) as e:` happy path + exception path (P50 B); **`test_whole_batch_refused`** via `RaisesOnNthCall` (P82 A rename — refuses entire batch from statement N+1; NOT real mid-batch — that's deferred per P41 B).
        * `test_occ_unit.py` (~5) — `_version` default == 1 on every element type; bump invariant on update path; exception class shape; `MissingExpectedVersionError` NOT present at L1 (P84 B — lives at L0/L2).
        * `test_occ_integration.py` (~3, `@pytest.mark.integration`) — stale-write raises `OptimisticConcurrencyConflict` against live FalkorDB.
        * `test_integrity.py` (~10) — 5-bucket scanner: each bucket triggered by a constructed offending fixture; `verify_invariants(mg).summary()` non-empty when issues present; `__bool__` returns True iff issues. Sibling `verify_invariants_graph(graph)` partial-scanner returns 3 of 5 buckets per P98 A.
        * `test_cypher_builders.py` (~10) — port v3 builder tests; cypher rel-type validation (ADR-0021) on edge/metaedge/intergraph; `_props_json` encoding round-trip.
        * `test_cli_persistence_sync.py` (~7, `@pytest.mark.integration`) — `sync --graph X` end-to-end; `--replace` flag DETACH DELETE + rewrite; refuse on missing graph; **refuse `--replace` if uncommitted WAL entries reference graph** per P91 A; metagraph-owned graph refusal if parent metagraph not yet in FalkorDB (P65 A consequence).
        * `test_cli_persistence_load.py` (~5, `@pytest.mark.integration`) — `load --graph X` stdout summary fixed shape per P52 A; `--to-json` writes `~/.mindsos/graph-<name>.fromdb.json` sibling per P85 B; `--to-json --force` overwrite semantics per P71 A; refuse on missing FalkorDB entry; round-trip equality preserved.
        * `test_cli_persistence_diagnose.py` (~3, `@pytest.mark.integration`) — connectivity ok / not ok / 14-index presence (P95 B) / WAL uncommitted count.
        * `test_cli_persistence_verify.py` (~6, mixed) — `--source=memory` runs on JSON-loaded mg with full 5-bucket scanner; `--source=db --graph G` runs 3-bucket partial scanner per P98 A; `--source=db --metagraph M` refused per P49 A; exit codes 0/1/2/3 per P64 A.
        * `test_cli_persistence_inspect_state.py` (~4, `@pytest.mark.integration`) — lists graphs+metagraphs+instance counts; Rich-table default output shape; `--json` opt-in machine output (P99 A).
        * `test_falkor_config.py` (~4) — `from_env()` reads env vars; `from_manifest()` reads `[falkordb]` section; password env-only enforcement (P15 A).
        * `test_doctor_phase07.py` (~5) — image tag regex; manifest `[falkordb]` section validation; FalkorDB ping when section present; 5-cell error matrix per P59 A; collect-then-report posture per P75 B.
        * `test_confirm_phase_timeout.py` (~2) — `_CONFIRM_PHASE_TIMEOUT_SECONDS == 900`; pytest summary parser unchanged.
        * `test_graph_equality_helper.py` (~3) — `assert_graphs_equal` walker (positive + 2 negatives).
        * `test_raises_on_nth_call.py` (~3) — wrapper raises on N-th call; propagates real result before N; close called.
        * `test_lockfile_falkordb_pin.py` (~2) — `requirements.in` already contains `falkordb>=1.6.1,<2.0` (Phase 00 baseline; P46 A — no relock action); manifest `requirements_txt_sha256` matches.
    - **Audit pass (pre-implementation):** Step 0 audit per addendum §4 + supplement P89 A / P97 B probes already executed 2026-05-13 (see commit `<this commit>`). All Phase-00-through-06 state-file literals reviewed; no Phase 07 state-file bump → no expected literal changes (per `feedback_state_version_audit_scope.md`).

  **Confirmation command:**
    `mindsos confirm-phase --phase 07 --notes-file notes-phase-07.md`
    (Init shape: `--init-notes 07` is canonical; backward-compat alias `phase-07`. Manifest stores `[mindsos] phase = "07"`. **Timeout 900s per M12.**)

  **Pass criterion:**

    - Tester can `mindsos persistence sync --graph G` and observe the Graph's nodes/edges/hyperedges in FalkorDB via direct Cypher introspection (`MATCH (n:Node {graph_id: $gid}) RETURN n`).
    - Tester can `mindsos persistence sync --graph G --replace` and observe DETACH DELETE + rewrite (no zombie nodes).
    - Tester can `mindsos persistence load --graph G` and see stdout summary in fixed shape per P52 A; `--to-json` writes `~/.mindsos/graph-G.fromdb.json` sibling per P85 B (canonical file untouched).
    - Tester can `mindsos persistence diagnose` and see connectivity ok + 14 indexes present (per P95 B) + WAL uncommitted count = 0.
    - Tester can `mindsos persistence verify --source=memory` and see full 5-bucket scanner output; `--source=db --graph G` returns 3-bucket partial scanner per P98 A; `--source=db --metagraph M` refused per P49 A.
    - Tester can `mindsos persistence inspect-state` and see Rich-table output of graphs+metagraphs+instance counts (P99 A); `--json` opt-in for machine.
    - `mindsos doctor --self-test` exits 0 including new `[falkordb]` manifest section validation.
    - OCC mechanism verified end-to-end: construct Node → persist → bump `_version` externally → attempt `update_node_properties(expected_version=stale)` → see `OptimisticConcurrencyConflict`.
    - WAL verified: `with wal.entry(...) as e:` happy path commits; `RaisesOnNthCall` causes whole-batch refusal (P82 A); `recover(client, mid)` replays uncommitted entries.
    - All Phase 03 + 04 + 04-v2 + 05a + 05b + 05c + 05d + 06 + 07 tests pass cumulatively in-container.
    - **Cumulative tests pass: ≥ Phase 06 baseline (1127 + 2 skipped) + ~110-140 Phase 07 added; tester records actual count in `PHASE_07_CONFIRMED.md`** (sandbox-projected: ~1237-1267 + 2 skipped; addendum + supplement add ~10-12 tests over original 100-130).

  **Risks / known issues to watch:**

    - **Graph `.properties` writer skip (P9 C) is asymmetric** with Metagraph `.properties`. PHASE_MAP §7 Q4 stays open; when it resolves (Phase 10 likely), Phase 07's `GraphRepository.persist` needs an additive amendment (no state-file impact; just adds `_props_json` to Graph anchor row).
    - **WAL semantics across phase rollbacks (stub Risks line).** A `phase-07-superseded` rollback leaves FalkorDB data + WAL entries in `.mindsos/falkordb-data/`. Phase 06 binary doesn't know about FalkorDB. Recovery: tester wipes `.mindsos/falkordb-data/` on rollback (documented in row §Rollback hazards).
    - **`persistence sync` is additive by default (P18 D).** Removing a node in memory does NOT remove it from FalkorDB unless `--replace`. Documented; tester convention is to use `--replace` after destructive in-memory edits.
    - **`load --to-json` writes to sibling `.fromdb.json` path (P85 B), NOT the canonical file.** Tester explicitly diffs `graph-X.json` vs `graph-X.fromdb.json` to compare states. M0 B JSON authority preserved. NEVER overwrites canonical state file.
    - **`InMemoryClient` records calls; doesn't execute Cypher.** Tests using it assert "right Cypher emitted" but NOT round-trip. Round-trip tests are `@pytest.mark.integration` and require live FalkorDB sidecar.
    - **`expected_version=None` skips OCC enforcement** but `_version` still bumps on every update (P7 C). Downstream layers calling without `expected_version` get last-write-wins semantics — by design at L1; L0/L2 wire enforcement per ADR-0127.
    - **WAL `recover()` is per-Metagraph.** Phase 07 ships `recover(client, metagraph_id)`; server boot path (Phase 18+) iterates over known metagraphs to call recover per-mg.
    - **`falkordb` Python package ALREADY pinned (P46 A).** No `tools/lock.sh` re-run needed; doctor self-test parity check matches current sha256 at row-amendment time.
    - **No advisory locks on state files** (J-02 carry-forward unchanged from 05a). Concurrent CLI invocations still racy on JSON side; FalkorDB OCC mitigates DB-side but doesn't solve JSON-side race.
    - **Round-trip integration tests require live FalkorDB sidecar.** Tester running `docker compose --profile test run --rm mindsos-test pytest tests/phase_07/` MUST have falkordb sidecar reachable; documented in `docs/usage/core/persistence.md`.
    - **`confirm-phase` timeout bump 600 → 900s (M12)** affects ALL phases retroactively; documented in row §Breaking changes. **Recipe requires pre-build: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`** per P93 + `feedback_confirm_phase_timeout.md`.
    - **Cross-package mindsos_instances bump.** P11 A adds `_version` field to `ElementInstance` + `CompositeInstance`; Phase 06 P62 A 3-package version-string parity check verifies the bump landed in all three packages.
    - **MetagraphRepository.persist observer partial-write hole** (P33 A). Observer (step 3 of 4-step ordering per P96 A) may fail after Core+WAL commit (steps 1-2); instances missing. Retry idempotent via MERGE; tester convention: re-run persist on observer failure.
    - **`sync --replace` leaves dangling MetaEdge/IntergraphEdge refs** outside target graph (P40 A). Surfaced by `verify` as `orphan_metaedges`. By design — scope is graph-scoped DETACH DELETE.
    - **`verify --source=memory` and `--source=db` are different snapshots** (P72 A). Memory-side may drift from FalkorDB after writes; both reports may differ. Drift detection is Phase 08+ future-work.
    - **Graph sync ordering** (P65 A consequence): refuses if graph is metagraph-owned AND parent metagraph not yet persisted in FalkorDB. Tester runs metagraph persist (programmatic only in 07) first OR uses `--source=memory` for verification.
    - **`verify --source=db --graph G` runs 3 of 5 buckets only** (P98 A). `cross_graph_edges` + `orphan_metaedges` require Metagraph reconstruction (Phase 08); reported as `[skipped]`.
    - **`_props_json` write has no size cap** (P83 C). Driver exception on oversized property is mapped to `PersistenceError` via narrow chained catch per P97 B. Step 0 probe pins the driver exception class.
    - **`MissingExpectedVersionError` lives at L0/L2** (P84 B). L1 ships only the 4 exceptions consumers raise at L1; the Global-policy exception ships with its raiser at L0/L2.
    - **WAL test wrapper does NOT exercise real mid-batch crash** (P82 A). `test_whole_batch_refused` exercises whole-batch atomicity; mid-batch fidelity test deferred to Phase 11 (subprocess-crash fixture).

  **Rollback hazards (documented; `--force` reset deferred to Phase 11):**

    1. FalkorDB data persists in `.mindsos/falkordb-data/` after rollback. Phase 06 binary ignores it.
    2. `requirements.txt` includes `falkordb` post-Phase 07; Phase 06 lockfile doesn't. Manual revert via `tools/lock.sh` on phase-06-confirmed checkout.
    3. FalkorDB indexes survive rollback (no clean DROP path in FalkorDB).
    4. WAL `:WALEntry` entries persist on disk.
    5. JSON state files unchanged (per M0 B) — no migration ambiguity.
    **Recovery recipe (Mac):** `docker compose down -v` + `rm -rf .mindsos/falkordb-data/` + `git checkout phase-06-confirmed` + `pip install --user -e . --force-reinstall --no-deps --break-system-packages` (P35 A) + `docker compose build`. Lockfile re-run NOT needed since `falkordb` was already pinned pre-Phase-07 (P46 A); `requirements.txt` unchanged across the rollback boundary.

  **Doc sections this phase confirms:**

    - `docs/usage/core/persistence.md` — full (NEW). Covers all 5 CLI verbs + sync semantics + load semantics + diagnose / verify / inspect-state output shapes + WAL operator concepts + OCC retry pattern + integration with `mindsos doctor --self-test` + rollback recipe. `last_confirmed_phase: 07`.
    - `docs/dev/internals/core.md` — **NEW "Persistence layer" section** with 5 subsections per P24 B (Substrate / WAL / Indexes / AsyncClient / OCC). Cross-references ADRs 0030 / 0121-0127. `last_confirmed_phase: 07`.
    - `docs/api/core/client.md` — full (NEW). Client + AsyncClient Protocol API. `last_confirmed_phase: 07`.
    - `docs/api/core/repositories.md` — full (NEW). GraphRepository + MetagraphRepository + InstanceRepository API. Includes `_props_json` encoding spec inline (P62 A) and driver-exception narrow chained catch spec per P97 B. `last_confirmed_phase: 07`.
    - `docs/api/core/wal.md` — full (NEW). WriteAheadLog + replayer registry API. `last_confirmed_phase: 07`.
    - `docs/api/core/integrity.md` — full (NEW). 5-bucket scanner + `verify_invariants(mg)` + sibling `verify_invariants_graph(graph) -> PartialIntegrityReport` per P98 A. `last_confirmed_phase: 07`.
    - `docs/usage/core/persistence.md` — additionally documents 5-cell doctor self-test matrix per P59 A.
    - `docs/dev/repo-layout.md` — adds one-line clarification that ADRs live at project-root `docs/decisions/adr/` (not halvim_mindsos) per P30 A.
    - `docs/changelog/CHANGELOG.md` — Phase 07 entry appended.
    - **ADR-0030** confirmed (already Accepted; no flip needed).
    - **ADR-0121** confirmed (substrate commitment validated by impl).
    - **ADR-0122** Proposed → **Accepted** (M3 A inline flip; acceptance-criteria amended per P27 C: *"Accepted when L1 mechanism ships + `core.md` documents it; consumer integration tracked separately"*; ADR file edit lands in 07).
    - **ADR-0123** Proposed → **Accepted** (DDL block rewritten per P89 A + P95 B: 10 node-label `id` indexes + 3 relationship-type `id` indexes + 1 hot-path `:Node {graph_id}` = 14 total; acceptance-criteria amended per P27 C; ADR file edit lands in 07).
    - **ADR-0126** Proposed → **Accepted** (AsyncClient ships; ADR file edit lands in 07).
    - **ADR-0127** Proposed → **Accepted** (OCC mechanism ships at L1; §"Repository API" amended per P28 B: *"L1 mechanism: bump always; OCC check opt-in via `expected_version`; L0/L2 wraps with policy that raises `MissingExpectedVersionError` for Globals"*; §Implementation references amended per P84 B: `MissingExpectedVersionError` ships at L0/L2 not L1; acceptance-criteria amended per P27 C; ADR file edit lands in 07).
    - **ADR-0124** (streaming loader) stays Proposed; consumer in Phase 08.
    - **ADR-0125** (lazy local hydration) stays Proposed; consumer at L0+.

  **Breaking changes from Phase 06:**

    - **`_version` already in `RESERVED_PROPERTY_KEYS`** since Phase 04 (P38 A); no Phase 07 reservation edit. User properties named `_version` were rejected since Phase 04; Phase 07 is the first to actively persist `_version` on FalkorDB rows.
    - **`confirm-phase` default timeout 600s → 900s** (M12). Affects all phases retroactively; prior phase tests unaffected (well under 600s); only matters if a future phase brushes 900s.
    - **NEW `[falkordb]` manifest section** (`host` / `port` / `graph`; NO `username` per P86 B). `doctor --self-test` validates presence; absence is a warning, not a fail.
    - **NEW CLI top-level subapp `mindsos persistence`** (5 verbs).
    - **`mindsos doctor --self-test` extended** to ping FalkorDB when `[falkordb]` section present; 5-cell error matrix per P59 A; collect-then-report per P75 B.
    - **`_version: int = 1` field added to 9 dataclasses** (7 core: Node, Edge, HyperEdge, MetaEdge, MetaHyperEdge, IntergraphEdge, IntergraphHyperEdge — including Node per P26 A; + 2 instance: ElementInstance, CompositeInstance). Constructor signatures unchanged (default value).
    - **NEW Cypher property on `:Metagraph` row**: `schema_name?` (plain property using existing `mg.schema_name` field per P100 A; NO `_schema_name` rename, NO RESERVED_PROPERTY_KEYS edit).
    - **NEW Compose env var `FALKORDB_PASSWORD`** added to both services (P86 B); `_USERNAME` and `_GRAPH` env vars NOT added (FalkorDB-Redis auth has no username; graph is per-call).
    - **`falkordb` Python driver: ALREADY pinned** (P46 A). No `requirements.in`/`.txt` change; no `tools/lock.sh` re-run; no manifest sha256 bump.

  **Final amendments (2026-05-12 — locked across 4 meta-pick passes + 3 design rounds):**

    1. **M0** — Backend-only Phase; JSON unchanged.
    2. **M1** — Slim-port v3 baseline + `cypher/builders.py` per P15 (round-2).
    3. **M2** — Single Phase 07.
    4. **M3** — Flip ADRs 0122/0123/0126/0127 inline; write `core.md` per P24.
    5. **M4** — Open-ended round count (closed at 3).
    6. **M5** — OCC wires in 07.
    7. **M6** — Minimum verify+diagnose+inspect-state scope.
    8. **M7** — Mechanism only.
    9. **M8** — Trimmed reading.
    10. **M9** — `after_persist(mg)` observer-driven persist for instances.
    11. **M10** — `tests/phase_07/`.
    12. **M11** — `pytest.mark.integration` marker.
    13. **M12** — Bump `confirm-phase` timeout 600 → 900s.
    14. **M13** — `reset --force` deferred to Phase 11; replaced by `inspect-state` (P13).
    15. **M14** — Phase 07 strictly graph-scoped (reverses Round-1 P3 B per P12 D).
    16. **M15** — Per-test fresh FalkorDB graph naming `test_<uuid_hex8>`.
    17. **P16-pre** — Tombstone-write in 07; read-filter Phase 10.
    18. **P9 C** — Graph .properties writer skipped (Q4 deferral); Metagraph .properties shipped.
    19. **P10 A** — `_version` on all 6 core element types.
    20. **P11 A** — `_version` on 2 instance types (mindsos_instances cross-package).
    21. **P12 D** — REVERSES Round-1 P3 B; symmetric sync+load graph-only.
    22. **P13 B** — `inspect-state` verb (rename of `reset --dry-run`).
    23. **P14 A** — 3 distinct verbs.
    24. **P15 A** — Manifest `[falkordb]` no password.
    25. **P16 A** — Standard lockfile regen.
    26. **P17 C** — `load` stdout default; `--to-json` opt-in.
    27. **P18 D** — `sync` additive default; `--replace` opt-in.
    28. **P19 C** — `verify --source=memory|db`; default memory.
    29. **P20 B** — `RaisesOnNthCall` test wrapper.
    30. **P21 A** — 5 persistence exceptions ported.
    31. **P22 C** — Test-side `assert_graphs_equal` helper.
    32. **P23 A** — Latest `falkordb`; tester relocks.
    33. **P24 B** — Single "Persistence layer" section in `core.md`.
    34. **P25 A** — Eager 14 sentinel-paths additions.
    35. Pre-implementation audit: every `tests/phase_*/test_state*.py` reviewed; no Phase 07 state-file bump.
    36. Image tags `mindsos:phase07-prod` / `mindsos:phase07-test`. Doctor `_COMPOSE_IMAGE_RE` already accepts `phase\d{2}` shape from 05a; no regex extension needed.
    37. `requirements.{in,txt}` adds `falkordb`. `pyproject.toml` package wildcards already cover new files.
    38. **No carry-forward closure** — PHASE_MAP §7 Q4 (Graph .properties) stays open per P9 C.
    39. **Phase 06 GitHub Release body unchanged**; tarball asset survives in 5-phase retention window.
    40. `confirmation_docs/PHASE_06_CONFIRMED.md` stays untouched; 07 ships sibling `PHASE_07_CONFIRMED.md`.
    41. `mkdocs.yml` nav: adds entries for new pages (`docs/usage/core/persistence.md`, `docs/api/core/client.md`, `docs/api/core/repositories.md`, `docs/api/core/wal.md`, `docs/api/core/integrity.md`); amends `docs/dev/internals/core.md`.
    42. `confirmation_docs/_template.md` and `_template_notes.md` unchanged.
    43. **Cross-package version-string parity** (Phase 06 P62 A): bumps `mindsos_cli` + `mindsos_core` + `mindsos_instances` all to `0.0.0+phase07`.
    44. **WAL recovery is per-Metagraph.** Server boot path (Phase 18+) iterates over known metagraphs calling `recover(client, mg_id)` per-mg.
    45. **ADR file edits in 07 override Phase 06 P45 B precedent** for the 4 specific ADRs (0122/0123/0126/0127). User instruction 2026-05-12: "ADR decisions can be changed if decided in this chat." Status: Proposed → Accepted; semantic edits (if any surface during impl) stay deferred to Phase 38.
    46. **`mindsos persistence` verb naming locked** (P1 C); no bikeshedding in implementation chat (`sync` not `push`/`project`/`materialize`).
    47. **Round-6 addendum applied** (53 pushbacks P26-P78 — `confirmation_docs/PHASE_07_ROUND_6_ADDENDUM.md` §2 ledger; row-amendments §3 applied 2026-05-13).
    48. **Design-review supplement applied** (P79-P100 — 22 pushbacks across 4 review passes 2026-05-12/13; this chat). Picks folded into row text.
    49. **M16 (Resync prerequisite)** — Phase 06 SHIPPED 2026-05-12 via recovery sweep; `phase-06-confirmed` tag on main; `phase-07` branched post-merge. Step 0 audit confirmed 2026-05-13.
    50. **ADR-0122/0123/0126/0127 acceptance-criteria** amended per P27 C (consumer integration tracked separately).
    51. **ADR-0127 §Repository API** amended per P28 B; **§Implementation references** amended per P84 B (`MissingExpectedVersionError` at L0/L2, not L1).
    52. **ADR-0123 DDL block** rewritten per P89 A (relationship-index syntax for `:Edge`/`:MetaEdge`/`:IntergraphEdge`); final 14-index list per P95 B.
    53. **`schema_name` persistence** uses existing dataclass field per P100 A; supersedes earlier P39 A/P65 A/P80 A/P90 A/P94 A forms. No `:MetagraphSchema` labeled node, no `_schema_name` rename, no `:HAS_SCHEMA` edge, no RESERVED_PROPERTY_KEYS edit.
    54. **`MissingExpectedVersionError` lives at L0/L2** per P84 B (not L1).
    55. **`load --to-json` writes to `~/.mindsos/graph-<name>.fromdb.json` sibling path** per P85 B (canonical state file never overwritten).
    56. **Compose env adds ONLY `FALKORDB_PASSWORD`** per P86 B (no `_USERNAME`, no `_GRAPH`).
    57. **CI workflow phase-ci.yml already boots FalkorDB sidecar** (P87 A — strike from §Modules touched).
    58. **`pyproject.toml packages.find` + `Dockerfile COPY mindsos_instances` already in place** from Phase 06 backfill (P92 — strike both from §Modules touched).
    59. **Recipe pre-build step** `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase` per P93 + `feedback_confirm_phase_timeout.md`.
    60. **Bootstrap 14 indexes total** per P95 B (10 node + 3 rel + 1 hot-path `:Node {graph_id}`); other hot-path indexes deferred to Phase 08.
    61. **MetagraphRepository.persist 4-step lifecycle** locked per P96 A (Core → WAL commit → observer → return).
    62. **`_props_json` narrow chained driver-exception catch** per P97 B (no size cap per P83 C; Step 0 probe pins exception tuple).
    63. **`verify --source=db --graph G` runs partial 3-bucket scanner** via sibling `verify_invariants_graph(graph)` per P98 A.
    64. **`inspect-state` Rich tables default + `--json` opt-in** per P99 A.
    65. **WAL test renamed** `test_mid_batch_crash` → `test_whole_batch_refused` per P82 A; mid-batch fidelity deferred to Phase 11 subprocess-crash fixture.
    66. **Step 0 audit performed 2026-05-13** — file-based items in this commit's chat; live-sidecar probes (P89 A node/rel index forms; P97 B driver-exception class on oversized write) deferred to tester recipe execution.
    67. **Test budget projection updated** ~110-140 added tests (was ~100-130); per `feedback_test_budget_unlimited.md` no cap applies.

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
| `docs/usage/core/metagraph-schema.md` | 05b (+ 05c amend for `IntergraphHyperEdgeType`; + 05d amend for `MetaEdgeType` / `MetaHyperEdgeType`) |
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
| 0014–0024 (L1 originals) | **0014 in 03** (amended in 05b for IntergraphEdge primitive — text in 05b row appendix; second amendment in 05c for IntergraphHyperEdge primitive — text in 05c row appendix §C; third amendment in 05d for MetaEdgeType + MetaHyperEdgeType vocab — text in 05d row appendix when authored; all file edits Phase 38); 0015 / 0019 / 0025 / 0026 in 06; 0016 in 09 (XRef supersession noted); **0017 in 04 + amended in 05d** (extended to metagraph-scoped MetaEdgeType / MetaHyperEdgeType; file edit Phase 38); 0018 in 07; **0020 confirmed in 05a** (amendment text drafted; file edit Phase 38); 0021 in 03 + 11; 0022 / 0023 in 07; 0024 in 10 |
| 0027–0037 | 0027 / 0028 in 10; **0029 Superseded by 0130 in 05a** (annotation text in 05a row appendix; file edit Phase 38); 0030 in 07; 0031 / 0032 in 08; 0033 in 10; 0034 in 09; 0035 in 02; 0036 in 07; 0037 in 06 |
| 0038–0057 (L2) | 0038–0042 in 25; 0043 in 14; 0044 in 14; 0045 / 0047 in 12; 0046 in 18; 0048 in 14; 0049–0056 in 16; 0057 in 13 |
| 0060–0100 (L3) | 0060 / 0084 in 27 + 28; 0061 / 0064 / 0065 / 0085 in 28; 0062 / 0063 / 0066 in 27; 0067 in 12; 0068–0070 / 0086 / 0092 in 29; 0071 / 0072 / 0074 in 30; 0073 / 0088 / 0100 in 31; 0075 / 0076 in 28; 0077–0081 in 25 (cross with 28); 0082 / 0083 / 0094 / 0095 / 0096 / 0097 — L4 implications **out of scope**; only the L3 surface they imply ships; 0091 / 0098 / 0099 in 31; 0093 in 27 |
| **0117** | **Reserved through 05a; Withdrawn in 05b** (originally graph-level CompositionalMetaEdge; concept moves to `compositional: bool` flag on `IntergraphEdge` / `IntergraphHyperEdge` per ADR-0148; canonical at `INTERGRAPH_EDGES_DESIGN.md`) |
| 0118 | 24 |
| 0121–0137 (L1 redesign) | 0121 in 07; 0122 in 07; 0123 in 07 + 11; 0124 in 08; 0125 in 08; 0126 in 07; 0127 in 07; 0128 in 09; 0129 in 10; **0130 Accepted in 05a** (Metagraph property bag shipped per N1-A1; Graph property bag deferred to Phase 10); 0131 in 02; 0132 in 06; 0133 in 10; 0134 in 11; 0135 in 10; 0136 in 18; 0137 in 23 + 24 |
| 0138–0144 (L2 closure) | 0138 in 14 (verify removed); 0139 in **36 — NEW CODE**; 0140 in 36 (constraints on writes); 0141 in 14; 0142 in 09; 0143 in 34; 0144 in **37 — NEW CODE** |
| 0145–0147 (L3 write side) | 0145 in **33 — NEW CODE**; 0146 in **34 — NEW CODE**; 0147 in **35 — NEW CODE** |
| **0148 (NEW; intergraph edge family)** | **drafted + Accepted in 05b** (`IntergraphEdge` binary + compositional flag — text in 05b row appendix §B); **amended in 05c** (`IntergraphHyperEdge` n-ary + `ordered: bool` semantic + compositional+ordered=False refusal — text in 05c row appendix §B). Canonical spec at `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`. ADR file edit Phase 38 per locked precedent. |

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
