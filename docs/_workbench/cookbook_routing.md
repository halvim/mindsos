# Cookbook Routing

**Purpose.** Routes for cookbook pages deferred at Phase 38 R0-PB-2 (OOS at that phase because the consumer code didn't ship). Per Chat C R0-PB-7: cookbook authoring is OOS for the Phase 39-49 plan except the one Phase 49 ships; the other two are routed to their natural authoring chats.

**Inherits from.** `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` cookbook-authoring-scope decision; `confirmation_docs/PHASE_38_DESIGN_LOG.md §4` items #11 + #13 origin.

---

## Routing table

| Cookbook page | Status | Authoring chat | Ships when | Notes |
|---|---|---|---|---|
| `docs/usage/cookbook/text-realm.md` | **Shipped** | Phase 38 | 2026-05-28 (Phase 38 confirmed) | First cookbook; baseline for the format. |
| `docs/usage/cookbook/end-to-end.md` | **Shipped** | Phase 49 (Integration C) | 2026-06-09 (phase-49-confirmed) | Trivial-task scenario walk-through. As-shipped: L0 login → read-side L3 `text.space_split` invoke + write-side L4 lifecycle over v0 catalogs → L5 consolidation → Episode in-memory → Phase-44 Falkor machinery round-trip (Global pair) → synchronous dream. Two-slice composition (PB-1a); the live **Episode** flush is a documented gap (PB-RT / L0-26 — node `value` is primitive, Episode `value` is a dict). Documents the substrate, not a feature-complete demo. |
| `docs/usage/cookbook/nlu-slice.md` | Deferred | **WSD_INSTALLATION_CHAT** | First WSD installation phase shipping `process.*` + `predicate.*` + `hint.*` catalogs sufficient for an NLU end-to-end | Phase 38 R0-PB-2 OOS'd this because no `nlu` builtins shipped at L3. WSD installation lands the relevant L3 family catalogs (per L1_L3_REFRAME_DECISIONS L3-36/L3-42/L3-43 family contracts). |
| `docs/usage/cookbook/code-slice.md` | Deferred | **CODE_SKILL_INSTALLATION_CHAT** | First code-skill installation phase shipping `code.*` realm DataState catalog + `process.code.*` + `generation.code_*` catalogs | Phase 38 R0-PB-2 OOS'd this because no `code` builtins shipped at L3. Per L3_FUTURE_WORK L3-28/L3-30/L3-31; per L1_L3_REFRAME_DECISIONS L3-43 `process.*` family ownership table (code → code-skill installation). |

---

## Discipline

- Each downstream chat reading this file is responsible for updating its routed cookbook's status when it ships.
- Cookbook format inherits from Phase 38's `text-realm.md`: walk-through prose + golden-output snippets + CLI invocations.
- Reading this file is part of any downstream chat's R0 reading-list if it would otherwise re-decide cookbook authoring.

---

*Live index. Update on cookbook ship or chat-ownership change.*
