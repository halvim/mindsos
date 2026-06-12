#!/usr/bin/env bash
#
# Robot Demo — one-command control for the live backend (Seam A/B WS server).
#
# Run on the Linux/Mac-Mini server, from the repo root (this file lives there):
#
#   ./demo.sh up        # build + start + print the browser URL
#   ./demo.sh down      # stop everything
#   ./demo.sh restart   # bounce the backend (reuses current image)
#   ./demo.sh logs      # follow the backend logs (Ctrl-C to exit)
#   ./demo.sh status    # container state + the live URL
#   ./demo.sh build     # rebuild the BASE image (first time / after a phase bump)
#
# Tip: `chmod +x demo.sh` once, then `./demo.sh up`. (Or `bash demo.sh up`.)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f robot_demo/deploy/docker-compose.demo.yml)
PORT="${DEMO_WS_PORT:-8765}"
LISTEN_MARKER="DM-4 WS SERVER LISTENING"

usage() {
  cat <<'EOF'

  Robot Demo — live backend control

  usage:  ./demo.sh <command>

  commands:
    up        build (demo image) + start the backend, wait until it is
              listening, then print the dashboard URL to open
    down      stop the backend + FalkorDB
    restart   bounce the backend (reuses the current image; faster than up)
    logs      follow the backend logs live (Ctrl-C to exit)
    status    show container state + the dashboard URL if it is up
    build     rebuild the BASE image — needed the first time, or after a
              MindsOS phase bump (slow); run once, then use 'up'
    help      show this message

  env overrides:
    DEMO_WS_PORT   WebSocket port (default 8765)

  typical first run:
    ./demo.sh build      # once
    ./demo.sh up         # prints presentation.html?live=ws://<ip>:<port>

EOF
}

lan_ip() { hostname -I 2>/dev/null | awk '{print $1}'; }

print_url() {
  local ip; ip="$(lan_ip)"
  echo
  echo "  ✅ demo backend is live on port ${PORT}."
  echo "  open the dashboard with one of these:"
  echo "    • same machine : presentation.html?live=ws://localhost:${PORT}"
  echo "    • another machine on your network:"
  echo "        presentation.html?live=ws://${ip:-<server-ip>}:${PORT}"
  echo
}

wait_listening() {
  echo "  waiting for the brains to come up (first boot builds the MuJoCo body, ~30-90s)…"
  local i
  for i in $(seq 1 120); do
    if "${COMPOSE[@]}" logs demo-backend 2>/dev/null | grep -q "$LISTEN_MARKER"; then
      return 0
    fi
    sleep 2
  done
  return 1
}

cmd="${1:-up}"
case "$cmd" in
  up)
    "${COMPOSE[@]}" up -d --build demo-backend
    if wait_listening; then
      print_url
    else
      echo "  ❌ the server did not report LISTENING in time."
      echo "     check the logs:  ./demo.sh logs"
      echo "     (first run only? build the base image:  ./demo.sh build)"
      exit 1
    fi
    ;;
  build)
    echo "  building the base image (this is the slow one — only needed first time / after a phase bump)…"
    docker compose -f docker-compose.yml --profile cli build mindsos
    "${COMPOSE[@]}" build demo-backend
    echo "  ✅ images built. start with:  ./demo.sh up"
    ;;
  restart)
    "${COMPOSE[@]}" restart demo-backend
    if wait_listening; then
      print_url
      echo "  (reload the dashboard page — it does not auto-reconnect.)"
    else
      echo "  ❌ no LISTENING after restart — check: ./demo.sh logs"
      exit 1
    fi
    ;;
  down)
    "${COMPOSE[@]}" down
    echo "  ✅ stopped."
    ;;
  logs)
    "${COMPOSE[@]}" logs -f demo-backend
    ;;
  status)
    "${COMPOSE[@]}" ps
    if "${COMPOSE[@]}" logs demo-backend 2>/dev/null | grep -q "$LISTEN_MARKER"; then
      print_url
    else
      echo "  (backend not listening yet — 'up' it or check 'logs')"
    fi
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "  unknown command: ${cmd}"
    usage
    exit 2
    ;;
esac
