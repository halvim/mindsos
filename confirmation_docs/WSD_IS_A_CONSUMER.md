# WSD is a CONSUMER, not an OWNER — doc-fix plan

**Filed:** 2026-07-30. **Status:** proposal, nothing changed yet.
**Verified at:** `origin/main` `01e4d0d`.

---

## 1. The rule already exists. It is being contradicted at the point of use.

`RULES.md` §8 already states this, in these words:

> **Subsystems own nothing architectural.** WSD is a MindsOS *subsystem* (a Skill)
> for text — one piece of the larger **NLU** system. It is *installed on top of*
> the MindsOS platform and *uses* core components; it does **not** own any L0–L5
> architectural component. […]
> **Any component that belongs to MindsOS is core, even if a subsystem needs it
> first.** […] (Stop deferring core mechanics "to WSD" — that framing is wrong and
> has misled multiple chats.)

So the rule is not missing. The problem is that **24 docstrings inside `mindsos_*`
say the opposite**, and a chat reading the code never reaches `RULES.md`. The
docstring is right next to the thing being built; the rule is in a file at the repo
root. The docstring wins every time.

**Conclusion: fixing this is a code-comment change, not a new rule.**

---

## 2. Every site that says "WSD ships it" (24 mentions, 18 files)

### 2a. WRONG — core mechanism deferred to a subsystem. Rewrite these.

| File | Line | Current framing |
|---|---|---|
| `mindsos_capacity/builtins/orchestration_v0.py` | 4 | "real bodies ship in WSD installation" |
| `mindsos_capacity/builtins/orchestration_v0.py` | 19 | "install is opt-in; WSD replaces" |
| `mindsos_capacity/builtins/phase1_v0.py` | 6 | "real L3 capacities … ship in WSD installation" |
| `mindsos_capacity/builtins/phase1_v0.py` | 14 | "install is opt-in; WSD replaces" |
| `mindsos_capacity/builtins/planning_v0.py` | 13 | "WSD installation atomically replaces this catalog" |
| `mindsos_capacity/identifiers.py` | 112 | "WSD installation atomically replaces them with real catalogs" |
| `mindsos_intelligence/orchestrator.py` | 10 | "real catalogs ship in WSD installation" |
| `mindsos_intelligence/phase_6.py` | 6 | "body ships in WSD installation" |
| `mindsos_intelligence/plan_construction.py` | 44 | "deferred with real decomposition / WSD" |
| `mindsos_intelligence/execution.py` | 87 | "MSUR + SCMS Plan/Milestone orchestration hooks (WSD) are still absent" |
| `mindsos_intelligence/als_registry.py` | 6 | "when WSD installation ships" |
| `mindsos_intelligence/als_subsystems.py` | 6 | "WSD installation fills the concrete mechanism" |
| `mindsos_intelligence/signal_sources.py` | 4 | "concrete payload schemas + emitters land in WSD" |
| `mindsos_intelligence/retention.py` | 13 | "consumers — WSD episode reconstruction / retrieval — wire later" |
| `mindsos_intelligence/dream_cycle.py` | 13, 85 | "WSD-gated"; "land with WSD" |
| `mindsos_intelligence/capacity_persister.py` | 28 | "until dream reconstruction (WSD)" |

**Replacement wording** (one sentence, same shape everywhere):

> Placeholder. The real body is a **core** capacity that has not been built yet;
> it is not owned by any subsystem. See `RULES.md` §8 and ADR-XXXX. Tracked in
> `CORE_CR_REAL_L4_CATALOGS.md`.

### 2b. ALREADY RESOLVED — no change needed, but say so.

| File | Line | Note |
|---|---|---|
| `mindsos_intelligence/capacity_persister.py` | 8 | reverses the "live-only until WSD" clause — correct as written |
| `mindsos_intelligence/consolidation.py` | 18 | same reversal — correct |
| `mindsos_intelligence/mm_persister.py` | 12 | `knowledge_mm` still live-only; reword the reason (it is a core CR — dream PRE-6) |

### 2c. LEGITIMATE — WSD as a consumer/example. Leave alone.

| File | Line | Why it is fine |
|---|---|---|
| `mindsos_capacity/builtins/reduction_v0.py` | 35 | says reduction is *not* a WSD placeholder — the right distinction |
| `mindsos_capacity/identifiers.py` | 126 | same |
| `mindsos_capacity/family_rules.py` | 70 | names WSD as one of several *installing chats* — a consumer |
| `mindsos_intelligence/als_subsystems.py` | 18 | `"wsd-candidate-scorer"` is a genuine WSD-owned subsystem id |

---

## 3. How to make it stick for future chats

Four changes, cheapest first.

**(a) Fix the 16 docstrings in §2a.** A chat reads the file it is editing. This is
the only change that reaches a chat at the moment it would make the mistake.

**(b) Write an ADR.** `RULES.md` is a working agreement; ADRs are what chats are
pointed at for *why*. Proposed:

> **ADR-XXXX — Subsystems consume; they never own architecture.**
> *Context:* Phase-47 shipped placeholder catalogs and recorded their real bodies
> as "shipping in WSD installation." WSD is a Skill installed on the platform, not
> a layer of it. Multiple chats have since treated a missing core mechanism as
> blocked on a subsystem that has no obligation to build it.
> *Decision:* No `mindsos_*` module may name a subsystem (WSD, FOL, NLU, a demo,
> a brain) as the owner or delivery vehicle of a core mechanism. A placeholder
> records **what is missing** and **which core CR tracks it** — never who will
> ship it. Subsystems appear in core docs only as consumers or examples.
> *Consequence:* Any "ships in <subsystem>" comment is a defect. Placeholders name
> a CR instead.

**(c) Add one line to `CLAUDE.md`.** That is what a chat loads first:
> A subsystem (WSD, FOL, a brain, a demo) never owns a core mechanism. If core is
> missing something, core builds it. See `RULES.md` §8 + ADR-XXXX.

**(d) Make it mechanical.** A `catalog_check`-style test that fails when a
`mindsos_*` docstring matches `ships in <subsystem>` / `<subsystem> replaces` /
`<subsystem>-gated`, with an allowlist for the §2c sites. This is the only one of
the four that cannot be forgotten.

---

## 4. Recommended order

1. (c) — one line, zero risk, immediate effect.
2. (a) — 16 docstrings, mechanical, no behaviour change.
3. (b) — the ADR, so the *why* is citable.
4. (d) — the guard, once (a) is done so the allowlist is stable.

All four together are a `chore/` branch: docs + one test, no `mindsos_*` behaviour
change, so the gate result is attributable and the merge is trivial.
