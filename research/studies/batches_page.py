"""Two batches of four challenge accounts, rotating on each signal. Data only.

  A batch  opening range      A1+A2 take signal 1, A3+A4 signal 2, A1+A2 3, ...
  B batch  previous-day fade  B1+B2 take signal 1, B3+B4 signal 2, ...

The rotation is by SIGNAL, not by weekday: a pair waits for its turn rather than
for a day of the week. So each pair takes half the trades and the assignment
drifts across weekdays on its own.

The pair sharing a signal takes the identical trade, so a batch of four is two
distinct attempts each held twice.

Pass rates are barrier simulations over resampled signals. Barriers: +12%
target, 12% maximum loss, 3% daily, all checked trade by trade -- an account
through a limit intraday is gone whatever the day closes at.

Account labelling lives on this page only; the strategy pages stay the record of
the strategy.

    python3 studies/batches_page.py
"""
import os, re, json, random, datetime as dt, statistics as st
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE); REPO = os.path.dirname(RESEARCH)

TARGET, MAXLOSS, DAILY = 12.0, 12.0, 3.0
PATHS = 20000
RISK  = 2.5
RISKS = (1.0, 1.5, 2.0, 2.25, 2.5)      # 2.5% is the cap, not a point on a curve
BE    = 0.10
random.seed(20260910)

def load(fn, key=None):
    d = json.load(open(os.path.join(RESEARCH, "data", fn)))
    return sorted([dict(d=dt.date.fromisoformat(t["date"]), R=t["R"])
                   for t in (d[key] if key else d)], key=lambda z: z["d"])

BOOKS = [dict(lab="Opening range", k="orb", short="A", href="index.html",
              trades=load("trade_index.json"), pairs=("A1 + A2", "A3 + A4")),
         dict(lab="Previous-day fade", k="fade", short="B", href="pdfade.html",
              trades=load("pdfade_trades.json", "trades"), pairs=("B1 + B2", "B3 + B4"))]

# --- signals arrive as DAYS: everything one day produced goes to one pair ---
for b in BOOKS:
    byday = defaultdict(list)
    for t in b["trades"]: byday[t["d"]].append(t["R"])
    b["signals"] = [(d, byday[d]) for d in sorted(byday)]
    for i, (d, rs) in enumerate(b["signals"]):
        b.setdefault("assigned", []).append((d, rs, i % 2))
    b["weeks"] = max(1, (b["signals"][-1][0]-b["signals"][0][0]).days/7.0)
    b["per_week"] = len(b["signals"])/b["weeks"]

def blk(v):
    w = [x for x in v if x > BE]; l = [x for x in v if x < -BE]
    pk = r = dd = 0
    for x in v:
        r += x; pk = max(pk, r); dd = max(dd, pk-r)
    return dict(n=len(v), w=len(w), l=len(l),
                wr=100.0*len(w)/max(1, len(w)+len(l)) if (w or l) else None,
                ev=sum(v)/len(v), tot=sum(v), dd=dd,
                se=st.pstdev(v)/len(v)**0.5 if len(v) > 1 else 9.9)
for b in BOOKS:
    b["s"] = blk([t["R"] for t in b["trades"]])
    b["w1"] = min(t["R"] for t in b["trades"])
    b["over1"] = len([t for t in b["trades"] if t["R"] < -1.0])
    b["ps"] = [blk([r for _, rs, p in b["assigned"] if p == i for r in rs]) for i in (0, 1)]

def sim(b, risk, every=False):
    """One account. every=True takes every signal; otherwise every other one.
    Time is counted in signals and converted with the book's own signal rate."""
    sig = [rs for _, rs in b["signals"]]
    step = 1 if every else 2
    cap = int(90*b["per_week"]/7.0)          # a 90-calendar-day horizon
    c = Counter(); dp = []
    for _ in range(PATHS):
        eq = 0.0; out = None; j = 0
        for j in range(0, cap, step):
            dl = 0.0
            for R in sig[random.randrange(len(sig))]:
                p = R*risk; eq += p
                if p < 0: dl += p
                if eq <= -MAXLOSS or dl <= -DAILY: out = "fail"; break
                if eq >= TARGET: out = "pass"; break
            if out: break
        if out == "pass": dp.append((j+1)*7.0/b["per_week"])
        c[out or "abandon"] += 1
    return (100.0*c["pass"]/PATHS, 100.0*c["fail"]/PATHS, 100.0*c["abandon"]/PATHS, dp)

