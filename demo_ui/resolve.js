/* MindsOS demo v10.3a — relation-resolution narrowing (Plan ▸ Resolve subsection).
 * Pure (no DOM): browser globals + node module.exports. Mock per-brain/per-beat
 * resolution shaped like a future chain-artifact (MappingResult). The beats are
 * scripted, so this SHOWS the resolution — it is NOT a live solver.
 *
 * Cell state: 'cand' (candidate) | 'win' (chosen) | 'out' (excluded).
 * 3x3 cell index i -> (row, col) = (floor(i/3), i%3).  Tube is the reference object.
 */
const R_ALL = ()=>{const m={};for(let i=0;i<9;i++)m[i]='cand';return m;};
const R_SET = set=>{const m={};for(let i=0;i<9;i++)m[i]=set.includes(i)?'cand':'out';return m;};
const R_WIN = w=>{const m={};for(let i=0;i<9;i++)m[i]='out';m[w]='win';return m;};

// Beat 3 (Cooperative execution): "Box above Tube on Arm 2" + "Sheet @ center on Arm 1".
// Tube sits at center (idx 4); "above" → the row above (0,1,2); tie-break → directly above (1).
const RESOLVE = {
  mgr:{8:{acc:'#d98040', tube:4, item:'Box', clause:'Box above Tube → Arm 2',
    stages:[{cap:'all shelf cells (9)',            cells:R_ALL()},
            {cap:'clause “above Tube” → 3',         cells:R_SET([0,1,2])},
            {cap:'tie-break: directly above → 1',   cells:R_WIN(1)}], winner:1}},
  a2:{8:{acc:'#d98040', tube:4, item:'Box', clause:'Box above Tube',
    stages:[{cap:'all shelf cells (9)',            cells:R_ALL()},
            {cap:'above Tube → 3 candidates',       cells:R_SET([0,1,2])},
            {cap:'directly above → place ✓',        cells:R_WIN(1)}], winner:1}},
  a1:{8:{acc:'#3a8be0', tube:null, item:'Sheet', clause:'Sheet @ center', absolute:true,
    stages:[{cap:'all shelf cells (9)',            cells:R_ALL()},
            {cap:'term “center” → 1 cell ✓',        cells:R_WIN(4)}], winner:4}}
};
function buildResolve(brain, beat){const b=RESOLVE[brain];return (b&&b[beat])||null;}
// max stage count across the brains resolving on this beat (drives the animation length)
function resolveStageCount(beat){
  let m=0; for(const k in RESOLVE){const r=RESOLVE[k][beat]; if(r) m=Math.max(m,r.stages.length);}
  return m;
}

// render one stage as a compact 3x3 svg string (Plan ▸ Resolve grid)
function resolveGridSVG(res, stageIdx){
  const n=res.stages.length, si=Math.max(0,Math.min(n-1,stageIdx|0));
  const st=res.stages[si], acc=res.acc||'#8b98a5';
  const C=18, G=4, P=2, dim=3*C+2*G+2*P;
  let s=`<svg viewBox="0 0 ${dim} ${dim}" class="rgrid" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">`;
  for(let i=0;i<9;i++){
    const r=Math.floor(i/3), c=i%3, x=P+c*(C+G), y=P+r*(C+G), stt=st.cells[i]||'out';
    let fill,stroke,sw,op='';
    if(stt==='win'){fill=acc; stroke='#eafcff'; sw=1.6;}
    else if(stt==='cand'){fill=acc+'40'; stroke=acc; sw=1.3;}
    else {fill='#0e131a'; stroke='#2b333d'; sw=1; op=' opacity="0.5"';}
    s+=`<rect x="${x}" y="${y}" width="${C}" height="${C}" rx="2.5" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"${op}/>`;
    if(res.tube===i) s+=`<circle cx="${(x+C/2).toFixed(1)}" cy="${(y+C/2).toFixed(1)}" r="${(C*0.26).toFixed(1)}" fill="#b3598c" stroke="#0a0d12" stroke-width="1"/>`;
    if(stt==='win') s+=`<rect x="${(x+C*0.28).toFixed(1)}" y="${(y+C*0.28).toFixed(1)}" width="${(C*0.44).toFixed(1)}" height="${(C*0.44).toFixed(1)}" rx="1.5" fill="#cab43c" stroke="#0a0d12" stroke-width="1"/>`;
  }
  s+=`</svg>`; return s;
}

if(typeof module!=='undefined' && module.exports){
  module.exports = {RESOLVE, buildResolve, resolveStageCount, resolveGridSVG, R_ALL, R_SET, R_WIN};
}
