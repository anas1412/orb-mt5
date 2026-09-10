"""The cumulative-return chart.

`curve` is cumulative R, not percent: the reader can change risk per trade on
the page, and a percent axis would then be wrong. The SHAPE is identical either
way -- scaling every point by the same factor does not move the line -- so only
the labels carry a percent, and each one carries its R value in `data-pct` for
the page to rewrite.
"""
import datetime as dt

def curve_svg(curve, risk=1.0, w=1180, h=280, pad=44):
    rs=[c[1] for c in curve]                       # cumulative R
    ys=[v*risk for v in rs]; lo=min(0,min(ys)); hi=max(ys)
    n=len(curve)
    # A degenerate curve has no span in either direction: one trade gives n==1,
    # and a single losing trade gives hi==lo==0. Both divided by zero, which a
    # three-day window through the control panel walked straight into.
    span=max(hi-lo, 1e-9)
    X=lambda i: pad + i*(w-pad-70)/max(n-1, 1)
    Y=lambda v: h-pad - (v-lo)*(h-pad-18)/span
    pts=" ".join("%.1f,%.1f"%(X(i),Y(v)) for i,v in enumerate(ys))
    area="%.1f,%.1f "%(X(0),Y(0))+pts+" %.1f,%.1f"%(X(n-1),Y(0))
    g=['<polygon points="%s" fill="url(#eqfill)" opacity=".5"/>'%area,
       '<polyline points="%s" fill="none" stroke="var(--pos)" stroke-width="2.4" stroke-linejoin="round"/>'%pts,
       '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".25"/>'%(pad,Y(0),w-70,Y(0))]
    # Gridlines are pinned to R, so they keep their positions when risk changes
    # and only their labels move. Twenty percent apart at the default risk.
    step=20.0/risk if risk else 20.0
    v=0.0
    while v<=max(rs)+1e-9:
        y=Y(v*risk)
        g.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".08"/>'%(pad,y,w-70,y))
        g.append('<text x="%d" y="%.1f" font-size="11" fill="currentColor" fill-opacity=".5" text-anchor="end" dy="3.5" data-pct="%.4f" data-fmt="int">%d%%</text>'%(pad-8,y,v,round(v*risk)))
        v+=step
    seen=set()
    for i,(iso,v) in enumerate(curve):
        mo=iso[:7]
        if mo not in seen:
            seen.add(mo)
            g.append('<text x="%.1f" y="%d" font-size="11" fill="currentColor" fill-opacity=".5" text-anchor="middle">%s</text>'
                     %(X(i),h-12,dt.date.fromisoformat(iso).strftime("%b")))
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--pos)"/>'%(X(n-1),Y(ys[-1])))
    g.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="var(--pos)" dy="4" data-pct="%.4f" data-fmt="signint">  %+.0f%%</text>'%(X(n-1)+7,Y(ys[-1]),rs[-1],ys[-1]))
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img"><title>Cumulative return</title>'
            '<desc>Cumulative return in percent, ending at %+.0f%%.</desc>'
            '<defs><linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%%" stop-color="var(--pos)" stop-opacity=".28"/>'
            '<stop offset="100%%" stop-color="var(--pos)" stop-opacity="0"/></linearGradient></defs>'
            '%s</svg>')%(w,h,ys[-1],"".join(g))