FULL, ROT = {}, {}
for b in BOOKS:
    for r in RISKS:
        FULL[(b["k"], r)] = sim(b, r, every=True)
        ROT[(b["k"], r)]  = sim(b, r)
def thr(cell):
    p, _, _, dp = cell
    return (p/100.0)*30.0/(st.mean(dp) if dp else 90.0)

css = re.search(r"<style>(.*?)</style>",
                open(os.path.join(RESEARCH, "template.html")).read(), re.S).group(1)
def pc(r): return '<span data-pct="%.4f">%+.1f</span>%%' % (r, RISK*r)
C_A, C_B, C_M, C_N = "var(--acc)", "var(--acc2)", "var(--mut)", "var(--neg)"

# ================= charts, inline SVG =================
def linechart(series, ylab, fmt="%.0f%%", h=250, ymin=None, ymax=None):
    w, pad, rpad = 1080, 54, 156
    xs = [x for _, _, pts in series for x, _ in pts]
    ys = [y for _, _, pts in series for _, y in pts]
    x0, x1 = min(xs), max(xs)
    y0 = ymin if ymin is not None else min(0, min(ys))
    y1 = ymax if ymax is not None else max(ys)*1.1
    SX = lambda v: pad + (v-x0)*(w-pad-rpad)/max(1e-9, x1-x0)
    SY = lambda v: h-32 - (v-y0)*(h-32-16)/max(1e-9, y1-y0)
    g = '<text x="%d" y="12" fill="var(--mut)" font-size="11">%s</text>' % (pad, ylab)
    for i in range(5):
        v = y0 + (y1-y0)*i/4.0
        g += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)"/>'
              '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%s</text>'
              % (pad, SY(v), w-rpad, SY(v), pad-8, SY(v)+4, fmt % v))
    for v in sorted(set(xs)):
        g += ('<text x="%.1f" y="%d" fill="var(--mut)" font-size="11" text-anchor="middle">%.2f%%</text>'
              % (SX(v), h-12, v))
    for lab, col, pts in series:
        g += ('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" stroke-linejoin="round"/>'
              % (" ".join("%.1f,%.1f" % (SX(x), SY(y)) for x, y in pts), col))
        for x, y in pts: g += '<circle cx="%.1f" cy="%.1f" r="3.4" fill="%s"/>' % (SX(x), SY(y), col)
        g += ('<text x="%.1f" y="%.1f" fill="%s" font-size="12" font-weight="600">%s</text>'
              % (SX(pts[-1][0])+10, SY(pts[-1][1])+4, col, lab))
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" '
            'aria-label="%s against risk per trade">%s</svg>' % (w, h, ylab, g))

CH_PASS = linechart([("A, in rotation", C_A, [(r, ROT[("orb", r)][0]) for r in RISKS]),
                     ("B, in rotation", C_B, [(r, ROT[("fade", r)][0]) for r in RISKS])],
                    "pass rate per account, taking every other signal", ymin=0, ymax=100)
CH_ROT  = linechart([("A, every signal", C_M, [(r, FULL[("orb", r)][0]) for r in RISKS]),
                     ("A, in rotation", C_A, [(r, ROT[("orb", r)][0]) for r in RISKS]),
                     ("B, every signal", C_N, [(r, FULL[("fade", r)][0]) for r in RISKS]),
                     ("B, in rotation", C_B, [(r, ROT[("fade", r)][0]) for r in RISKS])],
                    "what the rotation costs: every signal against every other", ymin=0, ymax=100)
CH_FAIL = linechart([("A batch", C_A, [(r, ROT[("orb", r)][1]) for r in RISKS]),
                     ("B batch", C_B, [(r, ROT[("fade", r)][1]) for r in RISKS])],
                    "breach rate per account, in rotation", ymin=0)
CH_THR  = linechart([("A, in rotation", C_A, [(r, thr(ROT[("orb", r)])) for r in RISKS]),
                     ("B, in rotation", C_B, [(r, thr(ROT[("fade", r)])) for r in RISKS])],
                    "passes per account-month", fmt="%.2f", ymin=0)

