import cairosvg
import os
_OUT=os.path.dirname(os.path.abspath(__file__))+"/.."
# ---- mock Orchestrator card (v10 — 4 brain sections; Capabilities section shown) ----
X0,Y0,W,H = 330,165,348,300
MGR="#b98cf0"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"; TEAL="#136f8a"
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
def max_btn(cx,cy,col):  # maximize-height control: bordered button + vertical-expand glyph
    return (f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="4" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<rect x="{cx-3}" y="{cy-2.5}" width="6" height="5" rx="1" fill="none" stroke="{col}" stroke-width="0.9"/>'
            f'<path d="M{cx-2},{cy-4} L{cx},{cy-5.8} L{cx+2},{cy-4}" fill="none" stroke="{col}" stroke-width="0.9" stroke-linejoin="round"/>'
            f'<path d="M{cx-2},{cy+4} L{cx},{cy+5.8} L{cx+2},{cy+4}" fill="none" stroke="{col}" stroke-width="0.9" stroke-linejoin="round"/>')
def audit_btn(cx,cy,col):  # reasoning-audit control: bordered button + magnifier glyph
    return (f'<rect x="{cx-10}" y="{cy-8}" width="20" height="16" rx="4" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<circle cx="{cx-1.5}" cy="{cy-1}" r="3.1" fill="none" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx+0.7}" y1="{cy+1.2}" x2="{cx+3.6}" y2="{cy+4}" stroke="{col}" stroke-width="1.1" stroke-linecap="round"/>')
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 720" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append('<rect x="0" y="0" width="1180" height="720" fill="#0e1116"/>')
S.append(f'<text x="590" y="34" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Orchestrator card — part names (use either the name or the .class)</text>')
S.append(f'<text x="590" y="58" fill="{MUT}" font-size="13" text-anchor="middle">same structure on every brain card · showing the Capabilities section</text>')

# card
S.append(f'<rect x="{X0}" y="{Y0}" width="{W}" height="{H}" rx="11" fill="{PANEL}" stroke="{MGR}" stroke-width="1.6"/>')
tb=34
S.append(f'<path d="M{X0} {Y0+11} q0 -11 11 -11 h{W-22} q11 0 11 11 v{tb-11} h-{W} z" fill="#2a2440"/>')
S.append(f'<line x1="{X0}" y1="{Y0+tb}" x2="{X0+W}" y2="{Y0+tb}" stroke="{MGR}" stroke-opacity="0.5"/>')
S.append(f'<text x="{X0+12}" y="{Y0+22}" fill="{MGR}" font-size="13" font-weight="700">Orchestrator</text>')
S.append(f'<rect x="{X0+104}" y="{Y0+9}" width="54" height="14" rx="7" fill="{PANEL2}" stroke="{EDGE}"/>')
S.append(f'<text x="{X0+131}" y="{Y0+19}" fill="{MUT}" font-size="7" font-weight="600" letter-spacing="0.5" text-anchor="middle">WORKING</text>')
# header right cluster — UX controls (audit, maximize) | 20px gap | card-UI (status dot, help)
S.append(audit_btn(X0+W-96, Y0+17, MGR))
S.append(max_btn(X0+W-72, Y0+17, MGR))
S.append(f'<circle cx="{X0+W-36}" cy="{Y0+17}" r="3.5" fill="{MGR}"/>')
S.append(f'<circle cx="{X0+W-16}" cy="{Y0+17}" r="7" fill="none" stroke="{MUT}"/><text x="{X0+W-16}" y="{Y0+21}" fill="{MUT}" font-size="9" text-anchor="middle">?</text>')
# pinned intent
ciy=Y0+tb+16
S.append(f'<text x="{X0+12}" y="{ciy}" fill="{INK}" font-size="10.5">Share capability fleet-wide</text>')
# section tabs: Task / Plan / Pipeline / Capabilities (Capabilities selected)
tabs=["Task","Plan","Pipeline","Capabilities"]; sel=3
ty=ciy+10; th=18; tw=(W-20)/len(tabs)
for i,t in enumerate(tabs):
    x=X0+10+i*tw; on=(i==sel)
    S.append(f'<rect x="{x:.1f}" y="{ty}" width="{tw-3:.1f}" height="{th}" rx="5" fill="{darken(MGR) if on else PANEL2}" stroke="{MGR}"/>')
    S.append(f'<text x="{x+(tw-3)/2:.1f}" y="{ty+13}" fill="{"#eafcff" if on else "#e6edf3"}" font-size="8.5" font-weight="{700 if on else 400}" text-anchor="middle">{t}</text>')
