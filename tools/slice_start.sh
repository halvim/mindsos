#!/usr/bin/env bash
# Cut a slice worktree off origin/main. MAC ONLY (RULES 2; git runs on the Mac).
#
# Usage:  tools/slice_start.sh <slice-name>
# Makes:  branch feat/<slice-name>, worktree ../_MindsOS-<slice-name>
#
# Every lane script ends in one ANSWER line computed from the END STATE, never
# from its own exit codes: a step's report is a claim about what it tried.
set -euo pipefail

name="${1:?usage: slice_start.sh <slice-name>}"
repo="$(git rev-parse --show-toplevel)"
cd "$repo"
wt="../_MindsOS-${name}"
branch="feat/${name}"

find .git -name '*.lock' -print -delete >/dev/null 2>&1 || true
git fetch -q origin

if git show-ref --quiet "refs/heads/${branch}"; then
  echo "ANSWER slice_start host=$(hostname -s) status=BRANCH_EXISTS branch=${branch}" >&2
  exit 1
fi

git worktree add -q -b "${branch}" "${wt}" origin/main

head="$(git -C "${wt}" rev-parse --short HEAD 2>/dev/null || echo NONE)"
echo "ANSWER slice_start host=$(hostname -s) wt=$(test -d "${wt}" && echo y || echo n)" \
     "branch=$(git -C "${wt}" branch --show-current 2>/dev/null || echo NONE)" \
     "head=${head} origin_main=$(git rev-parse --short origin/main)" \
     "path=${wt}"
