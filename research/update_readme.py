"""Rewrite the README's numbers from report_data.json.

Every figure on the README, the report and the client page comes from that one
file. Hand-editing is how the exits table once summed to +44.3 R under a
+47.1 R headline.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
d = json.load(open(os.path.join(HERE, "data", "report_data.json")))
H = d["headline"]
r = open(os.path.join(REPO, "README.md")).read()
before = r

last = d["coverage"]["last"] if isinstance(d.get("coverage"), dict) else None
if last:
    import datetime as dt
    day = dt.date.fromisoformat(last)
    r = re.sub(r"XAUUSD, real ticks, 2026 \(2 Jan – [^)]+\), [\d.]+% risk per trade\.",
               "XAUUSD, real ticks, 2026 (2 Jan – %s), %g%% risk per trade."
               % (day.strftime("%-d %b"), ctx.RISK), r)

res = ("| | |\n|---|---|\n"
       "| Trades | **%d** from %d eligible sessions |\n"
       "| Win rate | **%.1f%%** — %d wins, %d losses |\n"
       "| Expectancy | **%+.3f R** per trade (±%.3f standard error) |\n"
       "| Profit factor | **%.2f** — won +%.1f R against %.1f R lost |\n"
       "| Total | **%+.1f R** = **%+.0f%%** of the account |\n"
       "| Worst drawdown | **%.1f%%** |\n"
       "| Longest losing run | **%d** |") % (
    H["trades"], H["sessions"], H["wr"], H["wins"], H["trades"] - H["wins"],
    H["ev"], H["se"], H["pf"], H["gain"], H["loss"], H["total"], H["ret"],
    d["maxdd"], d["streaks"]["worst_loss"])
r = re.sub(r"\| \| \|\n\|---\|---\|\n\| Trades \|.*?\| Longest losing run \| \*\*\d+\*\* \|",
           res, r, flags=re.S)

# The report lets the reader pick risk; the README shows the same sweep so both
# tell one story. Rows come from report_data's precomputed simulation, never
# from scaling a pass rate.
SHOW = (1.0, 1.5, 2.0, 2.25, 2.5)
pas = ("| Risk per trade | Pass | Trades | Days | Return | Worst drawdown | Worst run costs |\n"
       "|---|---|---|---|---|---|---|\n")
for s in d["sweep"]:
    if s["risk"] not in SHOW:
        continue
    f = (lambda x: "**%s**" % x) if abs(s["risk"] - ctx.RISK) < 1e-9 else (lambda x: x)
    breaks = " ⚠" if s["run_breaks"] else ""
    pas += "| %s | %s | %s | %s | %s | %s | %s |\n" % (
        f("%g%%" % s["risk"]), f("%.1f%%" % s["pass_pct"]), f(str(s["trades"])),
        f("~%d" % s["days"]), f("%+.0f%%" % s["ret"]), f("%.1f%%" % s["maxdd"]),
        f("%.1f%%%s" % (s["run_cost"], breaks)))
r = re.sub(r"\| Risk per trade \| Pass[^\n]*\|\n\|[-|]+\|\n(\|.*\n)+", pas, r)

name = {"target": "Target hit (+%gR)" % ctx.RR, "stop": "Stopped out",
        "time cap": "%d-minute cap" % ctx.HOLD}
ex = "| Exit | Trades | Total |\n|---|---|---|\n" + "".join(
    "| %s | %d | %+.1f R |\n" % (name[e["kind"]], e["n"], e["total"]) for e in d["exits"])
r = re.sub(r"How the \d+ trades ended:\n\n\| Exit \| Trades \| Total \|\n\|---\|---\|---\|\n(\|.*\n)+",
           "How the %d trades ended:\n\n%s" % (H["trades"], ex), r)

r = re.sub(r"- \*\*\d+ trades is a small sample\.\*\*",
           "- **%d trades is a small sample.**" % H["trades"], r)

open(os.path.join(REPO, "README.md"), "w").write(r)

# "Nothing changed" is ambiguous: the README might already be current, or a
# heading drifted and a regex quietly stopped matching. Check the numbers are
# actually in there instead of trusting that a substitution ran.
want = ["**%d** from %d eligible sessions" % (H["trades"], H["sessions"]),
        "**%.1f%%**" % H["wr"],
        "**%+.3f R**" % H["ev"],
        "**%.2f**" % H["pf"],
        "**%+.1f R**" % H["total"],
        "| %d | %+.1f R |" % (d["exits"][0]["n"], d["exits"][0]["total"]),
        "**%.1f%%**" % next(s["pass_pct"] for s in d["sweep"] if abs(s["risk"] - ctx.RISK) < 1e-9)]
missing = [w for w in want if w not in r]
if missing:
    sys.exit("README did not take these -- a regex stopped matching:\n  " +
             "\n  ".join(missing))
print("README %s: %d trades, %.1f%%, %+.1f R, PF %.2f"
      % ("updated" if r != before else "already current",
         H["trades"], H["wr"], H["total"], H["pf"]))


def refresh_data_md():
    """The counts in DATA.md drift every run unless something owns them."""
    p = os.path.join(HERE, "DATA.md")
    m = open(p).read()
    import csv, datetime as dt
    bars = os.path.join(HERE, "bars_XAUUSD_2024_2026.csv")
    n_bars = sum(1 for _ in open(bars)) - 1
    last = None
    with open(bars) as fh:
        for line in fh: last = line
    last_day = dt.datetime.strptime(last.split(",")[0], "%Y.%m.%d %H:%M").strftime("%-d %b %Y")
    mb = os.path.getsize(bars) / 1e6
    n_sess = sum(1 for _ in open(os.path.join(HERE, "sessions_2024_2026.csv"))) - 1
    live = list(csv.DictReader(open(os.path.join(HERE, "trades_live_config.csv"))))
    allb = list(csv.DictReader(open(os.path.join(HERE, "trades_all_breaks.csv"))))
    n26 = len([r for r in live if r["entry_time"][:4] == "2026"])
    subs = [
        (r"[\d,]+ one-minute bars, 2 Jan 2024 to [^,]+,", "%s one-minute bars, 2 Jan 2024 to %s," % (format(n_bars, ","), last_day)),
        (r"\d+ MB, plain CSV", "%.0f MB, plain CSV" % mb),
        (r"One row per Asia session, \d+ of them", "One row per Asia session, %d of them" % n_sess),
        (r"\d+ eligible\nsessions, \d+ trades, [\d.]+% win rate, [+-][\d.]+ R per trade, [+-][\d.]+ R total",
         "%d eligible\nsessions, %d trades, %.1f%% win rate, %+.3f R per trade, %+.1f R total"
         % (H["sessions"], H["trades"], H["wr"], H["ev"], H["total"])),
        (r"\d+ trades, the configuration actually traded", "%d trades, the configuration actually traded" % len(live)),
        (r"\d+ of these are 2026", "%d of these are 2026" % n26),
        (r"\d+ trades, same configuration", "%d trades, same configuration" % len(allb)),
    ]
    for pat, rep in subs:
        m, k = re.subn(pat, rep, m, count=1)
        if k != 1:
            sys.exit("DATA.md: pattern no longer matches: %s" % pat)
    open(p, "w").write(m)
    print("DATA.md counts: %s bars to %s, %d sessions, %d / %d trades"
          % (format(n_bars, ","), last_day, n_sess, len(live), len(allb)))

refresh_data_md()
