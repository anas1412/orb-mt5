"""The rules diagram, generated so the geometry is checkable rather than eyeballed.

Two linear scales and nothing else:
    x(m) = 100 + 10*m      minutes after 00:00 UTC
    y(v) = 260 - 100*v     v is position in the range: 0 = low, 1 = high

The stop sits at the range midpoint, so risk = half the range = 0.5 in v, and
every R level falls out of that: entry v=1.0, +0.5R v=1.25, +2R v=2.0,
-0.5R v=0.75, -1R (the first stop) v=0.5.
"""
X0, PXM = 100, 10
def X(m): return X0 + PXM * m
def Y(v): return 260 - 100 * v

R      = 0.5                      # one R in v units
ENTRY_M, TRIG_M, WIN_M = 22, 35, 60
CAP_M  = ENTRY_M + 60
AXIS_Y, H, W = 300, 400, 1080

# the fifteen range candles: o, h, l, c in v units
RANGE = [(.55,.62,.48,.50),(.50,.58,.42,.44),(.44,.50,.30,.34),(.34,.40,.12,.18),
         (.18,.28,.00,.22),(.22,.38,.18,.35),(.35,.44,.30,.40),(.40,.52,.36,.48),
         (.48,.60,.44,.58),(.58,.72,.54,.68),(.68,.78,.62,.70),(.70,.86,.66,.82),
         (.82,1.0,.78,.94),(.94,.98,.84,.88),(.88,.96,.82,.90)]
# the entry window, 00:15 to 00:21 -- the last one closes outside the box
WINDOW = [(.90,.97,.86,.92),(.92,.94,.84,.88),(.88,.99,.86,.95),(.95,.97,.87,.90),
          (.90,1.00,.88,.98),(.98,1.00,.92,.94),(.94,1.05,.93,1.02)]
# the trade, once filled
PATH = [(ENTRY_M,1.03),(24,1.10),(28,1.05),(32,1.18),(TRIG_M,1.25),
        (40,1.22),(45,1.38),(50,1.32),(55,1.60),(58,1.75),(WIN_M,2.00)]

def candle(m, o, h, l, c, hi=False):
    up = c >= o
    col = "var(--pos)" if up else "var(--neg)"
    x, mid = X(m) + 2, X(m) + 5
    top, bot = Y(max(o, c)), Y(min(o, c))
    w = 2.4 if hi else 1.4
    return ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="%.1f"/>'
            '<rect x="%d" y="%.1f" width="6" height="%.1f" fill="%s"%s/>'
            % (mid, Y(h), mid, Y(l), col, w, x, top, max(bot - top, 1.6), col,
               ' stroke="var(--ink)" stroke-width="1.2"' if hi else ''))

