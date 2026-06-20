# Paste-into-DM-3-chat prompt (pose-frame alignment)

Copy everything below the line into the DM-3 chat.

---

Heads-up from the UI/comms side: the dashboard's **live data path (Seam B / DM-4)** is now built
and frozen against a documented WebSocket contract — `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`.
You're DM-3 (Seam C: body adapter + atomic capacities + live-motion wrapper), so you do **not**
need most of it. There is exactly **one** thing to align on so DM-4 can consume your motion output
without writing an adapter:

**Read only §2.3 `pose` of `ROBOT_DEMO_WS_CONTRACT.md`** (plus the "Which DM step needs this" note
at the top). The UI consumes body/item positions as a `pose` frame shaped like this:

- `items[name] = [x, y]` — item positions in the workcell world frame the cell view uses
  (the same 2D-schematic / vertical-shelf mapping the existing mock uses).
- Reserved for the 3D robot view: `bodies[name] = [x, y, z, qw, qx, qy, qz]` — per-body transform
  (position + quaternion). Not consumed yet, but this is the shape to target.

**What I need from you:** make your live-motion wrapper's per-step body/item output expressible as
that shape (a `pose` frame should be a thin wrapper over what you already produce — no reshaping at
DM-4). If your natural output differs (different units, frame, body naming, or you produce full
3D transforms now), say so and propose the mapping — it's cheaper to reconcile the names/frame now
than at DM-4.

You do **not** need the rest of the UI files (`presentation.html`, `datasource.js`,
`mock_ws_server.js`) — those are DM-4's. The cognitive `state`/`message` frames and the
browser→server commands are all DM-4 concerns; ignore them.

One naming note to confirm against the demo's canonical model: the contract uses brain ids
`mgr / a1 / a2 / conv` and item ids `box1 / sheet1 / tube1`. If your sim uses different body
names, note the body→id map so DM-4 can translate.
