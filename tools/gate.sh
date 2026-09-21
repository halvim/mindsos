#!/usr/bin/env bash
# Gate a SHA in a throwaway worktree. LINUX BOX ONLY (all code runs there).
#
# Usage:  tools/gate.sh <sha> [pytest-path...]
# Default paths: tests/architecture tests/test_adr_status_consistency.py
#
# Prints pass/fail counts, the FAILING TEST NAMES (a red count is not the
# check), and the claim-inventory verification line. Removes the worktree.
set -euo pipefail

sha="${1:?usage: gate.sh <sha> [pytest-path...]}"; shift || true
paths=("$@")
(( ${#paths[@]} )) || paths=(tests/architecture tests/test_adr_status_consistency.py)

main="${MINDSOS_MAIN:-/home/sanmyaku/mindsos}"
cd "${main}"
git fetch -q origin
wt="${main}-gate-${sha}"
[[ -d "${wt}" ]] && git worktree remove --force "${wt}" >/dev/null 2>&1 || true
git worktree add -q --detach "${wt}" "${sha}"
cd "${wt}"

out="${HOME}/gate-${sha}.txt"
set +e
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider -rf "${paths[@]}" > "${out}" 2>&1
rc=$?
set -e
inv="$(python3 tools/claim_inventory.py 2>/dev/null | grep -m1 verification || echo 'verification: n/a')"
real_head="$(git rev-parse --short HEAD)"
tail_line="$(tail -1 "${out}")"
fails="$(grep '^FAILED' "${out}" | sed 's/.*:://;s/ .*//' | paste -sd, -)"

cd "${main}"
git worktree remove --force "${wt}" >/dev/null 2>&1 || true

echo "ANSWER gate host=$(hostname -s) sha=${real_head} rc=${rc} result=[${tail_line}]" \
     "fails=[${fails}] ${inv} log=${out} wt_gone=$(test -d "${wt}" && echo n || echo y)"
