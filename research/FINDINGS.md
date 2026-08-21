# ORB parameter study — 2026

Asia opening range on XAUUSD. Session 00:00 UTC, 15-minute range, M1 signal
bars, 15-minute entry window, 60-minute hold cap, 2% risk, one trade per day.

**All figures are 2026** (2026.01.01 – 2026.08.19, 163 trading days) unless a
table says otherwise. Rules: FundingPips 2-Step Standard — +8% then +5%, 10% max
total loss, 5% max daily loss, minimum 3 trading days per phase, no time limit.

Two sections necessarily reach beyond 2026, and both are marked with ⚠: §9 (the
kill switch) and the inversion note in §8. In both the comparison *is* the
finding — 2026 contains almost no quiet days, so it cannot teach you what a quiet
market does to this strategy.

---

## Current configuration

| Setting | Value |
|---|---|
| Session | 00:00 UTC (`TZ_UTC`, hour 0, minute 0) |
| Range | 15 minutes |
| Signal candle | M1 |
| Entry window | 15 minutes after the range closes |
| Stop loss | 50% of range (midpoint) |
| Target | 2.0 R |
| Stop move | at +0.5R, to −0.5R |
| Close-position filter | 0.25 |
| Max hold | 60 minutes |
| Risk | 2% |

**Result: +0.404 R per trade, 44.6% win rate, 86.6% chance of passing both
phases, median 19 trading days.** 112 trades.

---

## 1. Stop-loss placement

Fraction of the range, measured from the broken level. 0.5 is the midpoint, 1.0
the opposite boundary.

| SL fraction | EV | Win rate |
|---|---|---|
| 0.250 | +0.002 | 33.6% |
| 0.375 | +0.142 | 37.0% |
| **0.500 — midpoint** | **+0.362** | **44.5%** |
| 0.625 | +0.263 | 42.0% |
| 0.750 | +0.173 | 42.0% |
| 1.000 — far side | +0.138 | 43.7% |

**Answer: the midpoint.** More than double the far side.

**Tight stops are the clearest failure in the study.** A quarter-range stop
returns +0.002 — it sits inside normal noise, so it is taken out before the move
resolves and you pay full risk on a coin that never lands. The relationship is
monotone below 0.5 and there is no case for going tighter.

---

## 2. Reward to risk

| RR | SL 0.5 | SL 1.0 |
|---|---|---|
| 1.00 | +0.094 | +0.103 |
| 1.25 | +0.118 | +0.121 |
| 1.50 | +0.201 | +0.136 |
| 1.75 | +0.260 | +0.125 |
| **2.00** | **+0.362** | +0.138 |
| 2.50 | +0.333 | +0.193 |
| 3.00 | +0.316 | +0.185 |

**Answer: 2.0.** A clear peak at the midpoint stop, and the pass-rate optimum
sits at 1.75–2.0. On real ticks RR 2 is worth roughly **five times** RR 1:
+0.333 against +0.067.

RR 1 is the trap. It buys a 49.6% win rate and gives up most of the edge — a 2R
target needs price to travel one range-width, which in 2026 it routinely does.

---

## 3. Moving the stop

EV by trigger and destination. SL 0.5, RR 2.

| Trigger | to −0.5R | to −0.25R | to breakeven |
|---|---|---|---|
| never move | **+0.387** | — | — |
| +0.25R | +0.230 | +0.169 | **−0.234** |
| **+0.50R** | **+0.362** | +0.327 | +0.083 |
| +0.75R | +0.358 | +0.356 | +0.216 |
| +1.00R | +0.366 | +0.356 | +0.275 |

**Answer: trigger at +0.5R, move to −0.5R. Never to breakeven.**

**Breakeven is the most destructive setting tested.** At a +0.25R trigger it
turns +0.387 into −0.234 — profitable configuration into losing one. A breakeven
stop sits exactly where price retests after a breakout: you get stopped for
nothing on trades that would have worked, and you keep every full loss.

**Early triggers are worse than late ones** at every destination, because moving
early tightens the stop while the trade is still inside noise.

On pure EV, not moving wins (+0.387 against +0.362). The move costs ~0.005–0.02R
and buys about **5 points of pass rate** — 81.4% against 75.9%. See §5.

---

## 4. Range length and signal candle

MT5 real ticks. Entry window and hold cap scale with the range: 15/30/60 minute
window, 60/120/240 minute hold.