# section header: artifact name + in-section view-mode toggle
hy=ty+th+14
S.append(f'<text x="{X0+12}" y="{hy}" fill="{INK}" font-size="9" font-weight="700" letter-spacing="0.5">CAPABILITIES</text>')
# view-mode buttons = icons only (panel selected = accent fill, graph = off)
bw=22; gx=X0+W-12-bw; pxb=gx-3-bw
S.append(f'<rect x="{pxb}" y="{hy-12}" width="{bw}" height="16" rx="5" fill="{darken(MGR)}" stroke="{MGR}"/>')
S.append(panel_icon(pxb+bw/2, hy-4, "#eafcff"))
S.append(f'<rect x="{gx}" y="{hy-12}" width="{bw}" height="16" rx="5" fill="{PANEL2}" stroke="{MGR}"/>')
S.append(graph_icon(gx+bw/2, hy-4, "#e6edf3"))
# caps list (this section's content)
py=hy+22
for i,(c,b) in enumerate([("decompose",""),("allocate",""),("replan",""),("promote","↑promoted")]):
    yy=py+i*17
    S.append(f'<text x="{X0+14}" y="{yy}" fill="{INK}" font-size="10" font-weight="600">{c}</text>')
    if b: S.append(f'<rect x="{X0+78}" y="{yy-9}" width="56" height="13" rx="6" fill="none" stroke="{MUT}"/><text x="{X0+106}" y="{yy}" fill="{MUT}" font-size="8" text-anchor="middle">{b}</text>')
# per-section flags (Capabilities owns promo + gate)
fy=py+4*17+6
S.append(f'<rect x="{X0+14}" y="{fy}" width="62" height="15" rx="7" fill="#141b2c" stroke="#2c3e72"/><text x="{X0+45}" y="{fy+11}" fill="#cbd9ff" font-size="8.5" text-anchor="middle">↑ promoted</text>')
S.append(f'<rect x="{X0+82}" y="{fy}" width="48" height="15" rx="7" fill="#2a2110" stroke="#7a5417"/><text x="{X0+106}" y="{fy+11}" fill="#ffd9a8" font-size="8.5" text-anchor="middle">⊘ gated</text>')

# ---- callouts ----
def leader(x1,y1,x2,y2,col="#5c6773"):
    S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{col}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{col}"/>')
def label(x,y,name,cls,anchor="start"):
    S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="13" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    S.append(f'<text x="{x}" y="{y+15}" fill="{MUT}" font-size="11" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')

# TOP
label(X0+12,120,"Name label","(brain name)"); leader(X0+40,126,X0+40,Y0+10)
label(X0+150,120,"Card state",".state  (status chip)"); leader(X0+172,126,X0+131,Y0+8)
label(905,95,"Reasoning audit",".auditbtn  (UX)"); leader(903,91,X0+W-96,Y0+9)
label(905,128,"Maximize height",".maxbtn  (UX)"); leader(903,124,X0+W-72,Y0+9)
label(905,161,"Status dot",".dot  (card UI)"); leader(903,157,X0+W-36,Y0+15)
label(905,194,"Help / tooltip",".help  (card UI)"); leader(903,190,X0+W-16,Y0+17)

# LEFT
label(300,Y0+6,"Card",".dcard.mgr",anchor="end"); leader(305,Y0+2,X0,Y0+2)
label(300,ciy-2,"Intent line (pinned)",".cintent",anchor="end"); leader(305,ciy-6,X0+12,ciy-4)
label(300,ty+8,"Brain sections",".bsections → .bsec",anchor="end"); leader(305,ty+6,X0+10,ty+9)
label(300,hy+2,"Section name",".sechdr .artname",anchor="end"); leader(305,hy-2,X0+12,hy-3)
label(300,fy+46,"Section body",".scroll → .secbody",anchor="end"); leader(305,fy+42,X0,fy+30)

# RIGHT
label(720,hy+2,"View mode (in section)",".vtog → .vmb  (icons)"); leader(716,hy-2,X0+W-22,hy-4)
label(720,py+8,"Capabilities",".caps → .cap + .badge"); leader(716,py+4,X0+140,py)
label(720,fy+10,"Flags (this section)",".flagrow → .flag"); leader(716,fy+6,X0+132,fy+7)

# BOTTOM captions
cy0=Y0+H+36
S.append(f'<text x="590" y="{cy0}" fill="{INK}" font-size="12.5" text-anchor="middle">All tabs/buttons share one class (.uitab): accent border + white text; selected = darker accent fill + white text. Accent is per-card.</text>')
S.append(f'<text x="590" y="{cy0+20}" fill="{MUT}" font-size="11.5" text-anchor="middle">View-mode icons (panel / graph) are white, no text. All four sections are always available. Header right: UX controls (audit, maximize), a 20px gap, then card-UI (status dot, help).</text>')

S.append("</svg>")
svg="".join(S)
cairosvg.svg2png(bytestring=svg.encode(),write_to=os.path.join(_OUT,"orchestrator_card_map.png"),output_width=1180,output_height=720,background_color="#0e1116")
print("rendered")
