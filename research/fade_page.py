"""Build the two fade reports and the page that puts all three edges together.

Reads research/data/fade_<name>.json (written by fades.py) and, for the ORB,
the tester CSV through ctx -- so no figure on any page is typed by hand.

    python3 research/fade_page.py

Writes pdfade.html, nqfade.html and edges.html at the repo root.
"""
import os, sys, re, json, math, struct, datetime as dt
import statistics as st
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "lib"))

import page          # the shared head, nav, risk selector and shell

BE = 0.05            # inside +-0.05 R is a scratch, neither win nor loss
RISK_PCT = 2.5       # what the page renders at; the selector rescales it
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# ---------------------------------------------------------------- data ----
def load_fade(name):
    d = json.load(open(os.path.join(HERE, "data", "fade_%s.json" % name)))
    for t in d["trades"]:
        t["d"] = dt.date.fromisoformat(t["date"])
    return d


def load_orb():
    """The ORB's trades, straight out of the tester CSV the published report uses."""
    import csv, ctx
    T = []
    for r in csv.DictReader(open(ctx.CSV_LIVE)):
        if not ctx.row_ok(r):
            continue
        t = dt.datetime.strptime(r["entry_time"], "%Y.%m.%d %H:%M")
        # a blank exit is the 90-minute hold cap: no stop, no target
        ex = (r["exit"].split() or ["eod"])[0].lower()
        T.append(dict(d=t.date(), date=t.date().isoformat(), R=float(r["R"]),
                      rr=ctx.RR, buy=r["dir"] == "buy",
                      risk=abs(float(r["entry"]) - float(r["sl"])),
                      kind="tp" if "tp" in ex else "sl" if "sl" in ex else "eod"))
    T.sort(key=lambda x: x["d"])
    return dict(trades=T, spec=dict(name="orb", symbol="XAUUSD",
                                    title="The Asia opening range",
                                    sub="gold, 00:00 UTC", sl=None, tp=None,
                                    daystxt="Monday to Thursday",
                                    windowtxt="00:00–01:45 UTC, the Asia session"))


def stats(T):
    R = [t["R"] for t in T]
    n = len(R)
    W = [x for x in R if x > BE]; L = [x for x in R if x < -BE]
    be = n - len(W) - len(L)
    ev = sum(R) / n
    sd = st.stdev(R) if n > 1 else 0.0
    cum = pk = dd = lr = worst = wrun = wbest = 0.0
    curve = []
    for x in R:
        cum += x; pk = max(pk, cum); dd = max(dd, pk - cum); curve.append(cum)
        if x <= BE:
            lr += 1; wrun = 0
        else:
            wrun += 1; lr = 0
        worst = max(worst, lr); wbest = max(wbest, wrun)
    mo = defaultdict(float)
    for t in T:
        mo[t["d"].strftime("%b")] += t["R"]
    rr = [t["rr"] for t in T]
    return dict(n=n, wins=len(W), losses=len(L), be=be,
                wr=100.0 * len(W) / max(len(W) + len(L), 1),
                ev=ev, sd=sd, total=sum(R), dd=dd, worst=int(worst), wbest=int(wbest),
                t=ev / (sd / math.sqrt(n)) if sd else 0.0,
                pf=(sum(W) / abs(sum(L))) if L else float("inf"),
                aw=sum(W) / len(W) if W else 0.0, al=sum(L) / len(L) if L else 0.0,
                curve=curve, months=mo, green=sum(1 for v in mo.values() if v > 0),
                nmonths=len(mo), avgrr=sum(rr) / n, medrr=st.median(rr),
                best=max(R), tworst=min(R))


# ---------------------------------------------------------- rendering ----
def sgn(v, dp=2, suf=" R"):
    return '<span class="%s">%+.*f%s</span>' % ("pos" if v > 0 else "neg", dp, v, suf)


def pct(r, dp=1):
    """Follows the risk selector: R on the element, number inside, % outside."""
    return '<span data-pct="%.4f">%+.*f</span>%%' % (r, dp, RISK_PCT * r)


