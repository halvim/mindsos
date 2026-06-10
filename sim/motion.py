"""Phase B1/B2 motion core — side-grasp pick & place, parametric over arm/object.

Physical model (fixes the spill bug):
  * The shelf cells are open-front cubbies; objects insert HORIZONTALLY.
  * Grasp is from the side: the tool points -y the whole time and grips the
    object's rear (+y, trailing) face, so the object NEVER pitches/rolls — it
    stays upright from belt to cubby. An open Box keeps its cargo.
  * Belt pick uses the same -y tool axis (no reorientation between pick & place).
  * Containment = attach-on-insertion: cargo lowered into a Box's open top is
    attached to the Box and rides along.

Attach is contact-gated (attach-on-valid-contact) then held kinematically
(reliable for the prototype; physics welds are pre-declared in cell.xml for
Phase-F tuning).

Build trajectories with `run_all()` -> web/anim_<name>.json for each combo.
"""
from __future__ import annotations
import os, json, numpy as np, mujoco
import geom_config as G
from build_cell import build_spec, add_home_keyframe, set_home, HOME, BOX_HY, BOX_HZ
from reach_validate import ik, arm_dofs, joint_limits

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
CAP_EVERY = 10

def _slerp(q0, q1, t):
    """Shortest-arc quaternion interpolation (wxyz)."""
    q0 = np.asarray(q0, float); q1 = np.asarray(q1, float)
    d = float(np.dot(q0, q1))
    if d < 0:
        q1 = -q1; d = -d
    if d > 0.9995:
        q = q0 + t * (q1 - q0)
    else:
        th = np.arccos(np.clip(d, -1, 1)); s = np.sin(th)
        q = (np.sin((1 - t) * th) * q0 + np.sin(t * th) * q1) / s
    return q / np.linalg.norm(q)


def R_from(zaxis, up=(0, 0, 1.0)):
    """Tool orientation with tool-z = zaxis and a natural roll (tool-x ⟂ up)."""
    z = np.asarray(zaxis, float); z = z / np.linalg.norm(z)
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross([0, 1, 0], z)
    x = x / np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


# Fixing the FULL tool orientation (not just the approach axis) keeps the grasp
# offset constant, so placement is exact. With the belt in front, both arms grip
# the object's arm-facing (+y) face with tool z = -y — an easy forward reach and
# the SAME axis as the shelf insert, so there's no reorientation: the object
# stays upright from belt to cubby. Top grasp: tool z down, to drop cargo in.
GRASP_R = {1: R_from([0, -1, 0]), 2: R_from([0, -1, 0])}
TOP_R = R_from([0, 0, -1])
# Arm-2 box grasp offset (box_centre - TCP) at the validated side-grasp. A small
# object (tube) snapped to ride at this same offset places exactly like the box.
BOX_GRASP_OFF = np.array([-0.043, -0.004, -0.091])


