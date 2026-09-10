"""Two batches of four challenge accounts, in weekday rotation. Data only.

  A batch  opening range, Mon-Thu   A1+A2 Mon+Wed   A3+A4 Tue+Thu
  B batch  previous-day fade, Tue-Fri  B1+B2 Tue+Thu   B3+B4 Wed+Fri

An account trades only its two weekdays, so it sees about half the signals. The
pair sharing a day takes the identical trade, so a batch of four is two distinct
attempts each held twice.

Everything is a barrier simulation on resampled trading days. Days are resampled
BY WEEKDAY, so a Wednesday is always drawn from Wednesdays -- the rotation is a
weekday rule and a pool that ignored weekdays could not model it. The 3% daily
limit needs the trades that shared a day to keep sharing one, so days are the
resampling unit rather than trades.

Barriers: +12% target, 12% maximum loss, 3% daily, checked trade by trade.

    python3 studies/batches_page.py
"""
import os, re, json, random, datetime as dt, statistics as st
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)

TARGET, MAXLOSS, DAILY = 12.0, 12.0, 3.0
PATHS, DEADLINE = 20000, 60        # paths per cell; deadline in weekday steps
RISK  = 2.5
RISKS = (1.5, 2.0, 2.25, 2.5, 2.6, 2.75, 2.9)
BE    = 0.10
WD    = ["Mon", "Tue", "Wed", "Thu", "Fri"]
random.seed(20260910)

def load(fn, key=None):
    d = json.load(open(os.path.join(RESEARCH, "data", fn)))
    return [dict(d=dt.date.fromisoformat(t["date"]), R=t["R"]) for t in (d[key] if key else d)]

BOOKS = [dict(lab="Opening range", k="orb", href="index.html", short="A",
              trades=load("trade_index.json"), days=(0, 1, 2, 3),
              pairs=(("A1 + A2", (0, 2)), ("A3 + A4", (1, 3)))),
         dict(lab="Previous-day fade", k="fade", href="pdfade.html", short="B",
              trades=load("pdfade_trades.json", "trades"), days=(1, 2, 3, 4),
              pairs=(("B1 + B2", (1, 3)), ("B3 + B4", (2, 4))))]

def weekpool(b):
    """pool[weekday] = one entry per calendar day of that weekday, each the list
    of R values that landed on it (empty when the strategy sat the day out)."""
    by = defaultdict(list)
    for t in b["trades"]: by[t["d"]].append(t["R"])
    lo, hi = min(by), max(by)
    pool = defaultdict(list); d = lo
    while d <= hi:
        if d.weekday() in b["days"]: pool[d.weekday()].append(by.get(d, []))
        d += dt.timedelta(days=1)
    return pool

for b in BOOKS: b["pool"] = weekpool(b)

def sim(b, risk, take=None):
    """One account. take = the weekdays it trades; None means every day the
    strategy trades. Walks Mon..Fri repeatedly, drawing each weekday from its
    own pool. -> pass%, fail%, abandon%, [steps to pass]"""
    pool = b["pool"]; days = b["days"]
    take = days if take is None else take
    c = Counter(); dp = []
    for _ in range(PATHS):
        eq = 0.0; out = None
        for step in range(DEADLINE):
            wd = step % 5
            if wd not in days: continue
            bucket = pool[wd][random.randrange(len(pool[wd]))]
            if wd not in take: continue
            dl = 0.0
            for R in bucket:
                p = R*risk; eq += p
                if p < 0: dl += p
                if eq <= -MAXLOSS or dl <= -DAILY: out = "fail"; break
                if eq >= TARGET: out = "pass"; break
            if out: break
        if out == "pass": dp.append(step+1)
        c[out or "abandon"] += 1
    return (100.0*c["pass"]/PATHS, 100.0*c["fail"]/PATHS, 100.0*c["abandon"]/PATHS, dp)

# ---- every number the page shows ----
FULL, ROT = {}, {}
for b in BOOKS:
    for risk in RISKS:
        FULL[(b["k"], risk)] = sim(b, risk)
        ROT[(b["k"], risk)]  = sim(b, risk, take=b["pairs"][0][1])
def thr(cell):
    p, _, _, dp = cell
    return (p/100.0)*21.0/(st.mean(dp) if dp else DEADLINE)

