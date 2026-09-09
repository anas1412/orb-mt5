"""Generate the report from report_data.json + trade_index.json.

Writes one file, ctx.REPORT_PAGES, and the charts are already where the page
links to them -- all_trades.py draws them straight into that folder.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import rules_svg, halves_svg
from curve import curve_svg
import json, os, re, datetime as dt
import ctx
import spec as S
d=json.load(open(ctx.DATA_JSON))
idx=json.load(open(ctx.INDEX_JSON))
RISK=ctx.RISK
HOLD=ctx.HOLD
H=d['headline']
PAGES = ctx.REPORT_PAGES

def pfc(v, cls=""):
    """One cell. A period with no losses has no meaningful ratio, so it shows a
    dash instead of a number that would read as spectacular."""
    if v is None:
        return '<td class="q">&ndash;</td>'
    return '<td class="%s">%.2f</td>' % (cls or ("pos" if v >= 1 else "neg"), v)

def seq_cell(s):
    """L-L-W-W-L, wins green and losses red, so a streak is visible at a glance."""
    if not s: return "&ndash;"
    return '<span class="seq">%s</span>' % "-".join(
        '<b class="%s">%s</b>' % ("pos" if c == "W" else "neg", c) for c in s.split("-"))

def weeks_rows():
    out=[]
    for w in d['weeks']:
        s=dt.date.fromisoformat(w['start'])
        lab="%s&nbsp;&ndash;&nbsp;%s"%(s.strftime("%d %b"),(s+dt.timedelta(days=3)).strftime("%d %b"))
        if w['trades']==0:
            out.append('<tr class="q"><td>%s</td><td>%d</td><td>0</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td><td>&ndash;</td></tr>'
                       %(lab,w['sessions'])); continue
        cls="pos" if w['total']>0 else ("neg" if w['total']<0 else "")
        out.append('<tr><td>%s</td><td>%d</td><td><b>%d</b></td><td>%d / %d</td><td>%s</td><td>%.0f%%</td>'
                   '%s<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
                   '<td class="%s"><b><span data-pct="%.4f"></span>%%</b></td></tr>'
                   %(lab,w['sessions'],w['trades'],w['wins'],w['trades']-w['wins'],
                     seq_cell(w['seq']),w['wr'],
                     pfc(w['pf']),cls,w['ev'],cls,w['total'],cls,w['total']))
    return "".join(out)

def q_rows():
    out=[]
    for q in d['quarters']:
        out.append('<tr><td><b>%s</b></td><td>%d</td><td>%d</td><td>%d / %d</td><td>%.1f%%</td>'
                   '%s<td class="pos">%+.3f</td><td class="pos"><b>%+.1f R</b></td><td class="pos"><b><span data-pct="%.4f"></span>%%</b></td></tr>'
                   %(q['q'],q['days'],q['trades'],q['wins'],q['losses'],q['wr'],
                     pfc(q['pf']),q['ev'],q['total'],q['total']))
    return "".join(out)

def m_rows():
    out=[]
    for m in d['months']:
        cls="pos" if m['total']>0 else ("neg" if m['total']<0 else "")
        out.append('<tr><td><b>%s</b></td><td>%d</td><td>%d</td><td>%d / %d</td><td>%s</td><td>%.1f%%</td>'
                   '%s<td class="%s">%+.3f</td><td class="%s"><b>%+.1f R</b></td>'
                   '<td class="%s"><b><span data-pct="%.4f"></span>%%</b></td></tr>'
                   %(m['month'],m['days'],m['trades'],m['wins'],m['losses'],
                     seq_cell(m['seq']),m['wr'],
                     pfc(m['pf']),cls,m['ev'],cls,m['total'],cls,m['total']))
    return "".join(out)

def exit_rows():
    NAME={'target':'Target hit  (+%gR)'%ctx.RR,'stop':'Stopped out','time cap':'%d-minute cap'%HOLD}
    out=[]
    for e in d['exits']:
        cls="pos" if e['total']>0 else "neg"
        out.append('<tr><td>%s</td><td><b>%d</b></td><td>%.1f%%</td><td class="%s">%+.2f R</td>'
                   '<td class="%s"><b>%+.1f R</b></td><td class="%s"><b><span data-pct="%.4f"></span>%%</b></td></tr>'
                   %(NAME[e['kind']],e['n'],e['share'],cls,e['avg'],cls,e['total'],
                     cls,e['total']))
    return "".join(out)

def sweep_rows():
    """One row per precomputed risk level. The page highlights the selected one
    and never recomputes these -- the pass columns come from a simulation."""
    lim=ctx.BENCH['maxloss'] or 0
    daily=ctx.BENCH['daily'] or 0
    out=[]
    for s in d['sweep']:
        # The input accepts anything to 99%, but a table of 129 rows is not a
        # table. Show the range where the answer is still a decision.
        if s['risk'] > 2.5 or s['risk'] < 0.5 or (s['risk']*4) % 1: continue
        cls=[]
        if s['run_breaks']: cls.append('neg')
        if daily and abs(s['worst_trade'])>daily: cls.append('neg')
        out.append('<tr data-rowrisk="%s"%s><td><b>%g%%</b></td><td class="pos"><b>%.1f%%</b></td>'
                   '<td>%d</td><td>%d</td><td class="pos"><b>%+.0f%%</b></td><td>%.1f%%</td>'
                   '<td class="%s">%.1f%%</td><td class="%s">%.2f%%</td></tr>'
                   %(s['risk'], ' class="%s"'%cls[0] if cls else '', s['risk'], s['pass_pct'],
                     s['trades'], s['days'], s['ret'], s['maxdd'],
                     'neg' if s['run_breaks'] else '', s['run_cost'],
                     'neg' if daily and abs(s['worst_trade'])>daily else '', s['worst_trade']))
    return "".join(out)

def streak_rows():
    """Cost of a k-loss run at the chosen risk. k full stops, each costing the
    average realised loss -- which is a little over 1 R once spread and
    commission are in, so this is not simply k x risk."""
    lim=ctx.BENCH['maxloss'] or 10.0
    worst=d['run_worst']
    out=[]
    for k,n in d['streaks']['loss_hist']:
        r=worst.get(str(k), worst.get(k, k*d['loss_avg_abs']))   # what k in a row really cost
        cost=r*RISK
        cls="neg" if cost>=lim else ("warn" if cost>=lim*0.6 else "")
        out.append('<tr class="%s"><td>%d in a row</td><td>%d&times;</td><td>%+.2f R</td>'
                   '<td><span data-pct="%.4f" data-fmt="plain1"></span>%% of the account</td></tr>'
                   %(cls,k,n,-r,r))
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
    return "".join(cards).replace('"trades/', '"%s/' % ctx.TRADES_WEB)   # charts live in trades-<name>/ for a spec

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
             + "".join(chip("month",dt.date(ctx.FROM.year,m,1).strftime("%b"),
                            "%s %d"%(dt.date(ctx.FROM.year,m,1).strftime("%b"),
                                     len([t for t in idx
                                          if dt.date.fromisoformat(t['date']).month==m])))
                       for m in months) + '</div>')
    g.append('<div class="fcount" id="fcount"></div>')
    return '<div class="filters">' + "".join(g) + '</div>'

wins=H['wins']; losses=H['trades']-wins
def mc_svg(risk):
    """Eighty sample attempts, drawn as they would run at this risk.

    The sequences come from report_data so the browser can redraw the SAME
    eighty attempts when risk changes -- the barriers move, the luck does not.
    Illustration only: the pass rate itself comes from 40 000 attempts in the
    sweep, not from these eighty.
    """
    W,H,PAD=1180,300,44
    T=ctx.BENCH['p1']; L=-(ctx.BENCH['maxloss'])
    Rv=d['R']; hi=T*1.45; lo=L*1.35
    X=lambda i,n: PAD + i*(W-PAD-24)/max(n-1,1)
    Y=lambda v: H-PAD - (v-lo)*(H-PAD-16)/(hi-lo)
    runs=[]
    longest=1
    for seq in d['mc_seq']:
        eq=0.0; pts=[0.0]; out_='open'
        for k in seq:
            eq += risk*Rv[k]; pts.append(eq)
            if eq>=T: out_='pass'; break
            if eq<=L: out_='fail'; break
        runs.append((out_,pts)); longest=max(longest,len(pts))
    g=[]
    for v,lab in ((T,'+%g%% target'%T),(L,'%g%% max loss'%L)):
        g.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" '
                 'stroke-opacity=".45" stroke-width="1.4" stroke-dasharray="7 5"/>'%(PAD,Y(v),W-24,Y(v)))
        g.append('<text x="%d" y="%.1f" font-size="12" font-weight="640" fill="currentColor" '
                 'fill-opacity=".65" dy="-6">%s</text>'%(PAD+2,Y(v),lab))
    g.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" stroke-opacity=".18"/>'%(PAD,Y(0),W-24,Y(0)))
    for out_,pts in sorted(runs, key=lambda r: r[0]=='fail'):
        col='var(--neg)' if out_=='fail' else 'var(--pos)'
        g.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
                 'stroke-opacity="%s" stroke-linejoin="round"/>'
                 %(" ".join("%.1f,%.1f"%(X(i,longest),Y(v)) for i,v in enumerate(pts)),
                   col, "2" if out_=="fail" else "1.1", ".95" if out_=="fail" else ".5"))
    nf=len([1 for o,_ in runs if o=='fail'])
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img" id="mcsvg" data-mc="1">'
            '<title>Eighty simulated challenge attempts</title>'
            '<desc>Eighty attempts at %g%% risk; %d reached the target, %d hit the maximum loss.</desc>'
            '%s<text x="%d" y="%d" font-size="11" fill="currentColor" fill-opacity=".5">trades taken</text>'
            '</svg>')%(W,H,risk,len(runs)-nf,nf,"".join(g),PAD,H-10)

def riskdata():
    """What the page needs to answer "what changes if I risk X?" offline.

    Only the simulated quantities travel: everything else on the page is R and
    the page multiplies. maxrisk is the largest risk this account permits, which
    is a rule of the challenge rather than anything measured.
    """
    hist=dict(d['streaks']['loss_hist'])
    run=d['streaks']['worst_loss']
    return dict(sweep=d['sweep'], chips=[1,1.5,2,2.5], maxrisk=99, risk=RISK,
                R=d['R'], mc=d['mc_seq'],
                maxloss=ctx.BENCH['maxloss'], daily=ctx.BENCH['daily'],
                target=ctx.BENCH['p1'], worst_run=run,
                worst_run_times="once" if hist.get(run,1)==1 else "%d times"%hist.get(run,1),
                worst_run_r=d['worst_run_r'], worst_trade_r=d['worst_trade_r'],
                deposit=ctx.DEPOSIT)

def qblock():
    """The quarters box used to be typed by hand and went stale (Q3 read +13.6 R
    after it had fallen). Generated from the same numbers as the table."""
    qs=d['quarters']; pos=[q for q in qs if q['total']>0]
    QL=d.get('qlabel') or "quarter"
    title=("Every %s positive"%QL) if len(pos)==len(qs) else "%d of %d %ss positive"%(len(pos),len(qs),QL)
    body=", ".join("%s <b>%+.1f R</b>"%(q['q'],q['total']) for q in qs)
    return '<div class="%s"><div class="t">%s</div><p>%s.</p></div>'%("good" if len(pos)==len(qs) else "note",title,body)

def runprose():
    run=d['streaks']['worst_loss']; times=dict((k,n) for k,n in d['streaks']['loss_hist']).get(run,1)
    cost=run*RISK; lim=ctx.BENCH['maxloss']
    vs=("the whole limit" if abs(cost-lim)<0.05 else
        "past the %g%% limit"%lim if cost>lim else "%g points inside the %g%% limit"%(round(lim-cost,2),lim))
    return ('A <strong>%d-loss run happened %s</strong>, and at %s risk it costs %g%% — %s.'
            %(run,"once" if times==1 else "%d times"%times,ctx.RISK_TXT,round(cost,1),vs))

tpl=open(os.path.join(ctx.RESEARCH, "template.html")).read()
def minus(x):
    """A real minus sign, U+2212 -- the template used one and a hyphen reads wrong
    beside it."""
    return ("%g" % x).replace("-", "\u2212")

MOVE_AT = float(ctx.SPEC["rules"]["stop_move_at_r"])
MOVE_TO = float(ctx.SPEC["rules"]["stop_move_to_r"])
MOVES   = MOVE_AT > 0

def settings_rows():
    """The EA inputs this spec actually emits. The table used to be typed out --
    Asia's twelve values, printed under every report, including one whose stop
    never moves and whose target is 3R."""
    inp = S.inputs(ctx.SPEC)
    tz  = next(k for k, v in S.TZ.items() if v == inp["InpTimeZone"])
    tf  = next(k for k, v in S.TF.items() if v == inp["InpSignalTF"])
    dirn = {"both": "either direction", "long": "upside breaks only",
            "short": "downside breaks only"}[ctx.DIRECTION]
    rows = [
        ("InpTimeZone", "TZ_%s" % tz.upper(), "session clock"),
        ("InpStartHour / Minute", "%d / %d" % (inp["InpStartHour"], inp["InpStartMinute"]), ctx.OPEN_TXT),
        ("InpRangeMinutes", inp["InpRangeMinutes"], "range length, so the box closes %s" % ctx.LAST_CANDLE),
        ("InpSignalTF", tf, "confirmation candle"),
        ("InpNoEntryAfterMin", inp["InpNoEntryAfterMin"], "stop looking at %s" % ctx.ENTRY_LAST),
        ("InpMinClosePos", "%.2f" % inp["InpMinClosePos"] if ctx.HALF_FILTER else "0",
         "trade only the half it closed in" if ctx.HALF_FILTER else "off — either half may break"),
        ("InpTradeLongs / Shorts", "%s / %s" % (inp["InpTradeLongs"], inp["InpTradeShorts"]), dirn),
        ("InpSLPercentOfRange", "%g" % inp["InpSLPercentOfRange"],
         "stop at the midpoint" if inp["InpSLPercentOfRange"] == 50 else "stop at %g%% of the range"
         % inp["InpSLPercentOfRange"]),
        ("InpRR", "%g" % ctx.RR, "target"),
        ("InpStopMoveAtR / ToR", "%s / %s" % (minus(MOVE_AT), minus(MOVE_TO)),
         "the stop move" if MOVES else "off — the stop never moves"),
        ("InpMaxHoldMinutes", HOLD, "time cap"),
        ("InpTradeFri", inp["InpTradeFri"], "Fridays traded" if inp["InpTradeFri"] == "true" else "Fridays off"),
        ("InpRiskPercent", "%g" % ctx.RISK, "risk per trade"),
    ]
    return "".join("<tr><td><code>%s</code></td><td><b>%s</b></td><td>%s</td></tr>" % r for r in rows)

def stop_section():
    """Section 03. The drawn-to-scale diagram belongs to a spec that moves its
    stop; the exits table below it belongs to every spec, and dropping it with
    the diagram lost "How the N trades ended" from the 05:30 report."""
    lib = os.path.join(ctx.RESEARCH, "lib")
    exits = open(os.path.join(lib, "exits_block.html")).read()
    if MOVES:
        return open(os.path.join(lib, "stop_section.html")).read() + "\n" + exits
    return (('<section id="stop">\n<h2><span class="num">03</span>The stop move</h2>\n'
            '<p class="sub">There isn\'t one. <code>InpStopMoveAtR</code> is <b>0</b> on this '
            'configuration: the stop is placed once at the range midpoint and stays there until '
            'the trade hits it, reaches the %s target, or runs out of time.</p>\n'
            '<p>So every loss here is a full <b>1R</b> — %d of %d, with none halved. '
            'The published Asia configuration moves the stop to &minus;0.5R once a trade is '
            '+0.5R up, which is why its losing runs cost less than a run of full stops. '
            'That protection is not present here, and the losing-run table below is not '
            'discounted for it. Section 04 gives the measured reason the move is off.</p>\n'
            % (ctx.RR_TXT, d["losses"]["n"], d["losses"]["n"])) + exits)

def rules_block():
    """The schematic when it depicts this spec, otherwise a table that does.

    rules_svg is drawn by hand for a 15-candle range, a 2R target and a 90-minute
    cap. Under a spec with different geometry it showed the wrong strategy, so it
    now returns "" and this fills in from the spec instead."""
    svg = rules_svg.build()
    if svg:
        return svg
    rows = [
        ("Range", "%s, the %s M1 candles from %s" % (ctx.OPEN_TXT, ctx.RANGE_WORD, ctx.RANGE_TXT)),
        ("Break confirmed on", "a closing %s candle beyond the box" % ctx.SIGNAL_TF),
        ("Half filter", "only the half the %s candle closed in" % ctx.LAST_CANDLE
                        if ctx.HALF_FILTER else "off — either half may break"),
        ("Direction", {"both": "either way", "long": "upward breaks only",
                       "short": "downward breaks only"}[ctx.DIRECTION]),
        ("Entries", "from %s until %s, then the day is done" % (ctx.BOX_DONE, ctx.ENTRY_LAST)),
        ("Stop", "%g%% of the range from the broken edge" % ctx.SPEC["rules"]["sl_pct_of_range"]),
        ("Target", "%s from entry" % ctx.RR_TXT),
        ("Stop management", "at +%gR the stop moves to %gR" % (ctx.SPEC["rules"]["stop_move_at_r"],
                                                               ctx.SPEC["rules"]["stop_move_to_r"])
                            if ctx.SPEC["rules"]["stop_move_at_r"] else "none — the stop never moves"),
        ("Time cap", "flat %d minutes after entry" % HOLD),
        ("Days", "%s, one trade a day" % ctx.DAYS_TXT),
    ]
    return ('<div class="scroll"><table><caption>The rules, read from the spec that '
            'produced this report</caption><tbody>'
            + "".join("<tr><td><b>%s</b></td><td>%s</td></tr>" % r for r in rows)
            + '</tbody></table></div>')

def why_rows():
    """The reasoning table. Rows come from the spec that measured them; a spec
    with none says so rather than inheriting another strategy's argument."""
    if ctx.WHY:
        return "".join("<tr><td><b>%s</b></td><td>%s</td></tr>" % (a, b) for a, b in ctx.WHY)
    return ("<tr><td colspan=\"2\">This configuration carries no per-rule reasoning. "
            "It was selected by a parameter search, so each setting is a measured "
            "result rather than an argument &mdash; read the numbers below and the "
            "evidence note in section 01.</td></tr>")

