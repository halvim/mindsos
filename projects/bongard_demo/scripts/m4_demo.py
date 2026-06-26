from __future__ import annotations

import random

from bongard.control import Solver
from bongard.problem import (ALL_SAME_PROBLEM, COUNT_EQ_PROBLEM, Problem,
                             _render, _not_all_same, TYPE_NS)
from bongard.concepts import ConceptCandidate, TEMPLATE_COUNT_EQ, TEMPLATE_ALL_SAME
from bongard.search import (search_and_verify, _parse, _library, _separates,
                            _evaluate, _arity)

N_TRAIN, N_HOLDOUT = 4, 12


def _gen_ambiguous(label, rng):
    if label:
        return _render([rng.choice(TYPE_NS)] * 3)
    return _render(_not_all_same([rng.choice(TYPE_NS) for _ in range(2)], rng))


def _gen_constant(label, rng):
    return _render([3, 4])


PROBLEMS = [
    ALL_SAME_PROBLEM,
    COUNT_EQ_PROBLEM,
    Problem("AMBIGUOUS: 3-same vs 2-mixed", ConceptCandidate(TEMPLATE_COUNT_EQ, (3,)), _gen_ambiguous),
    Problem("NO-CONSISTENT: every scene identical", ConceptCandidate(TEMPLATE_ALL_SAME), _gen_constant),
]


def trace(solver, problem):
    train_pos = [_parse(solver, im) for im in problem.batch(N_TRAIN, 0)[0]]
    train_neg = [_parse(solver, im) for im in problem.batch(N_TRAIN, 0)[1]]
    hp, hn = problem.batch(N_HOLDOUT, 1000)
    hold = [_parse(solver, im) for im in hp] + [_parse(solver, im) for im in hn]
    labels = tuple([True] * len(hp) + [False] * len(hn))

    lib = sorted(_library(train_pos + train_neg), key=_arity)
    consistent = [c for c in lib if _separates(solver, c, train_pos, train_neg)]
    survivors = [c for c in consistent
                 if tuple(_evaluate(solver, c, p) for p in hold) == labels]
    return lib, consistent, survivors


def main():
    solver = Solver("bongard-m4-demo")
    for problem in PROBLEMS:
        r = search_and_verify(solver, problem, n_train=N_TRAIN, n_holdout=N_HOLDOUT, seed=0)
        lib, consistent, survivors = trace(solver, problem)
        print(f"\n=== Problem: \"{problem.name}\"  (truth: {problem.truth.describe()}) ===")
        print(f"  library ({len(lib)})        : {', '.join(c.describe() for c in lib)}")
        print(f"  train-consistent ({len(consistent)})  : {', '.join(c.describe() for c in consistent) or '(none)'}")
        print(f"  held-out survivors ({len(survivors)}): {', '.join(c.describe() for c in survivors) or '(none)'}")
        if r.concluded:
            print(f"  => CONCLUDE: {r.concept.describe()}")
        else:
            print(f"  => ABSTAIN ({r.reason}): {r.detail}")
    print()


if __name__ == "__main__":
    main()
