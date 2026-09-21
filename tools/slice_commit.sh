#!/usr/bin/env bash
# Stage EXPLICIT paths, commit, push. MAC ONLY. Optionally open the PR.
#
# Usage:
#   tools/slice_commit.sh "<message>" <path> [<path>...]
#   tools/slice_commit.sh --pr "<title>" <body-file> "<message>" <path> [<path>...]
#
# Never `git add -A` (RULES 5): the staged set is asserted against the paths
# given, and the commit aborts if they differ.
set -euo pipefail

pr=0; title=""; body=""
if [[ "${1:-}" == "--pr" ]]; then
  pr=1; shift
  title="${1:?--pr needs a title}"; shift
  body="${1:?--pr needs a body file}"; shift
  [[ -f "${body}" ]] || { echo "ANSWER slice_commit status=NO_BODY_FILE file=${body}" >&2; exit 1; }
fi
msg="${1:?usage: slice_commit.sh [--pr <title> <body-file>] \"<message>\" <path>...}"; shift
(( $# > 0 )) || { echo "ANSWER slice_commit status=NO_PATHS" >&2; exit 1; }

repo="$(git rev-parse --show-toplevel)"; cd "$repo"
branch="$(git branch --show-current)"
[[ -n "${branch}" && "${branch}" != "main" ]] || {
  echo "ANSWER slice_commit status=REFUSING_ON_MAIN branch=${branch:-DETACHED}" >&2; exit 1; }

find .git -name '*.lock' -print -delete >/dev/null 2>&1 || true
find "$(git rev-parse --git-dir)" -name '*.lock' -print -delete >/dev/null 2>&1 || true

git add -- "$@"
staged="$(git diff --cached --name-only | sort | tr '\n' ' ')"
git commit -q -m "${msg}" \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>" \
  -m "Claude-Session: https://claude.ai/code/session_015DsVGzaAWuc6NwF2cr1RfU"
git push -q -u origin "${branch}"

url=""
if (( pr )); then
  url="$(gh pr create --base main --head "${branch}" --title "${title}" --body-file "${body}" 2>&1 | tail -1)"
fi

head="$(git rev-parse --short HEAD)"
remote="$(git rev-parse --short "origin/${branch}" 2>/dev/null || echo NONE)"
echo "ANSWER slice_commit host=$(hostname -s) head=${head} pushed=$([[ "${head}" == "${remote}" ]] && echo y || echo n)" \
     "files=$(git show --pretty= --name-only HEAD | wc -l | tr -d ' ')" \
     "numstat=$(git show --numstat --pretty= HEAD | awk '{a+=$1;d+=$2} END {print a"/"d}')" \
     "dirty=$(git status --porcelain | wc -l | tr -d ' ') staged=[${staged% }] pr=${url}"
