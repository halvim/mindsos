#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
ARC_DEMO="$REPO/projects/arc_demo"
ARC1="$ARC_DEMO/intelligence_demo/arc1"
export PYTHONPATH="$REPO:$ARC_DEMO${PYTHONPATH:+:$PYTHONPATH}"

help_top() {
  cat <<'EOF'
arc — ARC-1 capacity demo

usage: ./arc <command> [args]   ·   ./arc <command> --help

commands:
  start [port]                          build the spike + serve the debug UI (default 8042)
  solve <task#|id> <step 1-10>          run the solver pipeline up to <step> (resumable)
  evaluate <comparator> [task#|id|all]  probe a comparator (lists demands if no task given)

comparators: moved recolored rotated reflected touching inside
EOF
}

help_start() {
  cat <<'EOF'
arc start [port] — build the spike and serve the debug UI

  Rebuilds arc_debug_data.js over all 400 train tasks (runs the gate checks),
  then serves the Search / Gates / Map UI from a local web server.

  port    TCP port for the server (default 8042)

examples:
  ./arc start                  → http://localhost:8042/arc_debug.html
  ./arc start 9000             → http://localhost:9000/arc_debug.html
EOF
}

help_solve() {
  cat <<'EOF'
arc solve <task#|task_id> <step> — run the solver pipeline up to <step>
arc solve --phases — list every phase with a description (no task run)
arc solve --inferences — list the declared inference edges (wired / requires / display)

  task    1-based index into the 400 sorted train tasks, or a task id (e.g. 05f2a901)
  step    1–13; phases 1..<step> are recomputed in-memory on every run (no cache)

  steps:  1 input+perceive · 2 profile · 3 subdivision · 4 component re-comparison ·
          5 comparators hypothesis · 6 task pattern · 7 background+state-change ·
          8 roles · 9 persistence · 10 selectors · 11 rule · 12 verify ·
          13 apply → ANSWER

examples:
  ./arc solve --phases         list the 13 phases + descriptions
  ./arc solve --inferences     list the declared inference edges
  ./arc solve 8 3              run steps 1–3 for task #8
  ./arc solve 8 13             full pipeline → ANSWER grid
  ./arc solve 05f2a901 13      same task, by id
EOF
}

help_evaluate() {
  cat <<'EOF'
arc evaluate <comparator> [task#|task_id|all] — probe a comparator capacity

  comparator   one of: moved recolored rotated reflected touching inside
  (no task)    list the comparator's demands + implication parents
  task#|id     apply to one task → TRUE/FALSE (+ unmet demands / discrepancy)
  all          apply to every task → capacities.json + capacities_discrepancies.json

  A comparator is demand-gated (its required profilers must fire) and the result
  is cross-checked against the Search token; a mismatch is flagged + stored.

examples:
  ./arc evaluate rotated           list demands (same_cell_count, same_bbox_area)
  ./arc evaluate inside 8          apply to task #8
  ./arc evaluate touching all      bulk run over all 400 tasks
EOF
}

cmd="${1:-}"
shift || true

case "$cmd" in
  ""|-h|--help|help)
    help_top
    ;;
  start)
    case "${1:-}" in -h|--help) help_start; exit 0;; esac
    PORT="${1:-8042}"
    echo "▶ building spike (perceive + profile + gates over 400 tasks) ..."
    "$ARC_DEMO/run_spike"
    echo
    echo "▶ arc system ready"
    echo "    debug UI   http://localhost:${PORT}/arc_debug.html   (search · gates · map)"
    echo "    solve      ./arc solve <task#|id> <step 1-13>"
    echo "    evaluate   ./arc evaluate <comparator> [task#|id|all]"
    echo
    echo "  (Ctrl-C to stop the server)"
    echo
    cd "$ARC1/spike"
    exec python3 -m http.server "$PORT"
    ;;
  solve)
    case "${1:-}" in ""|-h|--help) help_solve; exit 0;; esac
    exec python3 "$ARC1/solve/runner.py" "$@"
    ;;
  evaluate)
    case "${1:-}" in ""|-h|--help) help_evaluate; exit 0;; esac
    exec python3 "$ARC1/solve/evaluate.py" "$@"
    ;;
  *)
    echo "unknown command: $cmd" >&2
    echo >&2
    help_top >&2
    exit 1
    ;;
esac
