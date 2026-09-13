"""What a 5%-daily / 10%-static account does with the ORB and the NQ fade.

Different rules to the FundingPips 1 Step Flex the other pages model: a 5%
daily limit instead of 3%, a 10% static maximum loss instead of 12%, the same
12% target. At 2% a trade that leaves room for two losses in a day, which is
the most the two strategies can produce -- one trades the Asia session, the
other New York.

Everything here is simulated at the level of a DAY, not a trade. The daily
limit is a per-day rule, so a day that produces two trades has to be resampled
as one unit or the limit is modelled as something it is not. It also keeps the
pairing: the days both strategies fire are the days that can breach it.

    python3 research/account_page.py

Writes account.html at the repo root.
"""
import os, sys, csv, json, math, random, datetime as dt
import statistics as st
from collections import defaultdict, Counter
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "lib"))
import page
import fade_page as FP

RISK = 2.0          # percent of the starting balance, per trade
TARGET = 12.0       # percent, the profit target
DAILY = 5.0         # percent, the daily loss limit
MAXLOSS = 10.0      # percent, static, from the starting balance
HORIZON = 400       # trading days before an attempt is abandoned
PATHS = 40000
BE = 0.05

QUARTERS = {"Q1": ("Jan", "Feb", "Mar"), "Q2": ("Apr", "May", "Jun"),
            "Q3": ("Jul", "Aug", "Sep"), "Q4": ("Oct", "Nov", "Dec")}


# ------------------------------------------------------------------ data ---
def load():
    """The two strategies' trades, and the calendar days each could have traded."""
    orb = FP.load_orb()
    nq = FP.load_fade("nq")
    for t in nq["trades"]:
        t["d"] = dt.date.fromisoformat(t["date"])
    elig = set(dt.date.fromisoformat(x) for x in nq["days"])
    # the ORB trades Mon-Thu on the same calendar; its eligible days are not in
    # the json, so take every weekday in the covered span that fits its week
    lo = min(t["d"] for t in orb["trades"]); hi = max(t["d"] for t in orb["trades"])
    d = lo
    while d <= hi:
        if d.weekday() in (0, 1, 2, 3):
            elig.add(d)
        d += dt.timedelta(days=1)
    return orb["trades"], nq["trades"], sorted(elig)


def daybook(sets, elig):
    """One entry per eligible day: the R values that day produced, in order."""
    by = defaultdict(list)
    for name, trades in sets:
        for t in trades:
            by[t["d"]].append((name, t["R"]))
    return [(d, by.get(d, [])) for d in elig]


# ------------------------------------------------------------ simulation ---
def simulate(book, risk=RISK, target=TARGET, daily=DAILY, maxloss=MAXLOSS,
             paths=PATHS, horizon=HORIZON, seed=7):
    """Resample whole days. Returns the outcome of every attempt."""
    random.seed(seed)
    days = [v for _, v in book]
    passed = []; killed = Counter(); dd_at_pass = []
    for _ in range(paths):
        eq = 0.0; peak = 0.0; worst = 0.0; d = 0; n = 0
        while d < horizon:
            d += 1
            today = days[random.randrange(len(days))]
            if not today:
                continue                      # a day with no signal is not a day
            pnl = sum(risk * r for _, r in today)
            n += len(today)
            if pnl <= -daily:
                killed["daily limit"] += 1; break
            eq += pnl
            peak = max(peak, eq); worst = max(worst, peak - eq)
            if eq <= -maxloss:
                killed["maximum loss"] += 1; break
            if eq >= target:
                passed.append((d, n, worst)); dd_at_pass.append(worst); break
        else:
            killed["ran out of time"] += 1
    if not passed:
        return dict(rate=0.0, killed=dict(killed))
    dd = sorted(d for _, _, d in passed)
    return dict(
        rate=100.0 * len(passed) / paths,
        days=dict(p10=_q([x[0] for x in passed], .10), p25=_q([x[0] for x in passed], .25),
                  p50=_q([x[0] for x in passed], .50), p75=_q([x[0] for x in passed], .75),
                  p90=_q([x[0] for x in passed], .90),
                  mean=sum(x[0] for x in passed) / len(passed)),
        trades=dict(p25=_q([x[1] for x in passed], .25), p50=_q([x[1] for x in passed], .50),
                    p75=_q([x[1] for x in passed], .75),
                    mean=sum(x[1] for x in passed) / len(passed)),
        dd=dict(p50=_q(dd, .50), p90=_q(dd, .90), max=dd[-1]),
        killed={k: 100.0 * v / paths for k, v in killed.items()})


