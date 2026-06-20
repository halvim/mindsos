"""Batch-generate the 17 remaining cubby animations (Arm1 8 + Arm2 9), each via the
shelf-face object-master pattern, and run the 10-item pre-present checklist on each.
Writes anim_<name>.json into web/ and a results log. Long-running -> launch in background."""
import sys, os, json, traceback
import numpy as np, mujoco
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import motion as M, geom_config as G

WEB = os.path.join(HERE, "..", "web")
LOG = "/sessions/amazing-youthful-heisenberg/mnt/outputs/gen_results.txt"


def q2m(q):
    R = np.zeros(9); mujoco.mju_quat2Mat(R, np.array(q, float)); return R.reshape(3, 3)


def checklist(name, arm, kind="box"):
    """Run the 10-item checklist on web/anim_<name>.json. Returns (ok, summary, detail).
    kind: 'box' (carried upright, half-height 0.05) or 'sheet' (stood up; rests on its
    standing half-extent 0.044)."""
    d = json.load(open(os.path.join(WEB, f"anim_{name}.json")))
    bs = d["bodies"]; F = np.array(d["frames"]); N = len(F); P = F[:, :, :3]; Q = F[:, :, 3:7]
    box = ("box1" if arm == 1 else "box2") if kind in ("box", "box_pick") else \
          ("tube1" if kind in ("tube_pick", "tube_place") else "sheet1")
    oi = bs.index(box)
    pf = f"a{arm}_"
    links = [f"{pf}link{i}" for i in range(8)] + [f"{pf}attachment"]
    links = [l for l in links if l in bs]
    ev = {e["frame"]: e["label"] for e in d["events"]}
    gf = [f for f in ev if "grasp" in ev[f]]
    sf = [f for f in ev if "seated" in ev[f] or "placed" in ev[f]]
    if not gf or not sf:
        return False, "no grasp/seated event", {}
    gf, sf = gf[0], sf[0]
    ax = G.ARM1_X if arm == 1 else G.ARM2_X; m = 0.04
    def in_rack(p):
        return (ax - 1.5 * G.COL_DX - m < p[0] < ax + 1.5 * G.COL_DX + m and
                G.SHELF_Y_ARM[arm] - G.SHELF_DEPTH - m < p[1] < G.SHELF_Y_ARM[arm] + m and
                G.ROW_Z0 - 0.5 * G.ROW_DZ - m < p[2] < G.ROW_Z0 + 2.5 * G.ROW_DZ + m)
    upper = [f"{pf}link{i}" for i in range(6) if f"{pf}link{i}" in bs]
    # 5 rack: upper-arm links must never enter; return phase must be clear EXCEPT the
    # wrist/tool while still inside the TARGET cubby (the rules' legal pull-out: "short
    # retract out of the cubby, then..."). Non-target regions stay forbidden for all.
    rrow = int(name.split("_r")[-1].split("c")[0]); rcol = int(name.split("c")[-1])
    tcx = ax + (rcol - 1) * G.COL_DX; tcz = G.ROW_Z0 + rrow * G.ROW_DZ
    def in_target(p):
        return abs(p[0] - tcx) < G.COL_DX / 2 + 0.02 and abs(p[2] - tcz) < G.ROW_DZ / 2 + 0.02
    wrist = {f"{pf}link6", f"{pf}link7", f"{pf}attachment"}
    upl_place = sorted({nm for f in range(sf + 1) for nm in upper if in_rack(P[f, bs.index(nm)])})
    ret = sorted({nm for f in range(sf + 1, N) for nm in links
                  if in_rack(P[f, bs.index(nm)])
                  and not (nm in wrist and in_target(P[f, bs.index(nm)]))})
    # 4 conveyor body
    cy0, cy1 = G.BELT_Y - G.BELT_HALF_W - m, G.BELT_Y + G.BELT_HALF_W + m
    conv = sorted({nm for f in range(N) for nm in links
                   if G.BELT_X0 < P[f, bs.index(nm)][0] < G.BELT_X1 and cy0 < P[f, bs.index(nm)][1] < cy1
                   and 0.40 < P[f, bs.index(nm)][2] < 0.86})
    # 1/2 jerk
    qa = [bs.index(f"{pf}link{i}") for i in range(8) if f"{pf}link{i}" in bs]
    jr = max(max(float(np.linalg.norm((P[f + 1, ix] - P[f, ix]) - (P[f, ix] - P[f - 1, ix]))) for ix in qa)
             for f in range(1, N - 1))
    db = np.linalg.norm(np.diff(P[:, oi], axis=0), axis=1)
    # 3 monotonic
    seat = P[sf, oi]; away = int((np.diff(np.linalg.norm(P[:sf + 1, oi] - seat, axis=1)) > 0.003).sum())
    # 6 box vs upper arm
    lk = [bs.index(n) for n in upper]
    def segd(pt, a, b):
        ab = b - a; t = np.clip(np.dot(pt - a, ab) / (np.dot(ab, ab) + 1e-9), 0, 1)
        return np.linalg.norm(pt - (a + t * ab))
    m6 = min(min(segd(P[f, oi], P[f, lk[s]], P[f, lk[s + 1]]) for s in range(len(lk) - 1))
             for f in range(gf, sf + 1)) if len(lk) >= 2 else 9.9
    # 6b object vs RACK: while the object's centre is outside the TARGET column, its
    # rotating xy-corners must stay clear of the rack front plane (closed a hole: the
    # r0c2 neighbour-orbit grazed within 10mm and read as touching)
    if kind in ("box", "sheet", "tube_place", "box_pick"):
        hx = {"box": 0.060, "sheet": 0.046, "tube_place": 0.035, "box_pick": 0.060}[kind]
        hy = {"box": 0.050, "sheet": 0.046, "tube_place": 0.035, "box_pick": 0.050}[kind]
        cors = np.array([[sx * hx, sy * hy, 0] for sx in (-1, 1) for sy in (-1, 1)])
        objrack = 9.9
        for f in range(gf, sf + 1):
            if tcx - G.COL_DX / 2 < P[f, oi, 0] < tcx + G.COL_DX / 2:
                continue                                   # entering its own mouth is legal
            Rb = q2m(F[f, oi, 3:7])
            ymin = (P[f, oi] + cors @ Rb.T)[:, 1].min()
            objrack = min(objrack, ymin - G.SHELF_Y_ARM[arm])
    else:
        objrack = 9.9
    # 7 float: box pose IN THE GRIPPER FRAME (rotation-invariant -> constant if rigidly held),
    # measured over the carry but EXCLUDING the last 15% (the legitimate settle into the seat).
    grip = "a1_suction" if arm == 1 else "a2g_base"
    gi = bs.index(grip); Qg = F[:, gi, 3:7]
    n85 = gf + int(0.85 * (sf - gf))
    locs = np.array([q2m(Qg[f]).T @ (P[f, oi] - P[f, gi]) for f in range(gf, n85 + 1)])
    floatstd = float(np.linalg.norm(locs - locs[0], axis=1).max())   # max drift off the grip
    # seated: box bottom on the shelf floor (floor height depends on the cubby ROW)
    row = int(name.split("_r")[-1].split("c")[0])
    if kind in ("sheet_pick", "tube_pick", "box_pick"):   # reverse runs: rest ON THE BELT
        floor = G.BELT_Z
        box_hz = {"sheet_pick": 0.010, "tube_pick": 0.035, "box_pick": 0.05}[kind]
    else:
        floor = (G.ROW_Z0 + row * G.ROW_DZ) - 0.5 * G.ROW_DZ + 0.008
        box_hz = 0.05 if kind == "box" else (0.035 if kind == "tube_place" else 0.044)
    seatgap = (P[N - 1, oi, 2] - box_hz) - floor
    # 9 start==end
    se = max(float(np.linalg.norm(P[0, bs.index(n)] - P[N - 1, bs.index(n)])) for n in links)
    # placement xy accuracy
    cellxy = np.array([ax + 0, 0])  # not used; box xy err computed in combo
    checks = {
        "1_armjerk_mm": round(jr * 1000),
        "2_objjerk_mm": round(db.max() * 1000),
        "3_away": away,
        "4_conv": conv or "none",
        "5_rack_upper_place": upl_place or "none",
        "5_rack_return": ret or "none",
        "6_box_arm_mm": round(m6 * 1000),
        "6b_obj_rack_mm": (round(objrack * 1000) if objrack < 9 else "n/a"),
        "7_float_std_mm": round(floatstd * 1000),
        "7_seat_gap_mm": round(seatgap * 1000),
        "9_start_end_mm": round(se * 1000),
        "N": N,
    }
    # away<=5: a ride-held box follows the gripper's slightly-curved path, not a straight line,
    # so a few frames of small backward motion are fine when the box stays gripped (float held).
    # float<40: tolerates the last-cm settle leaking into the window.
    ok = (away <= 5 and not conv and not upl_place and not ret and m6 > 0.060
          and floatstd < 0.040 and abs(seatgap) < 0.015 and se < 0.010
          and jr < 0.160 and db.max() < 0.090 and objrack > 0.025)
    return ok, ("PASS" if ok else "FLAG"), checks