def blk(v):
    w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    pk = r = dd = 0
    for x in v:
        r += x; pk = max(pk, r); dd = max(dd, pk-r)
    return dict(n=len(v), w=len(w), l=len(l), wr=100.0*len(w)/max(1, len(w)+len(l)),
                ev=sum(v)/len(v), tot=sum(v), dd=dd, se=st.pstdev(v)/len(v)**0.5)
for b in BOOKS:
    b["s"] = blk([t["R"] for t in b["trades"]])
    b["w1"] = min(t["R"] for t in b["trades"])
    b["over1"] = len([t for t in b["trades"] if t["R"] < -1.0])
    by = defaultdict(list)
    for t in b["trades"]: by[t["d"].weekday()].append(t["R"])
    b["byday"] = by

css = re.search(r"<style>(.*?)</style>",
                open(os.path.join(RESEARCH, "template.html")).read(), re.S).group(1)
def pc(r): return '<span data-pct="%.4f">%+.1f</span>%%' % (r, RISK*r)

# ================= charts, inline SVG so the page needs no library =========
def linechart(series, ylab, fmt="%.0f%%", h=250, ymin=None, ymax=None):
    """series = [(label, colour, [(x, y)...])]. x is risk in percent."""
    w, pad, rpad = 1080, 54, 150
    xs = [x for _, _, pts in series for x, _ in pts]
    ys = [y for _, _, pts in series for _, y in pts]
    x0, x1 = min(xs), max(xs)
    y0 = ymin if ymin is not None else min(0, min(ys))
    y1 = ymax if ymax is not None else max(ys)*1.08
    SX = lambda v: pad + (v-x0)*(w-pad-rpad)/max(1e-9, x1-x0)
    SY = lambda v: h-32 - (v-y0)*(h-32-14)/max(1e-9, y1-y0)
    g = ""
    for i in range(5):
        v = y0 + (y1-y0)*i/4.0
        g += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)"/>'
              '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%s</text>'
              % (pad, SY(v), w-rpad, SY(v), pad-8, SY(v)+4, fmt % v))
    for x in xs:
        pass
    for v in sorted(set(xs)):
        g += ('<text x="%.1f" y="%d" fill="var(--mut)" font-size="11" text-anchor="middle">%.2f%%</text>'
              % (SX(v), h-12, v))
    for lab, col, pts in series:
        g += ('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" stroke-linejoin="round"/>'
              % (" ".join("%.1f,%.1f" % (SX(x), SY(y)) for x, y in pts), col))
        for x, y in pts:
            g += '<circle cx="%.1f" cy="%.1f" r="3.4" fill="%s"/>' % (SX(x), SY(y), col)
        lx, ly = pts[-1]
        g += ('<text x="%.1f" y="%.1f" fill="%s" font-size="12" font-weight="600">%s</text>'
              % (SX(lx)+10, SY(ly)+4, col, lab))
    g += ('<text x="%d" y="%d" fill="var(--mut)" font-size="11">%s</text>'
          % (pad, 12, ylab))
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" '
            'aria-label="%s against risk per trade">%s</svg>' % (w, h, ylab, g))

C_A, C_B = "var(--acc)", "var(--acc2)"
CH_PASS = linechart([("A batch", C_A, [(r, FULL[("orb", r)][0]) for r in RISKS]),
                     ("B batch", C_B, [(r, FULL[("fade", r)][0]) for r in RISKS])],
                    "pass rate, one account taking every signal", ymin=0, ymax=100)
CH_FAIL = linechart([("A batch", C_A, [(r, FULL[("orb", r)][1]) for r in RISKS]),
                     ("B batch", C_B, [(r, FULL[("fade", r)][1]) for r in RISKS])],
                    "breach rate", ymin=0)
CH_THR  = linechart([("A batch", C_A, [(r, thr(FULL[("orb", r)])) for r in RISKS]),
                     ("B batch", C_B, [(r, thr(FULL[("fade", r)])) for r in RISKS])],
                    "passes per account-month", fmt="%.2f", ymin=0)