| Range / signal | n | Median range | EV | ±SE | WR | sd(R) | Pass both | Days |
|---|---|---|---|---|---|---|---|---|
| **15 min / M1** | 119 | 1 108 pts | **+0.333** | 0.127 | 42.0% | 1.39 | **81.0%** | **18** |
| 30 min / M3 | 124 | 1 502 | +0.007 | 0.110 | 32.3% | 1.22 | 33.5% | 25 |
| 60 min / M5 | 144 | 2 040 | +0.158 | 0.097 | 38.9% | 1.17 | 67.9% | 22 |

**Answer: 15 minutes with M1.** Bigger range does not mean better — the median
range grows 1108 → 1502 → 2040 while EV goes +0.333 → +0.007 → +0.158.

**Longer ranges are smoother but not better.** `sd(R)` falls steadily (1.39 →
1.22 → 1.17): wider ranges mean wider stops, so each trade is a smaller share of
the account. That smoothness costs more expectancy than it buys in pass rate.

Honest caveat: 30m/M3 landing *worst* rather than in the middle is probably
noise. The whole spread is about 1.5 standard errors wide, so treat the ranking
as directional.

---

## 5. Pass rate is not expectancy

Ranked by probability of passing both phases, 2% risk.

| SL | RR | Stop move | EV | WR | sd(R) | Pass both |
|---|---|---|---|---|---|---|
| 0.500 | 2.00 | +0.50 → −0.25 | +0.327 | 39.5% | 1.31 | **84.2%** |
| **0.500** | **2.00** | **+0.50 → −0.50** | **+0.362** | 44.5% | 1.37 | **84.1%** |
| 0.625 | 1.75 | +0.75 → −0.25 | +0.304 | 46.2% | 1.26 | 83.8% |
| 0.500 | 2.00 | never | **+0.387** | 49.6% | 1.49 | 80.7% |
| 0.250 | 2.00 | never | +0.116 | 42.9% | 1.49 | 47.9% |
| 0.250 | 3.00 | +0.50 → −0.50 | +0.128 | 27.7% | 1.69 | 43.3% |

**The highest-EV configuration ranks eleventh.** Turning the stop move off raises
EV to +0.387 and *lowers* pass rate to 80.7%. The reason is the `sd(R)` column:
1.37 against 1.49.

A challenge is a race between +8% and −10%, not a long-run expectancy game.
Variance reduction is worth more than the expectancy it costs, because the
drawdown barrier can end you before the edge has had time to express itself.

### Win rate matters more than it should

EV held constant at +0.24R, win size adjusted to compensate:

| Win rate | Win size | Pass both | Median trades |
|---|---|---|---|
| 20% | 3.20 R | 66.9% | 10 |
| 25% | 2.46 R | 77.6% | 11 |
| 30% | 1.97 R | 85.2% | 11 |
| 40% | 1.35 R | 95.2% | 14 |
| 50% | 0.98 R | 98.9% | 15 |
| 60% | 0.73 R | **99.8%** | 14 |

**Identical edge, and win rate alone moves pass rate from 67% to 99.8%.** Three
extra days buys ten points — an excellent trade when a failure costs a fee and a
restart.

But this only holds when the win rate comes **free**, from better entries. Buying
it by shortening the target is a bad trade: along the RR dial you give up more
edge than you gain in smoothness.

---

## 6. Entry cutoff and hold time

### When breaks happen

| Minutes after range close | Share | Cumulative |
|---|---|---|
| 0–5 | 39.2% | 39.2% |
| 5–10 | 20.2% | 59.4% |
| 10–15 | 11.5% | 70.9% |
| 15–20 | 8.4% | 79.3% |
| 20–30 | 9.1% | 88.4% |
| 30–60 | 10.4% | 98.8% |
| 60–120 | 1.2% | 100% |

### Entry cutoff

| Cutoff | Setups | EV |
|---|---|---|
| 5 min | 76 | +0.332 |
| 10 min | 106 | +0.367 |
| **15 min** | **119** | **+0.375** |
| 20 min | 127 | +0.330 |
| 30 min | 142 | +0.255 |
| 45 min | 154 | +0.201 |
| 60 min | 162 | +0.181 |

**A late breakout is a bad breakout.** The 29% of setups breaking after minute 15
are net harmful — including them drags EV from +0.375 to +0.181. A range that
takes half an hour to give way is drifting, not breaking. Cutting at 15 keeps 71%
of the opportunities and all of the edge.

### How long trades take

