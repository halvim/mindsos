/* MindsOS demo v10 — curated per-brain reasoning subgraphs.
 * Pure (no DOM): usable in the browser (globals) and in node (module.exports).
 * Shape mimics what a future WS `state` frame would carry as brains[b].graph,
 * so the view layer is reusable once wired to live data.
 *
 * Node kinds: prim | composite | affordance | world | robot | gap | episode
 * Node/edge states: default | absent | new | active | inherited | gated | grey | global
 */

const KIND_COL = {
  prim:'#7f8c99', composite:'#5ec8d8', affordance:'#cab43c',
  world:'#b98cf0', robot:'#9fb0bd', gap:'#e5534b', episode:'#66bf72'
};
const STATE = {
  default:{op:1,   dash:0,  stroke:null},
  active: {op:1,   dash:0,  stroke:'#e6edf3'},
  new:    {op:1,   dash:0,  stroke:'#66bf72', glow:'#66bf72'},
  inherited:{op:1, dash:0,  stroke:'#e0b341', glow:'#e0b341'},
  gated:  {op:1,   dash:4,  stroke:'#e5534b', glow:'#e5534b'},
  grey:   {op:.35, dash:0,  stroke:'#566270'},
  global: {op:1,   dash:0,  stroke:'#e0b341', ring:'#e0b341'},
  absent: {op:.4,  dash:5,  stroke:'#e5534b'}
};

// ---- per-brain node templates (fixed layout; states applied per beat) ----
const GRAPH = {
  mgr:{
    nodes:{
      world:{label:'world-model', kind:'world', x:50, y:13},
      a1:{label:'Arm1 caps',  kind:'robot', x:20, y:42},
      a2:{label:'Arm2 caps',  kind:'robot', x:80, y:42},
      conv:{label:'Conv caps',kind:'robot', x:50, y:66},
      skill:{label:'handoff-via-belt', kind:'composite', x:50, y:42}
    },
    edges:[['world','a1','link'],['world','a2','link'],['world','conv','link']]
  },
  a1:{
    nodes:{
      mg:{label:'move/grip', kind:'prim', x:50, y:80},
      suction:{label:'suction', kind:'affordance', x:85, y:80},
      place:{label:'place', kind:'prim', x:18, y:54},
      stage:{label:'stage', kind:'prim', x:50, y:54},
      pick:{label:'pick',  kind:'prim', x:82, y:54},
      handoff:{label:'handoff-via-belt', kind:'composite', x:50, y:20},
      placecell:{label:'place-at-cell', kind:'composite', x:16, y:24}
    },
    edges:[['handoff','place','partof'],['handoff','stage','partof'],
           ['handoff','pick','partof'],['placecell','mg','partof']]
  },
  a2:{
    nodes:{
      mg:{label:'move/grip', kind:'prim', x:30, y:80},
      jaw:{label:'jaw', kind:'affordance', x:75, y:80},
      handoff:{label:'handoff-via-belt', kind:'composite', x:28, y:30},
      placecell:{label:'place-at-cell', kind:'composite', x:70, y:48},
      pickSheet:{label:'pick-Sheet', kind:'composite', x:74, y:22},
      suctionReq:{label:'needs suction', kind:'affordance', x:74, y:4},
      finegrasp:{label:'fine-grasp', kind:'affordance', x:28, y:8}
    },
    edges:[['pickSheet','suctionReq','requires'],['handoff','finegrasp','partof']]
  },
  conv:{
    nodes:{
      adv:{label:'advance/reverse', kind:'prim', x:50, y:78},
      stagepos:{label:'stage-at-position', kind:'composite', x:50, y:30}
    },
    edges:[['stagepos','adv','partof']]
  }
};

