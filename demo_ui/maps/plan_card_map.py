import cairosvg
import os
_OUT=os.path.dirname(os.path.abspath(__file__))+"/.."
# ---- mock brain card, PLAN section, showing the Resolve subsection rendered as a SUB-CARD ----
# Companion to orchestrator_card_map.py (Capabilities section). The reusable subsection container
# = border + per-card accent rail + collapsible header (.subsec / .subhdr / .subbody). Resolve is
# the first subsection; future subsections reuse the same container.
X0,Y0,W,H = 330,150,348,330
MGR="#b98cf0"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"
def darken(h,t=0.70):
    h=h.lstrip("#"); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return "#%02x%02x%02x"%(round(r*t+14*(1-t)),round(g*t+17*(1-t)),round(b*t+22*(1-t)))
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def panel_icon(cx,cy,col):
    return (f'<rect x="{cx-5}" y="{cy-5}" width="10" height="10" rx="1.5" fill="none" stroke="{col}" stroke-width="1.2"/>'
            f'<line x1="{cx-3}" y1="{cy-2}" x2="{cx+3}" y2="{cy-2}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx-3}" y1="{cy}" x2="{cx+3}" y2="{cy}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx-3}" y1="{cy+2}" x2="{cx+1}" y2="{cy+2}" stroke="{col}" stroke-width="1"/>')
def graph_icon(cx,cy,col):
    ax,ay=cx-4,cy-3; bx,by=cx+4,cy-3.5; dx,dy=cx,cy+4
    return (f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{ax}" y1="{ay}" x2="{dx}" y2="{dy}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{bx}" y1="{by}" x2="{dx}" y2="{dy}" stroke="{col}" stroke-width="1"/>'
            f'<circle cx="{ax}" cy="{ay}" r="1.7" fill="{col}"/><circle cx="{bx}" cy="{by}" r="1.7" fill="{col}"/><circle cx="{dx}" cy="{dy}" r="1.7" fill="{col}"/>')
def max_btn(cx,cy,col):
    return (f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="4" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<rect x="{cx-3}" y="{cy-2.5}" width="6" height="5" rx="1" fill="none" stroke="{col}" stroke-width="0.9"/>'
            f'<path d="M{cx-2},{cy-4} L{cx},{cy-5.8} L{cx+2},{cy-4}" fill="none" stroke="{col}" stroke-width="0.9" stroke-linejoin="round"/>'
            f'<path d="M{cx-2},{cy+4} L{cx},{cy+5.8} L{cx+2},{cy+4}" fill="none" stroke="{col}" stroke-width="0.9" stroke-linejoin="round"/>')
def audit_btn(cx,cy,col):  # reasoning-audit control: bordered button + magnifier glyph
    return (f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="4" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<circle cx="{cx-1.5}" cy="{cy-1}" r="3.1" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx+0.7}" y1="{cy+1.2}" x2="{cx+3.6}" y2="{cy+4}" stroke="{col}" stroke-width="1.1" stroke-linecap="round"/>')
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 740" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append('<rect x="0" y="0" width="1180" height="740" fill="#0e1116"/>')
S.append(f'<text x="590" y="34" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Orchestrator card — Plan section, Resolve subsection as a SUB-CARD (part names)</text>')
S.append(f'<text x="590" y="58" fill="{MUT}" font-size="13" text-anchor="middle">reusable subsection container = border + per-card accent rail + collapsible header · Resolve is the first subsection</text>')

