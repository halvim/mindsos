# DREAM PRE-0 Slice 3 — open-tolerant Episode reader (CONFIRMED)

**Status:** SHIPPED 2026-07-30 (merged-state Linux gate 4421 passed / 12 skip / 1 xpass / 0 failed;
tag dream-pre0-slice3-confirmed). Branch `feat/dream-pre0-slice3` off main @ `01e4d0d`.
Model: project memory `dream-episode-model.md`.

## What
The FIRST reader over the streaming Episode (Slice 1b lifecycle + Slice 2 streamed grounding).
`episode_reader.read_episode(kl, client, *, episode_id, user_id) -> EpisodeView | None` loads the
Episode node from the live Local and resolves its grounding whether the request closed normally or
crashed, tolerating open / incomplete / partial episodes.

## Grounding finding that shaped it
`load_graph(client, graph_id)` is graph-scoped (cross-session by id), so a CLOSED episode reads back
via its stored refs. But a CRASHED episode has NULL grounding refs (D2-A never wrote them mid-stream),
and after a restart the writing session's `metagraph_id` is gone — and there was **no cross-metagraph
"find graphs by role" query** in core. So a crashed request's streamed grounding was durable but
unfindable. That findability IS Slice 2's crash payoff; Slice 3 supplies the lookup.

## Decisions (w/ HA)
- **S3-1 = C.** New core `graph_anchors_by_role(client, role_prefix=, name_suffix=)`
  (`MATCH (g:Graph) WHERE g.role STARTS WITH $p [AND g.name ENDS WITH $s]`) — locates graphs by their
  deterministic role/name when the metagraph_id is unknown. (`:Graph` carries id/name/role.)
- **S3-2 = reader-side fallback (NOT boot backfill).** Grounding revealed backfill needs a boot-time
  index rebuild + persister wiring, and the reader must tolerate partial anyway; doing the lookup in
  the reader is strictly less machinery and leaves `crash_recovery` UNCHANGED (lower risk).

## Reader behavior
- **chain (plan/task tree):** `mm_root_ref` when set, else by name (`chain:` role + name ENDS WITH
  `:{episode_id}`).
- **capacity run graphs:** the capacity index at `capacity_root_ref` when set, else by role prefix
  `capacity:run:{episode_id}:`. Latest replan attempt wins (best-effort dedup by ref-path position —
  strips trailing `-{run_attempt}[-r{retry}]`).
- Any missing/unloadable graph is skipped and `partial=True` (never raises). `client=None` -> node +
  props only (`partial=True`).

## Changes
- `mindsos_core/reconstruction/graph_loader.py` — `graph_anchors_by_role`; exported from `__init__`.
- `mindsos_intelligence/episode_reader.py` (NEW) — `EpisodeView` + `read_episode` + dedup helpers.
- `crash_recovery.py` — UNCHANGED (S3-2).

## Tests (tests/phase_48/test_episode_reader.py)
- Unit (no Falkor): prop parsing + `partial` (client=None), absent -> None, `_latest_by_position`
  keeps highest attempt, `_attempt_key` position-stable across replan attempts.
- Integration (live Falkor): a crashed episode (null refs) locates its chain (by name) + 2 run graphs
  (by role) — `partial=False`; a closed episode resolves the same via stored refs.

## Deferred
- Efficient index-scoped querying (avoid whole-graph scans / naive load) = **PRE-3**.
- `knowledge_mm` grounding = **PRE-6**.
- Full nested attempt/retry dedup beyond best-effort (consumer / PRE-3 concern).
