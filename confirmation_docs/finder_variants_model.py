"""CORE-C3R1 — standalone model of the finder, recursive and fixpoint forms.

Two jobs.

**Job 1 (original, 2026-07-31).** Mirror ``mindsos_capacity/pipeline.py``
phase 1 (``ds_reachable`` / ``cap_satisfiable`` with a cycle stack) and
phase 2 (``fire`` + the ``fired`` memo) exactly, and swap only the
producer-admission rule, to size defects D-B and D-E:

  old       cap_satisfiable(p, frozenset())          -- pre-4fd8baa
  new       p in fired or cap_satisfiable(p, stack)  -- closes D-B only
  inflight  new, plus an in-flight guard             -- SHIPPED at 4fd8baa

**Job 2 (added, CORE-C3R1 remainder).** Model the *replacement* —
``CORE_CR_FINDER_AS_CAPACITIES.md``'s bottom-up fixpoint — so that the
rewrite is measured against the shipped finder instead of asserted equal
to it. The CR's §2 admissibility rule ("a producer is admissible only if
its satisfiability stratum is strictly below the DataState's") is modelled
as written, alongside two candidate repairs, because as written it is
**unsound** — see the probes below.

  fp_ds       strata per DataState; admit p iff cap_s[p] < ds_s[d]   (§2 as written)
  fp_cons     admit p to feed input d of consumer c iff cap_s[p] < cap_s[c]
  fp_dep      admit p iff p does not transitively depend on an output of c
              (an exact acyclicity test; strata answer reachability only)

Every variant returns the same shape — ``(steps, fold_fanin)`` — so a
sweep can distinguish a *shorter DAG* (benign) from a *narrowed fold*
(a silent semantic loss of exactly the D-C/D-E kind the rewrite claims
to eliminate).

Run: python3 finder_variants_model.py
"""
import random

ALL, ANY, FOLD = "all_required", "any_of", "fold"


class Blew(Exception):
    """max_depth exceeded (recursive variants only)."""


class NotFound(Exception):
    """No route, or no admissible producer."""


class SelfFeed(Exception):
    """Construction re-entered a capacity already under construction.

    Only a *fixpoint* variant can raise this, and only if its
    admissibility rule failed to make self-feeding impossible. Counting
    it is how "impossible by construction" is tested rather than assumed.
    """


# ── recursive finder (mirrors pipeline.py) ───────────────────────────

def find_recursive(caps, target, starts, variant="inflight", max_depth=8):
    starts_f = frozenset(starts)
    producers_of = lambda d: sorted(i for i, (_, o, _) in caps.items() if d in o)

    def ds_reachable(d, stack):
        if d in starts_f:
            return True
        if d in stack:
            return False
        return any(cap_satisfiable(c, stack | {d}) for c in producers_of(d))

    def cap_satisfiable(c, stack):
        ins = caps[c][0]
        if not ins:
            return True
        if caps[c][2] == ANY:
            return any(ds_reachable(d, stack) for d in ins)
        return all(ds_reachable(d, stack) for d in ins)

    if target in starts_f:
        return [], {}
    if not any(cap_satisfiable(c, frozenset()) for c in producers_of(target)):
        raise NotFound("no satisfiable producer")

    steps, fired, inflight, fanin = [], {}, set(), {}

    def eligible(c, stack):
        if variant == "old":
            return cap_satisfiable(c, frozenset())
        if variant == "inflight" and c in inflight:
            return False
        return c in fired or cap_satisfiable(c, stack)

    def fire(c, depth, stack):
        if c in fired:
            return fired[c]
        if depth > max_depth:
            raise Blew("depth")
        inflight.add(c)
        ins, _outs, g = caps[c]
        for d in ins:
            if d in starts_f:
                continue
            nxt = stack | {d}
            sat = [p for p in producers_of(d) if eligible(p, nxt)]
            if g == FOLD:
                fanin.setdefault(c, {})[d] = frozenset(sat)
                for p in sat:
                    fire(p, depth + 1, nxt)
            elif sat:
                fire(sat[0], depth + 1, nxt)
            elif g == ALL:
                inflight.discard(c)
                raise NotFound(f"required input {d} of {c} unproducible")
        i = len(steps)
        steps.append(c)
        fired[c] = i
        inflight.discard(c)
        return i

    tp = sorted(p for p in producers_of(target) if cap_satisfiable(p, frozenset()))
    fire(tp[0], 0, frozenset())
    return steps, fanin


