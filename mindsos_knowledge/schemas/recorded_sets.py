"""Recorded-sets role-graph schema — pointers to recorded response sets (``mindsos_llm`` I-10).

Plan rulings **R1**, **R2**, **R8** (``docs/plans/MINDSOS_LLM_PLAN.md``), shape as
built in ADR-0210 amendment 6. ``mindsos_knowledge`` (L2) **HOLDS the pointer and
its provenance**; the payloads stay a **FILE**; ``mindsos_capacity`` (L3) **WRITES**
the pointer. This module is the holding half.

**The problem it closes.** A conclusion read by the borrowed model carries a
``request_key``, and nothing in the graph named the recorded set whose replay
answers it — so a stored conclusion could not be re-run without the model, which
is the third clause of the module's end state (plan §1).

**Single NodeType** (``RecordedSet``); **no EdgeTypes** — the ``prompts`` /
``policies`` / ``learned-pipelines`` zero-edge shape. A set relates to a
conclusion through the ``request_key`` both carry, and an edge would be a second
place for that truth to live (ADR-0192's criterion).

**Identity is the file's ``sha256``** (R8, R14): it is the node's address AND a
property, so the pointer is VERIFIABLE against the file it names — re-hash the
file at ``file_uri`` and compare. A re-capture of the same bytes is the same node.

**Discipline: ``append_only``** — a capture is never rewritten; a re-export is
different bytes and a new node. ⚠ **DECLARED, NOT ENFORCED at v1**
(``validate_mutation_discipline`` is uncalled system-wide); the store's duplicate
refusal is the enforcement. For THIS role that gap does not reach *shown*: the
identity is a hash of the file, so an overwritten node would no longer verify
against the file its own ``file_uri`` names.

**The node's ``value`` payload** is the derived manifest (``responses``,
``key_schema_version``, ``identities``, ``prompts``) plus the SORTED
``request_keys`` — a ``dict``, which ADR-0182's codec JSON-encodes into
``_value_json``. ⚠ Opaque to Cypher (ADR-0182 rule 5), and keys cannot be lifted
into properties (primitives only), so getting from a conclusion to its set is a
decode scan — measured and recorded for I-12, not guessed at here.

**Local-only.** ``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema, StorageMode


# ── Node type ──────────────────────────────────────────────────────────

NODE_RECORDED_SET = "RecordedSet"

RECORDED_SETS_NODE_TYPES: tuple[str, ...] = (NODE_RECORDED_SET,)


# ── Edge types ─────────────────────────────────────────────────────────

RECORDED_SETS_EDGE_TYPES: tuple[str, ...] = ()  # v1 has no edge types.


# ── Advisory property constants (ADR-0210 am-6) ────────────────────────

RECORDED_SET_PROPS: frozenset[str] = frozenset({
    # The identity (R8, R14): also the node's address.
    "sha256",
    # Where the file was when the pointer was written: resolved absolute
    # path, no scheme (R18). Provenance, not identity.
    "file_uri",
    # Lifted from the payload so they are queryable (ADR-0182 rule 5).
    "responses",
    "key_schema_version",
    # Facts about the WRITE, not claims about the recording (R16).
    "recorded_at",
    "recorded_by",
    "storage_mode",
    # Only when present: derived from the payloads (R9, R15), and the
    # recorder's own annotation.
    "credential_level",
    "note",
})

#: Named so a reader looking for what was ruled OUT finds it beside what was
#: ruled in. ``set_id`` would be a second spelling of the identity (R8, R14);
#: ``vendor_id`` is stamped by nothing (R9); ``captured_at`` is a claim no
#: payload supports (R16).
RULED_OUT_PROPS: frozenset[str] = frozenset({"set_id", "vendor_id", "captured_at"})

#: What the store writes into the node's ``storage_mode`` property (R17) —
#: declared below AND written, unlike the ``prompts`` role.
PAYLOAD_STORAGE_MODE = StorageMode.FALKOR_BLOB.value


# ── Per-NodeType large-payload field declaration (ADR-0151) ───────────

STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    NODE_RECORDED_SET: frozenset({"value"}),
}


def build_recorded_sets_schema(strict: bool = False) -> L2Schema:
    """Construct the recorded-sets role Schema (Local-only, ``append_only``).

    Args:
        strict: Opt-in property-type enforcement. Default ``False`` per
            ADR-0149.
    """
    s = L2Schema(mutation_discipline=Discipline.APPEND_ONLY, strict=strict)
    for nt in RECORDED_SETS_NODE_TYPES:
        s.add_node_type(NodeType(nt))
    return s


__all__ = [
    "NODE_RECORDED_SET",
    "PAYLOAD_STORAGE_MODE",
    "RECORDED_SETS_EDGE_TYPES",
    "RECORDED_SETS_NODE_TYPES",
    "RECORDED_SET_PROPS",
    "RULED_OUT_PROPS",
    "STORAGE_MODE_FIELDS",
    "build_recorded_sets_schema",
]
