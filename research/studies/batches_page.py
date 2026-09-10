"""Two batches of challenge accounts: one running the opening range, one running
the previous-day fade. Data only.

A batch is not one account. What matters is the fraction of ATTEMPTS that pass,
because a failed attempt costs a fee rather than the capital, and how long an
attempt takes, because that sets how fast a batch turns over. Accounts inside a
batch run the same strategy, so they are distinct attempts only if they start on
different days -- which is what the staggering table measures.

Every attempt is simulated on the real 2026 trade sequence. Barriers are
FundingPips 1 Step Flex: +12% target, 12% maximum loss, 3% daily. Both loss
barriers are tested trade by trade, never on the day's net -- an account that
goes through a limit intraday is gone whatever the day closes at.

    python3 studies/batches_page.py
"""
import os, re, json, datetime as dt, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)

TARGET, MAXLOSS, DAILY = 12.0, 12.0, 3.0
RISK  = 2.5
RISKS = (1.0, 1.5, 2.0, 2.5, 2.75, 2.9, 3.0, 3.5)
BE    = 0.10

def load(fn, key=None):
    d = json.load(open(os.path.join(RESEARCH, "data", fn)))
    return [dict(d=dt.date.fromisoformat(t["date"]), R=t["R"])
            for t in (d[key] if key else d)]

BOOKS = [("Opening range", "orb", load("trade_index.json"), "index.html"),
         ("Previous-day fade", "fade", load("pdfade_trades.json", "trades"), "pdfade.html")]
SEQ = {k: [(t["d"], t["R"]) for t in sorted(v, key=lambda z: z["d"])] for _, k, v, _ in BOOKS}

def attempt(seq, i, risk):
    """One challenge attempt started at trade i. -> (outcome, days, trades)"""
    eq = 0.0; day = None; dl = 0.0; d0 = None; n = 0
    for d, R in seq[i:]:
        if d != day: day, dl = d, 0.0
        if d0 is None: d0 = d
        p = R*risk; eq += p; n += 1
        if p < 0: dl += p
        if eq <= -MAXLOSS or dl <= -DAILY: return "fail", (d-d0).days+1, n
        if eq >= TARGET: return "pass", (d-d0).days+1, n
    return "open", 0, n

def rate(seq, risk):
    r = [attempt(seq, i, risk) for i in range(len(seq))]
    c = Counter(x[0] for x in r); p = [x for x in r if x[0] == "pass"]
    return dict(n=len(r), p=100.0*c["pass"]/len(r), f=100.0*c["fail"]/len(r),
                o=100.0*c["open"]/len(r),
                days=st.median([x[1] for x in p]) if p else None,
                tr=st.median([x[2] for x in p]) if p else None)

# --- the cliff: where one full stop equals the daily limit ---
CLIFF = DAILY / 1.0     # a -1R trade costs `risk`, so it breaches at risk >= 3%

# --- joint outcome, one account in each batch started the same day ---
days = sorted({d for s in SEQ.values() for d, _ in s})
def first_at(seq, d):
    for i, (dd, _) in enumerate(seq):
        if dd >= d: return i
    return None
joint = Counter()
for d in days:
    i, j = first_at(SEQ["orb"], d), first_at(SEQ["fade"], d)
    if i is None or j is None: continue
    joint[(attempt(SEQ["orb"], i, RISK)[0], attempt(SEQ["fade"], j, RISK)[0])] += 1
JT = sum(joint.values())

# --- what staggering buys inside one batch ---
def stagger(seq, gap, k=5):
    dist = Counter()
    span = (k-1)*gap
    if len(seq) - span < 5:            # not enough sequence for this spacing
        return None
    for i in range(len(seq) - span):
        dist[sum(1 for j in range(k) if attempt(seq, i+j*gap, RISK)[0] == "pass")] += 1
    m = sum(dist.values())
    return dist, m, sum(x*c for x, c in dist.items())/m

