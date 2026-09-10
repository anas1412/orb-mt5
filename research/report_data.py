"""Everything the final report needs, as JSON. Totals everywhere except EV."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import csv, os, json, datetime as dt, statistics, math, random
from collections import Counter
from mt5paths import COMMON as D, bars as barsfile
import ctx
random.seed(31337); RISK=ctx.RISK

# every Mon-Thu session that had a complete range = a tradeable day
bars={}
for row in csv.DictReader(open(barsfile(ctx.SYMBOL))):
    t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
    if not ctx.in_range(t): continue
    bars.setdefault(t.date(),{})[t.hour*60+t.minute]=(
        float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
out_cover=None
alldates=sorted(bars)
sessions=set()
for d,b in bars.items():
    if d.weekday() not in ctx.WEEKDAYS: continue   # the spec's trading days, not Mon-Thu
    st=ctx.session_start(d)
    if len([m for m in range(st,st+ctx.RANGE_MIN) if m in b])>=ctx.RANGE_MIN: sessions.add(d)

rows=[r for r in csv.DictReader(open(ctx.CSV_LIVE)) if ctx.row_ok(r)]
for r in rows:
    r['R']=float(r['R']); r['t']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M")
    r['date']=r['t'].date()
rows.sort(key=lambda r:r['t'])
R=[r['R'] for r in rows]

def pf(v):
    """Gross wins over gross losses. None when there are no losses to divide by:
    a week that never lost has an infinite ratio, which is true but says nothing,
    so the report shows a dash rather than a number that looks meaningful."""
    gain = sum(x for x in v if x > 0)
    loss = -sum(x for x in v if x <= 0)
    if loss <= 0:
        return None
    return round(gain / loss, 2)

def wl_seq(rs):
    """W/L per trade in the order they happened, e.g. L-L-W-W-L.

    Not `seq` -- that name is already a streak list further down, and shadowing
    it turns this into "list is not callable" at the point of use.
    """
    return "-".join("W" if r['R'] > 0 else "L"
                    for r in sorted(rs, key=lambda r: r['t']))

def blk(rs, days):
    if not rs: return None
    v=[r['R'] for r in rs]; w=len([x for x in v if x>0])
    return dict(days=days, trades=len(v), wins=w, losses=len(v)-w,
                wr=round(100.0*w/len(v),1), ev=round(sum(v)/len(v),3),
                total=round(sum(v),1), ret=round(RISK*sum(v),1),
                gain=round(sum(x for x in v if x>0),1),
                loss=round(sum(x for x in v if x<=0),1), pf=pf(v), seq=wl_seq(rs))

out={}
out['headline']=dict(
    trades=len(R), wins=len([x for x in R if x>0]),
    wr=round(100.0*len([x for x in R if x>0])/len(R),1),
    ev=round(sum(R)/len(R),3),
    se=round(statistics.pstdev(R)/math.sqrt(len(R)),3),
    total=round(sum(R),1), ret=round(RISK*sum(R),0),
    sd=round(statistics.pstdev(R),2),
    pf=pf(R),
    gain=round(sum(x for x in R if x>0),1),
    loss=round(sum(x for x in R if x<=0),1),
    sessions=len(sessions), taken=len({r['date'] for r in rows}),
)
# streaks
seq=[];cur=0
for v in R:
    if v<=0: cur+=1
    else:
        if cur: seq.append(cur)
        cur=0
if cur: seq.append(cur)
wseq=[];cur=0
for v in R:
    if v>0: cur+=1
    else:
        if cur: wseq.append(cur)
        cur=0
if cur: wseq.append(cur)
# A window with no winners at all leaves wseq empty, and max() of nothing raised
# ValueError -- which a three-day run through the control panel found at once.
out['streaks']=dict(worst_loss=max(seq, default=0), best_win=max(wseq, default=0),
                    loss_hist=sorted(Counter(seq).items()),
                    win_hist=sorted(Counter(wseq).items()))
# Cumulative R, not percent: risk is chosen on the page, so a percent curve
# would be wrong the moment the reader changes it. maxdd_r is the same quantity
# in R; maxdd stays in percent at the default risk for anything still reading it.
cum=peak=ddr=0.0; curve=[]
for r in rows:
    cum+=r['R']; peak=max(peak,cum); ddr=max(ddr,peak-cum)
    curve.append([r['date'].isoformat(), round(cum,3)])
out['curve']=curve; out['maxdd_r']=round(ddr,3); out['maxdd']=round(ddr*RISK,1)

# weekly, literal
weeks={}
for d in sorted(sessions):
    k=(d - dt.timedelta(days=d.weekday())).isoformat()
    weeks.setdefault(k,{'days':[], 'rows':[]})['days'].append(d)
for r in rows:
    k=(r['date'] - dt.timedelta(days=r['date'].weekday())).isoformat()
    weeks[k]['rows'].append(r)
out['weeks']=[]
for k in sorted(weeks):
    wk=weeks[k]
    b=blk(wk['rows'], len(wk['days']))
    out['weeks'].append(dict(start=k, sessions=len(wk['days']),
                             trades=(b or {}).get('trades',0),
                             wins=(b or {}).get('wins',0),
                             wr=(b or {}).get('wr',None),
                             ev=(b or {}).get('ev',None),
                             total=(b or {}).get('total',0.0),
                             ret=(b or {}).get('ret',0.0),
                             pf=(b or {}).get('pf',None),
                             seq=(b or {}).get('seq','')))
# quarterly
out['quarters']=[]
out['qlabel']=None   # set below: 'year' or 'quarter'
MULTIYEAR = len({r['t'].year for r in rows}) > 1
if MULTIYEAR:
    # One row per year. Quarters across three years read as one Q1 and hid which
    # year the money came from -- the only thing this strategy is judged on.
    for y in sorted({r['t'].year for r in rows}):
        rs=[r for r in rows if r['t'].year==y]
        x=blk(rs,len([d for d in sessions if d.year==y]))
        if x: out['quarters'].append(dict(q=str(y), **x))
else:
    for q,(a,b_) in enumerate([(1,3),(4,6),(7,9),(10,12)],1):
        rs=[r for r in rows if a<=r['t'].month<=b_]
        days=len([d for d in sessions if a<=d.month<=b_])
        x=blk(rs,days)
        if x: out['quarters'].append(dict(q="Q%d"%q, **x))
out['qlabel'] = "year" if MULTIYEAR else "quarter"
# monthly
out['months']=[]
for ym in sorted({(r['t'].year,r['t'].month) for r in rows}):
    y,m=ym
    rs=[r for r in rows if (r['t'].year,r['t'].month)==ym]
    days=len([d for d in sessions if (d.year,d.month)==ym])
    lab=dt.date(y,m,1).strftime("%b %y" if MULTIYEAR else "%b")
    out['months'].append(dict(month=lab, **blk(rs,days)))
# exits
c=Counter()
for r in rows:
    e=r['exit'].lower()
    c['target' if 'tp' in e else ('stop' if 'sl' in e else 'time cap')]+=1
out['exits']=[]
for k,n in c.most_common():
    g=[r['R'] for r in rows if (('tp' in r['exit'].lower()) if k=='target'
        else ('sl' in r['exit'].lower()) if k=='stop'
        else ('tp' not in r['exit'].lower() and 'sl' not in r['exit'].lower()))]
    out['exits'].append(dict(kind=k,n=n,share=round(100.0*n/len(rows),1),
                            avg=round(sum(g)/len(g),2),total=round(sum(g),1)))
# pass rates
def pr(risk,paths=40000):
    B=ctx.BENCH
    def ph(t):
        ok=0;days=[]
        for _ in range(paths):
            eq=0.0;d=0
            while d<2000:
                d+=1
                x=random.choice(R)
                # One trade a day, so a single trade IS the day. A loss past the
                # daily limit ends the attempt whatever the running total says --
                # above 2.74% risk the worst trade on record does exactly that,
                # and ignoring it overstated the pass rate badly at high risk.
                if B['daily'] and risk*x <= -B['daily']: break
                eq+=risk*x
                if eq<=-B['maxloss']: break
                if eq>=t and d>=max(B['mindays'],1): ok+=1;days.append(d);break
        return 100.0*ok/paths,(statistics.median(days) if days else 0)
    p1,m1=ph(B['p1'])
    p2,m2=ph(B['p2']) if B['p2'] else (100.0,0)      # a one-step challenge has no second phase
    freq=len(R)/float(len(sessions))
    return dict(risk=risk,p1=round(p1,1),p2=round(p2,1),both=round(p1*p2/100.0,1),
                trades=int(m1+m2), days=int(round((m1+m2)/freq)))
# out['pass'] used to live here: a SECOND Monte Carlo answer to the same
# question as the sweep, at a different path count, so the page could show
# 96.3% beside 96.4%. One simulation, one answer.

# What a losing run actually cost, per run length -- never reconstructed from an
# average loss. The stop move halves some losses, so the mean loss is -0.86 R
# while the five that actually landed in a row summed -5.10 R. Averaging them
# reports 10.7% at 2.5% risk and calls it safe; the real run is 12.8% and breaks
# a 12% limit. Same mistake, opposite conclusion.
def worst_runs(v):
    out_={}
    for i in range(len(v)):
        s_=0.0
        for k in range(1, len(v)-i+1):
            x=v[i+k-1]
            if x>=0: break
            s_+=x
            if k not in out_ or s_<out_[k]: out_[k]=s_
    return {k: round(abs(x),4) for k,x in out_.items()}
RUN_WORST = worst_runs(R)
out['run_worst'] = RUN_WORST
out['worst_run_r'] = RUN_WORST.get(out['streaks']['worst_loss'], 0.0)
out['worst_trade_r'] = round(abs(min(R)), 4)
out['loss_avg_abs'] = round(abs(statistics.mean([x for x in R if x <= 0])), 4)

# --- the risk sweep -------------------------------------------------------
# The report lets the reader set risk per trade. R is risk-independent, so a
# percent is just R x risk and the page can do that arithmetic itself. Three
# things it cannot: the pass rate, how long passing takes, and the chance a
# single loss breaks the daily limit -- all three come from walking real trade
# outcomes against the challenge barriers. Precompute them per risk level here,
# so the page swaps a looked-up value instead of inventing one.
def sweep_at(risk, paths=40000):
    B=ctx.BENCH
    p=pr(risk, paths)
    worst_trade=min(R)
    # A single loss past the daily limit ends the attempt on its own, whatever
    # the running total says.
    daily=[x for x in R if B['daily'] and x*risk <= -B['daily']]
    run=out['streaks']['worst_loss']
    return dict(risk=round(risk,2), ret=round(sum(R)*risk,1), maxdd=round(out['maxdd_r']*risk,1),
                pass_pct=p['both'], fail_pct=round(100.0-p['both'],1),
                trades=p['trades'], days=p['days'],
                money=round(ctx.DEPOSIT*risk/100.0),
                worst_trade=round(worst_trade*risk,2),
                daily_share=round(100.0*len(daily)/len(R),1),
                dd_breaks=bool(B['maxloss'] and out['maxdd_r']*risk > B['maxloss']),
                run_cost=round(out['worst_run_r']*risk,1),
                run_breaks=bool(B['maxloss'] and out['worst_run_r']*risk > B['maxloss']))
# The reader can type any risk from 1% to 99%, so every value the input can hold
# needs a simulated row -- the alternative is scaling a percent against a pass
# rate measured somewhere else, which looks measured and is invented. Fine
# where the answer is still interesting, coarse where it is obviously zero.
STEPS=([round(0.25*i,2) for i in range(1,21)]          # 0.25 .. 5.00 in quarters
       + [round(0.5*i,2) for i in range(11,41)]        # 5.5 .. 20 in halves
       + list(range(21,100)))                          # 21 .. 99 whole
# Above ~3% almost every path fails on the first bad trade, so the answer needs
# far fewer walks to be stable. Keeps a 130-row sweep to a few seconds.
out['sweep']=[sweep_at(x, 40000 if x <= 3 else 6000)
              for x in sorted(set(STEPS) | {round(RISK,2)})]

# Sample challenge attempts for the chart. Only the RANDOMNESS is fixed here:
# each attempt is a list of indexes into R, and the barriers are applied later
# at whatever risk the reader picks. So the page redraws the same eighty
# attempts rather than inventing new ones, and the picture is identical on
# every reload.
_mc=random.Random(20260909)
out['mc_seq']=[[_mc.randrange(len(R)) for _ in range(60)] for _ in range(80)]
out['R']=[round(x,4) for x in R]

# Where each rule starts to bite, in risk-per-trade. A limit divided by an R is
# risk-independent, so these are fixed prose -- but they were typed into the
# template and a comment, which is how a number goes stale.
out['cliffs']=dict(
    maxloss=round(ctx.BENCH['maxloss']/out['worst_run_r'],2) if out['worst_run_r'] else None,
    daily=round(ctx.BENCH['daily']/out['worst_trade_r'],2) if ctx.BENCH['daily'] and out['worst_trade_r'] else None)

# the range filter, measured on every date-eligible session -- row_ok would have
# removed the narrow ones, and the whole point of the section is to show them
def rangefilter():
    # Every session in the file, not just the reported window. The filter is
    # justified by what happened when the box was small, and in the reported
    # year it never was -- 2026's narrowest sessions are wider than 2024's median.
    allrows=list(csv.DictReader(open(ctx.CSV_LIVE)))
    if not allrows: return None
    v=sorted(((ctx.range_pct(r), float(r["R"])) for r in allrows), key=lambda x: x[0])
    # Quartiles of a handful of trades are noise with an index error attached.
    if len(v) < 8:
        return None
    years={}
    for r in allrows:
        y=int(r["entry_time"][:4])
        years.setdefault(y,[]).append((ctx.range_pct(r), float(r["R"]), float(r["entry"])))
    per=[dict(year=y,
              n=len(a),
              med=round(statistics.median([p_ for p_,_,_ in a]),4),
              px=round(statistics.median([x for _,_,x in a])),
              ev=round(sum(r for _,r,_ in a)/len(a),3),
              wr=round(100.0*len([1 for _,r,_ in a if r>0])/len(a),1))
         for y,a in sorted(years.items())]
    q=len(v)//4
    buckets=[]
    for i,lab in enumerate(("Narrowest 25%","Second 25%","Third 25%","Widest 25%")):
        seg=v[i*q:(i+1)*q] if i<3 else v[3*q:]
        rs=[r for _,r in seg]
        buckets.append(dict(label=lab, lo=round(seg[0][0],4), hi=round(seg[-1][0],4),
                            n=len(rs), wr=round(100.0*len([x for x in rs if x>0])/len(rs),1),
                            ev=round(sum(rs)/len(rs),3), total=round(sum(rs),1)))
    kept=[r for p_,r in v if ctx.MIN_RANGE_PCT<=0 or p_>=ctx.MIN_RANGE_PCT]
    return dict(pct=ctx.MIN_RANGE_PCT, buckets=buckets, years=per,
                n_all=len(v), n_kept=len(kept),
                ev_all=round(sum(r for _,r in v)/len(v),3),
                ev_kept=round(sum(kept)/len(kept),3) if kept else None,
                wr_all=round(100.0*len([1 for _,r in v if r>0])/len(v),1),
                wr_kept=round(100.0*len([1 for x in kept if x>0])/len(kept),1) if kept else None,
                widths=[round(p_,4) for p_,_ in v],
                med=round(statistics.median([p_ for p_,_ in v]),4))
out['rangefilter']=rangefilter()

# the half-of-the-range rule, measured against the same config with the filter off
def halves():
    v=[]
    for r in csv.DictReader(open(ctx.CSV_ALL)):
        if not ctx.row_ok(r): continue
        v.append((float(r['close_pos']), float(r['R'])))
    def st(x):
        n=len(x); w=len([y for y in x if y>0])
        return dict(n=n,wins=w,wr=round(100.0*w/n,1),ev=round(sum(x)/n,3),
                    total=round(sum(x),1),ret=round(RISK*sum(x),1),pf=pf(x))
    return dict(same=st([r for c,r in v if c>=0.50]),
                opp =st([r for c,r in v if c< 0.50]),
                all =st([r for c,r in v]))
out['halves']=halves()

# what the underlying price data covers, stated in the report
L=[x for x in R if x<=0]
out['losses']=dict(n=len(L), halved=len([x for x in L if x>-0.75]),
                   avg=round(sum(L)/len(L),2),
                   saved=round(sum(L)+len(L),1))     # in R; the page scales it
out['coverage']=dict(first=str(min(alldates)), last=str(max(alldates)),
                     dates=len(alldates))
# close-position quadrants -- hardcoded literals from an early study, no longer
# matching the record and read by nothing. Kept out of the JSON deliberately.
_dead_quadrants=[dict(band="above 75%",n=68,ev=0.529,wr=50.0),
                  dict(band="50 - 75%",n=25,ev=0.210,wr=36.0),
                  dict(band="25 - 50%",n=19,ev=0.217,wr=36.8),
                  dict(band="below 25%",n=7,ev=-0.816,wr=0.0)]
out['ctx']=dict(name=ctx.NAME,symbol=ctx.SYMBOL,risk=RISK,rr=ctx.RR,hold=ctx.HOLD,deposit=ctx.DEPOSIT,
                period=ctx.PERIOD,bench=ctx.BENCH,spec=ctx.SPEC_PATH or "strategies/asia-gold.toml")
json.dump(out,open(ctx.DATA_JSON,"w"),indent=1)
json.dump(out['halves'],open(ctx.HALVES_JSON,"w"),indent=1)
h=out['headline']
print("trades %d of %d sessions | WR %.1f%% | EV %+.3f | total %+.1f R = %+.0f%%"
      % (h['trades'],h['sessions'],h['wr'],h['ev'],h['total'],h['ret']))
print("weeks %d | quarters %d | worst DD %.1f%% | worst loss run %d"
      % (len(out['weeks']),len(out['quarters']),out['maxdd'],out['streaks']['worst_loss']))
c=out['coverage']; print("data covers %s .. %s (%d trading dates)"%(c['first'],c['last'],c['dates']))
hv=out['halves']; print("halves: same %d (%.1f%% WR, %+.3f EV) | opposite %d (%.1f%% WR, %+.3f EV)"
      %(hv['same']['n'],hv['same']['wr'],hv['same']['ev'],hv['opp']['n'],hv['opp']['wr'],hv['opp']['ev']))
for s in out['sweep']:
    if s['risk'] in (1.0,1.5,2.0,2.25,2.5):
        print("  risk %g%% -> pass %.1f%%, %d trades, ~%d days, run costs %.1f%%%s"
              % (s['risk'],s['pass_pct'],s['trades'],s['days'],s['run_cost'],
                 "  BREAKS the %g%% limit"%ctx.BENCH['maxloss'] if s['run_breaks'] else ""))
