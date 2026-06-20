/* MindsOS demo v10.6 — UI data-source seam (mock ↔ live WebSocket).
 * Pure (no DOM): browser global (window.DataSource) + node module.exports.
 *
 * Purpose: the dashboard's view layer reads a `states` array; this module decides
 * where that array comes from. MockDataSource builds it synchronously from the baked
 * scenario (today's behaviour, unchanged). LiveDataSource fills it from a backend
 * WebSocket speaking the protocol in confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md.
 * Going live is a constructor swap (?live=<wsurl>), not a view-layer rewrite.
 *
 * The frame/brains schema is the one in ROBOT_DEMO_PROTOTYPE_PLAN.md §4 (so the
 * MindsOS drop-in is transparent). See the contract doc for the authoritative spec.
 */
(function(){
  function clone(o){return JSON.parse(JSON.stringify(o));}

  // Build the cumulative `states` array from raw frames using the host's merge fn.
  // (mergeFn is the scenario's frame→state reducer, owned by the page so the scenario
  //  vocabulary stays in one place.)
  function buildStates(base, frames, mergeFn){
    const states=[]; let acc=clone(base);
    for(const f of frames){ acc=mergeFn(acc,f); states.push(clone(acc)); }
    return states;
  }

  // Normalize a server `state` frame into the per-beat shape mergeFn expects.
  // Server frame (contract): {type:'state', t, beat, items?, eff?, brains?, title?, narr?, msgs?}
  function normalizeFrame(f){
    const out={};
    if(f.beat!=null)  out.beat=f.beat;   // authoritative beat index (beat-strip counter; v0.24)
    if(f.title!=null) out.title=f.title;
    if(f.narr!=null)  out.narr=f.narr;
    if(f.items)       out.items=f.items;
    if(f.eff)         out.eff=f.eff;
    if(f.brains)      out.brains=f.brains;
    if(f.msgs)        out.msgs=f.msgs;
    return out;
  }

  // ---- MOCK: all beats present synchronously; playback driven by the page's own
  //      Play/Next timers. Commands are local no-ops. ----
  function makeMockSource(opts){
    const states=buildStates(opts.base, opts.frames, opts.merge);
    return {mode:'mock', isLive:false, status:'mock', states,
      start(){}, onUpdate(){}, sendCommand(){return false;}, stop(){}};
  }

  // ---- LIVE: WebSocket client. Frames arrive over time and append to `states`. ----
  // opts: {url, base, merge, WS?}  (WS injectable for tests; defaults to global WebSocket)
  function makeLiveSource(opts){
    const base=opts.base, merge=opts.merge;
    let acc=clone(base); if(!acc.msgs) acc.msgs=[];   // panels iterate msgs
    const states=[clone(acc)];           // seed one idle state so the UI renders at once
    const cbs=[]; let ws=null; let status='idle';
    function emit(kind,payload){ for(const cb of cbs) cb(kind,payload); }

    function applyState(frame){           // a beat-level cognitive snapshot → new UI state
      acc=merge(acc, normalizeFrame(frame));
      states.push(clone(acc)); emit('frame', states.length-1);
    }
    function applyPose(frame){            // high-freq pose update → mutate latest state in place
      const cur=states[states.length-1]; if(!cur) return;
      if(frame.items) cur.items=Object.assign(cur.items||{}, frame.items);
      if(frame.eff)   cur.eff=frame.eff;
      // keep `acc` in sync so the next cognitive frame builds on the latest pose
      if(frame.items) acc.items=Object.assign(acc.items||{}, frame.items);
      if(frame.eff)   acc.eff=frame.eff;
      emit('pose', states.length-1);
    }
    function applyMessage(m){             // Seam-B inter-brain log line → append to latest state
      const cur=states[states.length-1]; if(!cur) return;
      cur.msgs=(cur.msgs||[]).concat([[ (m.from||'?')+'→'+(m.to||'?'), m.text||'' ]]);
      emit('message', states.length-1);
    }
    function handle(msg){
      if(!msg||typeof msg!=='object') return;
      switch(msg.type){
        case 'hello':   emit('hello', msg); break;
        case 'state':   applyState(msg);    break;
        case 'pose':    applyPose(msg);     break;
        case 'message': applyMessage(msg);  break;
        case 'server_status': emit('server_status', msg); break;   // Seam-A vitals + liveness heartbeat (~3s)
        case 'server_event':  emit('server_event', msg);  break;   // Seam-A lifecycle/authz/audit event
        case 'resolve':       emit('resolve', msg);       break;   // Plan▸Resolve narrowing (per-brain, WS §5)
        case 'state_snapshot': emit('state_snapshot', msg); break; // reply to export_state (browser downloads)
        case 'import_result':  emit('import_result', msg);  break; // reply to import_state
        case 'reset':   states.length=0; acc=clone(base); if(!acc.msgs) acc.msgs=[]; states.push(clone(acc)); emit('reset'); break;
        default:        emit('unknown', msg);
      }
    }
    return {
      mode:'live', isLive:true, states,
      get status(){return status;},
      onUpdate(cb){ if(typeof cb==='function') cbs.push(cb); },
      start(){
        const WSImpl = opts.WS || (typeof WebSocket!=='undefined' ? WebSocket : null);
        if(!WSImpl){ status='error'; emit('error','no WebSocket available'); return; }
        try{ ws=new WSImpl(opts.url); }catch(e){ status='error'; emit('error',e); return; }
        ws.onopen   = ()=>{ status='open';   emit('open'); };
        ws.onclose  = ()=>{ status='closed'; emit('close'); };
        ws.onerror  = (e)=>{ status='error'; emit('error',e); };
        ws.onmessage= (ev)=>{ let m; try{ m=JSON.parse(typeof ev.data==='string'?ev.data:String(ev.data)); }catch(e){ return; } handle(m); };
      },
      // browser→server command: {type:'command', name, args}
      sendCommand(cmd){ if(ws && ws.readyState===1){ ws.send(JSON.stringify(cmd)); return true; } return false; },
      stop(){ if(ws){ try{ ws.close(); }catch(e){} } },
      _handle: handle    // test hook
    };
  }

  const API = {makeMockSource, makeLiveSource, buildStates, normalizeFrame};
  if(typeof module!=='undefined' && module.exports) module.exports = API;
  if(typeof window!=='undefined') window.DataSource = API;
})();
