"""Generate ~/orb/ORB-asia-report.html from report_data.json + trade_index.json."""
import rules_svg, halves_svg
import json, os, datetime as dt
d=json.load(open("report_data.json"))
idx=json.load(open("trade_index.json"))
RISK=2.0   # % of the initial balance per trade, no compounding
HOLD=90    # InpMaxHoldMinutes, must match the run that produced report_data.json
H=d['headline']
OUT   = os.path.expanduser("~/orb/ORB-asia-report.html")   # local deliverable
PAGES = os.path.expanduser("~/orb/strategy/index.html")        # GitHub Pages entry point
TRADES_SRC = os.path.expanduser("~/orb/trades")
TRADES_DST = os.path.expanduser("~/orb/strategy/trades")

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

def pfc(v, cls=""):
    """One cell. A period with no losses has no meaningful ratio, so it shows a
    dash instead of a number that would read as spectacular."""
    if v is None:
        return '<td class="q">&ndash;</td>'
    return '<td class="%s">%.2f</td>' % (cls or ("pos" if v >= 1 else "neg"), v)

def weeks_rows():
    out=[]
    for w in d['weeks']:
        s=dt.date.fromisoformat(w['start'])
        lab="%s&nbsp;&ndash;&nbsp;%s"%(s.strftime("%d %b"),(s+dt.timedelta(days=3)).strftime("%d %b"))
        if w['trades']==0:
            out.append('<tr class="q"><td>%s</td><td>%d</td><td>0</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td></tr>'
                       %(lab,w['sessions'])); continue
        cls="pos" if w['total']>0 else ("neg" if w['total']<0 else "")
        out.append('<tr><td>%s</td><td>%d</td><td><b>%d</b></td><td>%d / %d</td><td>%.0f%%</td>'
                   '%s<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
                   '<td class="%s"><b>%+.1f%%</b></td></tr>'
                   %(lab,w['sessions'],w['trades'],w['wins'],w['trades']-w['wins'],w['wr'],
                     pfc(w['pf']),cls,w['ev'],cls,w['total'],cls,w['ret']))
    return "".join(out)

def q_rows():
    out=[]
    for q in d['quarters']:
        out.append('<tr><td><b>%s</b></td><td>%d</td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
                   '%s<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td><td class="pos"><b>%+.1f%%</b></td></tr>'
                   %(q['q'],q['days'],q['trades'],q['wins'],q['losses'],q['wr'],
                     pfc(q['pf']),q['ev'],q['total'],q['ret']))
    return "".join(out)

def m_rows():
    out=[]
    for m in d['months']:
        out.append('<tr><td><b>%s</b></td><td>%d</td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
                   '%s<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td>'
                   '<td class="pos"><b>%+.1f%%</b></td></tr>'
                   %(m['month'],m['days'],m['trades'],m['wins'],m['losses'],m['wr'],
                     pfc(m['pf']),m['ev'],m['total'],m['ret']))
    return "".join(out)

def exit_rows():
    NAME={'target':'Target hit  (+2R)','stop':'Stopped out','time cap':'%d-minute cap'%HOLD}
    out=[]
    for e in d['exits']:
        cls="pos" if e['total']>0 else "neg"
        out.append('<tr><td>%s</td><td><b>%d</b></td><td>%.1f%%</td><td class="%s">%+.2f R</td>'
                   '<td class="%s"><b>%+.1f R</b></td><td class="%s"><b>%+.1f%%</b></td></tr>'
                   %(NAME[e['kind']],e['n'],e['share'],cls,e['avg'],cls,e['total'],
                     cls,e['total']*RISK))
    return "".join(out)

def pass_rows():
    out=[]
    for p in d['pass']:
        hi=' class="hi"' if p['risk']==2.0 else ''
        out.append('<tr%s><td><b>%.1f%%</b></td><td>%.1f%%</td><td>%.1f%%</td>'
                   '<td class="pos"><b>%.1f%%</b></td><td>%d</td><td>%d</td><td>%.0f%%</td></tr>'
                   %(hi,p['risk'],p['p1'],p['p2'],p['both'],p['trades'],p['days'],
                     d['streaks']['worst_loss']*p['risk']))
    return "".join(out)

