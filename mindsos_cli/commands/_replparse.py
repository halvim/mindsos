"""REPL-safe argument parsing for ``mindsos brain`` verbs.

``BrainREPL.dispatch`` must never raise or ``sys.exit`` — its contract is
``line -> str``. These helpers honour that: tokenization and flag parsing
return an error *string* rather than raising.

- :func:`tokenize` — ``shlex.split`` (adds quoting: ``"two words"``).
- :func:`parse` — maps short/long option aliases to canonical names and
  splits positionals; returns ``(opts, positionals, error)``.
- :func:`wants_help` — pre-scan for ``-h`` / ``--help`` (handled by the
  dispatcher before verb logic).
- :data:`SCOPE` — the shared ``-l/--local`` / ``-g/--global`` option spec.
"""

from __future__ import annotations

import shlex
from typing import Dict, List, Optional, Tuple

HELP_FLAGS = ("-h", "--help")

#: An option spec maps a canonical name -> (alias tuple, takes_value).
OptSpec = Dict[str, Tuple[Tuple[str, ...], bool]]

#: Scope options shared by nearly every verb.
SCOPE: OptSpec = {
    "local": (("-l", "--local"), False),
    "global": (("-g", "--global"), False),
}


def wants_help(tokens: List[str]) -> bool:
    """True if any token is a help flag (dispatcher prints the man page)."""
    return any(t in HELP_FLAGS for t in tokens)


def tokenize(line: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """shlex-split ``line``; return ``(tokens, None)`` or ``(None, error)``."""
    try:
        return shlex.split(line), None
    except ValueError as e:
        return None, f"parse error: {e}"


def _looks_negative_number(tok: str) -> bool:
    return len(tok) > 1 and tok[1].isdigit()


def parse(
    tokens: List[str], spec: OptSpec
) -> Tuple[Dict[str, object], List[str], Optional[str]]:
    """Split ``tokens`` into ``(opts, positionals, error)`` against ``spec``.

    ``opts`` maps canonical option name -> ``True`` (boolean) or the value
    (value-taking). Help flags are ignored here (pre-scanned upstream).
    Unknown options and missing values return an error string; ``-l``/``-g``
    are enforced mutually exclusive.
    """
    alias: Dict[str, Tuple[str, bool]] = {}
    for canon, (aliases, takes) in spec.items():
        for a in aliases:
            alias[a] = (canon, takes)

    opts: Dict[str, object] = {}
    positionals: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in HELP_FLAGS:
            i += 1
            continue
        is_flag = (
            tok.startswith("-") and tok != "-" and not _looks_negative_number(tok)
        )
        if is_flag:
            if tok not in alias:
                return {}, [], f"unknown option: {tok} (try -h)"
            canon, takes = alias[tok]
            if takes:
                if i + 1 >= len(tokens):
                    return {}, [], f"option {tok} needs a value"
                opts[canon] = tokens[i + 1]
                i += 2
            else:
                opts[canon] = True
                i += 1
        else:
            positionals.append(tok)
            i += 1

    if opts.get("local") and opts.get("global"):
        return {}, [], "-l and -g are mutually exclusive"
    return opts, positionals, None


def scope_of(opts: Dict[str, object]) -> str:
    """Resolve the scope selector: ``local`` | ``global`` | ``both``."""
    if opts.get("local"):
        return "local"
    if opts.get("global"):
        return "global"
    return "both"


__all__ = ["tokenize", "parse", "wants_help", "scope_of", "SCOPE", "OptSpec", "HELP_FLAGS"]
