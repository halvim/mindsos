# Phase 05c — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L1 IntergraphHyperEdge (n-ary, NOT 1-1, ADR-0148 amended) + IntergraphHyperEdgeType + replace-only update verb; 4 new `mindsos metagraph` subcommands (add/remove/update/list-intergraph-hyperedge) + 1 new `mindsos metagraph-schema` subcommand (add-intergraph-hyperedge-type) + 5-way set-prop mutex extension; metagraph state-file v=2→v=3 cumulative one-way migration (intergraph_hyperedges); metagraph-schema state-file v=1→v=2 cumulative one-way migration (intergraph_hyperedge_types); P17-A precheck extended; P12-A schema-mutation footgun; 05b CHANGELOG amendment for P13-B retreat lands on this branch

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Row locked across 4 reanalysis rounds in design chat; 20 numbered
pushbacks accepted (P1-B / P2-refined / P3 / P4-A / P5-refined / P6-A
/ P7-A / P8-A / P9-A / P10-C / P11→P13-B / P12-A / P14-A / P15-A /
P16-A / P17-A / P18-A / P19-A / P20-A + smaller-items folded). 2
future-work entries filed at `_source_backup/root/mindsos_future_plans.md`
under "Intergraph primitive structural mutation":

* "Discoverable endpoint-update verb for IntergraphEdge" (P11→P13-B).
* "In-place hyperedge→edge downgrade with edge_id stability" (P19-A).

Implementation chat added 5 numbered pushbacks (P26-P30) + 2
follow-ups (P31-P32) per `confirmation_docs/PHASE_05c_IMPLEMENTATION_LOG.md`
§3.

---

### Per-phase workflow steps (every step `[Mac]` or `[Linux]` tagged)

#### A. [Mac] Push the branch.

`git push origin phase-05c` → expect remote tip = local HEAD.

#### B. [Linux] Pull the branch.

`cd halvim_mindsos && git fetch origin && git checkout phase-05c && git pull origin phase-05c` → expect HEAD at the latest 05c commit.

#### C. [Linux] Refresh host venv.

`pip install -e .` (in `halvim_mindsos/.venv`) → expect "Successfully installed mindsos-cli-0.0.0+phase05c".

#### D. [Linux] Doctor preflight.

`FALKORDB_HOST=localhost mindsos doctor --self-test --static-only` → expect exit 0.

#### E. [Linux] REBUILD test image.

`docker compose build mindsos-test` → expect successful image rebuild. *(B-05b-T2 lesson: stale image breaks tests after pulling test fixes.)*

#### F. [Linux] Run cumulative pytest.

`docker compose run --rm mindsos-test pytest tests/` → expect ≥ 740 + 2 skipped baseline + 05c additions; record actual count below.

#### G. [Linux] Manual exploration — fixture build.

`mindsos graph create --name word --role word` → expect exit 0.
`mindsos graph add-node cat --name word --node-id cat --type Word` → expect exit 0; node_id="cat".
`mindsos graph create --name letter --role letter` → expect exit 0.
`mindsos graph add-node c --name letter --node-id c --type Letter` → expect exit 0.
`mindsos graph add-node a --name letter --node-id a --type Letter` → expect exit 0.
`mindsos graph add-node t --name letter --node-id t --type Letter` → expect exit 0.
`mindsos metagraph create --name mg` → expect exit 0.
`mindsos metagraph add-graph --name mg --graph word` → expect exit 0.
`mindsos metagraph add-graph --name mg --graph letter` → expect exit 0.

#### H. [Linux] Manual — IntergraphHyperEdgeType registration.

`mindsos metagraph-schema create --name ms --strict` → expect exit 0; JSON output includes `intergraph_hyperedge_types: []` (P05c add).

`mindsos metagraph-schema add-intergraph-hyperedge-type --schema ms --type-name COMPOSED_OF --allowed-anchor-type Word --allowed-member-type Letter --allowed-anchor-graph word --allowed-member-graph letter --json` → expect exit 0; `ordered: true` (P18-A default).

