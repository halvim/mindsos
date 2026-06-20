import cairosvg, os
_OUT = os.path.dirname(os.path.abspath(__file__)) + "/.."
# ---- Header part-name map (v0.24). Title “MindsOS Demo” (OS bold); Audit (magenta, VIEW) split from
#      Export (download only); system message = option-C callout. NOW INCLUDES the beat strip:
#      #beatnum (outlined chip) + #beatnarr + the far-right #tlbtn (opens the demo timeline). ----
BG="#0e1116"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"
WARN="#d29922"; GREEN="#48c78e"; BLUE="#1f6feb"; INFO="#5b9bf0"; RED="#e5534b"; A1="#3a8be0"
AUD="#c2419a"; AUDD="#a8327f"
HH=372
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
S=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 {HH}" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect x="0" y="0" width="1180" height="{HH}" fill="{BG}"/>')
S.append(f'<text x="590" y="30" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Header — part names (v0.24) — use the name or the #id / .class</text>')
S.append(f'<text x="590" y="53" fill="{MUT}" font-size="12.5" text-anchor="middle">Audit (magenta) = VIEW · Export = DOWNLOAD only · beat strip below the bar opens the demo timeline (#tlbtn)</text>')

def pill(x,y,w,txt,col,fill=PANEL2):
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="10" fill="{fill}" stroke="{col}"/>')
    S.append(f'<text x="{x+w/2:.0f}" y="{y+14}" fill="{col}" font-size="10" text-anchor="middle">{esc(txt)}</text>')
def btn(x,y,w,txt,prim=False):
    f=BLUE if prim else PANEL2; b=BLUE if prim else EDGE
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="6" fill="{f}" stroke="{b}"/>')
    S.append(f'<text x="{x+w/2:.0f}" y="{y+16}" fill="{INK}" font-size="10.5" text-anchor="middle">{esc(txt)}</text>')

hx,hy,hw=60,108,1060
S.append(f'<rect x="{hx}" y="{hy}" width="{hw}" height="50" rx="9" fill="#11151c" stroke="{EDGE}"/>')
# title — OS bold
S.append(f'<text x="{hx+16}" y="{hy+31}" font-size="16">'
         f'<tspan fill="{INK}" font-weight="500">Minds</tspan>'
         f'<tspan fill="{INK}" font-weight="800">OS</tspan>'
         f'<tspan fill="{INK}" font-weight="500"> Demo</tspan></text>')
pill(hx+150, hy+15, 78, "presentation", MUT)
pill(hx+236, hy+15, 46, "v0.24", MUT)
pill(hx+290, hy+15, 196, "● live — connected", GREEN, fill="#0f1f17")
btn(hx+hw-38,  hy+13, 26, "↺"); btn(hx+hw-68, hy+13, 26, "›"); btn(hx+hw-136, hy+13, 64, "▶ Play", prim=True); btn(hx+hw-166, hy+13, 26, "‹")
btn(hx+hw-238, hy+13, 64, "Import")
ex=hx+hw-320; btn(ex, hy+13, 78, "▾ Export")
ax=ex-40-92
S.append(f'<rect x="{ax}" y="{hy+13}" width="92" height="24" rx="6" fill="{AUD}" stroke="{AUDD}"/>')
S.append(f'<circle cx="{ax+18}" cy="{hy+25}" r="3.4" fill="none" stroke="#fff" stroke-width="1.3"/><line x1="{ax+20.4}" y1="{hy+27.4}" x2="{ax+23.6}" y2="{hy+30.6}" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>')
S.append(f'<text x="{ax+34}" y="{hy+29}" fill="#fff" font-size="11" font-weight="700">Audit ▾</text>')
S.append(f'<line x1="{ax+97}" y1="{hy+25}" x2="{ex-5}" y2="{hy+25}" stroke="#454e59" stroke-dasharray="2 3"/>')

# ===== beat strip (v0.22 / v0.24) — full-width, under the bar =====
bsx,bsy,bsw=hx,hy+62,hw
S.append(f'<rect x="{bsx}" y="{bsy}" width="{bsw}" height="30" rx="7" fill="#101a27" stroke="{EDGE}"/>')
S.append(f'<rect x="{bsx}" y="{bsy}" width="3.5" height="30" rx="2" fill="{A1}"/>')
# #beatnum — outlined-blue chip (display only)
S.append(f'<rect x="{bsx+16}" y="{bsy+5}" width="72" height="20" rx="10" fill="none" stroke="{A1}"/>')
S.append(f'<text x="{bsx+52}" y="{bsy+19}" fill="{A1}" font-size="10" text-anchor="middle">Beat 4 / 7</text>')
# #beatnarr — narration
S.append(f'<text x="{bsx+100}" y="{bsy+19}" fill="#eaf2ff" font-size="11">Cooperative execution — the brains run the new skill: belt hands Box and Tube to Arm 2…</text>')
# #tlbtn — FAR-RIGHT filled-blue Timeline button (list icon + label)
tbw=90; tbx=bsx+bsw-12-tbw
S.append(f'<rect x="{tbx}" y="{bsy+4}" width="{tbw}" height="22" rx="6" fill="{BLUE}" stroke="{BLUE}"/>')
icx=tbx+16
for dy in (-4,0,4):
    S.append(f'<circle cx="{icx-5}" cy="{bsy+15+dy}" r="1.2" fill="#fff"/>')
    S.append(f'<line x1="{icx-2}" y1="{bsy+15+dy}" x2="{icx+5}" y2="{bsy+15+dy}" stroke="#fff" stroke-width="1.3" stroke-linecap="round"/>')
S.append(f'<text x="{tbx+30}" y="{bsy+19}" fill="#fff" font-size="10.5">Timeline</text>')

# #l5cal callout
cy=hy+132
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
# BEAT STRIP parts (labels in the gap below the strip)
lab(bsx+52,218,"beat number","#beatnum",anchor="middle",col=A1); lead(bsx+52,208,bsx+52,bsy+28)
lab(bsx+330,218,"narration","#beatnarr",anchor="middle"); lead(bsx+330,208,bsx+330,bsy+22)
lab(tbx+45,218,"open timeline","#tlbtn  (list icon + label)",anchor="middle",col=BLUE); lead(tbx+45,208,tbx+45,bsy+28)
# BOTTOM-RIGHT (menu ghost removed → clear)
lab(640,cy+16,"System message callout","#l5cal  ·  .l5ico · #l5msg · #l5x",col=INFO); lead(636,cy+12,hx+560,cy+12)
lab(870,cy+16,"severity colour","#l5cal.sev-info / -ok / -warn / -error"); lead(866,cy+12,hx+4,cy+18)
lab(640,by+18,"Compatibility banner","#capbanner (separate, persistent)"); lead(636,by+14,hx+560,by+12)

S.append(f'<text x="590" y="{HH-24}" fill="{MUT}" font-size="11.5" text-anchor="middle">Beat strip (v0.22/0.24): #beatnum chip + #beatnarr; far-right #tlbtn opens the demo timeline. #l5cal: severity-coloured, auto-clears.</text>')
S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(), write_to=os.path.join(_OUT,"header_map.png"),
                 output_width=1180, output_height=HH, background_color=BG)
print("rendered header_map.png")