class Cell:
    def __init__(self):
        self.s = build_spec()
        self.m = add_home_keyframe(self.s)
        self.d = mujoco.MjData(self.m)
        mujoco.mj_resetDataKeyframe(self.m, self.d, 0)
        self.d.ctrl[:] = self.m.key_ctrl[0]
        mujoco.mj_forward(self.m, self.d)
        self.bodies = [mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, i)
                       for i in range(self.m.nbody)]
        self.frames, self.events = [], []
        self.attach = []          # list of dicts: child slaved to a parent
        self.arm = {}
        for a, pfx in ((1, "a1_"), (2, "a2_")):
            sid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_SITE, f"a{a}_tcp")
            df, qa = arm_dofs(self.m, pfx)
            lo, hi = joint_limits(self.m, pfx)
            act = [mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{pfx}actuator{k}")
                   for k in range(1, 8)]
            grip = [g for g in range(self.m.ngeom)
                    if (mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, g) or "").startswith(
                        "a1_cup" if a == 1 else "a2g_")]
            self.arm[a] = dict(pfx=pfx, sid=sid, dofs=df, qadr=qa, lo=lo, hi=hi,
                               act=act, grip=set(grip))

    # ---- ids ----
    def bid(self, n): return mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, n)
    def qadr_of(self, bid): return self.m.jnt_qposadr[self.m.body_jntadr[bid]]
    def dadr_of(self, bid): return self.m.jnt_dofadr[self.m.body_jntadr[bid]]

    # ---- attachments (kinematic) ----
    # Each held object follows its parent by a FIXED WORLD offset and keeps a
    # LOCKED orientation, so tool-orientation wobble can't tilt or fling it.
    def _apply_attach(self):
        for at in self.attach:
            if at["kind"] == "world":
                p, q = at["pos"], at["quat"]
            elif at["kind"] == "tcp":               # follow TCP position, LOCKED orientation
                p, q = self.d.site_xpos[at["sid"]].copy() + at["off"], at["quat"]
            elif at["kind"] == "rigid":             # follow TCP position AND orientation
                Rt = self.d.site_xmat[at["sid"]].reshape(3, 3)
                p = self.d.site_xpos[at["sid"]].copy() + Rt @ at["rel_pos"]
                tq = np.zeros(4); mujoco.mju_mat2Quat(tq, self.d.site_xmat[at["sid"]])
                q = np.zeros(4); mujoco.mju_mulQuat(q, tq, at["rel_quat"])
            else:                                   # parented to another (upright) body
                p, q = self.d.xpos[at["parent"]].copy() + at["off"], at["quat"]
            adr, dadr = self.qadr_of(at["child"]), self.dadr_of(at["child"])
            self.d.qpos[adr:adr + 3] = p
            self.d.qpos[adr + 3:adr + 7] = q
            self.d.qvel[dadr:dadr + 6] = 0.0

    def pin(self, child_body):
        cb = self.bid(child_body)
        self.attach.append(dict(child=cb, kind="world",
                                pos=self.d.xpos[cb].copy(), quat=self.d.xquat[cb].copy()))

    def pin_loose(self, *active):
        """Pin EVERY free belt item at its settled rest pose. This freezes the whole
        belt: idle items can't float, drift, or be knocked off, and the item the arm
        is about to grasp can't micro-settle and flip its knife-edge grasp branch
        (grasping it detaches its pin). Pairs with belt spacing so the arm never
        contacts a pinned neighbour."""
        for b in range(self.m.nbody):
            ja = self.m.body_jntadr[b]
            if ja >= 0 and self.m.jnt_type[ja] == mujoco.mjtJoint.mjJNT_FREE:
                self.pin(mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, b))

    def attach_tcp(self, child_body, sid):
        cb = self.bid(child_body)
        off = self.d.xpos[cb].copy() - self.d.site_xpos[sid].copy()
        self.detach(child_body)
        self.attach.append(dict(child=cb, kind="tcp", sid=sid, off=off,
                                quat=self.d.xquat[cb].copy()))

    def snap_to_tcp(self, a, obj, world_off=(0.0, 0.0, 0.0), upright=False):
        """Seat the held object at a fixed offset from the tool pinch point and
        re-grab, so it rides cleanly in the gripper at a KNOWN standoff. This makes
        the placement deterministic regardless of how the (knife-edge, possibly
        folded) grasp solved. upright=True also resets the object to upright, so a
        grasp that captured a tilted pose still places level."""
        sid = self.arm[a]["sid"]; cb = self.bid(obj)
        adr = self.qadr_of(cb)
        self.d.qpos[adr:adr + 3] = self.d.site_xpos[sid].copy() + np.asarray(world_off, float)
        if upright:
            self.d.qpos[adr + 3:adr + 7] = [1.0, 0.0, 0.0, 0.0]
        mujoco.mj_forward(self.m, self.d)
        self.attach_tcp(obj, sid)

    def attach_rigid(self, child_body, sid):
        """Rigid TOOL-FRAME grasp: child follows the wrist's position AND
        orientation, so rotating the wrist rotates the cargo (needed to stand a
        flat sheet up for a side insert). Capture the child pose in the TCP frame."""
        cb = self.bid(child_body)
        Rt = self.d.site_xmat[sid].reshape(3, 3)
        rel_pos = Rt.T @ (self.d.xpos[cb].copy() - self.d.site_xpos[sid].copy())
        tq = np.zeros(4); mujoco.mju_mat2Quat(tq, self.d.site_xmat[sid])
        tqi = np.zeros(4); mujoco.mju_negQuat(tqi, tq)
        rel_quat = np.zeros(4)
        mujoco.mju_mulQuat(rel_quat, tqi, self.d.xquat[cb].copy())
        self.detach(child_body)
        self.attach.append(dict(child=cb, kind="rigid", sid=sid,
                                rel_pos=rel_pos, rel_quat=rel_quat))

    def attach_body(self, child_body, parent_body):
        cb = self.bid(child_body); pb = self.bid(parent_body)
        off = self.d.xpos[cb].copy() - self.d.xpos[pb].copy()
        self.detach(child_body)
        self.attach.append(dict(child=cb, kind="body", parent=pb, off=off,
                                quat=self.d.xquat[cb].copy()))

    def detach(self, child_body):
        cb = self.bid(child_body)
        self.attach = [a for a in self.attach if a["child"] != cb]

    # ---- sim ----
    def capture(self):
        self.frames.append([[round(float(x), 4) for x in (*self.d.xpos[b], *self.d.xquat[b])]
                            for b in range(self.m.nbody)])

    _sync = None        # optional callback(self) per step, for a live viewer

    def step(self, n):
        for _ in range(n):
            mujoco.mj_step(self.m, self.d)
            self._apply_attach()
            if len(self.frames) == 0 or self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1
    _k = 0

    def _sim_hold(self, a, qg, target):
        """Drive a throwaway servo to qg and return the TCP error it actually
        HOLDS under gravity — the controllability of that IK branch."""
        A = self.arm[a]
        s = mujoco.MjData(self.m)
        s.qpos[:] = self.d.qpos; s.ctrl[:] = self.d.ctrl
        mujoco.mj_forward(self.m, s)
        q0 = np.array([s.ctrl[x] for x in A["act"]])
        for i in range(120):
            al = (i + 1) / 120
            for j, x in enumerate(A["act"]):
                s.ctrl[x] = (1 - al) * q0[j] + al * qg[j]
            mujoco.mj_step(self.m, s)
        for _ in range(150):
            mujoco.mj_step(self.m, s)
        return float(np.linalg.norm(s.site_xpos[A["sid"]] - np.asarray(target, float)))

    def solve(self, a, target, R, robust=False):
        A = self.arm[a]
        scratch = mujoco.MjData(self.m)
        cur = self.d.qpos[A["qadr"]].copy()
        seeds = [cur, np.array(HOME, float)]
        rng = np.random.default_rng(0)
        for _ in range(32):
            seeds.append(A["lo"] + rng.uniform(0, 1, 7) * (A["hi"] - A["lo"]))
        oks, fb = [], None
        for sd in seeds:
            scratch.qpos[:] = self.d.qpos
            r = ik(self.m, scratch, A["pfx"], A["sid"], A["dofs"], A["qadr"],
                   A["lo"], A["hi"], np.asarray(target, float),
                   seed=sd, iters=400, R_des=R)
            q = scratch.qpos[A["qadr"]].copy()
            if r["ok"]:
                oks.append(q)
            if fb is None or r["perr"] < fb[1]:
                fb = (q, r["perr"])
        if not oks:
            return fb[0]
        if not robust:
            return min(oks, key=lambda q: np.linalg.norm(q - cur))
        # robust (expensive): prefer the CONTROLLABLE branch nearest the current
        # pose — continuity alone can pick a branch the servo can't hold. Only the
        # strained top-grasp descent needs this.
        uniq = []
        for q in sorted(oks, key=lambda q: np.linalg.norm(q - cur)):
            if not any(np.linalg.norm(q - u) < 0.10 for u in uniq):
                uniq.append(q)
        best = None
        for q in uniq[:5]:
            held = self._sim_hold(a, q, target)
            if held < 0.03:
                return q
            if best is None or held < best[1]:
                best = (q, held)
        return best[0]

    def move_to(self, a, target, R, steps=150, settle=170, label="", robust=False):
        """KINEMATIC Cartesian move: the tool follows a STRAIGHT LINE (position lerp +
        orientation slerp) from its current pose to (target, R), solved by a warm-started
        local IK each step (seeded from the previous joint pose). Staying in one IK branch
        keeps the arm — and any held object — moving smoothly, with no branch-swing loops
        and no gravity sag. Physics drops/settles still go through step()."""
        A = self.arm[a]
        target = np.asarray(target, float)
        p0 = self.d.site_xpos[A["sid"]].copy()
        q0quat = np.zeros(4); mujoco.mju_mat2Quat(q0quat, self.d.site_xmat[A["sid"]].copy())
        q1quat = np.zeros(4); mujoco.mju_mat2Quat(q1quat, np.asarray(R, float).reshape(9).copy())
        n = max(int(steps), 1); hold = max(int(settle) // 10, 0)
        Rmat = np.zeros(9)
        for i in range(n + hold):
            al = min((i + 1) / n, 1.0)
            pi = (1 - al) * p0 + al * target
            mujoco.mju_quat2Mat(Rmat, _slerp(q0quat, q1quat, al))
            ik(self.m, self.d, A["pfx"], A["sid"], A["dofs"], A["qadr"],
               A["lo"], A["hi"], pi, seed=self.d.qpos[A["qadr"]].copy(),
               iters=50, R_des=Rmat.reshape(3, 3))   # warm-started -> stays in branch
            qsol = self.d.qpos[A["qadr"]]
            for j, x in enumerate(A["act"]):
                self.d.ctrl[x] = qsol[j]
            self._apply_attach()
            mujoco.mj_forward(self.m, self.d)
            if len(self.frames) == 0 or self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1
        err = float(np.linalg.norm(self.d.site_xpos[A["sid"]] - target))
        if label:
            print(f"   a{a} {label:12s} tcp_err={err*1000:4.0f} mm")
        return err

    def _box_clear(self, a, obj):
        """Min distance from obj's centre to the arm's upper-link segments (link0..7),
        excluding the wrist that holds it. Small => the held object is clipping the arm."""
        pts = [self.d.xpos[self.bid(f"a{a}_link{i}")] for i in range(8)]
        box = self.d.xpos[self.bid(obj)]
        dmin = 1e9
        for s in range(len(pts) - 1):
            p, q = pts[s], pts[s + 1]; ab = q - p
            t = float(np.clip(np.dot(box - p, ab) / (np.dot(ab, ab) + 1e-9), 0, 1))
            dmin = min(dmin, float(np.linalg.norm(box - (p + t * ab))))
        return dmin

    def solve_clear(self, a, target, R, obj, n_seeds=28, thr=0.11):
        """IK that prefers an arm branch keeping the HELD obj clear of the arm's own
        links. Among reachable branches, pick the clearest (>= thr if any), tie-broken
        by proximity to the current pose (so the following joint-lerp is short)."""
        A = self.arm[a]
        saved = self.d.qpos.copy(); cur = saved[A["qadr"]].copy()
        rng = np.random.default_rng(0)
        seeds = [cur.copy(), np.array(HOME, float)]
        seeds += [A["lo"] + rng.uniform(0, 1, 7) * (A["hi"] - A["lo"]) for _ in range(n_seeds)]
        tgt = np.asarray(target, float); Rd = np.asarray(R, float); cand = []
        for sd in seeds:
            sc = mujoco.MjData(self.m); sc.qpos[:] = saved
            r = ik(self.m, sc, A["pfx"], A["sid"], A["dofs"], A["qadr"],
                   A["lo"], A["hi"], tgt, seed=sd, iters=300, R_des=Rd)
            if not r["ok"]:
                continue
            q = sc.qpos[A["qadr"]].copy()
            self.d.qpos[:] = saved; self.d.qpos[A["qadr"]] = q
            self._apply_attach(); mujoco.mj_forward(self.m, self.d)
            cand.append((q, self._box_clear(a, obj)))
        self.d.qpos[:] = saved; self._apply_attach(); mujoco.mj_forward(self.m, self.d)
        if not cand:
            return self.solve(a, target, R)
        pool = [c for c in cand if c[1] >= thr] or cand
        return min(pool, key=lambda c: np.linalg.norm(c[0] - cur))[0]

    def move_to_q(self, a, qg, steps=260, label=""):
        """KINEMATIC joint-space lerp from the current pose to qg (a chosen branch):
        continuous (no branch switch), held object follows the wrist."""
        A = self.arm[a]
        q0 = self.d.qpos[A["qadr"]].copy(); qg = np.asarray(qg, float)
        for i in range(steps):
            al = (i + 1) / steps
            qi = (1 - al) * q0 + al * qg
            self.d.qpos[A["qadr"]] = qi
            for j, x in enumerate(A["act"]):
                self.d.ctrl[x] = qi[j]
            mujoco.mj_forward(self.m, self.d); self._apply_attach()
            if self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1

    def glide_into(self, a, obj, cell, hh=None, N=90):
        """Hold the arm where it is; glide obj kinematically the last few cm to the seat."""
        A = self.arm[a]
        cell = np.array(cell, float)
        if hh is None:
            hh = self.obj_half(obj, 2)
        floor_top = cell[2] - 0.5 * G.ROW_DZ + 0.008
        seat = np.array([cell[0], cell[1], floor_top + hh])
        held_q = self.d.qpos[A["qadr"]].copy()
        box0 = self.d.xpos[self.bid(obj)].copy(); upq = self.d.xquat[self.bid(obj)].copy()
        self.detach(obj); adr = self.qadr_of(self.bid(obj))
        for i in range(N):
            al = (i + 1) / N
            pos = box0 * (1 - al) + seat * al
            self.d.qpos[adr:adr + 3] = pos; self.d.qpos[adr + 3:adr + 7] = upq
            self.d.qpos[A["qadr"]] = held_q; self.d.qvel[:] = 0
            mujoco.mj_forward(self.m, self.d)
            if self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1
        self.pin(obj); self.event(f"{obj} seated")

    def _links_clear_structures(self, a, margin=0.04):
        """True if every arm link (and wrist) is clear of BOTH this arm's rack and the
        conveyor body. Point check (links are thin) — used to validate static rest poses."""
        ax = G.ARM1_X if a == 1 else G.ARM2_X
        x0, x1 = ax - 1.5 * G.COL_DX - margin, ax + 1.5 * G.COL_DX + margin
        ry0, ry1 = G.SHELF_Y_ARM[a] - G.SHELF_DEPTH - margin, G.SHELF_Y_ARM[a] + margin
        rz0, rz1 = G.ROW_Z0 - 0.5 * G.ROW_DZ - margin, G.ROW_Z0 + 2.5 * G.ROW_DZ + margin
        cy0, cy1 = G.BELT_Y - G.BELT_HALF_W - margin, G.BELT_Y + G.BELT_HALF_W + margin
        for nm in [f"a{a}_link{i}" for i in range(8)] + [f"a{a}_attachment", f"a{a}_suction"]:
            bid = self.bid(nm)
            if bid < 0:
                continue
            p = self.d.xpos[bid]
            if x0 < p[0] < x1 and ry0 < p[1] < ry1 and rz0 < p[2] < rz1:
                return False                                     # in the rack
            if G.BELT_X0 < p[0] < G.BELT_X1 and cy0 < p[1] < cy1 and 0.40 < p[2] < 0.86 + margin:
                return False                                     # in the conveyor body
        return True

    def rest_candidates(self, a, box, seed=None, per_target=2, max_total=None, iters=600):
        """Every clear, conveyor-FACING (tool +y) ready pose — the menu of rest poses to choose
        from. Home is set JUST BEHIND the box: EE at box + (0, -0.25, 0) (same x, same height),
        tool pointing +y at the box, ready to grip its shelf-facing face. Small (dx,dy,dz)
        variations are fallbacks for reachability/clearance only."""
        A = self.arm[a]
        oc = self.d.xpos[self.bid(box)].copy(); yh = self.obj_half(box, 1)
        Rg = R_from([0, 1, 0])
        saved = self.d.qpos.copy(); rng = np.random.default_rng(3)
        cands = [np.array([oc[0] + dx, oc[1] - 0.25 + dy, oc[2] + dz])
                 for dx, dy, dz in ((0, 0, 0), (0, 0.02, 0.03), (0, -0.03, 0),
                                    (0.03, 0, 0.03), (-0.03, 0, 0), (0, 0.05, 0.06))]
        seed_list = ([np.asarray(seed, float)] if seed is not None else [])
        out = []
        for tgt in cands:
            got = 0
            for sd in seed_list + [np.array(HOME, float)] + \
                      [A["lo"] + rng.uniform(0, 1, 7) * (A["hi"] - A["lo"]) for _ in range(18)]:
                sc = mujoco.MjData(self.m); sc.qpos[:] = saved
                r = ik(self.m, sc, A["pfx"], A["sid"], A["dofs"], A["qadr"],
                       A["lo"], A["hi"], tgt, seed=sd, iters=iters, R_des=Rg)
                if not r["ok"] or r["perr"] > 0.012:        # home must actually REACH the target
                    continue
                q = sc.qpos[A["qadr"]].copy()
                self.d.qpos[:] = saved; self.d.qpos[A["qadr"]] = q; mujoco.mj_forward(self.m, self.d)
                if self._links_clear_structures(a) and not any(np.linalg.norm(q - o) < 0.20 for o in out):
                    out.append(q); got += 1
                    if max_total is not None and len(out) >= max_total:
                        self.d.qpos[:] = saved; mujoco.mj_forward(self.m, self.d)
                        return out                      # early stop: caller only needs out[:max_total]
                    if got >= per_target:
                        break
        self.d.qpos[:] = saved; mujoco.mj_forward(self.m, self.d)
        return out

    def rest_pose(self, a, box, seed=None, iters=600):
        """First clear conveyor-facing ready pose (kept for callers that don't pick by return).
        max_total=1: identical result (out[0]) without solving the remaining targets."""
        cs = self.rest_candidates(a, box, seed=seed, max_total=1, iters=iters)
        return cs[0] if cs else None

    def return_to_rest(self, a, rest_q, n=200, reconfig=True, capture=True, label=""):
        """Rules §Return to home (tool is the master, no object): drive the EMPTY tool along a
        smooth Cartesian path (position lerp + orientation slerp) from its current (post-retract)
        pose to the REST tool pose. The other links FOLLOW by warm IK (stay in one branch);
        reconfigure with the MINIMAL joint perturbation ONLY where a link would otherwise touch a
        structure. capture=False -> dry run: no frames, restores qpos, returns the max per-step
        joint jump (a branch flip shows up as a big jump) so the caller can pick a flip-free REST."""
        A = self.arm[a]; sid = A["sid"]
        rest_q = np.asarray(rest_q, float)
        saved = self.d.qpos.copy()
        self.d.qpos[A["qadr"]] = rest_q; mujoco.mj_forward(self.m, self.d)
        rest_tcp = self.d.site_xpos[sid].copy()
        rest_quat = np.zeros(4); mujoco.mju_mat2Quat(rest_quat, self.d.site_xmat[sid].copy())
        self.d.qpos[:] = saved; mujoco.mj_forward(self.m, self.d)
        p0 = self.d.site_xpos[sid].copy()
        q0 = np.zeros(4); mujoco.mju_mat2Quat(q0, self.d.site_xmat[sid].copy())
        Rmat = np.zeros(9); rng = np.random.default_rng(2)
        prev = self.d.qpos[A["qadr"]].copy(); max_jump = 0.0
        for i in range(n):
            al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / n)        # smoothstep 0 -> 1
            pi = (1 - al) * p0 + al * rest_tcp
            mujoco.mju_quat2Mat(Rmat, _slerp(q0, rest_quat, al)); Rt = Rmat.reshape(3, 3)
            cur = self.d.qpos[A["qadr"]].copy()
            ik(self.m, self.d, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
               pi, seed=cur, iters=60, R_des=Rt)                # warm: links follow, stay in branch
            if reconfig and not self._links_clear_structures(a, margin=0.02):
                best = None
                for sd in [cur] + [np.clip(cur + rng.normal(0, s, 7), A["lo"], A["hi"])
                                   for s in (0.2, 0.4, 0.8) for _ in range(6)]:
                    sc = mujoco.MjData(self.m); sc.qpos[:] = self.d.qpos
                    r = ik(self.m, sc, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                           pi, seed=sd, iters=120, R_des=Rt)
                    if not r["ok"]:
                        continue
                    q = sc.qpos[A["qadr"]].copy()
                    self.d.qpos[A["qadr"]] = q; mujoco.mj_forward(self.m, self.d)
                    key = (self._links_clear_structures(a, margin=0.02), -float(np.linalg.norm(q - cur)))
                    if best is None or key > best[0]:
                        best = (key, q)
                if best is not None:
                    self.d.qpos[A["qadr"]] = best[1]
            qn = self.d.qpos[A["qadr"]].copy()
            max_jump = max(max_jump, float(np.linalg.norm(qn - prev))); prev = qn
            if not capture:
                continue
            for j, x in enumerate(A["act"]):
                self.d.ctrl[x] = self.d.qpos[A["qadr"]][j]
            self._apply_attach(); mujoco.mj_forward(self.m, self.d)
            if self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1
        if not capture:
            self.d.qpos[:] = saved; mujoco.mj_forward(self.m, self.d)
            return max_jump
        if label:
            err = float(np.linalg.norm(self.d.site_xpos[sid] - rest_tcp))
            print(f"   a{a} {label:12s} tcp_err={err*1000:4.0f} mm  max_jump={max_jump:.2f}")
        return max_jump

    def carry_master(self, a, obj, target, N=240, capture=True, reconfig=True, yaw_total=np.pi,
                     base_dir=0, ride=False, settle=True):
        """OBJECT-master carry to `target`: drive the object along a smooth, strictly
        MONOTONIC path (+ a single monotonic yaw so its gripped face ends facing the mouth).
        The ARM follows by warm IK with joints changing as LITTLE as possible, reconfiguring
        (smallest perturbation that clears) ONLY where the object would otherwise touch the
        arm. Returns the min object-vs-arm clearance (used to pick the clean grasp branch).
        capture=False -> dry run (no frames, no attach changes; caller restores qpos)."""
        A = self.arm[a]; sid = A["sid"]
        box0 = self.d.xpos[self.bid(obj)].copy()
        Rb0 = self.d.xmat[self.bid(obj)].reshape(3, 3).copy()
        tcp0 = self.d.site_xpos[sid].copy()
        Rt0 = self.d.site_xmat[sid].reshape(3, 3).copy()
        grip_local = Rb0.T @ (tcp0 - box0)        # TCP point in the box frame (fixed grip)
        tool_rel = Rb0.T @ Rt0                     # tool orientation in the box frame (fixed)
        rel_pos = Rt0.T @ (box0 - tcp0)            # box origin in the TOOL frame (rigid grip)
        rel_R = Rt0.T @ Rb0                         # box orientation in the TOOL frame (rigid grip)
        target = np.asarray(target, float)
        adr = self.qadr_of(self.bid(obj)); bqm = np.zeros(4); min_clear = 1e9
        prev_q = self.d.qpos[A["qadr"]].copy(); max_jump = 0.0; max_te = 0.0
        lids = [self.bid(f"a{a}_link{i}") for i in range(8)]   # for link-accel (visual jerk) at
        samp = []                                             # the CAPTURE cadence (every 10 steps)
        base_lo = self.d.qpos[A["qadr"]][0]                   # base joint 0 at carry start (body yaw)
        if capture:
            self.detach(obj)
        rng = np.random.default_rng(1)

        def set_box(box_pos, Rb):
            # ride=True: seat the box from the ACTUAL tool pose (rigid grip) so it can NEVER drift
            # off the gripper (the long jaw can't track the 180 orbit -> box rides it instead).
            # Assumes the model is forwarded (tool site current).
            if ride:
                tcp_a = self.d.site_xpos[sid].copy(); Rt_a = self.d.site_xmat[sid].reshape(3, 3).copy()
                mujoco.mju_mat2Quat(bqm, (Rt_a @ rel_R).reshape(9))
                self.d.qpos[adr:adr + 3] = tcp_a + Rt_a @ rel_pos
                self.d.qpos[adr + 3:adr + 7] = bqm
            else:
                mujoco.mju_mat2Quat(bqm, Rb.reshape(9))
                self.d.qpos[adr:adr + 3] = box_pos; self.d.qpos[adr + 3:adr + 7] = bqm

        for i in range(N):
            al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / N)    # smoothstep 0 -> 1
            box_pos = (1 - al) * box0 + al * target
            yaw = yaw_total * al                            # monotonic 0 -> yaw_total
            cz, sz = np.cos(yaw), np.sin(yaw)
            Rb = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ Rb0
            tcp = box_pos + Rb @ grip_local                # where the tool must be
            Rt = Rb @ tool_rel
            cur = self.d.qpos[A["qadr"]].copy()
            if base_dir:
                # constrain the BODY (base joint 0) to rotate only in the +z (base_dir>0) or -z
                # direction during the carry: clamp joint 0 monotonic, IK solves the rest to keep
                # the tool on the box. "Body turns +z as much as needed."
                lo2 = A["lo"].copy(); hi2 = A["hi"].copy()
                if base_dir > 0:
                    lo2[0] = base_lo
                else:
                    hi2[0] = base_lo
                cur2 = cur.copy(); cur2[0] = np.clip(cur2[0], lo2[0], hi2[0])
                ik(self.m, self.d, A["pfx"], sid, A["dofs"], A["qadr"], lo2, hi2,
                   tcp, seed=cur2, iters=70, R_des=Rt)
                base_lo = self.d.qpos[A["qadr"]][0]            # advance the monotonic floor
            else:
                ik(self.m, self.d, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                   tcp, seed=cur, iters=70, R_des=Rt)
            set_box(box_pos, Rb); mujoco.mj_forward(self.m, self.d)
            if reconfig and self._box_clear(a, obj) < 0.090:
                # MINIMAL reconfiguration: smallest joint perturbation that clears.
                best = None
                for sd in [cur] + [np.clip(cur + rng.normal(0, s, 7), A["lo"], A["hi"])
                                   for s in (0.2, 0.4, 0.8) for _ in range(6)]:
                    sc = mujoco.MjData(self.m); sc.qpos[:] = self.d.qpos
                    r = ik(self.m, sc, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                           tcp, seed=sd, iters=120, R_des=Rt)
                    if not r["ok"]:
                        continue
                    q = sc.qpos[A["qadr"]].copy()
                    self.d.qpos[A["qadr"]] = q; set_box(box_pos, Rb); mujoco.mj_forward(self.m, self.d)
                    key = (self._box_clear(a, obj) >= 0.090, -float(np.linalg.norm(q - cur)))
                    if best is None or key > best[0]:
                        best = (key, q)
                if best is not None:
                    self.d.qpos[A["qadr"]] = best[1]; set_box(box_pos, Rb); mujoco.mj_forward(self.m, self.d)
            min_clear = min(min_clear, self._box_clear(a, obj))
            max_te = max(max_te, float(np.linalg.norm(self.d.site_xpos[sid] - tcp)))  # EE-follows-box error
            qn = self.d.qpos[A["qadr"]].copy()
            max_jump = max(max_jump, float(np.linalg.norm(qn - prev_q))); prev_q = qn
            if i % CAP_EVERY == 0:                          # sample links at the capture cadence
                samp.append(np.array([self.d.xpos[b].copy() for b in lids]))
            for j, x in enumerate(A["act"]):
                self.d.ctrl[x] = self.d.qpos[A["qadr"]][j]
            set_box(box_pos, Rb); self.d.qvel[:] = 0
            if ride and settle and i >= int(0.85 * N):
                # ride keeps the box GLUED to the gripper through the turn; the gripper's small
                # final tracking error would leave the box off the seat, so over the last frames
                # blend the box onto the EXACT planned seat (a few-cm settle into the cubby).
                beta = (i - int(0.85 * N) + 1) / (N - int(0.85 * N))
                self.d.qpos[adr:adr + 3] = (1 - beta) * self.d.qpos[adr:adr + 3] + beta * box_pos
            mujoco.mj_forward(self.m, self.d)
            if capture:
                if self._k % CAP_EVERY == 0:
                    self.capture()
                if self._sync is not None:
                    self._sync(self)
                self._k += 1
        if capture:
            self.pin(obj)
        # max link-acceleration at the capture cadence = the VISUAL jerk the checklist flags
        max_la = 0.0
        for f in range(1, len(samp) - 1):
            max_la = max(max_la, float(np.max(np.linalg.norm(samp[f + 1] - 2 * samp[f] + samp[f - 1], axis=1))))
        return min_clear, max_jump, max_te, max_la

    def carry_pivot(self, a, obj, seat, yaw_dir=+1, capture=True, lift_dz=0.16,
                    stage_off=(0.0, 0.22, 0.10), legs=(70, 320, 120), via_tcp=None,
    via_legs=(70, 250, 160, 60), rot_axis=(0.0, 0.0, 1.0), rot_ang=None,
                    plan_override=None, end_seed=False):
        """Arm-2 carry: the box rotates about the JAW PINCH (not its own center), and the
        180 turn happens DURING the transit on the rack side (front hemisphere), where the
        arm has orientation authority — probed at ~12 mm / 1.5 deg tracking vs 146 mm for
        the center-spin orbit. The box rides its PLANNED pose (object master, rigid grip
        transform); the tool genuinely tracks it, so there is NO glue and NO end settle.
        Legs: lift straight up -> transit while yawing yaw_dir*180 about the pinch ->
        pure-translation insert. Returns (min_clear, max_jump, max_te, max_la) like
        carry_master. capture=False -> dry run (caller restores qpos)."""
        A = self.arm[a]; sid = A["sid"]
        box0 = self.d.xpos[self.bid(obj)].copy()
        Rb0 = self.d.xmat[self.bid(obj)].reshape(3, 3).copy()
        tcp0 = self.d.site_xpos[sid].copy()
        Rt0 = self.d.site_xmat[sid].reshape(3, 3).copy()
        rel_pos = Rt0.T @ (box0 - tcp0)            # box origin in the TOOL frame (rigid grip)
        rel_R = Rt0.T @ Rb0                        # box orientation in the TOOL frame
        seat = np.asarray(seat, float)
        # general rotation: axis-angle about rot_axis (z-yaw for the a2 box turn; x-pitch
        # -90 for the a1 sheet stand-up). rot_ang=None keeps the yaw_dir*180 box default.
        ax = np.asarray(rot_axis, float); ax = ax / np.linalg.norm(ax)
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        def _rot(ang):
            return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)
        YT = (yaw_dir * np.pi) if rot_ang is None else float(rot_ang)
        Rend = _rot(YT) @ Rt0
        tcp_seat = seat - Rend @ rel_pos           # tool pose that puts the box ON the seat
        lift = tcp0 + np.array([0.0, 0.0, lift_dz])
        stage = tcp_seat + np.asarray(stage_off, float)
        adr = self.qadr_of(self.bid(obj)); bqm = np.zeros(4); min_clear = 1e9
        prev_q = self.d.qpos[A["qadr"]].copy(); max_jump = 0.0; max_te = 0.0
        lids = [self.bid(f"a{a}_link{i}") for i in range(8)]
        samp = []
        if capture:
            self.detach(obj)
        if plan_override is not None:
            # caller-supplied legs [(frames, tcp_fn(al), ang_fn(al))] — e.g. the cubby->belt
            # REVERSE route (extract, transit, pitch-back at the comfort zone, lower)
            plan = plan_override
        elif via_tcp is not None:
            # comfort-waypoint schedule (the outer/low cubbies are an IK dead zone for the
            # 180 turn — probed: NO continuous branch turns there): turn ends at the proven
            # via point, then pure translations (diag to own mouth, straight in) — those
            # track tight. Both ends exact, no branch flip.
            via = np.asarray(via_tcp, float)
            mouth = tcp_seat + np.array([0.0, 0.12, 0.0])
            plan = [(via_legs[0], lambda u: tcp0 + u * (lift - tcp0), lambda u: 0.0),
                    (via_legs[1], lambda u: lift + u * (via - lift), lambda u: YT * u),
                    (via_legs[2], lambda u: via + u * (mouth - via), lambda u: YT),
                    (via_legs[3], lambda u: mouth + u * (tcp_seat - mouth), lambda u: YT)]
        else:
            plan = [(legs[0], lambda u: tcp0 + u * (lift - tcp0), lambda u: 0.0),
                    (legs[1], lambda u: lift + u * (stage - lift), lambda u: YT * u),
                    (legs[2], lambda u: stage + u * (tcp_seat - stage), lambda u: YT)]
        q_fin = None
        if end_seed:
            # greedy warm IK is direction-asymmetric: inserts INTO a tight corner can
            # diverge where the reverse extract tracks fine. Pull the seeds of the final
            # two legs progressively toward the robust-solved END pose. Engage PER CUBBY
            # (caller dry-runs first): a static pull breaks cubbies that track cleanly,
            # and an adaptive (engage-on-divergence) pull engages too late and yanks.
            q_fin = self.solve(a, tcp_seat, Rend, robust=True)
        k = 0
        for li, (n, tcp_fn, yaw_fn) in enumerate(plan):
            pull = end_seed and li >= len(plan) - 2
            for i in range(n):
                al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / n)   # smoothstep per leg
                tcp = tcp_fn(al)
                Rt = _rot(yaw_fn(al)) @ Rt0
                cur = self.d.qpos[A["qadr"]].copy()
                sd = cur if not pull else (1 - 0.4 * al) * cur + 0.4 * al * q_fin
                ik(self.m, self.d, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                   tcp, seed=sd, iters=70, R_des=Rt)
                # the box follows its PLANNED pose (master) — no glue to the actual tool
                mujoco.mju_mat2Quat(bqm, (Rt @ rel_R).reshape(9))
                self.d.qpos[adr:adr + 3] = tcp + Rt @ rel_pos
                self.d.qpos[adr + 3:adr + 7] = bqm
                mujoco.mj_forward(self.m, self.d)
                min_clear = min(min_clear, self._box_clear(a, obj))
                max_te = max(max_te, float(np.linalg.norm(self.d.site_xpos[sid] - tcp)))
                qn = self.d.qpos[A["qadr"]].copy()
                max_jump = max(max_jump, float(np.linalg.norm(qn - prev_q))); prev_q = qn
                if k % CAP_EVERY == 0:
                    samp.append(np.array([self.d.xpos[b].copy() for b in lids]))
                for j, x in enumerate(A["act"]):
                    self.d.ctrl[x] = self.d.qpos[A["qadr"]][j]
                self.d.qvel[:] = 0
                if capture:
                    if self._k % CAP_EVERY == 0:
                        self.capture()
                    if self._sync is not None:
                        self._sync(self)
                    self._k += 1
                k += 1
        if capture:
            self.pin(obj)
        max_la = 0.0
        for f in range(1, len(samp) - 1):
            max_la = max(max_la, float(np.max(np.linalg.norm(samp[f + 1] - 2 * samp[f] + samp[f - 1], axis=1))))
        return min_clear, max_jump, max_te, max_la

    def pick_grasp_branch(self, a, obj, grasp_tgt, R, mouth, follow_thr=0.085, yaw_total=np.pi,
                          base_dir=0, ride=False, pivot=False, via_tcp=None,
                          rot_axis=(0.0, 0.0, 1.0), rot_ang=None, dry_plan_override=None,
                          n_seeds=40):
        """Per the motion rules: enumerate IK branches for the grasp pose, dry-run the
        object-master carry from each, and return the one whose carry the END EFFECTOR can
        actually FOLLOW (low tool-tracking error -> the cup stays on the box, no floating),
        then keeps the object clear of the arm, then is smoothest. Tracking error is the new
        top key: a clean+smooth branch the tool can't reach makes the box float (the 'replan
        the IK so the EE matches the box path' fix)."""
        A = self.arm[a]
        grasp_tgt = np.asarray(grasp_tgt, float); R = np.asarray(R, float)
        saved_q = self.d.qpos.copy(); rng = np.random.default_rng(0)
        seeds = [np.array(HOME, float)] + \
                [A["lo"] + rng.uniform(0, 1, 7) * (A["hi"] - A["lo"]) for _ in range(n_seeds)]
        branches = []
        for sd in seeds:
            sc = mujoco.MjData(self.m); sc.qpos[:] = saved_q
            r = ik(self.m, sc, A["pfx"], A["sid"], A["dofs"], A["qadr"], A["lo"], A["hi"],
                   grasp_tgt, seed=sd, iters=300, R_des=R)
            if not r["ok"]:
                continue
            q = sc.qpos[A["qadr"]].copy()
            if not any(np.linalg.norm(q - b) < 0.15 for b in branches):
                branches.append(q)
        best = None
        for q in branches:
            self.d.qpos[:] = saved_q; self.d.qpos[A["qadr"]] = q
            mujoco.mj_forward(self.m, self.d)
            if pivot:
                yd = +1 if yaw_total >= 0 else -1
                mc, mj, te, la = self.carry_pivot(a, obj, mouth, yaw_dir=yd, capture=False,
                                                  legs=(18, 70, 22), via_tcp=via_tcp,
                                                  via_legs=(18, 62, 40, 16),
                                                  rot_axis=rot_axis, rot_ang=rot_ang,
                                                  plan_override=dry_plan_override)  # short dry-run
            else:
                mc, mj, te, la = self.carry_master(a, obj, mouth, N=380, capture=False, reconfig=False,
                                                   yaw_total=yaw_total, base_dir=base_dir, ride=ride)
            if pivot:
                # pivot: the tool genuinely tracks — key by follow, clearance, then LOWEST te
                # before smoothness (with the te-bool failed across branches, sorting by -la
                # picked smooth-but-far branches: r0c1 float 146 vs the 72 floor)
                key = (te <= 0.030, mc >= 0.060, -te, -la)
            elif ride:
                # ride glues the box to the gripper regardless of tracking, so follow (te) no
                # longer matters -> pick the CLEAREST + SMOOTHEST branch (jerk is what's left).
                key = (mc >= 0.060, -la, -te)
            else:
                # 1) EE can FOLLOW the box (no float), 2) clear of the arm, 3) SMOOTHEST by actual
                # link-acceleration (the visual jerk), 4) lowest tracking error.
                key = (te <= follow_thr, mc >= 0.090, -la, -te)
            if best is None or key > best[0]:
                best = (key, q, mc)
        self.d.qpos[:] = saved_q; mujoco.mj_forward(self.m, self.d)
        if best is None:
            return self.solve(a, grasp_tgt, R), 1.0
        return best[1], best[2]      # (grasp config, its carry box-vs-arm clearance)

    def touching(self, a, obj):
        gid = self.arm[a]["grip"]; ob = self.bid(obj)
        for c in range(self.d.ncon):
            con = self.d.contact[c]
            if con.dist > 0.004:
                continue
            b1 = self.m.geom_bodyid[con.geom1]; b2 = self.m.geom_bodyid[con.geom2]
            if (con.geom1 in gid and b2 == ob) or (con.geom2 in gid and b1 == ob):
                return True
        return False

    def event(self, label):
        self.events.append({"frame": len(self.frames), "label": label})

    # ---- high-level capabilities ----
    def home(self, a):
        """KINEMATIC retract: joint-space lerp from the current pose straight to HOME
        (no physics servo handoff, which was snapping the arm at the end of a move)."""
        A = self.arm[a]
        q0 = self.d.qpos[A["qadr"]].copy()
        qg = np.array(HOME, float)
        n = 240
        for i in range(n):
            al = (i + 1) / n
            qi = (1 - al) * q0 + al * qg
            self.d.qpos[A["qadr"]] = qi
            for j, x in enumerate(A["act"]):
                self.d.ctrl[x] = qi[j]
            mujoco.mj_forward(self.m, self.d)
            self._apply_attach()
            if self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1

    def obj_half(self, obj, axis):
        """half-extent of an object's body along world axis 0=x,1=y,2=z."""
        bid = self.bid(obj); ext = 0.0
        for g in range(self.m.ngeom):
            if self.m.geom_bodyid[g] != bid:
                continue
            sz = self.m.geom_size[g]; t = self.m.geom_type[g]
            if t == mujoco.mjtGeom.mjGEOM_BOX:
                s = sz[axis]
            elif axis == 2:                 # cylinder half-length along its z axis
                s = sz[1]
            else:
                s = sz[0]                    # cylinder radius in x/y
            ext = max(ext, self.m.geom_pos[g][axis] + s)
        return ext

    def grasp_side(self, a, obj, robust=False, direct=False, shelf_face=False):
        """Side grasp on the object's arm-facing (+y) face along tool z = -y.
        shelf_face=True instead grips the object's SHELF-FACING (-y) face with tool +y.
        Object stays upright the whole time (no reorientation to the cubby).
        Contact-gated, then held kinematically. robust= for the small cargo
        (cylinder) whose strained belt reach the fast solver folds.

        direct= (a2_box scope): skip the 7-step creep — it re-solves per micro-step
        with short settles and drifts into a gravity-folded branch that lands the TCP
        ~675 mm off, which attach_tcp then captures as a fake carry offset. Instead:
        pre-grasp -> ONE robust move to a controllability-filtered seat pose -> short
        final push into contact -> attach ONLY if the tool is genuinely at the object
        (proximity gate), so a drooped pose can never be captured. Verified: 675 mm
        -> ~25 mm held."""
        A = self.arm[a]
        oc = self.d.xpos[self.bid(obj)].copy()
        yh = self.obj_half(obj, 1)
        if shelf_face:
            R = R_from([0, 1, 0])                     # tool +y -> grips the -y (shelf-facing) face
            face = np.array([oc[0], oc[1] - yh, oc[2]])
        else:
            R = GRASP_R[a]
            face = np.array([oc[0], oc[1] + yh, oc[2]])   # +y (arm-facing) face
        appr = R[:, 2]                                # tool z = approach dir
        sid = A["sid"]
        if direct:
            self.pin(obj)                            # freeze the box at its rest pose
            self.move_to(a, face - appr * 0.09, R, label="pre-grasp", robust=True)
            self.move_to(a, face - appr * 0.02, R, steps=150, settle=150,
                         label="grasp", robust=True)   # controllable seat pose at the face
            # NB do NOT push further: the box is pinned (immovable), so driving the
            # tool past the face just collides into a wall and folds the good pose.
            # The seat pose already sits the tool ~1 box half-width off centre — an
            # honest, small offset (attach is now cosmetic, not load-bearing).
            gap = float(np.linalg.norm(self.d.site_xpos[sid] - self.d.xpos[self.bid(obj)]))
            ok = self.touching(a, obj)
            self.detach(obj)
            if gap > 0.10:                           # refuse to capture a drooped pose
                self.event(f"grasp {obj} FAILED (gap={gap*1000:.0f}mm, not attached)")
                return False
            self.attach_tcp(obj, sid)
            self.event(f"grasp {obj} ({'contact' if ok else 'near'} {gap*1000:.0f}mm)")
            return ok
        if robust:
            # tippy cargo (standing cylinder): freeze it UPRIGHT before the approach
            # so it can't be knocked over and have a tilted pose locked into the grasp.
            self.pin(obj)
            self.move_to(a, face - appr * 0.09, R, label="pre-grasp", robust=True)
        else:
            # stable object (box): original timing — approach, then pin at contact.
            self.move_to(a, face - appr * 0.09, R, label="pre-grasp")
            self.pin(obj)
        ok = False
        for k in range(7):
            self.move_to(a, face - appr * (0.035 - 0.010 * k), R,
                         steps=22, settle=22, label="approach" if k == 0 else "",
                         robust=robust)
            if self.touching(a, obj):
                ok = True; break
        self.detach(obj)
        self.attach_tcp(obj, sid)
        self.event(f"grasp {obj} ({'contact' if ok else 'reached'})")
        return ok

    def grasp_top(self, a, obj):
        """Top grasp for bare cargo being dropped into a box (no spill risk)."""
        A = self.arm[a]
        oc = self.d.xpos[self.bid(obj)].copy()
        zt = oc[2] + self.obj_half(obj, 2)
        self.move_to(a, [oc[0], oc[1], zt + 0.16], TOP_R, label="pre-grasp", robust=True)
        self.pin(obj)
        # single robust descent: hold ONE controllable IK branch all the way to
        # contact, instead of re-solving per creep step (which drifts the strained
        # over-shoulder reach into a branch the servo can't hold -> arm folds away).
        self.move_to(a, [oc[0], oc[1], zt + 0.005], TOP_R, steps=90, settle=60,
                     label="descend", robust=True)
        ok = self.touching(a, obj)
        self.detach(obj)
        self.attach_tcp(obj, A["sid"])
        self.event(f"grasp {obj} ({'contact' if ok else 'reached'})")
        return ok

    def offset(self, a, obj):
        """World offset object_centre - TCP while grasped; constant because the
        tool orientation is fixed."""
        return self.d.xpos[self.bid(obj)].copy() - self.d.site_xpos[self.arm[a]["sid"]].copy()

    def place_in_cell(self, a, obj, cell, stay=False, hh=None, robust=False, preplace=True):
        """Side-insert a held object into a front cubby (the universal placement).
        stay=True pins it where it lands (for a tippy object that would topple if
        released to physics). hh overrides the object half-height along its current
        UP axis (a reoriented sheet stands on a different extent than it grasps).
        robust= for a small object riding ON the pinch (zero standoff) whose deeper
        cubby reach the fast solver folds. preplace=False drops the intermediate
        pre-place waypoint (it forced a small reconfiguration / spike); the warm
        Cartesian move goes transit -> seat directly."""
        R = GRASP_R[a]; off = self.offset(a, obj)
        cell = np.array(cell, float)               # cubby interior (object rest point)
        if hh is None:
            hh = self.obj_half(obj, 2)             # object half-height
        floor_top = cell[2] - 0.5 * G.ROW_DZ + 0.008   # shelf-floor surface for this row
        seat = np.array([cell[0], cell[1], floor_top + hh])   # object rests ON the floor
        self.move_to(a, cell + [0, 0.40, 0.06] - off, R, steps=200, label="transit", robust=robust)
        if preplace:
            self.move_to(a, seat + [0, 0.18, 0] - off, R, steps=130, label="pre-place", robust=robust)
        self.move_to(a, seat - off, R, steps=200, label="seat", robust=robust)   # gently, on the floor
        self.event(f"{obj} seated")                 # checklist phase marker (place vs return)
        if stay:
            self.detach(obj); self.pin(obj)         # hold where it landed (no topple)
        else:
            self.detach(obj); self.step(30)         # release with no drop
        self.move_to(a, seat + [0, 0.26, 0.02] - off, R, label="retract", robust=robust)

    def place_cosmetic(self, a, obj, cell):
        """Honest grasp + honest carry, then a short SCRIPTED glide of the object the
        last few cm into the cubby while the tool HOLDS its controllable mouth pose.

        Why: arm 2 grasps from the rear belt and the rack is deep in the front
        hemisphere; physically seating the tool deep in the cubby needs a mid-carry
        elbow-flip that swings the rigidly-held object (the placement loop). The arm
        genuinely can't hold a deep-cubby pose. So we keep the parts the eye watches
        honest (grasp + carry, tool on the object) and script ONLY the final insert,
        with the tool parked at the cubby opening — not a 0.6 m fake offset, a few cm.
        """
        R = GRASP_R[a]; off = self.offset(a, obj)
        cell = np.array(cell, float)
        hh = self.obj_half(obj, 2)
        floor_top = cell[2] - 0.5 * G.ROW_DZ + 0.008
        seat = np.array([cell[0], cell[1], floor_top + hh])
        # carry to a controllable pose with the tool AT the cubby mouth (object on tool)
        self.move_to(a, cell + [0, 0.22, 0.0] - off, R, steps=180, settle=30,
                     label="carry", robust=True)
        # cosmetic insert: tool HOLDS its pose kinematically (no physics sag); object
        # glides the last few cm to the seat.
        A = self.arm[a]
        held_q = self.d.qpos[A["qadr"]].copy()
        box0 = self.d.xpos[self.bid(obj)].copy()
        upq = self.d.xquat[self.bid(obj)].copy()
        self.detach(obj)
        adr = self.qadr_of(self.bid(obj))
        N = 90
        for i in range(N):
            al = (i + 1) / N
            pos = box0 * (1 - al) + seat * al
            self.d.qpos[adr:adr + 3] = pos
            self.d.qpos[adr + 3:adr + 7] = upq
            self.d.qpos[A["qadr"]] = held_q          # hold the arm exactly (no sag)
            self.d.qvel[:] = 0
            mujoco.mj_forward(self.m, self.d)
            if self._k % CAP_EVERY == 0:
                self.capture()
            if self._sync is not None:
                self._sync(self)
            self._k += 1
        self.pin(obj)                                # rests on the cubby floor
        self.event(f"{obj} seated")

    def place_from_top(self, a, obj, cell):
        """Place a TOP-grasped cargo into an open-topped (top-row) cubby by lowering
        from directly above and releasing onto the shelf floor. Front-facing cubbies
        in lower rows have a shelf above them, so only the top row is top-accessible."""
        off = self.offset(a, obj)
        cell = np.array(cell, float)
        hh = self.obj_half(obj, 2)
        floor_top = cell[2] - 0.5 * G.ROW_DZ + 0.008
        over = np.array([cell[0], cell[1], cell[2] + 0.22])     # clear above the open cubby
        seat = np.array([cell[0], cell[1], floor_top + hh + 0.03])  # just above the floor
        self.move_to(a, over - off, TOP_R, steps=200, label="transit", robust=True)
        self.move_to(a, seat - off, TOP_R, steps=140, label="lower", robust=True)
        self.detach(obj)                            # release -> short drop onto the shelf
        self.step(70)
        self.move_to(a, over - off, TOP_R, label="retract", robust=True)

    def load_into_box(self, a, cargo, box):
        """Top-grasp cargo, lower into the box's open top, drop + contain. Stays in
        the narrow controllable top-access zone: a LOW approach just clearing the
        box rim, never the high (sagging) overhead pose."""
        self.grasp_top(a, cargo)
        bc = self.d.xpos[self.bid(box)].copy()
        self.pin(box)                                # hold the box upright; the cargo
        box_top = bc[2] + BOX_HZ                      # entering it must not shove it off-axis
        off = self.offset(a, cargo)
        # carry the cargo over the open box, just above the rim (controllable).
        # robust: this is a strained over-shoulder top pose; the fast solver folds it.
        # NB reaching deep INTO the box is uncontrollable (arm folds), so we don't —
        # we release above the rim and let it DROP in. The box is PINNED, so the
        # drop can't shove it off-axis.
        self.move_to(a, np.array([bc[0], bc[1], box_top + 0.04]) - off, TOP_R, steps=150, label="over-box", robust=True)
        self.detach(cargo)                           # release -> drops into the pinned box
        self.step(80)                                # fall + settle on the box floor
        self.attach_body(cargo, box)                 # containment: rides with the box
        self.event(f"{cargo} contained in {box}")
        self.move_to(a, np.array([bc[0], bc[1], box_top + 0.10]) - off, TOP_R, label="clear", robust=True)


