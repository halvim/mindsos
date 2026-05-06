# Phase 05b — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L1 IntergraphEdge (binary) + IntergraphEdgeType + MetagraphSchema container (ADR-0148 first draft; ADR-0117 already Withdrawn in 05a; new metagraph-schema CLI subapp + 5 new metagraph subcommands + 4-way set-prop mutex; metagraph state v=1→v=2; new metagraph-schema-<n>.json v=1)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Tester recipe (Linux box, host venv with Python 3.12):

```sh
cd halvim_mindsos
git pull origin phase-05b
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

# Static doctor pre-flight.
mindsos doctor --self-test --static-only

# Cumulative pytest in-container.
docker compose run --rm mindsos-test pytest tests/

# Manual exploration (see PHASE_05b_IMPLEMENTATION_LOG.md §9 for the
# full recipe walkthrough).
mindsos graph create --name lex --role lexicon
mindsos graph add-node --name lex --node-id n_cat --value cat --type Word
mindsos graph create --name cpt --role concepts
mindsos graph add-node --name cpt --node-id n_concept --value Cat#1 --type Concept
mindsos metagraph create --name mg
mindsos metagraph add-graph --name mg --graph lex
mindsos metagraph add-graph --name mg --graph cpt
mindsos metagraph-schema create --name ms1 --strict
mindsos metagraph-schema add-intergraph-edge-type --schema ms1 \
    --type-name EVOKES \
    --allowed-source-type Word --allowed-target-type Concept \
    --allowed-source-graph lexicon --allowed-target-graph concepts \
    --prop-type weight=float
mindsos metagraph attach-schema --name mg --schema ms1 --json
mindsos metagraph add-intergraph-edge --name mg \
    --source-graph lex --source-node n_cat \
    --target-graph cpt --target-node n_concept \
    --type EVOKES --prop weight=0.5
mindsos metagraph inspect --name mg --json

# Confirm the phase.
mindsos confirm-phase --phase 05b --notes-file notes-phase-05b.md
```

Phase 05b row was locked across 6 reanalysis rounds in the design chat;
34 numbered pushbacks accepted; 4 future-work entries filed at
`_source_backup/root/mindsos_future_plans.md` (Pushbacks 25-B, 31-B,
33-B, 34-B). See `confirmation_docs/PHASE_05b_IMPLEMENTATION_LOG.md` for
the full bug ledger + module change list + forward-compat notes for 05c.

Sandbox-projected cumulative tests in-container: ~660-700 + 2 skipped.
The 2 skips carry forward from 05a baseline:
`tests/test_mkdocs_buildable.py` (mkdocs not in test image) +
`tests/unit/test_graph.py::test_restore_node_registers_provided_id`
(Phase 08 deferral).

CASC-1 strict-sequential cascade: phase-05b confirmed → phase-05c row
refinement begins (IntergraphHyperEdge + IntergraphHyperEdgeType +
MetaEdgeType + MetaHyperEdgeType per Pushback 1-C deferral).