def histo(cells, h=232):
    w, pad, rpad = 1080, 54, 132
    bins = list(range(0, 96, 10))
    out = []
    for lab, col, dp in cells:
        c = Counter(min(90, int(x//10)*10) for x in dp); n = max(1, len(dp))
        out.append((lab, col, [100.0*c[b]/n for b in bins]))
    top = max(v for _, _, vs in out for v in vs)*1.14
    bw = (w-pad-rpad)/len(bins)
    g = '<text x="%d" y="12" fill="var(--mut)" font-size="11">calendar days to pass</text>' % pad
    for i in range(4):
        v = top*i/3.0; y = h-30-(h-46)*i/3.0
        g += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="var(--line)"/>'
              '<text x="%d" y="%.1f" fill="var(--mut)" font-size="11" text-anchor="end">%.0f%%</text>'
              % (pad, y, w-rpad, y, pad-8, y+4, v))
    for j, b in enumerate(bins):
        g += ('<text x="%.1f" y="%d" fill="var(--mut)" font-size="10.5" text-anchor="middle">%d</text>'
              % (pad+j*bw+bw/2, h-12, b))
    for si, (lab, col, vs) in enumerate(out):
        for j, v in enumerate(vs):
            hh = (h-46)*v/top
            g += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" rx="2"/>'
                  % (pad+j*bw+2+si*(bw-4)/len(out), h-30-hh, (bw-4)/len(out)-1, hh, col))
        g += ('<rect x="%d" y="%d" width="10" height="10" fill="%s" rx="2"/>'
              '<text x="%d" y="%d" fill="var(--ink2)" font-size="12">%s</text>'
              % (w-rpad+14, 18+si*20, col, w-rpad+30, 27+si*20, lab))
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" '
            'aria-label="Distribution of calendar days to pass">%s</svg>' % (w, h, g))
CH_DAYS = histo([("A batch", C_A, ROT[("orb", RISK)][3]),
                 ("B batch", C_B, ROT[("fade", RISK)][3])])

def rotdiag(b):
    """The first fourteen signals, showing which pair takes each."""
    w, h, pad = 1080, 150, 16
    n = 14
    cw = (w-pad*2)/float(n)
    g = ('<text x="%d" y="16" fill="var(--mut)" font-size="11">%s &mdash; the first %d signals of '
         '2026, in order</text>' % (pad, b["lab"], n))
    for i, (d, rs, p) in enumerate(b["assigned"][:n]):
        x = pad+i*cw
        col = C_A if p == 0 else C_M
        g += ('<rect x="%.1f" y="30" width="%.1f" height="44" rx="7" fill="%s"/>'
              '<text x="%.1f" y="49" fill="var(--bg)" font-size="11" text-anchor="middle" '
              'font-weight="600">%s</text>'
              '<text x="%.1f" y="65" fill="var(--bg)" font-size="10" text-anchor="middle" '
              'opacity="0.85">%s</text>'
              % (x+2, cw-4, col, x+cw/2, b["pairs"][p].replace(" ", ""), x+cw/2,
                 d.strftime("%d %b")))
        g += ('<text x="%.1f" y="92" fill="var(--mut)" font-size="10" text-anchor="middle">#%d</text>'
              % (x+cw/2, i+1))
        rr = sum(rs)
        g += ('<text x="%.1f" y="112" fill="%s" font-size="11" text-anchor="middle" '
              'font-weight="600">%+.2f</text>'
              % (x+cw/2, "var(--pos)" if rr > BE else "var(--neg)" if rr < -BE else "var(--mut)", rr))
    g += ('<text x="%d" y="136" fill="var(--mut)" font-size="11">R for that signal underneath. '
          'The pair alternates on every signal, so the weekday it lands on drifts.</text>' % pad)
    return ('<svg viewBox="0 0 %d %d" style="width:100%%;height:auto" role="img" aria-label='
            '"The first fourteen signals alternating between the two pairs of accounts">%s</svg>'
            % (w, h, g))
CH_RA, CH_RB = rotdiag(BOOKS[0]), rotdiag(BOOKS[1])

# ================= tables =================
rows_pair = ""
for b in BOOKS:
    for i in (0, 1):
        s = b["ps"][i]
        rows_pair += ('<tr><td><b>%s</b></td><td>%s</td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
                      '<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td><td>%.1f R</td>'
                      '<td class="%s"><b>%s</b></td></tr>'
                      % (b["pairs"][i], b["lab"], s["n"], s["w"], s["l"], s["wr"],
                         "pos" if s["ev"] > 0 else "neg", s["ev"],
                         "pos" if s["tot"] > 0 else "neg", s["tot"], s["dd"],
                         "pos" if s["tot"] > 0 else "neg", pc(s["tot"])))