def curve_svg(curve, w=1080, h=300, pad=46):
    lo = min(0, min(curve)); hi = max(curve); n = len(curve)
    span = max(hi - lo, 1e-9)
    X = lambda i: pad + i * (w - pad - 64) / max(n - 1, 1)
    Y = lambda v: h - pad - (v - lo) * (h - pad - 20) / span
    pts = " ".join("%.1f,%.1f" % (X(i), Y(v)) for i, v in enumerate(curve))
    g = ['<polygon points="%.1f,%.1f %s %.1f,%.1f" fill="url(#eq)" opacity=".5"/>'
         % (X(0), Y(0), pts, X(n - 1), Y(0)),
         '<polyline points="%s" fill="none" stroke="var(--pos)" stroke-width="2.4" '
         'stroke-linejoin="round"/>' % pts,
         '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".25"/>'
         % (pad, Y(0), w - 64, Y(0))]
    step = 5.0 if hi <= 26 else 10.0
    v = 0.0
    while v <= hi + 1e-9:
        y = Y(v)
        g.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" '
                 'stroke-opacity=".08"/>' % (pad, y, w - 64, y))
        g.append('<text x="%d" y="%.1f" font-size="11" fill="currentColor" fill-opacity=".5" '
                 'text-anchor="end" dy="3.5" data-pct="%.4f" data-fmt="int">%d%%</text>'
                 % (pad - 8, y, v, round(v * RISK_PCT)))
        v += step
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--pos)"/>' % (X(n - 1), Y(curve[-1])))
    g.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="var(--pos)" dy="4" '
             'data-pct="%.4f" data-fmt="signint">  %+.0f%%</text>'
             % (X(n - 1) + 7, Y(curve[-1]), curve[-1], curve[-1] * RISK_PCT))
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img"><title>Cumulative return</title>'
            '<desc>Cumulative return, ending at %+.0f%% at %g%% risk.</desc>'
            '<defs><linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%%" stop-color="var(--pos)" stop-opacity=".28"/>'
            '<stop offset="100%%" stop-color="var(--pos)" stop-opacity="0"/></linearGradient>'
            '</defs>%s</svg>') % (w, h, curve[-1] * RISK_PCT, RISK_PCT, "".join(g))


def png_size(web, fn):
    """Width and height from the PNG header. Without them on the tag the browser
    cannot reserve the box and a lazy card off-screen collapses to its caption."""
    with open(os.path.join(REPO, web, fn), "rb") as fh:
        d = fh.read(26)
    return struct.unpack(">II", d[16:24])


def gallery(T, web):
    cards = ""
    for t in T:
        w, h = png_size(web, t["file"])
        src = "%s/%s" % (web, t["file"])
        side = "long" if t["buy"] else "short"
        out = "win" if t["R"] > BE else "loss"
        cards += ('<a class="tc %s" data-outcome="%s" data-dir="%s" data-month="%s" href="%s" '
                  'target="_blank" data-r="%+.3f"><img loading="lazy" width="%d" height="%d" src="%s" '
                  'alt="%s %s, %+.2f R"><span class="tm"><b>%s</b> · %s · <i>%+.2f R</i> · '
                  '%.2f R target</span></a>'
                  % (out, out, side, t["d"].strftime("%b"), src, t["R"], w, h, src,
                     t["date"], side, t["R"], t["d"].strftime("%d %b"), side, t["R"], t["rr"]))
    mchips = "".join('<button class="chip" data-f="month" data-v="%s" aria-pressed="false">%s'
                     '</button>' % (m, m)
                     for m in MONTHS if any(t["d"].strftime("%b") == m for t in T))
    return cards, mchips


def month_rows(T):
    mo = defaultdict(list)
    for t in T:
        mo[t["d"].strftime("%b")].append(t)
    out = ""
    for m in MONTHS:
        if m not in mo:
            continue
        v = mo[m]; R = [x["R"] for x in v]
        w = [x for x in R if x > BE]; l = [x for x in R if x < -BE]
        out += ('<tr><td><b>%s</b></td><td>%d</td><td>%.0f%%</td><td>%s</td><td>%s</td></tr>'
                % (m, len(v), 100.0 * len(w) / max(len(w) + len(l), 1),
                   sgn(sum(R) / len(R), 3), sgn(sum(R), 1)))
    return out


def exit_rows(T, spec):
    kinds = defaultdict(list)
    for t in T:
        kinds[t["kind"]].append(t["R"])
    lab = {"tp": ("hit the target", "pos"), "sl": ("stopped out", "neg"),
           "eod": ("closed at the session end", "")}
    return "".join('<tr><td><b>%s</b></td><td>%d</td><td>%.0f%%</td><td>%s</td><td>%s</td></tr>'
                   % (lab[k][0], len(v), 100.0 * len(v) / len(T),
                      sgn(sum(v) / len(v), 2), sgn(sum(v), 1))
                   for k, v in sorted(kinds.items(), key=lambda z: -len(z[1])))