def streak_rows():
    out=[]
    for k,n in d['streaks']['loss_hist']:
        cost=k*2.0
        cls="neg" if cost>=10 else ("warn" if cost>=6 else "")
        out.append('<tr class="%s"><td>%d in a row</td><td>%d&times;</td><td>%.0f%% of the account</td></tr>'%(cls,k,n,cost))
    return "".join(out)

def half_rows():
    hv=d["halves"]
    spec=[("Broke the half it closed in","same","ok","TRADE"),
          ("Broke the opposite half","opp","no","SKIP")]
    out=[]
    for label,key,pill,verdict in spec:
        q=hv[key]
        out.append('<tr class="%s"><td><b>%s</b></td><td>%d</td><td>%d</td><td>%.1f%%</td>'
                   '%s<td class="%s">%+.3f</td><td class="%s">%+.1f R</td><td class="%s">%+.1f%%</td>'
                   '<td><span class="pill %s">%s</span></td></tr>'
                   %("hi" if key=="same" else "q", label, q['n'], q['wins'], q['wr'], pfc(q['pf']),
                     "pos" if q['ev']>0 else "neg", q['ev'],
                     "pos" if q['total']>0 else "neg", q['total'],
                     "pos" if q['total']>0 else "neg", q['total']*RISK, pill, verdict))
    a=hv['all']
    out.append('<tr><td><b>Every break, no filter</b></td><td>%d</td><td>%d</td><td>%.1f%%</td>'
               '%s<td class="pos">%+.3f</td><td class="pos">%+.1f R</td>'
               '<td class="pos">%+.1f%%</td><td></td></tr>'
               %(a['n'],a['wins'],a['wr'],pfc(a['pf']),a['ev'],a['total'],a['total']*RISK))
    return "".join(out)

def gallery():
    cards=[]
    for t in idx:
        cls="win" if t['R']>0 else "loss"
        d=dt.date.fromisoformat(t['date'])
        cards.append('<a class="tc %s" href="trades/%s" target="_blank" '
                     'data-outcome="%s" data-day="%s" data-month="%s" data-r="%.3f">'
                     '<img src="trades/%s" alt="%s %s" loading="lazy">'
                     '<span class="tm"><b>%s</b> %s · %s · closed %s half · <i>%+.2f R</i></span></a>'
                     %(cls,t['file'],cls,t['day'],d.strftime("%b"),t['R'],
                       t['file'],t['date'],t['dir'],
                       d.strftime("%d %b"),t['day'],
                       t['dir'].upper(),"top" if t['dir']=="buy" else "bottom",t['R']))
    return "".join(cards)

def filters():
    """Chips built from the trades that exist, so no chip can match nothing."""
    days   = [d for d in ("Mon","Tue","Wed","Thu","Fri") if any(t['day']==d for t in idx)]
    months = sorted({dt.date.fromisoformat(t['date']).month for t in idx})
    wins   = len([t for t in idx if t['R']>0])
    def chip(g,v,label,extra=""):
        return ('<button type="button" class="chip%s" data-f="%s" data-v="%s" '
                'aria-pressed="false">%s</button>' % (extra,g,v,label))
    g=[]
    g.append('<div class="fgroup"><b>Result</b>'
             + chip("outcome","*","All %d"%len(idx))
             + chip("outcome","win","Wins %d"%wins," win")
             + chip("outcome","loss","Losses %d"%(len(idx)-wins)," loss")
             + '</div>')
    g.append('<div class="fgroup"><b>Day</b>' + chip("day","*","All")
             + "".join(chip("day",d,"%s %d"%(d,len([t for t in idx if t['day']==d])))
                       for d in days) + '</div>')
    g.append('<div class="fgroup"><b>Month</b>' + chip("month","*","All")
             + "".join(chip("month",dt.date(2026,m,1).strftime("%b"),
                            "%s %d"%(dt.date(2026,m,1).strftime("%b"),
                                     len([t for t in idx
                                          if dt.date.fromisoformat(t['date']).month==m])))
                       for m in months) + '</div>')
    g.append('<div class="fcount" id="fcount"></div>')
    return '<div class="filters">' + "".join(g) + '</div>'

