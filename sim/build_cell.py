"""Build the Open-Order cell as a MuJoCo MjSpec and compile it.

Composes two real Franka Panda arms (via mujoco_menagerie, vendored under
sim/menagerie/) with asymmetric end-effectors:
  Arm 1 (left)  : custom suction tip   -> site a1_tcp
  Arm 2 (right) : Robotiq 2F-85 jaw    -> site a2_tcp

plus the cell: floor, pedestals, one continuous belt with an unreachable middle,
a per-arm vertical 3x3 shelf rack, and cargo (Box carrier / Sheet / Tube).

Geometry comes entirely from geom_config.py so reach re-tuning is one-file.

Usage:
  python3 build_cell.py            # compile + stability check
  python3 build_cell.py --save     # also write sim/cell.xml (vendored, self-contained)
"""
from __future__ import annotations
import os, sys, numpy as np, mujoco
import geom_config as G

HERE = os.path.dirname(os.path.abspath(__file__))
MEN = os.path.join(HERE, "menagerie")

PANDA = os.path.join(MEN, "franka_emika_panda", "panda_nohand.xml")
ROBOTIQ = os.path.join(MEN, "robotiq_2f85", "2f85.xml")

HOME = [0, 0, 0, -1.57079, 0, 1.57079, -0.7853]   # panda home keyframe qpos

SHORT_JAW = False   # arm 2 EE: True = custom short jaw (reach-margin experiment — removes
                    # the bottom-cubby collision but does NOT fix mid/bottom droop, so off);
                    # False = original Robotiq 2f85.


def _box(parent, name, pos, size, rgba, contype=1):
    g = parent.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=pos, size=size, rgba=rgba)
    g.name = name
    if contype == 0:
        g.contype = 0; g.conaffinity = 0
    return g


def _add_shelf(wb, arm: int, ax: float):
    """A vertical 3x3 cubby rack at SHELF_Y facing +y, centred on x=ax."""
    tag = "L" if arm == 1 else "R"
    rgba = [0.30, 0.55, 0.85, 1] if arm == 1 else [0.85, 0.50, 0.25, 1]
    panel_rgba = [c * 0.6 for c in rgba[:3]] + [1]
    x0 = ax - 1.5 * G.COL_DX
    x1 = ax + 1.5 * G.COL_DX
    z0 = G.ROW_Z0 - 0.5 * G.ROW_DZ
    z1 = G.ROW_Z0 + 2.5 * G.ROW_DZ
    yc = G.SHELF_Y_ARM[arm]
    yb = yc - G.SHELF_DEPTH                              # back panel plane
    t = 0.008                                            # panel half-thickness
    body = wb.add_body(name=f"shelf_{tag}")
    # back panel
    _box(body, f"shelf_{tag}_back", [ax, yb, (z0 + z1) / 2],
         [(x1 - x0) / 2, t, (z1 - z0) / 2], panel_rgba)
    # 4 horizontal shelves (z dividers)
    for i in range(4):
        z = z0 + i * G.ROW_DZ
        _box(body, f"shelf_{tag}_h{i}", [ax, (yc + yb) / 2, z],
             [(x1 - x0) / 2, G.SHELF_DEPTH / 2, t], rgba)
    # 4 vertical dividers (x dividers)
    for j in range(4):
        x = x0 + j * G.COL_DX
        _box(body, f"shelf_{tag}_v{j}", [x, (yc + yb) / 2, (z0 + z1) / 2],
             [t, G.SHELF_DEPTH / 2, (z1 - z0) / 2], rgba)
    # support posts from the floor up to the rack bottom
    if z0 > G.FLOOR_Z + 0.02:
        for j, x in enumerate((x0 + 0.02, x1 - 0.02)):
            _box(body, f"shelf_{tag}_post{j}", [x, yb + 0.02, (G.FLOOR_Z + z0) / 2],
                 [0.02, 0.02, (z0 - G.FLOOR_Z) / 2], panel_rgba)
    return body


# --- container geometry (open-top Box; carries cargo) -----------------------
BOX_HX, BOX_HY, BOX_HZ = 0.060, 0.050, 0.050   # outer half-extents
BOX_T = 0.006                                   # wall thickness (half)
BOX_RGBA = [0.82, 0.66, 0.28, 1]


