# Robot Demo — Current State (2026-06-10)

**Status: the animation set is COMPLETE and user-approved.** 46 clips, every one
verified against the full checklist (`confirmation_docs/ROBOT_DEMO_MOTION_RULES.md`,
including its 2026-06-10 Amendments section — read that file with this one).
This doc supersedes `A2_REDO_HANDOFF.md` (mission accomplished; kept for history).
Next planned work: **the demo UI** (web playback/index), not animation.

## 1. The 46-clip inventory (web/anim_*.json + web/gifs/*.gif, 1:1)

| set | clips | combo (sim/motion.py) | notes |
|---|---|---|---|
| a1 box places `a1_r*c*` | 8 (no r0c1) | `combo_box` classic carry | 5 float-FLAGged under the strict metric — see §4 |
| a2 box places `a2_r*c*` | 9 | `combo_box` pivot + via (plan B) | all PASS |
| a1 sheet places `a1_sheet_r*c*` | 9 | `combo_sheet` pivot, −90° pitch | all PASS |
| a1 sheet picks `a1_sheet_pick_r*c*` | 9 | `combo_sheet_pick` | all PASS (cubby→belt) |
| a2 tube picks `a2_tube_pick_r*c*` | 9 | `combo_tube_pick` backward-replay | 8 PASS; r0c1 FLAG (§4) |
| load+convey `a{1,2}_load_convey` | 2 | `combo_load_convey` | all PASS; wide-camera renders |

Deprecated legacy clips (a1_box, a2_box*, a1_sheet, a*_load, a2_tube, pick + 11
orphan jaw glbs) were **deleted by the user on 2026-06-10**.

## 2. Scene (sim/geom_config.py + sim/build_cell.py — comments there are current)

- sheet1 at x=−1.10 (relocated into a1's controllable band), box2 at +0.95, tube1 at +1.10.
- Belt SYMMETRIC: ±2.11; feeder (−x) and collector (+x) housings each 0.73 m from their arm.
  Both ends collect items the running belt sweeps into them.
- Viewer geometry export pipeline: `python3 build_cell.py --save` → `python3 export_gltf.py`
  (writes `sim/cell.xml`, `web/assets/*.glb`, `web/manifest.json`). Already current.
- `web/preview_offline.html` embeds PRE-collector geometry; regen via
  `sim/gen_offline_preview.py` if it is still wanted.

## 3. Generation / render operations (sandbox)

- `python3 gen_all.py <index> 1` — index map: 0–7 a1 boxes, 8–16 a2 boxes,
  17–25 sheet places, 26–34 sheet picks, 35–43 tube picks, 44–45 load_convey.
  Each run prints the checklist verdict to the LOG.
- **`LOG` in `gen_all.py` is SESSION-BOUND** (`/sessions/<session>/mnt/outputs/...`) —
  a fresh chat must repoint it first (one line). `render_all.py` OUT is repo-relative (fine).
- `python3 render_all.py <idx> <count>` — render idx map: 1–8 a1 boxes (0 was legacy
  a1_box, deleted), 9–17 a2 boxes, 18–26 sheet places, 27–35 sheet picks, 36–44 tube
  picks, 45–46 load_convey (wide camera). Budget: bash calls die at 45 s — 1 render
  per call for 100+ frame anims; the two wide load_convey renders exceed even that
  and are produced by a split half/half PNG pass + GIF assembly (see this chat's
  pattern or just re-derive: render frames range(0,N,5) into PNGs over two calls).
- Working style that produced this set: probe read-only first, propose, WAIT for
  user approval, one cubby/animation at a time, verify from data AND rendered GIF.

## 4. Open items

1. **a1 box classics float flags** — r1c1 64, r1c2 41, r2c0 86, r2c1 78, r2c2 100 mm
   under the strict gripper-local float metric (which postdates their user approval;
   they are the same approved trajectories). User has NOT re-judged. Either record a
   documented exception or redo (note: their pivot/yaw− alternatives were tried and
   are worse; the outer box pickup at −1.45 makes a pivot redo nontrivial).
2. **a2_tube_pick_r0c1** — FLAG, carry float 46 mm (limit 40), everything else clean.
   Bottom-center is the cell's documented intrinsic-limit cubby (box pick 76 mm there,
   sheet place needed the end-seed rescue). Accepted under the honesty rule.
3. **tube→cubby placement does not exist** — the deleted `a2_tube` was a scripted
   legacy demo and nothing replaced its action (current story: tube goes into the
   BOX). One-request job with today's machinery if the demo ever needs it.
4. **UI not built** — web/ has data + assets + `preview.html` (static scene seed,
   loads manifest + glbs) but no animation player/index for the 46 clips.

## 5. Pattern → implementation map (details in the rules doc Amendments)

- Pivot carry + comfort via: `Cell.carry_pivot` (+ `plan_override`, `end_seed`),
  `PIVOT_VIA_DEFAULT` in gen_all.
- Branch selection: robust-solve fast path + dry gate, `pick_grasp_branch`
  (`pivot`, `dry_plan_override`, `n_seeds`), re-dry from the branch actually chosen.
- Backward-plan-and-replay: `combo_tube_pick` (record traj, replay as approach
  forward and carry reversed).
- Branch-aligned REST: `make_rest` inside `combo_load_convey`, warm-IK rest in
  `combo_tube_pick`/`combo_sheet_pick`.
- Loading: a1 sheet standing insert via NEAR-face (+90°) pitch; a2 tube via SIDE
  grasp presented over the rim (top-down over box2's spot is unreachable: 47–130 mm
  sag — probed, do not retry).
