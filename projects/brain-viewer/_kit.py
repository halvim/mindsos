"""Shared draw helpers for the brain-viewer callout map (arc1 demo_ui style).

Palette overridden to match the live `view`-verb viewer
(mindsos_cli/commands/brain_viz_template.html).
"""
import os
import cairosvg

OUT = os.path.dirname(os.path.abspath(__file__))

# viewer palette (from the template :root vars)
BG = "#0d0f14"; PANEL = "#161a22"; PANEL2 = "#0e1218"; LINE = "#252b36"
INK = "#e6e9ef"; DIM = "#8b93a3"; ACCENT = "#7aa2ff"; OK = "#3ddc84"
WARN = "#ffb454"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def R(x, y, w, h, rx, fill, stroke=None, sw=1):
    s = f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{sw}"'
    return s + '/>'


def T(x, y, txt, fill, size, weight=400, anchor="start", mono=False, ls=None):
    fam = ' font-family="ui-monospace,Menlo,monospace"' if mono else ''
    wt = f' font-weight="{weight}"' if weight != 400 else ''
    l = f' letter-spacing="{ls}"' if ls else ''
    return (f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}"{wt}{fam}{l} '
            f'text-anchor="{anchor}">{esc(txt)}</text>')


def chip(x, y, w, txt, fg, bd, bgc, dim=False, h=20):
    op = ' opacity="0.55"' if dim else ''
    return (f'<g{op}>' + R(x, y, w, h, 5, bgc, bd)
            + T(x + w / 2, y + h - 6, txt, fg, 10.5, anchor="middle", mono=True) + '</g>')


def sw(x, y, color, s=13):
    return R(x, y, s, s, 3, color, "#0008")


def lead(x1, y1, x2, y2, c="#5c6773"):
    return (f'<polyline points="{x1:.0f},{y1:.0f} {x2:.0f},{y2:.0f}" fill="none" '
            f'stroke="{c}" stroke-width="1.1"/>'
            f'<circle cx="{x2:.0f}" cy="{y2:.0f}" r="2.6" fill="{c}"/>')


def lab(x, y, name, cls, anchor="start", col=INK):
    out = T(x, y, name, col, 12, 600, anchor)
    if cls:
        out += T(x, y + 13, cls, DIM, 10, anchor=anchor, mono=True)
    return out


def header(S, W, title, sub):
    S.append(T(W / 2, 34, title, INK, 21, 700, "middle"))
    S.append(T(W / 2, 57, sub, DIM, 12.5, anchor="middle"))


def footer(S, W, H, txt):
    S.append(T(W / 2, H - 24, txt, DIM, 11.5, anchor="middle"))


def render(S, name, W, H):
    S.insert(0, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">')
    S.insert(1, R(0, 0, W, H, 0, BG))
    S.append("</svg>")
    cairosvg.svg2png(bytestring="".join(S).encode(),
                     write_to=os.path.join(OUT, name),
                     output_width=W, output_height=H, background_color=BG)
    print("rendered", name)