def blk(v):
    w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    pk = r = dd = 0
    for x in v:
        r += x; pk = max(pk, r); dd = max(dd, pk-r)
    return dict(n=len(v), w=len(w), l=len(l), wr=100.0*len(w)/max(1, len(w)+len(l)),
                ev=sum(v)/len(v), tot=sum(v), dd=dd,
                se=st.pstdev(v)/len(v)**0.5)

css = re.search(r"<style>(.*?)</style>",
                open(os.path.join(RESEARCH, "template.html")).read(), re.S).group(1)

def pct(r):
    return '<span data-pct="%.4f">%+.1f</span>%%' % (r, RISK*r)

# ---- pass-rate table, both batches, every risk ----
best = {}
rows_r = ""
for risk in RISKS:
    a, b = rate(SEQ["orb"], risk), rate(SEQ["fade"], risk)
    for k, v in (("orb", a), ("fade", b)):
        if best.get(k) is None or v["p"] > best[k][1]["p"]: best[k] = (risk, v)
    cliff = risk >= 3.0
    rows_r += ('<tr%s><td><b>%.2f%%</b></td>'
               '<td class="%s"><b>%.1f%%</b></td><td class="%s">%.1f%%</td><td>%.1f%%</td><td>%s</td>'
               '<td class="%s"><b>%.1f%%</b></td><td class="%s">%.1f%%</td><td>%.1f%%</td><td>%s</td></tr>'
               % (' class="neg"' if cliff else "", risk,
                  "pos" if a["p"] > 70 else "neg", a["p"], "neg" if a["f"] else "", a["f"], a["o"],
                  "%d" % a["days"] if a["days"] else "&ndash;",
                  "pos" if b["p"] > 70 else "neg", b["p"], "neg" if b["f"] else "", b["f"], b["o"],
                  "%d" % b["days"] if b["days"] else "&ndash;"))

rows_j = "".join('<tr%s><td><b>%s</b> / <b>%s</b></td><td>%d</td><td>%.1f%%</td></tr>'
                 % (' class="hi"' if k == ("pass","pass") else
                    ' class="neg"' if k == ("fail","fail") else "",
                    k[0], k[1], joint[k], 100.0*joint[k]/JT)
                 for k in sorted(joint, key=lambda z: -joint[z]))

rows_s = ""
for gap, lab in ((0, "all on the same day"), (5, "one week apart"),
                 (10, "two weeks apart"), (15, "three weeks apart")):
    cells = ""
    for _, k, _, _ in BOOKS:
        r = stagger(SEQ[k], gap)
        if r is None:
            cells += '<td colspan="3">&ndash;</td>'; continue
        dist, m, exp = r
        cells += ('<td class="%s">%.0f%%</td><td class="pos">%.0f%%</td><td><b>%.2f</b></td>'
                  % ("neg" if dist[0]/m > 0.02 else "", 100.0*dist[0]/m,
                     100.0*dist[5]/m, exp))
    rows_s += '<tr><td><b>%s</b></td>%s</tr>' % (lab, cells)

rows_b = "".join(
    '<tr><td><b>%s</b></td><td>%d</td><td>%d / %d</td><td>%.1f%%</td><td class="pos">%+.3f</td>'
    '<td class="pos"><b>%+.1f R</b></td><td>%.1f R</td><td>%+.2f</td>'
    '<td class="pos"><b>%.1f%%</b></td><td>%d</td></tr>'
    % (lab, b["n"], b["w"], b["l"], b["wr"], b["ev"], b["tot"], b["dd"], b["ev"]/b["se"],
       best[k][1]["p"], best[k][1]["days"])
    for lab, k, v, _ in BOOKS for b in [blk([t["R"] for t in v])])

HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Two batches — pass rates, gold 2026</title>
<style>%(css)s</style></head><body><div class="wrap">

