"""A ``pytest.raises`` on a builtin exception class must name a message.

``pytest.raises(ValueError)`` passes if *anything* in the block raises a
``ValueError`` — a typo in a fixture, an unrelated argument check, a helper
three frames down. A designated mutation run against such a guard comes back
**green for the wrong reason**, which is the worst failure a mutation run has:
it certifies a claim nobody tested. The tree has **104 of these**.

**The fix is a mechanical inverse, not 104 edits.** The same move that closed
``ALL_AUDIT_EVENTS`` (``test_audit_event_roster_is_complete``): the current
occurrences are a *declared, shrinking* allowlist, and this guard refuses a new
one. Removing one is a line deleted from :data:`DECLARED`; adding one is a
review conversation.

**Why the domain is builtin classes only.** A bespoke exception raised in one
place — ``C.LevelTwoIsBrokered``, ``OriginContractError`` — is already a tight
guard: the class *is* the message. ``ValueError`` is not. The builtin set is
**derived from the ``builtins`` module at test time**, never listed here: a
hand-written set of "generic" names is the exact defect this file exists to
close, one level up.

**What this guard does NOT claim.** That every guard names its failure. A
project exception used in 38 places across a subsystem (``PropertyShapeError``)
is as undiscriminating *within that subsystem* as ``ValueError`` is tree-wide,
and this guard is silent about it. Narrowing that is
``core-guard-bare-raises-first-shrink``, not this file.

**The first census of this domain was itself defective, and that is guarded
here.** It walked the AST but could only name ``Name`` and ``Attribute``
arguments, so it silently dropped three tuple forms and one dynamic one and
reported 548/182 where the tree holds 552/184 — and two of the four it could
not see are ``pytest.raises((AttributeError, Exception))``, the loosest guards
in the tree. :func:`test_the_checker_sees_the_argument_forms_the_first_census_could_not`
pins all four forms. (The census *before* that one was a regex, and matched a
docstring describing its own subject: ask the AST, and ask it about every
argument shape it can be handed.)

RULES.md §9: a guard is born RED. The two fabricated-tree tests below are that
birth certificate — the checker is shown flagging and not flagging on a tree
built for the purpose, so no offending line has to be committed to prove it.
"""

from __future__ import annotations

import ast
import builtins
from collections import Counter
from pathlib import Path

_BUILTIN_EXCEPTIONS = frozenset(
    name
    for name, obj in vars(builtins).items()
    if isinstance(obj, type) and issubclass(obj, BaseException)
)


def _argument_spelling(node: ast.expr) -> tuple[str, str]:
    """``(form, spelling)`` for the first positional argument of ``raises``."""
    if isinstance(node, ast.Name):
        return "NAME", node.id
    if isinstance(node, ast.Attribute):
        return "ATTR", ast.unparse(node)
    if isinstance(node, ast.Tuple):
        return "TUPLE", ast.unparse(node)
    return "DYN", ast.unparse(node)


def _must_be_declared(form: str, node: ast.expr) -> bool:
    """True when the class being asked for does not discriminate on its own.

    ``NAME``  — a builtin exception class.
    ``TUPLE`` — any member is one; a tuple is at least as wide as its widest arm.
    ``DYN``   — not a class reference at all (``type(exc)``). Not necessarily
                weak, but **unclassifiable statically**, and a form a census
                must be unable to skip silently; it is declared for that reason.
    ``ATTR``  — ``sqlite3.IntegrityError``, ``typer.Exit``: a specific class in
                a named module. Out of scope, deliberately.
    """
    if form == "NAME":
        return isinstance(node, ast.Name) and node.id in _BUILTIN_EXCEPTIONS
    if form == "TUPLE":
        return isinstance(node, ast.Tuple) and any(
            isinstance(e, ast.Name) and e.id in _BUILTIN_EXCEPTIONS for e in node.elts
        )
    return form == "DYN"


