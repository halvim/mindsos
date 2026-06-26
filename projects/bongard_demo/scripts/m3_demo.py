from __future__ import annotations

from bongard import render
from bongard.control import Solver
from bongard.scene import parse_scene, scene_relations


SCENES = [
    ("two_squares", render.scene_two_squares),
    ("square_triangle", render.scene_square_triangle),
    ("three_mixed", render.scene_three_mixed),
    ("overlapping", render.scene_overlapping),
]


def _fmt_rel(r) -> str:
    arrow = "==" if r.symmetric else "->"
    return f"{r.rel_type}(#{r.subj} {arrow} #{r.obj})"


def main() -> None:
    solver = Solver("bongard-m3-demo")
    for name, make in SCENES:
        image = make()
        scene = parse_scene(solver, image)
        rels = scene_relations(solver, scene)
        print(f"\n=== scene: {name} ===")
        print(f"  figures individuated : {len(scene.figures)}")
        print(f"  shapes solved        : {scene.n_shapes}")
        print(f"  abstained            : {scene.n_abstained}")
        for i, s in enumerate(scene.shapes):
            print(f"    #{i}: {s.polygon_type} (vertices={len(s.vertices)}, "
                  f"conf={s.confidence:.3f})")
        for i, v in enumerate(scene.figures):
            if not v.solved:
                print(f"    component {i}: ABSTAIN ({v.reason}: {v.detail})")
        if rels:
            print(f"  relations            : {', '.join(_fmt_rel(r) for r in rels)}")
        else:
            print("  relations            : (none)")
    print()


if __name__ == "__main__":
    main()
