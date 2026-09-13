"""The two range-fade strategies: run them, draw every trade, write the JSON.

Both fade a level that a session already established. Only the source of the
level and the session they are traded in differ, so they share one engine:

    gold   the level is YESTERDAY'S high and low, faded in the Asia session
    nq     the level is today's 00:00-13:30 UTC high and low, faded in New York

Stop and target are both fractions of that range, read off a fib drawn on it:
a stop at -0.10 sits a tenth of the range beyond the level, a target at 0.35
sits a third of the way back across it. Reward-to-risk therefore falls out of
where the entry candle closed rather than being fixed.

    python3 research/fades.py gold
    python3 research/fades.py nq
    python3 research/fades.py all

Writes research/data/fade_<name>.json and the charts in trades-<name>/.
The report pages are built separately by fade_page.py.
"""
import os, sys, csv, json, collections, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "lib"))
from mt5paths import COMMON as D
from sim_offline import broker_offset
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

YEAR = 2026
TF = 5                      # the confirmation candle
INK = "#141310"; MUT = "#8a837a"; POS = "#12694a"; NEG = "#a8352a"
ACC = "#8a6d3b"; GRID = "#ece7dd"

SPECS = {
    "gold": dict(
        name="gold", symbol="XAUUSD", bars="bars_XAUUSD.csv",
        # yesterday's whole session is the reference, so the level is a day old
        # before it is ever traded.
        rangesrc="prevday", rangetxt="yesterday's",
        window=(0, 8 * 60), windowtxt="00:00–08:00 UTC, the Asia session",
        days=(1, 2, 3, 4), daystxt="Tuesday to Friday",
        sl=0.10, tp=0.35,
        spread=0.50, comm=0.10, pt=0.01, digits=2,
        title="Fading yesterday's high and low",
        sub="gold, Asia session",
        # Monday is out: its levels come from Friday, three days stale.
        why="Monday is excluded — its levels come from Friday, with a "
            "weekend in between.",
    ),
    "nq": dict(
        name="nq", symbol="US100.cash", bars="bars_US100.cash.csv",
        rangesrc=(0, 13 * 60 + 30), rangetxt="the pre-New-York",
        window=(13 * 60 + 30, 20 * 60), windowtxt="13:30–20:00 UTC, the New York session",
        days=(0, 1, 3, 4), daystxt="Monday, Tuesday, Thursday and Friday",
        sl=0.25, tp=0.50,
        spread=1.5, comm=0.0, pt=1.0, digits=1,
        title="Fading the pre-New-York range",
        sub="US100, New York session",
        # Wednesday was the only losing day of the week, negative in six months
        # of nine. Every other day removed makes the result worse.
        why="Wednesday is excluded — the only losing day of the week, "
            "negative in six months of nine.",
    ),
}


def load(spec):
    days = collections.defaultdict(list)
    p = os.path.join(D, spec["bars"])
    if not os.path.exists(p):
        sys.exit("no bar file at %s -- dump it first" % p)
    for r in csv.DictReader(open(p)):
        t = dt.datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
        days[t.date()].append((t.hour * 60 + t.minute, float(r["open"]), float(r["high"]),
                               float(r["low"]), float(r["close"])))
    # A short day is a holiday or a feed gap; its high and low are not the day's
    # range and would hand the session a level built from nothing.
    return {d: sorted(v) for d, v in days.items() if len(v) >= 600}


def to_m5(bars):
    """M1 into M5 aligned to the clock, because the rule reads an M5 CLOSE."""
    o = {}
    for mi, op, h, l, c in bars:
        k = mi // 5
        if k in o:
            p = o[k]; o[k] = (p[0], p[1], max(p[2], h), min(p[3], l), c)
        else:
            o[k] = (k * 5, op, h, l, c)
    return [o[k] for k in sorted(o)]