def _container(wb, name, x):
    """Open-top Box: floor + 4 walls, no lid, so cargo drops in from the top and
    rides along as long as the box stays upright (no pitch/roll)."""
    b = wb.add_body(name=name, pos=[x, G.BELT_Y, G.BELT_Z + BOX_HZ])
    b.add_freejoint()
    def g(gn, pos, size, mass):
        gm = b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=pos, size=size,
                        rgba=BOX_RGBA, mass=mass)
        gm.name = gn
    g(f"{name}_floor", [0, 0, -BOX_HZ + BOX_T], [BOX_HX, BOX_HY, BOX_T], 0.06)
    g(f"{name}_wpy", [0, BOX_HY - BOX_T, 0], [BOX_HX, BOX_T, BOX_HZ], 0.03)
    g(f"{name}_wmy", [0, -BOX_HY + BOX_T, 0], [BOX_HX, BOX_T, BOX_HZ], 0.03)
    g(f"{name}_wpx", [BOX_HX - BOX_T, 0, 0], [BOX_T, BOX_HY - BOX_T, BOX_HZ], 0.03)
    g(f"{name}_wmx", [-BOX_HX + BOX_T, 0, 0], [BOX_T, BOX_HY - BOX_T, BOX_HZ], 0.03)
    return b


def _free_item(wb, name, x, kind):
    if kind == "box":
        return _container(wb, name, x)
    # start each item RESTING on the belt (bottom at BELT_Z) so it can be pinned in
    # place immediately, with no settle drop (which floats the opening frames and
    # micro-shifts the box into a bad grasp pose).
    half_z = {"sheet": 0.010, "tube": 0.035}[kind]
    b = wb.add_body(name=name, pos=[x, G.BELT_Y, G.BELT_Z + half_z])
    b.add_freejoint()
    if kind == "sheet":     # wide flat PANEL: both faces are wider than the jaw can
        # open (85mm), so only the suction arm can take it — from the top. Still fits
        # inside a Box (interior ~96mm) for the load animation. Stands up when rotated.
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.046, 0.044, 0.010],
                   rgba=[0.40, 0.75, 0.45, 1], mass=0.08)
    elif kind == "tube":    # jaw-only cargo (fits inside a Box); wide enough that the
        # jaw contacts it despite the rear-reach sag, and stable standing upright
        b.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[0.035, 0.035, 0],
                   rgba=[0.70, 0.35, 0.55, 1], mass=0.09)
    return b


def _hide_mesh_visuals(spec):
    """Make the mesh visual geoms invisible (alpha 0) + group 3, so only the
    stick-figure primitives render. Kinematics/collision are untouched."""
    for b in spec.bodies:
        for g in b.geoms:
            if g.type == mujoco.mjtGeom.mjGEOM_MESH and g.contype == 0:
                g.rgba = [0.5, 0.5, 0.5, 0.0]
                g.material = ""
                g.group = 3


def _stick_panda(spec, rgba):
    """Replace the Panda's visual meshes with capsule links + joint spheres along
    its exact kinematic chain. Identical kinematics; always-solid visuals."""
    _hide_mesh_visuals(spec)
    for b in spec.bodies:
        if b.name == "world":
            continue
        sph = b.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, pos=[0, 0, 0],
                         size=[0.046, 0, 0], rgba=rgba)
        sph.contype = 0; sph.conaffinity = 0; sph.group = 2
        sph.name = f"stk_{b.name}_j"
        for c in b.bodies:                       # capsule to each child link
            L = float(np.linalg.norm(c.pos))
            if L > 0.03:
                cap = b.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                                 fromto=[0, 0, 0, c.pos[0], c.pos[1], c.pos[2]],
                                 size=[0.034, 0, 0], rgba=rgba)
                cap.contype = 0; cap.conaffinity = 0; cap.group = 2
                cap.name = f"stk_{b.name}_{c.name}"


def _stick_gripper(spec, prefix, rgba):
    """Stick-figure the attached Robotiq: hide its meshes, add a base block and
    two finger blocks on the pad bodies (so it reads as a 2-finger jaw)."""
    for b in spec.bodies:
        if not b.name.startswith(prefix):
            continue
        for g in b.geoms:
            if g.type == mujoco.mjtGeom.mjGEOM_MESH:
                g.rgba = [0.5, 0.5, 0.5, 0.0]; g.material = ""; g.group = 3
        if b.name == f"{prefix}base":
            gm = b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0, 0, 0.04],
                            size=[0.04, 0.018, 0.04], rgba=rgba)
            gm.contype = 0; gm.conaffinity = 0; gm.group = 2; gm.name = f"stk_{prefix}base"
        if b.name.endswith("silicone_pad"):
            gm = b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0, -0.004, 0.02],
                            size=[0.012, 0.006, 0.022], rgba=rgba)
            gm.contype = 0; gm.conaffinity = 0; gm.group = 2; gm.name = f"stk_{b.name}"