def _q(v, p):
    v = sorted(v)
    return v[min(int(p * len(v)), len(v) - 1)]


# ------------------------------------------------------- worst sequences ---
def runs(trades):
    """The real losing runs this strategy had, longest first."""
    out = []; cur = []
    for t in sorted(trades, key=lambda x: x["d"]):
        if t["R"] <= BE:
            cur.append(t)
        else:
            if cur:
                out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return sorted(out, key=lambda r: sum(x["R"] for x in r))


def day_runs(book):
    """Consecutive LOSING DAYS at the account level -- what you actually sit
    through, rather than one strategy's run interleaved with the other's."""
    out = []; cur = []
    for d, v in book:
        if not v:
            continue
        pnl = sum(r for _, r in v)
        if pnl <= BE:
            cur.append((d, pnl))
        else:
            if cur:
                out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return sorted(out, key=lambda r: sum(x[1] for x in r))


def equity_dd(book):
    """Two different numbers, and only one of them is the account rule.

    Peak-to-trough is what a TRAILING limit measures. A static limit is
    measured from the starting balance, so what matters is the lowest equity
    ever reached from zero -- once you are up, a big giveback can still be
    nowhere near the line."""
    eq = peak = worst = 0.0; lo_d = hi_d = None; pk_d = None
    floor = 0.0; floor_d = None
    for d, v in book:
        if not v:
            continue
        eq += sum(r for _, r in v)
        if eq > peak:
            peak = eq; pk_d = d
        if peak - eq > worst:
            worst = peak - eq; hi_d = pk_d; lo_d = d
        if eq < floor:
            floor = eq; floor_d = d
    return worst, hi_d, lo_d, floor, floor_d


# ----------------------------------------------------------- the page -----
def hist_svg(book, risk, target, daily, maxloss, paths=4000, seed=11,
             w=1080, h=300, pad=46):
    """How long an attempt takes, as a distribution rather than a median."""
    random.seed(seed)
    days = [v for _, v in book]
    out = []
    for _ in range(paths):
        eq = 0.0; d = 0
        while d < HORIZON:
            d += 1
            today = days[random.randrange(len(days))]
            if not today:
                continue
            pnl = sum(risk * r for _, r in today)
            if pnl <= -daily:
                break
            eq += pnl
            if eq <= -maxloss:
                break
            if eq >= target:
                out.append(d); break
    if not out:
        return ""
    top = _q(out, .97)
    nb = 30; step = max(1, int(math.ceil(top / nb)))
    bins = [0] * (nb + 1)
    for v in out:
        bins[min(v // step, nb)] += 1
    mx = max(bins)
    bw = (w - pad - 20) / len(bins)
    g = []
    for i, c in enumerate(bins):
        if not c:
            continue
        bh = (h - pad - 26) * c / mx
        g.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="var(--acc)" '
                 'opacity=".75" rx="2"><title>%d-%d days: %d of %d attempts</title></rect>'
                 % (pad + i * bw + 1, h - pad - bh, bw - 2, bh,
                    i * step, (i + 1) * step - 1, c, len(out)))
    med = _q(out, .50)
    x = pad + (med / step) * bw
    g.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%.1f" stroke="var(--pos)" '
             'stroke-width="2" stroke-dasharray="5 4"/>' % (x, 20, x, h - pad))
    g.append('<text x="%.1f" y="15" font-size="12" font-weight="700" fill="var(--pos)" '
             'text-anchor="middle">median %d days</text>' % (x, med))
    for i in range(0, nb + 1, 5):
        g.append('<text x="%.1f" y="%d" font-size="11" fill="currentColor" fill-opacity=".5" '
                 'text-anchor="middle">%d</text>' % (pad + i * bw + bw / 2, h - pad + 18, i * step))
    g.append('<text x="%d" y="%d" font-size="11" fill="currentColor" fill-opacity=".5">'
             'trading days to reach +%g%%</text>' % (pad, h - 6, target))
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img">'
            '<title>Days to pass</title><desc>Distribution of how many trading days an '
            'attempt took to reach the target, median %d.</desc>%s</svg>'
            % (w, h, med, "".join(g)))