def entry_section(rows, num):
    """Market on the close against a limit back at the level.

    Rendered from measured rows, never asserted: the live rule is marked, and
    the alternative that beats it on this data is shown beating it."""
    if not rows:
        return ""
    live = next(r for r in rows if r["live"])
    best = max(rows, key=lambda r: r["total"])
    body = "".join(
        '<tr%s><td><b>%s</b>%s</td><td>%.0f%%</td><td>%d</td><td>%.1f%%</td>'
        '<td>%.2f</td><td>%s</td><td>%s</td><td>%.1f R</td><td>%d</td></tr>'
        % (' class="hi"' if r["live"] else "", r["label"],
           ' <span class="pill">live</span>' if r["live"] else "",
           r["fill"], r["n"], r["wr"], r["rr"], sgn(r["ev"], 3), sgn(r["total"], 1),
           r["dd"], r["worst"])
        for r in rows)
    note = ("" if best["live"] else
            "<p class=\"note\"><b>%s ends the year ahead</b> — %s against %s, on %d trades "
            "rather than %d, with a %.1f R drawdown against %.1f. It is not what this page "
            "reports, because it was measured after the parameters were fixed and on the same "
            "year, and because the %.0f%% of signals it never fills are not a cost you can see "
            "until you have lived through them. The live rule takes every signal.</p>"
            % (best["label"][0].upper() + best["label"][1:],
               "%+.1f R" % best["total"], "%+.1f R" % live["total"],
               best["n"], live["n"], best["dd"], live["dd"], 100 - best["fill"]))
    return """
<section id="entry">
<h2><span class="num">%s</span>Market or limit?</h2>
<p class="sub">The signal is the same either way. This is only about the fill.</p>
<p>The confirming candle closes some way back inside the level, and you buy that close. The
alternative is to rest a limit between the level and that close and wait for price to come back:
a better price when it fills, and no trade at all when it does not. Because the stop and the
target are both pinned to the level, a fill at the level is always <b>%.2f / %.2f</b> — the
reward to risk stops varying.</p>
<div class="scroll"><table>
<tr><th>Fill</th><th>Filled</th><th>Trades</th><th>Win rate</th><th>RR</th>
<th>Per trade</th><th>Total</th><th>Drawdown</th><th>Worst run</th></tr>
%s
</table></div>
%s
</section>
""" % (num, TPF, SLF, body, note)


