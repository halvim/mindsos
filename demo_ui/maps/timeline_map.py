import cairosvg, os
_OUT = os.path.dirname(os.path.abspath(__file__)) + "/.."
# ---- Demo-timeline modal part-name map (v0.24). Opened from the beat-chip button (#beatnum).
#      Chronological, change-only transcript of every message + brain section/subsection change,
#      filterable by Sources / Sections / Subsections. ----
BG="#0e1116"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"
A1="#3a8be0"; MGR="#b98cf0"; USER="#53b0be"; SEAMA="#6f8092"; SEAMB="#9aa7b3"; NEU="#7f8c99"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
W,H=1380,880
S=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
S.append(f'<text x="{W/2}" y="32" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Demo timeline modal — part names (v0.24) — use the name or the #id / .class</text>')
S.append(f'<text x="{W/2}" y="55" fill="{MUT}" font-size="12.5" text-anchor="middle">Opened from #beatnum (the beat chip). Change-only transcript; Sources / Sections / Subsections toggles.</text>')

# geometry (margins on both sides for callouts)
mx,my,mw,mh=300,150,780,660
LX=mx-24; RX=mx+mw+26

def pill(x,y,w,txt,col,on=True):
    if on:
        S.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="10" fill="{col}" opacity="0.18"/>')
        S.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="10" fill="none" stroke="{col}"/>')
        S.append(f'<text x="{x+w/2:.0f}" y="{y+14}" fill="{col}" font-size="9.5" text-anchor="middle">{esc(txt)}</text>')
    else:
        S.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="10" fill="none" stroke="{MUT}" opacity="0.5"/>')
        S.append(f'<text x="{x+w/2:.0f}" y="{y+14}" fill="{MUT}" font-size="9.5" text-anchor="middle" opacity="0.7">{esc(txt)}</text>')

# trigger — #beatnum (beat chip button) on a beat strip, aligned above the modal
bsx,bsy,bsw=mx,84,mw
S.append(f'<rect x="{bsx}" y="{bsy}" width="{bsw}" height="30" rx="7" fill="#101a27" stroke="{EDGE}"/>')
S.append(f'<rect x="{bsx}" y="{bsy}" width="3.5" height="30" rx="2" fill="{A1}"/>')
S.append(f'<rect x="{bsx+14}" y="{bsy+6}" width="92" height="18" rx="9" fill="#1f6feb" stroke="#1f6feb"/>')
S.append(f'<text x="{bsx+52}" y="{bsy+19}" fill="#fff" font-size="10" text-anchor="middle">Beat 4 / 7  ⤢</text>')
S.append(f'<text x="{bsx+118}" y="{bsy+19}" fill="#eaf2ff" font-size="11">Cooperative execution — the brains run the new skill…</text>')

# ===== the modal =====
S.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="13" fill="{PANEL}" stroke="{A1}" stroke-width="1.6"/>')
S.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="42" rx="13" fill="{A1}" opacity="0.13"/>')
S.append(f'<text x="{mx+16}" y="{my+27}" fill="{INK}" font-size="14" font-weight="700">Demo timeline — every message &amp; state, in order</text>')
S.append(f'<text x="{mx+mw-24}" y="{my+28}" fill="{MUT}" font-size="18">×</text>')
# filter rows
fy0=my+54
rows_f=[("Sources",[("Seam A",SEAMA,1),("Seam B",SEAMB,1),("User",USER,1),("Orchestrator",MGR,1),("Arm 1",A1,1),("Arm 2",A1,0)]),
        ("Sections",[("Task",NEU,1),("Plan",NEU,1),("Pipeline",NEU,0),("Capabilities",NEU,1)]),
        ("Subsections",[("Plan ▸ Resolve",NEU,1)])]
fy=fy0
for lab_,pills in rows_f:
    S.append(f'<text x="{mx+16}" y="{fy+14}" fill="{MUT}" font-size="10" font-weight="700">{lab_}</text>')
    px=mx+100
    for t,c,on in pills:
        w=len(t)*6.4+24; pill(px,fy,w,t,c,on); px+=w+7
    fy+=28