# ── fixpoint finder (the CR's design) ────────────────────────────────

def strata(caps, starts, fold_over_max=False):
    """Monotone bottom-up reachability. Returns (ds_s, cap_s, ds_max).

    ``cap_s[c]`` is the round c became satisfiable; ``ds_s[d]`` the round
    d became reachable via its EARLIEST producer; ``ds_max[d]`` via its
    LATEST. ``fold_over_max`` stratifies a fold consumer over ``ds_max``
    of its inputs, since a fold consumes *every* producer of an input,
    not the first one.
    """
    ds_s = {d: 0 for d in starts}
    cap_s = {}
    while True:
        changed = False
        for c, (ins, outs, g) in caps.items():
            if c in cap_s:
                continue
            if not ins:
                s = 1
            elif g == ANY:
                av = [ds_s[d] for d in ins if d in ds_s]
                if not av:
                    continue
                s = 1 + min(av)
            else:
                if any(d not in ds_s for d in ins):
                    continue
                s = 1 + max(ds_s[d] for d in ins)
            cap_s[c] = s
            changed = True
            for o in outs:
                if o not in ds_s or ds_s[o] > s + 1:
                    ds_s[o] = s + 1
        if not changed:
            break

    ds_max = dict(ds_s)
    for c, s in cap_s.items():
        for o in caps[c][1]:
            ds_max[o] = max(ds_max.get(o, 0), s + 1)

    if fold_over_max:
        for c, (ins, _o, g) in caps.items():
            if g == FOLD and c in cap_s and all(d in ds_max for d in ins):
                cap_s[c] = 1 + max(ds_max[d] for d in ins)

    return ds_s, cap_s, ds_max


def dep_closure(caps, cap_s, starts):
    """Least fixpoint of "which DataStates does c transitively consume?".

    Over the satisfiable subgraph only. Monotone and bounded by the
    DataState set, so it converges. This is the EXACT relation the
    stratum comparison approximates — and the probes show the
    approximation is not conservative in the direction that matters.
    """
    producers_of = lambda d: [i for i, (_, o, _) in caps.items() if d in o and i in cap_s]
    dep = {c: set(caps[c][0]) - set(starts) for c in cap_s}
    while True:
        changed = False
        for c in cap_s:
            grew = set(dep[c])
            for d in dep[c]:
                for q in producers_of(d):
                    grew |= dep[q]
            grew -= set(starts)
            if grew != dep[c]:
                dep[c] = grew
                changed = True
        if not changed:
            return dep


def find_fixpoint(caps, target, starts, variant="fp_ds"):
    starts_f = frozenset(starts)
    ds_s, cap_s, ds_max = strata(caps, starts_f)
    if target in starts_f:
        return [], {}
    if target not in ds_s:
        raise NotFound("no satisfiable producer")

    producers_of = lambda d: sorted(i for i, (_, o, _) in caps.items() if d in o and i in cap_s)
    dep = dep_closure(caps, cap_s, starts_f) if variant == "fp_dep" else {}

    def admissible(d, consumer):
        """Producers of ``d`` this variant will wire into ``consumer``."""
        ps = producers_of(d)
        if variant == "fp_dep":
            if consumer is None:
                return ps
            outs = set(caps[consumer][1])
            return [p for p in ps if not (outs & dep[p]) and p != consumer]
        if variant == "fp_ds":
            bar = ds_s[d]
        else:
            bar = cap_s[consumer] if consumer is not None else ds_s[d]
        return [p for p in ps if cap_s[p] < bar]

    steps, idx, building, fanin = [], {}, set(), {}

    def emit(c):
        if c in idx:
            return idx[c]
        if c in building:
            raise SelfFeed(f"{c} re-entered under construction")
        building.add(c)
        ins, _outs, g = caps[c]
        for d in ins:
            if d in starts_f:
                continue
            sat = admissible(d, c)
            if g == FOLD:
                fanin.setdefault(c, {})[d] = frozenset(sat)
                for p in sat:
                    emit(p)
                if not sat:
                    building.discard(c)
                    raise NotFound(f"required input {d} of {c} unproducible")
            elif sat:
                emit(sat[0])
            elif g == ALL:
                building.discard(c)
                raise NotFound(f"required input {d} of {c} unproducible")
        building.discard(c)
        i = len(steps)
        steps.append(c)
        idx[c] = i
        return i

    tp = admissible(target, None)
    if not tp:
        raise NotFound("no satisfiable producer")
    emit(tp[0])
    return steps, fanin


