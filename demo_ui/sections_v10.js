/* MindsOS demo v10 — brain "sections" (curated set).
 * Pure (no DOM): browser globals + node module.exports. Mock per-section content
 * derived from the beat's brain data; replaced by real chain artifacts / capability
 * state once wired to live data (Phase D).
 *
 * Section tabs (user-chosen order): Task · Plan · Pipeline · Capabilities.
 * All sections are always available (no reach gating). Each owns its own flags.
 */

const STAGES = [
  ['task','Task'], ['plan','Plan'], ['pipe','Pipeline'], ['caps','Capabilities']
];
const SECTION_ART = {task:'TaskRun', plan:'Plan', pipe:'Pipeline', caps:'Capabilities'};
// which section each flag belongs to (mock; real data will carry this)
const FLAG_SECTION = {fault:'task', gap:'plan', learn:'pipe', promo:'caps', gate:'caps'};

function sectionFlags(sec, data){
  return ((data && data.flags) || []).filter(f => FLAG_SECTION[f] === sec);
}

// payload for one section at one beat
function sectionPayload(sec, data){
  const flags = sectionFlags(sec, data);
  if(sec === 'caps'){
    return {artifact:'Capabilities', isCaps:true, caps:(data.caps||[]), flags};
  }
  const dec = data.decision || '';
  const fault = ((data.flags)||[]).includes('fault');
  const caps = (data.caps||[]).map(c=>c[0]);
  let lines;
  if(sec === 'task')      lines = ['result: ' + (dec || '—') + (fault ? '  ⚠' : '')];
  else if(sec === 'plan') lines = ['plan: ' + (dec || '(ordered steps for this brain)')];
  else                    lines = ['pipeline: ' + (caps.join(' → ') || '—')];
  return {artifact:SECTION_ART[sec], isCaps:false, lines, flags};
}

if(typeof module!=='undefined' && module.exports){
  module.exports = {STAGES, SECTION_ART, FLAG_SECTION, sectionFlags, sectionPayload};
}
