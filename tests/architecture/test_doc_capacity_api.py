"""The L3 capacity API was replaced at CORE-C3R1; a live doc teaching the old
one hands the reader a snippet that raises.

⚠ **WRITTEN BECAUSE EVERY RUNNABLE SNIPPET ON THE L3 PAGES FAILED.** Measured
2026-09-14 against `711dc16`: `docs/usage/capacity/retrieval.md` imports
`PipelineNotFoundError` (retired), publishes a `class PipelineStep` dataclass
(retired) with a `via_datastate` field (retired) and a singular
`start_datastate` (now plural), and binds `find_pipeline`'s result to a name it
then subscripts as a `Pipeline`; `docs/usage/capacity/building.md` and both
cookbooks pass `task_id=` to `invoke` / `run_lifecycle`. Nothing asserted that
the pages a reader copies from agree with the shipped surface.

⚠ **EVERY CLAIM HERE IS DERIVED FROM `mindsos_capacity`, NEVER TYPED.** The
retirements are read off the live module (`hasattr`, `dataclasses.fields`,
`inspect.signature`) and off a token census of the packages, so a name that
comes back stops this guard claiming it is gone.
`test_the_retired_l3_names_are_really_gone_from_code` is that premise made
explicit — if it fails, the three doc tests below mean nothing.

⚠ **SCOPE — `docs/` ONLY.** The test image copies `docs/` but does **not** copy
`CLAUDE.md`, `README.md` or `RULES.md` (see the Dockerfile test stage). A guard
that scanned them would find no file, no claims, and go green in the container
for exactly the wrong reason. `docs/decisions/adr/` and `docs/changelog/`
record what was true at a date and `docs/_workbench/` is scratch; a guard that
reddens on a historical record is one that gets deleted.

⚠⚠ **`PipelineStep` IS NOT DEAD — IT IS DEAD AT L3 ONLY.** It is a live **L2
NodeType**: `mindsos_knowledge/schemas/promoted_pipelines.py:28`
`NODE_PIPELINE_STEP = "PipelineStep"`, used for the `HAS_STEP` edge and minted
by `identifiers.pipeline_step_iri`. So `docs/concepts/role-graphs.md:15` and
`docs/usage/knowledge/promoted-pipelines.md:15,20` are **correct** and must not
be swept. That is why the patterns below match only the L3 *dataclass*
positions (`class PipelineStep`, `Tuple[PipelineStep`) and never a bare
mention. A sweep driven by the audit's blanket "PipelineStep is now DAGStep"
would have introduced a new error into a page that is right.

⚠ **`start_datastate` is LIVE as a `find_pipeline` keyword** and retired as a
`Pipeline` *field* (it is `start_datastates`, plural). The patterns therefore
match the quoted JSON key and the annotated dataclass field only — never the
keyword argument, which is correct everywhere it appears.

⚠ **THE PATTERN LIST IS A FLOOR, NOT A CEILING.** Deliberately NARROW, like
`test_doc_role_count.py`: a stale L3 snippet written some other way is MISSED
here rather than reported wrong. `retrieval.md`'s bare prose mention of
`PipelineStep` is one such miss — it was corrected by hand, not by this guard.
Widen the list when a new phrasing is found in the wild.
"""

from __future__ import annotations

import dataclasses
import inspect
import io
import os
import re

import mindsos_capacity as mc
from mindsos_capacity.capacity_layer import CapacityLayer

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DOCS = os.path.join(_ROOT, "docs")
_SKIP_DIRS = ("decisions", "changelog", "_workbench")

# The retired L3 exception. Derived: see the premise test below.
_RETIRED_EXCEPTION = "PipelineNotFoundError"

# Phrasings that treat a FindVerdict as the retired linear Pipeline, or that
# publish the retired step/field shapes. FLOOR, not ceiling.
_VERDICT_AS_PIPELINE = (
    re.compile(r"\bpipeline\s*=\s*find_pipeline\s*\("),
    re.compile(r"\bclass\s+PipelineStep\b"),
    re.compile(r"\[\s*PipelineStep\b"),
    re.compile(r"\bvia_datastate\b"),
    re.compile(r'"start_datastate"'),
    re.compile(r"\bstart_datastate\s*:\s*str\b"),
)

_DEAD_KWARG = re.compile(r"\btask_id\b")


def _live_docs():
    for dirpath, dirnames, filenames in os.walk(_DOCS):
        rel = os.path.relpath(dirpath, _DOCS)
        top = rel.split(os.sep)[0]
        if top in _SKIP_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and d != "__pycache__"]
        for name in filenames:
            if name.endswith(".md") and not name.startswith(".fuse_hidden"):
                yield os.path.join(dirpath, name)