def census(root: Path, scan_dirs: list[Path]) -> tuple[Counter, int]:
    """``({(repo-relative path, spelling): count}, total pytest.raises calls)``.

    The count is the second axis on purpose: keyed by ``(file, class)`` alone,
    a new bare ``pytest.raises(ValueError)`` added to a file that already
    declares one would be invisible.
    """
    counts: Counter = Counter()
    total = 0
    for scan_dir in scan_dirs:
        for path in sorted(scan_dir.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr == "raises"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "pytest"
                ):
                    continue
                total += 1
                if any(kw.arg == "match" for kw in node.keywords):
                    continue
                if not node.args:
                    continue
                form, spelling = _argument_spelling(node.args[0])
                if _must_be_declared(form, node.args[0]):
                    counts[(path.relative_to(root).as_posix(), spelling)] += 1
    return counts, total


def _repo_root() -> Path:
    """Marker-free: the test image copies ``tests/`` and the packages into
    ``/app`` but not ``RULES.md``, so a repo-root marker file passes in a
    checkout and fails in the container."""
    root = Path(__file__).resolve().parents[2]
    if not (root / "tests").is_dir():
        raise RuntimeError(f"no tests/ directory above {__file__}")
    return root


def _test_roots(root: Path) -> list[Path]:
    """Every top-level ``tests*`` tree, found by scan.

    ``tests_server/`` holds none today and is in the domain anyway: it is
    ``COPY``-ed into the test stage, so a bare raises added there would run on
    the gate while sitting outside a ``tests/``-only census.
    """
    return sorted(d for d in root.iterdir() if d.is_dir() and d.name.startswith("tests"))


