---
last_confirmed_phase: 12
---

# `mindsos knowledge` — CLI reference

Phase 12 ships five verbs under `mindsos knowledge`, all backed by
the pure-library surface in
[`mindsos_knowledge.identifiers`](../../api/knowledge/identifiers.md).

## Verbs

### `iri build`

Build a version-qualified IRI for the given role + kwargs:

```bash
mindsos knowledge iri build --role memories --kind memory \
    --version 1 --user-id alice --memory-id m-001 --json
```

Required flags vary by role + kind — the CLI prints the missing flag
list on usage error. Exit codes:

* `0` — success.
* `1` — domain error (`RefFormatError`, e.g. bad `user_id` charset).
* `2` — usage error (unknown role, missing required flag, wrong
  `--kind` for the role).

### `iri parse`

Decompose a version-qualified IRI:

```bash
mindsos knowledge iri parse episodic-memories-1:memory:alice:m-001 --json
```

Output (JSON):

```json
{
  "full":    "episodic-memories-1:memory:alice:m-001",
  "role":    "episodic_memories",
  "source":  "episodic-memories",
  "version": "1",
  "kind":    "memory",
  "body":    "alice:m-001"
}
```

`capacity-state` IRIs leave the post-`snapshot:` body opaque (PB-8).

### `iri validate`

Yes/no probe over `is_version_qualified_iri`. Exit `0` if valid,
`1` if not. `alignment:lex<->con` graph-names are NOT
version-qualified IRIs — `validate` returns `1` on them per PB-4.

### `ref-types --list`

Enumerate the ADR-0047 starter vocabulary:

```bash
mindsos knowledge ref-types --list --json
```

### `roles --list`

Enumerate role constants. Optional mutex flags `--seed-only` and
`--upper-only`:

```bash
mindsos knowledge roles --list --json
mindsos knowledge roles --list --seed-only
mindsos knowledge roles --list --upper-only
```

## See also

* [API: `mindsos_knowledge.identifiers`](../../api/knowledge/identifiers.md)
* [API: `REF_TYPES`](../../api/knowledge/ref-types.md)
* [L2 concept: identifiers](../../concepts/identifiers.md)