# stick-figure arm colours
ARM1_RGBA = [0.30, 0.55, 0.85, 1]
ARM2_RGBA = [0.85, 0.50, 0.25, 1]


def build_spec() -> mujoco.MjSpec:
    panda = mujoco.MjSpec.from_file(PANDA)
    panda2 = mujoco.MjSpec.from_file(PANDA)
    robotiq = mujoco.MjSpec.from_file(ROBOTIQ)
    _stick_panda(panda, ARM1_RGBA)
    _stick_panda(panda2, ARM2_RGBA)

    s = mujoco.MjSpec()
    s.modelname = "open_order_cell"
    s.copy_during_attach = True
    s.meshdir = "assets"          # all panda + robotiq meshes consolidated here
    s.option.timestep = 0.002
    s.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST

    # materials
    grid = s.add_texture(name="grid", type=mujoco.mjtTexture.mjTEXTURE_2D,
                         builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                         rgb1=[0.85, 0.85, 0.85], rgb2=[0.70, 0.70, 0.70],
                         width=300, height=300)
    s.add_material(name="grid", textures=["", "grid"], texrepeat=[8, 8], reflectance=0.1)
    s.add_material(name="belt", rgba=[0.05, 0.05, 0.06, 1])      # near-black conveyor top
    s.add_material(name="steel", rgba=[0.30, 0.30, 0.32, 1])

    wb = s.worldbody
    wb.add_light(name="key", pos=[0, -1, 2.5], dir=[0, 0.4, -1], diffuse=[0.7, 0.7, 0.7])
    floor = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, pos=[0, 0, G.FLOOR_Z],
                        size=[4, 4, 0.1], material="grid")
    floor.name = "floor"

    # arm sits ON the floor (floor = base height); just a thin mounting plate
    for nm, ax in [("base1", G.ARM1_X), ("base2", G.ARM2_X)]:
        p = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                        pos=[ax, G.BASE_Y, G.FLOOR_Z + 0.008],
                        size=[0.12, 0.12, 0.008], material="steel")
        p.name = nm

    # solid conveyor base: a full-length housing from the floor up to the belt underside,
    # so it reads as an industrial conveyor body (not a table on legs). Visual only — the
    # belt surface geom below handles item contact; the base sits clear of the arms (y).
    base_bot, base_top = G.FLOOR_Z, G.BELT_Z - 0.04
    base_cx = (G.BELT_X0 + G.BELT_X1) / 2
    base_hw = (G.BELT_X1 - G.BELT_X0) / 2
    base = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                       pos=[base_cx, G.BELT_Y, (base_bot + base_top) / 2],
                       size=[base_hw, G.BELT_HALF_W, (base_top - base_bot) / 2], material="steel")
    base.name = "belt_base"; base.contype = 0; base.conaffinity = 0

    # belt: one continuous surface (red middle band drawn as a separate geom)
    bx_c = (G.BELT_X0 + G.BELT_X1) / 2
    bx_hw = (G.BELT_X1 - G.BELT_X0) / 2
    belt = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                       pos=[bx_c, G.BELT_Y, G.BELT_Z - 0.02],
                       size=[bx_hw, G.BELT_HALF_W, 0.02], material="belt")
    belt.name = "belt"
    band = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                       pos=[0.0, G.BELT_Y, G.BELT_Z + 0.001],
                       size=[G.GAP_HALF, G.BELT_HALF_W, 0.001],
                       rgba=[0.80, 0.15, 0.15, 0.5])
    band.name = "belt_gap_band"
    band.contype = 0; band.conaffinity = 0
    # feeder chute marker (visual only) at the conveyor's upstream end, clear of
    # the pickup zone so it never sits next to / blocks the box
    # in-feed housing at the upstream end: wide enough (along the belt) that the first
    # item sits partly inside its mouth, as if fed out of it.
    ch = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                     pos=[G.BELT_X0 + 0.18, G.BELT_Y, G.BELT_Z + 0.10],
                     size=[0.18, G.BELT_HALF_W, 0.13], material="steel")   # in-feed sitting on the
    # belt's extended -x end (its back face flush with the belt end); downstream face ~ -1.75,
    # well clear of the arm's pick zone (box1 at -1.45)
    ch.name = "feeder"
    ch.contype = 0; ch.conaffinity = 0
    # COLLECTOR housing at the downstream (+x) end, mirroring the feeder: when the
    # conveyor runs, items reaching the end slide into its mouth (collected) instead
    # of falling off. The feeder doubles as the collector for -x travel.
    co = wb.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX,
                     pos=[G.BELT_X1 - 0.18, G.BELT_Y, G.BELT_Z + 0.10],
                     size=[0.18, G.BELT_HALF_W, 0.13], material="steel")
    co.name = "collector"
    co.contype = 0; co.conaffinity = 0

    # arms (mounted facing their shelves; see geom_config.base_quat)
    q = G.base_quat()
    f1 = wb.add_frame(pos=list(G.ARM1_BASE), quat=q)
    s.attach(panda, prefix="a1_", frame=f1)
    f2 = wb.add_frame(pos=list(G.ARM2_BASE), quat=q)
    s.attach(panda2, prefix="a2_", frame=f2)

    # Arm 1 suction tip on attachment body
    a1_att = s.body("a1_attachment")
    tip = a1_att.add_body(name="a1_suction")
    # short COLLIDABLE cup (preserves the grasp offset → clean placement)
    tg = tip.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                      pos=[0, 0, G.SUCTION_LEN / 2],
                      size=[G.SUCTION_CUP_R, G.SUCTION_LEN / 2, 0],
                      rgba=[0.20, 0.50, 0.85, 1], mass=0.05)
    tg.name = "a1_cup"
    # non-colliding VISUAL extension so the cup visibly reaches the box (cosmetic only)
    tv = tip.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER,
                      pos=[0, 0, G.SUCTION_TIP_LEN / 2],
                      size=[G.SUCTION_CUP_R, G.SUCTION_TIP_LEN / 2, 0],
                      rgba=[0.20, 0.50, 0.85, 1], mass=0.0)
    tv.name = "a1_cup_vis"; tv.contype = 0; tv.conaffinity = 0
    tip.add_site(name="a1_tcp", pos=[0, 0, G.SUCTION_LEN], size=[0.008, 0, 0],
                 rgba=[1, 1, 0, 1])

    # Arm 2 end-effector
    if SHORT_JAW:
        # Custom SHORT 2-finger jaw built directly on the flange (like arm 1's suction
        # tip), replacing the long 0.145 m Robotiq 2f85 to recover arm-2 reach margin.
        # Body kept named "a2g_base" so the grip detection + weld declarations downstream
        # are unchanged. Fingers are collidable so the contact gate still fires.
        a2_att = s.body("a2_attachment")
        jaw = a2_att.add_body(name="a2g_base")
        L = G.SHORT_JAW_LEN
        blk = jaw.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0, 0, L * 0.30],
                           size=[0.035, 0.018, L * 0.30], rgba=ARM2_RGBA, mass=0.04)
        blk.name = "a2g_block"; blk.contype = 0; blk.conaffinity = 0; blk.group = 2
        for sgn, nm in ((+1, "a2g_fingerL"), (-1, "a2g_fingerR")):
            fg = jaw.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, pos=[sgn * 0.022, 0, L * 0.80],
                              size=[0.008, 0.014, L * 0.22], rgba=ARM2_RGBA, mass=0.02)
            fg.name = nm                          # collidable (contact gate)
        jaw.add_site(name="a2_tcp", pos=[0, 0, L], size=[0.008, 0, 0], rgba=[1, 1, 0, 1])
    else:
        a2_site = s.site("a2_attachment_site")
        s.attach(robotiq, prefix="a2g_", site=a2_site)
        a2_base = s.body("a2g_base")
        a2_base.add_site(name="a2_tcp", pos=[0, 0, G.ROBOTIQ_PINCH], size=[0.008, 0, 0],
                         rgba=[1, 1, 0, 1])
        _stick_gripper(s, "a2g_", ARM2_RGBA)         # stick-figure the jaw too

    # shelves + items
    _add_shelf(wb, 1, G.ARM1_X)
    _add_shelf(wb, 2, G.ARM2_X)
    # pickup items, in each arm's clear reachable zone (off the dead-cone axis,
    # clear of the belt legs)
    # box at the OUTER pickup, cargo at the INNER staging point: a big gap so the arm
    # reaching one never sweeps across the other (your spacing fix for the knock-off).
    _free_item(wb, "box1", -1.45, "box")        # Arm 1 box (outer)
    _free_item(wb, "sheet1", -1.10, "sheet")    # Arm 1 cargo: relocated into arm 1's
    # controllable top-grasp band (same fix as tube1 on the arm-2 side): at the old
    # inner staging (-0.62) the top-down grasp solve errs 47mm with 67deg axis tilt
    # (far rear corner); at -1.10 it solves to 3.5mm/0deg. Still 0.35m clear of box1.
    _free_item(wb, "box2", 0.95, "box")         # Arm 2 box: same -0.25 offset from base as box1
    #                                              (was 1.45, which forced a base-crossing carry)
    _free_item(wb, "tube1", 1.10, "tube")       # Arm 2 cargo: relocated into arm 2's
    # controllable grasp band (0.95-1.20); honest grasp there is ~68mm vs ~250mm at the
    # old inner staging (0.62). Still 0.35 m clear of box2 (1.45) so the arm never sweeps
    # across the box when taking the tube (pin_loose also freezes both).

    # grasp welds (attach-on-valid-contact): pre-declared, inactive; the motion
    # layer activates one only when a genuine cup/jaw contact is detected.
    for eff, obj in [("a1_suction", "sheet1"), ("a1_suction", "box1"),
                     ("a2g_base", "tube1"), ("a2g_base", "box1")]:
        eq = s.add_equality()
        eq.type = mujoco.mjtEq.mjEQ_WELD
        eq.objtype = mujoco.mjtObj.mjOBJ_BODY
        eq.name1 = eff
        eq.name2 = obj
        eq.active = False
        eq.name = f"grasp_{eff}_{obj}"
    return s