# ---------------------------------------------------------------------------
# The declared set. Measured at 6fb6979: 104 occurrences, 67 (file, class)
# pairs, 58 files. SHRINKING: adding ``match=`` to one means decrementing or
# deleting its line here, and this guard refuses a line it can no longer find.
# ---------------------------------------------------------------------------
DECLARED: dict[tuple[str, str], int] = {
    ("tests/decision_records/test_policy_store.py", "ValueError"): 3,
    ("tests/decision_records/test_run_driver.py", "AssertionError"): 1,
    ("tests/feat_subminds/test_submind_arbiter_grounding.py", "TypeError"): 1,
    ("tests/feat_subminds/test_submind_arbiter_grounding.py", "ValueError"): 1,
    ("tests/feat_subminds/test_submind_runtime.py", "ValueError"): 4,
    ("tests/learned_parameters/test_learn_parameter_capacity.py", "RuntimeError"): 1,
    ("tests/llm_seam/test_adapter_and_seam_guards.py", "TypeError"): 2,
    ("tests/llm_seam/test_adapter_and_seam_guards.py", "ValueError"): 5,
    ("tests/llm_seam/test_comprehension_reader.py", "Exception"): 2,
    ("tests/llm_seam/test_comprehension_reader.py", "type(exc)"): 1,
    ("tests/phase_01/test_retention.py", "ValueError"): 1,
    ("tests/phase_03/test_state.py", "FileNotFoundError"): 2,
    ("tests/phase_03/test_state.py", "ValueError"): 3,
    ("tests/phase_04/test_state.py", "FileNotFoundError"): 2,
    ("tests/phase_04/test_state.py", "RuntimeError"): 4,
    ("tests/phase_04/test_state.py", "ValueError"): 1,
    ("tests/phase_05a/test_metaedge_dataclass.py", "TypeError"): 2,
    ("tests/phase_05b/test_intergraph_edge_type.py", "Exception"): 1,
    ("tests/phase_05b/test_state_v2.py", "ValueError"): 3,
    ("tests/phase_05c/test_intergraph_hyperedge.py", "TypeError"): 1,
    ("tests/phase_05c/test_state_v3_round_trip.py", "ValueError"): 2,
    ("tests/phase_05d/test_meta_vocab_dataclasses.py", "Exception"): 2,
    ("tests/phase_05d/test_state_v3_schema_migration.py", "ValueError"): 1,
    ("tests/phase_06/test_composite.py", "IndexError"): 1,
    ("tests/phase_07/test_raises_on_nth_call.py", "ValueError"): 1,
    ("tests/phase_08/test_after_load_observer_dispatcher.py", "KeyboardInterrupt"): 1,
    ("tests/phase_08/test_load_metagraph_recovery.py", "Exception"): 1,
    ("tests/phase_09/test_xref_dataclass.py", "TypeError"): 1,
    ("tests/phase_11/test_migrate_from_unit.py", "(AttributeError, Exception)"): 1,
    ("tests/phase_15a/test_importer_protocol.py", "(AttributeError, Exception)"): 1,
    ("tests/phase_18/test_argon2.py", "Exception"): 1,
    ("tests/phase_18/test_session.py", "Exception"): 2,
    ("tests/phase_18/test_users.py", "Exception"): 1,
    ("tests/phase_18/test_users.py", "ValueError"): 1,
    ("tests/phase_19/test_ttl_injection.py", "Exception"): 1,
    ("tests/phase_20/test_reset_admin_atomicity.py", "RuntimeError"): 1,
    ("tests/phase_21/test_admin_query_audit_time_window.py", "ValueError"): 4,
    ("tests/phase_27/test_identifiers.py", "ValueError"): 3,
    ("tests/phase_28/test_capability_gate.py", "PermissionError"): 2,
    ("tests/phase_28/test_capacity_bootstrap.py", "ValueError"): 1,
    ("tests/phase_30/test_pipeline_dataclasses.py", "Exception"): 1,
    ("tests/phase_33/test_kl_writeable.py", "Exception"): 1,
    ("tests/phase_33/test_write_outcome_dataclass.py", "Exception"): 1,
    ("tests/phase_34/test_write_handle_mint_iri.py", "KeyError"): 1,
    ("tests/phase_36/test_validators.py", "Exception"): 1,
    ("tests/phase_39/test_iri_builders_registry_shape.py", "KeyError"): 1,
    ("tests/phase_40/test_family_rules_lookup.py", "ValueError"): 2,
    ("tests/phase_42/test_bipartite_detector.py", "SystemExit"): 1,
    ("tests/phase_42/test_typed_capacity_context.py", "TypeError"): 1,
    ("tests/phase_43/test_l2schema_subclass.py", "TypeError"): 1,
    ("tests/phase_46/test_als_registry.py", "ValueError"): 2,
    ("tests/phase_46/test_intelligence_layer_lifecycle.py", "NotImplementedError"): 1,
    ("tests/phase_46/test_intelligence_layer_lifecycle.py", "RuntimeError"): 1,
    ("tests/phase_46/test_mm_resolver.py", "KeyError"): 1,
    ("tests/phase_46/test_three_sub_mm.py", "KeyError"): 1,
    ("tests/phase_47/test_instance_iri_builders.py", "ValueError"): 4,
    ("tests/phase_47/test_replan_and_skeletons.py", "ValueError"): 1,
    ("tests/phase_48/test_capacity_mm_writer.py", "ValueError"): 1,
    ("tests/phase_48/test_kl_version_hooks.py", "Exception"): 1,
    ("tests/phase_48/test_kl_version_hooks.py", "KeyError"): 1,
    ("tests/phase_48/test_knowledge_mm_writer.py", "KeyError"): 2,
    ("tests/phase_48/test_map_member_multiinput.py", "ValueError"): 2,
    ("tests/phase_48/test_request_input_persist.py", "ValueError"): 1,
    ("tests/phase_50/test_installed_skills_substrate.py", "KeyError"): 1,
    ("tests/phase_50/test_skill_activation_resilience.py", "RuntimeError"): 1,
    ("tests/phase_50/test_skill_install_driver.py", "PermissionError"): 1,
    ("tests/policy_role/test_policy_role_core.py", "KeyError"): 1,
}


def test_no_generic_raises_beyond_the_declared_set():
    """The inverse. A new — or an additional — bare raises on a builtin class."""
    found, _ = census(_repo_root(), _test_roots(_repo_root()))
    new = sorted(
        f"{path}::{spelling} x{n}"
        for (path, spelling), n in found.items()
        if n > DECLARED.get((path, spelling), 0)
    )
    assert new == [], (
        f"{new} is a pytest.raises on a builtin exception class with no match= "
        "that this tree has not declared. Such a guard passes if ANYTHING of "
        "that class is raised anywhere in the block, which is how a designated "
        "mutation comes back green for the wrong reason. Add match='<a "
        "distinguishing fragment of the real message>', or raise a bespoke "
        "exception. Declaring it here instead is a review conversation."
    )


