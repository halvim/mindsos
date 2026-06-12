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
 *   then open:  presentation_v10.html?live=ws://localhost:8765
 */
const PORT = +process.argv[2] || 8765;

// Each beat = the cognitive snapshot the backend would push as one `state` frame,
// plus the Seam-B messages emitted on the way in. brains[id] = {intent,chain,decision,flags,active,caps}.
const BEATS = [
  {title:"Order placed", narr:"User submits an order with a spatial relation: Box above Tube on Arm 2; Sheet at the center of Arm 1.",
   msgs:[["User","Orchestrator","place_order(A2: Box above Tube; A1: Sheet @ center)"]],
   brains:{mgr:{intent:"A2: Box above Tube · A1: Sheet @ center",chain:0,decision:"Decompose → resolve spatial relations to shelf cells",active:true}}},
  {title:"Ignorant start → don’t-know", narr:"The plan needs a skill no brain has: hand an item across the belt gap.",
   msgs:[["Orchestrator","Arm1","query_capabilities()"],["Arm1","Orchestrator","DONT_KNOW(handoff-via-belt)"],
         ["Orchestrator","Arm2","query_capabilities()"],["Arm2","Orchestrator","DONT_KNOW(handoff-via-belt)"]],
   brains:{mgr:{intent:"Plan the order",chain:2,decision:"Need handoff-via-belt → NOT FOUND",flags:["gap"],active:true},
           a1:{intent:"answer capability query",chain:1,decision:"report DONT_KNOW",flags:["gap"]},
           a2:{intent:"answer capability query",chain:1,decision:"report DONT_KNOW",flags:["gap"]}}},
  {title:"Learn by composition", narr:"User demonstrates the skill once; MindsOS captures it as a Pipeline → new composite capacity.",
   msgs:[["User","Arm1","demonstrate([place, stage, pick])"],["Demonstration","L2","Pipeline → promoted-pipelines"]],
   brains:{mgr:{intent:"Acquire missing capability",chain:3,decision:"Register composite from demonstration",flags:["learn"],active:true},
           a1:{intent:"Learn handoff-via-belt",chain:3,decision:"captured Pipeline → composite (Local)",flags:["learn"],caps:[["move/grip","primitive"],["handoff-via-belt","learned"]],active:true},
           conv:{intent:"Learn staging",chain:2,decision:"stage-at-position learned",caps:[["advance/reverse","primitive"],["stage-at-position","learned"]],active:true}}},
  {title:"Cooperative execution", narr:"The brains run the new skill: belt hands Box and Tube to Arm 2; Arm 1 sets the Sheet at its center.",
   items:{box1:[0.70,-0.62], tube1:[0.70,-0.77], sheet1:[-0.70,-0.77]}, eff:{a1:[-0.70,-0.77],a2:[0.70,-0.62]},
   msgs:[["Orchestrator","Arm1","dispatch(place_at_cell, Sheet→A1 c)"],["Orchestrator","Conveyor","dispatch(advance→0.2)"],
         ["Orchestrator","Arm2","dispatch(place Box @ A2 r0c1, above Tube)"],["Arm2","Orchestrator","SUCCESS(A2: Box above Tube)"]],
   brains:{mgr:{intent:"Execute placements",chain:5,decision:"resolve 'Box above Tube' → A2 cell (r0,c1); dispatch",active:true},
           a1:{intent:"Place Sheet on its shelf",chain:5,decision:"place Sheet @ A1 center ✓",caps:[["move/grip","primitive"],["handoff-via-belt","learned"],["place-at-cell","learned"]],active:true},
           a2:{intent:"Place Box above Tube",chain:5,decision:"place Box @ A2(r0,c1), above Tube ✓",caps:[["move/grip","primitive"],["handoff-via-belt","inherited"],["place-at-cell","inherited"]],active:true},
           conv:{intent:"Bridge the gap",chain:4,decision:"advance → stage at x=0.2",caps:[["advance/reverse","primitive"],["stage-at-position","learned"]],active:true}}},
  {title:"Transfer + embodiment gate", narr:"The learned skill is promoted Local→Global; Arm 2 inherits it but its jaw is gated from the suction-only Sheet skill.",
   msgs:[["Arm1","Global","promote(handoff-via-belt)"],["Global","Arm2","capability available"],["Arm2","Orchestrator","gate: pick-Sheet requires suction"]],
   brains:{mgr:{intent:"Share capability fleet-wide",chain:5,decision:"promote Local→Global; gate pick-Sheet@Arm2",flags:["promo","gate"],active:true},
           a1:{intent:"Promote skill",chain:5,decision:"promote(handoff-via-belt) → Global",flags:["promo"]},
           a2:{intent:"Inherit + check feasibility",chain:4,decision:"inherited handoff; pick-Sheet GATED (no suction)",flags:["promo","gate"],caps:[["handoff-via-belt","inherited"],["pick-Sheet","GATED"]],active:true}}},
  {title:"Degradation → replan", narr:"Arm 2’s wrist faults mid-order; it self-diagnoses, the gap reappears, the Orchestrator replans around the loss.",
   eff:{a1:null,a2:null},
   msgs:[["Arm2","Orchestrator","FAULT(wrist) → withdraw fine-grasp"],["Orchestrator","Conveyor","dispatch(reverse→re-stage)"]],
   brains:{mgr:{intent:"Recover from fault",chain:4,decision:"replan(): reroute via Arm1 + conveyor",flags:["fault","gap"],active:true},
           a2:{intent:"Self-diagnose",chain:1,decision:"FAULT(wrist) → withdraw fine-grasp",flags:["fault","gap"],caps:[["handoff-via-belt","inherited"],["fine-grasp","FAULT"]],active:false},
           a1:{intent:"Absorb rerouted work",chain:4,decision:"accept reroute",active:true},
           conv:{intent:"Re-stage",chain:4,decision:"reverse → re-stage for Arm 1",active:true}}},
  {title:"Trace recap", narr:"The run replayed: gap → learned → shared → gated → recovered — reasoning visible throughout.",
   msgs:[["Orchestrator","L2","retain episode (episodic_memories)"]],
   brains:{mgr:{intent:"Retain episode",chain:5,decision:"episode retained: gap→learned→promoted→gated→recovered",flags:["learn","promo","gate","fault"],active:false},
           a2:{intent:"degraded",chain:5,decision:"fine-grasp pending repair",active:false}}}
];

let WebSocketServer;
try { ({ WebSocketServer } = require("ws")); }
catch(e){ console.error("This dev server needs the 'ws' package:  npm i ws"); process.exit(1); }

const wss = new WebSocketServer({ port: PORT });
console.log(`mock brains WS listening on ws://localhost:${PORT}  (open presentation_v10.html?live=ws://localhost:${PORT})`);

wss.on("connection", (ws) => {
  ws.send(JSON.stringify({ type:"hello", scenario:"open-order", brains:["mgr","a1","a2","conv"], beats_total:BEATS.length }));
  let i = 0, timer = null;
  function emitBeat(){
    if(i >= BEATS.length){ stop(); return; }
    const b = BEATS[i++];
    for(const m of (b.msgs||[])) ws.send(JSON.stringify({ type:"message", from:m[0], to:m[1], text:m[2] }));
    const { msgs, ...stateFields } = b;                 // a `state` frame is the beat minus its msgs
    ws.send(JSON.stringify(Object.assign({ type:"state", t:Date.now(), beat:i-1 }, stateFields)));
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
