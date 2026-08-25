"""Can more risk raise the pass rate on a FundingPips 2-step Standard account?

Rules modelled:
  phase 1 target +8%, phase 2 target +5%, each phase starting from 0
  max total loss 10% -- STATIC, measured from the starting balance
  max daily loss  5% -- one trade a day, so one trade must never cost 5%
  minimum 3 trading days

The static floor is the interesting part: at +5% profit you are 15% above it,
not 10%. So risking a fixed slice of the REMAINING buffer lets size grow as the
cushion grows, which flat sizing cannot do.
"""
import csv, random, statistics
from mt5paths import COMMON as D

R = [float(r['R']) for r in csv.DictReader(open(f"{D}/live_cp0.50.csv"))
     if r['entry_time'][:4] == '2026']
WORST = abs(min(R))            # -1.09 R, the worst single trade seen
DAILY_CAP = 5.0 / WORST        # risk above this can breach the daily limit
FLOOR, PATHS = -10.0, 40000
FREQ = len(R) / 132.0          # trades per eligible session

def phase(target, risk_fn, paths=PATHS, seed=0):
    """risk_fn(equity) -> percent of the starting balance to risk on this trade."""
    rng = random.Random(seed)
    ok, days = 0, []
    for _ in range(paths):
        eq, n = 0.0, 0
        while n < 3000:
            n += 1
            r = risk_fn(eq)
            eq += r * rng.choice(R)
            if eq <= FLOOR:
                break
            if eq >= target and n >= 3:
                ok += 1; days.append(n); break
    return 100.0 * ok / paths, (statistics.median(days) if days else 0)

def evaluate(label, risk_fn, start_risk):
    p1, n1 = phase(8.0, risk_fn, seed=1)
    p2, n2 = phase(5.0, risk_fn, seed=2)
    both = p1 * p2 / 100.0
    trades = n1 + n2
    return (label, start_risk, p1, p2, both, trades, int(round(trades / FREQ)))

rows = []
# --- flat risk ---
r = 1.0
while r <= 5.01:
    rows.append(evaluate("flat %.2f%%" % r, (lambda rr: (lambda eq: rr))(r), r))
    r += 0.25

# --- risk a fixed slice of the remaining buffer ---
def buffer_fn(k):
    def f(eq):
        return max(0.25, min(DAILY_CAP, (eq - FLOOR) / k))
    return f
bufrows = [evaluate("buffer/%d" % k, buffer_fn(k), (0 - FLOOR) / k) for k in range(3, 11)]

print("FLAT RISK")
print("  setting        start   ph1     ph2     BOTH     trades  days")
for lab, s, p1, p2, b, t, d in rows:
    print("  %-13s %5.2f%%  %5.1f%%  %5.1f%%  %5.1f%%   %4d   %4d" % (lab, s, p1, p2, b, t, d))
best = max(rows, key=lambda x: x[4])
print("  best pass rate: %s at %.1f%%" % (best[0], best[4]))

print("\nRISK A SLICE OF THE REMAINING BUFFER  (daily cap %.2f%%)" % DAILY_CAP)
print("  setting        start   ph1     ph2     BOTH     trades  days")
for lab, s, p1, p2, b, t, d in bufrows:
    print("  %-13s %5.2f%%  %5.1f%%  %5.1f%%  %5.1f%%   %4d   %4d" % (lab, s, p1, p2, b, t, d))

print("\nSAME SPEED, WHICH IS SAFER?")
for target_days in (11, 13, 16, 22):
    cand = [x for x in rows + bufrows if abs(x[6] - target_days) <= 1]
    if not cand: continue
    top = max(cand, key=lambda x: x[4])
    print("  ~%2d days: best is %-13s at %.1f%% pass  (of %d options)"
          % (target_days, top[0], top[4], len(cand)))