`mindsos metagraph-schema inspect --name ms --json` → expect `intergraph_hyperedge_types` array contains COMPOSED_OF entry; counts include `intergraph_hyperedge_types: 1`.

#### I. [Linux] Manual — attach + happy-path n-ary add.

`mindsos metagraph attach-schema --name mg --schema ms --json` → expect exit 0; eager validation passes (no hyperedges yet).

`mindsos metagraph add-intergraph-hyperedge --name mg --anchor-graph word --anchor-node cat --member-graph letter --member-node c --member-graph letter --member-node a --member-graph letter --member-node t --type COMPOSED_OF --compositional --json` → expect exit 0; JSON shows `compositional: true` + 1 anchor + 3 members + auto-minted `intergraph_hyperedge_id`.

`mindsos metagraph inspect --name mg --json` → expect `counts.intergraph_hyperedges: 1` (P05c shape extension).

#### J. [Linux] Manual — paired-flags mismatch refusal (P4-A).

`mindsos metagraph add-intergraph-hyperedge --name mg --anchor-graph word --anchor-graph word --anchor-node cat --member-graph letter --member-node c --member-graph letter --member-node a --type T --json` → expect exit 2; stderr contains "P4-A paired-flags mismatch" + "anchor".

#### K. [Linux] Manual — P8-A compositional+ordered=False refusal.

`mindsos metagraph-schema add-intergraph-hyperedge-type --schema ms --type-name UNORDERED_COMP --unordered --json` → expect exit 0; stderr warns schema attached to mg (P12-A); JSON `ordered: false`.

`mindsos metagraph attach-schema --name mg --schema ms --json` → expect re-validation passes (existing hyperedge still satisfies).

`mindsos metagraph add-intergraph-hyperedge --name mg --anchor-graph word --anchor-node cat --member-graph letter --member-node c --member-graph letter --member-node a --type UNORDERED_COMP --compositional --json` → expect exit 1; stderr "compositional hyperedges require ordered=True" (P8-A).

#### L. [Linux] Manual — P19-A 1-1 collapse refusal.

`mindsos metagraph add-intergraph-hyperedge --name mg --anchor-graph word --anchor-node cat --member-graph letter --member-node c --member-graph letter --member-node a --type COMPOSED_OF --intergraph-hyperedge-id update_test --json` → expect exit 0.

`mindsos metagraph update-intergraph-hyperedge --name mg --intergraph-hyperedge-id update_test --member-graph letter --member-node c --json` → expect exit 1; stderr contains "P19-A".

#### M. [Linux] Manual — P10-C replace-only update happy path.

`mindsos metagraph update-intergraph-hyperedge --name mg --intergraph-hyperedge-id update_test --member-graph letter --member-node c --member-graph letter --member-node a --member-graph letter --member-node t --json` → expect exit 0; JSON `intergraph_hyperedge_id` equals `update_test` (edge_id stable across update); members replaced.

#### N. [Linux] Manual — Compositional cascade (P17-A extended).

`mindsos metagraph remove-graph --name mg --graph word --json` → expect exit 1; stderr contains `CompositionalImmutableError` AND `intergraph_hyperedge` AND `anchor side`. State unchanged.

`mindsos metagraph inspect --name mg --json` → expect `counts.graphs: 2` (state unchanged).

#### O. [Linux] Manual — 5-way set-prop mutex.

`mindsos metagraph set-prop --name mg --on-metagraph --intergraph-hyperedge-id update_test --prop k=v` → expect exit 2; stderr contains "5-way" or "exactly one".

`mindsos metagraph set-prop --name mg --intergraph-hyperedge-id update_test --prop k=v --json` → expect exit 0; JSON `kind: "intergraph_hyperedge"`.

#### P. [Linux] Manual — P31 P13-B workaround on binary primitive.

