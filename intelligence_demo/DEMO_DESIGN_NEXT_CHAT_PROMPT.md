# Next-Chat Prompt — MindsOS Intelligence Demo Design (AI-community audience)

> Paste this as the opening message of the next chat. It seeds a design chat whose goal is to **design (not yet build) a minimal, non-circular, buildable demo that showcases MindsOS's learning paradigm to the AI/ML research community.**

---

## Role

Continue as a **critical design reviewer** (MindsOS project posture: skeptical by default, challenge assumptions, surface trade-offs, terse, no validation-to-be-polite, alternatives as a scannable menu). You are helping me design a demo, not cheerleading it.

## Why this demo exists (the goal)

A prior analysis chat audited the MindsOS code and found that **most of the system's headline capability claims have zero proof today** — the substrate is real, but the learning engine, structure discovery, transfer, and self-improvement are designed-but-unbuilt (scaffolding / empty ALS skeletons). That chat then ran ~7 rounds of adversarial debate that hardened MindsOS's *learning paradigm* into a defensible thesis **with explicit honest boundaries** (instruct-and-compose vs blind fit; auditable pipelines with small contained learned leaves; a representation trade vs VLA — NOT "strictly better, no black box anywhere").

**The `intelligence_demo` is the answer to the zero-proof problem: a minimal, honest, non-circular demonstration that converts *some* of those claims into evidence for the AI/ML research community.** It is not a product demo — it is a proof-of-path for the paradigm. The full record of that debate (the thesis, the mechanisms, and — critically — the boundaries we must NOT overclaim past) is in the paradigm handoff below; read it as the binding contract for what the demo may and may not assert.

## Required reading (in order)

1. `intelligence_demo/INTELLIGENCE_PARADIGM_HANDOFF.md` — **the distilled output of our debate**: the thesis, mechanisms, **honest boundaries (§4)**, architecture reconciliation (§3), and the demo criteria (§7–9). **Load this fully; it is the contract for the demo's claims.**
2. `ROBOTICS_PITCH_HANDOFF.md` §3 — code-verified reality (the zero-proof audit): the learning engine is unbuilt; the demo must build a minimal kernel, not wire existing parts.
3. `MINDSOS_VS_ROS_EVALUATION.md` §4 — the architectural ceilings (what MindsOS cannot learn by design).
4. `CLAUDE.md` + `HANDOFF.md` — current shipped state (Phase 50; WSD slots 51–56 reserved; ALS = empty skeletons).

## Where MindsOS lives (full code + documentation map — to know what is already planned)

The repo root is the MindsOS project folder. To understand the shipped system and **everything already planned** before designing the demo:

- **`CLAUDE.md`** (root) — project instructions + a dense running status of every shipped phase. **`HANDOFF.md`** (root) — the canonical entry point: current state, L4/L5 design state (settled vs contested), sister projects, carry-forward backlog, per-chat required-reading map.
- **Code packages** (8): `mindsos_core` (L1 graphs/metagraphs), `mindsos_knowledge` (L2 role-graphs), `mindsos_capacity` (L3 capacities — see `family_rules.py`, `capacity_layer.py`, `builtins/`, `identifiers.py`), `mindsos_intelligence` (L4/L5 orchestrator, chain artifacts, consolidation, ALS, dream), `mindsos_instances`, `mindsos_server` (auth/sessions/skills install), `mindsos_admin` (importers), `mindsos_cli`.
- **`docs/`** — `concepts/` (task-lifecycle, intelligence-layer, layers, planning, replan, capacity-families, mm-substrate, promotion-bridge, dream, …), `decisions/adr/` (ADRs 0001–0183+, the authoritative design decisions), **`future_work/` (L0–L5 FUTURE_WORK — the canonical list of what is planned-but-unbuilt; L3_FUTURE_WORK §L3-16 is the learning-strategy capacities, the load-bearing item for this demo)**, `usage/cookbook/`, `getting-started/facts-and-figures.md`. Preview: `pip install mkdocs mkdocs-material && mkdocs serve` → http://127.0.0.1:8000.
- **`confirmation_docs/`** — per-phase design logs + confirmed docs + chat decision logs: `CHAT_A_DECISIONS.md`/`CHAT_B_DECISIONS.md` (L4/L5 architecture), `L1_L3_REFRAME_DECISIONS.md`, `L2_CHAT_DECISIONS.md`, `POST_PHASE_38_PHASE_MAP.md` (Phases 39–49 plan), `WSD_INSTALLATION_PHASE_MAP.md` (Phases 51–56 — the learning/ALS/promotion roadmap), `SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md`, `PHASE_4x_DESIGN_LOG.md`.
- **`projects/`** — `wsd/`, `fol/`, `dwf_mapping/` each with `ANALYSIS.md` + `FUTURE_CHAT_PROMPT.md` + `source/`; `ANALYSIS_DELTA_2026-06.md` (corrections); `README.md` (chat ordering). **WSD is where the real learning engine (ALS mechanisms, signal sources, promotion loop) is specified** — essential for knowing what is already planned for learning.
- Use code search / a deep read over these before proposing the demo, so the design reuses planned vocabulary (capacities, DataStates, ALS mechanisms, signal sources) rather than inventing parallel concepts.

