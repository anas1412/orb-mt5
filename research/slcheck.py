import statistics, math
from sessionsim import run
for name,uh,um in (("Asia 00:00",0,0),("London 07:00",7,0),("New York 13:30",13,30)):
    print("\n%s" % name)
    print("   SL          RR    stop move      n     EV all  +/-SE     2024     2025     2026")
    for sl,lab in ((0.5,"0.50 midpoint"),(1.0,"1.00 far side")):
        for rr in (1.5,2.0,2.5,3.0):
            for mat,mto,mv in ((0.5,-0.5,"0.5->-0.5"),(0.0,0.0,"off      ")):
                res=run(uh,um,sl_frac=sl,rr=rr,mat=mat,mto=mto)
                R=[r for _,r in res]
                if not R: continue
                per={y:[r for yy,r in res if yy==y] for y in (2024,2025,2026)}
                print("   %s  %.1f   %s  %3d   %+.3f  %.3f   %+.3f   %+.3f   %+.3f"
                      % (lab,rr,mv,len(R),sum(R)/len(R),
                         statistics.pstdev(R)/math.sqrt(len(R)),
                         sum(per[2024])/len(per[2024]),sum(per[2025])/len(per[2025]),
                         sum(per[2026])/len(per[2026])))