def combo_load_convey(arm, cargo, box, name, title):
    """Load the cargo INTO the arm's own box (verified containment, not a rim-drop),
    then the CONVEYOR carries box+cargo across, ending EXACTLY at the other box's
    build position. Everything on the belt moves with it: the other free item rides
    too and is COLLECTED by the end housing (feeder doubles as collector at -x; a
    mirrored collector sits at +x) before it would fall off.
    Sheet (a1): the 92x88 panel cannot pass the ~96x76 opening flat -> pitched to
    STANDING via the proven pivot machinery (branch picked by dry-run), lowered in
    until the cup nears the rim, released, short settle inside.
    Tube (a2): top-grasped, lowered until its bottom is 25mm inside, released."""
    c = Cell()
    c.pin_loose(); c.step(20)
    sid = c.arm[arm]["sid"]; A = c.arm[arm]
    other = "box2" if arm == 1 else "box1"
    swept = "tube1" if arm == 1 else "sheet1"     # the other free item on the belt
    tgt_pos = c.d.xpos[c.bid(other)].copy()       # exact destination = other box's build pos
    oa = 2 if arm == 1 else 1                     # pre-shelve the other arm's box
    cell_o = G.shelf_cell(oa, 1, 1)
    floor_o = cell_o[2] - 0.5 * G.ROW_DZ + 0.008
    adr_o = c.qadr_of(c.bid(other))
    c.detach(other)
    c.d.qpos[adr_o:adr_o + 3] = [cell_o[0], cell_o[1], floor_o + BOX_HZ]
    c.d.qpos[adr_o + 3:adr_o + 7] = [1, 0, 0, 0]
    mujoco.mj_forward(c.m, c.d); c.pin(other); c.step(5)
    c.frames = []; c.events = []
    c.event(title)
    oc = c.d.xpos[c.bid(cargo)].copy()
    bc = c.d.xpos[c.bid(box)].copy()
    ch = c.obj_half(cargo, 2)
    box_top = bc[2] + BOX_HZ
    def make_rest(q_seed):
        Rrest = R_from([0, 1, 0])
        for off_r in ((0, -0.25, 0), (0, -0.25, 0.04), (0.04, -0.25, 0.04), (0, -0.30, 0.06)):
            sc = mujoco.MjData(c.m); sc.qpos[:] = c.d.qpos
            r = ik(c.m, sc, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                   oc + np.array(off_r, float), seed=q_seed, iters=300, R_des=Rrest)
            q = sc.qpos[A["qadr"]].copy()
            sv = c.d.qpos.copy()
            c.d.qpos[A["qadr"]] = q; mujoco.mj_forward(c.m, c.d)
            ok = r["ok"] and c._links_clear_structures(arm)
            c.d.qpos[:] = sv; mujoco.mj_forward(c.m, c.d)
            if ok:
                return q
        raise RuntimeError(f"{name}: no clear branch-aligned rest pose found")
    if arm == 1:
        # ---- SHEET: pitch to standing en route (pivot machinery), lower into the box
        so = ch + (G.SUCTION_TIP_LEN - G.SUCTION_LEN) - 0.008
        tcp_g = oc + np.array([0.0, 0.0, so])
        seat = np.array([bc[0], bc[1], box_top + 0.005])    # standing center: bottom 39mm in
        # KEY: pitch +90 so the cup grips the sheet's NEAR (-y) face -> the wrist stays
        # on the base side of the belt for the whole standing traverse. The far-face
        # (-90) variant is intractable there (te 126-378, static solve 12.5mm vs 2.8mm;
        # probed exhaustively: forward, backward, with/without the comfort via).
        tseat = seat - np.array([0.0, so, 0.0])             # cup on the near side
        lift = tcp_g + np.array([0.0, 0.0, 0.16])
        mid = np.array([-1.30, -0.18, 1.16])                # pitch zone, front of the belt
        overb = tseat + np.array([0.0, 0.0, 0.11])
        HP = np.pi / 2
        def mkplan(n1, n2, n3, n4):
            return [(n1, lambda u: tcp_g + u * (lift - tcp_g), lambda u: 0.0),
                    (n2, lambda u: lift + u * (mid - lift), lambda u: HP * u),
                    (n3, lambda u: mid + u * (overb - mid), lambda u: HP),
                    (n4, lambda u: overb + u * (tseat - overb), lambda u: HP)]
        ROT = dict(rot_axis=(1.0, 0.0, 0.0), rot_ang=HP)
        q_grasp, gmc = c.pick_grasp_branch(arm, cargo, tcp_g, TOP_R, seat, pivot=True,
                                           dry_plan_override=mkplan(10, 30, 26, 12),
                                           n_seeds=22, **ROT)
        REST = make_rest(q_grasp)
        c.d.qpos[A["qadr"]] = REST
        mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
        c.move_to_q(arm, q_grasp, steps=150, label="unfold")
        c.detach(cargo); c.attach_tcp(cargo, sid); c.event(f"grasp {cargo}")
        c.carry_pivot(arm, cargo, seat, plan_override=mkplan(50, 170, 150, 70), **ROT)
        c.event("release")
        c.detach(cargo)
        c.step(70)                                # short drop inside; settles/leans within
        c.attach_body(cargo, box)
        c.event(f"{cargo} contained in {box}")
        Rt_now = c.d.site_xmat[sid].reshape(3, 3).copy()
        c.move_to(arm, tseat + np.array([0, -0.05, 0.18]), Rt_now, steps=70, label="clear")
        c.move_to_q(arm, REST, steps=160, label="to-home")
    else:
        # ---- TUBE via SIDE GRASP: the top-down pose above the box is unreachable
        # accurately ANYWHERE here (probed: 47-130mm error at z 1.04-1.20 — box2's
        # spot was validated for side grasps), but the tool+y side pose is the proven
        # ~2mm-accurate class in this exact region (every tube-pick ends in it).
        # Carry the tube over the walls jaw-high, present it CENTERED with its bottom
        # 5mm above the rim, release -> centered drop to the box floor.
        so = c.obj_half(cargo, 1) + 0.02
        Rg2 = np.array([[-1.0, 0, 0], [0, -1.0, 0], [0, 0, 1.0]]) @ GRASP_R[arm]  # tool +y
        tcp_g = oc - np.array([0.0, so, 0.0])
        q_grasp = c.solve(arm, tcp_g, Rg2, robust=True)
        REST = make_rest(q_grasp)
        c.d.qpos[A["qadr"]] = REST
        mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
        c.move_to_q(arm, q_grasp, steps=150, label="unfold")
        c.detach(cargo); c.attach_tcp(cargo, sid); c.event(f"grasp {cargo}")
        off = c.offset(arm, cargo)
        c.move_to(arm, tcp_g + np.array([0, 0, 0.115]), Rg2, steps=100, label="lift")
        c.move_to(arm, np.array([bc[0], bc[1], box_top + 0.015 + ch]) - off, Rg2,
                  steps=150, label="over-box")
        c.move_to(arm, np.array([bc[0], bc[1], box_top + 0.005 + ch]) - off, Rg2,
                  steps=60, label="present")
        c.event("release")
        c.detach(cargo)
        c.step(80)                                # centered drop to the box floor
        c.attach_body(cargo, box)
        c.event(f"{cargo} contained in {box}")
        c.move_to(arm, np.array([bc[0], bc[1] - 0.03, box_top + 0.14 + ch]) - off, Rg2,
                  steps=80, label="clear")
        c.move_to_q(arm, REST, steps=160, label="to-home")
    # ---- conveyor: EVERYTHING on the belt moves; the swept item is collected by the
    # end housing before it would fall off; box+cargo stop exactly on the target
    c.event("conveyor")
    adr_b = c.qadr_of(c.bid(box)); c.detach(box)
    adr_s = c.qadr_of(c.bid(swept)); c.detach(swept)
    p0 = c.d.qpos[adr_b:adr_b + 3].copy()
    s0 = c.d.qpos[adr_s:adr_s + 3].copy()
    stop_x = (G.BELT_X1 - 0.18) if arm == 1 else (G.BELT_X0 + 0.18)   # housing centers
    n = 600
    for i in range(n):
        al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / n)
        pos = (1 - al) * p0 + al * tgt_pos
        disp = pos[0] - p0[0]
        c.d.qpos[adr_b:adr_b + 3] = pos
        sx = s0[0] + disp
        sx = min(sx, stop_x) if arm == 1 else max(sx, stop_x)
        c.d.qpos[adr_s:adr_s + 3] = [sx, s0[1], s0[2]]
        c.d.qvel[:] = 0
        mujoco.mj_forward(c.m, c.d)
        c._apply_attach()                          # contained cargo rides the box
        mujoco.mj_forward(c.m, c.d)
        if c._k % CAP_EVERY == 0:
            c.capture()
        if c._sync is not None:
            c._sync(c)
        c._k += 1
    c.pin(box); c.pin(swept)
    c.event("delivered")
    c.capture()
    c.event("done")
    bf = c.d.xpos[c.bid(box)].copy()
    rel = c.d.xpos[c.bid(cargo)] - bf
    print(f"[{name}] box final err = {np.linalg.norm(bf - tgt_pos) * 1000:.1f} mm; "
          f"cargo rel box = {np.round(rel, 3)}")
    _save(c, name, title)


