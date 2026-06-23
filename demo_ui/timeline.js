/* MindsOS demo v0.24 — demo-timeline builder (pure; node + browser, no DOM).
 * Turns the scripted `frames` (sparse per-beat deltas) into an ordered, CHANGE-ONLY
 * transcript of every message + brain section/subsection change, tagged by source +
 * section, for the beat-timeline modal. Sanitized data in → sanitized rows out
 * (IP policy B): the frames already carry behavior-level text; this only reorganizes.
 *
 * Source keys:  seamA | seamB | user | mgr | a1 | a2 | conv
 * Section keys: task | plan | pipeline | cap          (brain-card sections)
 * Subsection keys: resolve                            (Plan ▸ Resolve sub-card)
 * Message/server rows carry section=null (governed by the Sources filter only).
 */
(function(){
  // classify a message party "From→To" → source key
  function tlMsgSource(party){
    const from=((party||"").split("→")[0]||"").trim();
    return (from==="User"||from==="Demonstration") ? "user" : "seamB";
  }
  // a brain's per-beat decision → section key. Reuses the dashboard's flag→section
  // routing (fault→Task, learn→Pipeline, promo/gate→Capabilities); beat-0 order
  // intake = Task; default = Plan. Categorization of REAL text, nothing invented.
  function tlDecisionSection(brain, beatIdx){
    const f=(brain&&brain.flags)||[];
    if(f.indexOf("learn")>=0) return "pipeline";
    if(f.indexOf("promo")>=0||f.indexOf("gate")>=0) return "cap";
    if(f.indexOf("fault")>=0) return "task";
    if(beatIdx===0) return "task";
    return "plan";
  }
  // Build the ordered timeline. opts:
  //   serverByBeat {beatIdx:[{text}]}  — Seam A events (representative in mock; [] in live until emitted)
  //   resolveFor(brainKey, beatIdx)    — returns a resolve obj {clause,...} or null
  function buildTimeline(frames, opts){
    opts=opts||{};
    const serverByBeat=opts.serverByBeat||{};
    const resolveFor=opts.resolveFor||function(){return null;};
    const BR=["mgr","a1","a2","conv"];
    const out=[];
    for(let i=0;i<frames.length;i++){
      const f=frames[i]||{}, entries=[];
      if(Array.isArray(f.events)){
        // v0.26 — explicit ordered event log: emit verbatim, fully chronological. Each event:
        // {source, party?, section?, sub?, text}. source ∈ seamA|seamB|user|mgr|a1|a2|conv.
        // Sanitized strings in → sanitized rows out (the frame already carries policy-B text).
        for(const e of (f.events||[])){
          entries.push({source:e.source, party:e.party||null,
                        section:e.section||null, sub:e.sub||null, text:e.text});
        }
      } else {
        // legacy derivation (sparse per-beat deltas): msgs → brain changes → server.
        // 1) messages (Seam B / User) — in emission order
        for(const m of (f.msgs||[])){
          entries.push({source:tlMsgSource(m[0]), party:m[0], section:null, sub:null, text:m[1]});
        }
        // 2) brain changes — frames are sparse deltas, so iterating them IS change-only
        for(const k of BR){
          const b=f.brains&&f.brains[k]; if(!b) continue;
          const r=resolveFor(k,i);
          if(r){ entries.push({source:k, party:null, section:"plan", sub:"resolve",
                               text:(r.clause||"resolution")+" — narrows to the winning cell"}); }
          if(b.caps){ for(const c of b.caps){ if(c[1] && c[1]!=="primitive"){
            entries.push({source:k, party:null, section:"cap", sub:null, text:c[0]+" ("+c[1]+")"}); } } }
          if(b.decision){ entries.push({source:k, party:null, section:tlDecisionSection(b,i), sub:null, text:b.decision}); }
        }
        // 3) Seam A (server) events for this beat
        for(const e of (serverByBeat[i]||[])){ entries.push({source:"seamA", party:null, section:null, sub:null, text:e.text}); }
      }
      // group key = cbeat (0-based global storyline beat) when present, else legacy beat/index
      const cb=(f.cbeat!=null?f.cbeat:(f.beat!=null?f.beat:i));
      out.push({beat:cb, title:f.title||("Beat "+(cb+1)), entries});
    }
    return out;
  }
  const API={buildTimeline, tlMsgSource, tlDecisionSection};
  if(typeof module!=='undefined'&&module.exports) module.exports=API;
  if(typeof window!=='undefined') window.Timeline=API;
})();
