#!/usr/bin/env node
/* MindsOS demo — reference mock WS server for the v10 dashboard live mode.
 *
 * Implements the SERVER→BROWSER side of ROBOT_DEMO_WS_CONTRACT.md by replaying the
 * 7 scripted beats as live `hello`/`message`/`state` frames, and accepts the
 * browser→server `command` messages. It exists so the dashboard's ?live= path can be
 * exercised without the real backend, AND as a worked example of the exact frame
 * shapes the MindsOS backend must emit. THROWAWAY / dev-only — not the real backend.
 *
 *   npm i ws && node mock_ws_server.js [port]      (default 8765)
 *   then open:  presentation.html?live=ws://localhost:8765
 */
const PORT = +process.argv[2] || 8765;

// Each beat = the cognitive snapshot the backend would push as one `state` frame,
// plus the Seam-B messages emitted on the way in. brains[id] = {intent,chain,decision,flags,active,caps}.
const BEATS = [
  {title:"Order placed", narr:"User submits an order with a spatial relation: Box above Tube on Arm 2; Sheet at the center of Arm 1.",
   msgs:[["User","Orchestrator","Order: Box above Tube; Sheet at center"]],
   brains:{mgr:{intent:"A2: Box above Tube · A1: Sheet @ center",chain:0,decision:"Break down the order, work out where each item goes",active:true}}},
  {title:"Ignorant start → don’t-know", narr:"The plan needs a skill no brain has: hand an item across the belt gap.",
   msgs:[["Orchestrator","Arm1","What can you do?"],["Arm1","Orchestrator","Dont know how to hand across the gap"],
         ["Orchestrator","Arm2","What can you do?"],["Arm2","Orchestrator","Dont know how to hand across the gap"]],
   brains:{mgr:{intent:"Plan the order",chain:2,decision:"Need a way to hand items across the gap, dont know how",flags:["gap"],active:true},
           a1:{intent:"Answer: what can I do?",chain:1,decision:"Report: dont know",flags:["gap"]},
           a2:{intent:"Answer: what can I do?",chain:1,decision:"Report: dont know",flags:["gap"]}}},
  {title:"Learn by demonstration", narr:"User demonstrates the skill once; the system captures it as a new, reusable skill.",
   msgs:[["User","Arm1","Demonstrate: place, stage, pick"],["Demonstration","Library","Saved as a new skill"]],
   brains:{mgr:{intent:"Learn the missing skill",chain:3,decision:"Save the new skill from the demonstration",flags:["learn"],active:true},
           a1:{intent:"Learn the hand-off",chain:3,decision:"Captured the demo: new skill",flags:["learn"],caps:[["move/grip","primitive"],["hand-off","learned"]],active:true},
           conv:{intent:"Learn staging",chain:2,decision:"Learned to stage on the belt",caps:[["advance/reverse","primitive"],["stage-on-belt","learned"]],active:true}}},
  {title:"Cooperative execution", narr:"The brains run the new skill: belt hands Box and Tube to Arm 2; Arm 1 sets the Sheet at its center.",
   items:{box1:[0.70,-0.62], tube1:[0.70,-0.77], sheet1:[-0.70,-0.77]}, eff:{a1:[-0.70,-0.77],a2:[0.70,-0.62]},
   msgs:[["Orchestrator","Arm1","Place Sheet in Arm 1 center"],["Orchestrator","Conveyor","Advance the belt"],
         ["Orchestrator","Arm2","Place Box above the Tube"],["Arm2","Orchestrator","Done: Box above Tube"]],
   brains:{mgr:{intent:"Execute placements",chain:5,decision:"Work out Box above Tube: Arm 2 top-center; go",active:true},
           a1:{intent:"Place Sheet on its shelf",chain:5,decision:"Placed Sheet in Arm 1 center ✓",caps:[["move/grip","primitive"],["hand-off","learned"],["place-in-cell","learned"]],active:true},
           a2:{intent:"Place Box above Tube",chain:5,decision:"Placed Box above the Tube ✓",caps:[["move/grip","primitive"],["hand-off","inherited"],["place-in-cell","inherited"]],active:true},
           conv:{intent:"Bridge the gap",chain:4,decision:"Advance, stage on the belt",caps:[["advance/reverse","primitive"],["stage-on-belt","learned"]],active:true}}},
  {title:"Share + body limits", narr:"The learned skill is shared across the fleet; Arm 2 receives it but its jaw is blocked from the suction-only Sheet skill.",
   msgs:[["Arm1","Fleet","Share the hand-off skill"],["Fleet","Arm2","Skill available"],["Arm2","Orchestrator","Blocked: pick-sheet needs suction"]],
   brains:{mgr:{intent:"Share the skill fleet-wide",chain:5,decision:"Share the skill; block Arm 2 pick-sheet (wrong gripper)",flags:["promo","gate"],active:true},
           a1:{intent:"Share the skill",chain:5,decision:"Shared the hand-off fleet-wide",flags:["promo"]},
           a2:{intent:"Receive + check my body",chain:4,decision:"Received the hand-off; pick-sheet blocked (no suction)",flags:["promo","gate"],caps:[["hand-off","inherited"],["pick-sheet","GATED"]],active:true}}},
  {title:"Degradation → replan", narr:"Arm 2’s wrist faults mid-order; it self-diagnoses, the gap reappears, the Orchestrator replans around the loss.",
   eff:{a1:null,a2:null},
   msgs:[["Arm2","Orchestrator","Wrist fault: withdraw fine-grasp"],["Orchestrator","Conveyor","Reverse + re-stage"]],
   brains:{mgr:{intent:"Recover from fault",chain:4,decision:"Re-plan: reroute via Arm 1 + conveyor",flags:["fault","gap"],active:true},
           a2:{intent:"Self-diagnose",chain:1,decision:"Wrist fault: withdraw fine-grasp",flags:["fault","gap"],caps:[["hand-off","inherited"],["fine-grasp","FAULT"]],active:false},
           a1:{intent:"Absorb rerouted work",chain:4,decision:"Accept the reroute",active:true},
           conv:{intent:"Re-stage",chain:4,decision:"reverse → re-stage for Arm 1",active:true}}},
  {title:"Trace recap", narr:"The run replayed: gap, learned, shared, blocked, recovered — reasoning visible throughout.",
   msgs:[["Orchestrator","Library","Remember this run"]],
   brains:{mgr:{intent:"Remember this run",chain:5,decision:"Run remembered: didnt-know, learned, shared, blocked, recovered",flags:["learn","promo","gate","fault"],active:false},
           a2:{intent:"degraded",chain:5,decision:"fine-grasp pending repair",active:false}}}
];

