"""The half-of-the-range diagram. Both panels share one vertical scale and the
numbers are read from halves.json, so the picture cannot drift from the data.

    y(v) = 250 - 130*v      v is position in the range: 0 = low, 1 = high
"""
import json

W, H = 1080, 430
PW, PH = 495, 270          # panel size
PANELS = (30, 555)         # panel left edges
BOX_L, BOX_W = 120, 210    # box offset inside a panel, and its width
def Y(v): return 250 - 130 * v

# each panel: (heading, subheading, the 00:14 candle as open/high/low/close in v,
#             which break is taken, accent colour)
LEFT  = ("Closed in the TOP half",    "up-breaks only",
         (.72, .94, .66, .88), "up",   "var(--pos)")
RIGHT = ("Closed in the BOTTOM half", "down-breaks only",
         (.28, .34, .06, .12), "down", "var(--pos)")

def panel(px, head, sub, cndl, take, col):
    o, h, l, c = cndl
    s = []
    a = s.append
    a('<rect x="%d" y="50" width="%d" height="%d" rx="12" fill="%s" opacity=".06"/>'
      % (px, PW, PH, col))
    a('<text x="%d" y="82" font-size="15" font-weight="700" fill="%s">%s</text>'
      % (px + 24, col, head))
    a('<text x="%d" y="102" font-size="12.5" fill="currentColor" fill-opacity=".68">%s</text>'
      % (px + 24, sub))

    bx = px + BOX_L
    # the box, with the chosen half tinted
    a('<rect x="%d" y="%.0f" width="%d" height="%.0f" fill="currentColor" opacity=".045"/>'
      % (bx, Y(1), BOX_W, Y(0) - Y(1)))
    # y grows downward, so the height is always the lower y minus the upper one
    ty, th = (Y(1), Y(.5) - Y(1)) if take == "up" else (Y(.5), Y(0) - Y(.5))
    a('<rect x="%d" y="%.0f" width="%d" height="%.0f" fill="%s" opacity=".17"/>'
      % (bx, ty, BOX_W, th, col))
    a('<text x="%d" y="%.0f" font-size="11.5" font-weight="640" fill="%s" '
      'fill-opacity=".85">%s HALF</text>'
      % (bx + 10, ty + 20, col, "TOP" if take == "up" else "BOTTOM"))
    for v in (1, 0):
        a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="currentColor" stroke-width="1.8"/>'
          % (bx, Y(v), bx + BOX_W, Y(v)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--acc)" stroke-width="2" '
      'stroke-dasharray="7 5"/>' % (bx - 8, Y(.5), bx + BOX_W + 8, Y(.5)))
    for v, lab in ((1, "high"), (.5, "middle"), (0, "low")):
        bold = ' font-weight="640" fill="var(--acc)"' if v == .5 else \
               ' fill="currentColor" fill-opacity=".6"'
        a('<text x="%d" y="%.0f" font-size="12"%s text-anchor="end">%s</text>'
          % (bx - 14, Y(v) + 4, bold, lab))

    # the one candle that decides the day
    cx = bx + BOX_W - 40
    up = c >= o
    ccol = "var(--pos)" if up else "var(--neg)"
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="%s" stroke-width="2.4"/>'
      % (cx + 5, Y(h), cx + 5, Y(l), ccol))
    a('<rect x="%d" y="%.0f" width="10" height="%.0f" fill="%s" stroke="var(--ink)" '
      'stroke-width="1.1"/>' % (cx, Y(max(o, c)), Y(min(o, c)) - Y(max(o, c)), ccol))
    a('<text x="%d" y="%.0f" font-size="11.5" fill="currentColor" fill-opacity=".7" '
      'text-anchor="middle">00:14</text>' % (cx + 5, Y(1) - 10))

    # the two possible breaks
    ax = px + 400
    for d in ("up", "down"):
        good = (d == take)
        y1, y2 = (Y(1) - 4, Y(1) - 46) if d == "up" else (Y(0) + 4, Y(0) + 38)
        ac = col if good else "var(--neg)"
        a('<path d="M%d %.0f L%d %.0f" fill="none" stroke="%s" stroke-width="%s" '
          'stroke-opacity="%s" marker-end="url(#arH)"/>'
          % (ax, y1, ax, y2, ac, "3" if good else "2", "1" if good else ".45"))
        ty2 = y2 + (2 if d == "up" else 4)
        a('<text x="%d" y="%.0f" font-size="13.5" font-weight="700" fill="%s" '
          'fill-opacity="%s">%s</text>'
          % (ax + 14, ty2, ac, "1" if good else ".6", "TAKE IT" if good else "SKIP"))
        a('<text x="%d" y="%.0f" font-size="12" fill="currentColor" fill-opacity=".6">'
          'break %s</text>' % (ax + 14, ty2 + 18, "above" if d == "up" else "below"))
    return "\n".join(s)

def build(hv=None):
    hv = hv or json.load(open("halves.json"))
    s = []
    a = s.append
    a('<svg viewBox="0 0 %d %d" width="100%%" role="img">' % (W, H))
    a('<title>The half-of-the-range rule</title>')
    a('<desc>Two panels sharing one vertical scale. On the left the last candle of '
      'the range closes in the top half, so an upward break is taken and a downward '
      'break is skipped. On the right it closes in the bottom half and the rule '
      'mirrors. Below, the measured result: breaks in the same half as the close '
      'beat breaks in the opposite half on win rate and expectancy.</desc>')
    a('<defs><marker id="arH" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
      'markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" '
      'stroke="context-stroke" stroke-width="1.8" stroke-linecap="round"/></marker></defs>')
    a('<text x="30" y="28" font-size="14.5" font-weight="700" fill="currentColor">'
      'Same box, same stop, same target. Only the allowed direction changes.</text>')
    a(panel(PANELS[0], *LEFT))
    a(panel(PANELS[1], *RIGHT))

    a('<line x1="30" y1="344" x2="1050" y2="344" stroke="currentColor" stroke-opacity=".12"/>')
    rows = ((hv['same'], "Broke the half it closed in", "var(--pos)", "1"),
            (hv['opp'],  "Broke the opposite half",     "var(--neg)", ".72"))
    for i, (q, lab, col, op) in enumerate(rows):
        y = 374 + i * 26
        a('<text x="30" y="%d" font-size="13" font-weight="700" fill="%s" '
          'fill-opacity="%s">%s</text>' % (y, col, op, lab))
        a('<text x="290" y="%d" font-size="13" fill="currentColor" fill-opacity="%s">'
          '%d trades &#183; %.1f%% win rate &#183; %+.3f R each &#183; %+.1f R total '
          '&#183; %+.1f%% of the account</text>' % (y, op, q['n'], q['wr'], q['ev'],
                                                    q['total'], q['ret']))
    a('</svg>')
    return "\n".join(s)

if __name__ == "__main__":
    print(build())