def checklist_convey(name, arm):
    """Applicable rules items for the load+convey anims (no cubby placement -> items
    3/5/8 are N/A): 1 arm smooth, 2 object smooth, 4 no conveyor-body intrusion,
    6 cargo vs upper links, 7 tool holds cargo (grasp..release), 9 rest start==end.
    Plus: A final box position == the other box's build position EXACTLY; B cargo-in-box
    relative pose constant during the slide."""
    d = json.load(open(os.path.join(WEB, f"anim_{name}.json")))
    bs = d["bodies"]; F = np.array(d["frames"]); N = len(F); P = F[:, :, :3]; Q = F[:, :, 3:7]
    cargo = "sheet1" if arm == 1 else "tube1"
    box = "box1" if arm == 1 else "box2"
    other_x = 0.95 if arm == 1 else -1.45                  # other box's build position
    oi = bs.index(cargo); bi = bs.index(box)
    pf = f"a{arm}_"
    links = [f"{pf}link{i}" for i in range(8) if f"{pf}link{i}" in bs] + [f"{pf}attachment"]
    links = [l for l in links if l in bs]
    ev = {e["frame"]: e["label"] for e in d["events"]}
    gf = [f for f in ev if "grasp" in ev[f]][0]
    rf = [f for f in ev if "release" in ev[f]][0]
    cv = [f for f in ev if ev[f] == "conveyor"][0]   # exact: the title mentions 'conveyor' too
    m = 0.04
    cy0, cy1 = G.BELT_Y - G.BELT_HALF_W - m, G.BELT_Y + G.BELT_HALF_W + m
    conv = sorted({nm for f in range(N) for nm in links
                   if G.BELT_X0 < P[f, bs.index(nm)][0] < G.BELT_X1
                   and cy0 < P[f, bs.index(nm)][1] < cy1 and 0.40 < P[f, bs.index(nm)][2] < 0.86})
    qa = [bs.index(f"{pf}link{i}") for i in range(8) if f"{pf}link{i}" in bs]
    jr = max(max(float(np.linalg.norm((P[f + 1, ix] - P[f, ix]) - (P[f, ix] - P[f - 1, ix]))) for ix in qa)
             for f in range(1, N - 1))
    db = np.linalg.norm(np.diff(P[:, oi], axis=0), axis=1)
    upper = [f"{pf}link{i}" for i in range(6) if f"{pf}link{i}" in bs]
    lk = [bs.index(n) for n in upper]
    def segd(pt, a, b):
        ab = b - a; t = np.clip(np.dot(pt - a, ab) / (np.dot(ab, ab) + 1e-9), 0, 1)
        return np.linalg.norm(pt - (a + t * ab))
    m6 = min(min(segd(P[f, oi], P[f, lk[s]], P[f, lk[s + 1]]) for s in range(len(lk) - 1))
             for f in range(gf, rf + 1)) if len(lk) >= 2 else 9.9
    grip = "a1_suction" if arm == 1 else "a2g_base"
    gi = bs.index(grip)
    locs = np.array([q2m(Q[f, gi]).T @ (P[f, oi] - P[f, gi]) for f in range(gf, rf + 1)])
    floatstd = float(np.linalg.norm(locs - locs[0], axis=1).max())
    se = max(float(np.linalg.norm(P[0, bs.index(n)] - P[N - 1, bs.index(n)])) for n in links)
    # A: exact final box position vs the other box's build position
    tgt = np.array([other_x, G.BELT_Y, G.BELT_Z + 0.05])
    poserr = float(np.linalg.norm(P[N - 1, bi] - tgt))
    # B: cargo rides the box rigidly during the slide
    rel = P[cv:, oi] - P[cv:, bi]
    ride = float(np.linalg.norm(rel - rel[0], axis=1).max())
    # C: cargo truly INSIDE the box at the end (footprint + below the rim), from data
    relf = P[N - 1, oi] - P[N - 1, bi]
    inside = bool(abs(relf[0]) < 0.045 and abs(relf[1]) < 0.045 and -0.05 < relf[2] < 0.03)
    # E: cargo never clips the box WALLS on approach (before release): whenever the
    # cargo's bottom is below the wall tops, its footprint must be fully inside the
    # interior (the tube once cut diagonally through two wall tops -> caught by eye)
    chx, chy, chz = (0.046, 0.010, 0.044) if arm == 1 else (0.035, 0.035, 0.035)
    graze = 0
    for f in range(gf, rf + 1):
        r3 = P[f, oi] - P[f, bi]
        if r3[2] - chz < 0.048:                          # bottom below wall top (+2mm slack)
            # per-wall slab overlap (cross-axis gated: cargo at its own pickup spot is
            # nowhere near the box and must not fire the y test)
            # 2mm penetration slack: the planned-pose ride carries the attach-time
            # tool residual (~3mm) as constant bias -> sub-2mm technical overlaps are
            # invisible noise; the check is for the 10-50mm graze class
            hit_x = (abs(r3[0]) + chx > 0.050 and abs(r3[0]) - chx < 0.062
                     and abs(r3[1]) - chy < 0.052)
            hit_y = (abs(r3[1]) + chy > 0.040 and abs(r3[1]) - chy < 0.052
                     and abs(r3[0]) - chx < 0.062)
            if hit_x or hit_y:
                graze += 1
    # D: the swept belt item rode the belt and was COLLECTED by the end housing
    swept = "tube1" if arm == 1 else "sheet1"
    si = bs.index(swept)
    hx = (G.BELT_X1 - 0.18) if arm == 1 else (G.BELT_X0 + 0.18)
    moved = abs(P[N - 1, si, 0] - P[cv, si, 0]) > 0.3
    collected = bool(abs(P[N - 1, si, 0] - hx) < 0.10 and moved)
    checks = {"1_armjerk_mm": round(jr * 1000), "2_objjerk_mm": round(db.max() * 1000),
              "4_conv": conv or "none", "6_cargo_arm_mm": round(m6 * 1000),
              "7_float_mm": round(floatstd * 1000), "9_start_end_mm": round(se * 1000),
              "A_final_pos_err_mm": round(poserr * 1000, 1), "B_ride_drift_mm": round(ride * 1000, 1),
              "C_cargo_inside": inside, "C_rel": [round(float(v), 3) for v in relf],
              "D_swept_collected": collected, "E_wall_graze_frames": graze,
              "na": "items 3/5/8 (cubby monotonic/rack/overshoot) N/A", "N": N}
    ok = (not conv and jr < 0.160 and db.max() < 0.090 and m6 > 0.060
          and floatstd < 0.040 and se < 0.010 and poserr < 0.005 and ride < 0.005
          and inside and collected and graze == 0)
    return ok, ("PASS" if ok else "FLAG"), checks