def build():
    orbT, nqT, elig = load()
    book = daybook([("ORB", orbT), ("NQ", nqT)], elig)
    active = [(d, v) for d, v in book if v]
    loads = Counter(len(v) for _, v in active)

    mc = simulate(book)
    sweep = [(r, mc if abs(r - RISK) < 1e-9 else simulate(book, risk=r, paths=15000))
             for r in (1.0, 1.5, 2.0, 2.5, 3.0)]
    mlsweep = [(m, mc if abs(m - MAXLOSS) < 1e-9 else simulate(book, maxloss=m, paths=15000))
               for m in (6.0, 8.0, 10.0, 12.0)]

    # --- what the real year did, month and quarter -------------------------
    mo = defaultdict(lambda: defaultdict(float)); cnt = defaultdict(int)
    for d, v in active:
        m = d.strftime("%b")
        for name, r in v:
            mo[m][name] += r
            cnt[m] += 1
    mrows = ""
    for m in FP.MONTHS:
        if m not in mo:
            continue
        o, n = mo[m]["ORB"], mo[m]["NQ"]
        mrows += ('<tr><td><b>%s</b></td><td>%d</td><td>%s</td><td>%s</td><td>%s</td>'
                  '<td>%s</td></tr>'
                  % (m, cnt[m], FP.sgn(o, 2), FP.sgn(n, 2), FP.sgn(o + n, 2),
                     FP.pct(o + n, 1)))
    qrows = ""
    for q, ms in QUARTERS.items():
        have = [m for m in ms if m in mo]
        if not have:
            continue
        o = sum(mo[m]["ORB"] for m in have); n = sum(mo[m]["NQ"] for m in have)
        qrows += ('<tr><td><b>%s</b> <span class="lbn">%s</span></td><td>%d</td><td>%s</td>'
                  '<td>%s</td><td>%s</td><td>%s</td></tr>'
                  % (q, "–".join(have), sum(cnt[m] for m in have),
                     FP.sgn(o, 2), FP.sgn(n, 2), FP.sgn(o + n, 2), FP.pct(o + n, 1)))

    # --- worst sequences ---------------------------------------------------
    srows = ""; orbworst = 0.0
    for name, T in (("ORB Asia", orbT), ("NQ range fade", nqT)):
        rs = runs(T)
        longest = max(rs, key=len) if rs else []
        worst = rs[0] if rs else []
        if name.startswith("ORB"):
            orbworst = sum(t["R"] for t in worst)
        srows += ('<tr><td><b>%s</b></td><td>%d</td><td>%s</td><td>%d</td><td>%s</td>'
                  '<td>%s</td></tr>'
                  % (name, len(longest), FP.sgn(sum(t["R"] for t in longest), 2),
                     len(worst), FP.sgn(sum(t["R"] for t in worst), 2),
                     FP.pct(sum(t["R"] for t in worst), 1)))
    dr = day_runs(book)
    dlong = max(dr, key=len) if dr else []
    dworst = dr[0] if dr else []
    srows += ('<tr class="hi"><td><b>The account</b> <span class="lbn">losing days, '
              'both strategies together</span></td><td>%d</td><td>%s</td><td>%d</td>'
              '<td>%s</td><td>%s</td></tr>'
              % (len(dlong), FP.sgn(sum(x[1] for x in dlong), 2),
                 len(dworst), FP.sgn(sum(x[1] for x in dworst), 2),
                 FP.pct(sum(x[1] for x in dworst), 1)))
    ddR, pk, tr, floor, floor_d = equity_dd(book)

    worstday = min(sum(r for _, r in v) for _, v in active)
    twoday = [(d, sum(r for _, r in v)) for d, v in active if len(v) > 1]
    worst2 = min(twoday, key=lambda x: x[1]) if twoday else (None, 0)

    killrows = "".join('<tr><td><b>%s</b></td><td>%.1f%%</td></tr>' % (k, v)
                       for k, v in sorted(mc["killed"].items(), key=lambda z: -z[1]))
    swrows = "".join(
        '<tr%s><td><b>%.1f%%</b></td><td>%.1f%%</td><td>%d</td><td>%d</td><td>%.1f%%</td>'
        '<td>%.1f%%</td></tr>'
        % (' class="hi"' if abs(r - RISK) < 1e-9 else "", r, s["rate"],
           s["trades"]["p50"], s["days"]["p50"],
           s["killed"].get("daily limit", 0.0), s["killed"].get("maximum loss", 0.0))
        for r, s in sweep)
    mlrows = "".join(
        '<tr%s><td><b>%g%% static</b></td><td>%.1f%%</td><td>%d</td><td>%d</td></tr>'
        % (' class="hi"' if abs(m - MAXLOSS) < 1e-9 else "", m, s["rate"],
           s["trades"]["p50"], s["days"]["p50"])
        for m, s in mlsweep)

    body = TEMPLATE % dict(
        risk=RISK, target=TARGET, daily=DAILY, maxloss=MAXLOSS,
        rate=mc["rate"], paths=PATHS,
        t50=mc["trades"]["p50"], t25=mc["trades"]["p25"], t75=mc["trades"]["p75"],
        d50=mc["days"]["p50"], d10=mc["days"]["p10"], d25=mc["days"]["p25"],
        d75=mc["days"]["p75"], d90=mc["days"]["p90"],
        dd50=mc["dd"]["p50"] , dd90=mc["dd"]["p90"],
        hist=hist_svg(book, RISK, TARGET, DAILY, MAXLOSS),
        killrows=killrows, swrows=swrows, mlrows=mlrows,
        mrows=mrows, qrows=qrows, srows=srows,
        ndays=len(active), d1=loads.get(1, 0), d2=loads.get(2, 0),
        ntrades=len(orbT) + len(nqT),
        worstday=worstday, worstdaypct=FP.pct(worstday, 2),
        worst2=worst2[1], worst2pct=FP.pct(worst2[1], 2),
        worst2d=worst2[0].strftime("%d %B") if worst2[0] else "—",
        ddR=ddR, ddpct=FP.pct(-ddR, 1),
        ddfrom=pk.strftime("%d %b") if pk else "—",
        ddto=tr.strftime("%d %b") if tr else "—",
        orbworstpct=FP.pct(orbworst, 1),
        # trading the whole year from 1 January, equity never dipped below the
        # balance it started with -- so the static limit was never approached
        floortxt=("equity never once dipped below it — running the whole of 2026 from "
                  "1 January, the account was never behind."
                  if floor >= -1e-9 else
                  "the furthest equity ever fell below it was <b>%.1f R</b> — %s on %s."
                  % (floor, FP.pct(floor, 1), floor_d.strftime("%d %B"))),
        floord=floor_d.strftime("%d %B") if floor_d else "—",
        headroom=DAILY - 2 * RISK, risk2=2 * RISK,
    )
    html = page.shell("Passing a 5/10 account — ORB + NQ", "account.html", body,
                      risk=RISK, gallery=False)
    open(os.path.join(REPO, "account.html"), "w").write(html)
    print("wrote account.html  (%.1f%% pass, median %d trades / %d days)"
          % (mc["rate"], mc["trades"]["p50"], mc["days"]["p50"]))