# body
by=my+150
S.append(f'<line x1="{mx}" y1="{by-8}" x2="{mx+mw}" y2="{by-8}" stroke="{EDGE}"/>')
def beat(y,txt): S.append(f'<rect x="{mx+14}" y="{y}" width="{mw-28}" height="22" rx="5" fill="#11161d"/>');S.append(f'<text x="{mx+22}" y="{y+15}" fill="{INK}" font-size="10.5" font-weight="700">{esc(txt)}</text>')
def row(y,src,col,tag,text):
    S.append(f'<rect x="{mx+22}" y="{y}" width="3" height="20" rx="1.5" fill="{col}"/>')
    S.append(f'<rect x="{mx+30}" y="{y}" width="76" height="16" rx="5" fill="{col}" opacity="0.18" stroke="{col}"/>')
    S.append(f'<text x="{mx+68}" y="{y+12}" fill="{col}" font-size="8.4" text-anchor="middle">{esc(src)}</text>')
    S.append(f'<text x="{mx+116}" y="{y+12}" fill="{MUT}" font-size="9">{esc(tag)}</text>')
    S.append(f'<text x="{mx+258}" y="{y+12}" fill="{INK}" font-size="10">{esc(text)}</text>')
beat(by,"Beat 1 · Order placed")
row(by+28,"User",USER,"User → Orchestrator","Order: Box above Tube; Sheet at center")
row(by+52,"Orchestrator",MGR,"Task","Break down the order; work out where each item goes")
row(by+76,"Seam A",SEAMA,"Server","Session authenticated")
beat(by+104,"Beat 2 · Ignorant start → don’t-know")
row(by+132,"Seam B",SEAMB,"Orchestrator → Arm 1","What can you do?")
row(by+156,"Arm 1",A1,"Capabilities","hand-off (learned)")

# ===== callouts =====
def lead(x1,y1,x2,y2,c="#5c6773"): S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{c}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{c}"/>')
def lab(x,y,name,cls,anchor="start"):
    S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="12.5" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    if cls: S.append(f'<text x="{x}" y="{y+13}" fill="{MUT}" font-size="9.5" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')

# trigger
lead(bsx+60,bsy+9, bsx+250,bsy-4); lab(bsx+256,bsy-6,"beat chip → opens timeline","#beatnum (button)")

# LEFT labels (anchor end at LX)
lead(mx+300,my+12, LX-2,my+12);          lab(LX-6,my+8,  "header / title","#tlmodal .tlhead",anchor="end")
lead(mx+60,my+56,  LX-2,my+58);          lab(LX-6,my+58, "filter block",".tlfilters",anchor="end")
lead(mx+40,fy0+10, LX-2,fy0+34);         lab(LX-6,fy0+38,"row label",".tlflab",anchor="end")
lead(mx,my+mh-44,  LX-2,my+mh-44);       lab(LX-6,my+mh-48,"modal container","#tlmodal",anchor="end")

# RIGHT labels (anchor start at RX)
lead(mx+mw-22,my+22, RX,my+24);                 lab(RX+6,my+26, "close (×, Esc, backdrop)",".tlclose")
lead(mx+330,fy0+10,  RX,fy0+2);                 lab(RX+6,fy0+4, "a toggle (active)",".tlpill.on")
lead(mx+470,fy0+10,  RX,fy0+44);                lab(RX+6,fy0+46,"a toggle (excluded)",".tlpill.off")
lead(mx+220,fy0+66,  RX,fy0+76);                lab(RX+6,fy0+78,"Sources · Sections · Subsections",".tlpills[data-axis]")
lead(mx+mw-30,by+11, RX,by+30);                 lab(RX+6,by+32, "scrollable transcript","#tlbody")
lead(mx+210,by+115,  RX,by+120);                lab(RX+6,by+122,"beat group header",".tlbeat")
lead(mx+68,by+164,   RX,by+176);                lab(RX+6,by+178,"source badge (colour = source)",".tlsrc")
lead(mx+150,by+164,  RX,by+216);                lab(RX+6,by+218,"section / party tag",".tltag")
lead(mx+360,by+164,  RX,by+256);                lab(RX+6,by+258,"entry text (behavior-level)",".tltext")
lead(mx+95,by+166,   RX,by+296);                lab(RX+6,by+298,"one entry",".tlrow")

S.append('</svg>')
cairosvg.svg2png(bytestring="\n".join(S).encode(), write_to=_OUT+"/timeline_map.png", scale=1.4, background_color=BG)
print("wrote", _OUT+"/timeline_map.png")