def find(spec, days, ds):
    """Every trade the spec produces, in order. One per level per day, and only
    the first of the day is kept -- a second signal is a second commitment on a
    day that has already gone against you."""
    SP = spec["spread"]; CM = spec["comm"]
    out = []
    for i in range(1, len(ds)):
        c = ds[i]
        if c.year != YEAR or c.weekday() not in spec["days"]:
            continue
        b = days[c]; off = broker_offset(c) * 60
        if spec["rangesrc"] == "prevday":
            p = ds[i - 1]
            hi = max(x[2] for x in days[p]); lo = min(x[3] for x in days[p])
            rsrc = (days[p][0][0], days[p][-1][0])
        else:
            rs, re = spec["rangesrc"]
            seg = [x for x in b if rs + off <= x[0] < re + off]
            if len(seg) < 300:
                continue
            hi = max(x[2] for x in seg); lo = min(x[3] for x in seg)
            rsrc = (rs + off, re + off)
        rg = hi - lo
        if rg <= 0:
            continue
        w = (spec["window"][0] + off, spec["window"][1] + off)
        cands = [x for x in to_m5(b) if w[0] <= x[0] < w[1]]
        bymin = {x[0]: k for k, x in enumerate(b)}
        got = []
        for lvl, sgn in ((lo, -1), (hi, 1)):
            d_ = -sgn                       # break below -> buy, above -> sell
            state = 0; sig = None; ext = None; sweep = None
            for ms, o, h, l, cl in cands:
                if state == 0:
                    if (h >= lvl if sgn > 0 else l <= lvl):
                        state = 1; ext = h if sgn > 0 else l; sweep = ms
                    continue
                ext = max(ext, h) if sgn > 0 else min(ext, l)
                if (cl < lvl) if sgn > 0 else (cl > lvl):
                    sig = (ms + TF - 1, cl); break
            if sig is None:
                continue
            em, close = sig
            if em not in bymin or sweep not in bymin:
                continue
            ei = bymin[em]
            entry = close + (SP if d_ > 0 else 0.0)
            sl = lvl + sgn * spec["sl"] * rg
            risk = abs(entry - sl)
            if risk <= SP:
                continue
            tp = lvl - sgn * spec["tp"] * rg
            if (tp - entry) * d_ <= 0:
                continue                    # target already behind the entry
            rr = (tp - entry) * d_ / risk
            R = None; xi = None; xp = None; kind = "eod"
            for j in range(ei + 1, len(b)):
                mi, o, h, l, cl2 = b[j]
                if mi >= w[1]:
                    break
                adv = l if d_ > 0 else h + SP
                fav = h if d_ > 0 else l
                if (adv - sl) * d_ <= 0:
                    R = -1.0; xi = j; xp = sl; kind = "sl"; break
                if (fav - tp) * d_ >= 0:
                    R = rr; xi = j; xp = tp; kind = "tp"; break
            if R is None:
                last = [k for k, x in enumerate(b) if x[0] < w[1]]
                if not last:
                    continue
                xi = last[-1]; xp = b[xi][4]
                R = (xp - entry) * d_ / risk
            got.append(dict(date=c, buy=d_ > 0, lvl=lvl, hi=hi, lo=lo, rg=rg,
                            entry=entry, sl=sl, tp=tp, risk=risk, rr=rr,
                            R=R - CM / risk, kind=kind, ei=ei, xi=xi, xp=xp,
                            sweep_i=bymin[sweep], extreme=ext,
                            depth=abs(entry - lvl), rsrc=rsrc))
        if got:
            out.append(min(got, key=lambda g: g["ei"]))
    out.sort(key=lambda t: (t["date"], t["ei"]))
    return out


def place(levels, span):
    """Nudge labels apart so two levels a few points apart do not overprint."""
    gap = span * 0.055
    items = sorted(levels, key=lambda z: z[0])
    ys = [it[0] for it in items]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < gap:
            ys[i] = ys[i - 1] + gap
    return [(items[i][0], ys[i]) + items[i][1:] for i in range(len(items))]


