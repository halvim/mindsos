# amii_study — decisions & handoff (2026-07-18)

Pointers, not restatements. Read the referenced files; don't ask me to repeat them.

**What this project is.** Prove MindsOS's efficiency + on-device claims as a *door to get
help* (e.g. Amii) — NOT a new-mechanism research paper. Novelty = the deployment/organizing
**stance**, not the mechanism. Full positioning: project memory
`mindsos-positioning-novelty-stance.md` — read it.

**Location & rules.** Project/consumer of MindsOS under `projects/amii_study/` — **NOT core**.
Never edit `mindsos_*`. Heavy baseline deps (torch; the Avalanche CL library) live in THIS
project's own env, never core. Project tests run separately from the core gate.

**The study.** Defined in `MINDSOS_NOVELTY_STUDY_PREREG.md` (this folder): four axes off ONE
incremental run + a structure-ablation for causal attribution; domain = power-quality
parametric generator; strong baselines; matched-competence; pre-registered success/kill.
The prereg **is** the anti-drift contract — do not deviate without HA approval. Read it; do
not restate it.

**Prior-art check: DONE.** The 4-axis *concept* is already owned by active fields (few-shot
class-incremental learning; neuro-symbolic / compositional continual learning; DreamCoder-
style library learning); even incremental power-quality classification exists. So the study
proves MindsOS **works** and is honestly bounded — NOT that the mechanism is novel. Do not
reintroduce a novel-mechanism claim.

**Measurement.** `COMPUTE_MEASUREMENT_PROTOCOL.md` + `ondevice_profile.py`. Two SEPARATE
claims: the on-device envelope (run the profiler on the 2012 Mac Mini → real numbers feed
walkthrough §8a) and compute efficiency (FLOPs-at-matched-competence, counting the
baseline's pretraining — belongs in the STUDY, never on the toy demo).

**Pitch artifact.** `mindsos_ondevice_walkthrough.ipynb` (runs on CPU; the door). Demo
script + guard test are inside `MINDSOS_AMII_DEMO.md` — the guard test has **never
executed**; Linux-validate before trusting it.

**Control protocol (HA, non-negotiable — prior studies failed without it).** Before running
anything: (1) explain in plain English, (2) discuss until HA approves, (3) only then run —
Linux validates. Mac creates+commits+pushes (explicit paths only, never `git add -A`, git
only on Mac); Linux pulls+validates; no git from the Cowork sandbox. Never decide study
direction unilaterally.

**First steps for the next chat.** (1) Confirm this folder name; commit these files under the
protocol (Mac→Linux). (2) Run `ondevice_profile.py` on the Mac Mini for real envelope
numbers. (3) Build the study per the prereg (generator → baselines → MindsOS arm),
approval-gated, Linux-validated.
