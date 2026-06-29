"""Baseline grounding for bg_advance over the 400 train tasks (read-only).

For each task: run pipeline steps 1-4 (the only bg-mutating phases) calling
bg_advance after each, then read the resolved test-grid bg. Compare against
_bg_color (pooled most-frequent) to size the divergence/static-bg class.
No ground-truth bg label exists in the data, so this measures resolution rate
and the bg_advance-vs-frequency divergence, not accuracy.
"""
from intelligence_demo.arc1.spike import arc_grids, arc_solver
from intelligence_demo.arc1.solve import pipeline


def run_task(task_id, dataset):
    ctx = {"task_id": task_id}
    for (n, name, scope, fn, functions, produces) in pipeline.STEPS[:4]:
        fn(ctx, dataset)
        arc_solver.bg_advance(ctx, n)
    return ctx


def main():
    dataset = arc_grids.load_dataset()
    ids = list(dataset["train"].keys())
    rows = []
    errors = []
    for i, tid in enumerate(ids):
        try:
            ctx = run_task(tid, dataset)
            bc = ctx["bg_cand"]
            freq = arc_solver._bg_color(ctx["profile"])
            test = bc["test"][0]["input"]
            test_bg, test_cand = test["bg"], test["cand"]
            # all train grids resolved + agree?
            train_bgs = [g[s]["bg"] for g in bc["train"] for s in ("input", "output")]
            train_resolved = all(b is not None for b in train_bgs)
            train_agree = train_resolved and len(set(train_bgs)) == 1
            rows.append({
                "n": i + 1, "id": tid, "freq": freq,
                "test_bg": test_bg, "test_cand": test_cand,
                "train_agree": train_agree, "train_resolved": train_resolved,
                "diverge": test_bg is not None and test_bg != freq,
            })
        except Exception as e:
            errors.append((i + 1, tid, repr(e)[:80]))

    n = len(rows)
    resolved = [r for r in rows if r["test_bg"] is not None]
    abstain = [r for r in rows if r["test_bg"] is None]
    diverge = [r for r in rows if r["diverge"]]
    agree = [r for r in rows if r["train_agree"]]

    print(f"tasks run         : {n}  (errors {len(errors)})")
    print(f"test bg resolved  : {len(resolved)}  ({len(resolved)*100//max(n,1)}%)")
    print(f"test bg abstain   : {len(abstain)}")
    print(f"train all-agree   : {len(agree)}")
    print(f"diverge vs freq   : {len(diverge)}   (bg_advance != most-frequent)")
    print()
    print("DIVERGENCE SET (bg_advance test_bg != _bg_color most-frequent):")
    print(f"{'#':>4} {'id':<10} {'freq':>4} {'bg_adv':>6}  cand")
    for r in diverge:
        print(f"{r['n']:>4} {r['id']:<10} {r['freq']:>4} {r['test_bg']:>6}  {r['test_cand']}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(" ", e)


if __name__ == "__main__":
    main()