ALL = [(1, r, c, "box") for r in range(3) for c in range(3) if not (r == 0 and c == 1)]
ALL += [(2, r, c, "box") for r in range(3) for c in range(3)]
ALL += [(1, r, c, "sheet") for r in range(3) for c in range(3)]   # indices 17-25
ALL += [(1, r, c, "sheet_pick") for r in range(3) for c in range(3)]   # indices 26-34
ALL += [(2, r, c, "tube_pick") for r in range(3) for c in range(3)]    # indices 35-43
ALL += [(1, 0, 0, "load_convey"), (2, 0, 0, "load_convey")]            # indices 44-45
ALL += [(2, r, c, "tube_place") for r in range(3) for c in range(3)]   # indices 46-54
ALL += [(1, r, c, "box_pick") for r in range(3) for c in range(3)]    # indices 55-63

# neighbour-rotation override: (arm,r,c) -> (ref_r, ref_c) whose mouth to rotate at, then slide over
REF = {(1, 0, 2): (0, 1)}   # neighbour-rotate: turn at r0c1's mouth (clean +sweep,
# co-rotating like ALL siblings), then slide +x. RESTORED 2026-06-10: it is the ONLY
# r0c2 route matching the siblings' movement — probed exhaustively: natural branch
# counter-rotates (-109deg sweep, the user-visible defect), forced +sweep floats 229,
# pivot yaw+ blows the turn (344-452), yaw- mirrors the siblings. Costs the 18cm slide.
# per-cubby turn-direction override (some cubbies are smooth only turning the other way)
YAWNEG = set()   # ((2,1,0) was a ride-era override, dropped — plan-B pivot turns at the
                 # comfort zone where yaw+ is proven.)