rows_mc = "".join(
    '<tr%s><td><b>%.2f%%</b></td>%s</tr>'
    % (' class="hi"' if r == RISK else "", r,
       "".join('<td class="%s"><b>%.1f%%</b></td><td class="%s">%.1f%%</td><td>%.1f%%</td>'
               '<td>%s</td><td class="pos"><b>%.2f</b></td>'
               % ("pos" if ROT[(b["k"], r)][0] > 70 else "neg", ROT[(b["k"], r)][0],
                  "neg" if ROT[(b["k"], r)][1] > 8 else "", ROT[(b["k"], r)][1],
                  ROT[(b["k"], r)][2],
                  "%.0f" % st.median(ROT[(b["k"], r)][3]) if ROT[(b["k"], r)][3] else "&ndash;",
                  thr(ROT[(b["k"], r)]))
               for b in BOOKS))
    for r in RISKS)

rows_rot = ""
for b in BOOKS:
    f, o = FULL[(b["k"], RISK)], ROT[(b["k"], RISK)]
    p = o[0]/100.0
    rows_rot += ('<tr><td><b>%s batch</b></td><td>%.1f a week</td><td>%.1f%%</td><td>%.0f</td>'
                 '<td class="%s"><b>%.1f%%</b></td><td>%.0f</td><td><b>%.2f</b></td>'
                 '<td class="%s"><b>%.1f%%</b></td></tr>'
                 % (b["short"], b["per_week"], f[0], st.median(f[3]) if f[3] else 0,
                    "pos" if p > 0.7 else "neg", o[0], st.median(o[3]) if o[3] else 0,
                    4*p, "pos" if (1-p)**2 < 0.05 else "neg", 100*(1-p)**2))

rows_book = "".join(
    '<tr><td><b>%s</b></td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
    '<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td><td>%.1f R</td>'
    '<td>%+.2f</td><td class="neg">%.3f R</td><td class="%s"><b>%.2f%%</b></td></tr>'
    % (b["lab"], b["s"]["n"], b["s"]["w"], b["s"]["l"], b["s"]["wr"], b["s"]["ev"],
       b["s"]["tot"], b["s"]["dd"], b["s"]["ev"]/b["s"]["se"], b["w1"],
       "neg" if DAILY-RISK*abs(b["w1"]) < 0.5 else "pos", DAILY-RISK*abs(b["w1"]))
    for b in BOOKS)

O, F = BOOKS
ro, rf = ROT[("orb", RISK)], ROT[("fade", RISK)]

HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Two batches in rotation — gold 2026</title>
<style>%(css)s</style></head><body><div class="wrap">

<header>
<div class="eyebrow"><span class="dot"></span>research &middot; eight accounts, two batches</div>
<h1>Two batches, <em>four accounts each</em></h1>
<p class="lede">Batch A runs the <a href="index.html">Asia opening range</a>, batch B the
<a href="pdfade.html">previous-day fade</a>. Inside each batch the accounts rotate on every
<b>signal</b>: A1+A2 take the first, A3+A4 the second, A1+A2 the third. Risk is 2.5%% per trade.
Data only &mdash; each strategy's rules and limitations are on its own page.</p>

<div class="kpi">
<div class="k big"><div class="l">A account, in rotation</div><div class="v">%(oa).1f%%</div><div class="n">pass &middot; %(oad).0f days median</div></div>
<div class="k big"><div class="l">B account, in rotation</div><div class="v">%(ba).1f%%</div><div class="n">pass &middot; %(bad).0f days median</div></div>
<div class="k"><div class="l">A batch of 4</div><div class="v">%(oexp).2f</div><div class="n">expected passes &middot; %(oaf).1f%% all fail</div></div>
<div class="k"><div class="l">B batch of 4</div><div class="v">%(bexp).2f</div><div class="n">expected passes &middot; %(baf).1f%% all fail</div></div>
</div>

<nav>
<a href="#rot"><span>01</span>Who takes what</a>
<a href="#pairs"><span>02</span>Each pair in 2026</a>
<a href="#room"><span>03</span>Room at 2.5%%</a>
<a href="#rates"><span>04</span>Pass rates</a>
<a href="#cost"><span>05</span>What rotation costs</a>
<a href="#books"><span>06</span>The books</a>
</nav>
</header>