def test_the_declared_set_holds_nothing_the_tree_no_longer_does():
    """The ratchet. Without this direction the list never shrinks, and a
    deleted test leaves a line that silently re-permits the shape it named."""
    found, _ = census(_repo_root(), _test_roots(_repo_root()))
    stale = sorted(
        f"{path}::{spelling} declared {n}, found {found.get((path, spelling), 0)}"
        for (path, spelling), n in DECLARED.items()
        if found.get((path, spelling), 0) < n
    )
    assert stale == [], (
        f"{stale} is declared here and no longer in the tree. If you fixed or "
        "deleted it, decrement or delete its line in DECLARED - leaving it "
        "reserves permission for a shape nothing is using."
    )


def test_the_scan_is_not_empty():
    """The domain-emptied failure mode: a walk that finds nothing passes both
    directions above vacuously. Floors are far below the measured tree
    (2 roots, 738 calls, 104 occurrences) and above any plausible thinning."""
    root = _repo_root()
    roots = _test_roots(root)
    found, total = census(root, roots)
    assert len(roots) >= 2, f"only {[p.name for p in roots]} - a tests tree vanished"
    assert total >= 600, f"only {total} pytest.raises calls found - the walk is broken"
    assert sum(found.values()) >= 50, f"only {sum(found.values())} occurrences"


def _fabricate(tmp_path: Path, name: str, body: str) -> Path:
    (tmp_path / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_the_checker_flags_a_generic_raises_with_no_message(tmp_path):
    """RULES §9's red, on a tree built for it - no offending line is committed
    to this repo to prove the guard fires."""
    root = _fabricate(
        tmp_path,
        "test_fabricated.py",
        "import pytest\n"
        "def test_x():\n"
        "    with pytest.raises(ValueError):\n"
        "        pass\n"
        "def test_y():\n"
        "    with pytest.raises(ValueError):\n"
        "        pass\n",
    )
    found, total = census(root, [root])
    assert total == 2
    assert found == Counter({("test_fabricated.py", "ValueError"): 2}), found


def test_the_checker_passes_a_matched_or_bespoke_raises(tmp_path):
    """The other door. Both accepted forms, and the ATTR form held out of scope."""
    root = _fabricate(
        tmp_path,
        "test_fabricated.py",
        "import pytest, sqlite3\n"
        "from somewhere import LevelTwoIsBrokered\n"
        "def test_a():\n"
        "    with pytest.raises(ValueError, match='needs a resolver'):\n"
        "        pass\n"
        "def test_b():\n"
        "    with pytest.raises(LevelTwoIsBrokered):\n"
        "        pass\n"
        "def test_c():\n"
        "    with pytest.raises(sqlite3.IntegrityError):\n"
        "        pass\n",
    )
    found, total = census(root, [root])
    assert total == 3
    assert found == Counter(), found


def test_the_checker_sees_the_argument_forms_the_first_census_could_not(tmp_path):
    """The regression for this domain's own history.

    The first AST census named ``Name`` and ``Attribute`` arguments and dropped
    everything else, reporting 548/182 against a tree holding 552/184. A tuple
    is at least as wide as its widest arm, and a dynamic argument is a form no
    census may skip in silence.
    """
    root = _fabricate(
        tmp_path,
        "test_fabricated.py",
        "import pytest\n"
        "def test_a():\n"
        "    with pytest.raises((AttributeError, Exception)):\n"
        "        pass\n"
        "def test_b():\n"
        "    with pytest.raises(type(exc)):\n"
        "        pass\n"
        "def test_c():\n"
        "    with pytest.raises((CapabilityDeniedError, SkillInstallError)):\n"
        "        pass\n",
    )
    found, total = census(root, [root])
    assert total == 3
    assert found == Counter(
        {
            ("test_fabricated.py", "(AttributeError, Exception)"): 1,
            ("test_fabricated.py", "type(exc)"): 1,
        }
    ), found