def set_home(m, d):
    for pfx in ("a1_", "a2_"):
        for i, k in enumerate(range(1, 8)):
            jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, f"{pfx}joint{k}")
            d.qpos[m.jnt_qposadr[jid]] = HOME[i]
    mujoco.mj_forward(m, d)


def add_home_keyframe(s):
    """Compile a throwaway, capture the home qpos/ctrl, attach as a keyframe so
    the saved model rests in a sane pose (arms folded at home, not drooping from
    qpos=0). Returns a freshly compiled model."""
    m = s.compile(); d = mujoco.MjData(m)
    set_home(m, d)
    qpos = d.qpos.copy()
    ctrl = np.zeros(m.nu)
    for pfx in ("a1_", "a2_"):
        for i, k in enumerate(range(1, 8)):
            aid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{pfx}actuator{k}")
            if aid >= 0:
                ctrl[aid] = HOME[i]
    s.add_key(name="home", qpos=list(qpos), ctrl=list(ctrl))
    return s.compile()


def arm_shelf_penetration(m, d, tol=0.005):
    """Report any arm/EE geom penetrating a shelf or belt at the current state."""
    hits = []
    for c in range(d.ncon):
        con = d.contact[c]
        if con.dist > -tol:
            continue
        g1 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, con.geom1) or "?"
        g2 = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, con.geom2) or "?"
        arm = lambda g: g.startswith(("a1_", "a2_"))
        obs = lambda g: g.startswith("shelf_")
        if (arm(g1) and obs(g2)) or (arm(g2) and obs(g1)):
            hits.append((g1, g2, round(con.dist, 4)))
    return hits


