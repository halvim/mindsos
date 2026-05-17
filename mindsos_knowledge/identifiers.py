"""Stable-IRI identifiers for L2 Knowledge content.

Port of the v3 ``mindsos_knowledge/identifiers.py`` (seed roles
DOLCE / OEWN / FrameNet) **extended** with the 7 upper-layer builders
declared by ADR-0045 (pipelines, task-patterns, memories,
problem-trace, capacity-state). Together this module ships the full
14-builder surface ADR-0045 names.

Layout:

* §1 Role constants + frozensets.
* §2 Regex validators (`_VERSION_RE`, `_FRAGMENT_RE`, `_USER_ID_RE`)
  + private helpers (`_ensure_version`, `_normalise_fragment`,
  `_ensure_user_id`).
* §3 Seed-role IRI builders (DOLCE / OEWN / FrameNet — v3 verbatim).
* §4 Upper-layer IRI builders (ADR-0045 — Phase 12 net-new).
* §5 `alignment_role` graph-name helper (NOT a version-qualified IRI;
  PB-4 lock).
* §6 Source prefix table (`_PREFIXES`), kind-detection table
  (`_KINDS_PER_ROLE`), `ParsedIri` dataclass, `parse_iri`,
  `is_version_qualified_iri`.
* §7 Ref-key helpers + `REF_TYPE_KEY` + `REF_TYPES` frozenset.

Round-trip contract per PB-10:
``parse_iri(builder(*args)).full == builder(*args)`` for every
builder. Field-level decomposition (e.g. `parse_capacity_snapshot_iri`)
is deferred to the consumer phase (see ``__init__.py`` docstring).

``capacity_snapshot_iri`` per PB-8 embeds a colon-bearing inner
``capacity_iri`` in its body; the parser leaves the body opaque
(no kind extraction beyond ``snapshot:``) and full-string round-trip
holds.

``user_id`` charset per PB-11 + ADR-0044 §amendment-1 is
``^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$``. Enforced in ``memory_iri`` and
``capacity_snapshot_iri``; raises ``RefFormatError`` on violation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from .exceptions import RefFormatError


# ── §1 Role constants ──────────────────────────────────────────────────

# Seed roles — v3
ROLE_ONTOLOGY = "ontology"
ROLE_LEXICON = "lexicon"
ROLE_CONCEPTS = "concepts"

# Upper-layer roles — ADR-0045 + ADR-0044 (memories) + ADR-0066/0072
# (capacity-state / problem-trace) + Phase 12 PB-9 lock.
ROLE_PROMOTED_PIPELINES = "promoted-pipelines"
ROLE_TASK_PATTERNS = "task-patterns"
ROLE_MEMORIES = "memories"
ROLE_PROBLEM_TRACE = "problem-trace"
ROLE_CAPACITY_STATE = "capacity-state"

SEED_ROLES = frozenset({ROLE_ONTOLOGY, ROLE_LEXICON, ROLE_CONCEPTS})
UPPER_LAYER_ROLES = frozenset({
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_MEMORIES,
    ROLE_PROBLEM_TRACE,
    ROLE_CAPACITY_STATE,
})
ALL_ROLES = SEED_ROLES | UPPER_LAYER_ROLES


# ── §2 Regex validators + private helpers ──────────────────────────────

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_FRAGMENT_RE = re.compile(r"^[^\s]+$")  # anything non-whitespace
_USER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")  # PB-11


def _ensure_version(version: object) -> str:
    if not isinstance(version, str) or not version or not _VERSION_RE.match(version):
        raise RefFormatError(
            f"Invalid version string {version!r} — must match {_VERSION_RE.pattern}"
        )
    return version


def _normalise_fragment(fragment: object) -> str:
    """Canonicalise a source fragment for use in a stable IRI.

    - Strip whitespace
    - Apply NFC unicode normalisation
    - Reject empty results
    """
    if fragment is None:
        raise RefFormatError("Empty fragment")
    f = unicodedata.normalize("NFC", str(fragment)).strip()
    if not f or not _FRAGMENT_RE.match(f):
        raise RefFormatError(f"Invalid IRI fragment: {fragment!r}")
    return f


def _ensure_user_id(user_id: object) -> str:
    """Validate ``user_id`` charset per PB-11 + ADR-0044 §amendment-1.

    Charset: ``^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$``. Phase 18 server
    user-store inherits this invariant.
    """
    if not isinstance(user_id, str) or not _USER_ID_RE.match(user_id):
        raise RefFormatError(
            f"Invalid user_id {user_id!r} — must match {_USER_ID_RE.pattern} "
            f"(ADR-0044 §amendment-1)"
        )
    return user_id


# ── §3 Seed-role IRI builders (v3 verbatim port) ───────────────────────


def dolce_iri(version: str, fragment: str) -> str:
    """Build a DOLCE/DUL stable IRI: ``dolce-dul-<version>:<fragment>``.

    Example: ``dolce_iri("4.0", "PhysicalObject")`` →
    ``"dolce-dul-4.0:PhysicalObject"``.
    """
    return f"dolce-dul-{_ensure_version(version)}:{_normalise_fragment(fragment)}"


def oewn_synset_iri(version: str, synset_id: str, pos: str) -> str:
    """OEWN synset: ``oewn-<v>:synset:<id>-<pos>``."""
    v = _ensure_version(version)
    sid = _normalise_fragment(synset_id)
    p = _normalise_fragment(pos)
    return f"oewn-{v}:synset:{sid}-{p}"


def oewn_sense_iri(version: str, sense_id: str) -> str:
    """OEWN sense: ``oewn-<v>:sense:<id>``."""
    return f"oewn-{_ensure_version(version)}:sense:{_normalise_fragment(sense_id)}"


def oewn_lemma_iri(version: str, lemma: str, pos: str) -> str:
    """OEWN lemma: ``oewn-<v>:lemma:<lemma>-<pos>``."""
    v = _ensure_version(version)
    lem = _normalise_fragment(lemma)
    p = _normalise_fragment(pos)
    return f"oewn-{v}:lemma:{lem}-{p}"


def framenet_frame_iri(version: str, frame_id: str) -> str:
    """FrameNet frame: ``framenet-<v>:frame:<id>``."""
    return f"framenet-{_ensure_version(version)}:frame:{_normalise_fragment(frame_id)}"


def framenet_lu_iri(version: str, lu_id: str) -> str:
    """FrameNet lexical-unit: ``framenet-<v>:lu:<id>``."""
    return f"framenet-{_ensure_version(version)}:lu:{_normalise_fragment(lu_id)}"


def framenet_fe_iri(version: str, frame_id: str, fe_id: str) -> str:
    """FrameNet frame-element: ``framenet-<v>:fe:<frame_id>:<fe_id>``."""
    v = _ensure_version(version)
    fid = _normalise_fragment(frame_id)
    feid = _normalise_fragment(fe_id)
    return f"framenet-{v}:fe:{fid}:{feid}"


# ── §4 Upper-layer IRI builders (ADR-0045, Phase 12 net-new) ───────────


def pipeline_iri(version: str, pipeline_id: str) -> str:
    """Promoted pipeline: ``promoted-pipelines-<v>:pipeline:<id>``."""
    v = _ensure_version(version)
    pid = _normalise_fragment(pipeline_id)
    return f"promoted-pipelines-{v}:pipeline:{pid}"


def pipeline_step_iri(version: str, pipeline_id: str, step_id: str) -> str:
    """Promoted-pipeline step: ``promoted-pipelines-<v>:step:<pid>:<sid>``."""
    v = _ensure_version(version)
    pid = _normalise_fragment(pipeline_id)
    sid = _normalise_fragment(step_id)
    return f"promoted-pipelines-{v}:step:{pid}:{sid}"


def task_pattern_iri(version: str, pattern_id: str) -> str:
    """Task pattern: ``task-patterns-<v>:pattern:<id>``."""
    v = _ensure_version(version)
    pid = _normalise_fragment(pattern_id)
    return f"task-patterns-{v}:pattern:{pid}"


def subgoal_template_iri(version: str, pattern_id: str, subgoal_id: str) -> str:
    """Task-pattern subgoal template:
    ``task-patterns-<v>:subgoal:<pid>:<sid>``."""
    v = _ensure_version(version)
    pid = _normalise_fragment(pattern_id)
    sid = _normalise_fragment(subgoal_id)
    return f"task-patterns-{v}:subgoal:{pid}:{sid}"


def memory_iri(version: str, user_id: str, memory_id: str) -> str:
    """User memory (Local-per-user, ADR-0044):
    ``memories-<v>:memory:<user_id>:<memory_id>``.

    ``user_id`` is part of the IRI per ADR-0044; charset enforced by
    `_ensure_user_id` per ADR-0044 §amendment-1.
    """
    v = _ensure_version(version)
    uid = _ensure_user_id(user_id)
    mid = _normalise_fragment(memory_id)
    return f"memories-{v}:memory:{uid}:{mid}"


def problem_trace_iri(version: str, trace_id: str) -> str:
    """Problem-trace entry: ``problem-trace-<v>:entry:<id>``."""
    v = _ensure_version(version)
    tid = _normalise_fragment(trace_id)
    return f"problem-trace-{v}:entry:{tid}"


def capacity_snapshot_iri(
    version: str, user_id: str, capacity_iri: str, taken_at: str
) -> str:
    """Capacity-state snapshot (Local-per-user, ADR-0044 + ADR-0066):
    ``capacity-state-<v>:snapshot:<user_id>:<capacity_iri>:<taken_at>``.

    Per PB-8: ``capacity_iri`` is itself ``capacity:<category>:<name>``
    (ADR-0066) and ``taken_at`` is ISO8601 with colons. The parser
    leaves the body opaque (no kind-extraction beyond ``snapshot:``);
    full-string round-trip via ``parse_iri(...).full`` holds.

    Field-level decomposition is deferred to the first consumer
    (Phase 28+).
    """
    v = _ensure_version(version)
    uid = _ensure_user_id(user_id)
    ci = _normalise_fragment(capacity_iri)
    ta = _normalise_fragment(taken_at)
    return f"capacity-state-{v}:snapshot:{uid}:{ci}:{ta}"


# ── §5 alignment_role graph-name helper (NOT an IRI builder) ──────────


def alignment_role(role_a: str, role_b: str) -> str:
    """Canonical name for an alignment graph bridging ``role_a`` and ``role_b``.

    The two roles are sorted so ``alignment_role("lexicon", "concepts")``
    and ``alignment_role("concepts", "lexicon")`` return the same string.

    Returns: ``"alignment:<a>-<b>"`` where ``<a>`` and ``<b>`` are the
    sorted role names. NOT a version-qualified IRI per PB-4 lock —
    this is a **graph name** used for metagraph routing, not a
    node IRI; ``parse_iri()`` will reject it.
    """
    a, b = sorted((role_a, role_b))
    return f"alignment:{a}<->{b}"


# ── §6 Source prefix table + parser ────────────────────────────────────

# First match wins. Order chosen for clarity, not specificity (no two
# prefixes share a leading substring).
_PREFIXES: tuple[tuple[str, str], ...] = (
    ("dolce-dul-", ROLE_ONTOLOGY),
    ("oewn-", ROLE_LEXICON),
    ("framenet-", ROLE_CONCEPTS),
    ("promoted-pipelines-", ROLE_PROMOTED_PIPELINES),
    ("task-patterns-", ROLE_TASK_PATTERNS),
    ("memories-", ROLE_MEMORIES),
    ("problem-trace-", ROLE_PROBLEM_TRACE),
    ("capacity-state-", ROLE_CAPACITY_STATE),
)

# Per-role kind-extraction whitelist. The parser strips the kind
# sub-prefix from the body when (and only when) the candidate matches
# one of the role's allowed kinds. Roles absent from this table (e.g.
# ROLE_ONTOLOGY) get no kind extraction — body is the entire `rest`.
_KINDS_PER_ROLE: dict[str, frozenset[str]] = {
    ROLE_LEXICON: frozenset({"synset", "sense", "lemma"}),
    ROLE_CONCEPTS: frozenset({"frame", "lu", "fe"}),
    ROLE_PROMOTED_PIPELINES: frozenset({"pipeline", "step"}),
    ROLE_TASK_PATTERNS: frozenset({"pattern", "subgoal"}),
    ROLE_MEMORIES: frozenset({"memory"}),
    ROLE_PROBLEM_TRACE: frozenset({"entry"}),
    ROLE_CAPACITY_STATE: frozenset({"snapshot"}),
}


@dataclass(frozen=True)
class ParsedIri:
    """The decomposed form of a stable IRI."""

    role: str  # one of ALL_ROLES
    source: str  # e.g. "dolce-dul" / "oewn" / "memories" / "capacity-state"
    version: str  # e.g. "4.0", "2024", "1.7", "1"
    kind: Optional[str]  # e.g. "synset" / "memory" / "snapshot" — None for DOLCE etc.
    body: str  # remainder after `<source>-<version>:` (and `<kind>:` if extracted)
    full: str  # the original IRI


def parse_iri(iri: object) -> ParsedIri:
    """Parse a version-qualified stable IRI into its components.

    Raises :class:`RefFormatError` on any shape that doesn't match the
    version-qualified convention. A bare fragment (e.g. ``PhysicalObject``
    with no prefix), an alignment graph-name (``alignment:lex<->con``),
    or a non-string input is invalid.
    """
    if not isinstance(iri, str) or ":" not in iri:
        raise RefFormatError(
            f"Not a version-qualified IRI: {iri!r} — expected "
            f"'<source>-<version>:<body>' (e.g. 'dolce-dul-4.0:PhysicalObject')"
        )

    # Identify source prefix.
    role: Optional[str] = None
    source_prefix: Optional[str] = None
    for prefix, detected_role in _PREFIXES:
        if iri.startswith(prefix):
            source_prefix = prefix.rstrip("-")  # "dolce-dul" / "oewn" / "memories" / ...
            role = detected_role
            break
    if role is None or source_prefix is None:
        known = [p for p, _ in _PREFIXES]
        raise RefFormatError(
            f"IRI {iri!r} does not start with a known source prefix "
            f"(known prefixes: {known})"
        )

    # Split off the version at the first colon. Format:
    # `<source>-<version>:<rest>` — the source prefix already ends with
    # a trailing dash, so the version sits between dash and colon.
    source_and_version, rest = iri.split(":", 1)
    version_part = source_and_version[len(source_prefix) + 1 :]
    if not version_part:
        raise RefFormatError(f"IRI {iri!r} is missing a version component")

    # Optionally extract a kind prefix on the body, driven by
    # `_KINDS_PER_ROLE`. Roles absent from the table keep `body = rest`
    # and `kind = None`.
    kind: Optional[str] = None
    body = rest
    allowed_kinds = _KINDS_PER_ROLE.get(role)
    if allowed_kinds and ":" in rest:
        candidate_kind, candidate_body = rest.split(":", 1)
        if candidate_kind in allowed_kinds:
            kind = candidate_kind
            body = candidate_body

    return ParsedIri(
        role=role,
        source=source_prefix,
        version=version_part,
        kind=kind,
        body=body,
        full=iri,
    )


def is_version_qualified_iri(value: object) -> bool:
    """Return True iff ``value`` is a well-formed version-qualified IRI."""
    if not isinstance(value, str):
        return False
    try:
        parse_iri(value)
    except RefFormatError:
        return False
    return True


# ── §7 Ref property keys + REF_TYPES ──────────────────────────────────


def global_ref_key(role: str) -> str:
    """The ``ref:global_<role>`` property key used on Local nodes."""
    return f"ref:global_{role}"


def local_ref_key(role: str) -> str:
    """The ``ref:<role>`` property key used on same-metagraph nodes."""
    return f"ref:{role}"


REF_TYPE_KEY = "ref_type"

# Starter vocabulary for ref_type per ADR-0047 (open vocabulary).
# Extension recipe: (1) add to this frozenset, (2) add to the role docs,
# (3) add a test, (4) optionally update any classifier, (5) run the
# parity test (Phase 27+ when L3 ships its mirror per ADR-0067).
REF_TYPES = frozenset({
    "SPECIALISES",
    "INSTANCE_OF",
    "RENAMES",
    "EXTENDS",
    "CONTRADICTS",
    "PROXY",
    # Stamped on a Local draft after promotion copies it into the
    # Global metagraph. The draft stays as a breadcrumb pointing at
    # its new Global IRI. Added 2026-04-22 via the ADR-0047 recipe.
    "PROMOTED",
})
