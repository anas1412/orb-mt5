"""Render the previous-day fade report from the trades pdfade_report.py found.

Reuses template.html's stylesheet so the page matches index.html, but none of
its prose -- different strategy, different claims.

    python3 studies/pdfade_page.py
"""
import os, sys, re, json, struct, datetime as dt
from collections import defaultdict
import statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)
sys.path.insert(0, HERE)
import pdfade_report as CFG
OUT_WEB = "trades-pdfade"
RR = CFG.RR        # the target, so no string on this page can disagree with it
SL_FRAC = CFG.SL_FRAC
MAX_DEPTH_PTS = CFG.MAX_DEPTH / 0.01
BE = 0.10          # a trade inside +-0.10 R is a scratch, not a win or a loss
RISK_PCT = 2.5     # the default the page renders at; the selector rescales it

_raw = json.load(open(os.path.join(RESEARCH, "data", "pdfade_trades.json")))
T = _raw["trades"]
DAYS = [dt.date.fromisoformat(x) for x in _raw["days"]]
for t in T:
    t["d"] = dt.date.fromisoformat(t["date"])
R = [t["R"] for t in T]
W = [x for x in R if x > BE]; L = [x for x in R if x < -BE]; BEn = len(R)-len(W)-len(L)
aw = sum(W)/len(W); al = sum(L)/len(L)
wr = 100.0*len(W)/(len(W)+len(L)); need = 100.0/(1+aw/abs(al))
ev = sum(R)/len(R); se = st.pstdev(R)/len(R)**0.5
pk = run = dd = 0.0; curve = []
for t in T:
    run += t["R"]; pk = max(pk, run); dd = max(dd, pk-run); curve.append(run)
def streak(win):
    b = c = 0
    for x in R:
        if (x > BE) == win and abs(x) > BE: c += 1; b = max(b, c)
        elif abs(x) > BE: c = 0
    return b