CH_ROT  = linechart([("A, every day", C_A, [(r, FULL[("orb", r)][0]) for r in RISKS]),
                     ("A, rotation", "var(--mut)", [(r, ROT[("orb", r)][0]) for r in RISKS]),
                     ("B, every day", C_B, [(r, FULL[("fade", r)][0]) for r in RISKS]),
                     ("B, rotation", "var(--neg)", [(r, ROT[("fade", r)][0]) for r in RISKS])],
                    "pass rate: every signal against the two-weekday rotation", ymin=0, ymax=100)

def histo(cells, h=230):
    """days-to-pass distribution, two series of bars"""
    w, pad, rpad = 1080, 54, 130
    bins = list(range(0, 61, 5))
    out = []
    for lab, col, dp in cells:
        c = Counter(min(60, (x//5)*5) for x in dp)
        n = max(1, len(dp))
        out.append((lab, col, [100.0*c[b]/n for b in bins]))
    top = max(v for _, _, vs in out for v in vs)*1.12
    bw = (w-pad-rpad)/len(bins)
    g = ""
    for i in range(4):
        v = top*i/3.0
        g += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)"/>'
              '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%.0f%%</text>'
              % (pad, h-30-(h-44)*i/3.0, w-rpad, h-30-(h-44)*i/3.0, pad-8, h-26-(h-44)*i/3.0, v))
    for j, b in enumerate(bins):
        g += ('<text x="%.1f" y="%d" fill="var(--mut)" font-size="10.5" text-anchor="middle">%d</text>'
              % (pad+j*bw+bw/2, h-12, b))
    for si, (lab, col, vs) in enumerate(out):
        for j, v in enumerate(vs):
            hh = (h-44)*v/top
            g += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="2"/>'
                  % (pad+j*bw+2+si*(bw-4)/len(out), h-30-hh, (bw-4)/len(out)-1, hh, col))
        g += ('<rect x="%d" y="%d" width="10" height="10" fill="%s" rx="2"/>'
              '<text x="%d" y="%d" fill="var(--ink2)" font-size="12">%s</text>'
              % (w-rpad+14, 16+si*20, col, w-rpad+30, 25+si*20, lab))
    g += '<text x="%d" y="%d" fill="var(--mut)" font-size="11">trading days to pass</text>' % (pad, 12)
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" '
            'aria-label="Distribution of trading days to pass">%s</svg>' % (w, h, g))
CH_DAYS = histo([("A batch", C_A, FULL[("orb", RISK)][3]),
                 ("B batch", C_B, FULL[("fade", RISK)][3])])

def schedule():
    w, h, pad = 1080, 210, 120
    cw = (w-pad-20)/5.0
    rows = [("A1 + A2", C_A, (0, 2)), ("A3 + A4", C_A, (1, 3)),
            ("B1 + B2", C_B, (1, 3)), ("B3 + B4", C_B, (2, 4))]
    g = "".join('<text x="%.1f" y="26" fill="var(--mut)" font-size="12" text-anchor="middle" '
                'font-weight="600">%s</text>' % (pad+i*cw+cw/2, WD[i]) for i in range(5))
    for r, (lab, col, days) in enumerate(rows):
        y = 40+r*40
        g += ('<text x="%d" y="%.1f" fill="var(--ink)" font-size="12.5" text-anchor="end" '
              'font-weight="600">%s</text>' % (pad-14, y+22, lab))
        for i in range(5):
            on = i in days
            g += ('<rect x="%.1f" y="%.1f" width="%.1f" height="30" rx="6" fill="%s" '
                  'stroke="var(--line)"/>' % (pad+i*cw+3, y+2, cw-6, col if on else "transparent"))
            if on:
                g += ('<text x="%.1f" y="%.1f" fill="var(--bg)" font-size="11.5" '
                      'text-anchor="middle" font-weight="600">trade</text>'
                      % (pad+i*cw+cw/2, y+22))
            else:
                g += ('<text x="%.1f" y="%.1f" fill="var(--mut)" font-size="11.5" '
                      'text-anchor="middle">flat</text>' % (pad+i*cw+cw/2, y+22))
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" aria-label='
            '"Weekly rotation: A1 and A2 trade Monday and Wednesday, A3 and A4 Tuesday and '
            'Thursday, B1 and B2 Tuesday and Thursday, B3 and B4 Wednesday and Friday">%s</svg>'
            % (w, h, g))
CH_WEEK = schedule()

