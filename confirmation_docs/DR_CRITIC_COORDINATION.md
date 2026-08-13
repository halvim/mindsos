# Decision Records — coordination file for the critic lane

**Purpose.** A second chat is being opened to answer one question the build lane
has failed to answer for itself:

> **How should this system be checked, so that gaps are found in one pass rather
> than one per phase?**

This file is the shared record between the two lanes. The build lane wrote §1–§6.
The critic lane writes §8. Neither lane deletes the other's text.

---

## 1. What is being built, and what is a demo of what

Three different things, and conflating them has already cost real work:

- **MindsOS** is the **architecture / platform** — eight `mindsos_*` packages,
  L0–L5. It is the product.
- **Decision Records** is an **application built ON TOP of MindsOS**. It is a
  consumer: it registers its own DataStates and capacities into a Local realm and
  drives them through core's own orchestration. Per RULES §3 it **never edits
  `mindsos_*`**; a core change lands on `main` first and the application merges
  the tag. Per RULES §8, any mechanism that belongs to MindsOS is **core**, even
  when Decision Records needs it first — so "the run manifest", "the terminal
  node", "origin records" are core components, not application code.
- **The Decision Records demo** is the **presentation artifact** — a live
  demonstration, with a fixed date, built out of the application above.

So: the demo demonstrates the application, and the application demonstrates the
architecture. A gap that only shows up in the demo is usually a gap in one of
the two layers under it, and that is where it must be fixed.

## 2. What the demo has to be able to do

A **Decision Record** is a page a non-technical reader can be shown, which
answers: *what was asked, what answered it, where that came from, and — when
nothing could be concluded — why not.*

The load-bearing constraint, from which everything else follows:

> **A Record is rendered from the run's grounding graph and NOTHING else.**

Not from the blackboard, not from the catalog at render time, not from anything
the renderer knows about the domain. If a fact is not in the graph, it cannot
appear on the page. This is what makes the Record evidence rather than prose.

The plan (`confirmation_docs/DECISION_RECORDS_V0_PLAN.md`) fixes **five runs** —
clean / value absent / no policy in force / unroutable / two dates — and guards
**G1–G8**, of which the ones that keep biting are:

- **G2** — a deleted producer must be distinguishable from a premise the run was
  given.
- **G6** — no MindsOS vocabulary and no IRIs reach the page.
- **G7** — the parentless values are exactly the declared starts.

## 3. Where the work actually stands

