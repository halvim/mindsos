# Robot Demo — IP sanitization policy (what the demo may expose)

**Decided 2026-06-12 (Henrique), policy B.** Everything that reaches a participant's browser
(panel text **and** the raw WS frames behind it — devtools-visible over the tunnel) must show
**cognitive/operational behavior** but **strip MindsOS implementation/IP**. Applies to **all feeds**:
brain cards, Inter-brain (Seam B), Server (Seam A), and the future reasoning/audit view. The backend
(DM-4+) must emit already-sanitized content — the UI cannot protect what the wire already leaked.

## Principle

- **Show:** what the system *does* — authenticates, authorizes, **blocks**, saves, audits; doesn't
  know → learns → does → shares → blocked by body → recovers; the decisions and outcomes.
- **Hide:** *how it's built* — tech stack, internal type/role/capability names, layer mechanics.

## Do NOT expose (mechanism / IP)

- **Tech:** FalkorDB, SQLite, `server.db`, redis, etc.
- **Architecture terms:** Local / Global, promoted-pipelines, episodic_memories, Pipeline,
  composite, register_capacity, the "writeable gate", DataState, HintSet/MappingResult/Plan/
  PipelineRun/TaskRun (chain-artifact type names), L2/L3/L4.
- **Identifiers:** capability constants (`CAN_WRITE_GLOBAL`), audit constants (`EVT_*`), capacity
  IRIs (`a1.load_into_box`), task-pattern IRIs, role-graph names, skill-bundle names/versions/digests.
- **API/method names:** `query_capabilities()`, `promote()`, `dispatch(...)`, `place_at_cell(...)`.

## Generic mapping (the canonical token → display table)

| internal (do not show) | generic display |
|---|---|
| `query_capabilities()` | "What can you do?" |
| `DONT_KNOW(handoff-via-belt)` | "Don't know how to hand across the gap" |
| Register/`capture Pipeline → composite` | "Learn / save the new skill" |
| `promote Local→Global`, `→ Global` | "Share fleet-wide" |
| party **Global** | **Fleet** · party **L2** | **Library** |
| `promoted-pipelines`, `Pipeline` | "(shared) skill" |
| `gate` / `GATED` / "embodiment gate" | "blocked" / "blocked (wrong gripper)" |
| `CAN_WRITE_GLOBAL` | (drop) → "permission required" |
| `persisted → FalkorDB` | "State saved" |
| `EVT_SKILL_INSTALLED` etc. | "Audit entry recorded" (no constant on the wire) |
| `episode retained (episodic_memories)` | "Remember this run" |
| skill `handoff-via-belt` | "hand-off" | `place-at-cell` → "place-in-cell" | `stage-at-position` → "stage-on-belt" |
| capacity IRI `a1.load_into_box` | "load into box" |
| `server.db` / version `phase-50` | (drop) |

## Server (Seam A) event vocabulary (the only kinds emitted)

`bootstrap`→"System initialized" · `login`→"Session authenticated" (vitals "N sessions active") ·
`skill`→"Capability provisioned (<brain>)" · `gate_ok`→"Action authorized" (significant only —
skill install, state save) · **`gate_no`→"Action blocked — permission required"** (the money event) ·
`persist`→"State saved" · `audit`→"Audit entry recorded". Vitals: sessions, **"Storage: connected"**
(not "Falkor"), uptime. No `EVT_*`, no role/capability names, no tech.

## Reasoning/audit view (when built)

Render the chain as generic stages — **"Understood request → Chose approach → Planned steps →
Executed → Outcome"** — NOT "HintSet → MappingResult → Plan → …". Within: capacity IRIs → plain
action labels, task-pattern IRIs → plain approach names. The "why did it decide/refuse X" story is
preserved in behavior terms; the MindsOS vocabulary is not shown.

## Optional later (not v1)

A `?audience=internal` switch could restore full detail for a presenter/internal view while the
default (participant) view stays sanitized. Not built; noted.
