---
last_confirmed_phase: 07
verified_at: 5172b3c
---

# Repo layout

The repository contains (root listing, 2026-09-20):

```
.
├── .github/workflows/    # phase-ci.yml (gates main + PRs), release.yml (tag-driven).
├── confirmation_docs/    # PHASE_MAP.md, per-phase confirmation docs, live plans.
├── docs/                 # mkdocs source tree, including docs/decisions/ (ADRs).
├── projects/             # sister projects and lanes (not copied into the test image).
├── scripts/              # dataset fetchers.
├── tools/                # helper scripts and checkers (lock.sh, check_*.py, claim_inventory.py).
├── tests/                # the suite: tests/phase_NN/, tests/unit/, tests/architecture/, ...
├── tests_server/         # separate top-level server suite (legacy layout).
├── mindsos_core/         # L1 Core — graphs, metagraphs, identity, persistence.
├── mindsos_instances/    # instancing vocabulary (ADR-0132).
├── mindsos_knowledge/    # L2 Knowledge — IRIs, REF_TYPES, one schema builder per named role.
├── mindsos_capacity/     # L3 Capacity.
├── mindsos_intelligence/ # L4 Intelligence.
├── mindsos_llm/          # the LLM seam (top-level; see docs/plans/MINDSOS_LLM_PLAN.md).
├── mindsos_admin/        # admin surfaces (promotion, importers).
├── mindsos_broker/       # broker package.
├── mindsos_server/       # Server layer — auth, sessions, audit, lifecycle (ADR-0010: orthogonal).
├── mindsos_cli/          # CLI package (Typer), with manifest.toml and commands/.
├── STATE.json            # current state + the recent[] ship log.
├── RULES.md              # the lane rules (NOT copied into the test image).
├── HANDOFF.md            # canonical entry point for a fresh chat.
├── CLAUDE.md             # project instructions.
├── BRANCHES.md           # branch inventory.
├── Dockerfile            # multi-stage: base / prod / test.
├── docker-compose.yml    # stack: falkordb + mindsos + mindsos-test (profiles: cli, test).
├── entrypoint.sh         # container entrypoint.
├── mkdocs.yml            # mkdocs config.
├── pyproject.toml        # package definition.
└── requirements*.in/.txt # hand-edited inputs and their locked outputs (tools/lock.sh).
```

The per-file listing this section once carried (schema builders, individual
command modules) is not reproduced: it rots on every ship, and `ls` answers
it exactly.

## Adding a package

Later phases bring additional packages online inside this same repo:

| Package              | Phase that introduces it          |
|----------------------|-----------------------------------|
| `mindsos_core`       | Phases 02–11 (L1)                 |
| `mindsos_instances`  | Phase 06 (per ADR-0132)           |
| `mindsos_knowledge`  | Phases 12–17 (L2)                 |
| `mindsos_server`     | Phases 18–25 (L0)                 |
| `mindsos_capacity`   | Phases 27–35 (L3)                 |
| `mindsos_intelligence` | Phases 46–47 (L4)               |
| `mindsos_admin`      | admin surfaces (promotion, importers) |
| `mindsos_llm`        | the LLM seam — scope lives in `docs/plans/MINDSOS_LLM_PLAN.md` |
| `mindsos_broker`     | broker package                    |

Each phase keeps its scope tight to the row in
`confirmation_docs/PHASE_MAP.md`. Cross-cutting decisions live in §1 of that
file; per-phase implementation notes live in `confirmation_docs/PHASE_NN_CONFIRMED.md`.

## ADR locations

**ADRs live in this repo**, at `docs/decisions/adr/`, one file per decision,
with `docs/decisions/adr/README.md` as the full index and
`docs/decisions/summary/*.md` as the per-layer partial tables.
`tools/check_adr_status_consistency.py` (run by
`tests/test_adr_status_consistency.py`) asserts an ADR's front-matter status,
its prose `**Status:**` line, its README row and any summary cell all agree.
RULES §9 states the four edits a status change needs, and that an in-file
amendment uses `**Amendment status:**` so it does not shadow the ADR's own.

The "Model C hybrid" this section used to describe — ADRs kept outside the
repo, at a project-root path, tracked by the filesystem rather than by git —
is retired; nothing in the tree reads that layout any more.
