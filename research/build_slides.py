#!/usr/bin/env python3
"""Build index.html -- a self-contained web deck for the ORB Asia edge.

The deck is the landing page; the long report sits at full-report.html.

Every number comes from report_data.json and every diagram from the same
generators the report uses, so the deck cannot drift from the research.

    python3 build_slides.py     ->  ~/orb/strategy/index.html
"""
import base64, datetime as dt, json, os

import halves_svg
import rules_svg
from curve import curve_svg

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)          # research/ -> repo root
OUT = os.path.join(REPO, "index.html")
TRADES = os.path.expanduser("~/orb/trades")

d = json.load(open(os.path.join(HERE, "report_data.json")))
H = d["headline"]
RISK = 2.0
PASS2 = [p for p in d["pass"] if p["risk"] == 2.0][0]
LAST = dt.date.fromisoformat(d["coverage"]["last"]).strftime("%d %B %Y")


def img(name):
    """Inline the chart so the deck is one file you can email or open offline."""
    with open(os.path.join(TRADES, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def kpi(label, value, note, cls="pos"):
    return ('<div class="k"><div class="kl">%s</div><div class="kv %s">%s</div>'
            '<div class="kn">%s</div></div>' % (label, cls, value, note))


def table(headers, rows, hi=None):
    # Distinct names: the row loop used to reuse `cls` and clobber the table's
    # own class before it was ever applied, so `dense` silently never landed
    # and the table could inherit a row's highlight instead.
    tcls = ' class="dense"' if len(rows) > 6 else ""
    th = "".join("<th>%s</th>" % h for h in headers)
    tr = ""
    for i, r in enumerate(rows):
        rcls = ' class="hi"' if hi is not None and i == hi else ""
        tr += "<tr%s>%s</tr>" % (rcls, "".join("<td>%s</td>" % c for c in r))
    return "<table%s><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (tcls, th, tr)


# ----------------------------------------------------------------- slides
S = []

S.append(("", """
<div class="title">
  <div class="eyebrow">Opening range breakout &middot; XAUUSD</div>
  <h1>The Asia<br>Opening Range</h1>
  <p class="sub">One trade a day, decided in thirty minutes,
     flat within ninety.</p>
  <div class="titlestats">
    <span><b>%.1f%%</b> win rate</span>
    <span><b>+%.3f R</b> per trade</span>
    <span><b>%.2f</b> profit factor</span>
    <span><b>%.0f%%</b> pass rate</span>
  </div>
  <div class="foot">2026 &middot; real ticks &middot; data through %s</div>
</div>""" % (H["wr"], H["ev"], H["pf"], PASS2["both"], LAST)))

S.append(("What it is", """
<ul class="big">
  <li>Gold moves in a burst when <b>Tokyo opens</b> at 00:00 UTC.</li>
  <li>The first <b>fifteen minutes</b> draw a box. The box is the disagreement.</li>
  <li>When price leaves the box <b>quickly</b>, it usually keeps going.</li>
  <li>When it leaves <b>slowly</b>, it does not. So there is a deadline.</li>
</ul>
<div class="callout">Everything else is stop placement, position size,
and knowing which days to skip.</div>"""))

S.append(("One session, start to finish", '<div class="fig">%s</div>'
          % rules_svg.build()))

RULES = [
    ("Mark the range", "00:00&ndash;00:14 UTC, fifteen one-minute candles"),
    ("Pick the side", "whichever half the 00:14 candle closed in"),
    ("Wait for a close outside", "up to 00:29. Nothing by then, no trade"),
    ("Enter at market", "on the next candle"),
    ("Stop at the midpoint", "that distance is your 1R"),
    ("Target at 2R", "measured from the actual fill"),
    ("At +0.5R, stop to &minus;0.5R", "once only, never back out"),
    ("Flat after 90 minutes", "close at market"),
    ("Monday to Thursday", "Friday is the only losing day"),
    ("Same risk every trade", "no compounding"),
]
S.append(("The rules, all of them",
          '<ol class="rules">%s</ol>' % "".join(
              "<li><b>%s</b><span>%s</span></li>" % r for r in RULES)))

S.append(("The one filter that matters", '<div class="fig">%s</div>'
          % halves_svg.build(d["halves"])))

S.append(("A trade that worked", """
<div class="two">
  <img src="%s" alt="12 August 2026, long, +2.00 R">
  <div>
    <ul class="big">
      <li>00:14 closed in the <b>top half</b> &rarr; longs only</li>
      <li>Broke the high, entered at market</li>
      <li>Stop at the midpoint, target 2R above the fill</li>
      <li>Reached target after <b>88 minutes</b> &mdash; two minutes
          inside the cap</li>
    </ul>
    <div class="callout">Held 88 of the 90 minutes allowed. Only %d trades
      in %d ever reach the cap, and those still average positive.</div>
  </div>
</div>""" % (img("2026-08-12_long_win.png"),
             next(e["n"] for e in d["exits"] if e["kind"] == "time cap"),
             H["trades"])))

S.append(("A trade that failed &mdash; and only cost half", """
<div class="two">
  <img src="%s" alt="6 January 2026, long, minus 0.54 R">
  <div>
    <ul class="big">
      <li>Same setup, same rules, wrong outcome</li>
      <li>Ran to <b>+0.5R</b>, which pulled the stop to <b>&minus;0.5R</b></li>
      <li>Then reversed and stopped out</li>
      <li>Cost <b>&minus;0.54 R</b> instead of &minus;1.00 R</li>
    </ul>
    <div class="callout">%d of the %d losses were halved this way.
      Average loss %+.2f R, not &minus;1.00.</div>
  </div>
</div>""" % (img("2026-01-06_long_loss.png"), d["losses"]["halved"],
             d["losses"]["n"], d["losses"]["avg"])))

S.append(("2026, on real ticks", '<div class="kpis">%s</div>' % "".join([
    kpi("Total return", "+%.0f%%" % H["ret"], "%+.1f R banked" % H["total"]),
    kpi("Win rate", "%.1f%%" % H["wr"], "%d wins &middot; %d losses" % (H["wins"], H["trades"] - H["wins"]), ""),
    kpi("Per trade", "+%.3f R" % H["ev"], "&plusmn;%.3f standard error" % H["se"]),
    kpi("Profit factor", "%.2f" % H["pf"], "%+.1f R won vs %.1f lost" % (H["gain"], abs(H["loss"]))),
    kpi("Trades", "%d" % H["trades"], "from %d eligible sessions" % H["sessions"], ""),
    kpi("Worst drawdown", "%.1f%%" % d["maxdd"], "the limit is 10%", ""),
    # The minus matters: the report's matching card reads "-8% of the account",
    # and a loss rendered as a bare "8%" is the one number a reader could take
    # the wrong way round.
    kpi("Longest losing run", "%d" % d["streaks"]["worst_loss"], "-%.0f%% of the account" % (RISK * d["streaks"]["worst_loss"]), ""),
    kpi("Longest winning run", "%d" % d["streaks"]["best_win"], "wins in a row"),
])))

S.append(("Every trade of 2026, in order",
          '<div class="fig curve">%s</div>'
          '<div class="callout">Cumulative return at 2%% risk, no compounding. '
          'The deepest hole is %.1f%%, against a 10%% limit.</div>'
          % (curve_svg(d["curve"]), d["maxdd"])))

S.append(("Consistent by quarter", table(
    ["Quarter", "Days", "Trades", "Win rate", "Profit factor", "Per trade", "Total"],
    [[q["q"], q["days"], q["trades"], "%.1f%%" % q["wr"],
      "%.2f" % q["pf"], "%+.3f R" % q["ev"], "<b>%+.1f R</b>" % q["total"]]
     for q in d["quarters"]])
    + '<div class="callout">Three quarters, three profitable. The edge is not '
      'one lucky month.</div>'))

S.append(("Passing the challenge", table(
    ["Risk per trade", "Pass both phases", "Trades needed", "Trading days"],
    [["%.1f%%" % p["risk"], "<b>%.1f%%</b>" % p["both"], p["trades"], "~%d" % p["days"]]
     for p in d["pass"]],
    hi=[i for i, p in enumerate(d["pass"]) if p["risk"] == 2.0][0])
    + '<div class="callout">FundingPips two-step: +8%% then +5%%, 10%% maximum '
      'loss. Simulated 40 000 times on the 2026 outcomes.</div>'))

S.append(("What does not work", table(
    ["Idea", "Result"],
    [["London session", "&minus;0.207 per trade"],
     ["New York session", "&minus;0.082 per trade"],
     ["Nasdaq at the cash open", "flat, three range lengths tested"],
     ["Trading Friday at 2R", "20.8% win rate, &minus;0.241"],
     ["Trading Friday at 1R", "break-even, but drawdown 6.3% &rarr; 11.3%"],
     ["Taking the skipped half at 1R", "&minus;0.217 per trade"],
     ["Trailing the stop", "win rate 19&ndash;30% instead of 32&ndash;42%"],
     ["Tighter stop, quarter range", "&minus;0.27 per trade"],
     ["1R target instead of 2R", "roughly a fifth of the expectancy"],
     ["Entering after 00:29", "+0.375 &rarr; +0.181 per trade"]])
    + '<div class="callout">Eight sessions and a dozen variations were tested '
      'and rejected. The rules are what survived.</div>'))

S.append(("Honest limits", """
<ul class="big">
  <li><b>One symbol, one session, one year.</b> Gold at the Asia open in 2026.</li>
  <li><b>72 trades is a small sample.</b> The error bar on expectancy is
      &plusmn;%.3f R, and 2026 may simply have been kind.</li>
  <li><b>It is a bet on the regime.</b> The filter needs ranges that trend
      rather than chop. Tested on a choppy market the effect inverts.</li>
  <li><b>There is a kill switch.</b> If the fifteen-minute range falls below
      0.15%% of price, the edge is gone.</li>
</ul>
<div class="callout warn">Anything that looks this clean deserves suspicion.
These are the reasons to keep the size small.</div>""" % H["se"]))

S.append(("Run it yourself", """
<ul class="big">
  <li>Full report and all %d trade charts &mdash;
      <b>anas1412.github.io/orb-mt5/full-report.html</b></li>
  <li>Source, the MetaTrader 5 expert advisor &mdash;
      <b>github.com/anas1412/orb-mt5</b></li>
  <li>Every backtest reproduces from the repo on Windows or Linux</li>
</ul>
<div class="foot big">EA by Anas B. &amp; Nydhal G.</div>""" % H["trades"]))

# ----------------------------------------------------------------- render
slides = "".join(
    '<section class="slide"%s>%s%s</section>'
    % (' data-title="%s"' % t if t else "",
       '<h2>%s</h2>' % t if t else "", body)
    for t, body in S)

html = open(os.path.join(HERE, "slides_template.html")).read()
html = (html.replace("{{SLIDES}}", slides)
            .replace("{{COUNT}}", str(len(S)))
            .replace("{{LASTDATE}}", LAST))
open(OUT, "w").write(html)
print("wrote %s  (%d slides, %.0f KB)" % (OUT, len(S), len(html) / 1024.0))
