# amii_study — decisions & handoff (updated 2026-07-19)

Pointers + settled decisions. **Supersedes the 2026-07-18 version**, which
described a demo-first, `pressure→vent` toy strategy that has been dropped.
Read this before assuming anything from older files or memory.

## Framing
Novelty is the deployment/organizing **stance**, not the mechanism. Prior-art
check done: the four-axis concept is already owned by FSCIL, neuro-symbolic /
compositional continual learning, and DreamCoder-style library learning. So the
study proves MindsOS **works** and is honestly bounded — **not** a novel
mechanism. Do not reintroduce a novel-mechanism claim.

## The ask (corrected)
**Not** "get Amii's help to run the study" — that was a wrong conclusion from an
earlier chat. The ask is to **attract attention to MindsOS so HA can evolve its
incomplete parts**. The study, run by HA here, is the credible evidence that
makes that ask land.

## Order: study first
Run the full four-axis study; then the pitch presents its results. A small live
demo **cannot** prove MindsOS's value (its advantage is asymptotic — it shows up
under scale + continual change), so we do not lead with a toy. Study = proof;
demo = illustration of the mechanism.

## Domain: power-quality (energy)
Concluded anchor: a parametric PQ disturbance generator (IEEE-1159-style), 1-D,
CPU-fast, genuinely energy. Vibration (CWRU/Paderborn) = the single real-data
replication. SCADA = optional relevance vignette. Intrusion = dropped. Hard
rule: **stay 1-D, no image/video** (keeps compute-to-competence clean and the
laptop story honest).

## Input: raw waveform, not features
Every arm gets the raw 1-D signal — no hand-computed feature names. Removes the
textbook lookup shortcut, makes the LLM a fair-but-hard competitor, and raises
the bar equally (including MindsOS, whose leaves must learn features from signal).

## Held-out design
- Held-out **primitive** — `notch` (never taught) → honesty axis A5. A novel
  *element*: an honest system flags "unknown" instead of mislabeling.
- Held-out **combinations** — `sag+transient`, `swell+transient` (parts taught,
  pairing never) → transfer axis A4. A novel *arrangement* of known parts:
  success = genuine composition, not memorization.
- Caveats: score a held-out combination only after both its primitives are
  competent standalone; the held-out primitive must be genuinely distinct from
  the taught classes.

## LLM role
**Not** a core A1/A3/A4 baseline — PQ is textbook, so an LLM looks it up and our
held-outs aren't held out for a pretrained model (strawman risk). LLM =
**honesty contrast (A5) + one compute data point (A2)**. The real four-axis
competition is the CL + few-shot baselines (they learn from data). LLM behaviour
tested via HA pasting the fair prompt to ChatGPT/Gemini + a self-sample.

## MindsOS arm
Shipped MindsOS as a **consumer**. Its measured contribution is
**composition/reuse** — A1 on *new* combinations, A3 no-forgetting, A4 transfer,
ATTR ablation — **not** leaf learning (any arm can use the same leaves). Define
"MindsOS − structure" precisely before Phase 4 (a flat classifier, no primitive
reuse). Two capabilities the study needs are designed-not-built in core: the
learned-leaf apparatus with calibrated confidence, and multi-input fan-in
**execution** (detections→verdict). This chat writes **core requests (CRs)** for
them; the core track builds; the study consumes. Guardrails: surface
study-critical CRs early; record what core built in the supervision ledger; do
**not** build features shaped to win this study (gaming).

## Kill conditions honored
The study is falsifiable (ATTR may keep the gain; a CL baseline may reach ~0
forgetting cheaply). Report positive **or** sharpened-negative — do not soften
after seeing results.

## Pitch surface (revised — not a notebook)
Two artifacts, built fresh at the end:
- a **PDF document** (stance / bound / built-vs-roadmap / the ask) for the first
  email/application;
- a **live-talk demo** presenting study results, with live compose +
  teach-without-forgetting as *illustration* (not proof).

Superseded, to be removed in the consolidation commit:
`mindsos_ondevice_walkthrough.ipynb`, `MINDSOS_AMII_DEMO.md`,
`ondevice_profile.py`, and the `amii_demo/` pressure→vent core + its guard test.

## Progress — Phase 1 (built + Linux-validated on `chore/amii-study`)
In `projects/amii_study/study/`:
- `generator.py` — PQ raw-waveform generator (14 tests)
- `stream.py` — concept stream + dataset builder (6 tests)
- `metrics.py` — F1, BWT, FWT, labels-to-competence (7 tests)

Next: baselines (1-D CNN + runner → CL zoo/Avalanche + few-shot + LLM probe) →
pilot/calibrate/freeze prereg → MindsOS arm (needs the CRs) → run × ≥5 seeds,
read the frozen test once → analyze vs kill conditions → vibration replication →
write up. Phases run in the prereg's order.

## Rules & workflow
- Consumer of core; **never edit `mindsos_*`**. Heavy deps (torch/Avalanche) in
  the project venv, never core. Project tests run separately from the core gate.
- Control protocol: explain plain-English → HA approves → run. The Cowork
  sandbox writes files via the device bridge; **Mac** commits+pushes (explicit
  paths, never `git add -A`, git only on Mac); **Linux** pulls+validates. No git
  from the sandbox.
- Prereg (`MINDSOS_NOVELTY_STUDY_PREREG.md`) is the anti-drift contract; its
  "learned leaves" assumption depends on the core CRs above.
- Env: Linux repo `/home/sanmyaku/mindsos`; Mac worktree `.../mindsos-amii-study`
  on `chore/amii-study`. The Linux checkout has drifted to `main` mid-work —
  always confirm it's on `chore/amii-study` before validating.