| Finishes in | Trades | Cumulative | Avg result |
|---|---|---|---|
| 0–15 min | 54 (45%) | 45% | −0.19 R |
| 15–30 min | 35 (29%) | 75% | +0.59 R |
| 30–45 min | 17 (14%) | 89% | +1.13 R |
| 45–60 min | 7 (6%) | **95%** | +1.22 R |
| 60–90 min | 2 (2%) | 97% | +1.91 R |
| over 2 hours | 4 (3%) | 100% | +0.66 R |

### Hold cap

| Hold | EV | Pass both | Trades cut short |
|---|---|---|---|
| 15 min | +0.118 | — | most |
| 30 min | +0.205 | — | many |
| 45 min | +0.334 | 83.4% | 12 (10%) |
| **60 min** | **+0.362** | **84.2%** | 7 (6%) |
| 90 min | +0.375 | 85.2% | 4 (3%) |
| 120 min | +0.373 | 85.0% | 4 (3%) |
| 180 min | +0.370 | 85.0% | 2 (2%) |

**95% of trades finish inside 60 minutes on their own**, so the cap barely acts.
Going 60 → 90 gains +0.013R from **two trades out of 119** — smaller than the
±0.05R error bar, so noise. 60 is the rounder rule. Do not go below it: 45 cuts
12 trades averaging +1.09 R.

Note the shape: fast trades lose (−0.19R in the first 15 minutes), slow trades
win (+1.13R at 30–45). A trade going nowhere quickly is a bad trade — but the cap
cannot exploit that, since you cannot know at minute five which is which.

### The one-minute shift

| Window | EV | WR | Pass |
|---|---|---|---|
| **range 00:00–00:14, entries 00:15–00:29** | **+0.362** | 44.5% | **84.2%** |
| range 00:00–00:15, entries 00:16–00:30 | +0.286 | 42.4% | 78.5% |
| range 00:00–00:15, entries 00:16–00:31 | +0.300 | 42.9% | 80.1% |

Folding the 00:15 bar into the range costs 0.076R and 6 points of pass rate.
Inside the error bar, but it points the same way as the timing data — the
earliest break is the best one, and this change makes it untradeable.

---

## 7. Sessions

The original plan assumed London carried the widest gold ranges, since the
London–New York overlap is gold's peak volume window. **Measured, that is wrong.**

| Session | Median 15-min range | As % of price | Median ticks | vs Asia |
|---|---|---|---|---|
| Asia 00:00 UTC | 1 141 pts | 0.247% | 2 852 | 1.00× |
| London 08:00 local | 910 | 0.205% | 2 765 | 0.80× range |
| New York 09:30 local | **1 630** | **0.364%** | **4 494** | 1.43× range |

**London is now the quietest of the three** — Asia has overtaken it on both range
and tick count, consistent with the 2026 rally being Asian and ETF-driven.

### But the edge does not follow the range

MT5 real ticks, each session given its own parameters.

| Session | RR | Stop move | n | EV | ±SE | WR | Pass both | Days |
|---|---|---|---|---|---|---|---|---|
| Asia | 1.0 | on | 119 | +0.067 | 0.088 | 49.6% | 55.1% | 36 |
| Asia | 1.0 | off | 119 | +0.073 | 0.094 | 53.8% | 54.6% | 33 |
| **Asia** | **2.0** | **on** | 119 | **+0.333** | 0.127 | 42.0% | **81.4%** | **18** |
| Asia | 2.0 | off | 119 | +0.338 | 0.136 | 47.1% | 75.9% | 16 |
| London | 1.0 | on | 117 | −0.173 | 0.083 | 36.8% | 3.8% | 31 |
| London | 1.0 | off | 117 | −0.186 | 0.091 | 41.9% | 5.1% | 26 |
| London | 2.0 | on | 117 | **−0.308** | 0.092 | 20.5% | 1.4% | 18 |
| London | 2.0 | off | 117 | **−0.317** | 0.106 | 27.4% | 2.6% | 18 |
| New York | 1.0 | on | 123 | −0.024 | 0.085 | 44.7% | 28.3% | 37 |
| New York | 1.0 | off | 123 | −0.016 | 0.089 | 48.0% | 31.1% | 33 |
| New York | 2.0 | on | 123 | −0.015 | 0.107 | 33.3% | 29.5% | 25 |
| New York | 2.0 | off | 123 | +0.006 | 0.114 | 40.7% | 33.2% | 24 |

