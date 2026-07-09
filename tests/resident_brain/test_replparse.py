"""Unit tests for the REPL-safe flag parser (pure; no repo deps needed)."""

from __future__ import annotations

from mindsos_cli.commands._replparse import (
    SCOPE,
    parse,
    scope_of,
    tokenize,
    wants_help,
)


def test_tokenize_quotes():
    toks, err = tokenize('invoke cap "two words"')
    assert err is None
    assert toks == ["invoke", "cap", "two words"]


def test_tokenize_bad_quote_returns_error():
    toks, err = tokenize('search "unterminated')
    assert toks is None
    assert "parse error" in err


def test_scope_flags():
    opts, pos, err = parse(["-l"], SCOPE)
    assert err is None and scope_of(opts) == "local"
    opts, pos, err = parse(["--global"], SCOPE)
    assert scope_of(opts) == "global"
    assert scope_of({}) == "both"


def test_scope_mutually_exclusive():
    _o, _p, err = parse(["-l", "-g"], SCOPE)
    assert "mutually exclusive" in err


def test_unknown_option():
    _o, _p, err = parse(["--nope"], SCOPE)
    assert "unknown option" in err


def test_value_option_and_positionals():
    spec = {**SCOPE, "code": (("--code",), False)}
    opts, pos, err = parse(["some:iri", "--code", "-g"], spec)
    assert err is None
    assert opts.get("code") is True
    assert opts.get("global") is True
    assert pos == ["some:iri"]


def test_wants_help():
    assert wants_help(["-h"]) and wants_help(["x", "--help"])
    assert not wants_help(["x"])


def test_negative_number_is_positional():
    _o, pos, err = parse(["-5"], SCOPE)
    assert err is None and pos == ["-5"]