def main():
    s = build_spec()
    m = add_home_keyframe(s)
    d = mujoco.MjData(m)
    print(f"COMPILED  bodies={m.nbody} joints={m.njnt} actuators={m.nu} geoms={m.ngeom}")
    # reset to home keyframe, hold there with actuators
    mujoco.mj_resetDataKeyframe(m, d, 0)
    d.ctrl[:] = m.key_ctrl[0]
    mujoco.mj_forward(m, d)
    for nm in ("a1_tcp", "a2_tcp"):
        sid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, nm)
        print(f"  {nm} home world pos = {np.round(d.site_xpos[sid], 3)}")
    for _ in range(2000):
        mujoco.mj_step(m, d)
    for nm in ("box1", "sheet1", "tube1"):
        bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, nm)
        print(f"  {nm:7s} settled z={d.xpos[bid][2]:.3f}")
    maxv = float(np.abs(d.qvel).max())
    print(f"max|qvel| after settle = {maxv:.4f} -> {'STABLE' if maxv < 0.5 else 'UNSTABLE'}")
    pen = arm_shelf_penetration(m, d)
    print(f"arm/shelf penetration at rest: {'NONE' if not pen else pen}")

    if "--save" in sys.argv:
        out = os.path.join(HERE, "cell.xml")
        with open(out, "w") as fh:
            fh.write(s.to_xml())
        print("wrote", out)


if __name__ == "__main__":
    main()
