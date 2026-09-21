#!/usr/bin/env bash
# Gate a SHA in a throwaway worktree. LINUX BOX ONLY (all code runs there).
#
# Usage:  tools/gate.sh <sha> [pytest-path...]
# Default paths: tests/architecture tests/test_adr_status_consistency.py
#
# THREE THINGS THIS LEARNED BY BEING RUN (2026-09-20):
#  * an EXIT TRAP prints an ANSWER line on every path, including an early
#    abort -- a box that prints nothing tells the owner nothing;
#  * the log name carries the RUN, not just the sha: a second run at the same
#    sha used to overwrite the first one's evidence;
#  * a failed worktree removal is REPORTED (wt_gone=n), never swallowed by
#    `|| true` -- two stale gate worktrees is how that was found.
set -euo pipefail

sha="${1:?usage: gate.sh <sha> [pytest-path...]}"; shift || true
paths=("$@")
(( ${#paths[@]} )) || paths=(tests/architecture tests/test_adr_status_consistency.py)

main="${MINDSOS_MAIN:-/home/sanmyaku/mindsos}"
stamp="$(date +%Y%m%d-%H%M%S)-$$"
out="${HOME}/gate-${sha}-${stamp}.txt"
wt="${main}-gate-${stamp}"
step="start"; rc=99; tail_line=""; fails=""; inv=""; real_head=""

answer() {
  local gone="unknown"
  [[ -n "${wt}" ]] && gone="$(test -d "${wt}" && echo n || echo y)"
  local stale
  stale="$(git -C "${main}" worktree list 2>/dev/null | grep -c -- "-gate-" || true)"
  echo "ANSWER gate host=$(hostname -s) step=${step} sha=${real_head:-${sha}} rc=${rc}" \
       "result=[${tail_line}] fails=[${fails}] ${inv:-verification: n/a}" \
       "log=${out} wt_gone=${gone} stale_gate_wts=${stale}"
}
trap answer EXIT

step="fetch";     cd "${main}"; git fetch -q origin
step="worktree";  git worktree add -q --detach "${wt}" "${sha}"
step="pytest";    cd "${wt}"
set +e
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider -rf "${paths[@]}" > "${out}" 2>&1
rc=$?
set -e
real_head="$(git rev-parse --short HEAD)"
tail_line="$(tail -1 "${out}")"
fails="$(grep '^FAILED' "${out}" | sed 's/.*:://;s/ .*//' | paste -sd, -)"
step="inventory"; inv="$(python3 tools/claim_inventory.py 2>/dev/null | grep -m1 verification || echo 'verification: n/a')"
step="cleanup";   cd "${main}"
git worktree remove --force "${wt}" >/dev/null 2>&1 || true
step="done"
