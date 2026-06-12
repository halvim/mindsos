/* DM-4 headless UI-seam verification (no browser).
 *
 * Feeds the EXACT frame shapes the Python backend emits (frames.py DemoEvents
 * + pose_frame) through the live demo_ui/datasource.js LiveSource seam, using
 * a stub WebSocket, and asserts the UI builds the cumulative `states` array
 * correctly. This proves the backend's frames are consumable by the current
 * UI without a browser (per the robot-demo-ui-verification practice).
 *
 *   node robot_demo/tests/ui_seam_verify.js
 */
const assert = require("assert");
const path = require("path");
const DS = require(path.join(__dirname, "..", "..", "demo_ui", "datasource.js"));

// A stub WebSocket whose readyState is OPEN; the seam attaches on* handlers.
class StubWS {
  constructor() { this.readyState = 1; this.sent = []; }
  send(s) { this.sent.push(s); }
  close() {}
}

// The page's merge fn, transcribed from presentation.html (the §3 contract:
// active/flags transient; intent/decision/caps/items carry forward).
function mergeBrain(p, o) { const s = JSON.parse(JSON.stringify(p)); for (const k in o) s[k] = o[k]; return s; }
function merge(prev, f) {
  const s = JSON.parse(JSON.stringify(prev));
  if (f.title != null) s.title = f.title;
  if (f.narr != null) s.narr = f.narr;
  if (f.items) s.items = Object.assign(s.items || {}, f.items);
  if (f.eff) s.eff = f.eff;
  if (f.brains) for (const b in f.brains) s.brains[b] = mergeBrain(s.brains[b] || {}, f.brains[b]);
  for (const b of ["mgr", "a1", "a2", "conv"]) {
    if (!s.brains[b]) s.brains[b] = { intent: "", decision: "", active: false, flags: [] };
    if (!(f.brains && f.brains[b] && "active" in f.brains[b])) s.brains[b].active = false;
    if (!(f.brains && f.brains[b] && "flags" in f.brains[b])) s.brains[b].flags = [];
  }
  return s;
}

const base = {
  title: "", narr: "", items: { box1: [0, 0], sheet1: [0, 0], tube1: [0, 0] },
  eff: { a1: null, a2: null }, msgs: [],
  brains: {
    mgr: { intent: "idle", decision: "idle", active: false, flags: [] },
    a1: { intent: "idle", decision: "idle", active: false, flags: [] },
    a2: { intent: "idle", decision: "idle", active: false, flags: [] },
    conv: { intent: "idle", decision: "idle", active: false, flags: [] },
  },
};

let ws;
const src = DS.makeLiveSource({ url: "ws://x", base, merge, WS: function () { ws = new StubWS(); return ws; } });
const events = [];
src.onUpdate((k, i) => events.push([k, i]));
src.start();
ws.onopen();

// ---- feed the backend's exact frames (shapes from frames.py / pose_frame) ----
// 1) hello
src._handle({ type: "hello", scenario: "open-order", brains: ["mgr", "a1", "a2", "conv"], beats_total: 7 });
// 2) state — Order placed (mgr active)
src._handle({ type: "state", t: 1, beat: 0, title: "Order placed", narr: "User submitted an order.",
  brains: { mgr: { intent: "Interpret order", decision: "decompose", chain: 1, active: true, flags: [] } } });
// 3) message — dispatch
src._handle({ type: "message", from: "Orchestrator", to: "Arm1", text: "dispatch(move_to, home)", t: 2 });
// 4) state — arm executing (a1 active)
src._handle({ type: "state", t: 3, beat: 1, brains: { a1: { intent: "Execute move_to(home)", decision: "running…", chain: 4, active: true, flags: [] } } });
// 5) pose — affine-mapped items/eff (in the UI box)
src._handle({ type: "pose", t: 4, items: { box1: [0.3792, -0.3627] }, eff: { a1: [-0.3792, -0.3045], a2: null } });
// 6) message — report back
src._handle({ type: "message", from: "Arm1", to: "Orchestrator", text: "report(succeeded)", t: 5 });
// 7) state — Reported (mgr inactive again)
src._handle({ type: "state", t: 6, beat: 2, title: "Reported", narr: "Manager received the arm's report.",
  brains: { mgr: { intent: "Order complete", decision: "arm1 reported succeeded", chain: 5, active: false, flags: [] } } });

// ---- assertions ----
const states = src.states;
// seed idle + 3 state frames = 4 cumulative states
assert.strictEqual(states.length, 4, `expected 4 states, got ${states.length}`);

// beat 1 (Order placed): mgr active, carried decision
const s1 = states[1];
assert.strictEqual(s1.title, "Order placed");
assert.strictEqual(s1.brains.mgr.active, true);
assert.strictEqual(s1.brains.mgr.intent, "Interpret order");

// beat 2 (arm executing): a1 active; §3 — mgr.active reset to false (not in this frame)
const s2 = states[2];
assert.strictEqual(s2.brains.a1.active, true, "a1 should be active");
assert.strictEqual(s2.brains.mgr.active, false, "mgr.active must reset (transient §3)");
// intent carried forward for mgr
assert.strictEqual(s2.brains.mgr.intent, "Interpret order", "mgr.intent carries forward");

// pose mutated the CURRENT (latest) state's items/eff in place (no new state)
const cur = states[states.length - 1];
assert.deepStrictEqual(cur.items.box1, [0.3792, -0.3627], "pose item applied");
assert.deepStrictEqual(cur.eff.a1, [-0.3792, -0.3045], "pose eff applied");

// messages attach to whichever state is latest when they arrive (seam
// behavior); collect across all states and assert both were consumed.
const allMsgs = states.flatMap((s) => s.msgs || []);
assert.ok(allMsgs.some((m) => m[0] === "Orchestrator→Arm1" && m[1] === "dispatch(move_to, home)"),
  "dispatch message not consumed");
assert.ok(allMsgs.some((m) => m[0] === "Arm1→Orchestrator" && m[1] === "report(succeeded)"),
  "report message not consumed");

// final beat: Reported title fresh; mgr inactive
const s3 = states[3];
assert.strictEqual(s3.title, "Reported");
assert.strictEqual(s3.brains.mgr.active, false);

console.log("UI-seam verify PASS:", states.length, "states,", allMsgs.length, "messages, pose applied, §3 transients honored");
