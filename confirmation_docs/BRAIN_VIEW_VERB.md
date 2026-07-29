# Brain `view` verb — graph visualizer

Status: **SHIPPED to `main` and LIVE on all three brains (nilm, arc1, arc3).**
Generic verb/builder/template: PR #78 (Linux gate 4334) tagged
**`brain-view-confirmed`**; wheel-packaging follow-up PR #81 tagged
**`brain-view-pkgdata-confirmed`** (gate 4334, 0 fail). Per-brain `viz_spec`
hooks landed in each brain's own repo (see Files). Verified live 2026-07-27:
`view` builds the interactive HTML graph + prints the scp line on each brain.

## What it is
`view` inside the brain REPL builds a **self-contained interactive HTML graph**
of the live brain (DataStates + capacities + finder segments) into a temp file
on the Linux host, then prints a one-line **scp** command to download + open it
on the Mac. No tunnel, no server, no wrapper.

## Decisions made
- **Name `view` (verb) / `viz` (internals), not `graph`.** `Graph` /
  `Metagraph` / role-graphs are core concepts and `mindsos_cli/commands/graph.py`
  already exists — `graph` would clash. "graph" survives only as the artifact
  noun in help text.
- **Distribution.** The generic verb/builder/template are shared `mindsos_cli`
  and live on **main**, released as a `mindsos-runtime` tag; brains inherit by
  pinning that tag (or by an editable install) — never by committing the generic
  code per-brain. Only each brain's `viz_spec.py` + one-line repl wiring is
  per-brain.
- **Shared verb + per-brain hook.** One `_do_view` on `BrainREPL`; every brain
  inherits it. Each brain optionally ships a `viz_spec` (semantic ds-groups +
  finder segments). No `viz_spec` → a topology heuristic
  (given/derived/verdict/constant) fills groups and there are no segments.
- **Delivery = printed scp.** Runtime is a headless Linux box reached over SSH;
  only the Mac can open a browser / initiate a pull. Host is inferred from
  `SSH_CONNECTION`; swap for your ssh-config alias if you use one.
- **Template = the `brain_graph_2.html` prototype, ported** (vis-network inlined;
  DATA injected at the `/*__DATA__*/{}` placeholder).

## Legend / labels — brain-neutral (fix 2026-07-28)
The shipped template hardcoded **nilm's** legend vocabulary (`CAPNAMES`/`DSNAMES`)
and title, so on arc1/arc3 the legend + datastate-detail labels rendered
`undefined` and the title read "nilm_brain graph". Fixed:
- Legend/detail labels now come from the data: `build_data` emits
  `capNames`/`dsNames` = each brain's `viz_spec.CAP_LABELS`/`DS_LABELS` merged over
  generic labels for the topology-heuristic ds groups
  (given/derived/verdict/constant), filtered to groups present. The template reads
  those with **fallback to the raw group key** (`names[k] || k`) — never blank.