def build():
    s = []
    a = s.append
    a('<svg viewBox="0 0 %d %d" width="100%%" role="img">' % (W, H))
    a('<title>One trading day, start to finish</title>')
    a('<desc>A time axis in minutes after midnight UTC and a price axis in R. '
      'Fifteen one-minute candles form the range box; the last one closes in the '
      'top half, so only an upward break may be traded. In the 00:15 to 00:29 '
      'window a candle closes above the box, the trade is entered at market, the '
      'stop goes at the range midpoint and the target two R above entry. At plus '
      'half an R the stop moves up to minus half an R. Anything still open sixty '
      'minutes after entry is closed. A footer strip shows Monday to Thursday '
      'traded and Friday skipped.</desc>')
    a('<defs><marker id="arR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
      'markerHeight="6" orient="auto-start-reverse"><path d="M2 1L8 5L2 9" fill="none" '
      'stroke="context-stroke" stroke-width="1.8" stroke-linecap="round"/></marker></defs>')

    a('<text x="%d" y="26" font-size="14.5" font-weight="700" fill="currentColor">'
      'Every decision is made in the first 30 minutes.</text>' % X0)

    # ---- the 00:15-00:29 window, shaded ----
    a('<rect x="%d" y="106" width="%d" height="%d" fill="var(--acc)" opacity=".05"/>'
      % (X(15), X(30) - X(15), 284 - 106))

    # ---- the range box, with its top half marked ----
    a('<rect x="%d" y="%.0f" width="%d" height="%.0f" fill="currentColor" opacity=".05"/>'
      % (X0, Y(1), X(15) - X0, Y(0) - Y(1)))
    a('<rect x="%d" y="%.0f" width="%d" height="%.0f" fill="var(--pos)" opacity=".2"/>'
      % (X0, Y(1), X(15) - X0, Y(1) - Y(.5)))
    a('<text x="%d" y="%.0f" font-size="11" font-weight="640" fill="var(--pos)" '
      'fill-opacity=".8">TOP HALF</text>' % (X0 + 6, Y(1) + 16))
    for v, wd in ((1, 1.8), (0, 1.8)):
        a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="currentColor" stroke-width="%.1f"/>'
          % (X0, Y(v), X(15), Y(v), wd))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--acc)" stroke-width="1.6" '
      'stroke-dasharray="7 5"/>' % (X0 - 6, Y(.5), X(15) + 6, Y(.5)))
    a('<text x="%d" y="%.0f" font-size="12.5" fill="currentColor" fill-opacity=".62">'
      '15-minute range</text>' % (X0, Y(1) - 16))

    # ---- candles ----
    for i, c in enumerate(RANGE):
        a(candle(i, *c, hi=(i == 14)))
    for i, c in enumerate(WINDOW):
        a(candle(15 + i, *c, hi=(i == 6)))

    # ---- the filter, called out on the candle that decides it ----
    a('<text x="%d" y="60" font-size="13.5" font-weight="700" fill="var(--pos)">'
      '00:14 closed in the TOP half</text>' % X0)
    a('<text x="%d" y="80" font-size="12.5" fill="currentColor" fill-opacity=".72">'
      'so only an up-break counts today</text>' % X0)
    a('<path d="M%d 90 L%d %.0f" fill="none" stroke="var(--pos)" stroke-width="1.8" '
      'stroke-opacity=".7" marker-end="url(#arR)"/>' % (X0 + 30, X(14) + 3, Y(.96)))

    # ---- levels, from the fill onward ----
    xe = X(ENTRY_M)
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--pos)" stroke-width="1.6" '
      'stroke-dasharray="7 5"/>' % (xe, Y(1 + 2 * R), X(90), Y(1 + 2 * R)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--acc2)" stroke-width="1.4" '
      'stroke-dasharray="6 4"/>' % (xe, Y(1 + .5 * R), X(90), Y(1 + .5 * R)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="currentColor" stroke-opacity=".4" '
      'stroke-width="1.6"/>' % (xe, Y(1), X(90), Y(1)))
    # first stop, then the move
    xt = X(TRIG_M)
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--neg)" stroke-width="2" '
      'stroke-dasharray="9 5"/>' % (xe, Y(1 - R), xt, Y(1 - R)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--neg)" stroke-opacity=".28" '
      'stroke-width="1.4" stroke-dasharray="3 6"/>' % (xt, Y(1 - R), X(90), Y(1 - R)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="var(--neg)" stroke-width="2.2" '
      'stroke-dasharray="9 5"/>' % (xt, Y(1 - .5 * R), X(90), Y(1 - .5 * R)))
    a('<path d="M%d %.0f L%d %.0f" fill="none" stroke="var(--neg)" stroke-width="3" '
      'marker-end="url(#arR)"/>' % (xt + 16, Y(1 - R) - 4, xt + 16, Y(1 - .5 * R) + 6))

    # ---- the trade ----
    a('<path d="%s" fill="none" stroke="var(--pos)" stroke-width="2.8" stroke-linejoin="round"/>'
      % (" ".join(("M%d %.0f" if i == 0 else "L%d %.0f") % (X(m), Y(v))
                  for i, (m, v) in enumerate(PATH))))
    a('<circle cx="%d" cy="%.0f" r="6.5" fill="var(--ink)"/>' % (xe, Y(1.03)))
    a('<line x1="%d" y1="%.0f" x2="%d" y2="%.0f" stroke="currentColor" stroke-opacity=".35" '
      'stroke-dasharray="3 4"/>' % (xe, Y(1.03) + 9, xe, 232))
    a('<text x="%d" y="244" font-size="12.5" font-weight="700" fill="currentColor">'
      'enter at market</text>' % (xe - 34))
    a('<circle cx="%d" cy="%.0f" r="6.5" fill="var(--acc2)"/>' % (xt, Y(1.25)))
    a('<circle cx="%d" cy="%.0f" r="7" fill="var(--pos)"/>' % (X(WIN_M), Y(2)))
    a('<text x="%d" y="%.0f" font-size="13.5" font-weight="700" fill="var(--pos)">win</text>'
      % (X(WIN_M) + 14, Y(2) - 14))
    a('<text x="%d" y="%.0f" font-size="12.5" font-weight="640" fill="var(--neg)">'
      'stop moves up</text>' % (xt + 30, Y(.56)))

    # ---- the 60-minute cap ----
    a('<line x1="%d" y1="106" x2="%d" y2="284" stroke="var(--neg)" stroke-opacity=".45" '
      'stroke-width="1.5" stroke-dasharray="4 5"/>' % (X(CAP_M), X(CAP_M)))
    a('<text x="%d" y="244" font-size="12.5" fill="var(--neg)" fill-opacity=".8" '
      'text-anchor="end">flat 60 min after entry</text>' % (X(CAP_M) - 10))

    # ---- right-hand level labels ----
    for v, lab, col in ((1 + 2 * R, "+2R", 'fill="var(--pos)" font-weight="640"'),
                        (1 + .5 * R, "+0.5R", 'fill="var(--acc)"'),
                        (1, "entry", 'fill="currentColor" fill-opacity=".65"'),
                        (1 - .5 * R, "&minus;0.5R", 'fill="var(--neg)" font-weight="640"'),
                        (1 - R, "&minus;1R", 'fill="var(--neg)" fill-opacity=".5"')
                        ):
        a('<text x="%d" y="%.0f" font-size="12.5" %s>%s</text>' % (X(90) + 10, Y(v) + 4, col, lab))

    # ---- time axis ----
    a('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="currentColor" stroke-opacity=".25" '
      'stroke-width="1.5"/>' % (X0, AXIS_Y, X(90), AXIS_Y))
    for m, lab in ((0, "00:00"), (15, "00:15"), (30, "00:30"), (60, "01:00"), (90, "01:30")):
        a('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="currentColor" stroke-opacity=".3"/>'
          % (X(m), AXIS_Y - 5, X(m), AXIS_Y + 5))
        a('<text x="%d" y="%d" font-size="11.5" fill="currentColor" fill-opacity=".55" '
          'text-anchor="middle">%s</text>' % (X(m), AXIS_Y + 22, lab))
    a('<text x="%d" y="%.0f" font-size="12" fill="var(--acc)" fill-opacity=".95" '
      'text-anchor="middle">break window</text>' % ((X(15) + X(30)) // 2, 290))

    # ---- day strip ----
    top, ph, pw, gap = 338, 32, 88, 8
    for i, day in enumerate(("MON", "TUE", "WED", "THU", "FRI")):
        x = X0 + i * (pw + gap)
        off = (day == "FRI")
        a('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="%s" opacity="%s"/>'
          % (x, top, pw, ph, "var(--neg)" if off else "var(--pos)", ".13" if off else ".16"))
        a('<text x="%d" y="%d" font-size="12.5" font-weight="700" fill="%s"%s '
          'text-anchor="middle">%s</text>'
          % (x + pw // 2, top + 21, "var(--neg)" if off else "var(--pos)",
             ' fill-opacity=".7"' if off else '', day))
        if off:
            a('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="var(--neg)" stroke-width="2"/>'
              % (x + 14, top + ph - 10, x + pw - 14, top + 10))
    a('<text x="%d" y="%d" font-size="12.5" fill="currentColor" fill-opacity=".7">'
      'Friday off &mdash; the only losing day of the week</text>'
      % (X0 + 5 * (pw + gap) + 8, top + 21))
    a('</svg>')
    return "\n".join(s)

if __name__ == "__main__":
    print(build())