html=(tpl
 .replace("{{WHYROWS}}", why_rows())
 .replace("{{SETTINGS}}", settings_rows())
 .replace("{{STOPSECTION}}", stop_section())
 .replace("{{LOSSNOTE}}", ("%d of %d halved by the stop move" % (d["losses"]["halved"], d["losses"]["n"]))
                          if MOVES else "every one a full 1R — the stop never moves")
 .replace("{{STOPRULE}}", ("<li><b>At +%gR, move the stop to %sR</b><span>Once the trade is that far "
                           "toward target, pull the stop so the worst case is a part loss instead of a "
                           "full one. Once only — it never moves again.</span></li>" % (MOVE_AT, minus(MOVE_TO)))
                          if MOVES else
                          "<li><b>The stop never moves</b><span>Set once at the range midpoint and left "
                          "there. Every loss is a full 1R.</span></li>")
 .replace("{{RUNCAPTION}}", (" &mdash; the stop move halves some losses, so averaging them understates "
                             "the run that matters.") if MOVES else
                            " &mdash; every loss here is a full stop, since the stop never moves.")
 .replace("{{MOVEDCLAUSE}}", " where the stop moved to," if MOVES else "")
 .replace("{{TRADES}}",str(H['trades'])).replace("{{WINS}}",str(wins)).replace("{{LOSSES}}",str(losses))
 .replace("{{WR}}","%.1f"%H['wr']).replace("{{EV}}","%+.3f"%H['ev']).replace("{{SE}}","%.3f"%H['se'])
 .replace("{{TOTALR}}","%+.1f"%H['total'])
 .replace("{{RET}}",'<span data-pct="%.4f" data-fmt="signint"></span>'%H['total'])
 .replace("{{SD}}","%.2f"%H['sd']).replace("{{SESSIONS}}",str(H['sessions']))
 .replace("{{MAXDD}}",'<span data-sweep="maxdd"></span>')
 .replace("{{WORSTRUN}}",str(d['streaks']['worst_loss']))
 .replace("{{BESTRUN}}",str(d['streaks']['best_win']))
 .replace("{{PASS2}}",'<span data-sweep="pass_pct"></span>')
 .replace("{{DAYS2}}",'<span data-sweep="days"></span>')
 .replace("{{CURVE}}",curve_svg(d['curve'], RISK))
 .replace("{{WEEKROWS}}",weeks_rows()).replace("{{QROWS}}",q_rows())
 .replace("{{MROWS}}",m_rows()).replace("{{EXITROWS}}",exit_rows())
 .replace("{{SWEEPROWS}}",sweep_rows()).replace("{{STREAKROWS}}",streak_rows())
 .replace("{{HALFROWS}}",half_rows())
 .replace("{{RULESSVG}}",rules_block())
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
 .replace("{{NTARGET}}","%d"%next(e["n"] for e in d["exits"] if e["kind"]=="target"))
 .replace("{{NSTOP}}","%d"%next(e["n"] for e in d["exits"] if e["kind"]=="stop"))
 .replace("{{SELFPCT}}","%.0f%%"%(100.0*(H["trades"]-next(e["n"] for e in d["exits"] if e["kind"]=="time cap"))/H["trades"]))
 .replace("{{HOLD}}","%d"%HOLD)
 .replace("{{PF}}","%.2f"%H["pf"])
 .replace("{{AVGWIN}}","%+.2f"%(H["gain"]/H["wins"]))
 .replace("{{AVGLOSS}}","%+.2f"%(H["loss"]/(H["trades"]-H["wins"])))
 .replace("{{BESTWIN}}","%d"%d["streaks"]["best_win"])
 .replace("{{WORSTLOSS}}","%d"%d["streaks"]["worst_loss"])
 .replace("{{WORSTLOSSPCT}}",'<span data-sweep="run_cost" data-fmt="plain1"></span>')
 .replace("{{GAIN}}","%+.1f"%H["gain"]).replace("{{LOSS}}","%.1f"%abs(H["loss"]))
 .replace("{{LASTDATE}}",dt.date.fromisoformat(d["coverage"]["last"]).strftime("%d %B %Y")).replace("{{GALLERY}}",gallery()).replace("{{FILTERS}}",filters())

 .replace("{{GENERATED}}", dt.date.today().isoformat())
 .replace("{{TITLE}}", ctx.TITLE or ctx.H1)
 .replace("{{RISKPCT}}", ctx.RISK_TXT).replace("{{RRTXT}}", ctx.RR_TXT).replace("{{RRWORD}}", ctx.RR_WORD)
 .replace("{{HOLDMIN}}", str(HOLD)).replace("{{PERIOD}}", ctx.PERIOD)
 .replace("{{MAXLOSS}}", "%g" % ctx.BENCH["maxloss"]).replace("{{BENCHTEXT}}", ctx.BENCH["text"])
 .replace("{{DEPOSIT}}", "$%s" % format(int(ctx.DEPOSIT), ",")).replace("{{RISKMONEY}}", "$%s" % format(int(round(ctx.RISK_MONEY)), ","))
 .replace("{{QBLOCK}}", qblock()).replace("{{RUNPROSE}}", runprose())
 .replace("{{MCSVG}}", mc_svg(RISK))
 .replace("{{EVR}}", "%.4f" % H["ev"])
 .replace("{{RISKNUM}}", "%g" % ctx.RISK)
 .replace("{{QLABEL}}", (d.get('qlabel') or "quarter").capitalize())
 .replace("{{QLABEL2}}", d.get('qlabel') or "quarter")
 .replace("{{H1}}", ctx.H1).replace("{{H1EM}}", ctx.H1_EM)
 .replace("{{LEDE}}", ctx.LEDE).replace("{{SHORT}}", ctx.SHORT)
 .replace("{{RANGEMIN}}", ctx.RANGE_WORD).replace("{{RANGETXT}}", ctx.RANGE_TXT)
 .replace("{{LASTCANDLE}}", ctx.LAST_CANDLE).replace("{{BOXDONE}}", ctx.BOX_DONE)
 .replace("{{DAYSTXT}}", ctx.DAYS_TXT).replace("{{DAYSSHORT}}", ctx.DAYS_DASH)
 .replace("{{OFFDAYS}}", ctx.OFF_TXT).replace("{{NDAYS}}", ctx.NDAYS_WORD)
 .replace("{{DAILY}}", "%g" % (ctx.BENCH["daily"] or 0))
 .replace("{{TARGET}}", "%g" % ctx.BENCH["p1"])
 .replace("{{CLIFFLOSS}}", "%g" % (d["cliffs"]["maxloss"] or 0))
 .replace("{{CLIFFDAILY}}", "%g" % (d["cliffs"]["daily"] or 0))
 .replace("{{LSAVEDR}}", "%.4f" % d["losses"]["saved"])
 .replace("{{PHASETXT}}", "one phase" if not ctx.BENCH["p2"] else "both phases")
 .replace("{{RISKDATA}}", json.dumps(riskdata(), separators=(",", ":"))))