def _package_dirs():
    return [
        os.path.join(_ROOT, name)
        for name in sorted(os.listdir(_ROOT))
        if name.startswith("mindsos_") and os.path.isdir(os.path.join(_ROOT, name))
    ]


def _offenders(patterns):
    hits = set()
    for path in _live_docs():
        text = io.open(path, encoding="utf-8").read()
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in patterns:
                if pattern.search(line):
                    hits.add("%s:%d  %s" % (os.path.relpath(path, _ROOT), lineno, line.strip()))
                    break
    return hits


def test_the_docs_tree_is_present_so_this_guard_can_fail():
    """Abort rather than pass vacuously if docs/ was not copied."""
    assert os.path.isdir(_DOCS), "no docs tree at %s" % _DOCS
    assert any(_live_docs()), "docs tree present but no live pages found"


def test_the_retired_l3_names_are_really_gone_from_code():
    """The premise of the three doc tests, measured rather than assumed."""
    assert not hasattr(mc, _RETIRED_EXCEPTION), (
        "%s is exported again — the doc guard below is asserting a retirement "
        "that no longer holds" % _RETIRED_EXCEPTION
    )
    assert not hasattr(mc, "PipelineStep"), "PipelineStep is an L3 export again"
    assert hasattr(mc, "FindVerdict") and hasattr(mc, "DAGStep"), (
        "the replacement types are missing; this guard has nothing to point at"
    )

    verdict = mc.FindVerdict
    assert not hasattr(verdict, "steps"), "FindVerdict grew .steps"
    assert not hasattr(verdict, "__len__"), "FindVerdict grew __len__"

    returns = inspect.signature(mc.find_pipeline).return_annotation
    assert returns in (verdict, "FindVerdict"), (
        "find_pipeline no longer returns a FindVerdict: %r" % (returns,)
    )

    step_fields = {f.name for f in dataclasses.fields(mc.DAGStep)}
    assert "via_datastate" not in step_fields, "via_datastate is a live step field again"

    pipeline_fields = {f.name for f in dataclasses.fields(mc.Pipeline)}
    assert "start_datastate" not in pipeline_fields, "Pipeline.start_datastate is live again"
    assert "start_datastates" in pipeline_fields, "Pipeline lost start_datastates"

    find_params = inspect.signature(mc.find_pipeline).parameters
    assert "start_datastate" in find_params, (
        "start_datastate is no longer a find_pipeline keyword — the patterns "
        "here deliberately spare the keyword form and would now be wrong"
    )

    invoke_params = inspect.signature(CapacityLayer.invoke).parameters
    assert "request_id" in invoke_params, "CapacityLayer.invoke lost request_id"
    assert "task_id" not in invoke_params, "task_id is a live invoke keyword again"

    packages = _package_dirs()
    assert packages, "no mindsos_* packages next to the docs tree"
    live_uses = []
    for pkg in packages:
        for dirpath, dirnames, filenames in os.walk(pkg):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                for lineno, line in enumerate(
                    io.open(path, encoding="utf-8").read().splitlines(), 1
                ):
                    if _DEAD_KWARG.search(line):
                        live_uses.append("%s:%d" % (os.path.relpath(path, _ROOT), lineno))
    assert not live_uses, (
        "task_id is back in the packages, so the doc test below is asserting a "
        "rename that did not hold:\n  " + "\n  ".join(live_uses[:20])
    )


def test_no_live_doc_names_the_retired_pipeline_exception():
    offenders = _offenders((re.compile(r"\b%s\b" % _RETIRED_EXCEPTION),))
    assert not offenders, (
        "these pages name an exception retired at CORE-C3R1 (no-route is a "
        "FindVerdict reason now, not a raise):\n  " + "\n  ".join(sorted(offenders))
    )


def test_no_live_doc_binds_a_find_verdict_as_a_pipeline():
    offenders = _offenders(_VERDICT_AS_PIPELINE)
    assert not offenders, (
        "these pages use the retired linear pipeline shape; find_pipeline "
        "returns a FindVerdict and the chain is verdict.pipeline:\n  "
        + "\n  ".join(sorted(offenders))
    )


def test_no_live_doc_uses_the_dead_task_id_keyword():
    offenders = _offenders((_DEAD_KWARG,))
    assert not offenders, (
        "these pages pass or document task_id; the live keyword is "
        "request_id:\n  " + "\n  ".join(sorted(offenders))
    )
