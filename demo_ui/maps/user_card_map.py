import cairosvg
import os
_OUT=os.path.dirname(os.path.abspath(__file__))+"/.."
BG="#0e1116"; PANEL="#161b22"; PANEL2="#1c232d"; EDGE="#2b333d"; INK="#e6edf3"; MUT="#8b98a5"; WHITE="#eafcff"; LINE="#4a5563"
U="#53b0be"; UD="#3e808c"
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
X0,Y0,W,H=330,150,362,392
S=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 740" font-family="Segoe UI,Helvetica,Arial,sans-serif">']
S.append(f'<rect width="1180" height="740" fill="{BG}"/>')
S.append(f'<text x="590" y="34" fill="{INK}" font-size="20" font-weight="700" text-anchor="middle">User card — part names (use either the name or the .class)</text>')
S.append(f'<text x="590" y="58" fill="{MUT}" font-size="13" text-anchor="middle">where you drive the system · showing the Order pane</text>')
# card + title bar
S.append(f'<rect x="{X0}" y="{Y0}" width="{W}" height="{H}" rx="11" fill="{PANEL}" stroke="{U}" stroke-width="1.6"/>')
tb=34
S.append(f'<path d="M{X0} {Y0+11} q0 -11 11 -11 h{W-22} q11 0 11 11 v{tb-11} h-{W} z" fill="#15252a"/>')
S.append(f'<line x1="{X0}" y1="{Y0+tb}" x2="{X0+W}" y2="{Y0+tb}" stroke="{U}" stroke-opacity="0.5"/>')
S.append(f'<text x="{X0+12}" y="{Y0+22}" fill="{U}" font-size="13" font-weight="700">User</text>')
S.append(f'<rect x="{X0+50}" y="{Y0+9}" width="44" height="14" rx="7" fill="{PANEL2}" stroke="{EDGE}"/><text x="{X0+72}" y="{Y0+19}" fill="{MUT}" font-size="7" font-weight="600" letter-spacing="0.5" text-anchor="middle">ORDER</text>')
S.append(f'<rect x="{X0+W-118}" y="{Y0+8}" width="62" height="16" rx="5" fill="#1f6feb"/><text x="{X0+W-87}" y="{Y0+19}" fill="#fff" font-size="9" text-anchor="middle">▶ Submit</text>')
S.append(f'<rect x="{X0+W-52}" y="{Y0+8}" width="34" height="16" rx="5" fill="{PANEL2}" stroke="{EDGE}"/><text x="{X0+W-35}" y="{Y0+19}" fill="{INK}" font-size="9" text-anchor="middle">clear</text>')
S.append(f'<circle cx="{X0+W-14}" cy="{Y0+16}" r="6.5" fill="none" stroke="{MUT}"/><text x="{X0+W-14}" y="{Y0+19}" fill="{MUT}" font-size="8" text-anchor="middle">?</text>')
# tabs — boxed task / system groups
ty=Y0+48
def tab(x,y,w,sel,label,dashed=False,pencil=False,h=22):
    fill=UD if sel else PANEL2; col=WHITE if sel else INK
    dash=' stroke-dasharray="3 2"' if dashed else ''
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{U}" stroke-width="1.2"{dash}/>')
    tx=x+w/2
    if pencil:
        px=x+w/2-24
        S.append(f'<path d="M{px} {y+15} L{px+0.4} {y+12.6} L{px+7} {y+6} L{px+9} {y+8} L{px+2.4} {y+14.6} Z" fill="none" stroke="{col}" stroke-width="1.1" stroke-linejoin="round"/>')
        tx=x+w/2+5
    S.append(f'<text x="{tx}" y="{y+15}" fill="{col}" font-size="11" font-weight="{600 if sel else 400}" text-anchor="middle">{label}</text>')