# classic-carry escape hatch: cubbies where carry_master has no clean branch -> pivot carry.
# (a1 r1c1 probes: classic +180 float 64/jerk 183; -180 box-arm 39; pivot float 70 — none
# meet the NEW strict gripper-local float metric; the user-approved look is classic +180,
# which the old rotation-confounded float metric passed. Kept classic; flagged to the user.)
PIVOT_FORCE = set()
# classic-carry base-sweep override: (arm,r,c) -> +1/-1 monotonic base direction.
# a1_r0c2's picker chose the lone OPPOSITE-sweep branch (body -109deg vs +45..+103 on
# all siblings, counter-rotating against the +180 box turn -> user-visible mismatch);
# base_dir=+1 makes the dry-runs reject -sweep branches.
BASEDIR = {}     # (1,0,2)+1 forced co-rotation but the +sweep branch cannot TRACK the
                 # classic carry (float 229) -> r0c2 uses the pivot carry instead
# pivot comfort waypoint: ALL a2 carries do the 180 at (via_r,via_c)'s stage point (plan B —
# the outer/low cubbies are an IK dead zone for the turn; r1c1's spot is proven clean).
# Per-cubby override still possible via an explicit entry.
PIVOT_VIA_DEFAULT = (1, 1)
PIVOT_VIA = {}


