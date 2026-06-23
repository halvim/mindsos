# WSD coupling diagnosis — for the core-modification chat

**Tag:** `bongard-solver` · 2026-06-20 · presentable artifact.

## Claim
WSD is MindsOS's **text** subsystem. Only text-interpretation features should be gated by it. The WSD installation plan (`projects/wsd/WSD_INSTALLATION_PHASE_MAP.md`, phases 51–56) ships several **general-purpose core mechanisms** with nothing to do with text. They were parked in WSD because it was the *first* installation chat to need them — defensible under one consumer, but it now blocks every non-text consumer (e.g. bongard-solver) behind a text chat.

## Why this isn't "WSD did it wrong"
The repo parked these in WSD on **consumer discipline** ("don't build the real catalog against fiction — let the first real consumer force its shape"; Phase-47 v0 placeholder rationale). That was valid with *one* consumer. **bongard-solver is now a second, non-text consumer** — which is exactly the trigger to lift a mechanism out of its first consumer into a general home. Two consumers ⇒ generalize.

## Evidence: WSD phase-map slots, classified

| Slot | Item | Text? | Verdict |
|---|---|---|---|
| 51 | Lexicon empirical-layer EdgeTypes | ✅ | keep |
| 51 | **L3-59(b) read-path → typed `CapacityContext` + union-drop**; L0-25 delete-sweep audit | ❌ | **detach** — general L3/L0 cleanup |
| 52 | SemCor / GlossTag importers | ✅ | keep |
| 52 | **ADR-0181 physical Falkor index creation** | ❌ | **detach** — general retrieval/persistence infra |
| 53 | `perception.nlu_parse`, `scoring.wsd_rank_senses`, `REALM_NLU`, `wsd-core` bundle | ✅ | keep |
| 54 | **`hint.*` / `predicate.*` / `decision.*` capacity families** | ❌ | **detach** — general L3 families |
| 54 | **v0→real flip of `planning.*` / `phase1.*` / `orchestration.*` + orchestrator default flip** | ❌ | **detach** — the general L4 orchestrator's real catalogs |
| 54 | `wsd-pipeline` bundle, nlu-slice cookbook | ✅ | keep |
| 55 | **Promotion-loop mechanism** (staging→pending→learned; writer API + review surface + admin apply) | ❌ | **detach** — general autonomous-learning loop |
| 55 | **ALS mechanism + real L4 manifest slot shapes + capacity-gaps tooling + ALS audit constants** | ❌ | **detach** — general L4/admin infra |
| 55 | ALS **sense-ranker** subsystem; dream **sense-miner** | ✅ | keep (mechanism detaches; this subsystem stays) |
| 56 | DOLCE / FrameNet sense stratum | ✅ | keep |

## The pattern
Each flagged slot = **general mechanism + its first text consumer**, fused. Detach = split into (mechanism → general home) + (text consumer stays in WSD, depends on it). The repo half-did this already: S10 made the promotion loop "producer-agnostic" *on paper*, but its **mechanism still ships only in WSD-5**.

## Impact on bongard's two acquired skills
- **Skill 2 — minting** depends on the **promotion-loop mechanism** + **capacity-gaps tooling** (both WSD-55) and **CC-1/2/3** (composite persistence/promotion — `CORE_CHANGES.md`). All non-text. WSD-gated ⇒ minting blocks on a text chat or needs a shim.
- **Skill 1 — bongard solving** control loop depends on **real L4 catalogs** (WSD-54 v0-flip) and the **typed read-path** (WSD-51). Non-text. Same block.
- **Neural leaf** (skill 1's eventual path-2 ground for messy/curved images): vision, not text — rides the **shipped install path**, already independent of WSD. No detach needed.

## Recommendation to the core chat
Give these general homes, *then* let WSD consume them as the first text client:
- **D1** L4 real-catalog flip + `hint`/`predicate`/`decision` families.
- **D2** promotion-loop mechanism → its natural home is the skill-acquisition producer contract (already producer-agnostic).
- **D3** ALS mechanism + L4 manifest slot shapes + capacity-gaps tooling + ALS audit constants.
- **D4** read-path typed-`CapacityContext` migration + union-drop (overlaps bongard CC-4).
- **D5** ADR-0181 physical index creation.

Net: a non-text demo (bongard) and the text subsystem (WSD) both depend on D1–D5, but neither gates the other.
