import cairosvg, os
_OUT = os.path.dirname(os.path.abspath(__file__)) + "/.."
# ---- Header part-name map (v0.19). Title “MindsOS Demo” (OS bold); no beat/narration; NEW Audit
#      button (magenta, VIEW) split from Export (download only); system message = option-C callout. ----
BG="#0e1116"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"
WARN="#d29922"; GREEN="#48c78e"; BLUE="#1f6feb"; INFO="#5b9bf0"; RED="#e5534b"
AUD="#c2419a"; AUDD="#a8327f"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 600" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect x="0" y="0" width="1180" height="600" fill="{BG}"/>')
S.append(f'<text x="590" y="30" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Header — part names (v0.19) — use the name or the #id / .class</text>')
S.append(f'<text x="590" y="53" fill="{MUT}" font-size="12.5" text-anchor="middle">Audit (magenta) = VIEW · Export = DOWNLOAD only · #l5cal = the prominent system-message callout</text>')

def pill(x,y,w,txt,col,fill=PANEL2):
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="10" fill="{fill}" stroke="{col}"/>')
    S.append(f'<text x="{x+w/2:.0f}" y="{y+14}" fill="{col}" font-size="10" text-anchor="middle">{esc(txt)}</text>')
def btn(x,y,w,txt,prim=False):
    f=BLUE if prim else PANEL2; b=BLUE if prim else EDGE
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="6" fill="{f}" stroke="{b}"/>')
    S.append(f'<text x="{x+w/2:.0f}" y="{y+16}" fill="{INK}" font-size="10.5" text-anchor="middle">{esc(txt)}</text>')

hx,hy,hw=60,120,1060
S.append(f'<rect x="{hx}" y="{hy}" width="{hw}" height="50" rx="9" fill="#11151c" stroke="{EDGE}"/>')
# title — OS bold
S.append(f'<text x="{hx+16}" y="{hy+31}" font-size="16">'
         f'<tspan fill="{INK}" font-weight="500">Minds</tspan>'
         f'<tspan fill="{INK}" font-weight="800">OS</tspan>'
         f'<tspan fill="{INK}" font-weight="500"> Demo</tspan></text>')
pill(hx+150, hy+15, 78, "presentation", MUT)
pill(hx+236, hy+15, 46, "v0.19", MUT)
pill(hx+290, hy+15, 196, "● live — connected", GREEN, fill="#0f1f17")
btn(hx+hw-38,  hy+13, 26, "↺"); btn(hx+hw-68, hy+13, 26, "›"); btn(hx+hw-136, hy+13, 64, "▶ Play", prim=True); btn(hx+hw-166, hy+13, 26, "‹")
btn(hx+hw-238, hy+13, 64, "Import")
ex=hx+hw-320; btn(ex, hy+13, 78, "▾ Export")
ax=ex-40-92
S.append(f'<rect x="{ax}" y="{hy+13}" width="92" height="24" rx="6" fill="{AUD}" stroke="{AUDD}"/>')
S.append(f'<circle cx="{ax+18}" cy="{hy+25}" r="3.4" fill="none" stroke="#fff" stroke-width="1.3"/><line x1="{ax+20.4}" y1="{hy+27.4}" x2="{ax+23.6}" y2="{hy+30.6}" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>')
S.append(f'<text x="{ax+34}" y="{hy+29}" fill="#fff" font-size="11" font-weight="700">Audit ▾</text>')
S.append(f'<line x1="{ax+97}" y1="{hy+25}" x2="{ex-5}" y2="{hy+25}" stroke="#454e59" stroke-dasharray="2 3"/>')

# #l5cal callout
cy=hy+86
S.append(f'<rect x="{hx}" y="{cy}" width="560" height="34" rx="8" fill="{PANEL2}" stroke="{EDGE}"/>')
S.append(f'<rect x="{hx}" y="{cy}" width="4" height="34" rx="2" fill="{GREEN}"/>')
S.append(f'<text x="{hx+16}" y="{cy+22}" fill="{GREEN}" font-size="14">✓</text>')
S.append(f'<text x="{hx+36}" y="{cy+22}" fill="{INK}" font-size="13">opened Orchestrator reasoning audit</text>')
S.append(f'<text x="{hx+544}" y="{cy+22}" fill="{MUT}" font-size="14">×</text>')

# #capbanner (separate)
by=cy+44
S.append(f'<rect x="{hx}" y="{by}" width="560" height="24" rx="6" fill="#211a0e" stroke="#5a4a1f"/>')
S.append(f'<text x="{hx+12}" y="{by+16}" fill="{WARN}" font-size="10">⚠ Compatibility fallback active (2D / solid fills) · dismiss</text>')

# ===== callouts =====
def lead(x1,y1,x2,y2,c="#5c6773"): S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{c}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{c}"/>')
def lab(x,y,name,cls,anchor="start",col=INK):
    S.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="12" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    if cls: S.append(f'<text x="{x}" y="{y+13}" fill="{MUT}" font-size="10" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')

# TOP (staggered to avoid overlap)
lab(66,96,"Title — “MindsOS Demo”","h1  (OS = h1 .osb, bold)"); lead(112,100,hx+60,hy)
lab(300,96,"Tags",".tag · version · #honesty"); lead(330,100,hx+300,hy+15)
lab(ax+46,96,"Audit — VIEW","#audit → #auditmenu",anchor="middle",col=AUD); lead(ax+46,100,ax+46,hy+13)
lab(ex+39,116,"Export — DOWNLOAD","#export → #expmenu",anchor="middle"); lead(ex+39,120,ex+39,hy+13)
lab(1124,96,"Import · transport","#import #prev #play #next #reset",anchor="end"); lead(1120,100,hx+hw-136,hy+13)
# BOTTOM-RIGHT (menu ghost removed → clear)
lab(640,cy+16,"System message callout","#l5cal  ·  .l5ico · #l5msg · #l5x",col=INFO); lead(636,cy+12,hx+560,cy+12)
lab(870,cy+16,"severity colour","#l5cal.sev-info / -ok / -warn / -error"); lead(866,cy+12,hx+4,cy+18)
lab(640,by+18,"Compatibility banner","#capbanner (separate, persistent)"); lead(636,by+14,hx+560,by+12)

S.append(f'<text x="590" y="560" fill="{MUT}" font-size="11.5" text-anchor="middle">#l5cal: permanent reserved height, colour by severity, auto-clears to idle after a few seconds. Beat chip + narration removed.</text>')
S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(), write_to=os.path.join(_OUT,"header_map.png"),
                 output_width=1180, output_height=600, background_color=BG)
print("rendered header_map.png")
