# Part 5 (5a) — same-type operand arity: ARC consumer spec

**Status:** draft 2026-07-07 · ARC-owned · docs-only, no code · gate untouched.
**Purpose.** The validated operand shape core must build **before** ARC decomposes the #8
monolith and routes comparators through `invoke`. ARC is the executing consumer of record
(supersedes the 2026-06-23 `composition-lifecycle-s2-part5` park; bongard-m3 is the same
binary shape and co-signs). Companion: `ATOM_TABLE.md`, `CORE_REQUESTS.md` (C1), `PIPELINE_DECISIONS.md` §5.

## The gap (one line)

`invoke` inputs are `Mapping[DS-IRI → value]`; two `object` operands collide on one key. Part 6
(shipped, `capacity._validate_inputs`) keys the same way. So no comparator can execute through
`invoke` until the contract can express **two operands of one DataState type**.

## Headline finding — core needs *positional* arity, not roles

Every one of the 14 caps is expressible with **positional slots** (`0..N-1`) of a single DS type.
The semantic distinction the asymmetric caps carry (from/to, source/target, contained/container,
in/out) is **read off the slot index inside the ARC body** and lives in ARC-local metadata. It
**never enters the core contract.** So:

- **Core Part 5 (5a) = ordered positional operands of one DS type.** Value-blind, role-name-blind.
- **Role semantics = ARC-side**, layered on the slot order.

This is the smallest core change that unblocks execution, and it keeps the finder untouched.

## The 14 caps — classified

