You are the **SKILL_ACQUISITION_PROCESS_CHAT** for the MindsOS project.

> **AMENDMENT 2026-06-09 (reanalysis; Cowork session with Henrique) — read §AMENDMENT at the bottom of this file before acting on anything else. It changes your prerequisites and pre-loads four R0 items.**

CONTEXT: The post-Phase-38 numbered-phase plan is **COMPLETE** — Phases 39–49 are ALL SHIPPED (Integration C closed 2026-06-09, tag `phase-49-confirmed`, `main` at the confirm commit). You are the FIRST downstream **design-authoring** chat after the plan closed. You are NOT a numbered phase: per PB-A, each downstream chat authors its own `<CHAT_NAME>_PHASE_MAP.md` after its design-resolution closes. Your job is to design the skill-installation lifecycle and emit a phase-map — the WSD/FOL/code-skill installation chats ship against your contract.

YOUR CHARTER (read the authoritative definition; this is only a pointer): `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` §6 row "SKILL_ACQUISITION_PROCESS_CHAT" + the recommended-ordering DAG. In brief you own the per-layer skill-install lifecycle — a skill = L1+L2+L3+L4+L5 artifacts as an installable bundle: bundle integrity, Local vs Global tiers, conflict resolution, audit + provenance, de-installation. You are the shared umbrella that must close before WSD installation R0 saturates.

