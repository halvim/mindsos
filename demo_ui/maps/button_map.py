import cairosvg
import os
_OUT=os.path.dirname(os.path.abspath(__file__))+"/.."
BG="#0e1116"; PANEL2="#1c232d"; INK="#e6edf3"; MUT="#8b98a5"; WHITE="#eafcff"; EDGE="#2b333d"
def darken(h,t=0.70):
    h=h.lstrip("#"); r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return "#%02x%02x%02x"%(round(r*t+14*(1-t)),round(g*t+17*(1-t)),round(b*t+22*(1-t)))
ACCENTS=[("Orchestrator","#b98cf0"),("Arm 1","#3a8be0"),("Arm 2","#d98040"),("Conveyor","#48c78e"),("User","#53b0be")]
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 430" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect width="1000" height="430" fill="{BG}"/>')
S.append(f'<text x="500" y="34" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">Button map — the .uitab class (every card tab / toggle)</text>')
S.append(f'<text x="500" y="56" fill="{MUT}" font-size="12.5" text-anchor="middle">idle = panel bg + accent border + white text · selected (.on) = accent fill + white text · accent is per-card</text>')
def panel_icon(cx,cy,col):
    return (f'<rect x="{cx-5}" y="{cy-5}" width="10" height="10" rx="1.5" fill="none" stroke="{col}" stroke-width="1.2"/>'
            f'<line x1="{cx-3}" y1="{cy-2}" x2="{cx+3}" y2="{cy-2}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx-3}" y1="{cy}" x2="{cx+3}" y2="{cy}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{cx-3}" y1="{cy+2}" x2="{cx+1}" y2="{cy+2}" stroke="{col}" stroke-width="1"/>')
def graph_icon(cx,cy,col):
    ax,ay,bx,by,dx,dy=cx-4,cy-3,cx+4,cy-3.5,cx,cy+4
    return (f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{ax}" y1="{ay}" x2="{dx}" y2="{dy}" stroke="{col}" stroke-width="1"/>'
            f'<line x1="{bx}" y1="{by}" x2="{dx}" y2="{dy}" stroke="{col}" stroke-width="1"/>'
            f'<circle cx="{ax}" cy="{ay}" r="1.7" fill="{col}"/><circle cx="{bx}" cy="{by}" r="1.7" fill="{col}"/><circle cx="{dx}" cy="{dy}" r="1.7" fill="{col}"/>')
def btn(x,y,w,h,acc,sel,label=None,icon=None):
    fill=darken(acc) if sel else PANEL2; col=WHITE if sel else INK
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{acc}" stroke-width="1.2"/>')
    if icon=="panel": S.append(panel_icon(x+w/2,y+h/2,col))
    elif icon=="graph": S.append(graph_icon(x+w/2,y+h/2,col))
    else: S.append(f'<text x="{x+w/2}" y="{y+h/2+4}" fill="{col}" font-size="11" font-weight="{600 if sel else 400}" text-anchor="middle">{label}</text>')
def heading(x,y,t): S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="13.5" font-weight="700">{t}</text>')
def note(x,y,t,col=MUT): S.append(f'<text x="{x}" y="{y}" fill="{col}" font-size="10.5">{t}</text>')
def mono(x,y,t): S.append(f'<text x="{x}" y="{y}" fill="{MUT}" font-size="10.5" font-family="ui-monospace,Menlo,monospace">{t}</text>')

P="#b98cf0"
heading(60,100,"1 · Two states")
btn(60,112,96,28,P,False,label="Plan"); note(60,156,"idle"); mono(60,170,".uitab")
btn(250,112,110,28,P,True,label="Plan"); note(250,156,"selected"); mono(250,170,".uitab.on")
note(430,124,"border + (when selected) fill = the card accent.",INK)
note(430,142,"text is always white; only the fill changes.")

heading(60,232,"2 · Accent is per-card")
x=60
for name,acc in ACCENTS:
    note(x,250,name,INK); btn(x,258,64,24,acc,False,label="Tab"); btn(x+72,258,64,24,acc,True,label="Tab"); x+=185

heading(60,338,"3 · Variants")
note(60,360,"text tab",INK)
btn(60,368,96,26,P,False,label="Plan"); btn(166,368,96,26,P,True,label="Plan")
mono(60,412,".bsec · .tabs · .tsbtn · .ptype")
note(470,360,"icon toggle (view-mode)",INK)
btn(470,368,40,26,P,False,icon="panel"); btn(514,368,40,26,P,True,icon="panel")
btn(566,368,40,26,P,False,icon="graph"); btn(610,368,40,26,P,True,icon="graph")
mono(470,412,".vmb   (panel icon / graph icon)")

S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(),write_to=os.path.join(_OUT,"button_map.png"),output_width=1000,output_height=430,background_color=BG)
print("rendered")