# ---------------------------------------------------------------------------
def _save(c, name, title):
    out = {"bodies": c.bodies, "dt": float(c.m.opt.timestep * CAP_EVERY),
           "frames": c.frames, "events": c.events, "title": title}
    with open(os.path.join(WEB, f"anim_{name}.json"), "w") as fh:
        json.dump(out, fh)
    print(f"  -> web/anim_{name}.json  ({len(c.frames)} frames)")


def combo_box(arm, box, cell, name, title, direct=False, shelf_face=False, yaw_total=np.pi,
              base_dir=0, ref_cell=None, ride=False, pivot=False, pivot_via_cell=None):
    c = Cell()
    c.pin_loose()                     # freeze every item at its initial rest pose
    c.step(20)                        # let the arm stabilize at home (items frozen)
    c.frames = []; c.events = []      # record from the steady, settled state
    c.event(title)
    if shelf_face and not direct:
        sid = c.arm[arm]["sid"]
        oc = c.d.xpos[c.bid(box)].copy(); yh = c.obj_half(box, 1)
        Rg = R_from([0, 1, 0])                            # tool +y -> grips the shelf-facing face
        grasp_tgt = np.array([oc[0], oc[1] - yh, oc[2]]) - Rg[:, 2] * 0.02
        cellv = np.array(cell, float)
        floor_top = cellv[2] - 0.5 * G.ROW_DZ + 0.008
        seat = np.array([cellv[0], cellv[1], floor_top + c.obj_half(box, 2)])
        mouth = seat + [0, 0.12, 0]                       # cubby opening (tool halts here)
        # pick the grasp BRANCH using a NEIGHBOUR cubby's seat when given (ref_cell): neighbouring
        # cubbies share the same body-sweep direction, so r0c2 reuses r0c1's branch (sweeps +z)
        # and just carries ~18cm further, instead of the picker choosing a lone opposite-sweep branch.
        sel_seat = seat
        if ref_cell is not None:
            rc = np.array(ref_cell, float)
            sel_seat = np.array([rc[0], rc[1], rc[2] - 0.5 * G.ROW_DZ + 0.008 + c.obj_half(box, 2)])
        via_tcp = None
        if pivot and pivot_via_cell is not None:
            # turn-comfort waypoint = the via cell's stage point in TCP space
            vc = np.array(pivot_via_cell, float)
            via_seat = np.array([vc[0], vc[1], vc[2] - 0.5 * G.ROW_DZ + 0.008 + c.obj_half(box, 2)])
            via_tcp = via_seat + np.array([0.0, yh + 0.02, 0.0]) + np.array([0.0, 0.22, 0.10])
        q_grasp, gmc = c.pick_grasp_branch(arm, box, grasp_tgt, Rg, sel_seat, yaw_total=yaw_total,
                                           base_dir=base_dir, ride=ride, pivot=pivot, via_tcp=via_tcp)
        orbit_mouth = None
        if ref_cell is not None:                          # do the ROTATION at the neighbour's
            orbit_mouth = sel_seat + [0, 0.12, 0]         # mouth (tracks tight), then translate over
        REST = c.rest_pose(arm, box, seed=q_grasp)         # conveyor-facing, clear; grasp branch
        # 0. start AT the rest pose (frame 0)
        c.d.qpos[c.arm[arm]["qadr"]] = REST
        mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
        # 1. unfold REST -> grasp
        c.move_to_q(arm, q_grasp, steps=170, label="unfold")
        # 2. grip the box (tool is at its shelf face)
        c.detach(box); c.attach_tcp(box, sid); c.event(f"grasp {box}")
        # 3. object-master carry ALL THE WAY to the seat — the tool tracks the box the
        #    whole way (no cosmetic self-glide). The gripped face ends at the mouth, so
        #    the tool stops at the opening (no overshoot) with the box seated.
        if pivot:
            # Arm-2 pivot carry: 180 about the jaw pinch DURING transit (front hemisphere),
            # box on its planned pose, tool genuinely tracks — no ride glue, no end settle.
            c.carry_pivot(arm, box, seat, yaw_dir=(+1 if yaw_total >= 0 else -1), via_tcp=via_tcp)
        elif orbit_mouth is not None:
            # rotate the box at the NEIGHBOUR'S mouth (where this branch tracks tight, no float),
            # then translate it over in front of the rack to THIS cubby and insert — pure
            # translations track tight too. (r0c2 reuses r0c1's clean rotation, then slides +x.)
            shift_pt = np.array([seat[0], orbit_mouth[1], seat[2]])      # this cubby's mouth
            c.carry_master(arm, box, orbit_mouth, N=440, reconfig=False, yaw_total=yaw_total,
                           ride=ride, settle=False)                                          # rotate (held)
            c.carry_master(arm, box, shift_pt, N=120, reconfig=False, yaw_total=0.0,
                           ride=ride, settle=False)                                          # +x (held)
            c.carry_master(arm, box, seat, N=120, reconfig=False, yaw_total=0.0, ride=ride)  # insert+settle
        else:
            c.carry_master(arm, box, seat, N=560, reconfig=False, yaw_total=yaw_total, base_dir=base_dir,
                       ride=ride)               # ride: box glued to the gripper (Arm 2's long jaw)
        c.event(f"{box} seated")
        # 4. RETURN to rest (rules §Return to home): 4a short retract straight OUT of the cubby,
        #    then 4b a smooth path from that post-retract pose DIRECTLY to home (no detour back
        #    through the grasp/box). The 180° tool reorientation (faced the rack -> faces the
        #    conveyor) is realised as a JOINT-space swing (the base joint sweeps the arm around),
        #    which a straight Cartesian tool-line can't do without a branch flip. Ends exactly
        #    on REST (frame0 == frameN).
        c.move_to(arm, seat + [0, 0.18, 0.05], GRASP_R[arm], steps=70, label="retract",
                  robust=pivot)        # pivot mode: solved retract (warm-tracked was 128mm off)
        c.move_to_q(arm, REST, steps=200, label="to-home")
        c.capture()                                        # lock the final frame on REST
    else:
        c.grasp_side(arm, box, direct=direct, shelf_face=shelf_face)
        if direct:
            c.place_cosmetic(arm, box, cell)   # honest grasp+carry, scripted final insert
        else:
            c.place_in_cell(arm, box, cell)
        c.home(arm)
    c.event("done")
    final = c.d.xpos[c.bid(box)].copy()
    print(f"[{name}] box xy err = {np.linalg.norm((final-cell)[:2])*1000:.0f} mm")
    _save(c, name, title)