# task box
S.append(f'<rect x="{X0+12}" y="{ty}" width="206" height="38" rx="8" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
S.append(f'<rect x="{X0+24}" y="{ty-7}" width="32" height="13" rx="2" fill="{PANEL}"/><text x="{X0+28}" y="{ty+3}" fill="{U}" font-size="8" font-weight="700" letter-spacing="0.5">TASK</text>')
tab(X0+20,ty+8,90,True,"Order"); tab(X0+114,ty+8,90,False,"Sort")
# system box
sxb=X0+230
S.append(f'<rect x="{sxb}" y="{ty}" width="120" height="38" rx="8" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
S.append(f'<rect x="{sxb+12}" y="{ty-7}" width="88" height="13" rx="2" fill="{PANEL}"/><text x="{sxb+16}" y="{ty+3}" fill="{U}" font-size="8" font-weight="700" letter-spacing="0.5">CHANGE SYSTEM</text>')
tab(sxb+8,ty+8,104,False,"Teach",dashed=True,pencil=True)
# Order pane content
py=ty+38+24
S.append(f'<text x="{X0+14}" y="{py}" fill="{U}" font-size="10.5" font-weight="600">1. Object</text>')
shapes=[("Box","#cab43c","sq","both"),("Sheet","#66bf72","rect","suction"),("Tube","#b3598c","circ","jaw")]
sx=X0+14; sw=104; sgap=6
for i,(nm,c,shape,lim) in enumerate(shapes):
    x=sx+i*(sw+sgap); selb=(i==0)
    S.append(f'<rect x="{x}" y="{py+6}" width="{sw}" height="34" rx="7" fill="#0e131a" stroke="{U if selb else EDGE}" stroke-width="{1.4 if selb else 1}"/>')
    cxv=x+18; cyv=py+23
    if shape=="sq": S.append(f'<rect x="{cxv-7}" y="{cyv-7}" width="14" height="14" rx="2" fill="{c}"/>')
    elif shape=="rect": S.append(f'<rect x="{cxv-9}" y="{cyv-4}" width="18" height="8" rx="2" fill="{c}"/>')
    else: S.append(f'<circle cx="{cxv}" cy="{cyv}" r="8" fill="{c}"/>')
    S.append(f'<text x="{x+38}" y="{py+20}" fill="{INK}" font-size="9.5">{nm}</text>')
    S.append(f'<text x="{x+38}" y="{py+32}" fill="{MUT}" font-size="7.5">{lim}</text>')
py2=py+58
S.append(f'<text x="{X0+14}" y="{py2}" fill="{U}" font-size="10.5" font-weight="600">2. Shelf rack</text>')
S.append(f'<rect x="{X0+96}" y="{py2-12}" width="70" height="16" rx="4" fill="#0e131a" stroke="{EDGE}"/><text x="{X0+102}" y="{py2}" fill="{INK}" font-size="9">Arm 1  ▾</text>')
py3=py2+30
S.append(f'<text x="{X0+14}" y="{py3}" fill="{U}" font-size="10.5" font-weight="600">3. Position <tspan fill="{INK}" font-weight="400" font-size="8.5">(compose with +)</tspan></text>')
bx=X0+14; by=py3+8
for j,(lab,wd) in enumerate([("relational ▾",74),("above ▾",54),("Box ▾",48)]):
    S.append(f'<rect x="{bx}" y="{by}" width="{wd}" height="16" rx="4" fill="#0e131a" stroke="{EDGE}"/><text x="{bx+5}" y="{by+12}" fill="{INK}" font-size="8.5">{lab}</text>')
    bx+=wd+5
S.append(f'<rect x="{bx}" y="{by}" width="20" height="16" rx="4" fill="{PANEL2}" stroke="{EDGE}"/><text x="{bx+10}" y="{by+12}" fill="{MUT}" font-size="9" text-anchor="middle">×</text>')
S.append(f'<rect x="{X0+14}" y="{by+24}" width="64" height="16" rx="4" fill="{PANEL2}" stroke="{EDGE}"/><text x="{X0+46}" y="{by+36}" fill="{INK}" font-size="8.5" text-anchor="middle">+ position</text>')
S.append(f'<text x="{X0+14}" y="{by+62}" fill="{MUT}" font-size="9">order list:  no lines yet</text>')
# callouts
def leader(x1,y1,x2,y2,col="#5c6773"):
    S.append(f'<polyline points="{x1},{y1} {x2},{y2}" fill="none" stroke="{col}" stroke-width="1.1"/><circle cx="{x2}" cy="{y2}" r="2.6" fill="{col}"/>')
def label(x,y,name,cls,anchor="start"):
    S.append(f'<text x="{x}" y="{y}" fill="{INK}" font-size="13" font-weight="600" text-anchor="{anchor}">{esc(name)}</text>')
    S.append(f'<text x="{x}" y="{y+15}" fill="{MUT}" font-size="11" font-family="ui-monospace,Menlo,monospace" text-anchor="{anchor}">{esc(cls)}</text>')
label(X0+8,116,"Name label","(card name)"); leader(X0+30,122,X0+24,Y0+10)
label(X0+96,110,"Card state",".state"); leader(X0+120,116,X0+72,Y0+9)
label(X0+W-44,98,"Submit / clear","#o_run · #o_clear",anchor="end"); leader(X0+W-90,104,X0+W-100,Y0+8)
label(905,150,"Help / tooltip",".help"); leader(903,146,X0+W-14,Y0+12)
label(300,Y0+6,"Card",".dcard.user",anchor="end"); leader(305,Y0+2,X0,Y0+2)
label(300,ty+4,"Task / system groups",".tgroup · .tglabel",anchor="end"); leader(305,ty+2,X0+12,ty+12)
label(300,by+12,"Body / pane",".scroll → #pane_order",anchor="end"); leader(305,by+8,X0,by)
label(720,ty+10,"Teach · change system",".teachtab  (#tab_teach)"); leader(716,ty+6,sxb+112,ty+19)
label(720,py+10,"Object picker",".shapes → .shape"); leader(716,py+6,sx+3*(sw+sgap)-sgap,py+22)
label(720,py2+2,"Shelf rack","#o_shelf"); leader(716,py2-2,X0+166,py2-4)
label(720,py3+12,"Position builder",".pbrow rows · + position"); leader(716,py3+8,X0+14+176,by+8)
label(720,by+58,"Order list","#o_list"); leader(716,by+54,X0+120,by+59)
cy0=Y0+H+38
S.append(f'<text x="590" y="{cy0}" fill="{INK}" font-size="12.5" text-anchor="middle">Order + Sort = ask the system to do a task. Teach = change the system (its learnable substrate).</text>')
S.append(f'<text x="590" y="{cy0+20}" fill="{MUT}" font-size="11.5" text-anchor="middle">The two groups are bordered boxes; the gap between them is the divider. The pane (.scroll) swaps per tab.</text>')
S.append("</svg>")
cairosvg.svg2png(bytestring="".join(S).encode(),write_to=os.path.join(_OUT,"user_card_map.png"),output_width=1180,output_height=740,background_color=BG)
print("ok")
