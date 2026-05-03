#!/usr/bin/env bash
# mindsos container entrypoint.
#
# Briefly runs as root to:
#   1. Ensure /var/lib/mindsos and /var/log/mindsos exist.
#   2. chown them to mindsos:mindsos so the unprivileged user can write.
# Then drops privileges to the `mindsos` user (UID/GID 1000) via gosu and execs
# the requested command. If no command is provided, defaults to `mindsos --help`.
#
# Idempotent: chown failures (e.g., read-only mount) are tolerated.

set -euo pipefail

for d in /var/lib/mindsos /var/log/mindsos; do
    mkdir -p "$d" 2>/dev/null || true
    chown -R mindsos:mindsos "$d" 2>/dev/null || true
done

if [ "$#" -eq 0 ]; then
    exec gosu mindsos mindsos --help
fi

exec gosu mindsos "$@"