VARIANTS = {
    "old": lambda c, t, s: find_recursive(c, t, s, "old"),
    "new": lambda c, t, s: find_recursive(c, t, s, "new"),
    "inflight": lambda c, t, s: find_recursive(c, t, s, "inflight"),
    "fp_ds": lambda c, t, s: find_fixpoint(c, t, s, "fp_ds"),
    "fp_cons": lambda c, t, s: find_fixpoint(c, t, s, "fp_cons"),
    "fp_dep": lambda c, t, s: find_fixpoint(c, t, s, "fp_dep"),
}


def run(v, caps, t, st):
    try:
        steps, fanin = VARIANTS[v](caps, t, st)
        return ("OK", tuple(sorted(steps)), len(steps) != len(set(steps)), fanin)
    except Exception as ex:
        return (type(ex).__name__, str(ex), False, {})


def show(r):
    return f"OK steps={list(r[1])}" if r[0] == "OK" else f"{r[0]}: {r[1]}"


def _gen(rng):
    dss = [f"d{i}" for i in range(rng.randint(3, 6))]
    caps = {}
    for i in range(rng.randint(2, 6)):
        k = rng.randint(0, 2)
        caps[f"c{i}"] = (
            tuple(rng.sample(dss, min(k, len(dss)))),
            (rng.choice(dss),),
            rng.choice([ALL, ANY, FOLD]),
        )
    return caps, rng.choice(dss), set(rng.sample(dss, rng.randint(0, 2)))


def _narrowed(base_fanin, var_fanin):
    """True if any fold consumer fans in FEWER producers than the baseline."""
    for c, byds in base_fanin.items():
        for d, ps in byds.items():
            got = var_fanin.get(c, {}).get(d, frozenset())
            if got < ps:
                return True
    return False