Range length made no difference either — New York returns −0.015, −0.114 and
−0.056 at 15/30/60 minute ranges.

**London is dead in every configuration**, with a 20.5% win rate at RR 2 meaning
its opening range carries no directional information at all.

**New York has the widest ranges of any session and no edge.** That is the most
important negative result here: it kills the theory that range size alone
produces an edge. The likely mechanism is that the New York cash open is a
two-sided news spike whose range is violated in *both* directions, so the break
carries no information. **Wide range without directional persistence is whipsaw
with a bigger stop.**

Cost caveat: the same spread (52 points) was applied to every session, measured
at the Asia open. New York liquidity is deeper so its true spread is tighter,
meaning its result is flattered. It still has no edge.

DST note: London and New York anchor to their own local clocks with their own
switch dates. An earlier version of this test used fixed UTC hours — the summer
opens — which measured an hour before the real open for five months of the year
and flattered both sessions.

---

## 8. The close-position filter

**Rule:** at the moment the range closes, score how near price was to the side it
then breaks. Skip the trade if the score is too low.

```
score = (range_last_close − range_low) / (range_high − range_low)   for an up-break
score = 1 − that                                                    for a down-break
```

1.0 means the final range bar closed right against the boundary that broke — a
short journey, pressure already pointing that way. 0.0 means it closed at the
*opposite* boundary and had to traverse the whole range before breaking out.

**Mechanism.** A high score is continuation. A low score is a reversal wearing a
breakout's clothes: price flipped across the range first, and those flips tend to
keep flipping. Same failure that makes New York unusable.

Rejection ends the day rather than waiting for a break the other way. Deliberate:
the opposite break scores `1 − score` by construction, so allowing it would turn
every rejection into a coin flip on the other side.

### Quadrants

| Quadrant | n | Share | EV | ±SE | Win rate | Total R |
|---|---|---|---|---|---|---|
| **below 25%** | 7 | 5.9% | **−0.816** | 0.098 | **0.0%** | −5.71 |
| 25% – 50% | 19 | 16.0% | +0.217 | 0.317 | 36.8% | +4.12 |
| 50% – 75% | 25 | 21.0% | +0.210 | 0.260 | 36.0% | +5.24 |
| **above 75%** | 68 | 57.1% | **+0.529** | 0.173 | **50.0%** | +35.95 |

**Seven trades below 25%, and not one of them won.** The middle two quadrants are
indistinguishable from each other and both clearly worse than the top.

### Threshold sweep

MT5 real ticks.

| Min score | Trades | Kept | n | EV | ±SE | WR | Pass both | Days | Fees/pass |
|---|---|---|---|---|---|---|---|---|---|
| 0.00 off | 455 | 100% | 119 | +0.333 | 0.127 | 42.0% | 81.6% | **18** | 1.23 |
| 0.10 | 440 | 97% | 114 | +0.388 | 0.130 | 43.9% | 85.8% | 19 | 1.17 |
| 0.20 | 432 | 95% | 114 | +0.388 | 0.130 | 43.9% | 85.7% | 19 | 1.17 |
| **0.25** | **423** | **93%** | **112** | **+0.404** | 0.132 | **44.6%** | **86.6%** | **19** | **1.15** |
| 0.35 | 393 | 86% | 106 | +0.420 | 0.136 | 45.3% | 87.7% | 20 | 1.14 |
| 0.50 | 345 | 76% | 93 | +0.443 | 0.145 | 46.2% | 89.4% | 21 | 1.12 |
| 0.75 | 234 | 51% | 68 | +0.529 | 0.173 | 50.0% | 92.7% | 26 | 1.08 |

### Why 0.25 and not higher

The marginal cut at each step decides it:

| Step | Trades removed | Their average |
|---|---|---|
| 0.00 → 0.10 | 5 | **−0.938 R** |
| 0.20 → 0.25 | 2 | **−0.511 R** |
| 0.25 → 0.35 | 6 | +0.132 R |
| 0.35 → 0.50 | 13 | +0.256 R |
| 0.50 → 0.75 | 25 | +0.210 R |

**Everything below 0.25 is genuinely bad; everything above it is profitable.**
Seven trades in 119 account for the entire benefit.

Past 0.25 the pass rate keeps climbing to 92.7% — but only because you are taking
fewer trades. That buys a smoother ride by deleting winners, and costs seven extra
calendar days. Fees per pass improve by 0.07 across that whole stretch, which does
not cover it.

