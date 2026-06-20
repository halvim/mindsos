"""Reach validation + the shared damped-least-squares IK solver.

RECONSTRUCTED 2026-06-10 after an accidental deletion (see
confirmation_docs/ROBOT_DEMO_STATE.md). The `ik()` body is restored verbatim from
the session record; `arm_dofs`/`joint_limits`/`collides` are rebuilt against their
call sites in motion.py; POS_TOL/ANG_TOL recovered from reach_report.json evidence
(ok=True at perr 0.01034 / aerr 5.42deg, and the explicit 0.012 gate in
motion.rest_candidates). The original __main__ reach-sweep report generator was not
restored — reach_report.json is kept as the historical artifact.
"""
from __future__ import annotations
import numpy as np, mujoco

HOME = [0, 0, 0, -1.57079, 0, 1.57079, -0.7853]   # panda home keyframe qpos
POS_TOL = 0.012                                    # m
ANG_TOL = np.deg2rad(6.0)                          # rad


def arm_dofs(m, pfx):
    """(dof indices, qpos addresses) of the 7 arm joints with name prefix `pfx`."""
    dofs, qadr = [], []
    for j in range(m.njnt):
        nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) or ""
        if nm.startswith(pfx) and nm[len(pfx):].startswith("joint"):
            dofs.append(int(m.jnt_dofadr[j]))
            qadr.append(int(m.jnt_qposadr[j]))
    return np.array(dofs, int), np.array(qadr, int)


def joint_limits(m, pfx):
    lo, hi = [], []
    for j in range(m.njnt):
        nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) or ""
        if nm.startswith(pfx) and nm[len(pfx):].startswith("joint"):
            lo.append(float(m.jnt_range[j][0]))
            hi.append(float(m.jnt_range[j][1]))
    return np.array(lo), np.array(hi)


def collides(m, d, pfx):
    """(any-contact-involving-this-arm, count). Gripper bodies of arm 2 use the
    'a2g_' prefix and are counted with 'a2_'."""
    pfx2 = "a2g_" if pfx == "a2_" else None
    n = 0
    for c in range(d.ncon):
        for g in (d.contact[c].geom1, d.contact[c].geom2):
            b = m.geom_bodyid[g]
            nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or ""
            if nm.startswith(pfx) or (pfx2 and nm.startswith(pfx2)):
                n += 1
                break
    return n > 0, n


def ik(m, d, pfx, sid, dofs, qadr, lo, hi, target, a_des=None,
       seed=None, iters=300, damp=0.12, R_des=None):
    """Solve position + orientation for one arm.
    - a_des: align only the tool z-axis (5-DOF task; roll free).
    - R_des: 3x3, constrain the FULL tool orientation (6-DOF task).
    Returns dict."""
    if seed is None:
        seed = np.array(HOME, float)
    d.qpos[qadr] = seed
    mujoco.mj_forward(m, d)
    jacp = np.zeros((3, m.nv)); jacr = np.zeros((3, m.nv))
    if a_des is not None:
        a_des = a_des / np.linalg.norm(a_des)
    for _ in range(iters):
        mujoco.mj_jacSite(m, d, jacp, jacr, sid)
        pos = d.site_xpos[sid].copy()
        R = d.site_xmat[sid].reshape(3, 3)
        e_p = target - pos
        if R_des is not None:
            e_r = 0.5 * (np.cross(R[:, 0], R_des[:, 0]) + np.cross(R[:, 1], R_des[:, 1])
                         + np.cross(R[:, 2], R_des[:, 2]))
        else:
            e_r = np.cross(R[:, 2], a_des)
        e = np.concatenate([e_p, e_r])
        J = np.vstack([jacp[:, dofs], jacr[:, dofs]])
        JT = J.T
        dq = JT @ np.linalg.solve(J @ JT + (damp ** 2) * np.eye(6), e)
        q = np.clip(d.qpos[qadr] + dq, lo, hi)
        d.qpos[qadr] = q
        mujoco.mj_forward(m, d)
        if np.linalg.norm(e_p) < POS_TOL and np.linalg.norm(e_r) < np.sin(ANG_TOL):
            break
    pos = d.site_xpos[sid].copy()
    R = d.site_xmat[sid].reshape(3, 3)
    perr = float(np.linalg.norm(target - pos))
    if R_des is not None:
        aerr = float(np.linalg.norm(0.5 * (np.cross(R[:, 0], R_des[:, 0])
                     + np.cross(R[:, 1], R_des[:, 1]) + np.cross(R[:, 2], R_des[:, 2]))))
        aerr = float(np.arcsin(min(aerr, 1.0)))
    else:
        aerr = float(np.arccos(np.clip(np.dot(R[:, 2], a_des), -1, 1)))
    at_lim = bool(np.any(d.qpos[qadr] <= lo + 1e-4) or np.any(d.qpos[qadr] >= hi - 1e-4))
    col, ncon = collides(m, d, pfx)
    ok = perr < POS_TOL and aerr < ANG_TOL and not col
    return {"ok": ok, "perr": perr, "aerr_deg": float(np.rad2deg(aerr)),
            "at_limit": at_lim, "collision": col, "ncon": ncon}
