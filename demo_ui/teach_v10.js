/* MindsOS demo v10 — Teach-tab curation model (mock "Local KL").
 * Pure data + logic (no DOM). Shaped like the future WS teach/inspect/state
 * payloads so the view layer is reusable once wired to live data (Phase D).
 *
 * Position term = a named set of cells over the 3x3 (absolute), or a relational
 * offset.  v10.2a covers absolute cell-set terms (teach by example / by
 * composition).  Retire + Global override land in v10.2b.
 */

// 3x3 cell labels (row, col) -> human name, for inspect output
const CELL_NAME = [['top-left','top','top-right'],['left','center','right'],
                   ['bottom-left','bottom','bottom-right']];

// ---- seed substrate ----
function seedTerms(){
  return [
    {name:'top-left',    scope:'builtin', kind:'term', cells:[[0,0]]},
    {name:'top',         scope:'builtin', kind:'term', cells:[[0,1]]},
    {name:'top-right',   scope:'builtin', kind:'term', cells:[[0,2]]},
    {name:'left',        scope:'builtin', kind:'term', cells:[[1,0]]},
    {name:'center',      scope:'builtin', kind:'term', cells:[[1,1]]},
    {name:'right',       scope:'builtin', kind:'term', cells:[[1,2]]},
    {name:'bottom-left', scope:'builtin', kind:'term', cells:[[2,0]]},
    {name:'bottom',      scope:'builtin', kind:'term', cells:[[2,1]]},
    {name:'bottom-right',scope:'builtin', kind:'term', cells:[[2,2]]},
    // a Global (admin-authored) term — the demo overrides this with a Local shadow
    {name:'corner-pack', scope:'Global',  kind:'term', cells:[[0,0],[0,2],[2,0],[2,2]]}
  ];
}
function seedComposites(){
  return [
    {name:'place-at-cell',    scope:'builtin', kind:'composite', steps:['move-to','grip','place'],     dependents:['handoff-via-belt']},
    {name:'handoff-via-belt', scope:'Local',   kind:'composite', steps:['place','stage','pick'],       dependents:[]},
    {name:'stage-at-position',scope:'Local',   kind:'composite', steps:['advance/reverse','hold-at-x'], dependents:['handoff-via-belt']}
  ];
}

// ---- helpers ----
const cellKey = c => c[0]+','+c[1];
function unionCells(lists){
  const seen=new Set(), out=[];
  for(const cells of lists) for(const c of (cells||[])){ const k=cellKey(c); if(!seen.has(k)){seen.add(k); out.push([c[0],c[1]]);} }
  out.sort((a,b)=> a[0]-b[0] || a[1]-b[1]);
  return out;
}
// compose a new cell-set from existing term names
function composeCells(termNames, terms){
  const byName = Object.fromEntries(terms.map(t=>[t.name,t]));
  return unionCells(termNames.map(n=> byName[n] ? byName[n].cells : []));
}
function cellsLabel(cells){
  if(!cells||!cells.length) return '(none)';
  return cells.map(c=> CELL_NAME[c[0]] ? CELL_NAME[c[0]][c[1]] : `(${c[0]},${c[1]})`).join(' + ');
}
const SCOPE_BADGE = {builtin:'Built-in', Local:'Local', Global:'Global', 'Local-override':'Local override'};

// inspect payload for a library item (term or composite)
function inspect(item){
  if(item.kind==='composite'){
    return { name:item.name, scopeBadge:SCOPE_BADGE[item.scope]||item.scope,
      kind:'composite (learned)',
      definition:'pipeline: '+(item.steps||[]).join(' → '),
      provenance: item.scope==='Local' ? 'Local — captured on this brain' : 'Built-in primitive composite',
      dependents: item.dependents||[] };
  }
  return { name:item.name, scopeBadge:SCOPE_BADGE[item.scope]||item.scope,
    kind:'position term (cell-set)',
    definition:'cells: '+cellsLabel(item.cells),
    provenance: item.scope==='builtin' ? 'Built-in seed vocabulary'
               : item.scope==='Local-override' ? 'Global · your Local override'
               : 'Local — taught on this brain'+(item.how?(' ('+item.how+')'):''),
    dependents: item.dependents||[] };
}

// validate a proposed new term name (mock rule set).
// opt.overrideGlobal: allow reusing the name when it currently resolves to a Global
// (copy-on-write → Local-override shadow, per the governance decision).
function validateTermName(name, terms, opt){
  opt = opt||{};
  name=(name||'').trim();
  if(!name) return 'name required';
  const existing = terms.find(t=>t.name===name && !t.retired);
  if(existing){
    if(opt.overrideGlobal && existing.scope==='Global') return null;
    return 'a term named "'+name+'" already exists';
  }
  return null;
}

// ---- v10.2b curation: retire / restore / override ----
// Retire = reversible version-freeze (NOT hard-delete): item stays, marked retired,
// preserves provenance. Restore reverses it. Builtins/Global are not user-retireable.
function isRetireable(item){ return item && (item.scope==='Local' || item.scope==='Local-override'); }
function retire(item){ if(isRetireable(item)) item.retired = true; return item; }
function restore(item){ if(item) item.retired = false; return item; }

// dependents that would be affected by retiring `item` (UI surfaces these; the
// block/cascade/warn POLICY is an open MindsOS decision — not decided here).
function dependentsOf(item){ return (item && item.dependents) || []; }

// scope resolution order (lower = preferred): Local-override → Local → Global → builtin.
const SCOPE_RANK = {'Local-override':0, Local:1, Global:2, builtin:3};
// resolve a term name to the winning (non-retired) entry, Local-first.
function resolveTerm(name, terms){
  const c = terms.filter(t=>t.name===name && t.kind==='term' && !t.retired);
  c.sort((a,b)=> (SCOPE_RANK[a.scope]??9) - (SCOPE_RANK[b.scope]??9));
  return c[0] || null;
}
// unique active (non-retired) term names, in first-seen order (what the dropdowns show).
function activeTermNames(terms){
  const seen=new Set(), out=[];
  for(const t of terms){ if(t.kind&&t.kind!=='term') continue; if(t.retired) continue;
    if(!seen.has(t.name)){ seen.add(t.name); out.push(t.name); } }
  return out;
}
// create a Local-override term shadowing a Global one (copy-on-write).
function overrideGlobal(globalItem, cells, how, terms){
  const t = {name:globalItem.name, scope:'Local-override', kind:'term',
             cells, how:how||'override', dependents:[], shadows:'Global'};
  terms.push(t);
  return t;
}

if(typeof module!=='undefined' && module.exports){
  module.exports = {CELL_NAME, seedTerms, seedComposites, unionCells, composeCells,
    cellsLabel, inspect, validateTermName, SCOPE_BADGE,
    isRetireable, retire, restore, dependentsOf, resolveTerm, activeTermNames,
    overrideGlobal, SCOPE_RANK};
}
