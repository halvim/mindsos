#!/usr/bin/env bash
# Watch CI on a PR and report; with --merge, squash-merge and clean up. MAC ONLY.
#
# Usage:  tools/slice_land.sh <pr-number> [--merge]
#
# Without --merge it STOPS at green so you get a last look. It refuses to merge
# unless every check concluded SUCCESS, and it prints the branch-tip vs squash
# diff line count so RULES 12.2(a) is discharged by a MEASUREMENT, not a claim.
set -euo pipefail

pr="${1:?usage: slice_land.sh <pr-number> [--merge]}"
merge=0; [[ "${2:-}" == "--merge" ]] && merge=1

repo="$(git rev-parse --show-toplevel)"; cd "$repo"
branch="$(gh pr view "${pr}" --json headRefName -q .headRefName)"
tip="$(git rev-parse --short "origin/${branch}" 2>/dev/null || echo NONE)"

gh pr checks "${pr}" --watch --interval 60 > "/tmp/pr${pr}.txt" 2>&1 || true
rollup="$(gh pr view "${pr}" --json statusCheckRollup -q '[.statusCheckRollup[].conclusion]|join(",")')"
mergeable="$(gh pr view "${pr}" --json mergeable -q .mergeable)"

if (( ! merge )) || [[ "${rollup}" != *SUCCESS* || "${rollup}" == *FAILURE* ]]; then
  echo "ANSWER slice_land host=$(hostname -s) pr=${pr} merged=n ci=${rollup}" \
       "mergeable=${mergeable} branch=${branch} tip=${tip}" \
       "main=$(git rev-parse --short origin/main)"
  exit 0
fi

wt="../_MindsOS-${branch#feat/}"
find .git -name '*.lock' -print -delete >/dev/null 2>&1 || true
[[ -d "${wt}" ]] && git worktree remove "${wt}" >/dev/null 2>&1 || true
gh pr merge "${pr}" --squash --delete-branch > "/tmp/merge${pr}.txt" 2>&1 || true
git fetch -q origin
sq="$(gh pr view "${pr}" --json mergeCommit -q .mergeCommit.oid | cut -c1-7)"
diff_lines="$(git diff "${tip}" "${sq}" 2>/dev/null | wc -l | tr -d ' ')"
git -c rebase.autoStash=true pull -q --rebase origin main >/dev/null 2>&1 || true

echo "ANSWER slice_land host=$(hostname -s) pr=${pr} state=$(gh pr view "${pr}" --json state -q .state)" \
     "squash=${sq} parent=$(git rev-parse --short "${sq}^") tip=${tip} diff_lines=${diff_lines}" \
     "main=$(git rev-parse --short origin/main) wt_gone=$(test -d "${wt}" && echo n || echo y)" \
     "shared_head=$(git rev-parse --short HEAD)"