wins=H['wins']; losses=H['trades']-wins
tpl=open("template.html").read()
html=(tpl
 .replace("{{TRADES}}",str(H['trades'])).replace("{{WINS}}",str(wins)).replace("{{LOSSES}}",str(losses))
 .replace("{{WR}}","%.1f"%H['wr']).replace("{{EV}}","%+.3f"%H['ev']).replace("{{SE}}","%.3f"%H['se'])
 .replace("{{TOTALR}}","%+.1f"%H['total']).replace("{{RET}}","%+.0f"%H['ret'])
 .replace("{{SD}}","%.2f"%H['sd']).replace("{{SESSIONS}}",str(H['sessions']))
 .replace("{{MAXDD}}","%.1f"%d['maxdd'])
 .replace("{{WORSTRUN}}",str(d['streaks']['worst_loss']))
 .replace("{{BESTRUN}}",str(d['streaks']['best_win']))
 .replace("{{PASS2}}","%.1f"%[p for p in d['pass'] if p['risk']==2.0][0]['both'])
 .replace("{{DAYS2}}",str([p for p in d['pass'] if p['risk']==2.0][0]['days']))
 .replace("{{CURVE}}",curve_svg(d['curve']))
 .replace("{{WEEKROWS}}",weeks_rows()).replace("{{QROWS}}",q_rows())
 .replace("{{MROWS}}",m_rows()).replace("{{EXITROWS}}",exit_rows())
 .replace("{{PASSROWS}}",pass_rows()).replace("{{STREAKROWS}}",streak_rows())
 .replace("{{HALFROWS}}",half_rows())
 .replace("{{RULESSVG}}",rules_svg.build())
 .replace("{{HALVESSVG}}",halves_svg.build(d["halves"]))
 .replace("{{ALLR}}","%+.1f"%d["halves"]["all"]["total"])
 .replace("{{ALLN}}","%d"%d["halves"]["all"]["n"])
 .replace("{{ALLWR}}","%.1f%%"%d["halves"]["all"]["wr"])
 .replace("{{OPPN}}","%d"%d["halves"]["opp"]["n"])
 .replace("{{OPPR}}","%+.1f"%d["halves"]["opp"]["total"])
 .replace("{{LN}}","%d"%d["losses"]["n"])
 .replace("{{LHALVED}}","%d"%d["losses"]["halved"])
 .replace("{{LAVG}}","%+.2f"%d["losses"]["avg"])
 .replace("{{LAVGABS}}","%.2f"%abs(d["losses"]["avg"]))
 .replace("{{LSAVED}}","%+.1f"%d["losses"]["saved"])
 .replace("{{LSAVEDPCT}}","%+d%%"%d["losses"]["saved_pct"])
 .replace("{{NTARGET}}","%d"%next(e["n"] for e in d["exits"] if e["kind"]=="target"))
 .replace("{{NSTOP}}","%d"%next(e["n"] for e in d["exits"] if e["kind"]=="stop"))
 .replace("{{SELFPCT}}","%.0f%%"%(100.0*(H["trades"]-next(e["n"] for e in d["exits"] if e["kind"]=="time cap"))/H["trades"]))
 .replace("{{HOLD}}","%d"%HOLD)
 .replace("{{PF}}","%.2f"%H["pf"])
 .replace("{{GAIN}}","%+.1f"%H["gain"]).replace("{{LOSS}}","%.1f"%abs(H["loss"]))
 .replace("{{LASTDATE}}",dt.date.fromisoformat(d["coverage"]["last"]).strftime("%d %B %Y")).replace("{{GALLERY}}",gallery()).replace("{{FILTERS}}",filters())
 .replace("{{GENERATED}}","2026-08-22"))
open(OUT,"w").write(html)
open(PAGES,"w").write(html)

# Pages serves from the repo, so the charts have to live there too
import shutil
if os.path.isdir(TRADES_SRC):
    os.makedirs(TRADES_DST, exist_ok=True)
    n=0
    for f in os.listdir(TRADES_SRC):
        if f.endswith(".png"):
            shutil.copy2(os.path.join(TRADES_SRC,f), os.path.join(TRADES_DST,f)); n+=1
    print("copied %d charts into the repo for Pages" % n)
print("wrote %s  (%.0f KB)" % (OUT, os.path.getsize(OUT)/1024))
