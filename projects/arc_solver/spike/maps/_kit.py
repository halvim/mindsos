"""Shared draw helpers for the arc1 callout maps (demo_ui style)."""
import os
import cairosvg

OUT = os.path.dirname(os.path.abspath(__file__)) + "/.."

BG = "#11131a"; PANEL = "#1a1d27"; PANEL2 = "#222634"; LINE = "#2e3344"
INK = "#e7e9f0"; DIM = "#9aa3b8"; ACCENT = "#7aa2ff"; OK = "#3ddc84"
WARN = "#ffb454"; TOUCH = "#A78BFA"
RED = "#FF4136"; BLUE = "#0074D9"; GREEN = "#2ECC40"; AMBER = "#EF9F27"


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
    return (f'<g{op}>' + R(x, y, w, h, 6, bgc, bd)
            + T(x + w / 2, y + h - 6, txt, fg, 10.5, anchor="middle") + '</g>')


def lead(x1, y1, x2, y2, c="#5c6773"):
    return (f'<polyline points="{x1:.0f},{y1:.0f} {x2:.0f},{y2:.0f}" fill="none" '
            f'stroke="{c}" stroke-width="1.1"/>'
            f'<circle cx="{x2:.0f}" cy="{y2:.0f}" r="2.6" fill="{c}"/>')


def lab(x, y, name, cls, anchor="start", col=INK):
    out = T(x, y, name, col, 12, 600, anchor)
    if cls:
        out += T(x, y + 13, cls, DIM, 10, anchor=anchor, mono=True)
    return out


def divider(x1, y, x2):
    return f'<line x1="{x1:.0f}" y1="{y:.0f}" x2="{x2:.0f}" y2="{y:.0f}" stroke="{LINE}"/>'


def header(S, W, title, sub):
    S.append(T(W / 2, 32, title, INK, 20, 700, "middle"))
    S.append(T(W / 2, 55, sub, DIM, 12.5, anchor="middle"))


def footer(S, W, H, txt):
    S.append(T(W / 2, H - 26, txt, DIM, 11.5, anchor="middle"))


def render(S, name, W, H):
    S.insert(0, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                f'font-family="Segoe UI,Helvetica,Arial,sans-serif">')
    S.insert(1, R(0, 0, W, H, 0, BG))
    S.append("</svg>")
    cairosvg.svg2png(bytestring="".join(S).encode(),
                     write_to=os.path.join(OUT, name),
                     output_width=W, output_height=H, background_color=BG)
    print("rendered", name)
