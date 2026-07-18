# On-device & compute measurement — protocol

Two different claims, two different measurements. Keep them apart or the story collapses.

---

## The pushback first: you cannot show the compute *win* on the toy demo

There is no meaningful neural baseline for "pressure_high → vent." A compute-efficiency
**win** ("X FLOPs < Y FLOPs at equal competence") only exists on a task where a neural
network is the *natural* solution and MindsOS also solves it. That means the FLOPs win
rides on the **power-quality study** (or a comparable real classification task) — **not**
on the walkthrough's toy pipeline. Do not print a FLOPs number next to the toy demo; it
would be apples-to-oranges and a reviewer will say so.

What you *can* show today, honestly and with no baseline, is the **envelope**. So:

---

## Tier 1 — the envelope (run now, on the Mac Mini, no baseline)

Use `ondevice_profile.py`. It reports, on the actual 2012 hardware:

- **hardware + CPU-only** confirmation (CPU model, RAM, no GPU);
- **peak process RAM (RSS)** and peak Python-object memory for a task;
- **wall-clock** to compose + run a task on this CPU;
- **load-on-demand selectivity** — how few capabilities a task instantiates out of the
  full registered catalog (it registers decoys so the ratio is real).

These substantiate the two honest envelope claims: *"runs on a 2012 Mac Mini, CPU-only"*
and *"loads only the fraction of knowledge a task needs."* They are **not** a compute win —
the script says so itself. Present them as the envelope MindsOS operates in.

*(For a stronger load-on-demand number, register your real catalog size, not 20 decoys —
the point is N_used / N_total on a realistic catalog.)*

---

## Tier 2 — compute-at-matched-competence (the win; belongs in the PQ study)

The only fair compute claim. Four rules:

**1. Matched competence.** Compare FLOPs **only at the point both systems reach the same
task result** (e.g. per-class F1 ≥ the study threshold on held-out test). Report accuracy
next to every FLOP number. A lower FLOP count at lower accuracy is a trade-off point, not a
win.

**2. Measure MindsOS FLOPs.** The executed pipeline is small and known, so either:
- *analytical* — count multiply-adds in each executed capacity body (+ any learned-leaf
  inference), summed over the pipeline; or
- *instrumented* — wrap numpy/array ops in the capacity bodies with a counter.
Report **inference FLOPs per decision**. If a leaf was trained, also report its **one-time
training FLOPs** separately (honest, and usually tiny).

**3. Measure baseline FLOPs — including pretraining.** For the neural baseline (1-D CNN,
etc.): inference FLOPs via a standard profiler (`thop`, `fvcore`, `ptflops`), **plus** its
**training FLOPs** = (forward+backward FLOPs per step) × steps × epochs. Report:
- inference-only FLOPs (per decision), and
- **total FLOPs including training** — this is where a large model's real cost lives, and
  it is fair to count it because MindsOS did not pay it. This is the number that makes the
  envelope difference stark and honest.

**4. Report matched hardware + the ledger.** Same CPU for both where possible; report
params, peak RAM, and the **supervision ledger** (what human structure each side received)
so "MindsOS is cheaper because a human pre-authored it" is answered in the open.

### Reporting table (fill from the study)

| | accuracy | inference FLOPs/decision | total FLOPs (incl. training) | params | peak RAM | hardware |
|---|---|---|---|---|---|---|
| MindsOS | | | | | | 2012 Mac Mini, CPU |
| Baseline (tuned CNN) | | | | | | |

The claim is: **at equal accuracy, MindsOS's total FLOPs ≪ baseline's**, and it runs in an
envelope the baseline cannot deploy into. That is the honest, defensible compute story.

---

## What to say, and not say

- Say: *"On a 2012 Mac Mini, CPU-only, MindsOS composes and runs this task in ~X ms, holding
  only N of M capabilities; at matched accuracy on [task] it uses ≪ the total FLOPs a tuned
  CNN needs once you count its training."*
- Don't say: *"MindsOS is faster"* (faster than what, at what accuracy, on what hardware?),
  or attach any FLOPs number to the toy demo, or compare MindsOS inference to baseline
  training. Each of those is the apples-to-oranges a reviewer kills.