Shipped and gated (see the plan's §2.0 progress table for SHAs and counts):
origin records, the terminal node (`RunStopped`), the policy lookup + criterion,
the run driver through `execution.run`, `printable_phrase` on capacity
declarations, the run manifest, the structured-ingest reader, the origin-union
freeze, the refusal vocabulary, and (gating now) map-member manifests.

**Not built: the renderer.** Nothing in the system turns a graph into a page.
Every "gap" listed below is of the form *"the graph lacks X"* — discovered by
someone going looking, because nothing makes it visible.

**Also not built:** persistence of a Record through the orchestrator, and the
demo's own project home (`decision_records_demo/` on a `demo/*` branch).

## 4. The gap history — every gap, and how it was actually found

This is the evidence base for the question at the top. **Note the last column.**

| # | Gap | How it was found | Would a code-reading pass have found it? |
|---|---|---|---|
| 1 | Item 5's premise was false; run 2 was untested through four ships | running the fixtures | no — the code looked right |
| 2 | A local named `writer` shadowed a parameter, silently stripping `emit_step_execution_record` from every grounded run | whole-tree pre-filter, 31 failures | yes, if read closely |
| 3 | An `execute_pipeline` parameter added to prevent a double-mint prevented nothing | mutation — removing it reddened no test | no |
| 4 | `environment_fault` can never be `True`; both its reasons are on raising paths | classifying the union, then running the producers | yes |
| 5 | Three guards asserted over sets that could not contain the forbidden thing | mutation | yes |
| 6 | `source_unreachable` advertised on every record and recordable on none | classification | yes |
| 7 | **A map member's graph had no manifest at all** | **running a 3-member map and counting** | yes — sibling function, one had it, one didn't |
| 8 | An unroutable map member left no graph, and the abort destroyed the whole claim's Record | same run | yes |
| 9 | `runstopped:` / `runmanifest:` were IRI prefixes **no sub-MM owned** — the router raised `KeyError` on nodes inside a capacity graph | a guard reddening once the manifest moved | yes — prefix table vs IRI builders |
| 10 | **The fold leaves nothing in the grounding graph** — no manifest, no reducer instance, no conclusion node, no edge from the member verdicts to the conclusion. The claim-level answer is unrenderable | running a map+fold and dumping every graph | yes — `_run_fold_milestone` does not even take `mm` |

Two things this table says plainly:

1. **Every gap was surfaced by running the system**, never by re-reading it —
   but **most of them were reachable by reading**, if the reading had been
   pointed at the right question. The build lane's reading passes were not.
2. **They arrive one per phase.** Each costs a ~35-minute gate to confirm a
   ~20-minute implementation.

## 5. The process problem, stated without excuses

RULES §12 requires, after every ship, (1) a full check of the system and (2) a
re-evaluation of the plan. In practice the build lane has implemented "a full
check" as **one nominated surface per ship** — because that is what fits in a
ship, and because §12's own note says a check must not repeat the last one's
surface. The result is a **drip**: a new gap every phase, indefinitely, each
found *after* the thing it invalidates has already been built and gated.

By the build lane's own record, the first two §12 passes "re-read the same path
and found progressively less"; the third examined a surface nobody had looked at
and found more than both combined. That is a strong signal that **coverage of
surfaces, not depth on one surface, is the missing property** — but the build
lane has not designed a check that has coverage, and is not the right lane to
grade its own method.

There is a **fixed timeline** for the demo. The current rate of discovery does
not converge inside it.

## 6. Constraints any proposed method must live inside

- **Three machines.** Cowork edits files. The **Mac runs all git**. **Linux runs
  every test**, in docker, `--build` mandatory. The only bridge is the git
  remote — no shared filesystem.
- **The Linux gate is ~35 minutes** for the full suite (~4700 tests).
- **A whole-tree pre-filter runs in ~10 minutes** in the Cowork container on a
  tarball of the tree — this already catches essentially everything the gate
  catches, and its failure-name diff against a baseline tree has been exact.
- **Evidence standard, RULES §11:** the owner checks what the system produces,
  unaided. A claim about the system's state is a claim you have **read**, and a
  probe is never a capability. Output shown to the owner is raw system output,
  with any commentary labelled *above* it.
- **Guard standard, RULES §9:** a guard that has not been shown **RED by
  mutation** is not a guard. A mutation that reddens nothing is a finding.
- **The critic lane gets no worktree and no git.** Read the tree, run throwaway
  probes in its own sandbox, propose. Changes come back through the build lane.

## 7. What the critic lane is asked to produce

Not a list of bugs. **A method**, and the evidence that it would have worked:

1. **How should this system be checked** so that the gap list converges instead
   of dripping? Design it against §4's table: for each gap, say whether your
   method would have caught it, and at what cost.
2. **What should RULES §12 say instead?** It is the rule that produced the drip.
3. **What is the right build order from here**, given that the renderer is
   unbuilt and the timeline is fixed?
4. **Where are the claims-vs-code inconsistencies** between the plan, the ADRs,
   and the tree — as *questions that can be run*, not verdicts. A critic's claim
   is no more evidence than the build lane's (§11).

## 7.1 The build lane's own hypotheses — **do not read until §7 is answered**

Fenced deliberately. If you read these first they will anchor you, and the whole
point of a second lane is an independent view. Open this only after you have
written your own answer to §7, then attack these.

<details>
<summary>build lane hypotheses (open last)</summary>

- **H1.** The right instrument is an *execution* matrix, not a reading pass:
  every seam the demo traverses (leaf run, map member, fold, no-route, outage,
  refusal, replan, persist) × every claim the plan makes (renderable from the
  graph alone, G1–G8, one Record per exposure, a claim-level conclusion), each
  cell **run**, printing what the graph actually contains. Empty cells are the
  gap list.
- **H2.** The renderer is the gap detector and should be built next, not last.
  Probe D was a throwaway renderer and it found three gaps in one sitting; every
  gap since is of the form "the graph lacks X", which a page would have shown.
- **H3.** The 10-minute pre-filter should be the dev loop and the Linux gate a
  *ship* gate, with 2–3 fixes batched per gate.
- **H4.** §12 should require coverage of an enumerated surface list, with
  surfaces marked examined/unexamined, rather than "one new surface per ship".

</details>

## 8. Critic lane response

*(the critic lane writes here; the build lane replies inline underneath, and
neither deletes the other's text)*
