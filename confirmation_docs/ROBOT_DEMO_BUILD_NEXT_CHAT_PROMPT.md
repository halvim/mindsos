# Robot Demo — Build Chat (next-chat prompt)

> **STALE 2026-06-10.** This prompt targeted the Phase-A start and the stub-controller plan. Phases A and B are done; L4/L5 shipped; the stub is dropped. A fresh build chat should instead read `ROBOT_DEMO_STATUS.md` → `ROBOT_DEMO_MINDSOS_PLAN.md` and start from the plan's build sequence. Kept for history.

Paste the block below to start the build chat. It points at files rather than repeating them.

---

We are building the **MindsOS Robot Demo** (a showcase of MindsOS as a layered robot brain). The design is **settled at the demo level** in a prior Cowork chat; this chat moves from design to **build**. Do not re-litigate settled decisions — read the docs, then implement.

**Read first, in this order (do not skip):**
1. `HANDOFF.md` (root) — canonical entry point; see the "Robot Demo workstream" pointer near the top.
2. `CLAUDE.md` (root) — project + working conventions.
3. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` — the scenario; **read §0a "Canonical model update" first** (it supersedes drifted earlier sections).
4. `confirmation_docs/ROBOT_DEMO_PROTOTYPE_PLAN.md` — the build plan (Phases A–F, architecture, protocol).
5. `confirmation_docs/ROBOT_DEMO_OPEN_QUESTIONS.md` — every decision tagged resolved/open; **§7 locks + §8 round-2 are authoritative**.
6. `confirmation_docs/ROBOT_DEMO_ARCHITECTURE.md` — client–server rationale.
7. `confirmation_docs/DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` — net-new MindsOS features (F1–F6). **These are future MindsOS design, NOT this chat's job** — stub them.
8. `demo_ui/` — the **frozen v9** UI (`presentation_mockup.html`, `CHANGELOG.md`, `versions/`). `prototype_zero/` — the validated stick-arm cell + reach proof.

**Your goal:** deliver the working prototype described in the plan — everything **except** the real MindsOS brains, which are replaced by a **stub controller** that honors the same seam behavior (so MindsOS drops in later at Phase F).

**Start with Phase A** (no MindsOS dependency): build the real-asset MuJoCo scene — **Franka Panda ×2** (Arm 1 + suction tip, Arm 2 + Robotiq 2F-85), per-arm **vertical 3×3 shelves**, **continuous belt with an unreachable middle + command-driven conveyor**, carrier **Box** + **Sheet/Tube** cargo. **First task within Phase A: re-validate reach** on real Panda kinematics against the belt and all 9 vertical cells — the top shelf row at set-back distance is the expected failure point (P2). Then export meshes to glTF for browser rendering.

**Boundaries / do-nots:**
- Do **not** rebuild the v9 UI — it is the frozen visual baseline. The live frontend (graph tab, control-token, teach/inspect/replace/retire) is **v10 = Phase D**, built against live data.
- Do **not** design the F1–F6 MindsOS features — stub them at the seam; they belong to a separate MindsOS-design chat.
- Grasp = **attach-on-valid-contact**; containment = **attach-on-insertion** (see plan).

**Working conventions:**
- Act as a **critical design reviewer** per `CLAUDE.md` project instructions — push back, surface trade-offs, be concise.
- Keep the **versioning + CHANGELOG discipline** already used in `demo_ui/` for any new build artifacts.
- Record decisions in `confirmation_docs/`; update the `ROBOT_DEMO_OPEN_QUESTIONS.md` tags and the `HANDOFF.md` pointer as milestones land.
- Use the workspace shell for MuJoCo (CPU/headless is fine; no server GL — browser renders).

Confirm you've read the files and restate the Phase-A plan + the first reach-validation task before writing code.
