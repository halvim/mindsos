"""Single source of truth for the Open-Order cell geometry.

Both the scene builder (build_cell.py) and the reach validator (reach_validate.py)
import from here, so a geometry re-tune (driven by the P2 reach validation) changes
the scene and the validation targets together. Numbers are in metres, frame is
z-up, origin on the floor midway between the two arms.

Frame convention:
  +x : toward Arm 2 (right)        -x : toward Arm 1 (left)
  +y : toward the belt (front)     -y : toward the shelves (back, "set back")
  +z : up

The arms sit on pedestals at BASE_Z, facing the belt (+y). Each arm picks cargo
from its own belt segment (front) and places into its own vertical 3x3 shelf
(back). The belt is one continuous surface; cooperation is forced by an
unreachable middle (neither arm reaches |x| < ~GAP_HALF on the belt) plus a
conveyor that only moves on command.
"""
from __future__ import annotations
import numpy as np

# ---- arms -------------------------------------------------------------------
# Each arm is mounted facing its shelf (-y / "south"). The Panda's home pose
# faces +x_local; a -90deg base yaw maps that to world -y, so the 3x3 rack sits
# in the arm's strong front hemisphere (fixes the center-column dead-cone), while
# the belt sits in the rear hemisphere and is served by off-axis reach (feeder /
# staging points clear the joint-1 dead cone).
FLOOR_Z = 0.40                     # floor plane height; = BASE_Z so the arms sit ON the floor
                                   # (raising the floor instead of lowering the arm keeps every
                                   # other height + all kinematics exactly as they are)
BASE_Z = 0.40                      # link0 on a solid plinth at a natural working height
                                   # (pure floor-mount over-stretches the arm to the raised
                                   # belt -> uncontrollable grasp; a plinth looks clean + keeps
                                   # the reach honest, which is why real Pandas are pedestal-mounted)
BASE_Y = -0.45                     # arms; shelves in front (-y), belt behind (+y)
ARM1_X = -1.20                     # Arm 1 (suction) base x  (wide enough to force the gap)
ARM2_X = +1.20                     # Arm 2 (Robotiq jaw) base x
ARM1_BASE = np.array([ARM1_X, BASE_Y, BASE_Z])
ARM2_BASE = np.array([ARM2_X, BASE_Y, BASE_Z])
ARM_YAW_DEG = -90.0                # base yaw so home-facing (+x_local) -> world -y (toward shelf)
PEDESTAL_R = 0.09

def base_quat():
    """wxyz quaternion for a rotation of ARM_YAW_DEG about z (both arms)."""
    h = np.deg2rad(ARM_YAW_DEG) / 2.0
    return [np.cos(h), 0.0, 0.0, np.sin(h)]

# ---- end effectors (offsets past the panda attachment frame) ----------------
SUCTION_LEN = 0.06                 # TCP (a1_tcp) offset from the flange — drives IK; unchanged
SUCTION_TIP_LEN = 0.105            # VISUAL cup length: longer than the TCP so the cup bridges
                                   # the grasp servo-error gap and visibly touches the box,
                                   # WITHOUT moving the TCP (kinematics/placement unchanged)
SUCTION_CUP_R = 0.025
ROBOTIQ_PINCH = 0.145             # 2f85 pinch site from its mount (long jaw)
SHORT_JAW_LEN = 0.075             # custom short 2-finger jaw: TCP offset from the flange.
                                  # Experiment (arm 2 reach margin): the long 0.145 jaw eats
                                  # wrist torque + standoff at the deep cubbies. Shorter +
                                  # lighter cuts droop; cost is the flange must extend a bit
                                  # further to seat the TCP. Net effect validated by probe.

# ---- belt -------------------------------------------------------------------
# Belt is BEHIND the arms (rear hemisphere) AND raised to ~mid-arm height. The
# height is what makes a rear side-grasp controllable (at base level the arm
# sagged ~100 mm; at mid-height it holds to ~8 mm). Keeping the belt behind frees
# the front entirely for the shelves, so all 9 cells incl. the bottom row are
# reachable. Tool -y grips the box's far (+y) face -> same axis as the shelf
# insert -> no reorientation, box stays upright.
BELT_Y = 0.10                      # belt centre, moved further back (+y) from the arms so
                                   # the arm's mid links clear the solid conveyor body