def combo_tube(arm, tube, cell, name, title):
    """Tube: honest side-grasp at the relocated (controllable) pickup, honest carry,
    then the scripted final insert (place_cosmetic). place_cosmetic pins it upright on
    landing — a standing cylinder is tippy. Replaces the old snap_to_tcp teleport."""
    c = Cell()
    c.pin_loose()                     # freeze every item at its initial rest pose
    c.step(20)                        # let the arm stabilize at home (items frozen)
    c.frames = []; c.events = []      # record from the steady, settled state
    c.event(title)
    c.grasp_side(arm, tube, direct=True)         # honest grasp at the controllable pickup
    c.place_cosmetic(arm, tube, cell)            # honest carry + scripted final insert (pins upright)
    c.home(arm)
    c.event("done")
    of = c.d.xpos[c.bid(tube)].copy()
    print(f"[{name}] tube xy err = {np.linalg.norm((of-np.array(cell))[:2])*1000:.0f} mm")
    _save(c, name, title)


def combo_sheet(arm, sheet, cell, name, title):
    """Sheet via the plan-B pivot pattern (replaces the pre-checklist recipe, which
    failed items 1/2/4/5/9 — conveyor sweeps, link5 in rack, 197mm start!=end):
    top grasp at the relocated controllable pickup, then carry_pivot with a 90-deg
    PITCH about the cup (rot_axis=x, -pi/2: flat under the cup -> standing, cup on
    the +y face), pitch ending at the comfort waypoint (r1c1's stage zone, proven),
    then pure translations to the seat. No glue, no settle, no scripted glide."""
    c = Cell()
    c.pin_loose()                     # freeze every item at its initial rest pose
    c.step(20)                        # let the arm stabilize at home (items frozen)
    c.frames = []; c.events = []      # record from the steady, settled state
    c.event(title)
    sid = c.arm[arm]["sid"]
    oc = c.d.xpos[c.bid(sheet)].copy()
    th = c.obj_half(sheet, 2)                     # flat half-thickness (grasped face offset)
    sh = c.obj_half(sheet, 1)                     # standing half-height after the pitch
    # cup standoff from the sheet CENTER: the VISUAL cup extends (TIP_LEN - SUCTION_LEN)
    # = 45mm past the kinematic TCP; embed the drawn tip 8mm into the 20mm sheet so the
    # sheet visibly rides AT the tip (3mm standoff buried the wrist in the rack and poked
    # the cup out the sheet's far side)
    so = th + (G.SUCTION_TIP_LEN - G.SUCTION_LEN) - 0.008
    grasp_tgt = oc + np.array([0.0, 0.0, so])
    cellv = np.array(cell, float)
    floor_top = cellv[2] - 0.5 * G.ROW_DZ + 0.008
    seat = np.array([cellv[0], cellv[1], floor_top + sh])
    c11 = G.shelf_cell(arm, 1, 1)                 # comfort waypoint: pitch ends at r1c1's
    seat11 = np.array([c11[0], c11[1], c11[2] - 0.5 * G.ROW_DZ + 0.008 + sh])
    via = seat11 + np.array([0.0, so + 0.22, 0.10])
    ROT = dict(rot_axis=(1.0, 0.0, 0.0), rot_ang=-np.pi / 2)
    # robust-branch fast path + dry gate, enumeration fallback (same as combo_sheet_pick:
    # the enumeration alone picked non-tracking branches on the bottom row after the
    # visual-tip standoff moved every waypoint)
    q_grasp = c.solve(arm, grasp_tgt, TOP_R, robust=True)
    sv = c.d.qpos.copy()
    c.d.qpos[c.arm[arm]["qadr"]] = q_grasp; mujoco.mj_forward(c.m, c.d)
    mc, mj, te, la = c.carry_pivot(arm, sheet, seat, capture=False, via_tcp=via,
                                   via_legs=(18, 62, 40, 16), **ROT)
    c.d.qpos[:] = sv; mujoco.mj_forward(c.m, c.d)
    print(f"   robust-branch dry: te={te*1000:.0f}mm jump={mj:.2f} clear={mc*1000:.0f}mm")
    if te > 0.060 or mj > 1.5 or mc < 0.065:
        q_grasp, gmc = c.pick_grasp_branch(arm, sheet, grasp_tgt, TOP_R, seat, pivot=True,
                                           via_tcp=via, **ROT)
        # re-dry from the branch ACTUALLY chosen — the rescue decision must be keyed on
        # it, not on the rejected robust branch (r0c2: robust te=388 but enum tracks)
        sv = c.d.qpos.copy()
        c.d.qpos[c.arm[arm]["qadr"]] = q_grasp; mujoco.mj_forward(c.m, c.d)
        mc, mj, te, la = c.carry_pivot(arm, sheet, seat, capture=False, via_tcp=via,
                                       via_legs=(18, 62, 40, 16), **ROT)
        c.d.qpos[:] = sv; mujoco.mj_forward(c.m, c.d)
        print(f"   enum-branch dry:   te={te*1000:.0f}mm jump={mj:.2f} clear={mc*1000:.0f}mm")
    # end-seed rescue ONLY where the dry shows the insert diverging (te) — a static pull
    # on a cleanly-tracking cubby flips its branch instead (r0c2: 89 -> 343 jerk)
    rescue = te > 0.030
    REST = c.rest_pose(arm, sheet, seed=q_grasp)
    c.d.qpos[c.arm[arm]["qadr"]] = REST           # 0. start AT the rest pose (frame 0)
    mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
    c.move_to_q(arm, q_grasp, steps=170, label="unfold")
    c.detach(sheet); c.attach_tcp(sheet, sid); c.event(f"grasp {sheet}")
    c.carry_pivot(arm, sheet, seat, via_tcp=via, end_seed=rescue, **ROT)
    c.event(f"{sheet} seated")
    # warm retract: the arm ends ON the robust-solved seat pose (end_seed), so warm IK
    # tracks straight out; robust=True here re-solved into a FAR branch (jerk 223 r0c1)
    c.move_to(arm, seat + [0, 0.20, 0], GRASP_R[arm], steps=70, label="retract")  # pure +y:
    # the insert came in along -y; the diagonal (+y,+z) retract branch-flipped at r0c1
    c.move_to_q(arm, REST, steps=340, label="to-home")   # slower swing: the end-seeded
    # placing branch can sit far from REST in joint space (r0c1 jerk 223 at 200 steps)
    c.capture()
    c.event("done")
    final = c.d.xpos[c.bid(sheet)].copy()
    print(f"[{name}] sheet xy err = {np.linalg.norm((final - cellv)[:2]) * 1000:.0f} mm")
    _save(c, name, title)


