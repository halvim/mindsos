# Phase 04-v2 — Implementation Log

> Companion to `confirmation_docs/PHASE_MAP.md` Phase 04-v2 row.
> Written by the implementing chat (2026-05-04). Tester reads this
> along with the row before kicking off `confirm-phase --phase 04-v2`.

---

## 1. Charter

**Supersession trigger: expansion** (PHASE_MAP §1 amended in this
phase to extend supersession-policy coverage from regression-only to
"regression OR additive scope expansion").

Goal: ship `HyperEdgeType` (n-ary edge type vocabulary) + required
`HyperEdge.type_name` + cumulative state-file migration v=2→v=3, so
Phase 05b's `MetaHyperEdgeType` has a parent precedent for the
metagraph-scoped schema vocabulary. Symmetric typed-hyperedge surface
across L1.

**Out of scope** (carry-forwards untouched):
- ADR-0130 graph-level property bag → Phase 05/10.
- ADR-0133 soft-delete → Phase 10.
- ADR-0127 OCC `_version` → Phase 07.
- Phase 04 §7 deferrals (M-04 through R-04) — none target 04-v2.
- Q13 IntergraphEdge — Phase 05b.
- ADR-0117 status flip — Phase 05a.

---

## 2. Scope adjudications (decided across rounds 0-7 + 5 adversarial)