def main():
    # argv: start_index [count]  -> run that slice of ALL (foreground; <45s budget per call)
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else len(ALL)
    cubbies = ALL[start:start + count]
    if start == 0:
        open(LOG, "w").write("batch start; %d cubbies total\n" % len(ALL))
    rownames = {0: "bottom", 1: "mid", 2: "top"}; colnames = {0: "left", 1: "center", 2: "right"}
    for (arm, r, c, kind) in cubbies:
        if kind == "sheet":
            name = f"a{arm}_sheet_r{r}c{c}"
            title = f"Arm {arm} stands a Sheet on shelf {arm} ({rownames[r]}-{colnames[c]})"
        elif kind == "sheet_pick":
            name = f"a{arm}_sheet_pick_r{r}c{c}"
            title = f"Arm {arm} returns the Sheet from shelf {arm} ({rownames[r]}-{colnames[c]}) to the conveyor"
        elif kind == "tube_pick":
            name = f"a{arm}_tube_pick_r{r}c{c}"
            title = f"Arm {arm} returns the Tube from shelf {arm} ({rownames[r]}-{colnames[c]}) to the conveyor"
        elif kind == "tube_place":
            name = f"a{arm}_tube_place_r{r}c{c}"
            title = f"Arm {arm} places a Tube on shelf {arm} ({rownames[r]}-{colnames[c]})"
        elif kind == "box_pick":
            name = f"a{arm}_box_pick_r{r}c{c}"
            title = f"Arm {arm} returns a Box from shelf {arm} ({rownames[r]}-{colnames[c]}) to the conveyor"
        elif kind == "load_convey":
            name = f"a{arm}_load_convey"
            cargo_n = "Sheet" if arm == 1 else "Tube"
            title = f"Arm {arm} loads the {cargo_n} into its Box; the conveyor delivers it across"
        else:
            name = f"a{arm}_r{r}c{c}"
            title = f"Arm {arm} places a Box on shelf {arm} ({rownames[r]}-{colnames[c]})"
        box = "box1" if arm == 1 else "box2"
        line = f"{name} (arm{arm} {rownames[r]}-{colnames[c]}): "
        yaw = -np.pi if (arm, r, c) in YAWNEG else np.pi   # +180 default; some cubbies need -180
        bdir = BASEDIR.get((arm, r, c), 0)
        ref = REF.get((arm, r, c))                        # neighbour-rotation override (hard cubbies)
        ref_cell = G.shelf_cell(arm, *ref) if ref else None
        pivot = (arm == 2) or (arm, r, c) in PIVOT_FORCE
        pv = PIVOT_VIA.get((arm, r, c), PIVOT_VIA_DEFAULT if pivot else None)
        pv_cell = G.shelf_cell(arm, *pv) if pv else None
        try:
            if kind == "sheet":
                M.combo_sheet(arm, "sheet1", G.shelf_cell(arm, r, c), name, title)
            elif kind == "sheet_pick":
                M.combo_sheet_pick(arm, "sheet1", G.shelf_cell(arm, r, c), name, title)
            elif kind == "tube_pick":
                M.combo_tube_pick(arm, "tube1", G.shelf_cell(arm, r, c), name, title)
            elif kind == "tube_place":
                M.combo_tube_place(arm, "tube1", G.shelf_cell(arm, r, c), name, title)
            elif kind == "box_pick":
                M.combo_box_pick(arm, "box1" if arm == 1 else "box2",
                                 G.shelf_cell(arm, r, c), name, title)
            elif kind == "load_convey":
                M.combo_load_convey(arm, "sheet1" if arm == 1 else "tube1",
                                    "box1" if arm == 1 else "box2", name, title)
            else:
                M.combo_box(arm, box, G.shelf_cell(arm, r, c), name, title, shelf_face=True,
                            yaw_total=yaw, ref_cell=ref_cell, ride=False, pivot=pivot,
                            pivot_via_cell=pv_cell, base_dir=bdir)
            if kind == "load_convey":
                ok, verdict, checks = checklist_convey(name, arm)
            else:
                ok, verdict, checks = checklist(name, arm, kind)
            line += verdict + " " + json.dumps(checks)
        except Exception as e:
            line += "ERROR " + repr(e) + " | " + traceback.format_exc().splitlines()[-1]
        with open(LOG, "a") as fh:
            fh.write(line + "\n")


if __name__ == "__main__":
    main()
