"""dr_mutations — every new guard, shown RED by a named mutation, then reverted.

**Why this is an instrument and not eleven hand-runs.** RULES §12.2 requires
one mutation per new guard and calls *a mutation that reddens nothing* a
finding. Done by hand that is eleven edit/run/revert cycles, each an
opportunity to leave the tree mutated or to re-run a stale `.pyc` — the two
traps this lane has already recorded. Done here it is one command whose output
is a table, and the revert is a `finally`.

**It is not demo content.** It renders nothing, it registers nothing, and the
room never sees it. It is ship discipline, in the same category as
`dr_dump.py`.

**What it does, precisely.** For each mutation: apply an exact string
replacement to a source file, run every guard file in a FRESH SUBPROCESS
(`PYTHONDONTWRITEBYTECODE=1`, so a same-length revert cannot leave a mutated
`.pyc` behind), record which tests went red, then restore the file byte for
byte. Every source is hashed before and after the whole run and the hashes are
printed — if the tree is not identical at the end, that is the first thing you
see.

**Read the output as a prediction test, not a pass list.** Each row carries the
tests the build lane predicted would redden. A mutation whose actual red set is
EMPTY means the guard cannot fail and is worse than no guard. A mutation whose
actual set differs from the predicted one is a finding about the prediction,
which is usually a finding about the code.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 decision_records_demo/dr_mutations.py
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RENDER = "decision_records_demo/dr_render.py"
SCREEN = "decision_records_demo/dr_screen.py"
SETTLE = "decision_records_demo/dr_settlement.py"

GUARD_FILES = (
    "decision_records_demo/test_dr_render_guards.py",
    "decision_records_demo/test_dr_routing_guards.py",
    "decision_records_demo/test_dr_screen_guards.py",
)

#: (name, file, old, new, predicted-red test names)
MUTATIONS = [
    (
        "deciding_lines returns [] instead of raising on an unfindable pair",
        RENDER,
        "        if answer_node is None or record_node is None:\n",
        "        if answer_node is None or record_node is None:\n            return []\n",
        ["test_a_declared_deciding_fact_with_no_stored_question_raises"],
    ),
    (
        "the producing-capacity cross-check is removed (name match alone)",
        RENDER,
        "        if answer_by is None or answer_by != record_by:",
        "        if False:",
        ["test_a_question_and_an_answer_from_different_capacities_raise"],
    ),
    (
        "a refusing record is accepted as a deciding fact",
        RENDER,
        "        if not isinstance(record, dict) or not record.get(FIELD_ADMITTED):",
        "        if False:",
        ["test_a_verdict_standing_on_a_refusing_record_raises"],
    ),
    (
        "the member block stops emitting the deciding fact",
        RENDER,
        "    lines.extend(member.deciding_lines(entry))\n",
        "",
        [
            "test_only_the_deciding_read_reaches_the_page",
            "test_case_a_one_claim_two_desks",
            "test_case_b_refusal_beside_answers_names_the_item",
            "test_the_deciding_fact_and_the_refusal_do_not_share_a_style",
        ],
    ),
    (
        "the determining marker is printed on the page",
        RENDER,
        '        return [f"   Q. {record.get(FIELD_QUESTION)} — {_fmt(answer_node.value)}."]',
        '        return [f"   Q. {record.get(FIELD_QUESTION)} — {_fmt(answer_node.value)}. [{marker}]"]',
        ["test_the_determining_marker_never_reaches_the_page"],
    ),
    (
        "a verdict with NO determining input is punished instead of rendered",
        RENDER,
        "        if not marker:\n            return []",
        '        if not marker:\n            raise RendererGapError("no determining input")',
        ["test_a_capacity_that_records_no_deciding_fact_is_not_punished"],
    ),
    (
        "the conclusion is picked by iteration order again",
        RENDER,
        "        out = self._unconsumed(self.plain_produced())",
        "        out = self.plain_produced()[:1]",
        [
            "test_the_leaf_road_shows_the_deciding_fact",
            "test_two_unconsumed_values_raise_rather_than_pick_one",
        ],
    ),
    (
        "the completed check asks plain_produced again (a refusal stops counting)",
        RENDER,
        "not terminal.terminal_outcomes():",
        "not terminal.plain_produced():",
        ["test_a_refusing_leaf_is_a_conclusion_not_a_missing_one"],
    ),
    (
        "the leaf verdict line wears the first capacity's phrase again",
        RENDER,
        'f"   {analysis.phrase_for_value(produced[0].value)} → "',
        'f"   {analysis.phrase()} → "',
        ["test_the_leaf_road_shows_the_deciding_fact"],
    ),
    (
        "every Q line classifies as a refusal on the screen",
        SCREEN,
        'return "refusal" if line.startswith("Q. ") else "reason"',
        'return "refusal"',
        ["test_the_deciding_fact_and_the_refusal_do_not_share_a_style"],
    ),
    (
        "dr_settlement spells the determining field differently",
        SETTLE,
        'DETERMINED_BY = "determined_by"',
        'DETERMINED_BY = "determined"',
        [
            "test_the_field_name_is_spelled_the_same_in_all_three_places",
            "test_the_leaf_road_shows_the_deciding_fact",
        ],
    ),
]

_RUNNER = (
    "import importlib.util,sys,traceback\n"
    "spec=importlib.util.spec_from_file_location('m',sys.argv[1])\n"
    "m=importlib.util.module_from_spec(spec)\n"
    "try:\n"
    "    spec.loader.exec_module(m)\n"
    "except Exception:\n"
    "    print('IMPORT-RED'); raise SystemExit(0)\n"
    "for name in sorted(n for n in dir(m) if n.startswith('test_')):\n"
    "    try:\n"
    "        getattr(m,name)()\n"
    "    except Exception:\n"
    "        print('RED '+name)\n"
)


def _hash(path: str) -> str:
    with open(os.path.join(ROOT, path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def _red_set() -> set:
    red = set()
    for guard_file in GUARD_FILES:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=ROOT)
        out = subprocess.run(
            [sys.executable, "-c", _RUNNER, os.path.join(ROOT, guard_file)],
            cwd=ROOT, env=env, capture_output=True, text=True,
        ).stdout
        for line in out.splitlines():
            if line.startswith("RED "):
                red.add(line[4:].strip())
            elif line == "IMPORT-RED":
                red.add("<" + os.path.basename(guard_file) + " did not import>")
    return red


def main() -> int:
    before = {f: _hash(f) for f in (RENDER, SCREEN, SETTLE)}
    print("== baseline: every guard file green with no mutation applied ==")
    baseline = _red_set()
    if baseline:
        print("BASELINE IS NOT GREEN — everything below is meaningless:")
        for name in sorted(baseline):
            print("  RED " + name)
        return 2
    print("baseline green\n")

    findings = 0
    for name, path, old, new, predicted in MUTATIONS:
        full = os.path.join(ROOT, path)
        original = io.open(full, encoding="utf-8").read()
        if old not in original:
            print("== %s ==\n  MUTATION DID NOT APPLY — its anchor is not in %s"
                  % (name, path))
            findings += 1
            continue
        try:
            io.open(full, "w", encoding="utf-8").write(original.replace(old, new, 1))
            actual = _red_set()
        finally:
            io.open(full, "w", encoding="utf-8").write(original)
        print("== %s ==" % name)
        print("  file      : %s" % path)
        print("  predicted : %s" % ", ".join(sorted(predicted)))
        print("  actual    : %s" % (", ".join(sorted(actual)) or "NOTHING"))
        if not actual:
            print("  ⚠ FINDING: this mutation reddens nothing — the guard cannot fail")
            findings += 1
        elif set(predicted) != actual:
            print("  ⚠ PREDICTION MISS: the difference is the finding")
            findings += 1
        else:
            print("  exact")
        print()

    after = {f: _hash(f) for f in (RENDER, SCREEN, SETTLE)}
    print("== tree restored ==")
    for f in sorted(before):
        mark = "OK " if before[f] == after[f] else "⚠ NOT RESTORED "
        print("  %s%s  %s -> %s" % (mark, f, before[f], after[f]))
    if before != after:
        return 3
    print("\n== re-verify: the guards are green again after every revert ==")
    residue = _red_set()
    print("red after revert: %s" % (", ".join(sorted(residue)) or "none"))
    if residue:
        return 3
    print("\nmutations: %d, findings: %d" % (len(MUTATIONS), findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
