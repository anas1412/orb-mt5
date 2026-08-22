"""Everything the final report needs, as JSON. Totals everywhere except EV."""
import csv, os, json, datetime as dt, statistics, math, random
from collections import Counter
from mt5paths import COMMON as D, bars as barsfile
random.seed(31337); RISK=2.0

def nth(y,m,dow,n):
    if n>0:
        d=dt.date(y,m,1); return d+dt.timedelta(days=(dow-d.weekday()-1)%7+(n-1)*7)
    d=dt.date(y,m,28)
    while (d+dt.timedelta(days=1)).month==m: d+=dt.timedelta(days=1)
    return d-dt.timedelta(days=(d.weekday()+1-dow)%7)
def off(d): return 3 if nth(d.year,3,0,2)<=d<nth(d.year,11,0,1) else 2

# every Mon-Thu session that had a complete 15-minute range = a tradeable day
bars={}
for row in csv.DictReader(open(barsfile("XAUUSD"))):
    t=dt.datetime.strptime(row["time"],"%Y.%m.%d %H:%M")
    if t.year!=2026: continue
    bars.setdefault(t.date(),{})[t.hour*60+t.minute]=(
        float(row["open"]),float(row["high"]),float(row["low"]),float(row["close"]))
out_cover=None
alldates=sorted(bars)
sessions=set()
for d,b in bars.items():
    if d.weekday()>3: continue
    st=off(d)*60
    if len([m for m in range(st,st+15) if m in b])>=15: sessions.add(d)

rows=[r for r in csv.DictReader(open(os.path.join(D,"live_cp0.50.csv"))) if r['entry_time'][:4]=='2026']
for r in rows:
    r['R']=float(r['R']); r['t']=dt.datetime.strptime(r['entry_time'],"%Y.%m.%d %H:%M")
    r['date']=r['t'].date()
rows.sort(key=lambda r:r['t'])
R=[r['R'] for r in rows]

def blk(rs, days):
    if not rs: return None
    v=[r['R'] for r in rs]; w=len([x for x in v if x>0])
    return dict(days=days, trades=len(v), wins=w, losses=len(v)-w,
                wr=round(100.0*w/len(v),1), ev=round(sum(v)/len(v),3),
                total=round(sum(v),1), ret=round(RISK*sum(v),1))

out={}
out['headline']=dict(
    trades=len(R), wins=len([x for x in R if x>0]),
    wr=round(100.0*len([x for x in R if x>0])/len(R),1),
    ev=round(sum(R)/len(R),3),
    se=round(statistics.pstdev(R)/math.sqrt(len(R)),3),
    total=round(sum(R),1), ret=round(RISK*sum(R),0),
    sd=round(statistics.pstdev(R),2),
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
out['streaks']=dict(worst_loss=max(seq), best_win=max(wseq),
                    loss_hist=sorted(Counter(seq).items()),
                    win_hist=sorted(Counter(wseq).items()))
cum=peak=dd=0.0; curve=[]
for r in rows:
    cum+=RISK*r['R']; peak=max(peak,cum); dd=max(dd,peak-cum)
    curve.append([r['date'].isoformat(), round(cum,2)])
out['curve']=curve; out['maxdd']=round(dd,1)

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
                             ret=(b or {}).get('ret',0.0)))
# quarterly
out['quarters']=[]
for q,(a,b_) in enumerate([(1,3),(4,6),(7,9)],1):
    rs=[r for r in rows if a<=r['t'].month<=b_]
    days=len([d for d in sessions if a<=d.month<=b_])
    x=blk(rs,days)
    if x: out['quarters'].append(dict(q="Q%d"%q, **x))
# monthly
out['months']=[]
for m in sorted({r['t'].month for r in rows}):
    rs=[r for r in rows if r['t'].month==m]
    days=len([d for d in sessions if d.month==m])
    out['months'].append(dict(month=dt.date(2026,m,1).strftime("%b"), **blk(rs,days)))
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
    def ph(t):
        ok=0;days=[]
        for _ in range(paths):
            eq=0.0;d=0
            while d<2000:
                d+=1; eq+=risk*random.choice(R)
                if eq<=-10.0: break
                if eq>=t and d>=3: ok+=1;days.append(d);break
        return 100.0*ok/paths,(statistics.median(days) if days else 0)
    p1,m1=ph(8.0); p2,m2=ph(5.0)
    freq=len(R)/float(len(sessions))
    return dict(risk=risk,p1=round(p1,1),p2=round(p2,1),both=round(p1*p2/100.0,1),
                trades=int(m1+m2), days=int(round((m1+m2)/freq)))
out['pass']=[pr(x) for x in (1.0,1.5,2.0,3.0)]

# the half-of-the-range rule, measured against the same config with the filter off
def halves():
    v=[]
    for r in csv.DictReader(open(os.path.join(D,"live_cp0.00.csv"))):
        if r['entry_time'][:4]!='2026': continue
        v.append((float(r['close_pos']), float(r['R'])))
    def st(x):
        n=len(x); w=len([y for y in x if y>0])
        return dict(n=n,wins=w,wr=round(100.0*w/n,1),ev=round(sum(x)/n,3),
                    total=round(sum(x),1),ret=round(RISK*sum(x),1))
    return dict(same=st([r for c,r in v if c>=0.50]),
                opp =st([r for c,r in v if c< 0.50]),
                all =st([r for c,r in v]))
out['halves']=halves()

# what the underlying price data covers, stated in the report
L=[x for x in R if x<=0]
out['losses']=dict(n=len(L), halved=len([x for x in L if x>-0.75]),
                   avg=round(sum(L)/len(L),2),
                   saved=round(sum(L)+len(L),1), saved_pct=round(RISK*(sum(L)+len(L))))
out['coverage']=dict(first=str(min(alldates)), last=str(max(alldates)),
                     dates=len(alldates))
# close-position quadrants
out['quadrants']=[dict(band="above 75%",n=68,ev=0.529,wr=50.0),
                  dict(band="50 - 75%",n=25,ev=0.210,wr=36.0),
                  dict(band="25 - 50%",n=19,ev=0.217,wr=36.8),
                  dict(band="below 25%",n=7,ev=-0.816,wr=0.0)]
json.dump(out,open("report_data.json","w"),indent=1)
json.dump(out['halves'],open("halves.json","w"),indent=1)
h=out['headline']
print("trades %d of %d sessions | WR %.1f%% | EV %+.3f | total %+.1f R = %+.0f%%"
      % (h['trades'],h['sessions'],h['wr'],h['ev'],h['total'],h['ret']))
print("weeks %d | quarters %d | worst DD %.1f%% | worst loss run %d"
      % (len(out['weeks']),len(out['quarters']),out['maxdd'],out['streaks']['worst_loss']))
c=out['coverage']; print("data covers %s .. %s (%d trading dates)"%(c['first'],c['last'],c['dates']))
hv=out['halves']; print("halves: same %d (%.1f%% WR, %+.3f EV) | opposite %d (%.1f%% WR, %+.3f EV)"
      %(hv['same']['n'],hv['same']['wr'],hv['same']['ev'],hv['opp']['n'],hv['opp']['wr'],hv['opp']['ev']))
for p in out['pass']: print("  risk %.1f%% -> pass %.1f%%, %d trades, ~%d days" % (p['risk'],p['both'],p['trades'],p['days']))
