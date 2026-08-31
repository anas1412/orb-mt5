"""Rewrite the README's numbers from report_data.json.

Every figure on the README, the report, the deck and the client page comes from
that one file. Hand-editing is how the exits table once summed to +44.3 R under
a +47.1 R headline.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
d = json.load(open(os.path.join(HERE, "report_data.json")))
H = d["headline"]
r = open(os.path.join(REPO, "README.md")).read()
before = r

last = d["coverage"]["last"] if isinstance(d.get("coverage"), dict) else None
if last:
    import datetime as dt
    day = dt.date.fromisoformat(last)
    r = re.sub(r"XAUUSD, real ticks, 2026 \(2 Jan – [^)]+\)",
               "XAUUSD, real ticks, 2026 (2 Jan – %s)" % day.strftime("%-d %b"), r)

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

pas = "| Risk per trade | Pass both phases | Trades needed | Trading days |\n|---|---|---|---|\n"
for p in d["pass"]:
    f = (lambda s: "**%s**" % s) if p["risk"] == 2.0 else (lambda s: s)
    pas += "| %s | %s | %s | %s |\n" % (f("%.1f%%" % p["risk"]), f("%.1f%%" % p["both"]),
                                        f(str(p["trades"])), f("~%d" % p["days"]))
r = re.sub(r"\| Risk per trade \| Pass both phases \| Trades needed \| Trading days \|\n"
           r"\|---\|---\|---\|---\|\n(\|.*\n)+", pas, r)

name = {"target": "Target hit (+2R)", "stop": "Stopped out", "time cap": "90-minute cap"}
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
        "**%.1f%%** | **%d**" % ([p for p in d["pass"] if p["risk"] == 2.0][0]["both"],
                                 [p for p in d["pass"] if p["risk"] == 2.0][0]["trades"])]
missing = [w for w in want if w not in r]
if missing:
    sys.exit("README did not take these -- a regex stopped matching:\n  " +
             "\n  ".join(missing))
print("README %s: %d trades, %.1f%%, %+.1f R, PF %.2f"
      % ("updated" if r != before else "already current",
         H["trades"], H["wr"], H["total"], H["pf"]))
