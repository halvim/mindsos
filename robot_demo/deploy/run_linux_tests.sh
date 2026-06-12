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
    # Externally-managed hosts (PEP 668, e.g. apt Python 3.12 on the Mac
    # Mini) refuse a bare `pip install`; retry with --break-system-packages
    # (dedicated gate box — acceptable).
    "$PYBIN" -m pip install --quiet pip-tools \
      || "$PYBIN" -m pip install --quiet --break-system-packages pip-tools \
      || fail "pip-tools install failed (needed for pip-compile)"
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
# DM-2: FalkorDB is a long-running service — it must stay UP across both
# boots so the second boot can load the per-device Globals the first boot
# persisted (the consumer restarts, not the DB). Bring it up ONCE; run the
# demo as one-off `compose run` containers that do NOT stop it.
step "2b. Start the shared FalkorDB (stays up across both boots)"
"${COMPOSE[@]}" up -d --wait falkordb || fail "falkordb did not become healthy"
pass "falkordb up + healthy"

# Deterministic gate: drop the demo's own graph + clean its server.db so
# 'first boot' is a genuine empty-start (mint+install) and 'second boot' is
# a genuine reload (no-op). The demo's graph is isolated (PB-JJ:
# DEMO_FALKOR_GRAPH=robot_demo) so this never touches a real Global.
step "2c. Reset demo state for a deterministic empty-start"
"${COMPOSE[@]}" exec -T falkordb redis-cli GRAPH.DELETE "${DEMO_FALKOR_GRAPH:-robot_demo}" >/dev/null 2>&1 || true
rm -rf ./.mindsos-demo/server-db 2>/dev/null || true
pass "demo graph + server.db cleared"

# ---------------------------------------------------------------------------
run_smoke() {  # $1 = label, $2 = first|second (DM-2 assertions differ)
  local out rc mode="${2:-first}"
  out="$("${COMPOSE[@]}" run --rm -e DEMO_BOOTSTRAP_ONLY=1 demo-backend 2>&1)" \
    && rc=0 || rc=$?
  printf '%s\n' "$out" | sed 's/^/    | /'
  if [[ $rc -ne 0 ]]; then fail "$1: container exited $rc"; fi
  grep -q "DM-1 SMOKE PASS" <<<"$out" || fail "$1: 'DM-1 SMOKE PASS' not in logs"
  grep -q "4/4 Episodes" <<<"$out" || fail "$1: did not report 4/4 Episodes"
  # ── DM-2 assertions ──
  grep -q "DM-2 BUNDLES INSTALLED" <<<"$out" || fail "$1: no DM-2 bundle marker"
  grep -q "manager@1.0" <<<"$out" || fail "$1: manager bundle not installed on mgr"
  grep -q "arm-suction@1.0" <<<"$out" || fail "$1: arm-suction bundle not installed"
  grep -q "DM-2 LOCAL SEEDS" <<<"$out" || fail "$1: no DM-2 local-seed marker"
  grep -q "DM-2 GLOBAL PERSIST: falkor" <<<"$out" \
    || fail "$1: Global not persisted to Falkor (expected in-container)"
  if [[ "$mode" == "first" ]]; then
    grep -q "round-tripped intact" <<<"$out" \
      || fail "$1: G-5 episode→Falkor round-trip did not report success"
  else
    grep -q "(no-op)" <<<"$out" \
      || fail "$1: bundles did not no-op on the reloaded Global (idempotency)"
  fi
  pass "$1: 4 brains, 4/4 Episodes, bundles+seeds present, exit 0"
}

step "3. First boot (empty-start) — mint + install + seed + G-5 — DM-1+DM-2 GATE"
run_smoke "first boot" first

step "4. Second boot (reload) — persisted Globals load, bundles no-op (P6)"
run_smoke "second boot" second

# ---------------------------------------------------------------------------
step "5. RAM + jitter measurement (PB-N / P7)"
"${COMPOSE[@]}" run --rm -e DEMO_BOOTSTRAP_ONLY=1 demo-backend \
  python -m robot_demo.backend.measure 2>&1 | sed 's/^/    | /' \
  || fail "measure.py failed"
pass "RAM + jitter recorded (numbers above; bootstrap proxy — real live bar below)"

# ---------------------------------------------------------------------------
# DM-3 GATE: each atomic capacity moves the live MuJoCo sim, checklist-
# verified, on the single shared Cell (PB-KK) — plus fault injection (G-8)
# and the REAL jitter bar under load (PB-E/RR). Runs IN the container (the
# image ships sim/ + mujoco; tests/ is not shipped, so the gate is the
# greppable robot_demo.backend.dm3_check module, not pytest).
step "6. DM-3 live-motion gate (shared SimEngine + atomic capacities)"
DM3_OUT="$("${COMPOSE[@]}" run --rm demo-backend \
  python -m robot_demo.backend.dm3_check 2>&1)" && DM3_RC=0 || DM3_RC=$?
printf '%s\n' "$DM3_OUT" | sed 's/^/    | /'
[[ $DM3_RC -eq 0 ]] || fail "DM-3 live-motion check exited $DM3_RC"
grep -q "DM-3 LIVE MOTION PASS" <<<"$DM3_OUT" \
  || fail "DM-3: 'DM-3 LIVE MOTION PASS' not in logs (atomic/fault check failed)"
pass "DM-3: atomics move the live sim (checklist-verified), fault detected, jitter recorded"

# ---------------------------------------------------------------------------
if [[ "${RUN_PYTEST:-0}" == "1" ]]; then
  step "7. [optional] Host pytest of robot_demo/tests/"
  PYTHONPATH="$ROOT" "$PYBIN" -m pytest robot_demo/tests/ -q \
    && pass "core scenario tests" || fail "host pytest failed"
  # Integration tests need mujoco + a real server on the host; the in-
  # container DM-3 gate (step 6) is authoritative for live motion.
  PYTHONPATH="$ROOT" "$PYBIN" -m pytest robot_demo/tests/ -m integration -q \
    && pass "host integration tests" || fail "integration pytest failed"
fi

step "8. Teardown"
"${COMPOSE[@]}" down >/dev/null 2>&1 || true
pass "stack down"

printf '\n\033[1;32mALL MANDATORY CHECKS PASSED — DM-1 + DM-2 + DM-3 gate green.\033[0m\n'
printf '  (DM-2: per-device bundles installed idempotently, Local seeds visible,\n'
printf '   Globals persisted to Falkor, G-5 episode round-trip verified.\n'
printf '   DM-3: each ⬡ atomic moves the live shared sim checklist-verified,\n'
printf '   fault injection detected, real jitter bar measured.)\n'
