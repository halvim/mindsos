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
    {name:'bottom-right',scope:'builtin', kind:'term', cells:[[2,2]]}
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

// validate a proposed new term name (mock rule set)
function validateTermName(name, terms){
  name=(name||'').trim();
  if(!name) return 'name required';
  if(terms.some(t=>t.name===name)) return 'a term named "'+name+'" already exists';
  return null;
}

if(typeof module!=='undefined' && module.exports){
  module.exports = {CELL_NAME, seedTerms, seedComposites, unionCells, composeCells,
    cellsLabel, inspect, validateTermName, SCOPE_BADGE};
}
