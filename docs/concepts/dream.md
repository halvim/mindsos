# Dreaming (Phase 45)

Dreaming is MindsOS's corpus-replay mechanism. It re-runs past episodes so
the system can regression-check itself, detect drift against newer knowledge,
and retry past failures — all feeding the **same** ALS learning pipeline that
live execution uses. There is no separate "dream-learning" track
(Chat B D-B5, *dream-as-live*).

Phase 45 (Rail D) ships the **L3 contract** — three dream capacities and
their execution-policy declarations. The machinery that actually loads an
episode, deep-copies its mental model, re-executes it, and fires ALS signals
lives in the L4 substrate (Phase 46) and the L5 dream-pipeline hookup
(Phase 48). See [ADR-0162](../decisions/adr/0162-l3-dream-family.md).

## The three v1 dream pipelines

| Capacity | Execution policy | What it does |
|---|---|---|
| `dream.maintenance` | `replay_recorded` | Replays the recorded chain artifacts under pinned state — a regression check that the same inputs still produce the same result. |
| `dream.exploration` | `re_execute_capacities` | Re-invokes generative capacities against the *current* L2/L3 to detect drift or surface alternative strategies. |
| `dream.retry` | `re_execute_capacities` (+ replan-injection) | Re-executes a **failed** episode against current state, injecting a replan so the L4 loop can rebuild the chain. |

All three operate at the **TaskRun level** — they re-execute the whole task
from the latest-active chain entry (Chat B D-B6/D-B7). Cross-level variants
(re-run from a sub-Milestone, re-extract hints) are future work.

## Execution policies

A dream capacity declares its policy at registration:

- **`replay_recorded`** — use the recorded chain artifacts; do not re-invoke
  generative capacities. Used for regression checking.
- **`re_execute_capacities`** — re-invoke generative capacities against
  current L2/L3. Used for drift detection and retries.

(`hybrid`, a partial replay, is reserved for a future version.)

## Directives

A dream capacity body is a **directive-emitter**: given a reference to the
episode/TaskRun to dream over, it returns a `DreamDirective` describing the
action — the execution policy, the entry point, the source-episode
provenance, and (for `dream.retry` on a failed episode) a
`ReplanInjectionDirective`. The L4 dream loop reads this directive and
performs the deep-copy, re-execution, and replan.

If a capacity cannot produce a directive — a missing source episode, or
`dream.retry` over an episode that did not fail — it returns nothing
(the OPTIONAL_RETURN dont-know contract, L3-51).

## The dream-cycle driver (Phase 48)

Phase 48 wires the L4 **dream-cycle driver** (`mindsos_intelligence/dream_cycle.py`,
ADR-0178): each timer tick pulls episode descriptors from the corpus, invokes
the three capacities to collect `DreamDirective`s, and re-executes each one
through the orchestrator under the owning session, tagging the run with
`dream_source_episode_iri`. v1 re-runs from the episode's `task_input`; the
faithful episode→MM reconstruction (and the `replay_recorded` vs
`re_execute_capacities` behavioural difference, plus real ALS signal firing)
land with WSD installation, when the learning mechanisms that consume the
signals exist.

## Provenance and privacy

Every directive carries `source_episode_iri`. When the L4 loop re-executes
under it (Phase 48), the signals emitted carry `dream_source_episode_iri`
so learning updates are traceable to the dreamed episode. Dreams run under
the owning user's session and stage only locally — no dream path writes to
Global or crosses users (Chat B D-B9).
