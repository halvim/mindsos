# Robot Demo — deployment (Linux server)

Self-contained deploy assets for the Robot Demo backend. The demo runs as a
**compose overlay** on top of the repo-root stack, **reusing the existing
`falkordb`** service while keeping its own data dirs and its own folder.

Everything here runs from the **repo root** on the Mac Mini (Linux), with
Docker + Python 3.12 present.

## Pair-execution roles (strict — code never runs on the Mac)

| Host | Role |
|---|---|
| **Cowork sandbox** (3.10) | Author + validate core logic only (duck sessions, `tomli`; cannot import `mindsos_server`). No git. |
| **Mac** (3.12) | **git only** — `git add` (scoped paths), `commit`, `push`. **Do not run code/tests here.** |
| **Linux** (this box) | `git pull`, then **run + test ALL code** — pytest + `run_linux_tests.sh`. The authoritative gate. |

Code reaches Linux via the GitHub remote (`git push` on Mac → `git pull`
here), not file copy. Tests and the container gate produce non-authoritative
results anywhere but here.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | The **demo-owned** image: `FROM mindsos:<phase>-prod` + demo deps + the `robot_demo` package. Keeps the core Dockerfile demo-free. |
| `docker-compose.demo.yml` | Overlay defining only the `demo-backend` service; merged with the root compose so it reuses `falkordb`. |
| `run_linux_tests.sh` | The DM-1 validation runner (build base → build demo → bootstrap smoke → idempotency → measure). |

The demo image **owns its Dockerfile** here (`robot_demo/deploy/Dockerfile`)
and layers on the already-built core image (`FROM mindsos:<phase>-prod`), so
the core `Dockerfile` stays demo-free. **Build order matters:** the base prod
image must exist before the demo image (`run_linux_tests.sh` does both; the
default base tag is `mindsos:phase51-prod`, overridable via `MINDSOS_BASE`).
Build context is the repo root so the demo Dockerfile can COPY `robot_demo/`.
The demo's runtime data is isolated under `./.mindsos-demo/` (server.db +
logs), separate from any main MindsOS deployment even though the graph DB is
shared.

## One-time: compile the hash-pinned lockfile

The demo's heavy deps (MuJoCo, FastAPI, …) ride a **separate** hash-pinned
lockfile (the core image installs deps with `--no-deps`, so a `pyproject`
extras group would be inert — see design log PB-O):

```bash
pip install pip-tools
pip-compile --generate-hashes -o robot_demo/requirements-demo.txt robot_demo/requirements-demo.in
```

The demo image build requires `requirements-demo.txt` to exist; the core
`prod`/`test` images are unaffected (they don't reference it).

## Run the DM-1 gate

```bash
bash robot_demo/deploy/run_linux_tests.sh
```

This builds the image and runs the **container bootstrap smoke** twice (real
`mindsos_server`: schema init + `insert_user` + `login`, 4 device-instances,
4 Episodes consolidate, idempotent re-boot), then records RAM + jitter. It is
the authoritative DM-1 deployment check and needs no host Python deps.

## Run it for real (stays up)

```bash
# 1) build the base prod image the demo is FROM (once / on mindsos changes)
docker compose -f docker-compose.yml --profile cli build mindsos

# 2) build + start the demo
docker compose \
  -f docker-compose.yml \
  -f robot_demo/deploy/docker-compose.demo.yml \
  up -d --build demo-backend

docker compose -f docker-compose.yml -f robot_demo/deploy/docker-compose.demo.yml \
  logs -f demo-backend     # watch for "DM-1 SMOKE PASS"
```

DM-1 is **headless** — the container runs bootstrap + smoke and then idles
(DM-2+ starts the sim loop + BrainBus + WebSocket server here). There is no
browser UI yet; the first browser-linked live test is **DM-4**.

## Reset between runs (G-11)

```bash
docker compose -f docker-compose.yml -f robot_demo/deploy/docker-compose.demo.yml \
  restart demo-backend
```

In-memory CapacityLayers + KnowledgeLayers clear on restart (DM-1 holds all
L2 in memory). The run-scoped Local wipe lands in DM-2 with per-device Falkor
persistence.

## Environment variables

| Var | Default | Meaning |
|---|---|---|
| `DEMO_BOOTSTRAP_ONLY` | _(unset)_ | `1` → run bootstrap + smoke, then exit 0 (gate/CI). |
| `DEMO_PW_<ID>` | `demo-pass` | Per-user demo password (`DEMO_PW_ADMIN`, `DEMO_PW_MGR`, …). Local demo only. |
| `DEMO_LOG_LEVEL` | `INFO` | Python log level. |
| `FALKORDB_HOST` / `FALKORDB_PORT` | `falkordb` / `6379` | Shared graph DB (used from DM-2). |