## What this chat must produce

A **demo design spec** (1–3 pages) for an AI-community-facing demonstration of the MindsOS learning paradigm, covering: domain choice, exactly what is built vs mocked, the experimental protocol (incl. the held-out generalization test and a blind-ML baseline), the auditability/known-unknowns surface, and the minimal new-subsystem kernel to implement. **No code in this chat unless I ask** — design first.

## The paradigm the demo must make legible (the contrast to sell)

Blind ML / VLA: give data + label, machine invents an opaque middle.
MindsOS: give data + label + **the middle (pipeline)**; machine **verifies / repairs** it and **flags structural holes** for teaching. Learning = identifying/composing **auditable** pipelines + capacities, with sub-symbolic learning confined to **small, contained, named, replaceable leaves.**

## What the demo must prove (criteria — all five, or it's not enough)

1. **Instructed learning** — teach the pipeline (the middle), not just data→label.
2. **Verify / repair + known-unknown** — system checks a taught pipeline against data and **identifies a hole** rather than failing silently.
3. **Structure discovery (≥ front 1)** — system mints/refines a sub-capacity from experience, **provably not hardcoded** (auditable).
4. **Held-out generalization** — a never-seen case solved *because the learned structure transfers*; a memorizer/blind-ML baseline fails it. **Mandatory — no held-out test ⇒ proves nothing.**
5. **Auditability** — human-legible trace of *why*, and an honest "I have no pipeline for this" on the out-of-scope case.

## Hard constraints (from the handoff §4/§8 — non-negotiable)

- **Concede perception.** Feed pre-decomposed scalar signals or use a discrete rule-closed domain. The claim under test is *structure learning + generalization + auditability*, NOT perception-from-pixels.
- **No circularity.** Do not bake in the rule the system is supposed to discover. The skeptic's first probe is "did you hardcode it?" — the design must defeat that.
- **No faking the load-bearing beat.** If structure-discovery or generalization is mocked, the demo is void.
- **Don't claim "no blindness."** Show small contained leaves, not zero leaves. Honesty boundaries §4.1–4.6 hold.
- **Buildable minimal kernel.** The learning subsystem is unbuilt; scope the smallest real implementation that proves the five criteria, and state plainly what is out of scope.

## Open design decisions to resolve in this chat

1. **Domain** — chess-like / grid-world / simple dynamical system with scalar signals? Must allow structure-discovery + generalization to be *shown* and be cheap to run many trials. (Pick one; justify against the five criteria.)
2. **Build-vs-mock boundary** — the minimal kernel to implement vs honest out-of-scope.
3. **New signal-representation primitive** (handoff §3) — instantiate minimally; how?
4. **"Mint a new capacity" criterion** (handoff §2 front 1 / §4.4) — concrete rule for when a better parameter region becomes a named sub-capacity.
5. **Generalization metric + baseline** — the held-out set, and the blind-ML/memorizer control that makes the result legible to ML researchers.
6. **Firewall stance** — AI-community audience may warrant more architectural reveal than the robotics doc. Decide how much "how" to show vs keep black-boxed (IP).
7. **Reconciliation with fixed-not-learned** — confirm the demo's learning lives as {fixed L3 strategy capacity + learned L2 parameters + new signal primitive}, consistent with the invariant.

## Posture reminders

- Lead with the strongest concern; Pros/Cons; alternatives as a menu.
- Push back on vague choices; ask for the missing constraint instead of guessing.
- The thesis is a **research bet with honest boundaries** — design a demo that earns it, not one that overclaims it.