**Chosen: 0.25.** Removes the entire tail and nothing else.

| | Off | 0.25 |
|---|---|---|
| EV | +0.333 | **+0.404** |
| Win rate | 42.0% | **44.6%** |
| Pass both | 81.6% | **86.6%** |
| Attempts per pass | 1.23 | **1.15** |
| Days | 18 | 19 |

### ⚠ This filter is a regime bet

Tested on a choppy market instead of a trending one, the effect **inverts**:
below-25% becomes the *best* quadrant and above-75% turns negative — exactly
backwards from what 2026 shows.

That is mechanism, not noise. In a choppy market the range mean-reverts, so a
break *away* from where price sat pays. In a trending market the range is a pause
in a move, so a break *continuing* it pays.

**Consequence:** if the kill switch in §9 ever fires, this filter should be turned
off or inverted, not merely tolerated.

### Rejected candidates

Four others were tested and dropped: **break strength** (non-monotone buckets),
**trend alignment** against the 10-day drift (t = 0.85), **range efficiency**
(weak). A **volume filter** did survive — breaks on under 0.8× the range's median
tick count returned +0.080 against +0.389 — but was dropped as impractical to
judge in real time.

Testing five filters across roughly twenty buckets guarantees one looks good by
chance. What earns this one its place: the direction held in every sample tested,
and the mechanism states in a sentence.

---

## 9. ⚠ The kill switch — necessarily uses quiet-market data

**This is the one section that cannot be built from 2026.** Only 0.8% of 2026's
days had a range under 350 points, so 2026 contains no examples of the strategy
in a quiet market. Establishing where the edge dies requires days that 2026 does
not have.

Trades bucketed by absolute range size:

| 15-min range | n | EV | ±SE | WR | Verdict |
|---|---|---|---|---|---|
| under 200 pts | 106 | −0.213 | 0.114 | 24.5% | loses |
| 200–350 | 97 | −0.151 | 0.120 | 27.8% | loses |
| 350–500 | 46 | +0.052 | 0.187 | 34.8% | coin flip |
| 500–750 | 62 | −0.019 | 0.156 | 29.0% | coin flip |
| 750–1100 | 66 | +0.160 | 0.163 | 34.8% | coin flip |
| 1100–1600 | 45 | +0.230 | 0.196 | 40.0% | profitable |
| over 1600 | 32 | +0.440 | 0.246 | 50.0% | profitable |

Scale-free version, since gold's price level keeps moving:

| Range as % of price | n | EV |
|---|---|---|
| under 0.10% | 171 | −0.226 |
| 0.10–0.15% | 93 | −0.019 |
| 0.15–0.22% | 71 | +0.096 |
| **0.22–0.32%** | 70 | **+0.300** |
| 0.32–0.50% | 32 | +0.045 |
| over 0.50% | 18 | +0.509 |

**Monitoring rule: the 15-minute range must be at least 0.15% of the gold price.**
At gold 4 500 that is about 675 points ($6.75). Below 0.10% the strategy clearly
loses. Check the median of the last 20 sessions monthly; if it drops under the
line, stop trading Asia.

2026 currently runs at 0.247%, comfortably clear.

Necessary, **not sufficient** — New York clears this line and still has no edge
(§7). Treat it as a kill switch for Asia, not a search tool for new markets.

---

## 10. Prop-account mechanics

| Trades per day | Pass both | Median days | Daily-limit breach |
|---|---|---|---|
| **1** | 85.5% | 19 | 0.0% |
| 2 | 85.4% | 10 | 0.0% |
| 3 | 84.0% | 7 | 0.9% |

**Speed is nearly free.** Pass rate barely moves while median time drops from 19
days to 7, because pass probability is decided by the *sequence of trades*, not
the calendar. The only real cost is the 5% daily limit, which starts biting at
three trades a day.

### Risk sizing

| Risk / trade | With an edge (+0.24R) | Without one (−0.02R) |
|---|---|---|
| 0.5% | **100.0%** | 21.9% |
| 1% | 97.9% | 35.2% |
| 2% | 87.9% | 40.2% |
| 3% | 80.0% | **42.1%** |
| 4% | 72.7% | 41.5% |

**The optimum inverts.** With an edge, risk small — big bets add ruin chances you
do not need. Without one, risk big: small bets let a tiny negative drift grind you
to −10% and you never get a run to +8%. Variance is your friend only when you have
nothing else.

### Rotating accounts does not help

