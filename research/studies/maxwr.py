"""How high can the win rate go at RR 1, and what does it cost?"""
import statistics, math, random
exec(open('structsl.py').read().split('ss=setups()')[0])
random.seed(9999)

def setups_cp(min_cp):
    out=[]
    for d,b in sorted(days.items()):
        if d.weekday()>3: continue            # Mon-Thu
        st=off(d)*60
        w=[b[m] for m in range(st,st+15) if m in b]
        if len(w)<15: continue
        hi=max(x[1] for x in w); lo=min(x[2] for x in w); rng=hi-lo
        if rng<=0: continue
        cp=(w[-1][3]-lo)/rng
        sig=None
        for k in range(st+15,st+30):
            if k not in b: break
            if b[k][3]>hi: sig=(k,True); break
            if b[k][3]<lo: sig=(k,False); break
        if not sig: continue
        k,buy=sig
        if (cp if buy else 1-cp) < min_cp: continue
        if k+1 not in b: continue
        out.append(dict(d=d,b=b,k=k,buy=buy,hi=hi,lo=lo,rng=rng,e=b[k+1][0],w=w))
    return out
def pr(Rs,t,md,paths=20000):
    ok=0;dd=[]
    for _ in range(paths):
        eq=100.0;n=0
        while n<3000:
            n+=1;eq+=2.0*random.choice(Rs)*eq/100.0
            if eq<=90.0:break
            if eq>=100+t and n>=md: ok+=1;dd.append(n);break
    return 100*ok/paths,(statistics.median(dd) if dd else 0)
print("Gold Asia, Mon-Thu. Chasing win rate at RR 1.\n")
print("  close-pos  SL     move   n    WR      EV      pass both  ~days")
best=None
for cp in (0.25,0.50,0.75):
    ss=setups_cp(cp)
    for slf in (0.50,0.75,1.00):
        for mat,mto,mv in ((0.5,-0.5,"on "),(0.0,0.0,"off")):
            R=[simulate(s,slf,rr=1.0,mat=mat,mto=mto) for s in ss]
            R=[x for x in R if x is not None]
            if len(R)<30: continue
            wr=100.0*len([x for x in R if x>0])/len(R)
            ev=sum(R)/len(R)
            p1,m1=pr(R,8,3); p2,m2=pr(R,5,3)
            ndays=(m1+m2)/max(len(R)/130.0,.01)
            print("    %.2f     %.2f   %s   %3d  %4.1f%%  %+.3f    %5.1f%%     %3.0f"
                  % (cp,slf,mv,len(R),wr,ev,p1*p2/100,ndays))
            if best is None or wr>best[0]: best=(wr,cp,slf,mv,ev,p1*p2/100,ndays,len(R))
    print()
print("  highest win rate found: %.1f%%  (close-pos %.2f, SL %.2f, move %s)"
      % (best[0],best[1],best[2],best[3]))
print("     -> EV %+.3f, pass %.1f%%, ~%.0f days, %d trades" % (best[4],best[5],best[6],best[7]))
ssl=setups_cp(0.25)
R2=[simulate(s,0.50,rr=2.0,mat=0.5,mto=-0.5) for s in ssl]
R2=[x for x in R2 if x is not None]
p1,m1=pr(R2,8,3); p2,m2=pr(R2,5,3)
print("\n  the live RR2 config for comparison:")
print("     WR %.1f%%, EV %+.3f, pass %.1f%%, ~%.0f days, %d trades"
      % (100.0*len([x for x in R2 if x>0])/len(R2),sum(R2)/len(R2),
         p1*p2/100,(m1+m2)/max(len(R2)/130.0,.01),len(R2)))