Slot convention is ARC-local (the body's read order); core sees only "2 operands of type T".

| cap | operand DS | sym/asym | slot convention (ARC-local) | out |
|---|---|---|---|---|
| same_object | object | **sym** | — (equality) | bool |
| same_shape | shape | **sym** | — | bool |
| same_point | point | **sym** | — | bool |
| same_cell_count | shape | **sym** | — | bool |
| same_bbox_area | shape | **sym** | — | bool |
| touching | region | **sym** | — (unordered pair) | bool |
| union | object | **sym** | — (A∪B=B∪A) | region |
| compare_grid_dimension | grid | asym | 0=in, 1=out (`d=out−in`) | dimension_delta |
| compare_palette | grid/palette | asym | 0=in, 1=out (added/removed) | palette_delta |
| moved | object | asym | 0=from, 1=to (`Δ=b−a`) | move_transform |
| inset | object | asym | 0=contained, 1=container (`a⊆b`) | bool |
| recolored | object | asym | 0=from, 1=to (`from:a,to:b`) | recolor_transform |
| rotated | shape | asym | 0=source, 1=target | rotate_transform |
| reflected | shape | asym | 0=source, 1=target | reflect_transform |

7 symmetric, 7 asymmetric. Symmetric bodies are order-invariant (ARC's responsibility). Asymmetric
bodies fix slot 0 vs slot 1 — a **positional** distinction core supplies; the *names* are ARC's.

## Proposed contract — two forms; **B recommended**

**Form A — parallel positional API.** CONSUMES gains an ordered operand list; a new
`invoke(cap, operands=[...])` path validates arity + per-slot type. Body signature changes to
`(operands, context)`. Cost: a second invoke path + a second body signature everywhere.

**Form B — list-valued single key + arity (recommended).** Reuse the existing
`Mapping[DS-IRI → value]` path; let one key hold an **ordered list** under an
`operand_arity=N` declaration:

```
# register
declaration.operand_arity = {DS_OBJECT: 2}     # additive field; default 1 = today's behaviour
# invoke  (unchanged Mapping path)
invoke(moved, {DS_OBJECT: [obj_from, obj_to]}, context=ctx)
# Part 6 gains one check: if operand_arity[k]=N, inputs[k] must be a length-N list.
# body (unchanged **inputs signature)
def moved(**inputs, context): a, b = inputs[DS_OBJECT]; ...
```

Form B is the smaller delta: no new invoke API, no body-signature change (`**inputs` stays),
one additive `operand_arity` field, one added branch in `_validate_inputs`. Different-type
multi-input caps and `input_group` are untouched in both forms. The paper rewrites below use
Form B.

## Scope fences

- **Finder stays role-blind / type-level.** L4 supplies *which* two operands at dispatch (the
  correspondence/pairing is an L4 decision — see C4 group→pair). The finder composes on DS type
  only; it never threads operand order. So 5a touches the **registration + invoke** contracts, not
  `ConjunctionFinder`/`find_pipeline`.
- **No fold (5b) here.** No ARC cap consumes N-of-one-type under a single logical role. Group
  inputs (`objects*`) are one typed DS via C4 → a normal binary CONSUMES edge, not operand arity.
  (bongard-m5's fold is the 5b axis and is out of this spec's scope.)
- **C4 is the pairing seam, not 5a.** L4 unpacks a group (`objects*`), picks a pair, then invokes
  the comparator with two positional operands. C4 types the group; 5a expresses the arity.
- **`touching` is the one edge case — cross-kind operands.** Its body runs on Object×Object,
  Object×Point, Point×Point (anything with `cells`); the atom table types both operands as
  `region`. MindsOS DS types are flat (no subtyping), so an `arc.object` value won't satisfy a
  per-slot `region` type check. **Resolution is ARC-side, not core:** L4 wraps the object/point as
  a `region` view (both already carry `cells`) at the bind step, consistent with "binding is
  L4/ARC-local." Core keeps single-type-per-slot; no subtype machinery. Flagged so the family
  re-registration handles it explicitly.

## Decision cap worked through — proves 5a is comparator-only

`build_correspondence: same_objects*, move_transforms*, same_points* → correspondence`. Three
inputs, **different DS types**, each a C4 group. This registers today as `input_group=all_required`
over three DS-IRI keys (Part 6, shipped) + C4 group typing. **No same-type operand → no 5a.** The
same holds for `emit_candidates`/`select_rules`/`apply_solution` (all different-type multi-input).
So 5a's blast radius is exactly the **14 same-type-operand caps** — the set is defined by operand
*shape*, not category (it spans profilers, comparators, predicates `touching`/`inset`, and the
operator `union`).

## Paper rewrite 1 — symmetric (`same_object`), Form B

```
# register
operand_arity = {DS_OBJECT: 2}   ->  PRODUCES DS_SAME_OBJECT
# body (unchanged **inputs; order-invariant)
def same_object(**inputs, context):
    a, b = inputs[DS_OBJECT]
    return {DS_SAME_OBJECT: a["color"] == b["color"] and a["cells"] == b["cells"]}
# invoke (L4 picked the pair from objects* in L5)
invoke(same_object, {DS_OBJECT: [o_i, o_j]}, context=ctx)
```

Clean. Part 6 checks `len(inputs[DS_OBJECT]) == 2`. Symmetry is the body's business.

## Paper rewrite 2 — asymmetric (`moved`), Form B

```
# register  (from/to is a DOCSTRING, not a core field)
operand_arity = {DS_OBJECT: 2}   ->  PRODUCES DS_MOVE_TRANSFORM
# body reads list order = ARC's from/to convention
def moved(**inputs, context):
    a, b = inputs[DS_OBJECT]      # 0=from, 1=to
    if a["color"] != b["color"]: return {DS_MOVE_TRANSFORM: None}
    ... Δ = b.bbox - a.bbox ...
    return {DS_MOVE_TRANSFORM: {"kind": "translate", "vector": [dr, dc]}}
# invoke — L4's correspondence decided which object is from vs to
invoke(moved, {DS_OBJECT: [o_from, o_to]}, context=ctx)
```

Clean. Core supplies an *ordered list*; ARC's from/to meaning rides index 0/1. Core never learns
"from"/"to". Confirms the headline: **positional in core, roles ARC-local.**

## What core must build (the ask — Form B)

1. An additive `operand_arity: {DS-IRI → N}` field on the registration contract (default 1 =
   today). No role/label field.
2. One added branch in `capacity._validate_inputs`: if `operand_arity[k]=N`, `inputs[k]` must be a
   length-N list of type-`k` values. `**inputs` body signature and the DS-IRI-keyed invoke path
   are otherwise unchanged.
3. Finder/`find_pipeline` untouched (type-level; role-blind).

Form A (parallel positional API) remains on the table if core prefers it, but B is the smaller,
lower-risk delta and is what the rewrites assume.

## Handshake to the CORE chat

- ARC = executing consumer of record; this operand shape is validated against all 14 real bodies.
- Design gate cleared: **positional suffices for 14/14** — no cap needs core to know the role.
- After 5a + C4 ship, ARC reopens D3 (decompose the monolith), registers the family with real
  arity, and routes through `invoke`. ARC blocks on 5a; the CORE chat does not block on ARC beyond
  this spec.