- Title comes from `viz_spec.TITLE` (`DATA.title`), template default `brain graph`.
- Each brain's `viz_spec` now optionally ships `DS_LABELS`, `CAP_LABELS`, `TITLE`
  (nilm's live groups are the heuristic ones, covered by the generic defaults).
- **NOT done (deferred):** stripping nilm's palette out of `build_data`'s
  `DEFAULT_CAP_COLORS`/`DEFAULT_DS_COLORS` to make the builder fully brain-neutral.
  nilm's `viz_spec` is not tracked in this repo, so its live cap families are still
  coloured by those defaults and can't be relocated from here; the present-only
  legend filter already hides unused keys, so there is no visible cost to leaving
  them. Revisit when nilm's hook is in-repo.

## DATA schema (what `build_data` emits, what the template renders)
`{ nodes:[{id:"ds:x"|"cap:x", label, kind:"ds"|"cap", group, color{}, shape,
seg:[segkey], cap?:{family,inputs,outputs}}], edges:[{id,from,to,arrows,
kind:"produce"|"consume", seg:[segkey]}], segments:{key:{label,caps[],nodeIds[]}},
capColor:{family:hex}, dsColor:{group:hex}, title:str|null, capNames:{family:label}, dsNames:{group:label} }`. Node ids collapse to short names, but **node ids are the full IRI** (`cap:`/`ds:` + iri) so they are unique; `label` is the short name. `capNames`/`dsNames` are filtered to groups present in the nodes.

## Install divergence (load-bearing)
The generic `view` code ships inside the `mindsos-runtime` package. How a brain
picks it up dictates whether the HTML template is present at runtime:
- **arc1 = wheel-from-git.** `requirements.txt` pins
  `mindsos-runtime @ git+ssh://…/mindsos.git@<tag>` → pip builds a wheel, so the
  template MUST be declared as package-data or `view` crashes ("template not
  found").
- **arc3 = editable.** `pip install -e /home/sanmyaku/mindsos` → template sits on
  disk; package-data is irrelevant.
- **package_data fix (PR #81, `d2ec698`):** `pyproject.toml`
  `[tool.setuptools.package-data] mindsos_cli = ["manifest.toml","commands/*.html"]`.
  Verified: fresh wheel install → `mindsos_cli/commands/brain_viz_template.html`
  present. **Reinstall gotcha:** the runtime version string is unchanged across
  tags, so a plain `-r requirements.txt` reports "already satisfied" and keeps
  the old templateless build — bump with
  `pip install --force-reinstall --no-deps "mindsos-runtime @ …@<tag>"`.

## Files
Generic (mono-repo, on `main`):
- `mindsos_cli/brain_viz.py` — `build_data(views, spec, context)` → DATA;
  headless + unit-testable.
- `mindsos_cli/commands/brain_viz_template.html` — the viewer (self-contained).
- `mindsos_cli/commands/brain.py` — `_do_view` verb; `BrainREPL(stack, viz_spec=…)`.

Per-brain hooks (each brain's own repo):
- `projects/amii_study/nilm_brain/viz_spec.py` (+ `repl.py`) — nilm; 7-group
  `DS_GROUPS` + `SEGMENTS` (recompose via `nilm_brain.pipelines`).
  NOTE: shipped nilm `viz_spec` has `DS_GROUPS = 0` (undefined) → nilm runs
  heuristic-only; only its `SEGMENTS` is a real reference. Don't copy it.
- `arc1-brain` repo (`halvim/arc1-brain`, `main`, `6ad11de`):
  `arc1_brain/viz_spec.py` (+ `repl.py`). `DS_GROUPS` verbatim from the
  `ds(name, CATEGORY_*)` 7-category axis in `arc_capacities.py`; `SEGMENTS` = the
  4 `arc_profile.discovery_report` perceive chains via `find_pipeline`, guarded.
  Now also ships `DS_LABELS` (10 groups) + `CAP_LABELS` (9 families: perceiver / reasoning / comparator / detector / generator / operator / predicate / profiler / retrieval) + `TITLE`. Pin bumped to `brain-view-pkgdata-confirmed`. ~44 caps live.
- `arc3` repo (`halvim/arc3`, `main`, `f5cbe45`): `arc3_brain/viz_spec.py`
  (+ `repl.py`). arc3 does not category-tag datastates → `DS_GROUPS` = semantic
  pipeline-stage clusters of `arc3.*` (ingest / perception / subdivision /
  correspondence / grouping); `SEGMENTS` = 5 single-input chains from
  `arc3_caps.py` I/O, guarded. Now also ships `DS_LABELS` (5 groups) + `CAP_LABELS` (ingest / perceive / decompose / comparators / select) + `TITLE`.

## Run
- **nilm:** `PYTHONPATH=.:projects/amii_study python3 -m nilm_brain.repl` → `view`.
- **arc1:** `docker compose up -d` (arc1-falkordb :6381) then
  `FALKORDB_PORT=6381 python -m arc1_brain.repl` → `view`.
- **arc3:** `FALKORDB_PORT=6380 python -m arc3_brain.repl` → `view`
  (Falkor :6380 runs independently; no docker-compose.yml at `/home/sanmyaku/arc3`).
Commit on the Mac, run on the Linux box; `view` prints the scp line to paste.
**scp gotcha:** if the leading `s` is dropped in copy, `cp user@host:…` fails
locally — re-run with `scp`.

## Known limitations
- **arc1 SEGMENTS legitimately drop live.** Per arc1
  `docs/BRAIN_MINDSOS_CONFLICTS.md`, `ConjunctionFinder`/`find_pipeline` reaches
  only perceive chains; reasoning caps are NOT FOUND, so segments that need them
  don't assemble and are omitted. This is correct behavior — the graph reflects
  what the finder can actually build; the node/edge graph is the payload,
  segments are a secondary overlay. Not enriched by hand (hand-authored segments
  would show pipelines the finder can't assemble = misleading).
- **Node ids are the full IRI (unique).** `_vid` keys each node on `cap:`/`ds:` + the full IRI, so two datastates sharing a short name (arc1's `path_finding.goal` vs `phase1.goal`) stay distinct nodes; `label` shows the short name, the detail panel shows the namespace. Before this fix they collapsed to one id and `vis.DataSet` threw "id already exists", blanking the whole graph (arc1 never rendered). Fixed 2026-07-28; the earlier collision `logging.warning` removed as unreachable. Regression-tested in `tests/brain_viz/test_brain_viz_data.py`.
- **scp host** inferred from `SSH_CONNECTION`; hardcode the ssh-config alias if
  desired.
