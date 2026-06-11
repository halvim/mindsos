# Robot Demo — Motion State & Open Problems (as of 2026-06-08)

This is the canonical state of the `sim/` motion work. It supersedes any motion
notes elsewhere. Read this **plus the source files it names** before changing anything.

---

## 1. What exists right now

Six animations generate and render. Each is a JSON trajectory in `web/anim_<name>.json`
plus a GIF in `web/anim_<name>.gif`, built by the `combo_*` functions in `sim/motion.py`
(`run_all()` builds all six):

| name | what it does | placement metric |
|---|---|---|
| `a1_box`  | Arm 1 (suction) side-grasps a Box, shelves it | 6 mm |
| `a2_box`  | Arm 2 (jaw) side-grasps a Box, shelves it | 15 mm |
| `a1_sheet`| Arm 1 top-grasps the Panel, **rotates it upright**, side-inserts standing | 7 mm |
| `a2_tube` | Arm 2 side-grasps the Tube, places it upright | 5 mm |
| `a1_load` | Arm 1 drops Panel into a Box, shelves the Box (cargo contained) | gap 50 mm |
| `a2_load` | Arm 2 drops Tube into a Box, shelves the Box (cargo contained) | gap 8 mm |

**These metrics are misleading — see §3. The placements are numerically accurate but
the grasps are visually fake.**

Render path: no GL in the workspace, so use the software z-buffer renderer.
`sim/render_solid.py <name> <frame>` = one PNG; `sim/render_video.py <name> 0 16` then
`sim/render_video.py gif <name>` = the GIF; `sim/render_anim_frames.py <name>` = contact sheet.
The MuJoCo native viewer only runs on the user's Mac (`sim/view_local.py`).

---

## 2. Decisions locked in this chat (cargo geometry + layout)

Driven by the user; keep unless re-opened:

- **Tube** fattened to a ⌀70 mm × 70 mm cylinder (jaw-graspable, stable standing).
  Side-grasp + side-place **upright** (same face down as on the belt), like the box.
- **Sheet → wide flat Panel** (~92×88×20 mm). Rationale/story: both faces are wider than
  the 85 mm jaw opening, so only the **suction** arm can take it, **from the top**; it is
  then **rotated 90° to stand vertical** and side-inserted like a book. Still fits inside a
  Box (~96 mm interior) for `a1_load`.
- **Belt layout:** each arm's two items sit at **opposite ends** of its reachable belt
  segment — Box at the **outer** pickup (|x|=1.45), cargo at the **inner** staging (|x|=0.62).
  This spacing stops the arm sweeping across one item while reaching the other.
- Items **start resting on the belt** (z = `BELT_Z + half_height`), not floating.
- Universal placement rule: **every shelf placement is a side-hold horizontal insert**
  into the front of the cubby. Never a top-down drop into a shelf. "Top" is only ever a
  way to *pick up* (the panel).

Exact numbers live in `sim/geom_config.py` and `sim/build_cell.py` — do not transcribe
them here; read them there.

---

## 3. THE CORE PROBLEM (root cause of all three user complaints)