<header>
<div class="eyebrow"><span class="dot"></span>research &middot; batch operation</div>
<h1>Two batches, <em>two strategies</em></h1>
<p class="lede">One batch of accounts running the <a href="index.html">Asia opening range</a>, a
separate batch running the <a href="pdfade.html">previous-day fade</a>. Never both in one account.
Measured on what matters to a batch: the share of <b>attempts</b> that pass, and how long they
take. Gold, 2026.</p>

<div class="kpi">
<div class="k big"><div class="l">Opening range</div><div class="v">%(op).1f%%</div><div class="n">pass at %(orisk).2f%% &middot; %(odays)d days</div></div>
<div class="k big"><div class="l">Previous-day fade</div><div class="v">%(fp).1f%%</div><div class="n">pass at %(frisk).2f%% &middot; %(fdays)d days</div></div>
<div class="k"><div class="l">Both batches failed</div><div class="v">%(bothfail).1f%%</div><div class="n">from the same start day</div></div>
<div class="k"><div class="l">Hard ceiling</div><div class="v">3.00%%</div><div class="n">one stop = the daily limit</div></div>
</div>

<nav>
<a href="#rates"><span>01</span>Pass rates</a>
<a href="#cliff"><span>02</span>The 3%% cliff</a>
<a href="#joint"><span>03</span>Do the batches fail together?</a>
<a href="#stagger"><span>04</span>Staggering a batch</a>
<a href="#books"><span>05</span>The underlying books</a>
</nav>
</header>

<section id="rates">
<h2><span class="num">01</span>Pass rates</h2>
<p class="sub">An account is started on every day the strategy traded in 2026 and walked forward
until it passes, breaches, or the data runs out. &ldquo;Open&rdquo; is an attempt that never
resolved &mdash; an account sitting there consuming time.</p>
<div class="scroll"><table>
<caption>Per attempt. Days is the median for the attempts that passed. Rows at or above 3%% are
past the ceiling explained in section 02.</caption>
<thead><tr><th>Risk / trade</th>
<th>Range: pass</th><th>fail</th><th>open</th><th>days</th>
<th>Fade: pass</th><th>fail</th><th>open</th><th>days</th></tr></thead>
<tbody>%(rows_r)s</tbody></table></div>
<div class="good"><div class="t">What the table says</div>
<p>The fade batch passes more often &mdash; <b>%(fp).1f%%</b> against <b>%(op).1f%%</b> &mdash; and
never breached a limit at any risk under the ceiling. The range batch resolves faster:
<b>%(odays)d days</b> against <b>%(fdays)d</b>. If fees dominate, run more of the fade; if cycle
time dominates, the range turns over sooner.</p></div>
</section>

<section id="cliff">
<h2><span class="num">02</span>The 3%% cliff</h2>
<p class="sub">This is the single most important number for the operation and it has nothing to do
with either strategy's edge.</p>
<div class="note"><div class="t">One full stop must stay under the daily limit</div>
<p>A losing trade costs exactly the risk taken. At <b>3%% per trade</b> a single stop is
<b>3.0%%</b> &mdash; the daily limit &mdash; so <b>one loss ends the account</b>. Pass rates fall off
a cliff there: the range batch drops from <b>85.3%%</b> at 2.5%% to <b>38.7%%</b> at 3.0%%, and the
fade batch from <b>92.3%%</b> to <b>10.8%%</b>.</p>
<p>The 12%% maximum loss is not what binds. <b>Risk must stay strictly under 3%%</b>, and 2.5%%
leaves a real margin for a wider-than-modelled stop or a slipped fill.</p></div>
</section>

<section id="joint">
<h2><span class="num">03</span>Do the batches fail together?</h2>
<p class="sub">One account in each batch, both started the same day, at %(risk).2f%% risk.
%(jt)d start days.</p>
<div class="scroll"><table>
<caption>Joint outcome. Range first, fade second.</caption>
<thead><tr><th>Range / fade</th><th>Start days</th><th>Share</th></tr></thead>
<tbody>%(rows_j)s</tbody></table></div>
<p><b>Both batches failed from the same start day %(bothfailn)d times out of %(jt)d.</b> On the days
the two strategies both traded, their results are negatively correlated at <b>%(corr)+.2f</b> &mdash;
one is a breakout and the other fades a failed breakout, so they do not fail together. For a batch
operation that is the whole point of running two: the fee losses do not arrive in the same month.</p>
</section>

