#!/usr/bin/env bash
# Robot Demo — Linux validation runner (DM-1).
#
# Run from the REPO ROOT on the Linux server (Mac Mini), Python 3.12 +
# Docker present:
#
#   bash robot_demo/deploy/run_linux_tests.sh
#
# Tiers:
#   [MANDATORY] build the `demo` image + run the container bootstrap smoke
#               (real mindsos_server: schema init + insert_user + login,
#               4 device-instances, 4 Episodes consolidate) + idempotent
#               re-boot. This is the authoritative DM-1 deployment gate —
#               it exercises the real 3.12 stack end-to-end.
#   [MANDATORY] in-container RAM + jitter measurement (records the numbers).
#   [OPTIONAL]  host pytest of robot_demo/tests/ (dev-loop; set RUN_PYTEST=1
#               with a 3.12 venv that has the repo installed).
#
# Nothing here needs the browser — DM-1 is headless. The first browser-
# linked live test is DM-4. Exit non-zero on any mandatory failure.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f robot_demo/deploy/docker-compose.demo.yml)
REQ_IN="robot_demo/requirements-demo.in"
REQ_TXT="robot_demo/requirements-demo.txt"

pass() { printf '  \033[32m✓ PASS\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗ FAIL\033[0m %s\n' "$1"; exit 1; }
step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
step "0. Preflight"
command -v docker >/dev/null || fail "docker not found"
docker compose version >/dev/null 2>&1 || fail "docker compose v2 not found"
PYBIN="${PYBIN:-python3.12}"
command -v "$PYBIN" >/dev/null 2>&1 || PYBIN="python3"
pass "docker + $($PYBIN --version)"

# ---------------------------------------------------------------------------
step "1. Compile the hash-pinned demo lockfile (PB-O)"
if [[ -f "$REQ_TXT" && "${RECOMPILE:-0}" != "1" ]]; then
  pass "$REQ_TXT present (set RECOMPILE=1 to regenerate)"
else
  if ! "$PYBIN" -m piptools --version >/dev/null 2>&1; then
    "$PYBIN" -m pip install --quiet pip-tools || fail "pip-tools install failed (needed for pip-compile)"
  fi
  "$PYBIN" -m piptools compile --generate-hashes --output-file "$REQ_TXT" "$REQ_IN" \
    || fail "pip-compile failed (needs network for mujoco/fastapi wheels)"
  pass "generated $REQ_TXT"
fi

# ---------------------------------------------------------------------------
step "2. Build the base prod image, then the demo image"
# The demo Dockerfile is FROM mindsos:<phase>-prod, so build that first.
docker compose -f docker-compose.yml --profile cli build mindsos \
  || fail "core prod image build failed"
pass "base mindsos:phase51-prod built"
"${COMPOSE[@]}" build demo-backend || fail "demo image build failed"
pass "image mindsos:demo-backend built (FROM mindsos:phase51-prod)"

# ---------------------------------------------------------------------------
run_smoke() {  # $1 = label
  local out rc
  out="$(DEMO_BOOTSTRAP_ONLY=1 "${COMPOSE[@]}" up --abort-on-container-exit \
         --exit-code-from demo-backend demo-backend 2>&1)" && rc=0 || rc=$?
  printf '%s\n' "$out" | sed 's/^/    | /'
  if [[ $rc -ne 0 ]]; then fail "$1: container exited $rc"; fi
  grep -q "DM-1 SMOKE PASS" <<<"$out" || fail "$1: 'DM-1 SMOKE PASS' not in logs"
  grep -q "4/4 Episodes" <<<"$out" || fail "$1: did not report 4/4 Episodes"
  "${COMPOSE[@]}" down >/dev/null 2>&1 || true
  pass "$1: 4 device-instances up, 4/4 Episodes consolidated, exit 0"
}

step "3. Container bootstrap smoke (real server, 4 brains) — THE DM-1 GATE"
run_smoke "first boot"

step "4. Idempotent re-boot (P6) — second boot on the same server.db"
run_smoke "second boot"

# ---------------------------------------------------------------------------
step "5. RAM + jitter measurement (PB-N / P7)"
"${COMPOSE[@]}" run --rm -e DEMO_BOOTSTRAP_ONLY=1 demo-backend \
  python -m robot_demo.backend.measure 2>&1 | sed 's/^/    | /' \
  || fail "measure.py failed"
"${COMPOSE[@]}" down >/dev/null 2>&1 || true
pass "RAM + jitter recorded (numbers above; jitter is a provisional proxy — real bar at DM-3)"

# ---------------------------------------------------------------------------
if [[ "${RUN_PYTEST:-0}" == "1" ]]; then
  step "6. [optional] Host pytest of robot_demo/tests/"
  PYTHONPATH="$ROOT" "$PYBIN" -m pytest robot_demo/tests/ -q \
    && pass "core scenario tests" || fail "host pytest failed"
  PYTHONPATH="$ROOT" "$PYBIN" -m pytest robot_demo/tests/ -m integration -q \
    && pass "real-server integration test" || fail "integration pytest failed"
fi

printf '\n\033[1;32mALL MANDATORY CHECKS PASSED — DM-1 deployment gate green.\033[0m\n'