// ---- per-beat: which nodes are visible and each node/edge state ----
// vis: list of node ids shown.  ns: node-state overrides.  es: edge-state map "a>b".
const BEATS = {
  mgr:[
    {vis:['world','a1','a2','conv']},                                          // 0 order
    {vis:['world','a1','a2','conv','skill'], ns:{skill:'absent'}},             // 1 dont-know
    {vis:['world','a1','a2','conv','skill'], ns:{skill:'new'}, es:{'a1>skill':'new'}},// 2 learn
    {vis:['world','a1','a2','conv','skill'], ns:{skill:'active'}, es:{'a1>skill':'active'}}, // 3 exec
    {vis:['world','a1','a2','conv','skill'], ns:{skill:'global'}, es:{'a1>skill':'active','a2>skill':'new'}}, // 4 transfer
    {vis:['world','a1','a2','conv','skill'], ns:{a2:'grey',skill:'global'}, es:{'a2>skill':'grey'}},          // 5 degrade
    {vis:['world','a1','a2','conv','skill'], ns:{skill:'global',a2:'grey'}}    // 6 recap
  ],
  a1:[
    {vis:['mg','suction']},
    {vis:['mg','suction','handoff','place','stage','pick'], ns:{handoff:'absent',place:'grey',stage:'grey',pick:'grey'}},
    {vis:['mg','suction','handoff','place','stage','pick'], ns:{handoff:'new'}, es:{'handoff>place':'new','handoff>stage':'new','handoff>pick':'new'}},
    {vis:['mg','suction','handoff','place','stage','pick','placecell'], ns:{handoff:'active',placecell:'new'}},
    {vis:['mg','suction','handoff','place','stage','pick','placecell'], ns:{handoff:'global'}},
    {vis:['mg','suction','handoff','place','stage','pick','placecell'], ns:{handoff:'active'}},
    {vis:['mg','suction','handoff','place','stage','pick','placecell'], ns:{handoff:'global'}}
  ],
  a2:[
    {vis:['mg','jaw']},
    {vis:['mg','jaw']},
    {vis:['mg','jaw']},
    {vis:['mg','jaw','placecell'], ns:{placecell:'inherited'}},
    {vis:['mg','jaw','handoff','placecell','pickSheet','suctionReq'], ns:{handoff:'inherited',pickSheet:'gated',suctionReq:'gated'}, es:{'pickSheet>suctionReq':'gated'}},
    {vis:['mg','jaw','handoff','placecell','pickSheet','suctionReq','finegrasp'], ns:{handoff:'inherited',finegrasp:'grey',pickSheet:'gated',suctionReq:'gated'}, es:{'pickSheet>suctionReq':'gated','handoff>finegrasp':'grey'}},
    {vis:['mg','jaw','handoff','placecell','finegrasp'], ns:{handoff:'inherited',finegrasp:'grey'}}
  ],
  conv:[
    {vis:['adv']},
    {vis:['adv']},
    {vis:['adv','stagepos'], ns:{stagepos:'new'}, es:{'stagepos>adv':'new'}},
    {vis:['adv','stagepos'], ns:{stagepos:'active'}},
    {vis:['adv','stagepos']},
    {vis:['adv','stagepos'], ns:{stagepos:'active'}},
    {vis:['adv','stagepos']}
  ]
};

// Build a concrete subgraph {nodes:[...], edges:[...]} for (brain, beat).
function buildSub(brain, beat){
  const G = GRAPH[brain]; const B = (BEATS[brain]||[])[beat] || (BEATS[brain]||[]).slice(-1)[0] || {vis:[]};
  const vis = new Set(B.vis||[]); const ns = B.ns||{}; const es = B.es||{};
  const nodes = [];
  for(const id of (B.vis||[])){
    const n = G.nodes[id]; if(!n) continue;
    nodes.push({id, label:n.label, kind:n.kind, x:n.x, y:n.y, state:ns[id]||'default'});
  }
  const edges = [];
  for(const [a,b,kind] of G.edges){
    if(!vis.has(a)||!vis.has(b)) continue;
    edges.push({a,b,kind, state:es[a+'>'+b]||'default',
      ax:G.nodes[a].x, ay:G.nodes[a].y, bx:G.nodes[b].x, by:G.nodes[b].y});
  }
  // cross-robot copy edge on the mgr graph (a1->a2) when learned+promoted
  if(brain==='mgr' && (es['a2>skill'])){
    edges.push({a:'a1',b:'a2',kind:'copy',state:es['a2>skill']==='grey'?'grey':'copy',
      ax:G.nodes.a1.x, ay:G.nodes.a1.y, bx:G.nodes.a2.x, by:G.nodes.a2.y});
  }
  return {brain, beat, nodes, edges};
}