# Fill every live span with its value at the default risk. The page overwrites
# these on load, so they only show when JavaScript does not run -- on GitHub
# Pages with JS off, in print, in a reader view. A blank report is worse than a
# report at one fixed risk, and the numbers are the same ones the script writes.
def fill_defaults(html):
    row = next(s for s in d['sweep'] if abs(s['risk'] - RISK) < 1e-9)
    def f(v, k):
        if k == 'signint': return "%+d" % round(v)
        if k == 'int':     return "%d" % round(v)
        if k == 'money':   return "$%s" % format(int(round(v)), ",")
        if k == 'lots':    return "%.2f" % (v / 500.0)
        if k == 'plain1':  return "%.1f" % v
        if k == 'plain2':  return "%.2f" % v
        return "%+.1f" % v
    def pct(m):
        return '%s%s</span>' % (m.group(0)[:-len('</span>')], f(float(m.group(1)) * RISK, m.group(2) or ''))
    def swp(m):
        v = row[m.group(1)]
        txt = f(v, m.group(2)) if m.group(2) else str(v)
        return '%s%s</span>' % (m.group(0)[:-len('</span>')], txt)
    html = re.sub(r'<span data-pct="([-\d.]+)"(?: data-fmt="(\w+)")?></span>', pct, html)
    html = re.sub(r'<span data-sweep="(\w+)"(?: data-fmt="(\w+)")?></span>', swp, html)
    html = html.replace('<span data-risk></span>', '<span data-risk>%g%%</span>' % RISK)
    return html

