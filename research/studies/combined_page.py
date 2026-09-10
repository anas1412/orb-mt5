"""Both edges in one book: the Asia opening range and the previous-day fade.

Data only. Each strategy's own page carries its rules; this one answers what
happens when the two are traded together, which is a different question --
mostly about whether their losses arrive on the same days.

Reads what the two pipelines already produced, so it never re-derives a result:
  research/data/trade_index.json     the ORB's trades
  research/data/pdfade_trades.json   the fade's trades

    python3 studies/combined_page.py
"""
import os, sys, re, json, datetime as dt, statistics as st
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)

BE   = 0.10     # a trade inside +-0.10 R is a scratch, in neither column
RISK = 1.5      # the default the page renders at -- see the limits table
LIMIT_MAX, LIMIT_DAY = 12.0, 3.0        # FundingPips 1 Step Flex

O = [dict(d=dt.date.fromisoformat(t["date"]), R=t["R"], k="orb")
     for t in json.load(open(os.path.join(RESEARCH, "data", "trade_index.json")))]
F = [dict(d=dt.date.fromisoformat(t["date"]), R=t["R"], k="fade")
     for t in json.load(open(os.path.join(RESEARCH, "data", "pdfade_trades.json")))["trades"]]
A = sorted(O + F, key=lambda z: (z["d"], z["k"]))

def blk(v):
    """A single week can be all wins or all losses, so nothing here may divide
    by a count that can be zero -- the win rate and the required win rate are
    simply undefined then, not zero."""
    w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    aw = sum(w)/len(w) if w else 0.0
    al = sum(l)/len(l) if l else 0.0
    pk = r = dd = 0
    for x in v:
        r += x; pk = max(pk, r); dd = max(dd, pk-r)
    g = sum(x for x in v if x > 0); ls = -sum(x for x in v if x <= 0)
    return dict(n=len(v), w=len(w), l=len(l), be=len(v)-len(w)-len(l),
                wr=(100.0*len(w)/(len(w)+len(l))) if (w or l) else None,
                need=(100.0/(1+aw/abs(al))) if (w and l) else None,
                ev=sum(v)/len(v), tot=sum(v), dd=dd, pf=g/ls if ls else None,
                se=st.pstdev(v)/len(v)**0.5)

def worst_run(v):
    """The worst REAL consecutive sequence, never rebuilt from an average."""
    return -min([sum(v[i:i+n]) for n in range(1, min(13, len(v)+1))
                 for i in range(len(v)-n+1)] + [0.0])

so, sf, sc = blk([t["R"] for t in O]), blk([t["R"] for t in F]), blk([t["R"] for t in A])
WRUN = worst_run([t["R"] for t in A])

