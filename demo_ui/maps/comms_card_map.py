import cairosvg, os
_OUT=os.path.dirname(os.path.abspath(__file__))+"/.."
# ---- Messages card (formerly "Inter-brain messages") — now TABBED: Inter-brain (Seam B) / Server (Seam A) ----
# Two instances of the SAME card, each with a different tab active, so both tab-contents are named.
INK="#e6edf3"; MUT="#8b98a5"; EDGE="#2b333d"; PANEL="#161b22"; PANEL2="#1c232d"
NEU="#5f6b78"      # neutral card accent (comms card is not a brain)
SRV="#6f8092"      # server / Seam-A steel
def darken(h,t=0.70):
    h=h.lstrip("#"); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return "#%02x%02x%02x"%(round(r*t+14*(1-t)),round(g*t+17*(1-t)),round(b*t+22*(1-t)))
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 760" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append('<rect width="1180" height="760" fill="#0e1116"/>')
S.append(f'<text x="590" y="32" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Messages card — tabbed: Server (Seam A) · Inter-brain (Seam B) — part names</text>')
S.append(f'<text x="590" y="55" fill="{MUT}" font-size="13" text-anchor="middle">one card (#card_log), two tabs · same card shown twice, each with a different tab active</text>')

W,H=300,420
def card(ox,oy,active):   # active = "ib" | "server"
    S.append(f'<rect x="{ox}" y="{oy}" width="{W}" height="{H}" rx="11" fill="{PANEL}" stroke="{NEU}" stroke-width="1.6"/>')
    tb=30
    S.append(f'<path d="M{ox} {oy+11} q0 -11 11 -11 h{W-22} q11 0 11 11 v{tb-11} h-{W} z" fill="#1a1f27"/>')
    S.append(f'<text x="{ox+12}" y="{oy+20}" fill="{INK}" font-size="11" font-weight="700" letter-spacing="0.4">Messages</text>')
    # live chip + help (window-level)
    S.append(f'<circle cx="{ox+W-78}" cy="{oy+15}" r="3" fill="#56d18a"/>')
    S.append(f'<text x="{ox+W-70}" y="{oy+18}" fill="#9be7bd" font-size="8" font-weight="600">live</text>')
    S.append(f'<circle cx="{ox+W-16}" cy="{oy+15}" r="7" fill="none" stroke="{MUT}"/><text x="{ox+W-16}" y="{oy+18.5}" fill="{MUT}" font-size="9" text-anchor="middle">?</text>')
    # tab row (.uitab x2) in the BODY
    ty=oy+tb+8; th=18; labels=[("Server · Seam A","server"),("Inter-brain · Seam B","ib")]
    tw=(W-20)/2
    for i,(lab,key) in enumerate(labels):
        x=ox+10+i*tw; on=(key==active); acc = SRV if key=="server" else NEU
        S.append(f'<rect x="{x:.1f}" y="{ty}" width="{tw-3:.1f}" height="{th}" rx="5" fill="{darken(acc) if on else PANEL2}" stroke="{acc}"/>')
        S.append(f'<text x="{x+(tw-3)/2:.1f}" y="{ty+12}" fill="{"#eafcff" if on else INK}" font-size="8" font-weight="{700 if on else 400}" text-anchor="middle">{lab}</text>')
    by=ty+th+12
    if active=="ib":
        rows=[("Orchestrator","Arm1","query_capabilities()","#b98cf0","#3a8be0"),
              ("Arm1","Orchestrator","DONT_KNOW(handoff)","#3a8be0","#b98cf0"),
              ("User","Arm1","demonstrate([…])","#53b0be","#3a8be0"),
              ("Demonstration","L2","Pipeline → promoted","#7f8c99","#7f8c99"),
              ("Orchestrator","Conveyor","dispatch(advance)","#b98cf0","#46c07a")]
        for j,(a,b,txt,ca,cb) in enumerate(rows):
            yy=by+j*22
            S.append(f'<text x="{ox+12}" y="{yy}" font-size="9"><tspan fill="{ca}" font-weight="700">{a}</tspan><tspan fill="#566270"> → </tspan><tspan fill="{cb}" font-weight="700">{b}</tspan></text>')
            S.append(f'<text x="{ox+12}" y="{yy+11}" fill="{INK}" font-size="8.5">{esc(txt)}</text>')
            S.append(f'<line x1="{ox+12}" y1="{yy+16}" x2="{ox+W-12}" y2="{yy+16}" stroke="{EDGE}" stroke-opacity="0.4"/>')
    else:
        # vitals strip
        S.append(f'<rect x="{ox+10}" y="{by-10}" width="{W-20}" height="30" rx="6" fill="#11161d" stroke="{EDGE}"/>')
        S.append(f'<text x="{ox+18}" y="{by+1}" fill="#cfe6ff" font-size="9" font-weight="600">4 sessions</text>')
        S.append(f'<text x="{ox+96}" y="{by+1}" fill="#9be7bd" font-size="9">Falkor ✓</text>')
        S.append(f'<text x="{ox+160}" y="{by+1}" fill="{INK}" font-size="9">up 14m</text>')
        S.append(f'<text x="{ox+18}" y="{by+14}" fill="{MUT}" font-size="7.5" font-family="ui-monospace,Menlo,monospace">wss://brains.sanmyaku.com</text>')
        ev=[("login","#5aa9e6","admin + 4 brain sessions"),
            ("skill","#b98cf0","demo-world@1.0 on a1 (gate ✓)"),
            ("gate ✗","#e0685f","arm1 Global write DENIED"),
            ("persist","#4fb0a0","Global(a1) → Falkor")]
        ey=by+34
        for j,(k,c,txt) in enumerate(ev):
            yy=ey+j*24
            S.append(f'<rect x="{ox+12}" y="{yy-9}" width="42" height="13" rx="6" fill="{darken(c,0.30)}" stroke="{c}" stroke-opacity="0.6"/>')
            S.append(f'<text x="{ox+33}" y="{yy}" fill="{c}" font-size="7.5" font-weight="600" text-anchor="middle">{k}</text>')
            S.append(f'<text x="{ox+60}" y="{yy}" fill="{INK}" font-size="8.5">{esc(txt)}</text>')
            S.append(f'<line x1="{ox+12}" y1="{yy+8}" x2="{ox+W-12}" y2="{yy+8}" stroke="{EDGE}" stroke-opacity="0.4"/>')

