"""The cumulative-return chart. Shared by the report and the slide deck so
there is one copy of the drawing code."""
import datetime as dt

def curve_svg(curve, w=1180, h=280, pad=44):
    ys=[c[1] for c in curve]; lo=min(0,min(ys)); hi=max(ys)
    n=len(curve)
    X=lambda i: pad + i*(w-pad-70)/(n-1)
    Y=lambda v: h-pad - (v-lo)*(h-pad-18)/(hi-lo)
    pts=" ".join("%.1f,%.1f"%(X(i),Y(v)) for i,v in enumerate(ys))
    area="%.1f,%.1f "%(X(0),Y(0))+pts+" %.1f,%.1f"%(X(n-1),Y(0))
    g=['<polygon points="%s" fill="url(#eqfill)" opacity=".5"/>'%area,
       '<polyline points="%s" fill="none" stroke="var(--pos)" stroke-width="2.4" stroke-linejoin="round"/>'%pts,
       '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".25"/>'%(pad,Y(0),w-70,Y(0))]
    for v in range(0,int(hi)+1,20):
        g.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".08"/>'%(pad,Y(v),w-70,Y(v)))
        g.append('<text x="%d" y="%.1f" font-size="11" fill="currentColor" fill-opacity=".5" text-anchor="end" dy="3.5">%d%%</text>'%(pad-8,Y(v),v))
    seen=set()
    for i,(iso,v) in enumerate(curve):
        mo=iso[:7]
        if mo not in seen:
            seen.add(mo)
            g.append('<text x="%.1f" y="%d" font-size="11" fill="currentColor" fill-opacity=".5" text-anchor="middle">%s</text>'
                     %(X(i),h-12,dt.date.fromisoformat(iso).strftime("%b")))
    g.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--pos)"/>'%(X(n-1),Y(ys[-1])))
    g.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="700" fill="var(--pos)" dy="4">  +%.0f%%</text>'%(X(n-1)+7,Y(ys[-1]),ys[-1]))
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img"><title>Cumulative return</title>'
            '<desc>Cumulative return in percent across 2026, ending at +%.0f%%.</desc>'
            '<defs><linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%%" stop-color="var(--pos)" stop-opacity=".28"/>'
            '<stop offset="100%%" stop-color="var(--pos)" stop-opacity="0"/></linearGradient></defs>'
            '%s</svg>')%(w,h,ys[-1],"".join(g))