`mindsos metagraph remove-intergraph-edge --name mg --intergraph-edge-id <some-non-compositional-edge-id>` then `mindsos metagraph add-intergraph-edge --name mg ... --intergraph-edge-id <same-id>` → expect exit 0 on both; `--intergraph-edge-id` override preserves edge_id stability. Permanent regression test at `tests/phase_05c/test_cli_intergraph_hyperedge.py::TestP13BWorkaround` covers this. (Skip this step if no non-compositional binary edge exists; the regression test is sufficient.)

#### Q. [Linux] Cleanup — note v=3 / v=2 state files on disk.

`cat $MINDSOS_STATE_DIR/metagraph-mg.json | head -3` → expect `_state_version: 3` and `intergraph_hyperedges` array present.
`cat $MINDSOS_STATE_DIR/metagraph-schema-ms.json | head -3` → expect `_state_version: 2` and `intergraph_hyperedge_types` array present.

`mindsos metagraph reset --name mg --force --yes` → expect exit 0.
`mindsos metagraph-schema reset --name ms --force --yes` → expect exit 0.
`mindsos graph reset --name word` → expect exit 0.
`mindsos graph reset --name letter` → expect exit 0.

#### R. [Linux] Edit notes file (this file) FIRST, then run confirm-phase.

Edit `notes-phase-05c.md`: replace this block with run results (cumulative test count, any deviations from steps G-Q, hotfix ledger if any, doctor self-test result, host venv Python version).

`mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md` → expect a generated `confirmation_docs/PHASE_05c_CONFIRMED.md` populated with the auto-derived fields + the tester_notes block from this file.

#### S. [Linux] Review the generated confirmation doc.

`cat confirmation_docs/PHASE_05c_CONFIRMED.md` → expect 9 schema fields populated (phase_number, phase_title, git_sha, image_build_hash, falkordb_version, automated_test_summary, tester_notes, timestamp_utc, mkdocs_pages_updated).

#### T. [Mac OR Linux] Commit + push.

`git add confirmation_docs/PHASE_05c_CONFIRMED.md notes-phase-05c.md` → expect both files staged.
`git status` → verify NO untracked files in confirmation_docs/ (Phase 01 §10.1 footgun: untracked confirmation doc gets dropped at squash-merge).
`git commit -m "phase-05c: tester confirmation"` → expect commit.
`git push origin phase-05c` → expect remote updated.

#### U. [Mac OR Linux] Open PR + squash-merge.

GitHub PR `phase-05c` → `main` → squash-merge.

#### V. [Mac, on `main`] Tag from squash-merged commit + push.

`git checkout main && git pull` → expect HEAD at the squash-merged commit.
`git tag phase-05c-confirmed && git push origin phase-05c-confirmed` → CI builds Release with `mindsos-phase05c.tar.gz` + retention prune.

---

### Carry-forward operational lessons (read these first)

* **B-05b-T2 lesson** — rebuild test image after pulling test-side
  fixes. Step E above.
* **Confirm-phase ordering** — edit `notes-phase-05c.md` FIRST, THEN
  run `mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md`.
  The wrapper reads from the notes file. (User caught this reversed
  in 05b — corrected in step R above.)
* **Phase 03 add-node positional value** — `mindsos graph add-node cat
  --name word --node-id cat --type Word` (positional value, not
  `--value cat`). B-05b-T1 carry-forward.
* **`mindsos graph reset` has no `--force` flag** — Phase 03 surface
  takes `--name | --all` only. B-05b-Step15-deviation carry-forward
  (step Q above).

### Tester-result placeholder (fill in after step F)

* Cumulative test count: ___ passed, ___ skipped in-container.
* Sandbox-projected baseline: ≥ 740 + 2 skipped (05b) + 05c additions
  (no projection per `feedback_test_budget_unlimited.md`).
* Hotfix ledger: ___ (or "none").
* Manual deviations from steps G-Q: ___ (or "none").
* Doctor self-test (step D): ___ (exit 0 expected).
* Host venv Python version: ___ (3.12.x expected).

### Pushbacks (during tester run, if any surface)

(One block at end. None expected pre-tester-run.)
