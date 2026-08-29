"""Same comparison, but reporting the TIME tail, not just the median.

Scaling risk with the remaining buffer makes the 10% floor asymptotically hard
to reach -- risk shrinks as you approach it. That is genuinely how a static
floor works, but it converts a fail into a very long grind, and a median hides
that completely.
"""
import csv, random, statistics
from mt5paths import COMMON as D

R = [float(r['R']) for r in csv.DictReader(open(f"{D}/live_cp0.50.csv"))
     if r['entry_time'][:4] == '2026']
WORST = abs(min(R)); DAILY_CAP = 5.0 / WORST
FLOOR, PATHS = -10.0, 20000
FREQ = len(R) / 132.0
MINRISK = 0.25          # smallest position worth placing, percent of the start

def run(target, risk_fn, seed, cap_trades=3000):
    rng = random.Random(seed)
    res = []                      # trades used, or None for a fail
    for _ in range(PATHS):
        eq, n = 0.0, 0
        while n < cap_trades:
            n += 1
            eq += max(MINRISK, min(DAILY_CAP, risk_fn(eq))) * rng.choice(R)
            if eq <= FLOOR: res.append(None); break
            if eq >= target and n >= 3: res.append(n); break
        else:
            res.append(None)      # ran out of trades: not a pass
    return res

def pct(v, q): return statistics.quantiles(v, n=100)[q-1] if len(v) > 1 else v[0]

def evaluate(label, risk_fn):
    a = run(8.0, risk_fn, 1); b = run(5.0, risk_fn, 2)
    pa = [x for x in a if x]; pb = [x for x in b if x]
    both = (100.0*len(pa)/len(a)) * (100.0*len(pb)/len(b)) / 100.0
    tot = [x+y for x, y in zip(pa, pb[:len(pa)])] or [0]
    d = lambda t: int(round(t / FREQ))
    return (label, both, d(statistics.median(tot)), d(pct(tot, 90)), d(pct(tot, 99)))

FLAT = [("flat %.2f%%" % r, (lambda rr: (lambda eq: rr))(r))
        for r in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5)]
BUF  = [("buffer/%d" % k, (lambda kk: (lambda eq: (eq - FLOOR) / kk))(k))
        for k in (3, 4, 5, 6)]

print("  setting          pass    days: median   90th   99th")
for lab, fn in FLAT + BUF:
    l, p, m, p90, p99 = evaluate(lab, fn)
    print("  %-14s  %5.1f%%          %4d  %5d  %5d" % (l, p, m, p90, p99))

print("\nHOW SENSITIVE IS THE BUFFER RESULT TO THE SMALLEST POSITION YOU CAN PLACE?")
for mr in (0.10, 0.25, 0.50, 1.00):
    globals()['MINRISK'] = mr
    l, p, m, p90, p99 = evaluate("buffer/5", lambda eq: (eq - FLOOR) / 5)
    print("  min risk %.2f%%  ->  pass %5.1f%%   median %d days, 99th %d days" % (mr, p, m, p99))
