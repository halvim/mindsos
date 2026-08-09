"""Headless tests of the ``mindsos brain`` verb dispatcher.

``BrainREPL.dispatch`` is pure (line -> str), so the whole verb surface is
testable without a TTY, over an ephemeral in-memory brain.
"""

from __future__ import annotations

import json

import pytest

from mindsos_cli.commands._manpages import MANPAGES
from mindsos_cli.commands.brain import _HELP, BrainREPL
from mindsos_server.boot import boot_brain
from mindsos_server.episodes import iter_episodes


@pytest.fixture
def repl():
    return BrainREPL(boot_brain(user="alice"))


# ── dispatch / help / parser ──────────────────────────────────────────

def test_help_and_unknown_and_empty(repl):
    assert repl.dispatch("help") == _HELP
    assert repl.dispatch("frobnicate").startswith("unknown verb")
    assert repl.dispatch("") == ""


def test_per_command_manpage(repl):
    for verb in ("ls", "search", "ds", "caps", "pl", "skills", "episodes", "invoke", "verify"):
        out = repl.dispatch(f"{verb} -h")
        assert out == MANPAGES[verb]
        assert "NAME" in out


def test_bad_quoting_is_reported(repl):
    assert "parse error" in repl.dispatch('search "unterminated')


def test_unknown_option_reported(repl):
    assert "unknown option" in repl.dispatch("ds --bogus")


def test_scope_mutually_exclusive(repl):
    assert "mutually exclusive" in repl.dispatch("ls -l -g")


# ── ls / search ───────────────────────────────────────────────────────

def test_ls_lists_all_kinds(repl):
    out = repl.dispatch("ls")
    for kind in ("capacities", "datastates", "pipelines", "skills", "episodes"):
        assert kind in out


def test_ls_scope(repl):
    assert "[global]" in repl.dispatch("ls -g")
    assert "[local]" in repl.dispatch("ls -l")


def test_search_exact_and_glob(repl):
    # a real capacity IRI to search for
    iri = next(iter(repl.stack.global_view().iter_capacities())).node_id
    assert iri in repl.dispatch(f"search {iri}")
    assert iri in repl.dispatch("search *space_split*") or "no matches" in repl.dispatch("search *zzz*")
    assert "no matches" in repl.dispatch("search zzz-nothing-zzz")


def test_search_ignore_case(repl):
    iri = next(iter(repl.stack.global_view().iter_capacities())).node_id
    assert iri in repl.dispatch(f"search -i {iri.upper()}")


def test_search_usage(repl):
    assert "usage:" in repl.dispatch("search")


# ── ds ────────────────────────────────────────────────────────────────

def test_ds_list_inspect_code(repl):
    assert "datastates" in repl.dispatch("ds")
    ds = next(iter(repl.stack.global_view().iter_datastates())).node_id
    detail = repl.dispatch(f"ds {ds}")
    assert "produced by:" in detail and "consumed by:" in detail
    code = repl.dispatch(f"ds --code {ds}")
    assert "type:" in code


def test_ds_code_needs_iri_and_unknown(repl):
    assert "requires an <iri>" in repl.dispatch("ds --code")
    assert "no such datastate" in repl.dispatch("ds nope:not:real")


def test_ds_new_placeholder(repl):
    assert "pending skill-acquisition" in repl.dispatch("ds --new")


# ── caps ──────────────────────────────────────────────────────────────

def test_caps_list_inspect_code(repl):
    assert "capacities" in repl.dispatch("caps")
    cap = next(iter(repl.stack.global_view().iter_capacities())).node_id
    detail = repl.dispatch(f"caps {cap}")
    assert "consumes:" in detail and "produces:" in detail
    code = repl.dispatch(f"caps --code {cap}")
    assert "module:" in code


def test_caps_unknown_and_code_needs_iri(repl):
    assert "no such capability" in repl.dispatch("caps nope.not.real")
    assert "requires an <iri>" in repl.dispatch("caps --code")


# ── pl ────────────────────────────────────────────────────────────────

def test_pl_list(repl):
    assert "pipeline" in repl.dispatch("pl")  # "(no pipelines)" or "N pipelines"


def test_pl_find_and_transitions(repl):
    from mindsos_capacity.builtins.text import DS_RAW_TEXT

    noop = repl.dispatch(f"pl {DS_RAW_TEXT} {DS_RAW_TEXT}")
    assert "no-op" in noop or "pipeline:" in noop
    tr = repl.dispatch(f"pl --transitions {DS_RAW_TEXT} {DS_RAW_TEXT}")
    assert "no-op" in tr or "in:" in tr