The belt sits **behind** the arms (rear hemisphere). The side-grasp is a strained
over-shoulder reach that **sags**: the gripper lands **0.1–0.5 m short** of the object
(worst on arm 2's long Robotiq jaw). The IK is *reachable* but the position servo cannot
*hold* the pose.

This sag has been **hidden, not fixed**, by **kinematic attach**: at grasp the object is
slaved to the tool at whatever offset it happens to have (`attach_tcp`), and for the tube
it is even teleported to a chosen offset (`snap_to_tcp` + `BOX_GRASP_OFF`) so the placement
comes out deterministic. The object then *follows* the tool but at a large visible gap.

The user's three complaints all trace to this one thing:

1. **Objects floating** — partly the carry phase: the held object rides at the offset, off
   the hand.
2. **Object not attached to the gripper when moving** — the offset gap; the grasp is faked.
3. **Arm not in the right position when placing** — the sag/offset; the tool is far from
   where the object lands.

**The real fix is to make the gripper actually reach the objects** — a real, controllable
grasp where the TCP sits *at* the object (small offset), so attach is cosmetic, not
load-bearing. That almost certainly means **revisiting the geometry** (the belt-behind-the-
arm layout is the source of the sag). This geometry rework was repeatedly deferred in this
chat. Candidate directions (not yet evaluated): bring the pickup into the arm's strong
**front** hemisphere, **lower** the belt, or otherwise place objects where the arm grasps
without sagging. Reach validation tooling already exists: `sim/reach_validate.py`
(`reachable()` does multi-start IK + the demo distinguishes *reachable* from *controllable*).

---

## 4. Key files (read these, don't guess)

- `sim/geom_config.py` — **single source of truth** for all geometry: floor/base/belt/shelf
  heights and positions, `base_quat()`, `shelf_cell()`, belt pick targets. Changing a number
  here changes both the scene and the reach-validation targets.
- `sim/build_cell.py` — `build_spec()` assembles the MjSpec scene: two Panda arms converted
  to stick-figures, arm-1 suction tip (`a1_cup` collidable + `a1_cup_vis` non-colliding
  visual, massless), arm-2 Robotiq jaw, belt + legs + feeder, per-arm 3×3 shelves, and the
  four free items via `_free_item` / `_container`.
- `sim/motion.py` — the `Cell` class and all motion:
  - **Attach model** (`_apply_attach`, kinds `world`/`tcp`/`rigid`/`body`): objects are
    kinematically slaved (qpos forced each step), NOT physically welded. `rigid` = tool-frame
    (object rotates with the wrist, used for the panel stand-up). `body` = containment
    (cargo rides inside a box).
  - **Grasps:** `grasp_side` (tool −y, contact-gated), `grasp_top` (tool −z, robust descent),
    `snap_to_tcp` (force a clean offset / upright), `pin` / `pin_loose` (freeze items).
  - **Placement:** `place_in_cell` (side insert; `stay=` pins a tippy object, `hh=` overrides
    seat height for the standing panel), `place_from_top` (unused dead-end), `load_into_box`.
  - **IK:** `solve` (`robust=` runs a servo-hold controllability filter — slow; used for
    strained reaches), `move_to`.
  - **Combos:** `combo_box` / `combo_tube` / `combo_sheet` / `combo_load`, `run_all`.
- `sim/reach_validate.py` — damped-least-squares IK with full-orientation target; `reachable()`.
- `sim/render_solid.py` / `render_video.py` / `render_anim_frames.py` — software rendering.

---

## 5. Quirks / traps the next chat MUST know

- **Knife-edge box grasp:** arm 2's box grasp folds to a large-but-*consistent* offset that
  places ~8–15 mm by luck; any tiny change (settle steps, a neighbour's position, item start
  height) flips it to 40–70 mm. Current mitigation: pin the box at its **initial** pose so the
  grasp is deterministic — a band-aid over the sag, not a fix.
- **Current animation recipe** (in every `combo_*`): `Cell()` → `pin_loose()` (pin all items
  at initial rest) → `step(20)` (arm stabilises, items frozen) → clear `frames`/`events` →
  grasp (detaches the active item's pin) → place. Pinning kills float, drift, knock-off, and
  the grasp-flip in one move; it depends on items starting at rest (§2) and on the spacing.
- **No GL** in the workspace sandbox — never try to render with MuJoCo/EGL; use the software
  renderer. Native MuJoCo viewer is Mac-only.
- **Git** `.git/index.lock` cannot be removed in the Cowork Linux sandbox; **the user runs all
  git commands on their Mac.** Stage only the files you intend; do not `git add -A`.
- The wider design context (scenario, contracts, prototype) is in the other `ROBOT_DEMO_*.md`
  files in `confirmation_docs/`; this file covers only the `sim/` motion build.

---

## 6. Recommended next-chat scope

**Fix ONE problem at a time, starting with the real grasp (§3), because #2 and #3 are the
same root cause.** Do not add more kinematic patches. Likely first concrete step: re-validate
where on (or off) the belt each arm can grasp an object **controllably** (TCP actually at the
object, < ~10 mm held error), then move the pickup there — i.e., the geometry decision that
keeps getting deferred. Only once the grasp is physically honest should attach become
cosmetic and the float/detach/position artifacts disappear together.