mo = defaultdict(list)
for t in T: mo[t["d"].strftime("%b")].append(t)
MONTHS = [m for m in ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec") if m in mo]
kinds = defaultdict(list)
for t in T: kinds[t["kind"]].append(t["R"])

css = re.search(r"<style>(.*?)</style>", open(os.path.join(RESEARCH,"template.html")).read(), re.S).group(1)

def sgn(v, dp=1, suf=" R"):
    return '<span class="%s">%+.*f%s</span>' % ("pos" if v > 0 else "neg", dp, v, suf)

def pct(r):
    """A percentage that follows the risk selector, in build_report.py's exact
    shape: R on the element, the number inside the span and the % sign outside,
    so the same one-line JS fills it. Never rescale an already-rounded percent."""
    return '<span data-pct="%.4f">%+.1f</span>%%' % (r, RISK_PCT * r)

# ---- equity curve, drawn as plain SVG so the page needs no library ----
w_, h_ = 1080, 300; pad = 46
lo = min(0, min(curve)); hi = max(curve)
sx = lambda i: pad + i*(w_-pad-16)/max(1, len(curve)-1)
sy = lambda v: h_-28 - (v-lo)*(h_-28-14)/max(1e-9, hi-lo)
pts = " ".join("%.1f,%.1f" % (sx(i), sy(v)) for i, v in enumerate(curve))
grid = "".join('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)" stroke-width="1"/>'
               '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%d R</text>'
               % (pad, sy(v), w_-16, sy(v), pad-8, sy(v)+4, v)
               for v in range(int(lo//5*5), int(hi)+6, 5))
mk = ""
seen = set()
for i, t in enumerate(T):
    m = t["d"].strftime("%b")
    if m not in seen:
        seen.add(m)
        mk += ('<line x1="%.1f" y1="14" x2="%.1f" y2="%d" stroke="var(--line)" stroke-dasharray="3 4"/>'
               '<text x="%.1f" y="%d" fill="var(--mut)" font-size="10.5" text-anchor="middle">%s</text>'
               % (sx(i), sx(i), h_-28, sx(i), h_-12, m))
curve_svg = ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" '
             'aria-label="Cumulative return in R across the %d trades of 2026, ending at %+.1f R">'
             '%s%s<polyline points="%s" fill="none" stroke="var(--acc)" stroke-width="2.2" '
             'stroke-linejoin="round"/><line x1="%d" y1="%.1f" x2="%d" y2="%.1f" '
             'stroke="var(--mut)" stroke-width="1"/></svg>'
             % (w_, h_, len(T), sum(R), grid, mk, pts, pad, sy(0), w_-16, sy(0)))

def pf(v):
    """Gross wins over gross losses. None when nothing lost -- an infinite
    ratio is true and says nothing, so the table prints a dash."""
    g = sum(x for x in v if x > 0); l = -sum(x for x in v if x <= 0)
    return round(g / l, 2) if l > 0 else None

def pfc(v):
    """Profit-factor cell, coloured against 1.0, the same as build_report."""
    if v is None: return '<td>&ndash;</td>'
    return '<td class="%s">%.2f</td>' % ("pos" if v >= 1 else "neg", v)

def seq_cell(ts):
    """L-L-W-W-L, wins green and losses red, so a streak is visible at a
    glance. A dot is a scratch -- inside 0.10 R, counted in neither."""
    if not ts: return "&ndash;"
    return '<span class="seq">%s</span>' % "-".join(
        '<b class="%s">%s</b>' % (("pos", "W") if t["R"] > BE else
                                  ("neg", "L") if t["R"] < -BE else ("", "."))
        for t in sorted(ts, key=lambda z: (z["d"], z["n"])))

def row(label, ts, days, seq=True, cls_row="", bold_n=False):
    """One period row, in build_report.py's column order:
       label | trading days | trades | W / L / BE | [sequence] | win rate |
       profit factor | EV per trade | total R | total %"""
    v = [t["R"] for t in ts]
    w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    if not v:
        return ('<tr class="q"><td>%s</td><td>%d</td><td>0</td><td>&ndash;</td>%s'
                '<td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td>'
                '<td>&ndash;</td></tr>' % (label, days, "<td>&ndash;</td>" if seq else ""))
    c = "pos" if sum(v) > 0 else ("neg" if sum(v) < 0 else "")
    return ('<tr%s><td><b>%s</b></td><td>%d</td>%s<td>%d / %d / %d</td>%s'
            '<td>%.1f%%</td>%s<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
            '<td class="%s"><b>%s</b></td></tr>'
            % (cls_row, label, days,
               ('<td><b>%d</b></td>' % len(v)) if bold_n else ('<td>%d</td>' % len(v)),
               len(w), len(l), len(v)-len(w)-len(l),
               ('<td>%s</td>' % seq_cell(ts)) if seq else "",
               100.0*len(w)/max(1, len(w)+len(l)), pfc(pf(v)), c, sum(v)/len(v),
               c, sum(v), c, pct(sum(v))))

QHEAD = ('<thead><tr><th>%s</th><th>Trading days</th><th>Trades</th><th>W / L / BE</th>'
         '<th>Win rate</th><th>Profit factor</th><th>EV per trade</th><th>Total R</th>'
         '<th>Total %%</th></tr></thead>')
MHEAD = ('<thead><tr><th>%s</th><th>Trading days</th><th>Trades</th><th>W / L / BE</th>'
         '<th>Sequence</th><th>Win rate</th><th>Profit factor</th><th>EV per trade</th>'
         '<th>Total R</th><th>Total %%</th></tr></thead>')

qs = defaultdict(list); qd = defaultdict(int)
for t in T: qs["Q%d" % ((t["d"].month-1)//3+1)].append(t)
for d in DAYS: qd["Q%d" % ((d.month-1)//3+1)] += 1
rows_q = "".join(row(q, qs[q], qd[q], seq=False) for q in sorted(qs))
rows_q += row("2026", T, len(DAYS), seq=False, cls_row=' class="hi"')

md = defaultdict(int)
for d in DAYS: md[d.strftime("%b")] += 1
rows_mm = "".join(row(m, mo[m], md[m]) for m in MONTHS)

# Every week of the year, including the ones that produced nothing -- a table
# that silently drops the quiet weeks flatters the strategy.
ws = defaultdict(list); wd = defaultdict(int)
for t in T: ws[t["d"].isocalendar()[:2]].append(t)
for d in DAYS: wd[d.isocalendar()[:2]] += 1
def wlab(k):
    mon = dt.date.fromisocalendar(k[0], k[1], 1)
    return "%s&nbsp;&ndash;&nbsp;%s" % (mon.strftime("%d %b"),
                                        (mon+dt.timedelta(days=4)).strftime("%d %b"))
rows_w = "".join(row(wlab(k), ws.get(k, []), wd[k], bold_n=True) for k in sorted(wd))
best_w = max(ws.values(), key=lambda v: sum(x["R"] for x in v))
worst_w = min(ws.values(), key=lambda v: sum(x["R"] for x in v))

KIND = {"tp":("hit the %gR target" % RR,"pos"),"sl":("stopped out","neg"),
        "eod":("closed at the session end","")}
rows_k = "".join('<tr><td><b>%s</b></td><td>%d</td><td>%.0f%%</td><td>%s</td><td>%s</td></tr>'
                 % (KIND[k][0], len(v), 100.0*len(v)/len(R), sgn(sum(v)/len(v), 2), sgn(sum(v)))
                 for k, v in sorted(kinds.items(), key=lambda z: -len(z[1])))

def png_size(fn):
    """Width and height straight out of the PNG header. Without these on the
    tag the browser cannot reserve the box, and a lazy-loaded card off-screen
    collapses to its caption strip -- 45px instead of 409px -- so the gallery
    looks half empty until you scroll each row into view."""
    with open(os.path.join(REPO, OUT_WEB, fn), "rb") as fh:
        d = fh.read(26)
    return struct.unpack(">II", d[16:24])

cards = ""
for t in T:
    w, h = png_size(t["file"])
    src = OUT_WEB + "/" + t["file"]
    side = "long" if t["buy"] else "short"
    cards += ('<a class="tc %s" data-outcome="%s" data-dir="%s" data-month="%s" href="%s" '
              'data-r="%+.3f"><img loading="lazy" width="%d" height="%d" src="%s" '
              'alt="%s %s, %+.2f R"><span class="tm"><b>%s</b> \u00b7 %s \u00b7 '
              '<i>%+.2f R</i> \u00b7 risk %.0f pts</span></a>'
              % ("win" if t["R"] > BE else "loss", "win" if t["R"] > BE else "loss",
                 side, t["d"].strftime("%b"), src, t["R"], w, h, src,
                 t["date"], side, t["R"], t["d"].strftime("%d %b"), side,
                 t["R"], t["risk"]/0.01))

mchips = "".join('<button class="chip" data-f="month" data-v="%s" aria-pressed="false">%s</button>' % (m, m)
                 for m in MONTHS)

HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Previous-day level fade — gold, Asia session</title>
<style>%(css)s
/* The gallery images carry width and height attributes so the browser can
   reserve each card's box before a lazy image arrives. Without height:auto the
   attribute is the used height and every thumbnail stretches to 562px tall at
   full width -- the attributes must only inform the ratio. */
.tc img{height:auto}
.calc{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px 18px;
  background:var(--panel);border:1px solid var(--line);border-radius:var(--r);
  padding:20px 22px;box-shadow:var(--sh);margin:22px 0 0}
.calc label{display:block;font-size:11px;font-weight:660;letter-spacing:.08em;
  text-transform:uppercase;color:var(--mut);margin-bottom:6px}
.calc input{width:100%%;font:inherit;font-weight:660;font-size:17px;padding:8px 10px;
  border:1px solid var(--line);border-radius:8px;background:var(--bg);color:inherit;
  text-align:right;font-variant-numeric:tabular-nums}
.calc input:focus{outline:2px solid var(--acc);outline-offset:1px}
.side{display:flex;gap:8px}
.side button{flex:1;font:inherit;font-size:13.5px;font-weight:600;padding:9px 6px;
  border:1px solid var(--line);border-radius:8px;background:transparent;color:var(--mut);cursor:pointer}
.side button[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:var(--bg)}
.out{margin:18px 0 0;border:1px solid var(--line);border-radius:var(--r);overflow:hidden}
.out table{margin:0}
.out .big td{font-size:1.15rem;font-weight:680}
.calcwarn{margin:16px 0 0;padding:12px 16px;border-radius:12px;font-size:13.5px;line-height:1.6;
  border:1px solid var(--neg);background:color-mix(in srgb,var(--neg) 9%%,transparent)}
.calcwarn b{color:var(--neg)}
.calcok{margin:16px 0 0;padding:12px 16px;border-radius:12px;font-size:13.5px;
  border-left:3px solid var(--pos);background:var(--posbg)}
</style>
</head><body><div class="wrap">

<header>
<div class="eyebrow"><span class="dot"></span>research · not the live strategy</div>
<h1>Fading yesterday's <em>high and low</em></h1>
<p class="lede">Price sweeps yesterday\u2019s extreme, fails to hold, and an M5 candle closes back inside. You
take that close and trade against the sweep. Gold, Tuesday to Friday, entries in the Asia session,
%(rr)g R target, held to the end of the day. %(year)d only — %(n)d trades.</p>

<div class="riskbar">
<label for="risk">Risk per trade</label>
<div class="riskin"><input id="risk" type="number" min="0.25" max="3.5" step="0.25" value="2.5"><span>%%</span></div>
<div class="chips">
<button data-r="1" aria-pressed="false">1%%</button>
<button data-r="1.5" aria-pressed="false">1.5%%</button>
<button data-r="2" aria-pressed="false">2%%</button>
<button data-r="2.5" aria-pressed="true">2.5%%</button>
<button data-r="3" aria-pressed="false">3%%</button></div>
<p class="risknote">Every percentage on this page is R \u00d7 risk. The R figures, the win rate and
the payoff do not move. The worst losing run on record is <b>%(wrun).1f R</b> and the worst
drawdown <b>%(dd).1f R</b>, so a 12%% maximum loss is not reached until <b>%(brk).2f%%</b> and one
losing trade breaches a 3%% daily limit past <b>3.00%%</b>.</p>
</div>
<div id="riskwarn" class="riskwarn" hidden></div>

<div class="kpi">
<div class="k big"><div class="l">Total</div><div class="v">%(tot)s</div><div class="n">%(retpct)s of the account</div></div>
<div class="k"><div class="l">Per trade</div><div class="v">%(ev)s</div><div class="n">± %(se).3f standard error</div></div>
<div class="k"><div class="l">Win rate</div><div class="v">%(wr).1f%%</div><div class="n">%(W)d won · %(L)d lost · %(BE)d scratch</div></div>
<div class="k"><div class="l">Needs</div><div class="v">%(need).1f%%</div><div class="n">%(cush)+.1f points of cushion</div></div>
<div class="k"><div class="l">Worst dip</div><div class="v">%(dd).1f R</div><div class="n">%(ddpct)s of the account</div></div>
<div class="k"><div class="l">Runs</div><div class="v">%(ws)d / %(ls)d</div><div class="n">longest win / loss streak</div></div>
</div>

<nav>
<a href="#rules"><span>01</span>The rules</a>
<a href="#calc"><span>02</span>Stop calculator</a>
<a href="#curve"><span>03</span>The curve</a>
<a href="#months"><span>04</span>Month by month</a>
<a href="#exits"><span>05</span>How trades end</a>
<a href="#honest"><span>06</span>What is weak</a>
<a href="#gal"><span>07</span>Every trade</a>
</nav>
</header>

<section id="rules">
<h2><span class="num">01</span>The rules</h2>
<p class="sub">Two numbers off yesterday's chart, then one candle to wait for.</p>
<ol class="steps">
<li><b>Mark yesterday's high and low</b><span>Those are the two levels. Subtract them for
yesterday's range — you need it for the stop.</span></li>
<li><b>Tuesday to Friday only</b><span>Monday is skipped: its levels come from Friday with a
weekend in between, so the high and low being faded are three days stale. Monday returned
<strong>&minus;0.050 R</strong> a trade against <strong>+0.527</strong> for the other four days.</span></li>
<li><b>Take entries only between 00:00 and 08:00 UTC</b><span>The Asia session. Entering during
London or New York loses money on these same rules — section 05. The <em>exit</em> is not
restricted to Asia; see rule 9.</span></li>
<li><b>Wait for a sweep</b><span>Price has to trade beyond one of the levels. Above yesterday's
high, or below yesterday's low.</span></li>
<li><b>Wait for an M5 candle to CLOSE back inside</b><span>That close is the signal the sweep
failed. A wick back inside does not count.</span></li>
<li><b>Skip it if the close ran more than 600 points back inside</b><span>By then the snap-back
has already happened and you are late. It also caps how large your stop can get.</span></li>
<li><b>Enter at market on that close</b><span>Sell if the high was swept, buy if the low was.
No limit order, no waiting for a retest.</span></li>
<li><b>Stop: yesterday's range ÷ 3, beyond the level</b><span>Measured from the level, not from
your entry — so the sweep itself cannot take you out.</span></li>
<li><b>Target: %(rr)g × your risk</b><span>Risk is entry to stop, which is a little more than
range ÷ 3 because you entered inside the level. A bigger target is deliberate: on a challenge
account you need a lump, and three wins of this size clear a 12%% goal where three smaller ones
do not.</span></li>
<li><b>Close it before the day ends \u2014 never carry it overnight</b><span>Not the end of Asia:
the position runs on through London and New York and is flat by the broker day\u2019s close. The
median trade lasts <strong>%(hmed).0f minutes</strong> and the latest exit in 2026 was %(hlast)s broker time.
Cutting the hold at 08:00 UTC instead drops the result from %(tot_r)+.1f R to <strong>%(cut_r)+.1f R</strong>,
so most of the move arrives long after the entry.</span></li>
</ol>

<div class="card">
<h3>A worked example</h3>
<p>Yesterday: high <b>4650.00</b>, low <b>4548.00</b> → range <b>10200 points</b>, ÷3 =
<b>3400 points</b>.</p>
<p>Price pokes above 4650, then an M5 candle closes back below it at <b>4646.00</b> — 400 points
back inside, under the 600 limit, so it is valid.</p>
<p><b>Sell 4646.00</b> · <b>stop 4650 + 3400 = 4684.00</b> · risk <b>3800 points</b> ·
<b>target 4646 − 9500 = 4551.00</b> &nbsp;(%(rr)g × 3800)</p>
</div>
</section>

<section id="calc">
<h2><span class="num">02</span>Stop calculator</h2>
<p class="sub">The stop is anchored to the <b>level</b>, not to your fill, so it can be worked
out before the session opens and it does not move whatever price you get. Yesterday's high and low
are the only inputs.</p>

<div class="calc">
<div><label for="cy_hi">Yesterday's high</label><input id="cy_hi" type="number" step="0.01" value="4650.00"></div>
<div><label for="cy_lo">Yesterday's low</label><input id="cy_lo" type="number" step="0.01" value="4548.00"></div>
<div><label>Which side gets swept</label><div class="side">
<button id="c_hi" aria-pressed="true">High &rarr; sell</button>
<button id="c_lo" aria-pressed="false">Low &rarr; buy</button></div></div>
</div>
<div id="c_msg"></div>

<div class="out"><table>
<tbody>
<tr><td>Yesterday's range</td><td id="o_range"></td></tr>
<tr><td>Stop distance from the level &mdash; range &times; %(slfrac).2f</td><td id="o_dist"></td></tr>
<tr><td>The level you are fading</td><td id="o_level"></td></tr>
<tr class="big"><td><b>Stop &mdash; place it here whatever your fill</b></td><td id="o_stop"></td></tr>
</tbody></table></div>

<p style="font-size:13px;color:var(--mut);margin-top:14px">Your risk is that stop distance
<b>plus</b> however far inside the level you got filled, so it is a little more than
%(slfrac).2f&nbsp;&times; the range. The rules above round the fraction to &ldquo;a third&rdquo;;
the tested constant is <b>%(slfrac).2f</b> and that is what this uses.</p>
</section>

<section id="curve">
<h2><span class="num">03</span>The curve</h2>
<p class="sub">Cumulative return in R, trade by trade, in the order they happened.</p>
<figure><div class="fig">%(curve)s</div>
<figcaption>%(n)d trades, %(year)d. R is multiples of what you risked, so the curve does not
depend on account size.</figcaption></figure>
</section>

<section id="months">
<h2><span class="num">04</span>Quarter, month, week</h2>
<p class="sub">The test that matters for a small sample: is this one lucky stretch, or all of
them? Trading days are the days <em>available</em> in the period, not the days that produced a
trade. A scratch (BE) finished within 0.10 R of flat and counts in neither the wins nor the
losses.</p>

<div class="scroll"><table>
<caption>By quarter &mdash; trading days available, trades taken, and totals</caption>
%(QHEAD)s<tbody>%(rows_q)s</tbody></table></div>

<div class="scroll"><table>
<caption>By month. The sequence is every trade in order: W won, L lost, a dot is a scratch.</caption>
%(MHEAD)s<tbody>%(rows_mm)s</tbody></table></div>

<div class="scroll"><table>
<caption>Every week of 2026. Trades taken out of the days available.</caption>
%(WHEAD)s<tbody>%(rows_w)s</tbody></table></div>

<div class="kpi" style="grid-template-columns:repeat(4,minmax(0,1fr))">
<div class="k"><div class="l">Best week</div><div class="v">%(bw)s</div><div class="n">%(bwn)d trades</div></div>
<div class="k"><div class="l">Worst week</div><div class="v">%(ww)s</div><div class="n">%(wwn)d trades</div></div>
<div class="k"><div class="l">Winning weeks</div><div class="v">%(pw)d / %(nw)d</div><div class="n">of the weeks that traded</div></div>
<div class="k"><div class="l">Profit factor</div><div class="v">%(pfall).2f</div><div class="n">%(gain)+.1f R won, %(loss)+.1f R lost</div></div>
</div>
</section>

<section id="exits">
<h2><span class="num">05</span>How trades end</h2>
<p class="sub">Median hold %(hmed).0f minutes. Targets take a median of %(htp).0f minutes; stops land in %(hsl).0f.</p>
<div class="scroll"><table>
<thead><tr><th>Exit</th><th>Count</th><th>Share</th><th>Average</th><th>Total</th></tr></thead>
<tbody>%(rows_k)s</tbody></table></div>
<p>Average win <b>%(aw)+.2f R</b>, average loss <b>%(al)+.2f R</b> — a real payoff of
<b>%(payoff).2f : 1</b>, which is why %(need).1f%% is the break-even win rate rather than 33%%.</p>
</section>

<section id="honest">
<h2><span class="num">06</span>What is weak about this</h2>
<p class="sub">Everything below is a reason not to size this like a proven edge.</p>
<div class="note"><div class="t">Small sample, and it was searched</div>
<p><b>%(n)d trades over nine months.</b> The configuration was picked from a grid of roughly a
thousand. t = <b>%(t).2f</b> — it clears the usual bar, but the usual bar assumes one test,
not a thousand.</p></div>
<div class="note"><div class="t">2026 only, and 2024–25 lose</div>
<p>These same rules lose money on 2024 and 2025. That may be regime — gold's Asia range tripled
into 2026 — or it may be that %(year)d is the year the noise happened to line up.</p></div>
<div class="note"><div class="t">The level itself may not matter</div>
<p>A placebo test replaced yesterday's high and low with the high and low from <b>ten days
ago</b>, and the search scored just as well. What is being paid for is waiting after an
overshoot, not yesterday's orders specifically.</p></div>
<div class="note"><div class="t">A day trade, but a slow one</div>
<p>Nothing is carried overnight: every one of the 65 trades closes inside the same broker day, the
latest at <b>%(hlast)s</b> broker time. But the hold is long \u2014 median <b>%(hmed).0f minutes</b>,
and the target takes a median of <b>%(htp).0f minutes</b> to arrive. <b>%(nlate)d of %(n)d exit after
22:00 broker time</b>,
so depending on where your broker sets its rollover some of them may be charged one swap. Spread is
charged at entry; swap is not modelled.</p></div>
<div class="note"><div class="t">The Monday filter rests on an argument, not on significance</div>
<p>Monday is excluded because its levels come from Friday with a weekend in between &mdash; a
mechanism, not a pattern spotted in the data. The measurement agrees but cannot carry the claim on
its own: %(mon_n)d Monday trades at <b>%(mon_ev)+.3f R</b> against <b>%(rest_ev)+.3f R</b> for
Tuesday to Friday, and shuffling the trades between the two groups beats that gap about a
<b>quarter of the time</b>. Four other weekdays were looked at, so the worst of five looking bad is
expected.</p>
<div class="scroll"><table>
<caption>Every weekday the rules produced a trade on, before the filter.</caption>
<thead><tr><th>Day</th><th>Trades</th><th>W / L</th><th>Win rate</th><th>EV per trade</th><th>Total R</th><th></th></tr></thead>
<tbody>%(rows_wd)s</tbody></table></div></div>
<div class="note"><div class="t">The 600-point skip was chosen after the fact</div>
<p>It survives a constant-risk control (so it is not just arithmetic) and sits at the
<b>98.3rd percentile</b> of dropping 17 trades at random — but seven thresholds were tried, and
correcting for that leaves it merely suggestive. Treat it as risk control with a possible bonus.</p></div>
<div class="note"><div class="t">One month carries more than its share</div>
<p>Delete the single best month (%(bestm)s) and the rest returns <b>%(evrest)+.3f R</b> a trade
against <b>%(ev_plain)+.3f R</b> with it \u2014 the result survives, but it thins. On 65 trades that
is the most useful robustness check available, and it is a check, not a result.</p></div>
<div class="good"><div class="t">What does hold up</div>
<p>Entering the moment price touches the level loses badly. Waiting for the M5 close back inside
is worth roughly <b>+0.27 R per trade</b>, and that part is stable across every cut tested.</p></div>
</section>

<section id="gal">
<h2><span class="num">07</span>Every trade</h2>
<p class="sub">All %(n)d of them. Shaded band = from the sweep to the entry candle.</p>
<div class="filters">
<div class="fgroup"><b>Result</b>
<button class="chip win" data-f="outcome" data-v="win" aria-pressed="false">Wins</button>
<button class="chip loss" data-f="outcome" data-v="loss" aria-pressed="false">Losses</button></div>
<div class="fgroup"><b>Side</b>
<button class="chip" data-f="dir" data-v="long" aria-pressed="false">Long</button>
<button class="chip" data-f="dir" data-v="short" aria-pressed="false">Short</button></div>
<div class="fgroup"><b>Month</b>%(mchips)s</div>
<div class="fcount"><b id="fc">%(n)d</b> of %(n)d shown · <button class="chip" id="clr">clear</button></div>
</div>
<div class="gal" id="gal">%(cards)s</div>
<div class="legend">
<span><i class="sw" style="background:#12694a"></i>up candle</span>
<span><i class="sw" style="background:#a8352a"></i>down candle</span>
<span>▲▼ entry · ✕ exit · dashed = entry, stop, target</span>
</div>
</section>

<footer>
<p><b>Previous-day level fade — gold.</b> Generated %(gen)s from %(n)d trades replayed over M1
bars. Research only; the live strategy is the <a href="index.html">Asia opening range</a>.</p>
</footer>
</div>

<div id="lb"><figure><img id="lbimg" alt=""><figcaption><b id="lbcap"></b><span id="lbn" class="lbn"></span></figcaption></figure>
<button class="lbbtn" id="lbprev" aria-label="Previous">‹</button>
<button class="lbbtn" id="lbnext" aria-label="Next">›</button>
<button class="lbbtn" id="lbclose" aria-label="Close">×</button></div>

<script>
var cards=[].slice.call(document.querySelectorAll('.tc')),F={},i=0;
function apply(){var n=0;cards.forEach(function(c){
  var ok=Object.keys(F).every(function(k){return !F[k].length||F[k].indexOf(c.dataset[k])>=0});
  c.hidden=!ok;if(ok)n++});document.getElementById('fc').textContent=n}
document.querySelectorAll('.chip[data-f]').forEach(function(b){b.onclick=function(){
  var k=b.dataset.f,v=b.dataset.v;F[k]=F[k]||[];var j=F[k].indexOf(v);
  if(j<0){F[k].push(v);b.setAttribute('aria-pressed','true')}
  else{F[k].splice(j,1);b.setAttribute('aria-pressed','false')}apply()}});
document.getElementById('clr').onclick=function(){F={};
  document.querySelectorAll('.chip[data-f]').forEach(function(b){b.setAttribute('aria-pressed','false')});apply()};
var lb=document.getElementById('lb');
function show(k){var vis=cards.filter(function(c){return !c.hidden});if(!vis.length)return;
  i=(k+vis.length)%%vis.length;var c=vis[i];
  document.getElementById('lbimg').src=c.querySelector('img').src;
  document.getElementById('lbcap').textContent=c.querySelector('.tm').textContent;
  document.getElementById('lbn').textContent=(i+1)+' / '+vis.length;lb.classList.add('on')}
cards.forEach(function(c){c.onclick=function(e){e.preventDefault();
  show(cards.filter(function(x){return !x.hidden}).indexOf(c))}});
document.getElementById('lbprev').onclick=function(){show(i-1)};
document.getElementById('lbnext').onclick=function(){show(i+1)};
document.getElementById('lbclose').onclick=function(){lb.classList.remove('on')};
lb.onclick=function(e){if(e.target===lb)lb.classList.remove('on')};
(function(){
  var SLF=%(slfrac).4f;
  var hi=document.getElementById('cy_hi'), lo=document.getElementById('cy_lo'),
      bHi=document.getElementById('c_hi'), bLo=document.getElementById('c_lo'),
      msg=document.getElementById('c_msg'), sellSide=true;
  function px(v){return (v*100).toFixed(0)+' pts'}
  function set(id,t){document.getElementById(id).innerHTML=t}
  function calc(){
    var H=parseFloat(hi.value), L=parseFloat(lo.value);
    msg.innerHTML='';
    if(!(H>L)){
      msg.innerHTML='<div class="calcwarn"><b>The high must be above the low.</b></div>';
      ['o_range','o_dist','o_level','o_stop'].forEach(function(i){set(i,'&mdash;')});
      return}
    var rng=H-L, dist=SLF*rng, lvl=sellSide?H:L, stop=lvl+(sellSide?1:-1)*dist;
    set('o_range', rng.toFixed(2)+' &nbsp; <b>'+px(rng)+'</b>');
    set('o_dist', dist.toFixed(2)+' &nbsp; <b>'+px(dist)+'</b>');
    set('o_level', '<b>'+lvl.toFixed(2)+'</b> &nbsp; the '+(sellSide?'high':'low')+' of yesterday');
    set('o_stop', '<b>'+stop.toFixed(2)+'</b>');
    msg.innerHTML='<div class="calcok">Sell'.replace('Sell',sellSide?'Sell':'Buy')
      +' the sweep of <b>'+lvl.toFixed(2)+'</b>, stop <b>'+stop.toFixed(2)
      +'</b>. That stop holds whatever price you get filled at.</div>';
  }
  function side(sell){sellSide=sell;
    bHi.setAttribute('aria-pressed',sell?'true':'false');
    bLo.setAttribute('aria-pressed',sell?'false':'true');calc()}
  bHi.onclick=function(){side(true)}; bLo.onclick=function(){side(false)};
  [hi,lo].forEach(function(el){el.oninput=calc});
  calc();
})();

var ri=document.getElementById('risk'),rw=document.getElementById('riskwarn'),
    MAXDD=%(ddr).4f,WRUN=%(wrun).4f;
function risk(){var v=parseFloat(ri.value);if(!(v>0))return;
  document.querySelectorAll('[data-pct]').forEach(function(el){
    var r=parseFloat(el.dataset.pct);
    el.textContent=(r>0?'+':'')+(r*v).toFixed(1)});
  document.querySelectorAll('.chips button').forEach(function(b){
    b.setAttribute('aria-pressed',parseFloat(b.dataset.r)===v?'true':'false')});
  var m=[];
  if(MAXDD*v>12)m.push('the worst drawdown on record costs <b>'+(MAXDD*v).toFixed(1)+'%%</b>, past a 12%% maximum loss');
  if(WRUN*v>12)m.push('the worst losing run costs <b>'+(WRUN*v).toFixed(1)+'%%</b>, past a 12%% maximum loss');
  if(v>3)m.push('a single full stop costs <b>'+v.toFixed(2)+'%%</b>, breaching a 3%% daily limit on its own');
  rw.innerHTML=m.length?('At '+v.toFixed(2)+'%% risk, '+m.join('; ')+'.'):'';
  rw.hidden=!m.length}
ri.oninput=risk;
document.querySelectorAll('.chips button').forEach(function(b){
  b.onclick=function(){ri.value=b.dataset.r;risk()}});
risk();
document.onkeydown=function(e){if(!lb.classList.contains('on'))return;
  if(e.key==='Escape')lb.classList.remove('on');
  if(e.key==='ArrowLeft')show(i-1);if(e.key==='ArrowRight')show(i+1)};
</script>
</body></html>"""

# The worst run must be the worst REAL sequence, never rebuilt from an average
# loss -- averaging understates it and calls a limit safe that is not.
WRUN = -min([sum(R[i:i+n]) for n in range(1, min(9, len(R)+1)) for i in range(len(R)-n+1)] + [0.0])

HOLD = _raw["hold"]
EXCL = [dict(d=dt.date.fromisoformat(t["date"]), R=t["R"]) for t in _raw.get("excluded", [])]

WDN = ["Mon", "Tue", "Wed", "Thu", "Fri"]
_wd = defaultdict(list)
for t in T: _wd[t["d"].weekday()].append(t["R"])
for t in EXCL: _wd[t["d"].weekday()].append(t["R"])
rows_wd = ""
for i in sorted(_wd):
    v = _wd[i]; w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    out = (i == 0)
    rows_wd += ('<tr%s><td><b>%s</b></td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
                '<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
                '<td>%s</td></tr>'
                % (' class="q"' if out else "", WDN[i], len(v), len(w), len(l),
                   100.0*len(w)/max(1, len(w)+len(l)),
                   "neg" if sum(v) <= 0 else "pos", sum(v)/len(v),
                   "neg" if sum(v) <= 0 else "pos", sum(v),
                   '<span class="pill no">excluded</span>' if out else ""))
_mon = [t["R"] for t in EXCL]
_rest = [t["R"] for t in T]

best = max(MONTHS, key=lambda m: sum(x["R"] for x in mo[m]))
rest = [x["R"] for m in MONTHS if m != best for x in mo[m]]
open(os.path.join(REPO, "pdfade.html"), "w").write(HTML % dict(
    css=css, year=2026, n=len(T), tot=sgn(sum(R)), retpct=pct(sum(R)),
    ev=sgn(ev, 3), se=se, wr=wr, W=len(W), L=len(L), BE=BEn, need=need, cush=wr-need,
    dd=dd, ddpct=pct(-dd), ws=streak(True), ls=streak(False),
    curve=curve_svg, rows_k=rows_k, evrest=sum(rest)/len(rest),
    rows_q=rows_q, rows_mm=rows_mm, ev_plain=ev, bestm=best,
    pfall=pf(R) or 0, gain=sum(x for x in R if x > 0), loss=sum(x for x in R if x <= 0),
    QHEAD=QHEAD % "Quarter", MHEAD=MHEAD % "Month", WHEAD=MHEAD % "Week",
    rows_w=rows_w,
    bw=sgn(sum(x["R"] for x in best_w)), bwn=len(best_w),
    ww=sgn(sum(x["R"] for x in worst_w)), wwn=len(worst_w),
    pw=len([v for v in ws.values() if sum(x["R"] for x in v) > 0]), nw=len(ws),
    aw=aw, al=al, payoff=aw/abs(al), t=ev/se, cards=cards, mchips=mchips,
    gen=dt.date.today().strftime("%d %B %Y"),
    wrun=WRUN, brk=12.0/max(dd, WRUN), ddr=dd, rr=RR,
    sldiv=1.0/SL_FRAC, slfrac=SL_FRAC, maxd=MAX_DEPTH_PTS,
    rows_wd=rows_wd, mon_n=len(_mon), mon_ev=sum(_mon)/len(_mon),
    rest_ev=sum(_rest)/len(_rest),
    hmed=HOLD["med"], htp=HOLD["tp"], hsl=HOLD["sl"], hlast=HOLD["last"],
    nlate=HOLD["late"], tot_r=sum(R), cut_r=HOLD["cut"]))
print("wrote pdfade.html  (%d trades, %+.1f R, WR %.1f%%, t=%.2f)" % (len(T), sum(R), wr, ev/se))