// Pure SVG renderer for a subgraph. Returns an <svg> string.
function graphSVG(sub, opt){
  opt = opt||{}; const W=100, H=90;
  const px=x=>(x/100*W).toFixed(1), py=y=>(y/100*H).toFixed(1);
  let s = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" class="gsvg" preserveAspectRatio="xMidYMid meet">`;
  s += `<defs><marker id="ga" markerWidth="6" markerHeight="6" refX="5" refY="2" orient="auto"><path d="M0,0 L5,2 L0,4 Z" fill="#7f8c99"/></marker>`+
       `<marker id="gar" markerWidth="6" markerHeight="6" refX="5" refY="2" orient="auto"><path d="M0,0 L5,2 L0,4 Z" fill="#e5534b"/></marker></defs>`;
  // edges first
  for(const e of sub.edges){
    const st = STATE[e.state]||STATE.default;
    const col = e.state==='gated' ? '#e5534b' : e.state==='new' ? '#66bf72' :
                e.state==='inherited'||e.kind==='copy' ? '#e0b341' :
                e.state==='grey' ? '#566270' : (e.kind==='requires'?'#cab43c':'#46505c');
    const dash = (e.kind==='requires'||e.state==='gated'||e.kind==='copy') ? ' stroke-dasharray="3 2"' : (st.dash?` stroke-dasharray="${st.dash} ${st.dash}"`:'');
    const mk = e.state==='gated' ? 'url(#gar)' : (e.kind==='partof'?'url(#ga)':'');
    s += `<line x1="${px(e.ax)}" y1="${py(e.ay)}" x2="${px(e.bx)}" y2="${py(e.by)}" stroke="${col}" stroke-width="1"${dash} opacity="${st.op}"${mk?` marker-end="${mk}"`:''}/>`;
  }
  // nodes
  for(const n of sub.nodes){
    const st = STATE[n.state]||STATE.default;
    const base = KIND_COL[n.kind]||'#9fb0bd';
    const stroke = st.stroke||base;
    const x=+px(n.x), y=+py(n.y);
    const cls = 'gn' + (n.state==='new'?' gn-new':'') + (n.state==='absent'?' gn-absent':'') + (n.state==='gated'?' gn-gated':'');
    if(st.ring) s += `<circle cx="${x}" cy="${y}" r="6.4" fill="none" stroke="${st.ring}" stroke-width="0.6" opacity="0.8"/>`;
    if(n.kind==='affordance'){
      s += `<g class="${cls}" opacity="${st.op}"><polygon points="${x},${(y-4.2).toFixed(1)} ${(x+4.2).toFixed(1)},${y} ${x},${(y+4.2).toFixed(1)} ${(x-4.2).toFixed(1)},${y}" fill="${base}22" stroke="${stroke}" stroke-width="0.8"${st.dash?` stroke-dasharray="${st.dash*0.4} ${st.dash*0.4}"`:''}/></g>`;
    } else if(n.kind==='world'||n.kind==='episode'||n.kind==='gap'){
      s += `<g class="${cls}" opacity="${st.op}"><circle cx="${x}" cy="${y}" r="4.4" fill="${base}22" stroke="${stroke}" stroke-width="0.8"${st.dash?` stroke-dasharray="${st.dash*0.4} ${st.dash*0.4}"`:''}/></g>`;
    } else {
      s += `<g class="${cls}" opacity="${st.op}"><rect x="${(x-5).toFixed(1)}" y="${(y-3.2).toFixed(1)}" width="10" height="6.4" rx="1.6" fill="${base}22" stroke="${stroke}" stroke-width="0.8"${st.dash?` stroke-dasharray="${st.dash*0.4} ${st.dash*0.4}"`:''}/></g>`;
    }
    const fs = 2.9;
    s += `<text x="${x}" y="${(y+7.6).toFixed(1)}" font-size="${fs}" fill="#c7d0db" text-anchor="middle" opacity="${Math.max(st.op,.6)}">${esc(n.label)}</text>`;
  }
  s += `</svg>`;
  return s;
}
function esc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

if(typeof module!=='undefined' && module.exports){
  module.exports = {GRAPH, BEATS, buildSub, graphSVG, KIND_COL, STATE};
}