READ FIRST (entry + routing — read in full; this prompt deliberately does NOT restate what these files say):
1. `HANDOFF.md` — §1 (orientation); §3.1.22 (Phase 49 ship — confirms the plan is complete + the as-shipped state); §5 (sister-projects DWF/WSD/FOL intake); §6 (carry-forwards + open R0 questions); §9 (process discipline + ship-env invariants — pair-execution Cowork↔Mac↔Linux, the gate box is a SEPARATE checkout so confirm its HEAD sha + `ls tests/phase_NN` before trusting any gate count; no `gh`/`mindsos` CLI on the gate host; `python3`; squash-before-confirm; tag at the confirm commit; bump manifest `phase`+`version`); §10 (required-reading map + companion docs).
2. `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` — §6 (downstream sequencing: YOUR charter row + the ordering DAG — you open after Phase 47/49 confirmed and must close before WSD installation R0; note ADAPTER_FAMILY_CHAT branches off you); §7 (open questions — q4/q5/q9 land here or in WSD); §8 (closure summary).
3. `projects/README.md` — the recommended chat ordering across DWF / WSD / FOL / skill-acquisition.
4. `projects/wsd/FUTURE_CHAT_PROMPT.md` + `projects/wsd/ANALYSIS.md` — WSD installation is your PRIMARY consumer; inherit its constraints so your bundle/install contract fits what it must ship (the `process.*`/`predicate.*`/`hint.*`/`decision.*` catalogs, ALS subsystems #1–#11, `world-axioms`, the 6 L2 importers, the pending ADRs).
5. `projects/fol/FUTURE_CHAT_PROMPT.md` — FOL installation inherits WSD's picks on shared blockers; note its bundle/provenance/external-blob-store needs.
6. `docs/_workbench/L*_FUTURE_WORK.md` — open items routed to skill-acquisition / WSD / maintenance (grep "skill", "install", "de-install", "bundle", "provenance", "SKILL_ACQUISITION"). Note L0-25 + **L0-26** (durable Falkor persistence gaps) bound what an install can durably persist.

DESIGN GROUND TRUTH (inherit; do not re-litigate — see `CLAUDE.md` + the ADRs):
- The 5 domain layers + the orthogonal Server layer. A skill spans all five domain layers plus Server-owned auth/audit/provenance; Server imports downward (ADR-0010), domain layers never import Server.
- Local (per-user) vs Global (shared) tiers — established across L2/L3/L4/L5; an install must place each artifact in the right tier.
- The capability + audit model (ADR-0010), the L0 persisters (ADR-0160/0161), and the write-capability gate (ADR-0180, `make_writeable`/scope-aware) — installs are WRITE paths; ground the install/provenance writes against the shipped gate, not a new one.
- **L0-26 (open):** the node persister stores node `value` as a primitive (ADR-0130 `_props_json` is metagraph-level only), so structured artifact values don't durably round-trip to Falkor yet — factor this into what install-time provenance/state can persist vs hold in-memory.

OPERATING MODE (project instructions + every prior phase): skeptical design reviewer — default posture is to challenge, surface hidden trade-offs, state the strongest concern first, give scannable options + your pick, no filler. **Probe-first:** read the real shipped surfaces (capability/audit constants, the persisters + KL bootstrap, `CapacityLayer.register_*`, the L4/L5 install touchpoints, any existing bundle/manifest shapes) before locking picks — every Phase 39–49 chat caught a scope reality this way and several reversed their pre-R0 framing. Ground every surface against its real consumer (WSD installation); defer absent-consumer surfaces.

FIRST ACTIONS:
1. Prereq check: `git tag --list | grep -E "phase-49-confirmed"` (present); `git log --oneline -1` on `main` = the Phase-49 confirm commit; note the long-standing untracked items (never `git add -A`; stage selectively).
2. Acknowledge the required-reading (one line each on what you took from it).
3. Open `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` R0 (mirror prior phases' S-surface + pushback format): enumerate the lifecycle surfaces — bundle schema + integrity; the per-layer artifact set (what L1/L2/L3/L4/L5 pieces a skill contributes); Local vs Global tier placement per artifact; conflict resolution (name/IRI collisions, version skew); audit + provenance on install/de-install; de-installation (reverse-dependency safety); idempotency — and surface the genuine design forks as pushbacks with options + your pick.
4. Run pre-impl pushback rounds to saturation, then author `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` (your sequencing output) before any code.

OUTPUT EXPECTATION: this is a DESIGN chat — its deliverable is the design log + a phase-map that sequences the install lifecycle; it does NOT ship product code (WSD installation ships against your contract). If you decide a thin shippable substrate is warranted, surface it as a pushback first.

ALTERNATIVES (per `POST_PHASE_38_PHASE_MAP.md §6`, independently openable if you'd rather sequence differently): `DWF_INSTALLATION_CHAT` (L2-only, parallelizable now), `L4-v2 follow-up chat` (opens now that Phase 49 is confirmed), `MAINTENANCE_CHAT` (any time — holds L0-24/L0-25/L0-26 + small items). Pick deliberately and say why in R0.

---

## §AMENDMENT 2026-06-09 — revised prerequisites + pre-loaded R0 items

A reanalysis pass (2026-06-09, post-Phase-49) revised the downstream ordering and pre-loaded this chat's R0. Where this section conflicts with the body above, this section wins.

**Revised prerequisites — you now open AFTER `MAINTENANCE_CHAT` closes** (prompt: `confirmation_docs/MAINTENANCE_CHAT_NEXT_CHAT_PROMPT.md`). Two of its outputs are your inputs:

1. **The L0-26 serialization-contract ADR** (decide-and-document; implementation deliberately deferred to YOUR phase-map slot 1 as first consumer). Design install provenance/state against that ADR's contract — not against in-memory holds, and not by inventing a new persistence shape.
2. **`projects/ANALYSIS_DELTA_2026-06.md`** — the WSD/FOL ANALYSIS docs named in READ-FIRST items 4–5 are dated 2026-05-28 and contain claims falsified by Phases 43–49 (L4/L5 "nothing shipped"; `sense-correlations` ship-once — withdrawn at Phase 43 with a regression guard; `learned-parameters` WSD/FOL alignment — FOL split deferred, NOT aligned; C-bin conflicts already resolved by ADR-0155/Phase 41). **Read the delta addendum FIRST; treat the originals as historical.**

**Pre-loaded R0 items (surface these as your first pushbacks; defaults were picked at reanalysis — re-litigate only with new evidence):**

- **R0-SA-1 — Scope fork: installation vs acquisition.** The system has TWO acquisition paths: (i) admin-side bundle install (your charter); (ii) the runtime promotion loop (`parameter-staging` → `pending-promotions` → `learned-parameters`), which as of Phase 49 is **schema-only with zero writers/consumers and no owning chat in PHASE_MAP §6** — a routing gap, not a design nuance. Options: (A) unify both under one lifecycle here; (B) split, route promotion-loop closure to WSD; (C) **[DEFAULT]** unify the *contract* (promotion = a second producer of the same install artifacts: same tiers, audit, provenance, conflict rules) but the promotion *mechanism* ships in WSD. Whatever you pick, author the PHASE_MAP §6 routing amendment at your closure so the loop has an owner on paper.

- **R0-SA-2 — Phase-map slot 1 = trivial-bundle reference install.** Package something already shipped (e.g., a `text.*` extension) as a bundle; install + de-install it end-to-end. This is the first consumer for the L0-26 ADR implementation. **Pass criterion — write it this narrowly:** validates install / de-install / provenance / idempotency ONLY. It does NOT validate "installed skill runs" — real dispatch arrives only when WSD replaces the `planning.*` v0 catalog (the v0 lifecycle dispatches no real L3 capacity; Phase 49 PB-1a). Do not let the criterion inflate; do not pull a dispatch fix into slot 1 (L4 scope creep).

- **R0-SA-3 — De-installation is a design stub at v1; L4 artifact slots are opaque.** Zero installs exist and the ALS subsystems / signal sources are empty skeletons — reverse-dependency-safe de-install semantics and rich L4 artifact slots designed now would be spec-against-fiction. Keep the v1 bundle schema's L4 slots minimal/opaque; expect WSD to force the real shape; record the v2 trigger.

- **R0-SA-4 — Bundle L3 bodies are CapacityContext-native from day one.** The shipped read path is still dict-based (union annotation; PB-23 read-half open, recorded by MAINTENANCE M4). Your contract mandates: capacity bodies arriving in bundles are authored against typed `CapacityContext`, never the dict form — so they are never migrated. The mechanical corpus migration of EXISTING bodies is WSD slot 1, not yours.

- **R0-SA-5 (small) —** Close the `IntergraphEdge` vs `InterGraphEdge` naming reconciliation (HANDOFF §2.1 routes it here). Shipped code is uniformly `IntergraphEdge`; default = WSD docs adopt shipped spelling.

---

## §AMENDMENT-2 2026-06-09 — MAINTENANCE_CHAT closed; prerequisites SATISFIED

MAINTENANCE_CHAT closed 2026-06-09 (tag `maintenance-2026-06-09`; cumulative gate **3874/11/1 xpassed/0 failed**; full record `confirmation_docs/MAINTENANCE_CHAT_LOG.md`). Where this section conflicts with anything above, this section wins.

- **Prereq check correction (FIRST ACTIONS item 1):** `main`-tip is now the MAINTENANCE closure range, NOT the Phase-49 confirm commit. Check instead: `git tag --list | grep -E "phase-49-confirmed|maintenance-2026-06-09"` (both present) + `git log --oneline -1` showing the MAINTENANCE gate-record commit (`8256299` or later).
- **The L0-26 contract ADR is ADR-0182** (`docs/decisions/adr/0182-node-value-serialization-contract.md`): node-level `_value_json` (ADR-0130 pattern); primitives unchanged; writer lifts queryable fields flat (keeps ADR-0181 indexes). Your slot 1 implements it (sentinel `tests/maintenance/test_adr_0182_sentinel.py` pins "no implementation shipped" — replace it with round-trip coverage when slot 1 lands). DESIGN GROUND TRUTH's "L0-26 (open)" bullet: the *contract* is no longer open; only the implementation is, and it is yours.
- **`projects/ANALYSIS_DELTA_2026-06.md` is on disk** — read before the WSD/FOL ANALYSIS docs (both carry stale-banners now).
- **The CapacityContext read-path routing record is `docs/_workbench/L3_FUTURE_WORK.md` L3-59** (R0-SA-4's "recorded by MAINTENANCE M4").
- **New since this prompt was written:** `tests/maintenance/` exists (live FalkorDBLocalPersister round-trip + scoped-delete coverage; orphan-scan xfail probe — sweep audit routed to WSD); **M2-F1** fixed a pre-existing L0 bug (hyperedge `type_name` was never persisted — `28d149f`); L0-24 import cycle fixed (the phase_44/phase_49 conftest warm-ups are GONE — don't reintroduce that pattern).