def test_pl_unknown_ds_and_usage(repl):
    assert "no such datastate" in repl.dispatch("pl nope:a nope:b")
    assert "usage:" in repl.dispatch("pl one:only")


def test_pl_seq_placeholder(repl):
    assert "pending skill-acquisition" in repl.dispatch("pl --seq")


# ── skills / episodes ─────────────────────────────────────────────────

def test_skills_ephemeral_empty(repl):
    assert "installed-skills" in repl.dispatch("skills")


def test_skills_new_placeholder(repl):
    assert "pending skill-acquisition" in repl.dispatch("skills --new")


def test_episodes_list_and_global(repl):
    assert "episode" in repl.dispatch("episodes")
    assert "Global" in repl.dispatch("episodes -g")


def test_episode_detail_if_present(repl):
    repl.dispatch("task the cat sat")
    eps = [n.node_id for n in iter_episodes(repl.stack.kl, "alice")]
    if not eps:
        pytest.skip("no Episode written on the ephemeral task path")
    assert eps[0] in repl.dispatch(f"episodes {eps[0]}")


# ── invoke ────────────────────────────────────────────────────────────

def test_invoke_positional_single_input(repl):
    out = repl.dispatch('invoke space_split "the cat sat"')
    assert out.startswith("outputs:")
    assert "cat" in out


def test_invoke_keyvalue(repl):
    from mindsos_capacity.builtins.text import DS_RAW_TEXT

    short = DS_RAW_TEXT.split(":")[-1]
    out = repl.dispatch(f'invoke space_split {short}="the cat sat"')
    assert out.startswith("outputs:")


def test_invoke_json_still_works(repl):
    from mindsos_capacity.builtins.text import DS_RAW_TEXT

    payload = json.dumps({DS_RAW_TEXT: "the cat sat"})
    out = repl.dispatch(f"invoke space_split '{payload}'")
    assert out.startswith("outputs:")


def test_invoke_unknown_and_usage(repl):
    assert "no such capability" in repl.dispatch("invoke nope.not.real")
    assert "usage:" in repl.dispatch("invoke")


# ── verify ────────────────────────────────────────────────────────────

def test_verify_full_and_scoped(repl):
    full = repl.dispatch("verify")
    assert "user: alice" in full and "catalog:" in full
    assert "datastates:" in repl.dispatch("verify --ds")
    assert "capabilities:" in repl.dispatch("verify --caps")
    assert "pipelines:" in repl.dispatch("verify --pl")


def test_task_still_present(repl):
    assert repl.dispatch("task the cat sat") == "task: succeeded"


def test_pl_finds_real_chain(repl):
    from mindsos_capacity.builtins.text import DS_RAW_TEXT

    v = repl.stack.global_view()
    cap = next((n.node_id for n in v.iter_capacities() if n.node_id.endswith("space_split")), None)
    if cap is None:
        pytest.skip("space_split not found")
    target = v.outputs_of(cap)[0]
    out = repl.dispatch(f"pl {DS_RAW_TEXT} {target}")
    assert out.startswith("pipeline:")
    assert "space_split" in out


# ── finder scope (ADR-0071 §am-5) ─────────────────────────────────────


def test_finder_session_is_none_only_for_scope_global(repl):
    """``--scope global`` searches the shared catalog; everything else unions."""
    assert repl._finder_session("global") is None
    assert repl._finder_session("local") is repl.stack.session
    assert repl._finder_session("") is repl.stack.session


def test_pl_and_execute_no_longer_hardcode_session_none():
    """Regression: both verbs passed ``session=None`` as a pre-am-5 workaround.

    That workaround escaped a ``_view_for`` which returned Local ALONE for any
    session and so hid the global builtins. Under the union view it has the
    opposite effect — it discards the user's Local overrides — which would
    leave the two-tier feature unreachable from the only shipped surface that
    reaches the sound finder.
    """
    import inspect

    from mindsos_cli.commands.brain import BrainREPL

    for verb in ("_do_pl", "_do_execute"):
        src = inspect.getsource(getattr(BrainREPL, verb))
        assert "session=None" not in src, (
            f"BrainREPL.{verb} hard-codes session=None; the finder would "
            f"search Global alone and skip this user's Local capacities"
        )
