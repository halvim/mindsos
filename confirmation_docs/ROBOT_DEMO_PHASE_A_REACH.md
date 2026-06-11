# Robot Demo — Phase A: real-asset cell + P2 reach re-validation

**Status:** Phase A COMPLETE (2026-06-07, Cowork build chat). No MindsOS dependency.
**Companions:** `ROBOT_DEMO_PROTOTYPE_PLAN.md` (Phase A spec), `ROBOT_DEMO_SCENARIO.md` §5.2 (body-model / reach contract), `ROBOT_DEMO_OPEN_QUESTIONS.md` (P2).
**Artifacts (all under `sim/` + `web/`):** `sim/cell.xml` (self-contained), `sim/assets/` (75 meshes), `sim/{geom_config,build_cell,reach_validate,layout,export_gltf}.py`, `sim/reach_report.json`, `sim/layout.png`, `web/assets/*.glb` (37), `web/manifest.json`.

---

## What shipped

Replaced the stick-arm `prototype_zero/cell.xml` with the real-asset cell:

- **2× Franka Emika Panda** (mujoco_menagerie, vendored at `sim/menagerie/`), composed via the `MjSpec` API with prefixes (`a1_`, `a2_`) so two instances coexist without body-name collisions.
- **Asymmetric end-effectors:** Arm 1 = custom **suction tip** (cup geom + `a1_tcp` site, weld-on-contact in Phase B); Arm 2 = **Robotiq 2F-85** jaw (`a2_tcp` at the pinch site). 15 actuators total (7+7 arm + 1 gripper).
- **One continuous belt** with a red band marking the unreachable middle; **per-arm vertical 3×3 shelf racks**; cargo **Box / Sheet / Tube** as free bodies.
- Loads + settles stable (`max|qvel|≈0`), no arm/shelf penetration at the home keyframe, and **`cell.xml` reloads standalone**.

## P2 reach re-validation — method (not prototype_zero's 2D circle)

`prototype_zero/layout.py` modelled reach as a flat Euclidean circle (`REACH=0.62`). That is invalid for a 7-DOF Panda. `sim/reach_validate.py` instead tests **pose-reachability**: damped-least-squares IK to a position **+ tool-axis-alignment** target per cell (suction normal / jaw axis along the approach direction), with **multi-start seeding (HOME + 24 full-range restarts)**, **joint-limit** checks, and **penetration** checks against the shelf/belt.

Two invariants must hold for the cooperation to be real:
1. **Coverage** — each arm reaches all 9 of its own shelf cells (OPEN_QUESTIONS locks "no per-arm row-reach gate").
2. **Partition** — each arm reaches its own belt segment; the belt middle (`|x| < 0.28`) is reachable by **neither** arm.

## Result — PASS

```
Arm 1 (suction)  shelf 9/9   own belt PASS   gap unreachable PASS
Arm 2 (jaw)      shelf 9/9   own belt PASS   gap unreachable PASS
RESULT: GEOMETRY VALID — reach forces cooperation
```

## Findings that overrode the going-in assumptions

- **The predicted failure point was wrong.** The plan expected the *top shelf row at set-back distance* to be the out-of-reach risk. It was not. The real binding constraints were (a) the **gap wasn't forced at all** at the prototype_zero spacing — a real Panda reaches ~0.85 m, far past the 0.62 m stick-arm, so both arms reached the belt centre; and (b) the **shelf centre column** (straight ahead, low/mid rows) failed, not the top row.
- **Belt and shelf are on opposite sides of each arm**, so whichever way an arm faces, the other is in its rear/dead-cone hemisphere. **Resolution: mount each arm facing its shelf (−y).** The 3×3 rack then sits in the strong front hemisphere (fixes the centre column); the belt sits in the rear hemisphere but only needs **off-axis** working points (feeder pickup + inner staging), which clear the joint-1 dead cone.
- **Asymmetric EEs require per-arm rack depth** (confirms the pre-build pushback). The Robotiq adds ~0.145 m past the flange vs ~0.06 m for the suction tip, folding Arm 2 into a joint limit at the suction-arm depth. Arm 2's rack is set back further (`SHELF_Y = -0.99`) than Arm 1's (`-0.88`).
- **Belt picks at cargo-top height.** Targeting the belt surface let the short suction tip dip a link into the belt; picking at cargo-top (`BELT_Z + 0.09`) clears it.
- **Validator seed count is load-bearing.** A 7-DOF arm has many IK basins; under-seeding reported reachable cells as failures. 24 restarts removed the false negatives (verified against an 80-restart probe).

## Frozen geometry (single source of truth: `sim/geom_config.py`)

| Param | Value |
|---|---|
| Arm bases x | ±1.15 (y −0.45, z 0.40) |
| Base yaw | −90° (each arm faces its shelf, −y) |
| Belt | x ∈ [−1.55, 1.55], y −0.05, surface z 0.42 |
| Unreachable middle | \|x\| < 0.28 |
| Staging (box hand-off) | x ≈ ±0.45 |
| Shelf set-back (face y) | Arm 1 −0.88 · Arm 2 −0.99 |
| Shelf rows z | 0.46 / 0.63 / 0.80 (ROW_DZ 0.17) |
| Shelf cols Δx | 0.18 |

## Asset → glTF pipeline (browser rendering)

`sim/export_gltf.py` bakes each **body's** visual geometry (collision group skipped) into **body-local** coordinates (pose-invariant) and writes one `.glb` per body + `web/manifest.json` (`body → file, dynamic, home_xpos, home_xquat`). The server streams body transforms per frame; the browser sets each mesh group's transform. Reconstruction verified faithful against MuJoCo forward kinematics.

**Follow-up (not blocking):** total glb ≈ 16 MB — the Franka visual meshes are high-poly (~1 MB/link). Decimate for the browser in Phase D if first-load latency bites.

## How to run

```
pip install mujoco trimesh pygltflib
cd sim
python3 build_cell.py --save     # compile, settle-check, write cell.xml
python3 reach_validate.py --json # P2 validation -> reach_report.json
python3 layout.py                # schematic -> layout.png
python3 export_gltf.py           # web/assets/*.glb + web/manifest.json
```