TEMPLATE = """
<header>
<h1>Passing a 5 / 10 account</h1>
<p class="lede">A different rule set to the one the other pages model: <b>%(daily)g%% daily</b>,
<b>%(maxloss)g%% maximum loss</b>, <b>+%(target)g%% target</b>, at <b>%(risk)g%% a trade</b>.
Two strategies, one in the Asia session and one in New York, so at most two trades a day —
%(risk2)g%% if both lose, with %(headroom)g%% of headroom against the daily limit. Everything
below is resampled from the %(ndays)d days those two really produced in 2026.</p>
</header>

<section id="result">
<h2><span class="num">01</span>Does it pass, and how fast</h2>
<p class="sub">%(paths)d attempts, resampling whole days so the daily limit applies to the day.</p>
<div class="kpi">
<div class="card"><div class="l">Pass rate</div><div class="v pos">%(rate).1f%%</div><div class="t">of %(paths)d attempts</div></div>
<div class="card"><div class="l">Trades to pass</div><div class="v">%(t50)d</div><div class="t">middle half %(t25)d–%(t75)d</div></div>
<div class="card"><div class="l">Days to pass</div><div class="v">%(d50)d</div><div class="t">middle half %(d25)d–%(d75)d</div></div>
<div class="card"><div class="l">Fastest tenth</div><div class="v">%(d10)d days</div><div class="t">slowest tenth %(d90)d+</div></div>
<div class="card"><div class="l">Drawdown on the way</div><div class="v neg">%(dd50).1f%%</div><div class="t">nine in ten under %(dd90).1f%%</div></div>
<div class="card"><div class="l">Worst single day</div><div class="v neg">%(worstday)+.2f R</div><div class="t">%(worstdaypct)s — inside the %(daily)g%% limit</div></div>
</div>
<figure><div class="fig">%(hist)s</div>
<figcaption>How long an attempt takes. The tail matters more than the median: half of all
passes land in the middle band, but the slowest tenth take %(d90)d days or more.</figcaption></figure>
</section>

<section id="kill">
<h2><span class="num">02</span>What ends the attempts that fail</h2>
<div class="scroll"><table>
<tr><th>Cause</th><th>Share of all attempts</th></tr>
%(killrows)s
</table></div>
<p class="note">Two trades at %(risk)g%% cannot breach a %(daily)g%% daily limit — the worst
possible day is %(risk2)g%%, leaving %(headroom)g%% of room. The daily limit is not what kills
this account; the %(maxloss)g%% maximum loss is, and it takes a run of losing <b>days</b> rather
than a run of losing trades.</p>
</section>

<section id="worst">
<h2><span class="num">03</span>The worst sequences that actually happened</h2>
<p class="sub">A pooled losing run across two strategies is not a thing you sit through. These
are each strategy's own run, and then the account's run of losing days.</p>
<div class="scroll"><table>
<tr><th></th><th>Longest run</th><th>Cost</th><th>Worst run</th><th>Cost</th><th>At %(risk)g%%</th></tr>
%(srows)s
</table></div>
<p>On the real 2026 sequence the account's worst <b>peak-to-trough</b> was %(ddR).1f R —
%(ddpct)s at %(risk)g%% — from %(ddfrom)s to %(ddto)s. That is the number a <i>trailing</i>
limit measures, and it would have breached this one.</p>
<p>But a <b>static</b> %(maxloss)g%% limit is measured from the starting balance, and %(floortxt)s
The distinction is the whole difference between passing and not: once the account is up, a
giveback that looks alarming is nowhere near the line.</p>
<p class="note">Both single-strategy runs above cost more than %(maxloss)g%% at %(risk)g%%
— the ORB's worst six in a row is %(orbworstpct)s. Those runs did not end an attempt because
they did not arrive at the start of one. A losing run in the first fortnight is fatal; the same
run after +8%% is survivable. That is what the pass rate is really measuring.</p>
<div class="kpi">
<div class="card"><div class="l">Days with a trade</div><div class="v">%(ndays)d</div><div class="t">%(ntrades)d trades in total</div></div>
<div class="card"><div class="l">One strategy fired</div><div class="v">%(d1)d</div><div class="t">days</div></div>
<div class="card"><div class="l">Both fired</div><div class="v">%(d2)d</div><div class="t">days — the only ones that can double a loss</div></div>
<div class="card"><div class="l">Worst two-trade day</div><div class="v neg">%(worst2)+.2f R</div><div class="t">%(worst2pct)s on %(worst2d)s</div></div>
</div>
</section>

<section id="months">
<h2><span class="num">04</span>Month by month</h2>
<div class="scroll"><table>
<tr><th>Month</th><th>Trades</th><th>ORB</th><th>NQ</th><th>Total</th><th>At %(risk)g%%</th></tr>
%(mrows)s
</table></div>
</section>

<section id="quarters">
<h2><span class="num">05</span>By quarter</h2>
<p class="sub">A quarter is roughly one attempt's length, so this is the closest thing in the
real data to "would that attempt have passed".</p>
<div class="scroll"><table>
<tr><th>Quarter</th><th>Trades</th><th>ORB</th><th>NQ</th><th>Total</th><th>At %(risk)g%%</th></tr>
%(qrows)s
</table></div>
</section>

<section id="sweep">
<h2><span class="num">06</span>If you change the risk, or the firm</h2>
<div class="scroll"><table>
<tr><th>Risk per trade</th><th>Pass rate</th><th>Trades</th><th>Days</th><th>Died on the daily limit</th><th>Died on the maximum loss</th></tr>
%(swrows)s
</table></div>
<p class="sub">The same strategies against a different maximum loss, at %(risk)g%% a trade.</p>
<div class="scroll"><table>
<tr><th>Maximum loss</th><th>Pass rate</th><th>Trades</th><th>Days</th></tr>
%(mlrows)s
</table></div>
</section>

<section id="limits">
<h2><span class="num">07</span>What this does not show</h2>
<ul>
<li><b>2026 only.</b> Every path is resampled from the same %(ndays)d days. A simulation cannot
invent a market the data never contained, so the pass rate is what these two strategies would do
in a year like this one, not in any year.</li>
<li><b>Resampling breaks the order.</b> Real losing runs cluster more than independent draws do,
which makes the drawdown figures optimistic. The measured runs in section 03 are the honest
counterweight — those are what actually happened, in sequence.</li>
<li><b>The NQ fade's parameters were chosen on this data</b>, and its expectancy on 2024 and 2025
is about a fifth of what it shows here. Halve its contribution and the pass rate falls.</li>
<li><b>No slippage beyond the spread, no missed fills, no news halt, no execution error.</b>
Every trade is taken.</li>
<li><b>One account.</b> Running several at once correlates them perfectly — the same trades on
each — so it multiplies the outcome rather than diversifying it.</li>
</ul>
</section>
"""

if __name__ == "__main__":
    build()
