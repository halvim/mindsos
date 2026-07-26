# Brain `view` verb — graph visualizer

Status: shipped for nilm and verified live (`view` → 51 caps / 92 datastates /
2 segments, scp-download flow works). Inherited by every brain that boots the
shared `BrainREPL` (arc1, arc3) — but only nilm has a `viz_spec` so far.

## What it is
`view` inside the brain REPL builds a **self-contained interactive HTML graph**
of the live brain (DataStates + capacities + finder segments) into a temp file
on the Linux host, then prints a one-line **scp** command to download + open it
on the Mac. No tunnel, no server, no wrapper.

## Decisions made (this chat)
- **Name `view` (verb) / `viz` (internals), not `graph`.** `Graph` /
  `Metagraph` / role-graphs are core concepts and `mindsos_cli/commands/graph.py`
  already exists — `graph` would clash. "graph" survives only as the artifact
  noun in help text.
- **Shared verb + per-brain hook.** One `_do_view` on `BrainREPL`; every brain
  inherits it. Each brain optionally ships a `viz_spec` (semantic ds-groups +
  finder segments). No `viz_spec` → a topology heuristic
  (given/derived/verdict/constant) fills groups and there are no segments.
- **Delivery = printed scp.** The runtime is a headless Linux box reached over
  SSH; only the Mac can open a Mac browser or initiate a pull. SSH stdout / scp
  is the one generic, no-tunnel, no-server, terminal-agnostic transport. Host is
  inferred from `SSH_CONNECTION`; swap for your ssh-config alias if you use one.
- **Template = the `brain_graph_2.html` prototype, ported** (vis-network inlined;
  DATA injected at the `/*__DATA__*/{}` placeholder). Palette parity kept.

## DATA schema (what `build_data` emits, what the template renders)
`{ nodes:[{id:"ds:x"|"cap:x", label, kind:"ds"|"cap", group, color{}, shape,
seg:[segkey], cap?:{family,inputs,outputs}}], edges:[{id,from,to,arrows,
kind:"produce"|"consume", seg:[segkey]}], segments:{key:{label,caps[],nodeIds[]}},
capColor:{family:hex}, dsColor:{group:hex} }`. Node ids collapse to short names.

## Files
- `mindsos_cli/brain_viz.py` — `build_data(views, spec, context)` → DATA; headless
  + unit-testable; default palette matches the prototype.
- `mindsos_cli/commands/brain_viz_template.html` — the viewer (self-contained).
- `mindsos_cli/commands/brain.py` — `_do_view` verb; `BrainREPL(stack, viz_spec=…)`.
- `projects/amii_study/nilm_brain/viz_spec.py` — nilm hook: 7-group `DS_GROUPS`
  + `SEGMENTS` (recomposes cycle + appliance via `nilm_brain.pipelines`).
- `projects/amii_study/nilm_brain/repl.py` — passes `viz_spec` to `BrainREPL`.

## Run
`PYTHONPATH=.:projects/amii_study python3 -m nilm_brain.repl` then `view`
(commit on the Mac, run on the Linux box; `view` prints the scp line to paste).

## Open items / next
- **arc1 + arc3 to parity:** each needs its own `viz_spec.py` (DS_GROUPS +
  SEGMENTS) + one-line `repl.py` wiring. Derive each brain's real ds-group
  taxonomy and finder segments from *that brain's own code* — do not copy nilm's.
- **Wheel packaging:** add `package_data` `mindsos_cli = ["commands/*.html"]` so
  the template ships in an installed build (source/PYTHONPATH runs don't need it).
- **Node-id caveat:** ids are `cap:`/`ds:` + last name segment; two capacities
  sharing a short name across categories would merge. Fine for current brains.
- **scp host:** inferred from `SSH_CONNECTION`; hardcode the alias if desired.