def draw(spec, t, days, n, outdir):
    b = days[t["date"]]
    a = max(0, t["sweep_i"] - 12); z = min(len(b) - 1, t["xi"] + 8)
    m5 = to_m5(b[a:z + 1])
    if len(m5) < 4:
        return None
    x0 = m5[0][0]
    dg = spec["digits"]; PT = spec["pt"]
    mid = (t["hi"] + t["lo"]) / 2.0
    fig, ax = plt.subplots(figsize=(11.8, 5.7), dpi=105)
    keep = [t["sl"], t["tp"], t["entry"], mid, t["lvl"]]
    lo_ = min([x[3] for x in m5] + keep); hi_ = max([x[2] for x in m5] + keep)
    span = hi_ - lo_
    xr = m5[-1][0] - x0
    step = next(s for s in (15, 30, 60, 120, 180, 240) if xr / s <= 14) if xr > 210 else 15
    for mi, o, h, l, cl in m5:
        x = mi - x0 + 2.5; up = cl >= o; col = POS if up else NEG
        ax.plot([x, x], [l, h], color=col, lw=1.0, solid_capstyle="butt", zorder=2)
        ax.add_patch(Rectangle((x - 1.7, min(o, cl)), 3.4, max(abs(cl - o), span * .0025),
                     facecolor=col if up else "white", edgecolor=col, lw=1.0, zorder=3))
    ax.axvspan(b[t["sweep_i"]][0] - x0, b[t["ei"]][0] - x0 + 5, color=ACC, alpha=.07, zorder=0)
    side = "low" if t["buy"] else "high"
    lv = [(t["entry"], ACC, "entry  %.*f" % (dg, t["entry"]), True),
          (t["sl"], NEG, "stop  %.*f   −1R  (fib −%.2f)" % (dg, t["sl"], spec["sl"]), True),
          (t["tp"], POS, "target  %.*f   +%.2fR  (fib %.2f)" % (dg, t["tp"], t["rr"], spec["tp"]), True),
          (mid, MUT, "mid of the range  %.*f" % (dg, mid), False),
          (t["lvl"], INK, "%s %s  %.*f" % (spec["rangetxt"], side, dg, t["lvl"]), False)]
    far = t["hi"] if t["buy"] else t["lo"]
    if lo_ - span * .04 <= far <= hi_ + span * .04:
        lv.append((far, MUT, "%s %s  %.*f"
                   % (spec["rangetxt"], "high" if t["buy"] else "low", dg, far), False))
    pad = span * .11
    ax.set_ylim(lo_ - pad, hi_ + pad)
    for y0, ytxt, col, lab, bold in place(lv, span):
        ax.plot([-4, xr + 4.5], [y0, y0], color=col, ls="--" if bold else "-",
                lw=1.15 if bold else 1.0, alpha=.85, zorder=1)
        ax.plot([xr + 5.5, xr + xr * 0.035 + 7], [y0, ytxt], color=col, lw=.7, alpha=.45, zorder=1)
        ax.text(xr + xr * 0.045 + 8, ytxt, lab, color=col, fontsize=9, va="center",
                weight="bold" if bold else "normal")
    ax.plot([b[t["ei"]][0] - x0 + 2.5], [t["entry"]], marker="^" if t["buy"] else "v", ms=12,
            color=ACC, zorder=6, markeredgecolor="white", markeredgewidth=.9)
    win = t["R"] > 0
    ax.plot([b[t["xi"]][0] - x0 + 2.5], [t["xp"]], marker="X", ms=11, color=POS if win else NEG,
            zorder=6, markeredgecolor="white", markeredgewidth=.9)
    ax.set_title("%s   ·   %s   ·   %s   —   %s   %+.2f R"
                 % (t["date"].strftime("%d %B %Y"), t["date"].strftime("%A"),
                    "LONG" if t["buy"] else "SHORT", "WIN" if win else "LOSS", t["R"]),
                 fontsize=14, color=POS if win else NEG, weight="bold", loc="left", pad=16)
    ax.text(0, 1.02, "M5 candles   ·   swept the %s   ·   closed %.0f pts back inside   ·   "
            "range %.0f pts   ·   risk %.0f pts   ·   %.2f R target   ·   held %d min   ·   trade %d"
            % (side, t["depth"] / PT, t["rg"] / PT, t["risk"] / PT, t["rr"],
               b[t["xi"]][0] - b[t["ei"]][0], n),
            transform=ax.transAxes, fontsize=9, color=MUT)
    off = broker_offset(t["date"]) * 60
    tick = list(range(0, xr + 1, step))
    ax.set_xticks(tick)
    ax.set_xticklabels(["%02d:%02d" % (((x0 + m - off) // 60) % 24, (x0 + m) % 60) for m in tick],
                       fontsize=9)
    ax.set_xlabel("UTC", fontsize=9, color=MUT)
    ax.set_ylabel(spec["symbol"], fontsize=9, color=MUT)
    ax.set_xlim(-5, xr + xr * 0.30 + 12)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=.6, zorder=0)
    fn = "%s_%s_%s.png" % (t["date"].isoformat(), "long" if t["buy"] else "short",
                           "win" if win else "loss")
    fig.savefig(os.path.join(outdir, fn), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return fn


def build(key):
    spec = SPECS[key]
    outdir = os.path.join(REPO, "trades-" + spec["name"])
    os.makedirs(outdir, exist_ok=True)
    days = load(spec); ds = sorted(days)
    trades = find(spec, days, ds)
    print("%s: %d trades in %d" % (key, len(trades), YEAR))
    # Any chart left over from a previous run whose trade has since changed
    # would ship as a picture of a trade that no longer exists.
    keep = set()
    for i, t in enumerate(trades, 1):
        t["n"] = i
        t["file"] = draw(spec, t, days, i, outdir)
        if t["file"]:
            keep.add(t["file"])
    trades = [t for t in trades if t["file"]]
    for f in os.listdir(outdir):
        if f.endswith(".png") and f not in keep:
            os.remove(os.path.join(outdir, f)); print("  removed orphan %s" % f)
    elig = [d for d in ds if d.year == YEAR and d.weekday() in spec["days"]]
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    out = dict(
        spec={k: v for k, v in spec.items() if k != "rangesrc"},
        rangesrc=("prevday" if spec["rangesrc"] == "prevday" else list(spec["rangesrc"])),
        days=[d.isoformat() for d in elig],
        trades=[dict(date=t["date"].isoformat(), buy=t["buy"], R=round(t["R"], 4),
                     rr=round(t["rr"], 3), risk=t["risk"], rg=t["rg"], depth=t["depth"],
                     kind=t["kind"], file=t["file"], n=t["n"],
                     hold=days[t["date"]][t["xi"]][0] - days[t["date"]][t["ei"]][0])
                for t in trades])
    p = os.path.join(HERE, "data", "fade_%s.json" % spec["name"])
    json.dump(out, open(p, "w"), indent=1)
    print("  %d charts in trades-%s/, json at %s"
          % (len(trades), spec["name"], os.path.relpath(p, REPO)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k in (SPECS if which == "all" else [which]):
        build(k)