# ================= tables =================
rows_mc = "".join(
    '<tr%s><td><b>%.2f%%</b></td>%s</tr>'
    % (' class="hi"' if r == RISK else "", r,
       "".join('<td class="%s"><b>%.1f%%</b></td><td class="%s">%.1f%%</td><td>%.1f%%</td>'
               '<td>%s</td><td class="pos"><b>%.3f</b></td>'
               % ("pos" if FULL[(b["k"], r)][0] > 70 else "neg", FULL[(b["k"], r)][0],
                  "neg" if FULL[(b["k"], r)][1] > 8 else "", FULL[(b["k"], r)][1],
                  FULL[(b["k"], r)][2],
                  "%d" % st.median(FULL[(b["k"], r)][3]) if FULL[(b["k"], r)][3] else "&ndash;",
                  thr(FULL[(b["k"], r)]))
               for b in BOOKS))
    for r in RISKS)

rows_rot = ""
for b in BOOKS:
    f, o = FULL[(b["k"], RISK)], ROT[(b["k"], RISK)]
    p = o[0]/100.0
    rows_rot += ('<tr><td><b>%s batch</b></td><td>%.1f%%</td><td>%s</td>'
                 '<td class="%s"><b>%.1f%%</b></td><td>%s</td><td><b>%.2f</b></td>'
                 '<td class="pos"><b>%.1f%%</b></td></tr>'
                 % (b["short"], f[0], "%d" % st.median(f[3]) if f[3] else "&ndash;",
                    "pos" if p > 0.6 else "neg", o[0],
                    "%d" % st.median(o[3]) if o[3] else "&ndash;", 4*p, 100*(1-p)**2))

rows_day = ""
for b in BOOKS:
    for i in sorted(b["byday"]):
        v = b["byday"][i]; w_ = [x for x in v if x > BE]; l_ = [x for x in v if x < -BE]
        rows_day += ('<tr><td><b>%s</b></td><td>%s</td><td>%d</td><td>%d / %d</td>'
                     '<td>%.1f%%</td><td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td></tr>'
                     % (b["short"], WD[i], len(v), len(w_), len(l_),
                        100.0*len(w_)/max(1, len(w_)+len(l_)),
                        "pos" if sum(v) > 0 else "neg", sum(v)/len(v),
                        "pos" if sum(v) > 0 else "neg", sum(v)))

rows_book = "".join(
    '<tr><td><b>%s</b></td><td>%s</td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
    '<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td><td>%.1f R</td>'
    '<td>%+.2f</td><td class="neg">%.3f R</td><td class="neg"><b>%.2f%%</b></td></tr>'
    % (b["lab"], "&ndash;".join((WD[b["days"][0]], WD[b["days"][-1]])), b["s"]["n"],
       b["s"]["w"], b["s"]["l"], b["s"]["wr"], b["s"]["ev"], b["s"]["tot"], b["s"]["dd"],
       b["s"]["ev"]/b["s"]["se"], b["w1"], DAILY/abs(b["w1"]))
    for b in BOOKS)

HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Two batches in rotation — gold 2026</title>
<style>%(css)s</style></head><body><div class="wrap">

<header>
<div class="eyebrow"><span class="dot"></span>research &middot; eight accounts, two batches</div>
<h1>Two batches, <em>four accounts each</em></h1>
<p class="lede">Batch A runs the <a href="index.html">Asia opening range</a>, batch B runs the
<a href="pdfade.html">previous-day fade</a>. Inside each batch the four accounts rotate on
weekdays, so every account trades two days a week and sits flat the rest. Data only &mdash; each
strategy's rules and limitations are on its own page.</p>

<div class="kpi">
<div class="k big"><div class="l">A batch, per account</div><div class="v">%(oa).1f%%</div><div class="n">pass in rotation &middot; %(oad)d days</div></div>
<div class="k big"><div class="l">B batch, per account</div><div class="v">%(ba).1f%%</div><div class="n">pass in rotation &middot; %(bad)d days</div></div>
<div class="k"><div class="l">A batch of 4</div><div class="v">%(oexp).2f</div><div class="n">expected passes &middot; %(oaf).1f%% all fail</div></div>
<div class="k"><div class="l">B batch of 4</div><div class="v">%(bexp).2f</div><div class="n">expected passes &middot; %(baf).1f%% all fail</div></div>
</div>