BELT_Z = 0.90                      # belt surface raised to the arms' comfortable working
                                   # height (~shoulder level). At 0.62 the shelf-face grasp
                                   # drove the joints to their limits (cramped pose); at 0.90
                                   # the IK pose sits mid-range (joint margin ~3x better).
BELT_HALF_W = 0.10                 # belt half-width in y
BELT_X0, BELT_X1 = -2.11, 2.11     # continuous span, SYMMETRIC: each end extended so its
                                   # feeder/collector housing sits 0.73m from its arm (the +x
                                   # end was 1.60, putting the collector only 0.22m from arm 2)
GAP_HALF = 0.28                    # |x| < GAP_HALF on the belt = the unreachable middle
FEEDER_X = -1.40                   # items enter upstream (Arm 1 side), off the dead-cone axis
ITEM_Z = BELT_Z + 0.05            # cargo rest height (approx; settles in sim)

# ---- shelves (vertical 3x3 rack per arm, set back, facing +y) ---------------
# Per-arm rack set-back. The two arms carry different end effectors, so a single
# shelf depth can't satisfy both: the long Robotiq (0.145 m past the flange) folds
# Arm 2 into a joint limit at the short-EE depth, so its rack is set back further.
SHELF_Y_ARM = {1: -0.80, 2: -0.88}   # cubby MOUTH plane per arm; just behind the belt
SHELF_DEPTH = 0.12                 # rack depth in -y
COL_DX = 0.18                      # column spacing in x
ROW_DZ = 0.16                      # row spacing in z
ROW_Z0 = 0.98                      # bottom row centre z. Raised so the bottom shelf FLOOR
                                   # (ROW_Z0 - ROW_DZ/2 = 0.90) lines up with the conveyor
                                   # surface (BELT_Z = 0.90) -> a box transfers belt->bottom
                                   # cubby at one level. Rows then at 0.98 / 1.14 / 1.30.
# columns are centred on each arm's base x

def shelf_cell(arm: int, row: int, col: int) -> np.ndarray:
    """World-space centre of a shelf cubby INTERIOR (the object-rest point).
    SHELF_Y_ARM is the cubby MOUTH (front, +y); the cubby extends back (-y), so
    the interior centre is SHELF_Y - DEPTH/2. arm: 1|2; row 0(bot)..2(top);
    col 0(left)..2(right)."""
    cx = (ARM1_X if arm == 1 else ARM2_X) + (col - 1) * COL_DX
    cz = ROW_Z0 + row * ROW_DZ
    return np.array([cx, SHELF_Y_ARM[arm] - SHELF_DEPTH * 0.5, cz])

def all_cells(arm: int):
    for row in range(3):
        for col in range(3):
            yield (row, col), shelf_cell(arm, row, col)

# ---- approach directions (tool z-axis points along these at the target) -----
APPROACH_BELT = np.array([0.0, 0.0, -1.0])   # pick from above
APPROACH_SHELF = np.array([0.0, -1.0, 0.0])  # place horizontally into the rack

# belt pick sample points per arm (along that arm's reachable segment)
def belt_pick_targets(arm: int):
    """The arm's actual belt WORKING points, not a uniform sweep: an upstream
    pickup cluster and an inner staging cluster (just outside the gap). The
    strip directly behind the base (belt is in the rear hemisphere) is a
    dead-cone dead spot and is intentionally not a working point."""
    if arm == 1:
        xs = [-1.45, -1.40, -1.35, -0.60, -0.55]   # pickup ........ staging
    else:
        xs = [1.45, 1.40, 1.35, 0.60, 0.55]
    return [np.array([x, BELT_Y, BELT_Z + 0.09]) for x in xs]   # cargo-top height

# belt points that MUST be unreachable by either arm (the forced gap)
GAP_TEST_XS = [-0.28, -0.18, -0.08, 0.0, 0.08, 0.18, 0.28]
def gap_targets():
    return [np.array([x, BELT_Y, BELT_Z + 0.09]) for x in GAP_TEST_XS]