def combo_sheet_pick(arm, sheet, cell, name, title):
    """REVERSE of combo_sheet: the sheet STARTS standing in the cubby (scene is staged
    that way before recording); the arm grasps its +y face, extracts straight out the
    mouth, transits back, pitches +90 at the comfort zone (standing -> flat under the
    cup), and lowers it flat onto the conveyor at its pickup spot. Same plan-B pivot
    machinery via plan_override (the legs run in reverse order); branch picked by
    dry-run (the single robust solve branch-flips on the bottom row)."""
    c = Cell()
    c.pin_loose(); c.step(20)
    sid = c.arm[arm]["sid"]
    th = c.obj_half(sheet, 2)                     # flat half-thickness
    sh = c.obj_half(sheet, 1)                     # standing half-height
    so = th + (G.SUCTION_TIP_LEN - G.SUCTION_LEN) - 0.008   # see combo_sheet: visual-tip
    belt = c.d.xpos[c.bid(sheet)].copy()          # the sheet's belt rest spot (build pos)
    cellv = np.array(cell, float)
    floor_top = cellv[2] - 0.5 * G.ROW_DZ + 0.008
    seat = np.array([cellv[0], cellv[1], floor_top + sh])
    tcp_end0 = belt + np.array([0.0, 0.0, so])
    # REST must be computed while the sheet is STILL AT THE BELT: rest_candidates keys
    # off the object's current position, and with the sheet staged in the cubby every
    # rest target lands behind the rack and fails clearance (-> None -> NaN poisoning).
    q_end = c.solve(arm, tcp_end0 + np.array([0, 0, 0.15]), TOP_R)
    REST = c.rest_pose(arm, sheet, seed=q_end)
    if REST is None:
        raise RuntimeError(f"{name}: no clear rest pose found")
    # stage the scene: sheet standing in the cubby (exactly the post-place pose)
    Rstand_obj = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0.0]])    # rotx(-pi/2)
    bq = np.zeros(4); mujoco.mju_mat2Quat(bq, Rstand_obj.reshape(9))
    adr = c.qadr_of(c.bid(sheet))
    c.detach(sheet)
    c.d.qpos[adr:adr + 3] = seat; c.d.qpos[adr + 3:adr + 7] = bq
    mujoco.mj_forward(c.m, c.d); c.pin(sheet); c.step(10)
    c.frames = []; c.events = []                  # record from the staged state
    c.event(title)
    Rg = _ROTX_NEG90 @ TOP_R                      # tool pose holding the STANDING sheet
    tcp_g = seat + np.array([0.0, so, 0.0])
    tcp_end = belt + np.array([0.0, 0.0, so])     # cup on top, sheet flat on the belt
    hover = tcp_end + np.array([0.0, 0.0, 0.16])
    mouth = tcp_g + np.array([0.0, 0.12, 0.0])
    c11 = G.shelf_cell(arm, 1, 1)
    seat11 = np.array([c11[0], c11[1], c11[2] - 0.5 * G.ROW_DZ + 0.008 + sh])
    via = seat11 + np.array([0.0, so + 0.22, 0.10])
    HP = np.pi / 2
    def mkplan(n1, n2, n3, n4):
        return [(n1, lambda u: tcp_g + u * (mouth - tcp_g), lambda u: 0.0),
                (n2, lambda u: mouth + u * (via - mouth), lambda u: 0.0),
                (n3, lambda u: via + u * (hover - via), lambda u: HP * u),
                (n4, lambda u: hover + u * (tcp_end - hover), lambda u: HP)]
    ROT = dict(rot_axis=(1.0, 0.0, 0.0), rot_ang=HP)
    # fast path: the robust-solve branch, validated by ONE short dry run. Full branch
    # enumeration only as fallback — enumerated branches can dry-pass on the short plan
    # yet grind warm-IK at full length (iters saturate every frame -> blows the 45s wall).
    q_grasp = c.solve(arm, tcp_g, Rg, robust=True)
    sv = c.d.qpos.copy()
    c.d.qpos[c.arm[arm]["qadr"]] = q_grasp; mujoco.mj_forward(c.m, c.d)
    mc, mj, te, la = c.carry_pivot(arm, sheet, belt, capture=False,
                                   plan_override=mkplan(10, 22, 32, 10), **ROT)
    c.d.qpos[:] = sv; mujoco.mj_forward(c.m, c.d)
    print(f"   robust-branch dry: te={te*1000:.0f}mm jump={mj:.2f} clear={mc*1000:.0f}mm")
    # NOTE: the dry plan is ~6x coarser than the real carry, so per-frame joint steps are
    # ~6x larger — gate jump at the short-plan scale (1.5), not the capture scale (0.6)
    if te > 0.030 or mj > 1.5 or mc < 0.065:    # mc margin: checklist item 6 needs >60mm
        q_grasp, gmc = c.pick_grasp_branch(arm, sheet, tcp_g, Rg, tcp_end, pivot=True,
                                           dry_plan_override=mkplan(10, 22, 32, 10),
                                           n_seeds=22, **ROT)
    # REST seeded from the BELT-side end pose (not the cubby grasp): the return lerp is
    # then short/clean, and the unfold REST->cubby-grasp is the reverse of the place
    # anims' proven rack->REST swing (cubby-seeded REST swept link5 through the rack
    # corner in both lerps).
    # unfold via the carry's own via pose (joint-near the grasp, in FRONT of the rack):
    # a single REST->grasp lerp sweeps link5 under the rack's bottom-left corner.
    A = c.arm[arm]
    sc = mujoco.MjData(c.m); sc.qpos[:] = c.d.qpos
    ik(c.m, sc, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
       via, seed=q_grasp, iters=300, R_des=Rg)
    q_pre = sc.qpos[A["qadr"]].copy()
    c.d.qpos[c.arm[arm]["qadr"]] = REST           # 0. start AT the rest pose (frame 0)
    mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
    c.move_to_q(arm, q_pre, steps=100, label="unfold-1")
    # approach: joint-lerp only to a PRE-grasp pose in front of the mouth, then a short
    # straight-in Cartesian move to the face (lerping directly to the grasp visibly
    # clipped the wrist into the rack front)
    sc2 = mujoco.MjData(c.m); sc2.qpos[:] = c.d.qpos
    ik(c.m, sc2, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
       tcp_g + np.array([0.0, 0.10, 0.0]), seed=q_grasp, iters=300, R_des=Rg)
    q_appr = sc2.qpos[A["qadr"]].copy()
    c.move_to_q(arm, q_appr, steps=70, label="unfold-2")
    c.move_to(arm, tcp_g, Rg, steps=45, label="approach")
    c.detach(sheet); c.attach_tcp(sheet, sid); c.event(f"grasp {sheet}")
    c.carry_pivot(arm, sheet, belt, plan_override=mkplan(50, 130, 210, 60), **ROT)
    c.event(f"{sheet} placed")
    c.move_to(arm, tcp_end + [0, 0, 0.15], TOP_R, steps=70, label="retract", robust=True)
    # to-home: Cartesian tool-master path (return_to_rest) — the joint lerp from the
    # belt-retract pose swung the elbow back through the rack corner.
    c.return_to_rest(arm, REST, n=120, reconfig=False, label="to-home")   # open-space path;
    # per-step reconfig sampling (19 MjData x ik120 per near-margin step) blows the 45s wall
    c.move_to_q(arm, REST, steps=30, label="settle-rest")    # exact frame0 == frameN
    c.capture()
    c.event("done")
    final = c.d.xpos[c.bid(sheet)].copy()
    print(f"[{name}] sheet-on-belt xy err = {np.linalg.norm((final - belt)[:2]) * 1000:.0f} mm")
    _save(c, name, title)