def fill_warning(html):
    """Server-render the banner at the default risk. Left to the script it is
    hidden and empty in the file, so with JS off -- or in print, or to a crawler
    -- the finding that the worst run breaks the limit at the default risk would
    be invisible. That is the one thing the page exists to say."""
    row = next(s for s in d['sweep'] if abs(s['risk'] - RISK) < 1e-9)
    daily = ctx.BENCH['daily'] or 0
    bad = []
    if row['run_breaks']:
        bad.append('A run of <b>%d losses</b> costs <b>%.1f%%</b>, past the %g%% maximum loss. '
                   'That run is in this data.'
                   % (d['streaks']['worst_loss'], row['run_cost'], ctx.BENCH['maxloss']))
    if daily and abs(row['worst_trade']) > daily:
        bad.append('The worst single loss on record is <b>%.2f%%</b>, past the %g%% daily limit '
                   '&mdash; one trade could end it.' % (abs(row['worst_trade']), daily))
    if not bad:
        return html
    return html.replace('<div id="riskwarn" class="riskwarn" hidden></div>',
                        '<div id="riskwarn" class="riskwarn">%s</div>' % " ".join(bad))

html = fill_warning(fill_defaults(html))
open(PAGES,"w").write(html)

# The charts are drawn straight into the folder the page links to, so there is
# nothing to copy. That copy step is why every chart existed twice.
print("wrote %s  (%.0f KB)" % (PAGES, os.path.getsize(PAGES)/1024))