<section id="rot">
<h2><span class="num">01</span>Who takes what</h2>
<p class="sub">The rotation is by signal, not by weekday, so a pair waits for its turn rather than
for a particular day &mdash; and the weekday each pair lands on drifts by itself.</p>
<figure><div class="fig">%(rota)s</div></figure>
<figure><div class="fig">%(rotb)s</div>
<figcaption>Both pairs of each batch take half the signals. Signals arrive %(orate).1f a week in
batch A and %(brate).1f a week in batch B, so a pair sees about %(ohalf).1f and %(bhalf).1f
a week.</figcaption></figure>
<div class="note"><div class="t">Four accounts, two outcomes</div>
<p>A1 and A2 take the same signal at the same moment, so they pass or fail together. A batch of
four is <b>two distinct attempts held twice</b> &mdash; two fees per attempt. Starting the second
account of each pair a week later would give four different outcomes at the same speed.</p></div>
</section>

<section id="pairs">
<h2><span class="num">02</span>Each pair in 2026</h2>
<p class="sub">What each pair of accounts actually held, splitting the real year by the rotation.</p>
<div class="scroll"><table>
<caption>The two pairs of each batch, alternating on every signal. Account is R &times; 2.5%%.</caption>
<thead><tr><th>Accounts</th><th>Strategy</th><th>Trades</th><th>W / L</th><th>Win rate</th>
<th>EV per trade</th><th>Total R</th><th>Worst dip</th><th>Account</th></tr></thead>
<tbody>%(rows_pair)s</tbody></table></div>
<p>The pairs are not identical because they held different trades, but they are two halves of one
sample rather than two strategies &mdash; the split is arbitrary and neither pair has an edge over
the other.</p>
</section>

<section id="room">
<h2><span class="num">03</span>Room at 2.5%%</h2>
<p class="sub">Risk is capped at 2.5%% per trade. The question is whether that keeps a single bad
trade clear of the 3%% daily limit, because one trade past it ends the account on its own.</p>
<div class="scroll"><table>
<caption>At 2.5%% per trade a loss of 1.20 R is the whole daily limit.</caption>
<thead><tr><th>Batch</th><th>Worst single loss</th><th>Costs at 2.5%%</th><th>Headroom to 3%%</th>
<th>Breaches at</th><th>Trades past &minus;1R</th></tr></thead>
<tbody>
<tr><td><b>A &mdash; opening range</b></td><td class="neg">%(ow1).3f R</td>
<td class="neg"><b>%(ocost).2f%%</b></td><td class="%(ocls)s"><b>%(oroom).2f%%</b></td>
<td>1.20 R</td><td>%(oover)d of %(on)d</td></tr>
<tr><td><b>B &mdash; previous-day fade</b></td><td>%(bw1).3f R</td>
<td><b>%(bcost).2f%%</b></td><td class="pos"><b>%(broom).2f%%</b></td>
<td>1.20 R</td><td>%(bover)d of %(bn)d</td></tr>
</tbody></table></div>
<div class="note"><div class="t">The A batch has little room, and it is measured room</div>
<p>The opening range fills <b>past</b> its stop on %(oover)d of %(on)d trades &mdash; real-tick
execution, spread and slippage included &mdash; worst case <b>%(ow1).3f R</b>. At 2.5%% that costs
<b>%(ocost).2f%%</b> of the 3.00%% daily limit, leaving <b>%(oroom).2f%%</b>. A fill only
%(pcworse).0f%% worse than anything on record would breach the day on one trade.</p></div>
<div class="note"><div class="t">The B batch's larger headroom is not real</div>
<p>Every fade stop fills at exactly <b>&minus;1.000 R</b>, because that study replays M1 bars and
takes the stop at its level &mdash; it models <b>no slippage past the stop at all</b>. Its
<b>%(broom).2f%%</b> is therefore optimistic; give it the overshoot the A batch actually shows and
it lands where the A batch does.</p></div>
<figure><div class="fig">%(chfail)s</div>
<figcaption>Breach rate per account in rotation, up to the 2.5%% cap.</figcaption></figure>
</section>

<section id="rates">
<h2><span class="num">04</span>Pass rates</h2>
<p class="sub">%(paths)s resampled paths per cell, to a 90-calendar-day horizon. Signals are
resampled whole, so trades that shared a day keep sharing one and the daily limit still means
something. These are per account <b>in rotation</b>.</p>
<figure><div class="fig">%(chpass)s</div></figure>
<div class="scroll"><table>
<caption>Per account taking every other signal. Highlighted row is the 2.5%% cap.</caption>
<thead><tr><th>Risk</th>
<th>A: pass</th><th>breach</th><th>open</th><th>days</th><th>per month</th>
<th>B: pass</th><th>breach</th><th>open</th><th>days</th><th>per month</th></tr></thead>
<tbody>%(rows_mc)s</tbody></table></div>
<figure><div class="fig">%(chthr)s</div>
<figcaption>Passes per account-month, one slot cycling: start, resolve, restart. A fast breach
costs a fee but frees the slot.</figcaption></figure>
<figure><div class="fig">%(chdays)s</div>
<figcaption>How long a passing account takes at 2.5%%, in calendar days.</figcaption></figure>
</section>