<nav>
<a href="#week"><span>01</span>The week</a>
<a href="#risk"><span>02</span>Risk and the ceiling</a>
<a href="#mc"><span>03</span>Pass rates</a>
<a href="#rot"><span>04</span>What rotation costs</a>
<a href="#days"><span>05</span>Weekdays</a>
<a href="#books"><span>06</span>The books</a>
</nav>
</header>

<section id="week">
<h2><span class="num">01</span>The week</h2>
<p class="sub">Eight accounts. On any given day four hold a position and four are flat. The pair
sharing a day takes the <b>identical</b> trade.</p>
<figure><div class="fig">%(week)s</div>
<figcaption>The opening range trades Monday to Thursday; the fade trades Tuesday to Friday, Monday
having been dropped because its levels come from Friday with a weekend in between.</figcaption></figure>
<div class="note"><div class="t">Four accounts, two outcomes</div>
<p>A1 and A2 take the same signal at the same moment, so they pass or fail together. A batch of
four is <b>two distinct attempts held twice</b> &mdash; two fees per attempt. Starting the second
account of each pair a week later would give four different outcomes at the same speed.</p></div>
</section>

<section id="risk">
<h2><span class="num">02</span>Risk and the ceiling</h2>
<p class="sub">One trade that costs more than the daily limit ends an account by itself, so the
ceiling is 3%% divided by the worst single loss. It is not the same for both books.</p>
<figure><div class="fig">%(chfail)s</div>
<figcaption>Breach rate against risk per trade. The A batch turns up sharply once a single
worst-case loss can reach the 3%% daily limit; the B batch does not, for the reason below.</figcaption></figure>
<div class="note"><div class="t">The fade's cleaner ceiling is a modelling artefact</div>
<p>The A batch fills <b>past</b> its stop on %(oover)d of %(on)d trades, worst case
<b>%(ow1).3f R</b> &mdash; real-tick execution with spread and slippage. Its ceiling is
<b>%(oceil).2f%%</b>. Every B batch stop fills at exactly <b>&minus;1.000 R</b> because that study
replays M1 bars and takes the stop at its level, modelling <b>no slippage at all</b>, so its
%(bceil).2f%% is optimistic. <b>Treat %(oceil).2f%% as the ceiling for both and 2.5%% as the working
figure.</b></p></div>
</section>

<section id="mc">
<h2><span class="num">03</span>Pass rates</h2>
<p class="sub">%(paths)s resampled paths per cell, %(deadline)d weekday steps of deadline. Days are
resampled <b>by weekday</b> &mdash; a Wednesday is always drawn from Wednesdays &mdash; because the
rotation is a weekday rule. Figures here are for an account taking <b>every</b> signal; section 04
applies the rotation.</p>
<figure><div class="fig">%(chpass)s</div></figure>
<figure><div class="fig">%(chthr)s</div>
<figcaption>Throughput is expected passes per 21 trading days for one account slot cycling: start,
resolve, restart. A fast breach costs a fee but frees the slot, which is why throughput keeps
rising after the pass rate has turned down.</figcaption></figure>
<div class="scroll"><table>
<caption>Per account taking every signal. The highlighted row is the working risk.</caption>
<thead><tr><th>Risk</th>
<th>A: pass</th><th>breach</th><th>open</th><th>days</th><th>per month</th>
<th>B: pass</th><th>breach</th><th>open</th><th>days</th><th>per month</th></tr></thead>
<tbody>%(rows_mc)s</tbody></table></div>
<figure><div class="fig">%(chdays)s</div>
<figcaption>How long a passing account takes, at %(risk).2f%% risk and taking every signal.</figcaption></figure>
</section>

<section id="rot">
<h2><span class="num">04</span>What rotation costs</h2>
<p class="sub">An account on two weekdays sees about half the signals, so it reaches +12%% later
and more attempts run out of deadline.</p>
<figure><div class="fig">%(chrot)s</div></figure>
<div class="scroll"><table>
<caption>At %(risk).2f%% risk. A batch of four is two distinct attempts, so all four fail together
only when both of those attempts fail.</caption>
<thead><tr><th>Batch</th><th>Every signal: pass</th><th>days</th>
<th>In rotation: pass</th><th>days</th><th>Expected passes of 4</th><th>All four fail</th></tr></thead>
<tbody>%(rows_rot)s</tbody></table></div>
<div class="good"><div class="t">What the rotation is actually buying</div>
<p>It is not throughput &mdash; each account is slower. It is that the two pairs hold
<b>different days</b>, so no single bad session can take the whole batch. All four fail together
only %(oaf).1f%% of the time in batch A and %(baf).1f%% in batch B.</p></div>
</section>