| Round | Lock | Decision |
|---|---|---|
| 0 | MC-2 | Override the "drop MetaHyperEdgeType correction" — ship symmetric typed-hyperedge surface; patch Phase 04 with HyperEdgeType. |
| 0 | HET-1 | `allowed_member_types: list[str]` only; no cardinality / per-position constraints. Mirrors `EdgeType` simplicity. |
| 0 | MIG-1 | Graph state-file v=2 → v=3 one-way migration (mirror of Phase 04's v=1 → v=2). |
| 0 | SS-1 | Schema state-file v=1 → v=2 one-way migration. |
| 0 | PA-1 | Amend ADR-0017 in place; no new ADR-0150. |
| 0 | CASC-1 | Strictly sequential cascade 04-v2 → 05a → 05b. |
| 1 | SENT-1 | Sentinel literal `"UNSPECIFIED"` (uppercase; satisfies cypher rel-type regex per ADR-0021). Adversarial round 1 surfaced the regex conflict with the original `_unspecified` candidate. |
| 1 | UHT-1 | Ship `mindsos graph update-hyperedge-type` legacy-migration recovery CLI. Asymmetric — Edge / Node `type_name` remain immutable. |
| 2 | VERSTR-1 | Python version literal `0.0.0+phase04.v2` (PEP 440 local version with period separator). |
| 3 | WARN-2 | Empty-strict warning condition unchanged from Phase 04 (warn iff zero NodeTypes); does NOT extend to HyperEdgeType emptiness. Self-correction of round-7 lock that would have regressed Phase 04 condition. |
| 4 | AME-1 | Empty `allowed_member_types: []` permitted; mirrors EdgeType precedent. |
| 5 | TEXT-1 | Re-draft ADR-0017 amendment text to incorporate SENT-1 / AME-1 / UHT-1 / ADR-0021 cross-reference. Self-correction of approved text from round 7. |
| — | TRIG-1 | Supersession trigger recorded free-form in `tester_notes`; no new schema field. |

---

## 3. Locked decisions (final, post-iteration — 30-item row appendix)

The full list lives in PHASE_MAP Phase 04-v2 row "Final amendments
(2026-05-04)". Highlights:

| # | Decision |
|---|---|
| 1 | MC-2 — HyperEdgeType ships in 04-v2. |
| 2 | HET-1 — `allowed_member_types: list[str]` only. |
| 3 | MIG-1 — Graph state-file v=2 → v=3 one-way migration. |
| 4 | SS-1 — Schema state-file v=1 → v=2 one-way migration. |
| 5 | PA-1 — ADR-0017 amended in place; text in row appendix. |
| 6 | CASC-1 — Strict sequential cascade. |
| 7 | SENT-1 — Sentinel `"UNSPECIFIED"` (uppercase). |
| 8 | UHT-1 — `update-hyperedge-type` ships in 04-v2 (asymmetric). |
| 9 | WARN-2 — Empty-strict warning unchanged from Phase 04. |
| 10 | AME-1 — Empty `allowed_member_types: []` permitted. |
| 11 | VERSTR-1 — `0.0.0+phase04.v2`. |
| 12 | TRIG-1 — Free-form supersession trigger in `tester_notes`. |
| 13 | SUPER-§1-EXT — PHASE_MAP §1 supersession-policy extends to expansion. |
| 14 | Eager attach validation order: Node → Edge → HyperEdge. |
| 15 | `_validate=False` rehydration extends to `add_hyperedge`. |
| 16 | JSON-then-string `--prop k=v` parsing inherited. |
| 17 | `set-prop` 3-way mutex `--node-id | --edge-id | --hyperedge-id`. |
| 18 | UHT-1 JSON output: `{previous_type_name, new_type_name, hyperedge_id}`. |
| 19 | Idempotent `update-hyperedge-type` writes file (timestamp updates). |
| 20 | Pre-implementation audit of Phase 04 test_state files for hard-coded version constants. |
| 21 | `mindsos graph list` / `schema list` continue to bypass strict version check. |
| 22 | Image tags `mindsos:phase04-v2-{prod,test}`; `_COMPOSE_IMAGE_RE` regex extension. |
| 23 | `requirements.{in,txt}` unchanged (stdlib-only). |
| 24 | No carry-forward closures (Phase 04 §7 deferrals untouched). |
| 25 | Phase 04 GitHub Release body unchanged; tarball asset replaced by 1-line placeholder. |
| 26 | `PHASE_04_CONFIRMED.md` untouched; v2 ships sibling `PHASE_04_v2_CONFIRMED.md`. |
| 27 | `tests/_shared/sentinel_paths.py` unchanged. |
| 28 | `mkdocs.yml` nav unchanged. |
| 29 | `docs/dev/release.md` etc. unchanged in 04-v2 (DOCREL-2 defer). |
| 30 | `confirmation_docs/_template*.md` unchanged. |

---

## 4. Bug ledger

No production bugs surfaced. The 5-round adversarial pass closed two
design-time issues before code:

| ID | Issue | Resolution |
|---|---|---|
| **D-04-v2** | Original sentinel `"_unspecified"` (lowercase) failed ADR-0021's cypher rel-type regex; `Graph.add_hyperedge` rehydration would have crashed at `__post_init__`. | SENT-1 lock: change sentinel literal to `"UNSPECIFIED"` (uppercase) — satisfies the regex and doubles as a tester-declarable HyperEdgeType for the "escape hatch" pattern. |
| **D-04-v2-text** | Approved ADR-0017 amendment text from round 7 referenced `"_unspecified"` and didn't mention AME-1 / UHT-1 / ADR-0021 cross-reference; text would have shipped contradicting other locks. | TEXT-1 re-draft incorporated all five locks. |

---

## 5. Files added / modified

### Added (Phase 04-v2)

```
tests/phase_04_v2/__init__.py
tests/phase_04_v2/conftest.py
tests/phase_04_v2/test_hyperedge_type.py
tests/phase_04_v2/test_schema_add_hyperedge_type.py
tests/phase_04_v2/test_graph_add_hyperedge_type.py
tests/phase_04_v2/test_state_v3_round_trip.py
tests/phase_04_v2/test_legacy_v1_v2_migration.py
tests/phase_04_v2/test_sentinel_unspecified.py
tests/phase_04_v2/test_update_hyperedge_type.py
tests/phase_04_v2/test_attach_schema_hyperedge_eager.py
tests/phase_04_v2/test_set_prop_hyperedge.py
confirmation_docs/PHASE_04_v2_IMPLEMENTATION_LOG.md   <- this file
```

### Modified

```
confirmation_docs/PHASE_MAP.md   — Phase 04 row marked Superseded; Phase 04-v2 row appended;
                                   §1 supersession-policy amendment.
mindsos_cli/__init__.py          — version 0.0.0+phase04 → 0.0.0+phase04.v2; docstring updated.
mindsos_cli/manifest.toml        — phase 04 → 04-v2; version bumped.
pyproject.toml                   — version + description bumped.
docker-compose.yml               — image tags phase04 → phase04-v2 (prod + test).
Dockerfile                       — comment lines updated for HyperEdgeType + sentinel-paths note.
mindsos_cli/state.py             — GRAPH_STATE_VERSION 2 → 3; SCHEMA_STATE_VERSION 1 → 2;
                                   docstring rewritten for cumulative migration semantics.
mindsos_cli/commands/doctor.py   — _COMPOSE_IMAGE_RE regex extends to recognize phaseNN-vM-stage.
mindsos_cli/commands/confirm_phase.py — _init_notes regex tolerates letter / v-suffix.
mindsos_cli/commands/schema.py   — add-hyperedge-type subcommand;
                                   _schema_to_state writes v=2 with hyperedge_types map;
                                   _state_to_schema reads v=1 (empty-list default);
                                   inspect_cmd JSON includes hyperedge_types;
                                   list_schemas counts include hyperedge_types.
mindsos_cli/commands/graph.py    — add-hyperedge --type required + cypher regex;
                                   update-hyperedge-type subcommand (UHT-1);
                                   set-prop 3-way mutex with --hyperedge-id;
                                   _graph_to_state writes v=3 (hyperedge entry includes type_name);
                                   _state_to_graph populates UNSPECIFIED for legacy hyperedges;
                                   eager attach validation extends to hyperedges;
                                   list-hyperedges JSON adds type_name.
mindsos_core/__init__.py         — exports HyperEdgeType; cumulative ~27. Version bumped.
mindsos_core/schema/__init__.py  — re-exports HyperEdgeType.
mindsos_core/schema/types.py     — HyperEdgeType frozen dataclass added.
mindsos_core/schema/schema.py    — _hyperedge_types map; add_hyperedge_type;
                                   require_hyperedge_type; validate_hyperedge;
                                   validate_hyperedge_properties.
mindsos_core/models/edge.py      — HyperEdge.type_name: str (required);
                                   cypher rel-type validation in __post_init__.
mindsos_core/models/graph.py     — add_hyperedge signature gains required type_name;
                                   _validated_hyperedge_properties helper;
                                   update_hyperedge_properties added (no _version bump);
                                   update_hyperedge_type added (UHT-1).
docs/usage/core/schema.md        — HyperEdgeType section + Migration v=2→v=3 + escape-hatch
                                   pattern + UHT-1 recovery + asymmetry note.
docs/api/core/types.md           — HyperEdgeType API.
docs/api/core/hyperedge.md       — type_name field + UHT-1 path + asymmetry note.
docs/api/core/schema.md          — add_hyperedge_type / require_hyperedge_type /
                                   validate_hyperedge / validate_hyperedge_properties.
docs/changelog/CHANGELOG.md      — Phase 04-v2 entry.
tests/phase_03/test_graph_add_hyperedge.py — pass --type to all add-hyperedge calls;
                                   add 2 new tests for missing-type / invalid-cypher-type.
tests/phase_03/test_graph_state_persistence.py — pass --type to all add-hyperedge calls.
tests/phase_04/test_state.py     — version constants 3 / 2 (was 2 / 1); v=3 round-trip;
                                   v=4 future-version refused.
tests/phase_04/test_legacy_compat.py — assertion uses state_mod.GRAPH_STATE_VERSION dynamically.
tests/phase_04/test_graph_detach_schema.py — same dynamic-constant pattern.
tests/unit/test_graph.py         — pass type_name to all add_hyperedge calls.
```

`requirements.in` / `requirements.txt` / `requirements-test.txt` —
**unchanged** (Phase 04-v2 is stdlib-only — `json`, `os`, `pathlib`,
`re`, `enum`, `dataclasses`).

---

## 6. Tests added / count delta

**Phase 04-v2 added:** 9 test files in `tests/phase_04_v2/` totalling
30 tests:
- `test_hyperedge_type.py` (3)
- `test_schema_add_hyperedge_type.py` (5)
- `test_graph_add_hyperedge_type.py` (3)
- `test_state_v3_round_trip.py` (3)
- `test_legacy_v1_v2_migration.py` (4)
- `test_sentinel_unspecified.py` (1)
- `test_update_hyperedge_type.py` (5)
- `test_attach_schema_hyperedge_eager.py` (3)
- `test_set_prop_hyperedge.py` (3)

Plus minor edits to Phase 03 / Phase 04 / unit tests for the new
`type_name` requirement (2 new Phase 03 tests for missing-type +
invalid-cypher-type guarding the breaking change).

**Sandbox cumulative result (Mac, Python 3.10):**

* **372 passed + 41 failed (subprocess CLI on 3.10) + 1 skipped.**
* The 41 failures are documented Phase 02/03/04 sandbox quirks
  (Python 3.10 vs 3.12 + tomllib unavailable). All pass in-container.

**In-container expected (Python 3.12):** **≈ 409 passed + 2 skipped.**
The 2 skips are the existing `test_mkdocs_buildable.py` (mkdocs not in
test image) + `test_restore_node_registers_provided_id` (Phase 08
deferral).

**Tester records the post-collection actual count** in
`PHASE_04_v2_CONFIRMED.md` `tester_notes`.

---

## 7. Residual concerns (deferred to Phase 05a+)

Inherited from Phase 01-04 deferrals (carry-forward; none target
04-v2):

| ID | Issue | Plan |
|---|---|---|
| **η, H, D, J-02, K-02, L-03, M-04, N-04, O-04, P-04, Q-04, R-04** | All Phase 04 §7 carry-forwards. | Untouched in 04-v2. |
| **Q13** | IntergraphEdge primitive. | Phase 05b ships. |

New deferrals introduced in Phase 04-v2:

| ID | Issue | Plan |
|---|---|---|
| **A-04-v2** | UHT-1 asymmetry — only HyperEdge.type_name is post-create mutable. Edge / Node remain immutable. | Documented; tester accepts. May be revisited if Phase 05a/05b surface a similar legacy-migration concern for MetaEdge / IntergraphEdge type_name. |
| **B-04-v2** | Cumulative migration v=1 ∪ v=2 → v=3 jumps directly (no stepwise). Tester running Phase 04-v2 binary on a Phase 03 v=1 file upgrades to v=3 in one step. | Documented in Migration section of `docs/usage/core/schema.md`. |
| **C-04-v2** | UNSPECIFIED-sentinel hyperedge under strict mode requires either UHT-1 update OR escape-hatch HyperEdgeType OR recreate. No CLI to delete a single hyperedge in Phase 04-v2 (parity with Phase 04 — `remove_hyperedge` Python API exists but no CLI). | Documented; recreate via `mindsos graph reset` is the heaviest hammer. |
| **D-04-v2** | The `update_hyperedge_properties` Python API doesn't bump `_version` (Phase 07 OCC owns). | Acknowledged — same M-04 / O-04 / ADR-0127 trajectory. |

---

## 8. Tester checklist

(See full Sections A-J ~50 numbered steps in this file's §8 — kept
inline for tester ergonomics.)

### Section A — Branch + version-bump verification [Mac]

1. **[Mac]** Pull main, branch off `origin/main`:
   ```sh
   git fetch origin
   git checkout main
   git pull
   git checkout -b phase-04-v2 origin/main
   ```
   Expected: branch created.

2. **[Mac]** Verify version strings aligned:
   ```sh
   grep -n "version\|phase" mindsos_cli/manifest.toml pyproject.toml mindsos_cli/__init__.py
   ```
   Expected: all three show `0.0.0+phase04.v2`; manifest's `[mindsos] phase = "04-v2"`.

3. **[Mac]** Verify compose image tags:
   ```sh
   grep "image: mindsos:" docker-compose.yml
   ```
   Expected: both lines show `mindsos:phase04-v2-prod` / `mindsos:phase04-v2-test`.

4. **[Mac]** Verify Dockerfile comments updated:
   ```sh
   grep -n "Phase 04-v2" Dockerfile
   ```
   Expected: 2+ COMMENT lines mention Phase 04-v2.

5. **[Mac]** Commit + push.

### Section B — Linux build + container tests

6. **[Linux]** Pull, checkout, build:
   ```sh
   git fetch origin
   git checkout phase-04-v2
   git pull
   docker compose build mindsos mindsos-test
   ```
   Expected: `mindsos:phase04-v2-prod` and `mindsos:phase04-v2-test` images built.

7. **[Linux]** Bring up FalkorDB:
   ```sh
   docker compose up -d falkordb
   ```
   Expected: falkordb healthy.

8. **[Linux]** Run cumulative tests in-container (canonical pass criterion):
   ```sh
   docker compose run --rm mindsos-test pytest tests/ -v
   ```
   Expected: **≈ 409 passed + 2 skipped** (1 mkdocs, 1 `_restore_node`).
   Confirm exact count from the pytest summary; record in
   `PHASE_04_v2_CONFIRMED.md` `tester_notes`.

### Section C — Doctor self-test

9. **[Linux]** Doctor + self-test:
   ```sh
   docker compose run --rm mindsos doctor
   docker compose run --rm mindsos doctor --self-test
   ```
   Expected: both exit 0; pin reports include `phase = "04-v2"`,
   `version = "0.0.0+phase04.v2"`.

10. **[Linux]** `confirm-phase` preflight smoke:
    ```sh
    mindsos confirm-phase --init-notes 04-v2
    ```
    Expected: `notes-phase-04-v2.md` template written; preflight succeeds.

### Section D — HyperEdgeType happy path

11. **[Linux]** Schema with HyperEdgeType:
    ```sh
    docker compose run --rm --entrypoint /bin/sh mindsos -c '
      mindsos schema create --name people-schema --strict &&
      mindsos schema add-node-type --schema people-schema --type-name Person &&
      mindsos schema add-node-type --schema people-schema --type-name School &&
      mindsos schema add-hyperedge-type --schema people-schema \
          --type-name ATTENDS --allowed-member Person --allowed-member School &&
      mindsos schema inspect --name people-schema --json
    '
    ```
    Expected: inspect JSON shows `hyperedge_types` array with one entry.

12. **[Linux]** Use HyperEdgeType in a graph:
    ```sh
    docker compose run --rm --entrypoint /bin/sh mindsos -c '
      mindsos graph create --name folks --schema people-schema &&
      mindsos graph add-node Alice --name folks --type Person --node-id alice &&
      mindsos graph add-node Acme --name folks --type School --node-id acme &&
      mindsos graph add-hyperedge --name folks --type ATTENDS \
          --member alice --member acme --json
    '
    ```
    Expected: hyperedge added; JSON shows `type_name: "ATTENDS"`.

13. **[Linux]** Wrong member type rejected (strict):
    ```sh
    docker compose run --rm --entrypoint /bin/sh mindsos -c '
      mindsos schema add-node-type --schema people-schema --type-name Cat &&
      mindsos graph add-node Whiskers --name folks --type Cat --node-id whiskers &&
      mindsos graph add-hyperedge --name folks --type ATTENDS --member alice --member whiskers
    '
    ```
    Expected: exit 1; `UnknownTypeError: HyperEdge type 'ATTENDS' does not permit member type 'Cat'`.

### Section E — AME-1 empty allowed_member_types

14. **[Linux]** Empty allowed-member permitted:
    ```sh
    mindsos schema add-hyperedge-type --schema people-schema --type-name OPEN --json
    ```
    Expected: exit 0; JSON `allowed_member_types: []`.

15. **[Linux]** Under non-strict, OPEN type accepts any member.
16. **[Linux]** Under strict, OPEN type rejects all (no allowed members).

### Section F — UHT-1: update-hyperedge-type recovery

17. **[Linux]** Hand-write a v=2 graph file with hyperedge missing type_name:
    ```sh
    cat > /tmp/legacy.json <<'EOF'
    {"_state_version": 2, "graph_id": "00000000-0000-4000-8000-200000000001",
     "name": "legacy", "role": null, "schema_name": null,
     "nodes": [{"node_id": "n-a", "value": "A", "type_name": "T", "properties": {}}],
     "edges": [],
     "hyperedges": [{"edge_id": "he-1", "member_ids": ["n-a"], "label": null, "properties": {}}]}
    EOF
    cp /tmp/legacy.json $HOME/.mindsos/graph-legacy.json
    ```

18. **[Linux]** Inspect — sentinel populated:
    ```sh
    mindsos graph list-hyperedges --name legacy --json
    ```
    Expected: hyperedge JSON shows `type_name: "UNSPECIFIED"`.

19. **[Linux]** Update to a real type:
    ```sh
    mindsos graph update-hyperedge-type --name legacy --hyperedge-id he-1 --type SOLO --json
    ```
    Expected: JSON `{previous_type_name: "UNSPECIFIED", new_type_name: "SOLO", hyperedge_id: "he-1"}`.

20. **[Linux]** Idempotent update:
    ```sh
    mindsos graph update-hyperedge-type --name legacy --hyperedge-id he-1 --type SOLO
    ```
    Expected: exit 0; "ok: updated hyperedge id=he-1 type 'SOLO' -> 'SOLO'".

21. **[Linux]** Invalid cypher type:
    ```sh
    mindsos graph update-hyperedge-type --name legacy --hyperedge-id he-1 --type lower-case
    ```
    Expected: exit 1; `CypherError`.

### Section G — Migration v=2 → v=3

22. **[Linux]** First mutation upgrades file:
    ```sh
    mindsos graph add-node Bob --name legacy --type T --node-id n-b
    cat $HOME/.mindsos/graph-legacy.json | python3 -c "import json,sys; print(json.load(sys.stdin)['_state_version'])"
    ```
    Expected: `3`.

23. **[Linux]** v=4 future-version rejected:
    ```sh
    echo '{"_state_version": 4, "name": "future"}' > $HOME/.mindsos/graph-future.json
    mindsos graph inspect --name future
    ```
    Expected: exit 1; `this CLI supports v3`.

### Section H — set-prop --hyperedge-id mutex

24. **[Linux]** Update hyperedge property:
    ```sh
    mindsos graph add-hyperedge --name legacy --type SOLO --member n-a --hyperedge-id he-2 --prop year=2024
    mindsos graph set-prop --name legacy --hyperedge-id he-2 --prop since=2025 --json
    ```
    Expected: JSON `{kind: "hyperedge", properties: {year: 2024, since: 2025}}`.

25. **[Linux]** Mutex violation (two flags):
    ```sh
    mindsos graph set-prop --name legacy --node-id n-a --hyperedge-id he-2 --prop k=v
    ```
    Expected: exit 2; "Specify exactly one of --node-id, --edge-id, or --hyperedge-id."

26. **[Linux]** --replace preserves ref:* on hyperedge:
    ```sh
    mindsos graph add-hyperedge --name legacy --type SOLO --member n-a --hyperedge-id he-3 \
        --prop year=2024 --prop ref:source=alpha-uuid
    mindsos graph set-prop --name legacy --hyperedge-id he-3 --replace --prop score=99 --json
    ```
    Expected: JSON properties = `{ref:source: "alpha-uuid", score: 99}` (year DROPPED, ref:* preserved).

### Section I — Eager attach + escape-hatch

27. **[Linux]** Strict schema with no HyperEdgeType refuses on attach:
    ```sh
    mindsos schema create --name s2 --strict
    mindsos schema add-node-type --schema s2 --type-name T
    mindsos graph attach-schema --name legacy --schema s2
    ```
    Expected: exit 1; "hyperedge he-1: UnknownTypeError: ..." or similar.

28. **[Linux]** Escape-hatch — declare UNSPECIFIED HyperEdgeType:
    ```sh
    mindsos schema add-hyperedge-type --schema s2 --type-name UNSPECIFIED
    ```
    Expected: exit 0; AME-1 empty allowed_member_types permitted.

29. **[Linux]** Re-attach now succeeds (assuming all hyperedges have UNSPECIFIED type, OR via update-hyperedge-type to SOLO + add SOLO HyperEdgeType to schema):
    ```sh
    mindsos schema add-hyperedge-type --schema s2 --type-name SOLO
    mindsos graph attach-schema --name legacy --schema s2
    ```
    Expected: exit 0.

### Section J — Confirm phase

30. **[Linux]** Run `confirm-phase`:
    ```sh
    mindsos confirm-phase --phase 04-v2 --notes-file notes-phase-04-v2.md
    ```
    Expected: writes `confirmation_docs/PHASE_04_v2_CONFIRMED.md`.

31. **[Linux]** Edit `tester_notes` field:
    Add free-form supersession trigger note (TRIG-1):
    > "Supersession trigger: additive scope expansion (HyperEdgeType, MC-2 lock 2026-05-04 — round 7 + 5 adversarial rounds).
    > Cumulative pytest: <actual N> passed + 2 skipped."

32. **[Linux]** Verify confirmation doc:
    ```sh
    ls -la confirmation_docs/PHASE_04_v2_CONFIRMED.md
    ```
    Expected: file exists, non-empty.

33. **[Linux]** Commit + push branch.

34. **[Linux]** Tag + push (after squash-merge on Mac):
    ```sh
    git tag phase-04-v2-confirmed <squash-merge-sha>
    git push origin phase-04-v2-confirmed
    ```
    Expected: GitHub Release pipeline triggers.

35. **[Linux]** Verify tarball + supersession of phase-04 asset:
    ```sh
    gh release view phase-04-v2-confirmed --json assets
    gh release view phase-04-confirmed --json assets
    ```
    Expected: `phase-04-v2-confirmed` release has `mindsos-phase04-v2.tar.gz`;
    `phase-04-confirmed` release's tarball asset replaced by 1-line "source-rebuild required" placeholder per (NN, vM) eviction policy.

### Failure paths

36. **[Linux]** Doctor self-test catches version-string drift:
    Edit `mindsos_cli/__init__.py` to mismatch (e.g. `__version__ = "0.0.0+phase04.v3"`):
    ```sh
    docker compose run --rm mindsos doctor --self-test
    ```
    Expected: exit non-zero; "init=... manifest=..." mismatch reported.
    Restore version string after testing.

37. **[Linux]** Doctor self-test catches compose-image tag drift:
    Edit `docker-compose.yml` to reference `mindsos:phase04-prod`:
    ```sh
    docker compose run --rm mindsos doctor --self-test
    ```
    Expected: exit non-zero; "compose image-tag drift" reported.
    Restore image tag after testing.

38. **[Linux]** Phase 03 binary loading v=3 file (regression test):
    Install Phase 03 wheel (or check out `phase-03-confirmed`); attempt to read a v=3 file:
    Expected: exit non-zero; "this CLI supports v1" message.

### Recovery procedures (documented)

39. **Rollback to Phase 04:** `rm -rf ~/.mindsos/graph-*.json && rm -rf ~/.mindsos/schema-*.json`. Or hand-edit JSON downgrade.

40. **Rollback to Phase 03:** Layer v=2 → v=1 downgrade on top of the above.

---

## 9. Decision references

* **PHASE_MAP** Phase 04-v2 row §5 — full final-amendments appendix (~30 numbered items).
* **ADR-0017** — amended in place per PA-1; text in PHASE_MAP row appendix.
* **ADR-0021** — Cypher rel-type validation, applies to `HyperEdge.type_name` per Phase 04-v2 lock.
* **ADR-0014** — Layer boundary; HyperEdgeType is a vocabulary primitive, no domain logic added.
* **ADR-0127** — `_version` OCC; Phase 04-v2 still does NOT bump `_version` on `update_*` (Phase 07 owns).

---

## 10. State at end of session

Phase 04-v2 design pre-locks complete. Implementation complete in slim
repo. Sandbox tests: 372 passed + 41 sandbox CLI quirks + 1 skipped.
In-container projection: ≈ 409 + 2 skipped.

**Awaiting tester run on Linux box to produce
`confirmation_docs/PHASE_04_v2_CONFIRMED.md`.**

Cascade: 04-v2 → **05a** (Metagraph port, CASC-1 lock) → 05b
(IntergraphEdge + MetagraphSchema). 05a row refinement starts only
AFTER 04-v2 confirmed.