if __name__ == "__main__":
    print("=" * 68)
    print("JOB 1 — D-B / D-E, the shipped patch (unchanged from 2026-07-31)")
    print("=" * 68)
    G = {"c0": (("d2", "d5"), ("d5",), ANY), "c1": (("d5",), ("d2",), FOLD),
         "c2": ((), ("d2",), ANY), "c3": ((), ("d2",), FOLD), "c4": ((), ("d5",), ANY)}
    for v in ("old", "new", "inflight"):
        print(f"  {v:9s}: {show(run(v, G, 'd5', {'d3', 'd4'}))}")

    S1 = {"make_out": (("x",), ("out",), ALL), "a_loop": (("out",), ("x",), ALL),
          "b_direct": (("seed",), ("x",), ALL)}
    S2 = {"mk_root": ((), ("root",), ALL), "to_a": (("root",), ("a",), ALL),
          "to_b": (("root",), ("b",), ALL), "combine": (("a", "b"), ("out",), ALL)}
    S3 = {"gen_0": ((), ("d",), ALL), "gen_1": ((), ("d",), ALL),
          "gen_2": ((), ("d",), ALL), "reduce": (("d",), ("out",), FOLD)}
    print("\n  conformance (AND / diamond / fold fan-in):")
    for nm, (c, t, s) in {"S1": (S1, "out", {"seed"}), "S2": (S2, "out", set()),
                          "S3": (S3, "out", set())}.items():
        row = "  ".join(f"{v}={show(run(v, c, t, s))}" for v in ("inflight", "fp_ds", "fp_cons", "fp_dep"))
        print(f"    {nm}: {row}")

    rng = random.Random(23)
    blew = {v: 0 for v in ("old", "new", "inflight")}
    dup = dict(blew)
    for _ in range(20000):
        caps, t, st = _gen(rng)
        for v in ("new", "inflight"):
            r = run(v, caps, t, st)
            if r[0] == "Blew":
                blew[v] += 1
            if r[0] == "OK" and r[2]:
                dup[v] += 1
    print(f"\n  sweep 20000: new blew={blew['new']} dup={dup['new']} | "
          f"inflight blew={blew['inflight']} dup={dup['inflight']}")
    print("  NOTE: duplicate-step count is 25, not the 20 recorded in the CR §1,")
    print("        ADR-0071 §am-3 and the ConjunctionFinder docstring. Direction")
    print("        of the finding is unchanged (0 with the in-flight guard).")

    print()
    print("=" * 68)
    print("JOB 2 — the fixpoint replacement. Constructed probes.")
    print("=" * 68)

    print("\nPROBE A — any_of self-feed. c consumes d0 and also produces it.")
    PA = {"c": (("d1", "d0"), ("d0",), ANY), "mk": ((), ("d1",), ALL)}
    for v in ("inflight", "fp_ds", "fp_cons", "fp_dep"):
        print(f"  {v:9s}: {show(run(v, PA, 'd0', set()))}")
    print("  READ: fp_ds raises SelfFeed. any_of's stratum is 1+MIN over inputs,")
    print("        so a capacity can rank strictly below a DataState it consumes.")
    print("        §2's rule does NOT make self-feeding impossible by construction.")

    print("\nPROBE B — fold fan-in with a second producer at a higher stratum.")
    PB = {"g0": ((), ("d",), ALL), "mk_s": ((), ("s",), ALL),
          "g1": (("s",), ("d",), ALL), "red": (("d",), ("out",), FOLD)}
    for v in ("inflight", "fp_ds", "fp_cons", "fp_dep"):
        r = run(v, PB, "out", set())
        print(f"  {v:9s}: {show(r)}   fold fan-in={sorted(r[3].get('red', {}).get('d', ()))}")
    print("  READ: the shipped finder fans in BOTH producers. fp_ds and fp_cons")
    print("        drop g1 and report success — a silently narrower fold.")
    print("        No stratum-only bar preserves it: g1 is genuinely later than d,")
    print("        yet a fold must still consume it. Only the exact dependency")
    print("        test (fp_dep) keeps the fold whole.")

    print("\nPROBE C — the D-B/D-E graph the stopgap fixed.")
    for v in ("inflight", "fp_ds", "fp_cons", "fp_dep"):
        print(f"  {v:9s}: {show(run(v, G, 'd5', {'d3', 'd4'}))}")

    print()
    print("=" * 68)
    print("JOB 2 — sweep: each fixpoint variant vs the SHIPPED finder, 20000 graphs")
    print("=" * 68)
    hdr = f"  {'variant':9s} {'same':>6s} {'shorter':>8s} {'narrowed':>9s} {'lost':>6s} {'gained':>7s} {'selffeed':>9s} {'other':>6s}"
    print(hdr)
    for v in ("fp_ds", "fp_cons", "fp_dep"):
        rng = random.Random(23)
        same = short = narrow = lost = gained = selffeed = other = 0
        for _ in range(20000):
            caps, t, st = _gen(rng)
            b = run("inflight", caps, t, st)
            x = run(v, caps, t, st)
            if x[0] == "SelfFeed":
                selffeed += 1
                continue
            if b[0] != "OK" and x[0] != "OK":
                same += 1
            elif b[0] == "OK" and x[0] != "OK":
                lost += 1
            elif b[0] != "OK" and x[0] == "OK":
                gained += 1
            elif b[1] == x[1] and not _narrowed(b[3], x[3]):
                same += 1
            elif _narrowed(b[3], x[3]):
                narrow += 1
            elif set(x[1]) < set(b[1]):
                short += 1
            else:
                other += 1
        print(f"  {v:9s} {same:6d} {short:8d} {narrow:9d} {lost:6d} {gained:7d} {selffeed:9d} {other:6d}")
    print("\n  same     — identical result (incl. both don't-know)")
    print("  shorter  — a strict subset of the shipped DAG; benign, expected")
    print("  narrowed — a fold fans in FEWER producers; SILENT semantic loss")
    print("  lost     — shipped finds a route, the variant does not; a REGRESSION")
    print("  gained   — the variant finds a route the shipped finder cannot")
    print("  selffeed — construction re-entered a capacity; the rule FAILED")