# card
S.append(f'<rect x="{X0}" y="{Y0}" width="{W}" height="{H}" rx="11" fill="{PANEL}" stroke="{MGR}" stroke-width="1.6"/>')
tb=34
S.append(f'<path d="M{X0} {Y0+11} q0 -11 11 -11 h{W-22} q11 0 11 11 v{tb-11} h-{W} z" fill="#2a2440"/>')
S.append(f'<line x1="{X0}" y1="{Y0+tb}" x2="{X0+W}" y2="{Y0+tb}" stroke="{MGR}" stroke-opacity="0.5"/>')
S.append(f'<text x="{X0+12}" y="{Y0+22}" fill="{MGR}" font-size="13" font-weight="700">Orchestrator</text>')
# header right cluster — UX controls (audit, maximize) | 20px gap | card-UI (status dot, help)
S.append(audit_btn(X0+W-96, Y0+17, MGR))
S.append(max_btn(X0+W-72, Y0+17, MGR))
S.append(f'<circle cx="{X0+W-36}" cy="{Y0+17}" r="3.5" fill="{MGR}"/>')
S.append(f'<circle cx="{X0+W-16}" cy="{Y0+17}" r="7" fill="none" stroke="{MUT}"/><text x="{X0+W-16}" y="{Y0+21}" fill="{MUT}" font-size="9" text-anchor="middle">?</text>')
# pinned intent
ciy=Y0+tb+16
S.append(f'<text x="{X0+12}" y="{ciy}" fill="{INK}" font-size="10.5">Execute placements</text>')
# section tabs (Plan selected)
tabs=["Task","Plan","Pipeline","Capabilities"]; sel=1
ty=ciy+10; th=18; tw=(W-20)/len(tabs)
for i,t in enumerate(tabs):
    x=X0+10+i*tw; on=(i==sel)
    S.append(f'<rect x="{x:.1f}" y="{ty}" width="{tw-3:.1f}" height="{th}" rx="5" fill="{darken(MGR) if on else PANEL2}" stroke="{MGR}"/>')
    S.append(f'<text x="{x+(tw-3)/2:.1f}" y="{ty+13}" fill="{"#eafcff" if on else "#e6edf3"}" font-size="8.5" font-weight="{700 if on else 400}" text-anchor="middle">{t}</text>')
# section header
hy=ty+th+14
S.append(f'<text x="{X0+12}" y="{hy}" fill="{INK}" font-size="9" font-weight="700" letter-spacing="0.5">PLAN</text>')
bw=22; gx=X0+W-12-bw; pxb=gx-3-bw
S.append(f'<rect x="{pxb}" y="{hy-12}" width="{bw}" height="16" rx="5" fill="{darken(MGR)}" stroke="{MGR}"/>')
S.append(panel_icon(pxb+bw/2, hy-4, "#eafcff"))
S.append(f'<rect x="{gx}" y="{hy-12}" width="{bw}" height="16" rx="5" fill="{PANEL2}" stroke="{MGR}"/>')
S.append(graph_icon(gx+bw/2, hy-4, "#e6edf3"))
# plan decision line
py=hy+18
S.append(f'<text x="{X0+14}" y="{py}" fill="{INK}" font-size="9.5">decision: resolve ‘Box above Tube’ → A2 (r0,c1)</text>')

# ---- Resolve SUB-CARD (.subsec) ----
sx=X0+12; sw=W-24; sy=py+10; sh=104
S.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="7" fill="#11151c" stroke="{EDGE}"/>')          # .subsec border
S.append(f'<rect x="{sx+1.5}" y="{sy+1.5}" width="3" height="{sh-3}" rx="1.5" fill="{MGR}"/>')                    # accent rail (::before)
hh=18
S.append(f'<path d="M{sx+6} {sy+1} h{sw-13} q6 0 6 6 v{hh-6} h-{sw-6} v-{hh-6} q0 -6 6 -6 z" fill="{darken(MGR,0.22)}"/>')  # .subhdr strip
S.append(f'<text x="{sx+13}" y="{sy+13}" fill="#e7edf3" font-size="8.5" font-weight="700" letter-spacing="0.6">RESOLVE</text>')
# expanded chevron ▾
chx=sx+sw-16; chy=sy+9
S.append(f'<path d="M{chx-3},{chy-2} l3,4 l3,-4" fill="none" stroke="{MUT}" stroke-width="1.2" stroke-linejoin="round"/>')
# .subbody : clause + grid + cap
bx=sx+13; bodyy=sy+hh+14
S.append(f'<text x="{bx}" y="{bodyy}" fill="{INK}" font-size="10">Box above Tube</text>')                        # .rclause
gx0=bx; gy0=bodyy+8; cs=18
state=[["cand","win","cand"],["out","out","out"],["out","tube","out"]]
for r in range(3):
    for c in range(3):
        st=state[r][c]; cx=gx0+c*cs; cy=gy0+r*cs
        if st=="win": fill,stroke,swd="#1d3a2a","#eafcff",1.6
        elif st=="cand": fill,stroke,swd="#142233",MGR,1.0
        elif st=="tube": fill,stroke,swd="#2a1330","#b3598c",1.0
        else: fill,stroke,swd=PANEL2,EDGE,1.0
        S.append(f'<rect x="{cx}" y="{cy}" width="{cs-2}" height="{cs-2}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{swd}"/>')
        if st=="win": S.append(f'<text x="{cx+(cs-2)/2}" y="{cy+12}" fill="#eafcff" font-size="8" text-anchor="middle">■</text>')
        if st=="tube": S.append(f'<text x="{cx+(cs-2)/2}" y="{cy+12}" fill="#e7a6cf" font-size="7" text-anchor="middle">T</text>')