byday = defaultdict(list)
for t in A: byday[t["d"]].append(t)
both = [d for d, v in byday.items() if len({t["k"] for t in v}) == 2]
xs = [sum(t["R"] for t in byday[d] if t["k"] == "orb") for d in both]
ys = [sum(t["R"] for t in byday[d] if t["k"] == "fade") for d in both]
mx, my = st.mean(xs), st.mean(ys)
CORR = (sum((a-mx)*(b-my) for a, b in zip(xs, ys)) /
        ((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5))
DAYS = sorted(byday)
worst_day = min(sum(t["R"] for t in byday[d]) for d in DAYS)
both_lost = len([d for d in both if all(t["R"] < -BE for t in byday[d])])

def runs(v):
    out = []; cur = []
    for x in v:
        if abs(x) <= BE: continue
        if x > BE: cur.append(x)
        else:
            if cur: out.append(cur)
            cur = []
    if cur: out.append(cur)
    return out
RUNS = runs([t["R"] for t in A])
def reach(rk):
    n = 0
    for r in RUNS:
        c = 0
        for x in r:
            c += x*rk
            if c >= LIMIT_MAX: n += 1; break
    return n

css = re.search(r"<style>(.*?)</style>",
                open(os.path.join(RESEARCH, "template.html")).read(), re.S).group(1)

def sgn(v, dp=1, suf=" R"):
    return '<span class="%s">%+.*f%s</span>' % ("pos" if v > 0 else "neg", dp, v, suf)
def pct(r):
    return '<span data-pct="%.4f">%+.1f</span>%%' % (r, RISK*r)
def pfc(v):
    return '<td>&ndash;</td>' if v is None else '<td class="%s">%.2f</td>' % ("pos" if v >= 1 else "neg", v)
def seq_cell(ts):
    if not ts: return "&ndash;"
    return '<span class="seq">%s</span>' % "-".join(
        '<b class="%s">%s</b>' % (("pos", "W") if t["R"] > BE else
                                  ("neg", "L") if t["R"] < -BE else ("", ".")) for t in ts)

# ---- curves: the book, and each edge on the same axis ----
W_, H_ = 1080, 320; PAD = 48
def series(ts):
    c = 0; out = []
    for t in ts: c += t["R"]; out.append((t["d"], c))
    return out
cA, cO, cF = series(A), series(O), series(F)
d0, d1 = DAYS[0], DAYS[-1]
span = (d1-d0).days or 1
lo = min(0, min(v for _, v in cA+cO+cF)); hi = max(v for _, v in cA+cO+cF)
sx = lambda d: PAD + (d-d0).days*(W_-PAD-16)/span
sy = lambda v: H_-30 - (v-lo)*(H_-30-14)/max(1e-9, hi-lo)
def poly(c, col, w, dash=""):
    return ('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
            'stroke-linejoin="round"%s/>'
            % (" ".join("%.1f,%.1f" % (sx(d), sy(v)) for d, v in c), col, w,
               ' stroke-dasharray="5 4"' if dash else ""))
grid = "".join('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)"/>'
               '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%d R</text>'
               % (PAD, sy(v), W_-16, sy(v), PAD-8, sy(v)+4, v)
               for v in range(0, int(hi)+11, 10))
mk = "".join('<line x1="%.1f" y1="14" x2="%.1f" y2="%d" stroke="var(--line)" stroke-dasharray="3 4"/>'
             '<text x="%.1f" y="%d" fill="var(--mut)" font-size="10.5" text-anchor="middle">%s</text>'
             % (sx(m), sx(m), H_-30, sx(m), H_-14, m.strftime("%b"))
             for m in [dt.date(2026, i, 1) for i in range(1, 10)])
CURVE = ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" aria-label='
         '"Cumulative return in R for the two strategies separately and combined, 2026">'
         '%s%s%s%s%s</svg>'
         % (W_, H_, grid, mk, poly(cO, "var(--mut)", "1.6", "d"),
            poly(cF, "var(--acc2)", "1.6", "d"), poly(cA, "var(--acc)", "2.4")))

def row(label, ts, seq=True, cls=""):
    v = [t["R"] for t in ts]
    if not v:
        return '<tr class="q"><td>%s</td><td>0</td><td>&ndash;</td>%s<td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td></tr>' % (label, "<td>&ndash;</td>" if seq else "")
    b = blk(v); c = "pos" if b["tot"] > 0 else "neg"
    return ('<tr%s><td><b>%s</b></td><td>%d</td><td>%d / %d / %d</td>%s<td>%s</td>%s'
            '<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
            '<td class="%s"><b>%s</b></td></tr>'
            % (cls, label, b["n"], b["w"], b["l"], b["be"],
               ('<td>%s</td>' % seq_cell(ts)) if seq else "",
               ("%.1f%%" % b["wr"]) if b["wr"] is not None else "&ndash;", pfc(b["pf"]),
               c, b["ev"], c, b["tot"], c, pct(b["tot"])))

HEAD = ('<thead><tr><th>%s</th><th>Trades</th><th>W / L / BE</th>%s<th>Win rate</th>'
        '<th>Profit factor</th><th>EV per trade</th><th>Total R</th><th>Account</th></tr></thead>')