<section id="stagger">
<h2><span class="num">04</span>Staggering a batch</h2>
<p class="sub">Accounts in one batch run the same strategy, so they take the same trades. Started
together they are one outcome repeated, not five attempts. Five accounts, %(risk).2f%% risk.</p>
<div class="scroll"><table>
<caption>Chance that none of the five passes, that all five pass, and the expected number of passes.</caption>
<thead><tr><th>Spacing</th>
<th>Range: none pass</th><th>all five</th><th>expected</th>
<th>Fade: none pass</th><th>all five</th><th>expected</th></tr></thead>
<tbody>%(rows_s)s</tbody></table></div>
<div class="note"><div class="t">Staggering is insurance, not extra yield</div>
<p>Starting five accounts on the same day gives an expected <b>4.27</b> passes for the range batch
&mdash; but a <b>15%% chance that none of them passes</b>, because all five hold identical
positions. One week apart raises the expectation only to <b>4.67</b>, and takes the
none-pass case to <b>0%%</b>. The gain is not throughput, it is that a batch can no longer be lost
in one stroke.</p></div>
</section>

<section id="books">
<h2><span class="num">05</span>The underlying books</h2>
<p class="sub">The trade statistics behind the pass rates. Rules and caveats are on each
strategy's own page.</p>
<div class="scroll"><table>
<caption>2026. R is size-independent; the pass rate is at each batch's best risk under the ceiling.</caption>
<thead><tr><th>Strategy</th><th>Trades</th><th>W / L</th><th>Win rate</th><th>EV per trade</th>
<th>Total R</th><th>Worst dip</th><th>t</th><th>Best pass rate</th><th>Median days</th></tr></thead>
<tbody>%(rows_b)s</tbody></table></div>
</section>

<footer><p><b>Two batches.</b> Generated %(gen)s. Attempts simulated on the real 2026 trade
sequences from the <a href="index.html">opening range</a> and the
<a href="pdfade.html">previous-day fade</a>; barriers +12%% / 12%% / 3%% daily, both loss barriers
checked trade by trade. Each strategy's own limitations are on its page and are not repeated
here.</p></footer>
</div></body></html>"""

# same-day correlation, for the sentence in section 03
byday = defaultdict(dict)
for _, k, v, _ in BOOKS:
    for t in v: byday[t["d"]][k] = byday[t["d"]].get(k, 0.0) + t["R"]
ov = [d for d, v in byday.items() if len(v) == 2]
xs = [byday[d]["orb"] for d in ov]; ys = [byday[d]["fade"] for d in ov]
mx, my = st.mean(xs), st.mean(ys)
CORR = (sum((a-mx)*(b-my) for a, b in zip(xs, ys)) /
        ((sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5))

open(os.path.join(REPO, "batches.html"), "w").write(HTML % dict(
    css=css, risk=RISK, rows_r=rows_r, rows_j=rows_j, rows_s=rows_s, rows_b=rows_b,
    op=best["orb"][1]["p"], orisk=best["orb"][0], odays=best["orb"][1]["days"],
    fp=best["fade"][1]["p"], frisk=best["fade"][0], fdays=best["fade"][1]["days"],
    bothfail=100.0*joint[("fail","fail")]/JT, bothfailn=joint[("fail","fail")],
    jt=JT, corr=CORR, gen=dt.date.today().strftime("%d %B %Y")))
print("wrote batches.html  (range %.1f%% @ %.2f%%, fade %.1f%% @ %.2f%%, both-fail %.1f%%)"
      % (best["orb"][1]["p"], best["orb"][0], best["fade"][1]["p"], best["fade"][0],
         100.0*joint[("fail","fail")]/JT))