LX,RX,OY=320,628,110
card(LX,OY,"ib")
card(RX,OY,"server")
S.append(f'<text x="{LX+W/2}" y="{OY-12}" fill="{NEU}" font-size="12" font-weight="700" text-anchor="middle">Inter-brain tab active</text>')
S.append(f'<text x="{RX+W/2}" y="{OY-12}" fill="{SRV}" font-size="12" font-weight="700" text-anchor="middle">Server tab active</text>')

def leader(x1,y1,x2,y2,col="#5c6773"):
    S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{col}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{col}"/>')
def label(x,y,name,cls,anchor="start"):
    S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="12" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    if cls: S.append(f'<text x="{x}" y="{y+14}" fill="{MUT}" font-size="10" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')

# LEFT card → labels on the left
label(300,OY+6,"Card",".dcard #card_log",anchor="end"); leader(305,OY+2,LX,OY+2)
label(300,OY+24,"Card title (rename)",'"Messages"',anchor="end"); leader(305,OY+20,LX+40,OY+15)
label(300,OY+60,"Tab row",".uitab × 2",anchor="end"); leader(305,OY+56,LX+10,OY+47)
label(300,OY+150,"Inter-brain feed (Seam B)","from→to colored + text",anchor="end"); leader(305,OY+146,LX+30,OY+110)
label(300,OY+250,"Active tab","darker accent fill",anchor="end"); leader(305,OY+246,LX+218,OY+47)

# RIGHT card → labels on the right
label(960,OY+6,"Live status",".state ● live"); leader(956,OY+2,RX+W-78,OY+15)
label(960,OY+30,"Help / tooltip",".help"); leader(956,OY+26,RX+W-16,OY+15)
label(960,OY+70,"Server tab (Seam A)","steel accent · first tab"); leader(956,OY+66,RX+78,OY+47)
label(960,OY+120,"Server vitals","sessions · Falkor · uptime"); leader(956,OY+116,RX+W-40,OY+82)
label(960,OY+185,"Kind badge","color-coded event"); leader(956,OY+181,RX+33,OY+150)
label(960,OY+245,"Server event feed","Seam-A · auth · authz · audit · persist"); leader(956,OY+241,RX+90,OY+178)

cy0=OY+H+44
S.append(f'<text x="590" y="{cy0}" fill="{INK}" font-size="12.5" text-anchor="middle">The card formerly named “Inter-brain messages” becomes “Messages” with two .uitab tabs. Tab 1 = the live Server feed (Seam-A); Tab 2 = the existing inter-brain log (Seam-B).</text>')
S.append(f'<text x="590" y="{cy0+20}" fill="{MUT}" font-size="11.5" text-anchor="middle">Design approved 2026-06-12 (placement option C-as-tab). Build pending. Server tab is live-only (?live=); mock shows a representative sequence labeled mock.</text>')

S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(),write_to=os.path.join(_OUT,"comms_card_map.png"),output_width=1180,output_height=760,background_color="#0e1116")
print("rendered comms_card_map.png")
