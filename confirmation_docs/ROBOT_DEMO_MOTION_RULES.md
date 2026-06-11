# Robot Demo — Motion Planning Rules (always follow)

When building or fixing any pick-and-place animation in `sim/`, follow this exactly.
**The object is the master: plan the object's path first; the arm serves it.**

## Five invariants — all must hold, verify every time from the animation data
1. **Arm joints move smoothly** — no snaps / branch-jumps.
2. **Object moves smoothly** — no position jerks.
3. **Object path is monotonic** — always getting closer to the target cubby, never reversing.
4. **No arm part touches/passes through the conveyor.**
5. **The object never touches the arm or the conveyor** (only the gripping tool may contact it).

**Plus:** the tool tracks the object to the seat and **stops the moment the object is placed**
— no forward overshoot past the box — then retracts.

6. **Rest pose** — the arm's **start and end** (home/rest) pose must be clear of BOTH its rack
   and the conveyor, oriented **toward the conveyor** (a natural "ready to pick" pose). Never
   park the arm inside a structure. The unfold (rest → grasp) and the retract (place → rest)
   must reach that pose collision-free — note the retract travels back across to the conveyor
   side and must clear the rack, the just-placed object, and the conveyor.
   (This is a *rest-pose* choice; the arm stays mounted facing the rack so placement is still a
   front-hemisphere reach — do not re-mount the arm toward the conveyor.)

