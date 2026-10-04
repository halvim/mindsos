#!/usr/bin/env bash
# Gate a SHA in a throwaway worktree. LINUX BOX ONLY (all code runs there).
#
# Usage:  tools/gate.sh <sha> [--mutate <file> <sed-expr>] [pytest-path...]
# Default paths: tests/architecture tests/test_adr_status_consistency.py
#
# --mutate applies ONE designated mutation to the clone before the run and
# refuses unless EXACTLY one line changed. The clone is thrown away with the
# run, so a mutation needs no restore and no clone has to outlive a gate.
#
# THREE THINGS THIS LEARNED BY BEING RUN (2026-09-20):
#  * an EXIT TRAP prints an ANSWER line on every path, including an early
#    abort -- a box that prints nothing tells the owner nothing;
#  * the log name carries the RUN, not just the sha: a second run at the same
#    sha used to overwrite the first one's evidence;
#  * a failed worktree removal is REPORTED, never swallowed by `|| true` --
#    two stale gate worktrees is how that was found. The run leaves root-owned
#    files under `<wt>/.mindsos` and the box has NO PASSWORDLESS SUDO, so the
#    DIRECTORY can survive: the registration is pruned either way, and the
#    leftover path is printed as `rm_me=` for one interactive `sudo rm -rf`.
#
# AND THREE MORE (2026-10-03), held by tests/architecture/test_gate_cleans_up.py,
# which RUNS this script:
#  * a GREEN run aborted before cleanup: under `set -euo pipefail` a grep for
#    FAILED lines that matches nothing exits 1. Every green gate left its
#    clone. A search that may find nothing must say so (`failed_lines`);
#  * cleanup lives in the EXIT TRAP, not at the end of the happy path, so an
#    abort after the clone exists removes it too;
#  * logs go in ONE folder, ~/gate-logs/, capped at the newest LOG_CAP, and
#    each ends with its run's ANSWER line -- a lost paste is answered by
#    `tail -1 <log>`, never by a re-run.
set -euo pipefail

LOG_CAP=20

sha="${1:?usage: gate.sh <sha> [--mutate <file> <sed-expr>] [pytest-path...]}"; shift || true
mfile=""; mexpr=""; mutated="none"
if [[ "${1:-}" == "--mutate" ]]; then
  mfile="${2:?--mutate needs a file}"; mexpr="${3:?--mutate needs a sed expression}"
  shift 3
  mutated="${mfile}:unapplied"
fi
paths=("$@")
(( ${#paths[@]} )) || paths=(tests/architecture tests/test_adr_status_consistency.py)

main="${MINDSOS_MAIN:-/home/sanmyaku/mindsos}"
stamp="$(date +%Y%m%d-%H%M%S)-$$"
# A ref may contain "/" (origin/main); a log path may not.
slug="${sha//\//-}"
logdir="${HOME}/gate-logs"
out="${logdir}/gate-${slug}-${stamp}.txt"
wt="${main}-gate-${stamp}"
step="start"; rc=99; tail_line=""; fails=""; inv=""; real_head=""

failed_lines() {
  grep '^FAILED' "$1" || :
}

answer() {
  # Cleanup is VERIFIED, not attempted, and it runs on EVERY exit: `worktree
  # remove` can fail (a file the checkout itself modifies), and swallowing
  # that is how stale worktrees accumulated. Fall back to rm -rf + prune, then
  # report the state that resulted.
  cd "${main}" 2>/dev/null || true
  git worktree remove --force "${wt}" >/dev/null 2>&1 || true
  if [[ -d "${wt}" ]]; then
    rm -rf "${wt}" >/dev/null 2>&1 || true
  fi
  # Prune regardless: a directory that survives root-owned files must not also
  # survive as a registration, or `git worktree list` stops being readable.
  git worktree prune >/dev/null 2>&1 || true

  local gone
  gone="$(test -d "${wt}" && echo n || echo y)"
  local stale
  stale="$(git -C "${main}" worktree list 2>/dev/null | grep -c -- "-gate-" || true)"
  local rm_me="none"
  [[ "${gone}" == "n" ]] && rm_me="${wt}"
  local line
  line="ANSWER gate host=$(hostname -s) step=${step} sha=${real_head:-${sha}} rc=${rc}"
  line+=" result=[${tail_line}] fails=[${fails}] ${inv:-verification: n/a}"
  line+=" mutated=${mutated} log=${out} wt_gone=${gone} registered=${stale} rm_me=${rm_me}"
  if [[ -d "${logdir}" ]]; then
    echo "${line}" >> "${out}" 2>/dev/null || true
    # Newest LOG_CAP survive; this run's log is the newest of them.
    ls -1t "${logdir}"/gate-*.txt 2>/dev/null | tail -n "+$((LOG_CAP + 1))" \
      | while read -r old; do rm -f "${old}" || true; done || true
  fi
  echo "${line}"
}
trap answer EXIT

mkdir -p "${logdir}"; : > "${out}"
step="fetch";     cd "${main}"; git fetch -q origin
step="worktree";  git worktree add -q --detach "${wt}" "${sha}"
cd "${wt}"
if [[ -n "${mfile}" ]]; then
  step="mutate"
  before="$(mktemp)"
  cp "${mfile}" "${before}"
  sed -i -e "${mexpr}" "${mfile}"
  changed="$(diff "${before}" "${mfile}" | grep -c '^<' || true)"
  rm -f "${before}"
  mutated="${mfile}:${changed}"
  [[ "${changed}" == "1" ]]
fi
step="pytest"
set +e
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider -rf "${paths[@]}" >> "${out}" 2>&1
rc=$?
set -e
real_head="$(git rev-parse --short HEAD)"
tail_line="$(tail -1 "${out}")"
fails="$(failed_lines "${out}" | sed 's/.*:://;s/ .*//' | paste -sd, -)"
step="inventory"; inv="$(python3 tools/claim_inventory.py 2>/dev/null | grep -m1 verification || echo 'verification: n/a')"
step="done"
