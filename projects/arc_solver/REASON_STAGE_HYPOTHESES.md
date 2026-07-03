# Reason-stage hypotheses — to analyze (parked)

**Status:** holding area · started 2026-06-18. Candidate reason-stage rules/heuristics raised
during design, to be analyzed against the ARC corpus later. **Nothing here is locked.**

---

## H1 — Background detection by correspondence residual (raised 2026-06-18, owner)

**Hypothesis (verbatim intent):** *"If all other shapes match on input and output, the shape
that doesn't match is the background."*
Reframed: **background = the object/shape with no cross-pair correspondent** — the residual left
after the foreground objects are matched input↔output.

**Where it would live:** Reason stage **3A (correspondence / background proposal)** — an
alternative to the shipped background detector.

**Shipped method (for contrast):** background = the **most-frequent color** per grid (a Color in
the `functional:background` role, derived per-grid, reasoning-time judgment; ONTOLOGY §2.1, §4 #3,
§4 #18 makes Background a derived `attribute`). Color-frequency based; works on a single grid with
no output.

### Pushback / analysis (2026-06-18) — **does not hold for #8**

Real #8 (`05f2a901`) data, every demo:
- objects = `O0` (color 0, area ~77–116, **irregular, large**), `O1` (color 2, irregular),
  `O2` (color 8, 2×2 **square**).
- across input→output: **`O0` (bg) is INVARIANT** (matches, `same_object`); `O2` invariant;
  **`O1` is the one that moves** (does NOT match by position).

So:
1. **The heuristic mislabels #8.** The object that "doesn't match" input↔output is the **mover**
   (`O1`), which is *foreground*. The actual background (`O0`) **does** match (it's the large
   invariant region). The rule would call the mover the background — backwards for #8.
2. **"Match" is ambiguous and the answer flips with the choice.** `same_object` (position-exact):
   the mover is the non-match → wrongly bg. `same_shape` (position-independent): in #8 *everything*
   matches → identifies nothing.
3. **It's a different *model* of background.** Shipped = a **Color role** by frequency, per-grid,
   single-grid-capable. This hypothesis is **correspondence-based** (needs the in→out pair) and
   **object/shape-level** — a different axis entirely.

### Useful kernel (keep, don't discard)
"Background = residual after foreground correspondence" is a legitimate **alternative detector**
for a *different task family*: textured/patterned backgrounds where the **foreground objects recur
(match)** and the background is the odd, non-recurring field. #8 is the opposite family (large
flat invariant background → frequency wins). Likely outcome after analysis: **an ensemble of
background detectors** (frequency · residual · others), reconciled per task — not one rule.

**To analyze:** bucket the 400 train tasks by which background detector agrees with the
human-evident background; measure where frequency vs residual wins; design the reconciliation.

---

## H2 — "no dim/palette delta + shapes invariant (except background) → moving" (raised 2026-06-18, owner)

**Hypothesis:** if **no DimensionDelta** AND **no PaletteDelta** AND all foreground shapes are the
same input↔output (**background excluded**) → the rule is a **move** (translation).

**Profile-as-filter framing (owner):** *"The profile phase will be a filtering feature… maybe
through paths in a graph."* — **This is correct, and it's `find_pipeline`.** An absent Delta means
the corresponding transform generator has **no input DataState to consume**, so `find_pipeline`
**cannot compose** any pipeline through it. The profile thus **prunes the transform-family search**
by which Deltas exist (resize CONSUMES a DimensionDelta; recolor CONSUMES a PaletteDelta → absent ⇒
unreachable). This is the mechanism to build for the whole profile phase.

**Fits #8 ✓** (unlike H1). Real #8: no dim delta, no palette delta, foreground shapes invariant by
`same_shape` (mover keeps its shape and only translates; target + bg invariant) → move. Matches the
solved rule.

### Pushback / refinements
1. **Profile *filters*, it does not *conclude* "moving."** No-dim + no-palette only **excludes**
   resize/recolor. It does not by itself confirm translation — the **induce-stage `moved` detector**
   does (it produces the move Transform). Two stages: profile prunes families → induce confirms the
   survivor. Honest form: *"→ not resize, not recolor; move then confirmed at induce."*
2. **Identity vs move.** "Shapes the same" includes the no-op (same shape AND same position). Need
   **≥1 displaced object** to separate moving from identity.
3. **Palette-as-set misses recolor-by-permutation.** A task swapping two *existing* colors keeps the
   palette **set** identical (no PaletteDelta) with shapes identical — yet it's a recolor, not a
   move. "No palette delta" therefore does **not** fully exclude recolor; per-object/per-cell color
   correspondence is needed to close this hole.
4. **Presupposes a solved background.** "Except the background" depends on background detection
   (H1) — itself unresolved/ensemble. H2 inherits H1's uncertainty.

### Kernel (keep — the real design target)
**Profile = a filter over transform families, realized as `find_pipeline` path-availability.**
Generalize H2 to: *each profile comparator's Delta (present/absent) gates its transform family's
composability.* H2 is one instance (no-dim+no-palette ⇒ resize/recolor pruned). Build the profile
phase as this gate, not as hand-coded if/then.

---

### ⚠ REFUTED 2026-06-21 — the `find_pipeline` framing above is wrong (D7 + D-A LOCKED)

The bolded claims in this section ("*This is correct, and it's `find_pipeline`*"; "*Profile = a
filter realized as `find_pipeline` path-availability*") **do not hold**. `find_pipeline`
(`mindsos_capacity/pipeline.py`) is a **type-static, value-blind** single-input BFS: comparators
always produce their Delta DataState (value `None` when no change), so the Delta type is never
topologically absent and BFS can never prune `resize`/`recolor` per-task. A live probe further
showed BFS composes *every* multi-input reason cap **unsoundly** (drops all-but-one input). The
correct mechanism is an **instance-level L3 eligibility predicate** over swept Delta values (D7),
with composition handled by a future conjunction/fold finder, **not** BFS path-availability (D-A).
The *kernel intuition* — profile prunes transform families by which Deltas exist — survives; only
the `find_pipeline` realization is rejected. See `PIPELINE_DECISIONS.md` D7 / D-A / §5.

<!-- Add further reason-stage hypotheses below as H3, H4, … -->