<section id="cost">
<h2><span class="num">05</span>What rotation costs</h2>
<figure><div class="fig">%(chrot)s</div></figure>
<div class="scroll"><table>
<caption>At 2.5%% risk. A batch of four is two distinct attempts, so all four fail together only
when both of those fail.</caption>
<thead><tr><th>Batch</th><th>Signals</th><th>Every signal: pass</th><th>days</th>
<th>In rotation: pass</th><th>days</th><th>Expected passes of 4</th><th>All four fail</th></tr></thead>
<tbody>%(rows_rot)s</tbody></table></div>
<div class="good"><div class="t">What the rotation buys</div>
<p>It is not throughput &mdash; each account is slower, because it waits out every other signal.
It is that the two pairs hold <b>different trades</b>, so no single session can take the whole
batch: all four fail together only %(oaf).1f%% of the time in batch A and %(baf).1f%% in
batch B.</p></div>
</section>

<section id="books">
<h2><span class="num">06</span>The books</h2>
<div class="scroll"><table>
<caption>2026, the whole strategy before the rotation splits it. R is size-independent.</caption>
<thead><tr><th>Strategy</th><th>Trades</th><th>W / L</th><th>Win rate</th><th>EV per trade</th>
<th>Total R</th><th>Worst dip</th><th>t</th><th>Worst single</th><th>Headroom at 2.5%%</th></tr></thead>
<tbody>%(rows_book)s</tbody></table></div>
</section>

<footer><p><b>Two batches in rotation.</b> Generated %(gen)s. Barrier simulations on resampled
signals from the <a href="index.html">opening range</a> and the <a href="pdfade.html">previous-day
fade</a>; +12%% target, 12%% maximum loss, 3%% daily, all checked trade by trade. Each strategy's own
limitations are on its page and are not repeated here.</p></footer>
</div></body></html>"""

open(os.path.join(REPO, "batches.html"), "w").write(HTML % dict(
    css=css, paths="{:,}".format(PATHS), gen=dt.date.today().strftime("%d %B %Y"),
    rota=CH_RA, rotb=CH_RB, chpass=CH_PASS, chrot=CH_ROT, chfail=CH_FAIL,
    chthr=CH_THR, chdays=CH_DAYS,
    rows_pair=rows_pair, rows_mc=rows_mc, rows_rot=rows_rot, rows_book=rows_book,
    oa=ro[0], oad=st.median(ro[3]) if ro[3] else 0,
    ba=rf[0], bad=st.median(rf[3]) if rf[3] else 0,
    oexp=4*ro[0]/100.0, bexp=4*rf[0]/100.0,
    oaf=100*(1-ro[0]/100.0)**2, baf=100*(1-rf[0]/100.0)**2,
    orate=O["per_week"], brate=F["per_week"],
    ohalf=O["per_week"]/2, bhalf=F["per_week"]/2,
    ow1=O["w1"], bw1=F["w1"], oover=O["over1"], bover=F["over1"],
    on=O["s"]["n"], bn=F["s"]["n"],
    ocost=RISK*abs(O["w1"]), bcost=RISK*abs(F["w1"]),
    oroom=DAILY-RISK*abs(O["w1"]), broom=DAILY-RISK*abs(F["w1"]),
    ocls="neg" if DAILY-RISK*abs(O["w1"]) < 0.5 else "pos",
    pcworse=100.0*(DAILY/RISK/abs(O["w1"])-1.0)))
print("wrote batches.html")
for b, c in ((O, ro), (F, rf)):
    print("  %s batch: %.1f%% pass in %.0f days | of 4: %.2f expected, %.1f%% all fail | pairs %+.1f R / %+.1f R"
          % (b["short"], c[0], st.median(c[3]) if c[3] else 0, 4*c[0]/100.0,
             100*(1-c[0]/100.0)**2, b["ps"][0]["tot"], b["ps"][1]["tot"]))