// Plan▸Resolve narrowing frames (WS §5), emitted on the cooperative-execution beat (beat 3).
// Sanitized behavior-level cap labels (policy B). Mirrors demo_ui/resolve.js — `acc` (per-brain
// accent) + `absolute` are injected UI-side and are NOT on the wire (a1 omits `tube` → UI infers
// absolute). Cell state per 3×3 index: "cand" | "win" | "out".
const rcAll = () => { const m={}; for(let i=0;i<9;i++) m[i]="cand"; return m; };
const rcSet = s => { const m={}; for(let i=0;i<9;i++) m[i]=s.includes(i)?"cand":"out"; return m; };
const rcWin = w => { const m={}; for(let i=0;i<9;i++) m[i]="out"; m[w]="win"; return m; };
const RESOLVE_FRAMES = {
  3: [
    { brain:"mgr", clause:"Box above Tube → Arm 2", item:"Box", tube:4,
      stages:[{cap:"all shelf cells (9)",          cells:rcAll()},
              {cap:"clause “above Tube” → 3",       cells:rcSet([0,1,2])},
              {cap:"tie-break: directly above → 1", cells:rcWin(1)}], winner:1 },
    { brain:"a2", clause:"Box above Tube", item:"Box", tube:4,
      stages:[{cap:"all shelf cells (9)",       cells:rcAll()},
              {cap:"above Tube → 3 candidates",  cells:rcSet([0,1,2])},
              {cap:"directly above → place ✓",   cells:rcWin(1)}], winner:1 },
    { brain:"a1", clause:"Sheet @ center", item:"Sheet",
      stages:[{cap:"all shelf cells (9)",      cells:rcAll()},
              {cap:"term “center” → 1 cell ✓", cells:rcWin(4)}], winner:4 }
  ]
};

let WebSocketServer;
try { ({ WebSocketServer } = require("ws")); }
catch(e){ console.error("This dev server needs the 'ws' package:  npm i ws"); process.exit(1); }

const wss = new WebSocketServer({ port: PORT });
console.log(`mock brains WS listening on ws://localhost:${PORT}  (open presentation.html?live=ws://localhost:${PORT})`);

wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ type:"hello", scenario:"open-order", brains:["mgr","a1","a2","conv"], beats_total:BEATS.length }));
  let i = 0, timer = null;
  function emitBeat(){
    if(i >= BEATS.length){ stop(); return; }
    const b = BEATS[i++];
    // STATE FIRST, then this beat's messages — so messages group with THIS beat's state (matches
    // the real DM-4 backend + the baked `frames` where msgs are inline in the beat). Sending
    // messages before the state would attach them to the previous beat's state.
    const { msgs, ...stateFields } = b;                 // a `state` frame is the beat minus its msgs
    ws.send(JSON.stringify(Object.assign({ type:"state", t:Date.now(), beat:i-1, cbeat:i-1 }, stateFields)));
    for(const m of (b.msgs||[])) ws.send(JSON.stringify({ type:"message", from:m[0], to:m[1], text:m[2] }));
    const rf = RESOLVE_FRAMES[i-1];                     // per-brain Plan▸Resolve frames for this beat
    if(rf) for(const f of rf) ws.send(JSON.stringify(Object.assign({ type:"resolve", t:Date.now() }, f)));
  }
  function play(){ if(timer) return; timer = setInterval(emitBeat, 2200); }
  function stop(){ if(timer){ clearInterval(timer); timer=null; } }
  ws.on("message", (raw) => {
    let cmd; try { cmd = JSON.parse(raw.toString()); } catch(e){ return; }
    const name = cmd && cmd.name;
    if(name==="place_order"){ i=0; emitBeat(); play(); }
    else if(name==="play"){ play(); }
    else if(name==="pause"){ stop(); }
    else if(name==="step"){ emitBeat(); }
    else if(name==="reset"){ stop(); i=0; ws.send(JSON.stringify({ type:"reset" })); }
    else if(name==="sort"||name==="teach"){ /* acknowledged; real backend would act */ }
  });
  ws.on("close", stop);
});