<section id="days">
<h2><span class="num">05</span>Weekdays</h2>
<p class="sub">What each pair is actually holding. On this sample the pairs are not equal, but the
gap is not significant &mdash; shuffling the trades beats it about a quarter of the time &mdash; so
it should be read as noise rather than as one pair being better.</p>
<div class="scroll"><table>
<caption>By weekday, 2026. A1+A2 hold the Mon and Wed rows, A3+A4 the Tue and Thu rows; B1+B2 the
Tue and Thu rows, B3+B4 the Wed and Fri rows.</caption>
<thead><tr><th>Batch</th><th>Day</th><th>Trades</th><th>W / L</th><th>Win rate</th>
<th>EV per trade</th><th>Total R</th></tr></thead>
<tbody>%(rows_day)s</tbody></table></div>
<div class="note"><div class="t">Rotate the assignment, not just the accounts</div>
<p>Because the weekdays are fixed, any real day-of-week effect would land on the same pair for
ever. Swapping which pair takes which days each week costs nothing and removes that exposure.</p></div>
</section>

<section id="books">
<h2><span class="num">06</span>The books</h2>
<div class="scroll"><table>
<caption>2026. R is size-independent. The ceiling is 3%% divided by the worst single loss.</caption>
<thead><tr><th>Strategy</th><th>Days</th><th>Trades</th><th>W / L</th><th>Win rate</th>
<th>EV per trade</th><th>Total R</th><th>Worst dip</th><th>t</th><th>Worst single</th><th>Ceiling</th></tr></thead>
<tbody>%(rows_book)s</tbody></table></div>
</section>

<footer><p><b>Two batches in rotation.</b> Generated %(gen)s. Barrier simulations on resampled
weekdays from the <a href="index.html">opening range</a> and the <a href="pdfade.html">previous-day
fade</a>; +12%% target, 12%% maximum loss, 3%% daily, both loss barriers checked trade by trade.
Each strategy's own limitations are on its page and are not repeated here.</p></footer>
</div></body></html>"""

O, F = BOOKS[0], BOOKS[1]
ro, rf = ROT[("orb", RISK)], ROT[("fade", RISK)]
open(os.path.join(REPO, "batches.html"), "w").write(HTML % dict(
    css=css, risk=RISK, paths="{:,}".format(PATHS), deadline=DEADLINE,
    week=CH_WEEK, chpass=CH_PASS, chfail=CH_FAIL, chthr=CH_THR, chdays=CH_DAYS, chrot=CH_ROT,
    rows_mc=rows_mc, rows_rot=rows_rot, rows_day=rows_day, rows_book=rows_book,
    oa=ro[0], oad=st.median(ro[3]) if ro[3] else 0,
    ba=rf[0], bad=st.median(rf[3]) if rf[3] else 0,
    oexp=4*ro[0]/100.0, bexp=4*rf[0]/100.0,
    oaf=100*(1-ro[0]/100.0)**2, baf=100*(1-rf[0]/100.0)**2,
    oover=O["over1"], on=O["s"]["n"], ow1=O["w1"],
    oceil=DAILY/abs(O["w1"]), bceil=DAILY/abs(F["w1"]),
    gen=dt.date.today().strftime("%d %B %Y")))
print("wrote batches.html")
print("  A per account in rotation %.1f%% pass, %d days | batch of 4: %.2f expected, %.1f%% all fail"
      % (ro[0], st.median(ro[3]) if ro[3] else 0, 4*ro[0]/100.0, 100*(1-ro[0]/100.0)**2))
print("  B per account in rotation %.1f%% pass, %d days | batch of 4: %.2f expected, %.1f%% all fail"
      % (rf[0], st.median(rf[3]) if rf[3] else 0, 4*rf[0]/100.0, 100*(1-rf[0]/100.0)**2))