_ROTX_NEG90 = np.array([[1.0, 0, 0], [0, 0, 1], [0, -1, 0]])


def combo_tube_pick(arm, tube, cell, name, title):
    """Arm-2 REVERSE tube run: the tube starts STANDING in the cubby; the jaw grasps its
    +y side (tool -y), extracts out the mouth, transits back doing the 180 tool turn at
    the comfort zone (the tube is radially symmetric - only the JAW pose turns), and sets
    it upright on the conveyor at its pickup spot.
    PLANNING IS BACKWARD (record-and-replay): greedy warm IK tracks this corridor only in
    the belt->rack direction (probed: 13mm vs ~200mm in reverse, every branch/direction).
    So the route is marched hover->via->mouth->grasp from the robust belt-hover solve,
    the joint trajectory is RECORDED, and the animation REPLAYS it: the recorded tail
    (mouth->grasp) plays as the approach, the whole recording plays reversed as the carry.
    Branch continuity is guaranteed by construction; the tube rides its planned pose."""
    c = Cell()
    c.pin_loose(); c.step(20)
    sid = c.arm[arm]["sid"]; A = c.arm[arm]
    tr = c.obj_half(tube, 1)                      # cylinder radius
    tz = c.obj_half(tube, 2)                      # half-height
    so = tr + 0.02                                # jaw standoff from the gripped side
    belt = c.d.xpos[c.bid(tube)].copy()
    cellv = np.array(cell, float)
    seat = np.array([cellv[0], cellv[1], cellv[2] - 0.5 * G.ROW_DZ + 0.008 + tz])
    tcp_end = belt + np.array([0.0, -so, 0.0])    # belt place pose: tool +y
    # (REST is derived AFTER backward planning, warm from the carry's end branch)
    # stage: tube standing in the cubby
    adr = c.qadr_of(c.bid(tube))
    c.detach(tube)
    c.d.qpos[adr:adr + 3] = seat; c.d.qpos[adr + 3:adr + 7] = [1, 0, 0, 0]
    mujoco.mj_forward(c.m, c.d); c.pin(tube); c.step(10)
    c.frames = []; c.events = []
    c.event(title)
    Rg = GRASP_R[arm]                             # tool -y at the cubby
    tcp_g = seat + np.array([0.0, so, 0.0])
    hover = tcp_end + np.array([0.0, 0.0, 0.16])
    mouth = tcp_g + np.array([0.0, 0.12, 0.0])
    c11 = G.shelf_cell(arm, 1, 1)
    seat11 = np.array([c11[0], c11[1], c11[2] - 0.5 * G.ROW_DZ + 0.008 + tz])
    via = seat11 + np.array([0.0, so + 0.22, 0.10])
    def Rzf(t):
        ct, st = np.cos(t), np.sin(t)
        return np.array([[ct, -st, 0], [st, ct, 0], [0, 0, 1.0]])
    # ---- backward planning: march hover -> via -> mouth -> grasp, record (tcp, Rt, q).
    # Try BOTH turn directions, keep the better-tracking plan (bottom-center floats 103mm
    # with -pi; the other direction tracks it).
    sv = c.d.qpos.copy()
    best = None                                   # (max_te, eg, YT, traj)
    for YT in (-np.pi, np.pi):
        q_hover = c.solve(arm, hover, Rzf(YT) @ Rg, robust=True)
        q_m = c.solve(arm, mouth, Rg, robust=True)
        q_gr = c.solve(arm, tcp_g, Rg, robust=True)
        c.d.qpos[A["qadr"]] = q_hover; mujoco.mj_forward(c.m, c.d)
        traj = []; mte = 0.0
        # 4-leg backward route: rise hover->OVER-BASE (tool stays turned), un-turn while
        # crossing OB->via (probed 4mm there vs 98-191 turning on the descent), then
        # via->mouth->grasp with a LIGHT seed pull (bottom-center descent transient
        # 98 plain / 52+morph-jerk at 0.4 pull / ~40 at 0.25)
        OB = np.array([1.15, -0.25, 1.25])
        legsB = [(70, hover, OB, "hold", None), (160, OB, via, "turn", None),
                 (130, via, mouth, "none", None), (60, mouth, tcp_g, "none", None)]
        # NOTE: seed pulls toward q_m/q_gr looked good in isolation but ADDED error in
        # the full pipeline (r0c1: float 43->51, grasp-end 1->10mm) - keep plain warm
        for n, p0, p1, mode, qpull in legsB:
            for i in range(n):
                al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / n)
                tcp = p0 + al * (p1 - p0)
                ang = YT if mode == "hold" else (YT * (1 - al) if mode == "turn" else 0.0)
                Rt = Rzf(ang) @ Rg
                cur = c.d.qpos[A["qadr"]].copy()
                sd = cur if qpull is None else (1 - 0.25 * al) * cur + 0.25 * al * qpull
                ik(c.m, c.d, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
                   tcp, seed=sd, iters=70, R_des=Rt)
                mujoco.mj_forward(c.m, c.d)
                mte = max(mte, float(np.linalg.norm(c.d.site_xpos[sid] - tcp)))
                traj.append((tcp.copy(), Rt.copy(), c.d.qpos[A["qadr"]].copy()))
        eg = float(np.linalg.norm(c.d.site_xpos[sid] - tcp_g))
        c.d.qpos[:] = sv; mujoco.mj_forward(c.m, c.d)
        print(f"   backward plan yaw{'+' if YT > 0 else '-'}: march-te={mte*1000:.0f}mm grasp-end={eg*1000:.0f}mm")
        if eg <= 0.020 and (best is None or mte < best[0]):
            best = (mte, eg, YT, traj)
    if best is None:
        raise RuntimeError(f"{name}: backward plan missed the grasp in both directions")
    mte, eg, YT, traj = best
    q_grasp = traj[-1][2]
    i_via, i_mouth = 229, 359
    # REST in the carry's OWN end branch: warm-solve the conveyor-facing ready pose from
    # the hover configuration. An independently-solved REST lands in a foreign branch and
    # the post-place go-home becomes a long cross-branch swing (user: "should be very
    # shorter"). Branch-aligned REST -> the final leg is a short natural hop, and the
    # opening unfold (REST -> hover) shortens for the same reason.
    Rrest = R_from([0, 1, 0])
    REST = None
    for off in ((0, -0.25, 0), (0, -0.25, 0.04), (0.04, -0.25, 0.04),
                (-0.04, -0.28, 0.02), (0, -0.31, 0.06)):
        sc3 = mujoco.MjData(c.m); sc3.qpos[:] = c.d.qpos
        r = ik(c.m, sc3, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
               belt + np.array(off, float), seed=traj[0][2], iters=300, R_des=Rrest)
        q = sc3.qpos[A["qadr"]].copy()
        sv3 = c.d.qpos.copy()
        c.d.qpos[A["qadr"]] = q; mujoco.mj_forward(c.m, c.d)
        ok = r["ok"] and c._links_clear_structures(arm)
        c.d.qpos[:] = sv3; mujoco.mj_forward(c.m, c.d)
        if ok:
            REST = q
            break
    if REST is None:
        raise RuntimeError(f"{name}: no clear branch-aligned rest pose found")                      # leg boundaries in the recording
    def play(seq, ride_rel=None):
        """replay recorded frames; if ride_rel=(rel_pos, rel_R) drive the tube on the
        PLANNED pose of each frame (object master; the replayed arm tracks it)."""
        bqm = np.zeros(4)
        for tcp, Rt, q in seq:
            c.d.qpos[A["qadr"]] = q
            if ride_rel is not None:
                rp, rR = ride_rel
                mujoco.mju_mat2Quat(bqm, (Rt @ rR).reshape(9))
                c.d.qpos[adr:adr + 3] = tcp + Rt @ rp
                c.d.qpos[adr + 3:adr + 7] = bqm
            for j, x in enumerate(A["act"]):
                c.d.ctrl[x] = q[j]
            c.d.qvel[:] = 0
            mujoco.mj_forward(c.m, c.d)
            if c._k % CAP_EVERY == 0:
                c.capture()
            if c._sync is not None:
                c._sync(c)
            c._k += 1
    # ---- animate: REST -> unfold (via recorded poses) -> approach (recorded tail)
    c.d.qpos[A["qadr"]] = REST
    mujoco.mj_forward(c.m, c.d); c._apply_attach(); c.capture()
    # DIRECT approach (user: the corridor-retrace opening read as a pointless forward
    # detour): one natural joint swing REST -> via pose (the 180 tool reorientation
    # happens inside it), then to the mouth pose, then the recorded straight-in. All
    # targets are recorded-trajectory poses -> branch-continuous with the carry. The
    # jaw passes UNDER the rack's bottom-front edge with real clearance (verified
    # >=10mm per frame by the extras check; only the over-padded margin band flagged it).
    c.move_to_q(arm, traj[i_via][2], steps=170, label="unfold")
    c.move_to_q(arm, traj[i_mouth][2], steps=130, label="unfold-2")
    play(traj[i_mouth + 1:])                      # recorded straight-in: mouth -> grasp
    c.detach(tube); c.attach_tcp(tube, sid); c.event(f"grasp {tube}")
    # rigid grip transform measured at attach (for the planned-pose ride)
    tcp0 = c.d.site_xpos[sid].copy(); Rt0 = c.d.site_xmat[sid].reshape(3, 3).copy()
    ob0 = c.d.xpos[c.bid(tube)].copy(); Rb0 = c.d.xmat[c.bid(tube)].reshape(3, 3).copy()
    rel = (Rt0.T @ (ob0 - tcp0), Rt0.T @ Rb0)
    c.detach(tube)
    play(traj[::-1], ride_rel=rel)                # the carry: grasp -> mouth -> via -> hover
    # ---- lower onto the belt (easy leg, warm IK), then pin and go home
    n = 60
    for i in range(n):
        al = 0.5 - 0.5 * np.cos(np.pi * (i + 1) / n)
        tcp = hover + al * (tcp_end - hover); Rt = Rzf(YT) @ Rg
        cur = c.d.qpos[A["qadr"]].copy()
        ik(c.m, c.d, A["pfx"], sid, A["dofs"], A["qadr"], A["lo"], A["hi"],
           tcp, seed=cur, iters=70, R_des=Rt)
        bqm = np.zeros(4)
        mujoco.mju_mat2Quat(bqm, (Rt @ rel[1]).reshape(9))
        c.d.qpos[adr:adr + 3] = tcp + Rt @ rel[0]
        c.d.qpos[adr + 3:adr + 7] = bqm
        for j, x in enumerate(A["act"]):
            c.d.ctrl[x] = c.d.qpos[A["qadr"]][j]
        c.d.qvel[:] = 0
        mujoco.mj_forward(c.m, c.d)
        if c._k % CAP_EVERY == 0:
            c.capture()
        if c._sync is not None:
            c._sync(c)
        c._k += 1
    c.pin(tube)
    c.event(f"{tube} placed")
    Rt_now = c.d.site_xmat[sid].reshape(3, 3).copy()
    c.move_to(arm, tcp_end + np.array([0, -0.15, 0.08]), Rt_now, steps=70, label="retract")
    c.move_to_q(arm, REST, steps=160, label="to-home")   # branch-aligned REST: short hop
    c.capture()
    c.event("done")
    final = c.d.xpos[c.bid(tube)].copy()
    print(f"[{name}] tube-on-belt xy err = {np.linalg.norm((final - belt)[:2]) * 1000:.0f} mm")
    _save(c, name, title)


