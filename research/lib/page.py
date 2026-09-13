"""The chrome every published page shares: the stylesheet link, the site nav,
the risk selector and the document shell.

There is exactly one stylesheet (`site.css` at the repo root) and exactly one
definition of the nav. A generated page that wants a rule adds it to site.css,
never to its own head -- two pages that look different should differ in markup,
not in CSS.

`build_report.py` renders `template.html` and fills `{{SITENAV}}` from here.
`fade_page.py` builds its whole document from `shell()`. Both end up with the
same head, the same nav and the same stylesheet.
"""

STYLESHEET = "site.css"

# One list, in the order the pages should be read: the overview, then each edge.
PAGES = (
    ("index.html",  "All three"),
    ("orb.html",    "ORB Asia"),
    ("pdfade.html", "Gold PD fade"),
    ("nqfade.html", "NQ range fade"),
)


def navbar(current):
    """The site nav, with `current` marked. Pass the page's own filename."""
    return '<nav class="site">' + "".join(
        '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == current else "", label)
        for href, label in PAGES) + "</nav>"


def riskbar(default=2.5, note=None):
    """The risk-per-trade selector.

    Same markup as template.html's, so the control looks identical on every
    page. The ORB report adds chips and a cliff warning on top, because it has
    a precomputed pass-rate sweep to drive them; the fades do not."""
    return """<div class="riskbar">
    <label for="riskin">Risk per trade</label>
    <div class="riskin"><input id="riskin" type="number" min="0.25" max="10" step="0.25"
      value="%g" inputmode="decimal" aria-label="Risk per trade, percent"><span>%%</span></div>
    <p class="risknote">%s</p>
  </div>""" % (default, note or ("Every percentage here is <b>R &times; risk</b>. "
                                "R values, win rate and profit factor do not move."))


# Percentages are rendered server-side at the default risk, so a reader with no
# JavaScript still gets a real report rather than blanks.
RISK_JS = """
var RISK=%(risk)g;
function paint(){
  document.querySelectorAll('[data-pct]').forEach(function(e){
    var r=parseFloat(e.dataset.pct), f=e.dataset.fmt, v=r*RISK;
    if(f==='int') e.textContent=Math.round(v)+'%%';
    else if(f==='signint') e.textContent='  '+(v>=0?'+':'')+Math.round(v)+'%%';
    else e.textContent=(v>=0?'+':'')+v.toFixed(1);
  });
}
var sl=document.getElementById('riskin');
if(sl){sl.addEventListener('input',function(){
  var v=parseFloat(sl.value);
  if(isFinite(v)&&v>0){RISK=v;paint();}   // a half-typed number must not blank the page
});}
paint();
"""

# The trade gallery's filter chips. Any page with a .gal and .chip buttons gets
# this behaviour for free.
GALLERY_JS = """
var F={outcome:null,dir:null,month:null};
function filter(){
  var n=0;
  document.querySelectorAll('.tc').forEach(function(c){
    var ok=(!F.outcome||c.dataset.outcome===F.outcome)&&
           (!F.dir||c.dataset.dir===F.dir)&&(!F.month||c.dataset.month===F.month);
    c.hidden=!ok; if(ok)n++;
  });
  var fc=document.getElementById('fcount'); if(fc)fc.textContent=n+(n===1?' trade':' trades');
  var nr=document.getElementById('noresult'); if(nr)nr.hidden=n>0;
}
document.querySelectorAll('.chip').forEach(function(b){
  b.addEventListener('click',function(){
    var k=b.dataset.f,v=b.dataset.v,on=F[k]===v;
    document.querySelectorAll('.chip[data-f="'+k+'"]').forEach(function(o){
      o.setAttribute('aria-pressed','false');});
    F[k]=on?null:v; if(!on)b.setAttribute('aria-pressed','true');
    filter();
  });
});
filter();
"""

FOOTER = ('<footer><p>Generated from the run — no figure on this page is typed by hand. '
          '2026 only, and the limits each page states are the ones that matter. '
          'Not financial advice.</p></footer>')


def shell(title, current, body, risk=2.5, gallery=True):
    """A complete document: shared head, shared nav, the page's body, shared JS."""
    js = RISK_JS % dict(risk=risk) + (GALLERY_JS if gallery else "")
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<link rel="stylesheet" href="%s">
</head><body><div class="wrap">
%s
%s
%s
</div>
<script>%s</script>
</body></html>
""" % (title, STYLESHEET, navbar(current), body, FOOTER, js)