## Algorithm
1. **Plan the object path:** smooth + monotonic from grasp to the seat, **entering the cubby
   mouth cleanly** (don't cut a diagonal that clips the rack).
2. **Tool follows the object naturally**, rotating it as needed (e.g. the 180° turn so the
   gripped face ends at the mouth). The tool **tracks the object all the way to the seat** —
   the object is never moved by a scripted self-glide while the tool sits still (that reads as
   fake). Because the gripped face ends facing the mouth, the tool naturally **halts at the
   opening** when the object is seated — no overshoot.
3. **Track the arm along that natural path with joints changing as LITTLE as possible**
   — stay in one configuration, no branch jumps.
4. **Reconfigure the arm ONLY where the object would otherwise touch the arm**, and make it
   the **minimum joint movement** that clears — never a jump to a far branch.
5. A fully clean carry usually exists from **only one grasp configuration (one IK branch)**.
   So first **pick that branch** (simulate the natural carry for candidate branches; choose
   the one whose carry never hits the arm and needs the least reconfiguration), then
   **joint-lerp smoothly from home straight to it** (smooth unfold). Never reach the grasp
   with a Cartesian move from the folded home pose — that branch-switches and snaps.

## Return to home (same algorithm, run on the empty tool)
After the object is seated, the arm returns to the rest pose using the **same object-master
pattern**, now with the **end effector as the master** (there is no object):
1. **Short retract** — the empty tool first pulls back a little, straight out of the cubby, to
   clear the rack. This is a fixed small move, **not** the planned path; it exists so the
   planned path never has to solve exiting the rack.
2. **Plan the natural path** — a smooth path **from that post-retract pose to the rest pose**,
   chosen by how much the tool must reorient:
   - **Small reorientation → straight Cartesian path** (position lerp + orientation slerp).
   - **Large reorientation (e.g. the ~180° turn-around: placed facing the rack → rest facing
     the conveyor) → a joint-space swing** — the base joint sweeps the arm around. A straight
     Cartesian tool-line CANNOT realize a big in-place tool spin: IK branch-flips mid-path
     (verified — every rest-pose candidate flips), which snaps the arm. Interpolate in joint
     space instead (e.g. lerp back through the grasp pose, which sits over the belt clear of
     the rack, then on to rest). Its start is already clear of the cubby, so the path never
     cuts through the rack.
3. **Drive the end effector along that path** (the tool is the master).
4. **The other links follow** (warm IK for the Cartesian case; the joint-lerp already moves
   them together), joints changing as little as possible, **reconfiguring only where a link
   would otherwise collide** — so no part touches the rack or the conveyor at any point.
Either way **verify the chosen path is rack/conveyor-clear and smooth, and that the end pose
equals the start rest pose exactly.** Do **not** return by a blind joint-space lerp from the
placing pose *straight* to home (skipping the over-belt waypoint) — that branch-swings the
wrist/forearm through the rack.

## Honesty rule
If **no** grasp branch yields a fully clean carry for a cell, then invariant 1 (smooth) and
invariant 5 (no contact) genuinely conflict there — **flag it, don't hide it.**

## Collision-check caveat
The stick-figure arm geoms are **non-colliding** (`contype=0`), so MuJoCo's penetration query
reports nothing — collisions are **visual only**. You MUST check arm-link positions against
structure regions (rack, conveyor) **yourself**, and that check must include the **static start
and end poses**, not just the moving frames.

## Always
Drive the arm **kinematically** (set joint angles directly) — never the sagging position
servo. After generating, **measure all six invariants + the overshoot** from the saved
animation (moving frames AND the static rest poses) before claiming success.

## Amendments (2026-06-10 — the session that produced the full 46-clip set)

These extend (never replace) the rules above. Implementations live in `sim/motion.py`;
the executable checklist forms are `checklist()` / `checklist_convey()` in `sim/gen_all.py`.

a. **Rotation axis through the grasp point is legal object-mastering.** The object's
   POSE path is still planned first, but for a rigid grip the rotation may be about
   the grasp point (jaw pinch / cup contact) instead of the object centre — that is
   what a rigid grip physically does, and it minimises the wrist orbit
   (`carry_pivot`). The object rides its planned pose; the tool genuinely tracks it
   (no glue, no settle).
b. **Comfort-zone turns (plan B).** In-place tool reorientations (the a2 180°, the
   sheet 90° pitch) only track in the arm's strong front-hemisphere zone; carries
   route the turn through that zone (via waypoint) and reach the target by pure
   translations, which track everywhere.
c. **Backward-plan-and-replay.** Greedy warm IK is direction-asymmetric: a corridor
   that tracks one way may diverge the other way. When the forward direction fails,
   march the corridor in the trackable direction from a robust-solved end pose,
   RECORD the joint trajectory, and replay it (reversed) for the animation. Rules-
   compliant: joints smooth, tool tracks the planned object path (`combo_tube_pick`).
d. **Branch-aligned REST.** Solve the rest pose warm FROM the carry's own end branch.
   An independently-solved REST lands in a foreign branch and turns the go-home into
   a long cross-branch swing.
e. **Grip-face freedom.** Either face of a symmetric grip is legal; pick the one that
   keeps the wrist in reachable space (the sheet's NEAR face made an intractable
   insert trivial). Suction standoffs must use the VISUAL tip length
   (`SUCTION_TIP_LEN - SUCTION_LEN`), or the drawn cup pokes through thin objects.
f. **Checklist additions** (all data-driven): wrist/tool beyond the mouth plane only
   inside the TARGET cubby (any phase); overshoot vs the gripped face; object-vs-belt
   contact; rest pose faces the conveyor at both ends; reverse runs (`*_pick`) seat
   on the belt and use the `placed` event; load+convey runs use `checklist_convey`
   (items 1/2/4/6/7/9 + A exact delivery, B rigid ride, C cargo-inside-box,
   D swept-item collected, E no box-wall graze). Float is measured as object pose in
   the gripper's LOCAL frame.
g. **Guard rails.** `rest_pose` returning None must raise (a None silently written
   into qpos poisons the state with NaN and every later IK call saturates — it looks
   like "slow IK", not like an error). Event lookups must match labels exactly
   (titles can contain event words).

## Pre-present checklist (ALWAYS run before showing any animation)
Verify every item **from the saved animation data** (not by eye), across the moving frames AND
the static start/end poses. Never present an animation until all pass; if one can't pass, flag
it (see Honesty rule) instead of hiding it.

1. **Arm joints smooth** — no per-step jump / acceleration spike on any link (catches IK
   branch-flips).
2. **Object smooth** — no per-frame position jerk.
3. **Object monotonic** — during the carry the object always gets closer to the seat; never
   moves away.
4. **No arm part in the conveyor** — no link inside the conveyor body, any frame.
5. **No arm part in the rack** — checked separately for the PLACE phase and the RETURN phase.
   The only allowed rack-region entry is the wrist/tool placing into the target cubby;
   forearm/upper links must never enter, and the RETURN must be entirely rack-clear.
6. **Object never touches the arm or the conveyor** — only the gripping tool may contact it.
7. **Tool holds the object — no floating** — the tool/cup-to-object gap stays ≈ the grasp gap
   for the whole carry (no drift); the object is never separated from the cup, and at rest the
   object's bottom sits on the shelf floor in the correct cubby (not hovering).
8. **No overshoot** — the tool halts when the object is seated; no forward lunge past it.
9. **Rest pose start == end** — frame 0 and the final frame match on every link, and both are
   clear of the rack and conveyor, oriented toward the conveyor.
10. **Return path legal** — short retract out of the cubby, then the smooth path (Cartesian for
    a small reorientation, joint-space swing for a large one), verified rack/conveyor-clear.