def combo_load(arm, cargo, box, cell, name, title, direct=False):
    c = Cell()
    c.pin_loose()                     # freeze every item at its initial rest pose
    c.step(20)                        # let the arm stabilize at home (items frozen)
    c.frames = []; c.events = []      # record from the steady, settled state
    c.event(title)
    c.load_into_box(arm, cargo, box)
    c.grasp_side(arm, box, direct=direct)        # honest box grasp (arm 2); arm 1 unchanged
    if direct:
        c.place_cosmetic(arm, box, cell)         # honest carry + scripted final insert
    else:
        c.place_in_cell(arm, box, cell)
    c.home(arm)
    c.event("done")
    cf = c.d.xpos[c.bid(cargo)].copy(); bf = c.d.xpos[c.bid(box)].copy()
    print(f"[{name}] cargo-in-box gap = {np.linalg.norm(cf-bf)*1000:.0f} mm (should stay small)")
    _save(c, name, title)


def run_all():
    A1 = lambda r, col: G.shelf_cell(1, r, col)
    A2 = lambda r, col: G.shelf_cell(2, r, col)
    combo_box(1, "box1", A1(2, 1), "a1_box", "Arm 1 (suction) places a Box on shelf 1 (top-center)")
    combo_box(2, "box2", A2(2, 1), "a2_box", "Arm 2 (jaw) places a Box on shelf 2 (top-center)", direct=True)
    combo_sheet(1, "sheet1", A1(1, 0), "a1_sheet", "Arm 1 (suction) stands a Sheet on shelf 1 (mid-left)")
    combo_tube(2, "tube1", A2(1, 1), "a2_tube", "Arm 2 (jaw) places a Tube on shelf 2 (mid-center)")
    combo_load(1, "sheet1", "box1", A1(0, 1), "a1_load",
               "Arm 1 loads a Sheet into a Box, then places the Box on shelf 1 (bottom-center)")
    combo_load(2, "tube1", "box2", A2(0, 1), "a2_load",
               "Arm 2 loads a Tube into a Box, then places the Box on shelf 2 (bottom-center)", direct=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "one":
        combo_box(1, "box1", G.shelf_cell(1, 2, 1), "a1_box",
                  "Arm 1 (suction) places a Box on shelf 1 (top-center)")
    else:
        run_all()