qs = defaultdict(list); ms = defaultdict(list); ws = defaultdict(list)
for t in A:
    qs["Q%d" % ((t["d"].month-1)//3+1)].append(t)
    ms[t["d"].strftime("%b")].append(t)
    ws[t["d"].isocalendar()[:2]].append(t)
MON = [m for m in ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep") if m in ms]
rows_q = "".join(row(q, qs[q], seq=False) for q in sorted(qs)) + row("2026", A, seq=False, cls=' class="hi"')
rows_m = "".join(row(m, ms[m]) for m in MON)
def wlab(k):
    mon = dt.date.fromisocalendar(k[0], k[1], 1)
    return "%s&nbsp;&ndash;&nbsp;%s" % (mon.strftime("%d %b"), (mon+dt.timedelta(days=4)).strftime("%d %b"))
rows_w = "".join(row(wlab(k), ws[k]) for k in sorted(ws))

CMP = "".join(
    '<tr%s><td><b>%s</b></td><td>%d</td><td>%d / %d / %d</td><td>%.1f%%</td><td>%.1f%%</td>%s'
    '<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td><td>%.1f R</td>'
    '<td class="pos"><b>%s</b></td><td>%+.2f</td></tr>'
    % (cls, lab, b["n"], b["w"], b["l"], b["be"], b["wr"], b["need"], pfc(b["pf"]),
       b["ev"], b["tot"], b["dd"], pct(b["tot"]), b["ev"]/b["se"])
    for lab, b, cls in (("Opening range, alone", so, ""), ("Previous-day fade, alone", sf, ""),
                        ("Both together", sc, ' class="hi"')))

WORST = "".join('<tr><td><b>%s</b></td><td>%s</td><td class="neg"><b>%+.2f R</b></td>'
                '<td class="neg"><b>%s</b></td></tr>'
                % (d.strftime("%d %b"), ", ".join("%s %+.2f" % (t["k"], t["R"]) for t in byday[d]),
                   sum(t["R"] for t in byday[d]), pct(sum(t["R"] for t in byday[d])))
                for d in sorted(DAYS, key=lambda d: sum(t["R"] for t in byday[d]))[:8])

RUNTAB = "".join('<tr><td><b>%d in a row</b></td><td class="neg"><b>%.2f R</b></td>'
                 '<td class="neg"><b>%s</b></td></tr>'
                 % (n, -min(sum([t["R"] for t in A][i:i+n]) for i in range(len(A)-n+1)),
                    pct(min(sum([t["R"] for t in A][i:i+n]) for i in range(len(A)-n+1))))
                 for n in (1, 2, 3, 4, 5, 6, 8))

HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Two edges in one book — gold, 2026</title>
<style>%(css)s</style></head><body><div class="wrap">

<header>
<div class="eyebrow"><span class="dot"></span>research &middot; both strategies together</div>
<h1>Two edges, <em>one account</em></h1>
<p class="lede">The Asia opening range and the previous-day level fade, traded side by side on gold
through 2026. Data only &mdash; the rules for each live on their own pages:
<a href="index.html">opening range</a> and <a href="pdfade.html">previous-day fade</a>.</p>

<div class="riskbar">
<label for="risk">Risk per trade</label>
<div class="riskin"><input id="risk" type="number" min="0.25" max="3" step="0.25" value="%(risk)g"><span>%%</span></div>
<div class="chips">
<button data-r="1" aria-pressed="false">1%%</button>
<button data-r="1.5" aria-pressed="true">1.5%%</button>
<button data-r="2" aria-pressed="false">2%%</button>
<button data-r="2.5" aria-pressed="false">2.5%%</button></div>
<p class="risknote">Applied to <b>each</b> trade, so a day that fires both strategies puts twice
this at risk. The worst real day was <b>%(wday).2f R</b> and the worst real losing run
<b>%(wrun).2f R</b>, which is why the default here is lower than either strategy's own page.</p>
</div>
<div id="riskwarn" class="riskwarn" hidden></div>

<div class="kpi">
<div class="k big"><div class="l">Total</div><div class="v">%(tot)s</div><div class="n">%(totpct)s of the account</div></div>
<div class="k"><div class="l">Per trade</div><div class="v">%(ev)s</div><div class="n">&plusmn; %(se).3f standard error</div></div>
<div class="k"><div class="l">Trades</div><div class="v">%(n)d</div><div class="n">%(no)d range &middot; %(nf)d fade</div></div>
<div class="k"><div class="l">Win rate</div><div class="v">%(wr).1f%%</div><div class="n">needs %(need).1f%%</div></div>
<div class="k"><div class="l">Worst dip</div><div class="v">%(dd).1f R</div><div class="n">%(ddpct)s of the account</div></div>
<div class="k"><div class="l">t statistic</div><div class="v">%(t).2f</div><div class="n">%(t1).2f and %(t2).2f apart</div></div>
</div>

<nav>
<a href="#side"><span>01</span>Side by side</a>
<a href="#curve"><span>02</span>The curves</a>
<a href="#div"><span>03</span>Do they overlap?</a>
<a href="#risk"><span>04</span>Worst days and runs</a>
<a href="#periods"><span>05</span>Quarter, month, week</a>
</nav>
</header>

<section id="side">
<h2><span class="num">01</span>Side by side</h2>
<div class="scroll"><table>
<caption>Each strategy alone, then the two merged in the order the trades happened.
BE is a scratch, inside 0.10 R, counted in neither column.</caption>
<thead><tr><th>Book</th><th>Trades</th><th>W / L / BE</th><th>Win rate</th><th>Needs</th>
<th>Profit factor</th><th>EV per trade</th><th>Total R</th><th>Worst dip</th><th>Account</th><th>t</th></tr></thead>
<tbody>%(cmp)s</tbody></table></div>
<div class="good"><div class="t">The drawdowns do not add up</div>
<p>Separately the two worst dips are <b>%(dd1).1f R</b> and <b>%(dd2).1f R</b>, which would be
<b>%(ddsum).1f R</b> if they arrived together. The combined book's worst dip is
<b>%(dd).1f R</b> &mdash; barely more than the opening range suffers on its own, for
<b>%(gain).0f%% more return</b>. That is the whole case for running both.</p></div>
</section>

<section id="curve">
<h2><span class="num">02</span>The curves</h2>
<div class="mclegend">
<span><i class="sw" style="background:var(--acc)"></i>both together</span>
<span><i class="sw" style="background:var(--mut)"></i>opening range alone</span>
<span><i class="sw" style="background:var(--acc2)"></i>previous-day fade alone</span>
</div>
<figure><div class="fig">%(curve)s</div>
<figcaption>Cumulative R against the calendar, so the flat stretches are real time rather than
trades. R is size-independent, so none of this depends on the account.</figcaption></figure>
</section>

<section id="div">
<h2><span class="num">03</span>Do they overlap?</h2>
<div class="kpi" style="grid-template-columns:repeat(4,minmax(0,1fr))">
<div class="k"><div class="l">Days traded</div><div class="v">%(nd)d</div><div class="n">at least one trade</div></div>
<div class="k"><div class="l">Both on one day</div><div class="v">%(nboth)d</div><div class="n">%(bothpc).0f%% of traded days</div></div>
<div class="k"><div class="l">Both lost</div><div class="v">%(bothlost)d</div><div class="n">of those %(nboth)d days</div></div>
<div class="k"><div class="l">Same-day correlation</div><div class="v">%(corr)+.2f</div><div class="n">n = %(nboth)d</div></div>
</div>
<p>On the %(nboth)d days both strategies fired, their results are <b>negatively correlated at
%(corr)+.2f</b> &mdash; when one lost the other tended to win. Both lost on the same day
<b>%(bothlost)d times</b> in the year. One is a breakout and the other fades a failed breakout, so
that they do not fail together is structural rather than lucky, but %(nboth)d days is a small
sample to measure a correlation on.</p>
</section>

<section id="risk">
<h2><span class="num">04</span>Worst days and runs</h2>
<p class="sub">Both figures below are real sequences out of 2026, not rebuilt from an average
loss &mdash; averaging understates a run and calls a limit safe that is not.</p>
<div class="scroll"><table>
<caption>The eight worst days. A day that fires both strategies risks twice the per-trade figure.</caption>
<thead><tr><th>Day</th><th>Trades</th><th>Combined</th><th>Account</th></tr></thead>
<tbody>%(worst)s</tbody></table></div>
<div class="scroll"><table>
<caption>The worst consecutive sequence of each length, across the merged book.</caption>
<thead><tr><th>Length</th><th>Worst real run</th><th>Account</th></tr></thead>
<tbody>%(runtab)s</tbody></table></div>
<div class="note"><div class="t">What the limits allow</div>
<p>A 12%% maximum loss is reached by the worst run at <b>%(brk_run).2f%%</b> risk per trade and by
the worst drawdown at <b>%(brk_dd).2f%%</b>. A 3%% daily limit is breached by the worst day at
<b>%(brk_day).2f%%</b>. The binding constraint is the <b>day</b>, because two strategies can lose
on it, and that is what caps this book below either strategy traded alone.</p></div>
<div class="kpi" style="grid-template-columns:repeat(3,minmax(0,1fr))">
<div class="k"><div class="l">Winning runs</div><div class="v">%(nruns)d</div><div class="n">longest %(longest)d trades</div></div>
<div class="k"><div class="l">Runs clearing 12%%</div><div class="v">%(reach)d</div><div class="n">at the risk selected</div></div>
<div class="k"><div class="l">Worst losing run</div><div class="v">%(wrun).2f R</div><div class="n">%(wrunpct)s of the account</div></div>
</div>
</section>

<section id="periods">
<h2><span class="num">05</span>Quarter, month, week</h2>
<p class="sub">The merged book only. The order column is every trade as it happened, both
strategies interleaved: W won, L lost, a dot is a scratch.</p>
<div class="scroll"><table><caption>By quarter.</caption>%(HQ)s<tbody>%(rows_q)s</tbody></table></div>
<div class="scroll"><table><caption>By month.</caption>%(HM)s<tbody>%(rows_m)s</tbody></table></div>
<div class="scroll"><table><caption>Every week that traded.</caption>%(HM)s<tbody>%(rows_w)s</tbody></table></div>
</section>

<footer><p><b>Two edges, one account.</b> Generated %(gen)s from %(n)d trades &mdash; %(no)d from the
<a href="index.html">opening range</a> and %(nf)d from the <a href="pdfade.html">previous-day
fade</a>, merged in date order. Both are 2026 only. Neither page's caveats are repeated here; read
them there.</p></footer>
</div>

<script>
var ri=document.getElementById('risk'),rw=document.getElementById('riskwarn'),
    DD=%(ddr).4f,WRUN=%(wrun).4f,WDAY=%(wdayabs).4f;
function risk(){var v=parseFloat(ri.value);if(!(v>0))return;
  document.querySelectorAll('[data-pct]').forEach(function(el){
    var r=parseFloat(el.dataset.pct);
    el.textContent=(r>0?'+':'')+(r*v).toFixed(1)});
  document.querySelectorAll('.chips button').forEach(function(b){
    b.setAttribute('aria-pressed',parseFloat(b.dataset.r)===v?'true':'false')});
  var m=[];
  if(WDAY*v>3)m.push('the worst day costs <b>'+(WDAY*v).toFixed(1)+'%%</b>, past a 3%% daily limit');
  if(WRUN*v>12)m.push('the worst losing run costs <b>'+(WRUN*v).toFixed(1)+'%%</b>, past a 12%% maximum loss');
  if(DD*v>12)m.push('the worst drawdown costs <b>'+(DD*v).toFixed(1)+'%%</b>, past a 12%% maximum loss');
  rw.innerHTML=m.length?('At '+v.toFixed(2)+'%% per trade, '+m.join('; ')+'.'):'';
  rw.hidden=!m.length}
ri.oninput=risk;
document.querySelectorAll('.chips button').forEach(function(b){
  b.onclick=function(){ri.value=b.dataset.r;risk()}});
risk();
</script></body></html>"""

open(os.path.join(REPO, "combined.html"), "w").write(HTML % dict(
    css=css, risk=RISK, n=sc["n"], no=so["n"], nf=sf["n"],
    tot=sgn(sc["tot"]), totpct=pct(sc["tot"]), ev=sgn(sc["ev"], 3), se=sc["se"],
    wr=sc["wr"], need=sc["need"], dd=sc["dd"], ddpct=pct(-sc["dd"]), ddr=sc["dd"],
    t=sc["ev"]/sc["se"], t1=so["ev"]/so["se"], t2=sf["ev"]/sf["se"],
    cmp=CMP, dd1=so["dd"], dd2=sf["dd"], ddsum=so["dd"]+sf["dd"],
    gain=100.0*(sc["tot"]-so["tot"])/so["tot"], curve=CURVE,
    nd=len(DAYS), nboth=len(both), bothpc=100.0*len(both)/len(DAYS),
    bothlost=both_lost, corr=CORR, worst=WORST, runtab=RUNTAB,
    wday=worst_day, wdayabs=-worst_day, wrun=WRUN, wrunpct=pct(-WRUN),
    brk_run=LIMIT_MAX/WRUN, brk_dd=LIMIT_MAX/sc["dd"], brk_day=LIMIT_DAY/-worst_day,
    nruns=len(RUNS), longest=max(len(r) for r in RUNS), reach=reach(RISK),
    HQ=HEAD % ("Quarter", ""), HM=HEAD % ("Period", "<th>Order</th>"),
    rows_q=rows_q, rows_m=rows_m, rows_w=rows_w,
    gen=dt.date.today().strftime("%d %B %Y")))
print("wrote combined.html  (%d trades, %+.1f R, WR %.1f%%, dd %.1f R, t=%.2f)"
      % (sc["n"], sc["tot"], sc["wr"], sc["dd"], sc["ev"]/sc["se"]))