capx=gx0+3*cs+12; capy=gy0+12
S.append(f'<text x="{capx}" y="{capy}" fill="#bff5cf" font-size="9">row above Tube</text>')                      # .rcap
S.append(f'<text x="{capx}" y="{capy+14}" fill="#ffe6a8" font-size="9" font-weight="600">9 → 3 → 1 (step 2/3)</text>')

# ---- callouts ----
def leader(x1,y1,x2,y2,col="#5c6773"):
    S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{col}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{col}"/>')
def label(x,y,name,cls,anchor="start"):
    S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="12.5" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    if cls: S.append(f'<text x="{x}" y="{y+14}" fill="{MUT}" font-size="10.5" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')

# TOP
_planc=X0+10+1*tw+(tw-3)/2
label(X0+12,108,"Brain sections",".bsec  (Plan selected)"); leader(X0+60,114,_planc,ty-1)
label(905,90,"Reasoning audit",".auditbtn"); leader(903,86,X0+W-96,Y0+9)
label(905,122,"Maximize height",".maxbtn"); leader(903,118,X0+W-72,Y0+9)
label(905,154,"Help / tooltip",".help  (hover = description)"); leader(903,150,X0+W-16,Y0+17)

# LEFT
label(300,Y0+6,"Card",".dcard.mgr",anchor="end"); leader(305,Y0+2,X0,Y0+2)
label(300,hy+2,"Section name",".sechdr .artname",anchor="end"); leader(305,hy-2,X0+12,hy-3)
label(300,sy+8,"Sub-card",".subsec  (border)",anchor="end"); leader(305,sy+4,sx,sy+1)
label(300,sy+40,"Accent left-rail",".subsec ::before",anchor="end"); leader(305,sy+36,sx+3,sy+34)
label(300,sy+80,"Sub-card body",".subbody",anchor="end"); leader(305,sy+76,sx+30,gy0+2*cs)

# RIGHT
label(720,hy+2,"View mode (in section)",".vtog → .vmb"); leader(716,hy-2,X0+W-22,hy-4)
label(720,sy+6,"Collapsible header",".subhdr  (▾ collapse toggle)"); leader(716,sy+2,chx,chy)
label(720,sy+44,"Spatial clause",".rclause"); leader(716,sy+40,bx+50,bodyy-3)
label(720,sy+78,"Narrowing 3×3 grid",".rgrid"); leader(716,sy+74,gx0+3*cs-4,gy0+cs)
label(720,sy+112,"Stage caption",".rcap"); leader(716,sy+108,capx-4,capy)

# BOTTOM captions
cy0=Y0+H+44
S.append(f'<text x="590" y="{cy0}" fill="{INK}" font-size="12.5" text-anchor="middle">One reusable container (.subsec) for every subsection: bordered box + per-card accent rail + a header (.subhdr) that collapses to header-only. Subsections start expanded.</text>')
S.append(f'<text x="590" y="{cy0+20}" fill="{MUT}" font-size="11.5" text-anchor="middle">Empty-beat body: “no spatial relation resolved this beat” (.rnone). Live (?live=): “feed not yet emitted” until a backend resolve producer exists. Click the header to collapse.</text>')

S.append("</svg>")
svg="".join(S)
cairosvg.svg2png(bytestring=svg.encode(),write_to=os.path.join(_OUT,"plan_card_map.png"),output_width=1180,output_height=740,background_color="#0e1116")
print("rendered plan_card_map.png")
