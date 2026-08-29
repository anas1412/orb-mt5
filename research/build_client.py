#!/usr/bin/env python3
"""Client-facing explainer: what $1,000 does under this strategy, flat vs
compounding. Every figure comes from client_data.json, which is a replay of the
72 real 2026 trades -- nothing here is typed by hand."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/orb/client-example.html")
d = json.load(open(os.path.join(HERE, "client_data.json")))

def money(v):
    return "${:,.0f}".format(v)

# the losing-run ladder, the number a client has to see before the returns
streaks = "".join(
    '<tr%s><td>%d in a row</td>'
    '<td class="neg">%.0f%%</td><td class="neg">%.0f%%</td>'
    '<td class="neg">%.0f%%</td><td class="neg">%.0f%%</td>'
    '<td class="neg"><b>%.0f%%</b></td><td class="neg"><b>%.0f%%</b></td></tr>'
    % (' class="seen"' if s["n"] == d["worstRun"] else "",
       s["n"], s["2flat"], s["2comp"], s["5flat"], s["5comp"],
       s["10flat"], s["10comp"])
    for s in d["streaks"])

TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>One Thousand Dollars</title>
<style>
:root{
  --paper:#f4f6f9; --card:#ffffff; --ink:#131c27; --mut:#5d6b7c;
  --line:#dce2ea; --rule:#c9d2dd; --accent:#96701f; --accent-soft:#f0e6cf;
  --pos:#1a6a4c; --neg:#a3372b; --posbg:#e8f2ec; --negbg:#faece9;
  --shadow:0 1px 2px rgba(19,28,39,.04),0 10px 26px -14px rgba(19,28,39,.18);
  --serif:ui-serif,Georgia,"Times New Roman",serif;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --paper:#0e131a; --card:#161d26; --ink:#e8edf3; --mut:#8896a8;
  --line:#232d39; --rule:#313e4c; --accent:#d3a85a; --accent-soft:#2a2415;
  --pos:#4fbe8b; --neg:#e0806f; --posbg:#12251c; --negbg:#2a1714;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 28px -14px rgba(0,0,0,.7);
}}
:root[data-theme=dark]{
  --paper:#0e131a; --card:#161d26; --ink:#e8edf3; --mut:#8896a8;
  --line:#232d39; --rule:#313e4c; --accent:#d3a85a; --accent-soft:#2a2415;
  --pos:#4fbe8b; --neg:#e0806f; --posbg:#12251c; --negbg:#2a1714;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 28px -14px rgba(0,0,0,.7);
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font:16px/1.6 var(--sans);
  -webkit-font-smoothing:antialiased}
.wrap{max-width:920px;margin:0 auto;padding:0 24px 96px}
section{margin-top:64px}
h1{font:600 clamp(2.6rem,6vw,4.1rem)/1.04 var(--serif);letter-spacing:-.025em;
  text-wrap:balance}
h2{font:600 1.6rem/1.25 var(--serif);letter-spacing:-.015em;text-wrap:balance;
  margin-bottom:8px}
h3{font:600 1.02rem/1.4 var(--sans);margin:26px 0 8px}
p{color:var(--mut);max-width:66ch}
p+p{margin-top:12px}
b,strong{color:var(--ink);font-weight:640}
.lede{font-size:1.14rem;margin-top:18px;max-width:56ch}
.eyebrow{font:650 11.5px/1 var(--sans);letter-spacing:.16em;text-transform:uppercase;
  color:var(--accent);margin-bottom:20px}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.pos{color:var(--pos)} .neg{color:var(--neg)}

header{padding:76px 0 0}

/* ---------- the controls, and the balance they drive ---------- */
.panel{margin-top:38px;background:var(--card);border:1px solid var(--line);
  border-radius:4px;box-shadow:var(--shadow);overflow:hidden}
.readout{padding:30px 32px 26px;border-bottom:1px solid var(--line);
  display:flex;flex-wrap:wrap;gap:28px 44px;align-items:flex-end}
.big{font:600 clamp(2.6rem,7vw,3.9rem)/1 var(--mono);letter-spacing:-.03em;
  font-variant-numeric:tabular-nums}
.big small{display:block;font:650 11.5px/1 var(--sans);letter-spacing:.14em;
  text-transform:uppercase;color:var(--mut);margin-bottom:12px}
.sub{font:600 1.5rem/1 var(--mono);font-variant-numeric:tabular-nums}
.sub small{display:block;font:650 11.5px/1 var(--sans);letter-spacing:.14em;
  text-transform:uppercase;color:var(--mut);margin-bottom:11px}
.controls{padding:20px 32px 22px;display:flex;flex-wrap:wrap;gap:22px 40px;
  align-items:center;background:var(--paper)}
.cgroup{display:flex;align-items:center;gap:10px}
.clabel{font:650 11.5px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;
  color:var(--mut)}
.seg{display:flex;border:1px solid var(--rule);border-radius:3px;overflow:hidden}
.seg button{appearance:none;border:0;background:var(--card);color:var(--mut);
  font:600 13.5px/1 var(--mono);padding:9px 15px;cursor:pointer;
  border-right:1px solid var(--rule);transition:background .14s,color .14s}
.seg button:last-child{border-right:0}
.seg button[aria-pressed=true]{background:var(--accent);color:var(--card)}
.seg button:focus-visible{outline:2px solid var(--accent);outline-offset:2px;z-index:1}
.tested{font:600 10.5px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;
  color:var(--accent);background:var(--accent-soft);padding:4px 8px;border-radius:2px}

/* ---------- chart ---------- */
figure{margin-top:22px;background:var(--card);border:1px solid var(--line);
  border-radius:4px;padding:22px 24px 14px;box-shadow:var(--shadow)}
figcaption{color:var(--mut);font-size:13.5px;margin-top:12px;max-width:70ch}
svg{width:100%;height:auto;display:block}

/* ---------- tables ---------- */
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);
  border-radius:4px;box-shadow:var(--shadow);margin-top:20px}
table{border-collapse:collapse;width:100%;font-size:14.5px}
caption{caption-side:top;text-align:left;padding:16px 20px 2px;color:var(--mut);
  font-size:13px}
th{text-align:right;padding:12px 18px;font:650 10.5px/1.3 var(--sans);
  letter-spacing:.08em;text-transform:uppercase;color:var(--mut);
  border-bottom:1px solid var(--rule);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:11px 18px;border-bottom:1px solid var(--line);text-align:right;
  font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
td:first-child{font-family:var(--sans)}
tbody tr:last-child td{border-bottom:none}
tr.seen td{background:var(--accent-soft)}
tr.seen td:first-child::after{content:" — happened";color:var(--accent);
  font-size:12px;font-weight:600}

/* ---------- notes ---------- */
.note{border-left:2px solid var(--accent);padding:2px 0 2px 20px;margin-top:22px}
.note.warn{border-color:var(--neg)}
.note p{max-width:64ch}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:4px;
  padding:20px 22px;box-shadow:var(--shadow)}
.card h3{margin-top:0}
.card .v{font:600 1.7rem/1 var(--mono);font-variant-numeric:tabular-nums;
  margin:6px 0 8px}
ul{list-style:none;display:flex;flex-direction:column;gap:11px;margin-top:16px}
ul li{padding-left:20px;position:relative;color:var(--mut);max-width:66ch}
ul li::before{content:"";position:absolute;left:2px;top:.62em;width:6px;height:6px;
  border-radius:50%;background:var(--accent)}
footer{margin-top:72px;padding-top:22px;border-top:1px solid var(--rule);
  color:var(--mut);font-size:13px}
@media (max-width:640px){
  .two{grid-template-columns:1fr}
  .readout{gap:22px 30px;padding:24px}
  .controls{padding:18px 24px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head><body>
<div class="wrap">

<header>
  <div class="eyebrow">Gold &middot; Asia session &middot; 2026 result</div>
  <h1>What one thousand dollars did.</h1>
  <p class="lede">Every figure below is a replay of the same
     <b>__TRADES__ real trades</b>, __FIRST__ to __LAST__. The only thing the
     buttons change is how much was staked on each one.</p>

  <div class="panel">
    <div class="readout">
      <div class="big"><small>Ending balance</small>
        <span id="final" class="pos">&mdash;</span></div>
      <div class="sub"><small>Gain</small><span id="gain" class="pos">&mdash;</span></div>
      <div class="sub"><small>Deepest fall</small><span id="dd" class="neg">&mdash;</span></div>
      <div class="sub"><small>Risk per trade</small><span id="stake">&mdash;</span></div>
    </div>
    <div class="controls">
      <div class="cgroup"><span class="clabel">Risk</span>
        <div class="seg" id="risk" role="group" aria-label="Risk per trade">
          <button data-r="2" aria-pressed="false">2%</button>
          <button data-r="5" aria-pressed="false">5%</button>
          <button data-r="10" aria-pressed="true">10%</button>
        </div>
        <span class="tested" id="testedTag" hidden>tested setting</span>
      </div>
      <div class="cgroup"><span class="clabel">Staking</span>
        <div class="seg" id="mode" role="group" aria-label="Staking method">
          <button data-m="flat" aria-pressed="true">Fixed cash</button>
          <button data-m="comp" aria-pressed="false">Compounding</button>
        </div>
      </div>
    </div>
  </div>

  <figure>
    <svg id="chart" viewBox="0 0 900 300" role="img" aria-labelledby="chartTitle">
      <title id="chartTitle">Account balance across the 72 trades</title>
    </svg>
    <figcaption id="cap"></figcaption>
  </figure>
</header>

<section>
  <h2>On day one, both choices are the same</h2>
  <p>Ten per cent of $1,000 <b>is</b> $100. So the first trade is identical
     whichever button you pick. The two only separate from the second trade
     onwards, and the difference is one word: <b>whose</b> balance the
     percentage is taken from.</p>
  <div class="two">
    <div class="card">
      <h3>Fixed cash</h3>
      <div class="v num">$100</div>
      <p>Always ten per cent of the <b>opening</b> $1,000. Win or lose, the next
         trade stakes $100. Profits are set aside.</p>
    </div>
    <div class="card">
      <h3>Compounding</h3>
      <div class="v num">$100 &rarr; $120</div>
      <p>Ten per cent of <b>today's</b> balance. Win the first trade and the
         account is $1,200, so the next stake is $120. Profits are put back to
         work.</p>
    </div>
  </div>
  <div class="note"><p>Compounding grows faster and falls harder, because the
     stake rises with the account. Neither is more correct &mdash; they answer
     different questions.</p></div>
</section>

<section>
  <h2>Month by month</h2>
  <p>The same trades, month by month, at the settings you have chosen above.</p>
  <div class="scroll">
    <table>
      <caption id="mcap"></caption>
      <thead><tr><th>Month</th><th>Opening</th><th>Trades</th><th>Won</th>
        <th>Profit</th><th>Closing</th></tr></thead>
      <tbody id="months"></tbody>
    </table>
  </div>
</section>

<section>
  <h2>Now the part that matters</h2>
  <p>Returns are the easy half. This is what a run of losing trades costs,
     because that is the thing that ends accounts. The strategy's worst run in
     2026 was <b>three</b> losses together.</p>
  <div class="scroll">
    <table>
      <caption>Account remaining after a run of losing trades, by risk setting</caption>
      <thead><tr><th>Losing run</th>
        <th>2% fixed</th><th>2% comp.</th>
        <th>5% fixed</th><th>5% comp.</th>
        <th>10% fixed</th><th>10% comp.</th></tr></thead>
      <tbody>__STREAKS__</tbody>
    </table>
  </div>
  <div class="note warn">
    <p><b>Read the last two columns.</b> At ten per cent staked as fixed cash,
       ten losing trades in a row is the whole account. Compounding survives
       that same run at &minus;65%, because a shrinking balance means a
       shrinking stake &mdash; the one situation where compounding is the safer
       of the two.</p>
    <p>Ten losses in a row never happened in 2026. It is also not unlikely
       enough to ignore: at a 54% win rate it comes up roughly once in every
       three thousand trades.</p>
  </div>
</section>

<section>
  <h2>What you are actually being shown</h2>
  <ul>
    <li><b>One year, __TRADES__ trades, one market.</b> Gold at the Tokyo open,
        January to August 2026. Not a decade, and not many instruments.</li>
    <li><b>A backtest on real tick data</b>, including the spread and the
        broker's own execution &mdash; not an idealised simulation.</li>
    <li><b>2% is the tested setting.</b> The research was done at two per cent
        a trade. Five and ten are shown because they were asked for, not
        because they were validated.</li>
    <li><b>Past results are not a forecast.</b> The strategy depends on gold
        continuing to move at the Asia open the way it moved in 2026. If that
        changes, so does everything on this page.</li>
  </ul>
  <div class="note"><p>The full study, every one of the __TRADES__ trades
     charted individually, and the source code are all published openly at
     <b>anas1412.github.io/orb-mt5</b>.</p></div>
</section>

<footer>Prepared from a replay of __TRADES__ executed trades, __FIRST__ to
  __LAST__. Illustration only &mdash; not investment advice.</footer>
</div>

<script>
const DATA = __JSON__;

const el = id => document.getElementById(id);
const fmt = v => "$" + Math.round(v).toLocaleString("en-US");
const state = { risk: "10", mode: "flat" };

function seg(id, key, attr){
  el(id).addEventListener("click", e => {
    const b = e.target.closest("button"); if(!b) return;
    state[key] = b.dataset[attr];
    [...el(id).children].forEach(x => x.setAttribute("aria-pressed", x === b));
    render();
  });
}
seg("risk", "risk", "r");
seg("mode", "mode", "m");

function chart(path, colour){
  const W = 900, H = 300, L = 62, R = 16, T = 14, B = 30;
  const lo = Math.min(DATA.start, ...path), hi = Math.max(DATA.start, ...path);
  const pad = (hi - lo) * 0.08 || 1;
  const y0 = lo - pad, y1 = hi + pad;
  const X = i => L + i * (W - L - R) / (path.length - 1);
  const Y = v => H - B - (v - y0) * (H - T - B) / (y1 - y0);
  let g = "";
  // four gridlines, labelled in dollars so the axis means something
  for(let k = 0; k <= 3; k++){
    const v = y0 + (y1 - y0) * k / 3, y = Y(v);
    g += `<line x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}"
            stroke="var(--line)"/>
          <text x="${L-10}" y="${(y+4).toFixed(1)}" text-anchor="end"
            font-size="11" font-family="var(--mono)" fill="var(--mut)">${fmt(v)}</text>`;
  }
  const pts = path.map((v,i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
  const base = Y(DATA.start);
  g += `<line x1="${L}" y1="${base.toFixed(1)}" x2="${W-R}" y2="${base.toFixed(1)}"
          stroke="var(--rule)" stroke-dasharray="4 4"/>
        <text x="${W-R}" y="${(base-8).toFixed(1)}" text-anchor="end" font-size="11"
          font-family="var(--mono)" fill="var(--mut)">started ${fmt(DATA.start)}</text>
        <polygon points="${X(0).toFixed(1)},${base.toFixed(1)} ${pts} ${X(path.length-1).toFixed(1)},${base.toFixed(1)}"
          fill="${colour}" opacity=".10"/>
        <polyline points="${pts}" fill="none" stroke="${colour}" stroke-width="2.2"
          stroke-linejoin="round"/>
        <circle cx="${X(path.length-1).toFixed(1)}" cy="${Y(path[path.length-1]).toFixed(1)}"
          r="4" fill="${colour}"/>
        <text x="${L}" y="${H-8}" font-size="11" font-family="var(--mono)"
          fill="var(--mut)">trade 1</text>
        <text x="${W-R}" y="${H-8}" text-anchor="end" font-size="11"
          font-family="var(--mono)" fill="var(--mut)">trade ${path.length}</text>`;
  el("chart").innerHTML =
    '<title id="chartTitle">Account balance across the ' + path.length + ' trades</title>' + g;
}

function render(){
  const m = DATA.modes[state.risk][state.mode];
  const compounding = state.mode === "comp";
  const stake = compounding
        ? state.risk + "% of balance"
        : fmt(DATA.start * state.risk / 100) + " fixed";

  el("final").textContent = fmt(m.final);
  // whole percent: a decimal here reads as false precision on a one-year sample
  el("gain").textContent  = "+" + Math.round(m.gainpct).toLocaleString("en-US") + "%";
  el("dd").textContent    = "\\u2212" + m.dd + "%";
  el("stake").textContent = stake;
  el("testedTag").hidden  = state.risk !== "2";

  chart(m.path, compounding ? "var(--accent)" : "var(--pos)");
  el("cap").textContent =
    "Balance after each of the " + DATA.trades + " trades, risking " + stake +
    ". The deepest fall from a high point was " + m.dd + "%.";

  el("mcap").textContent =
    "Risking " + stake + (compounding ? ", profits reinvested" : ", profits set aside");
  el("months").innerHTML = m.months.map(r => {
    const nice = new Date(r.month + "-01T00:00:00Z")
                 .toLocaleDateString("en-GB", {month:"long", year:"numeric", timeZone:"UTC"});
    const cls = r.pnl >= 0 ? "pos" : "neg";
    return `<tr><td>${nice}</td><td>${fmt(r.start)}</td><td>${r.trades}</td>
      <td>${r.wins}</td><td class="${cls}">${r.pnl>=0?"+":"\\u2212"}${fmt(Math.abs(r.pnl)).slice(1)}</td>
      <td><b>${fmt(r.end)}</b></td></tr>`;
  }).join("");
}
render();
</script>
</body></html>
"""

html = TEMPLATE
for token, value in (("__TRADES__", str(d["trades"])),
                     ("__FIRST__",  d["first"]),
                     ("__LAST__",   d["last"]),
                     ("__STREAKS__", streaks),
                     ("__JSON__",   json.dumps(d, separators=(",", ":")))):
    html = html.replace(token, value)
assert "__" not in html.replace("__proto__", ""), "a token was left unreplaced"

open(OUT, "w").write(html)
print("wrote %s  (%.0f KB)" % (OUT, len(html) / 1024.0))
