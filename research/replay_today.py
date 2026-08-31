"""Add the sessions the Strategy Tester refuses to test, and say so in writing.

MetaTrader's history server only serves bars up to the last COMPLETED trading
day, so the tester silently clamps its range and the current session is simply
absent. This replays those days from raw bars and appends them to the trade
CSVs, recording which rows are replayed in replayed.json and regenerating the
provenance note in DATA.md from it.

Nothing here is sticky: the tester rewrites the CSVs from scratch on every run,
so a replayed row disappears the moment the tester can see that day for real.

    python3 replay_today.py 2026.08.28      tester covered through this date
"""
import csv, json, math, os, sys, datetime as dt
from mt5paths import COMMON as D
from sim_offline import load_bars, session, broker_offset

HERE  = os.path.dirname(os.path.abspath(__file__))
LOT   = 0.01     # broker lot step
CSIZE = 100      # XAUUSD contract size, ounces per lot
RISK  = 0.02     # InpRiskPercent
FILES = {"live_cp0.50.csv": True, "live_cp0.00.csv": False}   # half filter on/off

MARK_A = "<!-- replayed:start -->"
MARK_B = "<!-- replayed:end -->"


def friction(rows):
    """How much worse than the ideal a stop really lands, in R.

    Commission and slippage mean a full stop reads about -1.03 rather than
    -1.00. Measuring it from the tested rows keeps a replayed one carrying the
    same drag instead of a clean number that flatters the total.
    """
    full = [abs(float(r["R"])) for r in rows
            if r["exit"].strip().startswith("sl") and abs(float(r["R"])) > 0.9]
    return (sum(full) / len(full) - 1.0) if full else 0.0


def lots_for(balance, risk_pts):
    """Nearest lot step, matching the EA's rounding."""
    raw = balance * RISK / (risk_pts * CSIZE)
    steps = raw / LOT
    n = round(steps)
    if n < 1 or (steps and n / steps > 1.25):
        n = math.floor(steps)
    return max(n, 1) * LOT


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    # The tester reports its range as an EXCLUSIVE end: "to 2026.08.31 00:00"
    # means it stopped at the start of the 31st, so the 31st itself is exactly
    # the day it did not test.
    untested_from = dt.datetime.strptime(sys.argv[1], "%Y.%m.%d").date()
    bars = load_bars()
    replayed = []

    for fname, half in FILES.items():
        path = os.path.join(D, fname)
        rows = list(csv.DictReader(open(path)))
        hdr = list(rows[0].keys())
        drag = friction(rows)

        last = rows[-1]
        balance = float(last["risk_money"]) / RISK + float(last["profit_money"])
        have = set(r["entry_time"][:10] for r in rows)

        for d in sorted(x for x in bars if x >= untested_from):
            if d.strftime("%Y.%m.%d") in have:
                continue
            r = session(bars, d, half_filter=half)
            if isinstance(r, str):
                if half:
                    print("  %s  no trade: %s" % (d, r))
                continue

            risk_pts = abs(r["entry"] - r["sl"])
            lots = lots_for(balance, risk_pts)
            risk_money = lots * CSIZE * risk_pts
            # Apply the measured drag against the trade, never in its favour.
            R = r["R"] - drag
            profit = R * risk_money
            # entry_time is written in broker time, like every tested row
            t = dt.datetime.combine(d, dt.time()) + dt.timedelta(
                minutes=broker_offset(d) * 60 + r["entry_min"])

            row = {
                "entry_time":       t.strftime("%Y.%m.%d %H:%M"),
                "range_pts":        "%d" % round(r["rng"] / 0.01),
                "spread_pts":       "50",
                "mins_after_range": "%d" % (r["entry_min"] - 15),
                "dir":              "buy" if r["buy"] else "sell",
                "entry":            "%.2f" % r["entry"],
                "sl":               "%.2f" % r["sl"],
                "risk_money":       "%.2f" % risk_money,
                "profit_money":     "%.2f" % profit,
                "R":                "%.3f" % R,
                "exit":             "%s %.2f" % (r["exit"], r["price"])
                                    if r["exit"] != "hold" else "",
                "close_pos":        "%.3f" % r["close_pos"],
            }
            rows.append({k: row.get(k, "") for k in hdr})
            balance += profit
            if half:
                replayed.append(dict(entry_time=row["entry_time"], date=d.isoformat(),
                                     dir=row["dir"], R=round(R, 3),
                                     exit=r["exit"], held=r["held"]))
                print("  %s  %-4s %+.3f R  %s after %d min  <- replayed"
                      % (d, row["dir"], R, r["exit"], r["held"]))

        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, hdr)
            w.writeheader()
            w.writerows(rows)

    json.dump(dict(tested_before=untested_from.isoformat(), rows=replayed),
              open(os.path.join(HERE, "replayed.json"), "w"), indent=1)
    write_note(replayed)
    print("%d replayed row(s)" % len(replayed))


def write_note(replayed):
    """Keep DATA.md's provenance note in step with what was actually replayed."""
    p = os.path.join(HERE, "DATA.md")
    md = open(p).read()
    if MARK_A not in md or MARK_B not in md:
        print("  (no %s markers in DATA.md, note not written)" % MARK_A)
        return
    if replayed:
        body = [
            "",
            "## Rows that are not from the Strategy Tester",
            "",
            "**%s replayed from the bars, not tested.** Worth knowing before you"
            % (", ".join("`%s`" % r["entry_time"] for r in replayed)),
            "diff anything against your own run.",
            "",
            "MetaTrader's history server only serves bars up to the last *completed*",
            "trading day. Today's bars exist in a live chart, because the terminal builds",
            "them from the tick stream, but they never reach the history base the Strategy",
            "Tester reads, so the tester quietly clamps its date range instead of failing.",
            "",
            "`sim_offline.py` replays the EA over raw bars to cover those days. Run it with",
            "no arguments and it checks itself against the tester across 2026: same days,",
            "same directions, agreeing within 0.10 R on the large majority. Where it differs",
            "is intrabar ordering, since an M1 bar cannot say whether its high or its low",
            "came first.",
            "",
            "R carries the mean drag measured from every full stop-out in the tested rows,",
            "so a replayed row is no cleaner than a real one.",
            "",
            "These rows vanish on the next tester run that can see the day.",
            "",
        ]
    else:
        body = ["", "Every row in both trade files came from the Strategy Tester.", ""]
    md = md[:md.index(MARK_A) + len(MARK_A)] + "\n".join(body) + md[md.index(MARK_B):]
    open(p, "w").write(md)


if __name__ == "__main__":
    main()
