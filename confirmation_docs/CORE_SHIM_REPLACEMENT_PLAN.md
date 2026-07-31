# Core shim replacement plan

**Filed:** 2026-07-30. **Verified at:** `origin/main` `01e4d0d`.
**Rule:** a shim may exist only while (a) we know what it stands in for and (b) a
real MindsOS piece is named to replace it. Anything failing either test is a defect,
not a shim.

---

## 1. The register

| # | Shim | Where | What it stands in for | Replacement | Blocked on |
|---|---|---|---|---|---|
| S1 | `find_pipeline` | `mindsos_capacity/pipeline.py:479` | the old singular `start_datastate=` keyword; 7 call sites | the **path-finding capacity** (Plan → Pipeline as a dispatched L4-family capacity) | S2 |
| S2 | `BFSFinder` | `pipeline.py:257` | a search method that cannot wire >1 input | a **selection policy** on the sound walk | producer-choice seam |
| S3 | `mindsos_server/pipeline_runner.py` | L0 | running a Pipeline from the REPL | L4's `pipeline_execution.execute_pipeline` | layering (L0 must not drive L4) |
| S4 | `phase1_v0` (4 caps) | `mindsos_capacity/builtins/` | real interpretation | real catalogs — `CORE_CR_REAL_L4_CATALOGS.md` §5.3, §5.6 | design decision D-2 |
| S5 | `planning_v0` (4 caps) | same | real planning / decomposition | same CR, slice 1 | — |
| S6 | `orchestration_v0` (5 caps) | same | real replan / sufficiency / scoring / blame | same CR, slices 2, 4, 5 | — |
| S7 | `DuckSession` ×3 | brain-side (nilm, arc1, bongard) | a minimal Local session | a **core** session primitive | none — buildable now |
| S8 | `mindsos_capacity/types.py` | L3 | a deprecation shim, self-described as dead code | delete | verify zero importers |
| S9 | `Session.for_testing` | `mindsos_server/session.py` | test-only Session construction | fold into S7 | S7 |
| S10 | `signal_triage` passthrough | `mindsos_intelligence/signal_triage.py` | real triage | `decision.signal_to_tier` (S6) — partly superseded already | S6 |
| S11 | `submind` stub resolver | `submind_registry.py` | a real resolver | the submind arbiter work | separate lane |
| S12 | `metagraph_snapshot` helper | `mindsos_core` | narrowed by ADR-0129 | keep — scoped, documented | n/a |

**Not shims** (checked and cleared): `bootstrap.py` helpers in each layer,
`_argon2` / `_db` in L0, `_replparse`, `identifiers` helpers, `_resolve`,
`registry.attach`. These are ordinary internal utilities with no missing counterpart.

---

## 2. Order, and why

**Wave A — no dependencies, buildable now.**
- **S7** core session primitive. Removes three brain-side copies and unblocks S9.
  Smallest change with the widest reach.
- **S8** delete `types.py` after confirming zero importers. Pure removal.

**Wave B — the finder lane (this chat's original scope).**
- fix the self-feeding-producer defect (prerequisite for anything routing through
  the sound walk)
- open the **producer-choice seam** — one hook that serves alternatives-recording,
  strategy selection, and dream PRE-5
- **S2** BFS becomes a policy on that seam
- **S1** `find_pipeline` dies behind the path-finding capacity
- then: taught-pipeline lookup as a second producer of the same DataState

**Wave C — the catalogs.** S5 → S6 → S4, per `CORE_CR_REAL_L4_CATALOGS.md` §5.
This is what unblocks both brains.

**Wave D — cleanup after C.**
- **S3** REPL moves to `execute_pipeline`; `pipeline_runner.py` deletes
- **S9**, **S10** fold into their replacements
- **S11** on its own lane

---

## 3. Rules for the register

1. **A shim with no named replacement is a defect.** File it as a CR or delete it.
2. **A shim's docstring names its replacement CR** — not a subsystem, not a phase.
   (See `WSD_IS_A_CONSUMER.md`.)
3. **Deleting a shim is its own commit**, separate from building the replacement,
   so a gate failure is attributable.
4. **This register lives in the repo and is updated on every ship**, like
   `STATE.json`. A shim removed silently is a shim nobody learns from.
