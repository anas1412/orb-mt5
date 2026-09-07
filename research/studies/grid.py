import json, statistics, math, random
from sweep import load, setups, evaluate, stats

random.seed(101)
ss = setups(load())
SL = [0.25, 0.375, 0.5, 0.625, 0.75, 1.0]
RR = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
MOVES = [(0.0, 0.0)] + [(a, t) for a in (0.25, 0.5, 0.75, 1.0) for t in (-0.5, -0.25, 0.0)]

rows = []
for sl in SL:
    for rr in RR:
        for ma, mt in MOVES:
            res = evaluate(ss, sl, rr, ma, mt)
            st = stats(res)
            if not st: continue
            per = {}
            for y in (2024, 2025, 2026):
                sy = stats([r for r in res if r[0] == y])
                per[y] = sy["ev"] if sy else None
            rows.append(dict(sl=sl, rr=rr, move_at=ma, move_to=mt, n=st["n"],
                             ev=st["ev"], wr=st["wr"], sd=st["sd"], se=st["se"],
                             y24=per[2024], y25=per[2025], y26=per[2026],
                             worst=min(v for v in per.values() if v is not None)))
json.dump(rows, open("grid.json", "w"))
print("evaluated %d combinations on %d setups\n" % (len(rows), len(ss)))

def table(title, sel, key="ev", n=12):
    print(title)
    print("   SL     RR    move        n     EV      WR     2024    2025    2026   worst-yr")
    for r in sorted(sel, key=lambda r: -r[key])[:n]:
        mv = "off" if r["move_at"] == 0 else "%.2f->%+.2f" % (r["move_at"], r["move_to"])
        print("  %.3f  %.2f  %-11s %3d  %+.3f  %4.1f%%  %+.3f  %+.3f  %+.3f   %+.3f"
              % (r["sl"], r["rr"], mv, r["n"], r["ev"], r["wr"], r["y24"], r["y25"], r["y26"], r["worst"]))
    print()

table("=== best by overall EV ===", rows)
table("=== best by WORST year (robustness) ===", rows, key="worst")
