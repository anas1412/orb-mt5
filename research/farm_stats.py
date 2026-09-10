"""What MetaTrader actually did, read back from the run records.

    python3 research/farm_stats.py            # every record, newest last
    python3 research/farm_stats.py --last 10
    python3 research/farm_stats.py --id asia-gold-010839-s1   # one, in full

A container run is a black box unless it says what it did, and the two failures
that look like success are the tester silently clamping the date range and a
terminal that never started. Both are flagged here rather than left in a log.
"""
import os, sys, json, glob, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")

def load():
    out = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        try:
            with open(p) as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            pass
    return sorted(out, key=lambda r: r.get("started") or 0)

def hhmm(sec):
    if sec is None: return "  -  "
    return "%d:%02d" % (sec // 60, sec % 60) if sec >= 60 else "%4ds" % sec

def clamped(r):
    """The tester reports an EXCLUSIVE end, so asked_to one day past it is normal."""
    a, t = r.get("asked_to"), r.get("tester_reported_to")
    if not a or not t: return False
    try:
        ad = dt.datetime.strptime(a, "%Y.%m.%d").date()
        td = dt.datetime.strptime(t, "%Y.%m.%d").date()
    except ValueError:
        return False
    return (ad - td).days > 1

def warnings(r):
    w = []
    if r.get("status") != "ok": w.append("FAILED")
    if clamped(r): w.append("dates clamped to %s" % r["tester_reported_to"])
    tr = r.get("trades") or {}
    if r.get("status") == "ok" and not tr.get("cp050"): w.append("no trades")
    bad = [l for l in (r.get("journal") or [])
           if any(k in l for k in ("authorization on", "not specified", "no history"))]
    if bad: w.append(bad[0][-70:])
    return w

def table(rows):
    print("%-30s %-16s %-9s %-14s %6s %6s %6s %7s"
          % ("id", "spec", "symbol", "account", "test", "build", "total", "trades"))
    print("-" * 104)
    for r in rows:
        tr = (r.get("trades") or {}).get("cp050")
        mark = "" if r.get("status") == "ok" else "  <<"
        print("%-30s %-16s %-9s %-14s %6s %6s %6s %7s%s"
              % (r["id"][:30], (r.get("spec") or "")[:16], (r.get("symbol") or "")[:9],
                 (r.get("account") or "")[:14], hhmm(r.get("seconds_tester")),
                 hhmm(r.get("seconds_build")), hhmm(r.get("seconds")),
                 "-" if tr is None else tr, mark))
    print()
    flagged = [(r, warnings(r)) for r in rows]
    flagged = [(r, w) for r, w in flagged if w]
    if not flagged:
        print("no warnings: every run finished, covered the window it asked for, and found trades")
        return
    print("warnings")
    for r, w in flagged:
        for line in w:
            print("  %-30s %s" % (r["id"][:30], line))

def detail(r):
    print(json.dumps(r, indent=1))

def main():
    a = sys.argv[1:]
    rows = load()
    if not rows:
        print("no run records yet -- research/runs/ is empty"); return
    if "--id" in a:
        want = a[a.index("--id") + 1]
        for r in rows:
            if r["id"] == want: detail(r); return
        sys.exit("no record with id %s" % want)
    if "--last" in a:
        rows = rows[-int(a[a.index("--last") + 1]):]
    table(rows)

if __name__ == "__main__":
    main()
