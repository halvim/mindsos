# syntax=docker/dockerfile:1.7
#
# Robot Demo backend image — OWNS its build (the core Dockerfile stays
# demo-free). It layers on top of the already-built MindsOS prod image:
#
#   FROM mindsos:<phase>-prod  (built by the repo-root Dockerfile `prod` stage)
#     + the demo-only heavy deps (separate hash-pinned lockfile, PB-O)
#     + the `robot_demo` consumer package (imports the stack downward, ADR-0010)
#
# Build it AFTER the base image exists. Build context = repo root (so the
# COPY robot_demo/... lines resolve). The compose overlay
# (robot_demo/deploy/docker-compose.demo.yml) wires both:
#
#   docker compose -f docker-compose.yml --profile cli build mindsos   # base
#   docker compose -f docker-compose.yml \
#     -f robot_demo/deploy/docker-compose.demo.yml build demo-backend  # this
#
# (robot_demo/deploy/run_linux_tests.sh does both in order.)
#
# requirements-demo.txt is generated on the 3.12 host:
#   pip-compile --generate-hashes -o robot_demo/requirements-demo.txt \
#       robot_demo/requirements-demo.in

ARG MINDSOS_BASE=mindsos:phase51-prod
FROM ${MINDSOS_BASE}

# Demo-only deps (MuJoCo, FastAPI, …). Inherits /app + the mindsos_* packages
# + entrypoint.sh from the base prod image.
COPY robot_demo/requirements-demo.txt ./robot_demo/requirements-demo.txt
RUN pip install --no-cache-dir --require-hashes -r robot_demo/requirements-demo.txt

# Only the importable package — tests/docs/deploy are not needed at runtime.
COPY robot_demo/__init__.py ./robot_demo/__init__.py
COPY robot_demo/backend ./robot_demo/backend
# DM-2 skill-bundle TOML data (read at runtime by install_skill).
COPY robot_demo/bundles ./robot_demo/bundles
# DM-3 live motion: the shipped MuJoCo cell + motion machinery (wrapped, not
# edited — PB-QQ) and the render/geometry assets. sim/ is required at runtime
# (SimEngine imports motion.py + build_cell + the menagerie meshes); web/ is
# the render-asset source the DM-4 UI will consume.
COPY sim ./sim
COPY web ./web

RUN chown -R mindsos:mindsos /app

# entrypoint.sh (inherited) does the gosu drop, then execs this command.
CMD ["python", "-m", "robot_demo.backend.main"]
