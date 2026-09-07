import statistics
from sweep import load, setups, SPREAD_PTS, POINT, COMM_PER_LOT_SIDE, CONTRACT

ss = [s for s in setups(load()) if s['late'] < 15 and s['date'].year == 2026]

def trace(s, sl_frac=0.5, rr=2.0, move_at=0.5, move_to=-0.5, hold=240):
    """Return (R, minutes_to_exit, reason) with a very long cap."""
    rng = s["hi"] - s["lo"]
    lvl = s["hi"] if s["is_buy"] else s["lo"]
    sl  = lvl - rng*sl_frac if s["is_buy"] else lvl + rng*sl_frac
    e = s["entry"]; risk = abs(e - sl)
    if risk <= 0: return None
    tp = e + rr*risk if s["is_buy"] else e - rr*risk
    sgn = 1 if s["is_buy"] else -1
    moved = False
    cost = (SPREAD_PTS[s['date'].year]*POINT)/risk + 2*COMM_PER_LOT_SIDE/(risk*CONTRACT)
    for k,(h,l,c) in enumerate(s["path"][:hold+1]):
        adverse   = l if s["is_buy"] else h
        favorable = h if s["is_buy"] else l
        if (adverse - sl)*sgn <= 0:
            return ((sl-e)*sgn/risk - cost, k, "stop" if not moved else "moved stop")
        if move_at > 0 and not moved and (favorable-e)*sgn >= move_at*risk:
            moved = True; sl = e + sgn*move_to*risk
            if (adverse - sl)*sgn <= 0:
                return ((sl-e)*sgn/risk - cost, k, "moved stop")
        if (favorable - tp)*sgn >= 0:
            return (rr - cost, k, "target")
        last = c
    return ((last-e)*sgn/risk - cost, hold, "still open")

tr = [t for t in (trace(s) for s in ss) if t]
print("2026, 15-min entry cutoff, %d trades. Left running up to 4 hours.\n" % len(tr))

print("how long trades take to finish on their own:")
buckets=[(0,15),(15,30),(30,45),(45,60),(60,90),(90,120),(120,180),(180,241)]
cum=0
for lo,hi in buckets:
    g=[t for t in tr if lo<=t[1]<hi]
    cum+=len(g)
    if g:
        print("   %3d-%3d min   %3d trades (%4.1f%%)   cumulative %4.1f%%   avg %+.2f R"
              % (lo,hi,len(g),100.0*len(g)/len(tr),100.0*cum/len(tr),sum(x[0] for x in g)/len(g)))
still=[t for t in tr if t[2]=="still open"]
print("   never finished within 4h: %d (%.1f%%)" % (len(still),100.0*len(still)/len(tr)))
print()
print("what each cap actually changes:")
print("   cap    trades cut short   they earn (cut)   they'd earn (left alone)   total EV")
for cap in (45,60,90,120,180,240):
    cut=[t for t in tr if t[1] > cap]
    # value with the cap applied
    vals=[]
    for s,t in zip(ss,tr):
        if t[1] <= cap: vals.append(t[0])
        else:
            r=trace(s,hold=cap)
            vals.append(r[0])
    ev=sum(vals)/len(vals)
    if cut:
        cutvals=[]
        for s,t in zip(ss,tr):
            if t[1] > cap: cutvals.append(trace(s,hold=cap)[0])
        print("   %3d     %3d (%4.1f%%)        %+.3f R          %+.3f R                 %+.3f"
              % (cap,len(cut),100.0*len(cut)/len(tr),sum(cutvals)/len(cutvals),
                 sum(t[0] for t in cut)/len(cut),ev))
    else:
        print("   %3d       0                    -                 -                    %+.3f" % (cap,ev))