Rotating one account per day does **not** change any account's pass probability —
each still needs the same trade sequence, and you have only slowed the calendar by
N×. Expected passes = N × P(pass) either way.

What rotation buys is decorrelation, and there is a better way to get it:
decorrelate by session or symbol, not by day. Same date, one trade each,
independent outcomes. That was the argument for testing London and New York; §7
shows neither qualifies, so on gold this remains unsolved.

---

## 11. Rules of thumb

1. **Shortest range, fastest candle.** 15 minutes with M1 beats 30/M3 and 60/M5.
   The edge lives in the first 15 minutes and the earliest break.
2. **Never tighten the stop inside noise.** A quarter-range stop returns +0.002; a
   breakeven stop-move turns +0.387 into −0.234. Both fail for the same reason.
3. **RR 2, never RR 1.** Worth about five times the expectancy. The higher win
   rate at RR 1 is paid for in edge.
4. **A late breakout is a bad breakout.** Breaks after minute 15 drag EV from
   +0.375 to +0.181. Stop looking.
5. **Skip reversal breaks.** If the range closed at the far end from the side that
   broke, price crossed the whole range first. Those went 0 for 7.
6. **Optimise pass rate, not profit factor.** They select different parameters —
   the highest-EV setup ranks eleventh on pass rate.
7. **Win rate is worth paying for, but only if it is free.** At constant edge, 30%
   → 40% is worth 10 points of pass rate. Buying it with a nearer target is not.
8. **Range size is necessary, not sufficient.** New York has the widest ranges on
   the board and no edge.
9. **Speed is nearly free; risk sizing is not.** More trades per day barely dents
   pass rate. Changing risk per trade moves it 15–30 points.
10. **Trust nothing inside ±0.05 R.** That is the simulator's error bar against
    MT5. Several apparent improvements here were noise.
11. **Only Asia works.** London loses in every configuration; New York is flat at
    every range length.

---

## 12. Method and caveats

The Strategy Tester needs about 90 seconds per real-tick pass over 2.6 years, so
600 configurations would take hours. Instead `BarDump.mq5` recorded 730 857 M1
bars with tick counts across broker hours 01:00–18:59, and the Python harness in
this folder replays them. Entry timing depends only on the range break, so stop
distance, target and stop-management rules can all be re-evaluated against
identical recorded paths. Shortlists were then confirmed in MT5 on real ticks —
every table labelled "real ticks" is a genuine backtest.

### Simulator against MT5, identical configuration

| | Python sim | MT5 real ticks |
|---|---|---|
| 2026 EV | +0.362 | +0.333 |
| Win rate | 34.7% | 31.6% |
| Close-pos filter at 0.25 | +0.436 | +0.404 |
| Rolling filter at 1.00 | +0.426 | +0.454 |

Known gaps, all of which flatter the simulation:

- **M1 OHLC rather than real ticks.** Intrabar order is unknown, so when one bar
  contains both stop and target the simulation assumes the stop hit first. MT5
  recorded 7 hold-cap exits where the sim predicted 5.
- **Spread is a median** (52 points for 2026), measured at the Asia open, applied
  to every session. The Asia open is thin so the median understates.
- **Commission** modelled flat at $3.04 per lot per side.
- **481 setups against MT5's 455** — about 5% of days differ, most likely history
  gaps and entry-window boundary handling.

**Treat absolute levels as ±0.05 R. Rankings are reliable; levels are not.**

**And the sample is 112 trades.** That is enough to rank parameters and nowhere
near enough to establish an edge. Selecting on 2026 also means there is no
out-of-sample data left — forward live results are the only validation remaining.

---

## 13. Roadmap

- **`US100.cash` on its own cash open.** The New York result on gold does not
  condemn it: an index's cash open is its primary session, not a mid-session news
  spike. Cost structure needs re-measuring, not assuming.
- **Pre-commit the acceptance threshold** before sweeping any new session or
  symbol — say EV above +0.20 R with win rate above 40% — and trade every stream
  that clears it rather than ranking and picking the best. Selecting a maximum
  from several noisy 120-trade estimates is how a filter that works on paper fails
  live.
- **Verify `InpFollowsUSDST`** with `CheckBrokerOffset`. August is DST under both
  rulesets so the current setting is inferred, and it matters for the week each
  autumn when US and EU dates disagree.
- **Watch the range, not the backtest.** The kill switch in §9 is the one piece of
  ongoing monitoring this strategy needs.