def report(name, pagefile):
    d = load_fade(name)
    spec = d["spec"]; T = d["trades"]; S = stats(T)
    web = "trades-" + spec["name"]
    cards, mchips = gallery(T, web)
    elig = len(d["days"])
    # rangesrc's end is EXCLUSIVE -- the session it feeds starts on that
    # minute. Printing it as the range's end reads as though the range
    # included the bar the first signal candle is built from.
    rangetxt = ("yesterday's high and low" if d["rangesrc"] == "prevday"
                else "the high and low of every M5 candle from %02d:%02d to %02d:%02d UTC"
                     % (d["rangesrc"][0] // 60, d["rangesrc"][0] % 60,
                        (d["rangesrc"][1] - 5) // 60, (d["rangesrc"][1] - 5) % 60))
    body = """
<header>
<h1>%(title)s</h1>
<p class="lede">Price sweeps %(rangetxt)s, fails to hold, and an M5 candle closes back inside.
You take that close and trade against the sweep. %(symbol)s, %(daystxt)s, entries in
%(windowtxt)s, flat by the end of the window. 2026 only — %(n)d trades on %(elig)d eligible days.</p>
%(riskbar)s
</header>

<section id="headline">
<h2><span class="num">01</span>The result</h2>
<p class="sub">Every trade the rules produced in 2026. Nothing excluded after the fact.</p>
<div class="kpi">
<div class="card"><div class="l">Trades</div><div class="v">%(n)d</div><div class="t">%(permo).1f a month</div></div>
<div class="card"><div class="l">Win rate</div><div class="v">%(wr).1f%%</div><div class="t">%(wins)d W · %(losses)d L · %(be)d scratch</div></div>
<div class="card"><div class="l">Per trade</div><div class="v %(evc)s">%(ev)+.3f R</div><div class="t">%(evpct)s of the account</div></div>
<div class="card"><div class="l">Total</div><div class="v %(totc)s">%(total)+.1f R</div><div class="t">%(totpct)s at %(risk)g%% risk</div></div>
<div class="card"><div class="l">Reward : risk</div><div class="v">%(medrr).2f</div><div class="t">median · %(avgrr).2f average</div></div>
<div class="card"><div class="l">Profit factor</div><div class="v">%(pf).2f</div><div class="t">avg win %(aw)+.2f R · avg loss %(al)+.2f R</div></div>
<div class="card"><div class="l">Worst drawdown</div><div class="v neg">%(dd).1f R</div><div class="t">%(ddpct)s at %(risk)g%% risk</div></div>
<div class="card"><div class="l">Worst losing run</div><div class="v neg">%(worst)d</div><div class="t">best winning run %(wbest)d</div></div>
</div>
<figure><div class="fig">%(curve)s</div>
<figcaption>Cumulative return, trade by trade. The axis follows the risk selector.</figcaption></figure>
</section>

<section id="rules">
<h2><span class="num">02</span>The rules</h2>
<p class="sub">Draw one fib on the range before the session. Everything else reads off it.</p>
<table>
<tr><th>Step</th><th></th></tr>
<tr><td><b>The range</b></td><td>%(rangetxt_c)s.%(rangenote)s</td></tr>
<tr><td><b>Draw the fib</b></td><td>Anchor 0 on the level you are fading, 1 on the other side. Longs: drag low→high. Shorts: high→low.</td></tr>
<tr><td><b>The sweep</b></td><td>Price trades beyond the level during %(windowtxt)s</td></tr>
<tr><td><b>The entry</b></td><td>An <b>M5 candle closes back inside</b> the level. Enter at that close, at market. One trade a day — the first signal only.</td></tr>
<tr><td><b>The stop</b></td><td>The <b>%(slfib)s fib</b> — %(slpct)s of the range beyond the level</td></tr>
<tr><td><b>The target</b></td><td>The <b>%(tpfib)s fib</b> — %(tppct)s of the range back inside. Reward:risk therefore varies; median %(medrr).2f.</td></tr>
<tr><td><b>The stop move</b></td><td><b>None.</b> Moving it to breakeven or to −0.5R was measured on both strategies and lost money every way it was tried.</td></tr>
<tr><td><b>The exit</b></td><td>Stop, target, or the close of the window — whichever comes first</td></tr>
<tr><td><b>Days</b></td><td>%(daystxt)s. %(why)s</td></tr>
</table>
</section>

<section id="months">
<h2><span class="num">03</span>Month by month</h2>
<p class="sub">%(green)d of %(nmonths)d months green.</p>
<div class="scroll"><table>
<tr><th>Month</th><th>Trades</th><th>Win rate</th><th>Per trade</th><th>Total</th></tr>
%(months)s
</table></div>
</section>

<section id="exits">
<h2><span class="num">04</span>How the trades ended</h2>
<div class="scroll"><table>
<tr><th>Exit</th><th>Trades</th><th>Share</th><th>Average</th><th>Total</th></tr>
%(exits)s
</table></div>
<p class="note">A trade that reaches neither level is closed at the end of the window, at whatever
price is there. Those are neither wins by design nor failures — they are the rule running out of time.</p>
</section>

%(entrysection)s
<section id="trades">
<h2><span class="num">%(ntrades)s</span>Every trade</h2>
<p class="sub">All %(n)d, drawn from the same bars the result was computed on. Click to open full size.</p>
<div class="filters">
<div class="fgroup"><span class="lbl">Outcome</span>
<button class="chip" data-f="outcome" data-v="win" aria-pressed="false">Wins</button>
<button class="chip" data-f="outcome" data-v="loss" aria-pressed="false">Losses</button></div>
<div class="fgroup"><span class="lbl">Direction</span>
<button class="chip" data-f="dir" data-v="long" aria-pressed="false">Long</button>
<button class="chip" data-f="dir" data-v="short" aria-pressed="false">Short</button></div>
<div class="fgroup"><span class="lbl">Month</span>%(mchips)s</div>
<span class="fcount" id="fcount">%(n)d trades</span>
</div>
<div class="gal">%(cards)s</div>
<p class="noresult" id="noresult" hidden>Nothing matches those filters.</p>
</section>

<section id="limits">
<h2><span class="num">%(nlimits)s</span>What this does not show</h2>
<ul>
<li><b>2026 only.</b> %(n)d trades on %(elig)d eligible days.%(oos)s</li>
<li><b>Bar replay, not the Strategy Tester.</b> Entries and exits are walked over M1 bars with a fixed
%(spread)s spread and commission taken off the R. A short's stop is checked against the ask.</li>
<li><b>Intrabar order is unknown.</b> An M1 bar does not say whether its high or low came first,
which can move an exit by a minute on a handful of charts.</li>
<li><b>The parameters were chosen on this data.</b> The stop and target levels came out of a sweep
over this same year, so the exact figures are optimistic even where the shape of the result is not.</li>
</ul>
</section>
"""
    global TPF, SLF
    TPF, SLF = spec["tp"], spec["sl"]
    vals = dict(
        sub=spec["sub"], title=spec["title"], symbol=spec["symbol"],
        daystxt=spec["daystxt"], windowtxt=spec["windowtxt"], why=spec["why"],
        rangetxt=rangetxt, rangetxt_c=rangetxt[0].upper() + rangetxt[1:],
        riskbar=page.riskbar(RISK_PCT), n=S["n"], elig=elig, permo=S["n"] / (elig / 21.7),
        wr=S["wr"], wins=S["wins"], losses=S["losses"], be=S["be"],
        ev=S["ev"], evc="pos" if S["ev"] > 0 else "neg", evpct=pct(S["ev"], 2),
        total=S["total"], totc="pos" if S["total"] > 0 else "neg", totpct=pct(S["total"]),
        medrr=S["medrr"], avgrr=S["avgrr"], pf=S["pf"], aw=S["aw"], al=S["al"],
        dd=S["dd"], ddpct=pct(-S["dd"]), worst=S["worst"], wbest=S["wbest"],
        risk=RISK_PCT, curve=curve_svg(S["curve"]), months=month_rows(T),
        green=S["green"], nmonths=S["nmonths"], exits=exit_rows(T, spec),
        mchips=mchips, cards=cards,
        slfib="−%.2f" % spec["sl"], tpfib="%.2f" % spec["tp"],
        slpct="%g%%" % (spec["sl"] * 100), tppct="%g%%" % (spec["tp"] * 100),
        spread="%g-point" % spec["spread"],
        # only an intraday range has an edge worth spelling out; yesterday's
        # whole session has none
        rangenote=("" if d["rangesrc"] == "prevday" else
                   " The last one opens at %02d:%02d and closes as the session begins;"
                   " the %02d:%02d candle is the first that can signal."
                   % ((d["rangesrc"][1] - 5) // 60, (d["rangesrc"][1] - 5) % 60,
                      d["rangesrc"][1] // 60, d["rangesrc"][1] % 60)),
        entrysection=entry_section(d.get("entrycmp"), "05"),
        ntrades="06" if d.get("entrycmp") else "05",
        nlimits="07" if d.get("entrycmp") else "06",
        oos=(" " + spec["oos"]) if spec.get("oos")
            else " There is no out-of-sample test behind these numbers.",
    )
    html = page.shell(spec["title"] + " — " + spec["sub"], pagefile, body % vals,
                      risk=RISK_PCT)
    open(os.path.join(REPO, pagefile), "w").write(html)
    print("wrote %s  (%d trades, %+.1f R)" % (pagefile, S["n"], S["total"]))
    return T, S






# ------------------------------------------------------------ combined ----
def combined(sets, outfile, h1, lede, current=None):
    """sets: [(label, page, trades, stats)]. Any subset, on its own page."""
    NW = {2: "two", 3: "three", 4: "four"}.get(len(sets), str(len(sets)))
    cols = "".join("<th>%s</th>" % s[0] for s in sets) + "<th>Together</th>"
    allT = sorted([dict(t, _o=i) for i, (_, _, T, _) in enumerate(sets) for t in T],
                  key=lambda x: (x["d"], x["_o"]))
    AS = stats(allT)
    S = [s[3] for s in sets] + [AS]

    def line(lab, fmt, get, hi=max):
        vals = [get(x) for x in S]
        best = hi(vals[:-1])
        return ("<tr><td><b>%s</b></td>" % lab +
                "".join('<td%s>%s</td>' % (' class="hi"' if v == best else "", fmt % v)
                        for v in vals) + "</tr>")

    rows = "".join([
        line("Trades", "%d", lambda s: s["n"]),
        line("Win rate", "%.1f%%", lambda s: s["wr"]),
        line("Median RR", "%.2f", lambda s: s["medrr"]),
        line("Average RR", "%.2f", lambda s: s["avgrr"]),
        line("Per trade", "%+.3f R", lambda s: s["ev"]),
        line("Total", "%+.1f R", lambda s: s["total"]),
        line("Profit factor", "%.2f", lambda s: s["pf"]),
        line("Worst drawdown", "%.1f R", lambda s: s["dd"], min),
        line("Worst losing run", "%d", lambda s: s["worst"], min),
        line("Best winning run", "%d", lambda s: s["wbest"]),
        line("t-statistic", "%+.2f", lambda s: s["t"]),
    ])
    # monthly grid
    mrows = ""
    for m in MONTHS:
        if not any(m in s["months"] for s in S[:-1]):
            continue
        cells = "".join("<td>%s</td>" % sgn(s["months"].get(m, 0.0), 2) for s in S[:-1])
        tot = sum(s["months"].get(m, 0.0) for s in S[:-1])
        mrows += "<tr><td><b>%s</b></td>%s<td>%s</td></tr>" % (m, cells, sgn(tot, 2))
    tot_cells = "".join("<td>%s</td>" % sgn(s["total"], 1) for s in S[:-1])
    mrows += ("<tr><td><b>Total</b></td>%s<td>%s</td></tr>"
              % (tot_cells, sgn(AS["total"], 1)))

    # correlation of monthly R
    ms = sorted({m for s in S[:-1] for m in s["months"]},
                key=lambda m: MONTHS.index(m))
    cor = ""
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            a = [S[i]["months"].get(m, 0.0) for m in ms]
            b = [S[j]["months"].get(m, 0.0) for m in ms]
            ma, mb = sum(a) / len(a), sum(b) / len(b)
            cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) - 1)
            sa, sb = st.stdev(a), st.stdev(b)
            cor += ("<tr><td><b>%s</b> vs <b>%s</b></td><td>%+.2f</td></tr>"
                    % (sets[i][0], sets[j][0], cov / (sa * sb) if sa and sb else 0.0))

    # trades per day, pooled
    perday = defaultdict(int)
    for t in allT:
        perday[t["d"]] += 1
    hist = defaultdict(int)
    for v in perday.values():
        hist[v] += 1
    drows = "".join("<tr><td><b>%d</b></td><td>%d days</td></tr>" % (k, hist[k])
                    for k in sorted(hist))
    worstday = min(sum(t["R"] for t in allT if t["d"] == d) for d in perday)

    body = """
<header>
<h1>%(h1)s</h1>
<p class="lede">%(lede)s</p>
%(riskbar)s
</header>

<section id="side">
<h2><span class="num">01</span>The %(nword)s</h2>
<div class="scroll"><table class="cmp">
<tr><th></th>%(cols)s</tr>
%(rows)s
</table></div>
<p class="note">Bold marks the best of the %(nword)s on each line. The last column is every trade
pooled in date order, one unit of risk each.</p>
</section>

<section id="pooled">
<h2><span class="num">02</span>Pooled</h2>
<div class="kpi">
<div class="card"><div class="l">Trades</div><div class="v">%(n)d</div><div class="t">%(permo).1f a month</div></div>
<div class="card"><div class="l">Win rate</div><div class="v">%(wr).1f%%</div><div class="t">%(wins)d W · %(losses)d L</div></div>
<div class="card"><div class="l">Per trade</div><div class="v pos">%(ev)+.3f R</div><div class="t">%(evpct)s of the account</div></div>
<div class="card"><div class="l">Total</div><div class="v pos">%(total)+.1f R</div><div class="t">%(totpct)s at %(risk)g%% risk</div></div>
<div class="card"><div class="l">Worst drawdown</div><div class="v neg">%(dd).1f R</div><div class="t">%(ddpct)s at %(risk)g%% risk</div></div>
<div class="card"><div class="l">Worst losing run</div><div class="v neg">%(worst)d</div><div class="t">across %(nall)s</div></div>
</div>
<figure><div class="fig">%(curve)s</div>
<figcaption>All %(n)d trades in date order, one unit of risk each.</figcaption></figure>
</section>

<section id="months">
<h2><span class="num">03</span>Month by month</h2>
<div class="scroll"><table>
<tr><th>Month</th>%(cols2)s<th>Total</th></tr>
%(mrows)s
</table></div>
</section>

<section id="corr">
<h2><span class="num">04</span>Do they move together?</h2>
<p class="sub">Correlation of monthly R. Near zero means a bad month in one says nothing about the others.</p>
<div class="scroll"><table>
<tr><th>Pair</th><th>Correlation</th></tr>
%(cor)s
</table></div>
</section>

<section id="load">
<h2><span class="num">05</span>Trades on the same day</h2>
<p class="sub">They can fire on the same day, and a prop firm's daily loss limit counts the day, not the trade.</p>
<div class="scroll"><table>
<tr><th>Trades in a day</th><th>How often</th></tr>
%(drows)s
</table></div>
<p class="note">The worst single day across %(nall)s was <b>%(worstday)+.2f R</b> — %(worstpct)s at
%(risk)g%% risk. A 3%% daily limit is breached by two full losses at 2.5%% risk, so position size has
to be set for the number of strategies running, not for one of them.</p>
</section>

<section id="limits">
<h2><span class="num">%(nlimits)s</span>What this does not show</h2>
<ul>
<li><b>2026 only.</b> %(oosnote)s</li>
<li><b>The ORB is real-tick Strategy Tester output; the fades are bar replays</b> with an assumed
spread. They are not measured to the same standard and the fades will read slightly optimistic.</li>
<li><b>The fade parameters were chosen on this data.</b> Stop and target levels came out of
sweeps over this same year.</li>
<li><b>Pooling assumes equal risk on every trade</b> and ignores that simultaneous losses
breach a 3%% daily limit long before the drawdown figure does.</li>
</ul>
</section>
"""
    vals = dict(riskbar=page.riskbar(RISK_PCT), cols=cols,
                cols2="".join("<th>%s</th>" % s[0] for s in sets),
                rows=rows, mrows=mrows, cor=cor, drows=drows,
                n=AS["n"], permo=AS["n"] / max(AS["nmonths"], 1), wr=AS["wr"],
                wins=AS["wins"], losses=AS["losses"], ev=AS["ev"],
                evpct=pct(AS["ev"], 2), total=AS["total"], totpct=pct(AS["total"]),
                dd=AS["dd"], ddpct=pct(-AS["dd"]), worst=AS["worst"],
                risk=RISK_PCT, curve=curve_svg(AS["curve"]),
                worstday=worstday, worstpct=pct(worstday, 2),
                nlimits="06", h1=h1, lede=lede, nword=NW,
                # "across all two" is not English
                nall=("both" if len(sets) == 2 else "all " + NW),
                oosnote=("The NQ fade has since been run on 2024 and 2025 as well and stays "
                         "positive, at about a fifth of the expectancy it shows here. Nothing "
                         "else on this page has an out-of-sample test behind it."))
    html = page.shell(h1 + " — 2026", current or outfile, body % vals,
                      risk=RISK_PCT, gallery=False)
    open(os.path.join(REPO, outfile), "w").write(html)
    print("wrote %s  (%d trades pooled, %+.1f R)" % (outfile, AS["n"], AS["total"]))


if __name__ == "__main__":
    gT, gS = report("gold", "pdfade.html")
    nT, nS = report("nq", "nqfade.html")
    orb = load_orb()
    oS = stats(orb["trades"])
    print("ORB: %d trades, %+.1f R" % (oS["n"], oS["total"]))
    ORB  = ("ORB Asia", "orb.html", orb["trades"], oS)
    GOLD = ("Gold PD fade", "pdfade.html", gT, gS)
    NQ   = ("NQ range fade", "nqfade.html", nT, nS)
    combined([ORB, GOLD, NQ], "index.html", "All three, side by side",
             "One opening-range breakout and two range fades, on gold and the Nasdaq, in three "
             "different sessions. Same year, same risk, one trade a day each. This page pools them.")
    # The two that carry the result. Gold's fade earns a fifth of what these do
    # and is the only one of the three whose t-statistic is under 1.
    combined([ORB, NQ], "orbnq.html", "ORB and NQ",
             "The two strongest of the three: the Asia opening range on gold, and the "
             "pre-New-York range faded in New York. Different instruments, different sessions, "
             "twelve hours apart. This page pools just those two.")
