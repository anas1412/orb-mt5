# ORB parameter study — 2026

Asia opening range on XAUUSD. Session 00:00 UTC, 15-minute range, M1 signal
bars, 15-minute entry window, 60-minute hold cap, 2% risk, one trade per day.

**All figures are 2026** (2026.01.02 – 2026.08.21, 165 trading days) unless a
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
| Days traded | Monday to Thursday (Friday off, §12) |
| Risk | 2% |

**Result: +0.580 R per trade, 51.1% win rate, 95.3% chance of passing both
phases, median 15 calendar days.** 88 trades, verified on real ticks.

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

### Two ideas tested and rejected

**Structure-based stops** (`research/structsl.py`). Place the stop under the swing
low of the last K range bars instead of at the midpoint, accepting it only when
the distance lands in 0.25–0.50. Tested at K = 3, 5, 8 and 15, it loses in every
variant, with a clean dose-response: firing on 42% of trades costs −0.131 R,
32% costs −0.116, 15% costs −0.015, 0% costs nothing.

Isolating structure from distance settles it. On the 37 setups where a 3-bar swing
qualified, the structure stop returned +0.207 R against **+0.188 R for an
arithmetic stop at exactly the same distance** — a difference of +0.019, t = 0.06.
Against the midpoint on the same 37 setups: **+0.519 R**.

**A stop is a price level; the market does not know why you chose it.** If swing
lows were safer, a structure stop would beat an arithmetic one at equal distance.
It does not, so the entire cost is the tightening — §1 arriving through a
different door.

**The optimal stop distance depends on the target** (`research/rr1sl.py`). At RR 1
the best stop is the *far side*, not the midpoint:

| Target | Best SL | EV | Win rate | Pass both | ~Days |
|---|---|---|---|---|---|
| RR 1.0 | 1.00 far side | +0.231 | **61.4%** | 92.3% | 30 |
| **RR 2.0** | **0.50 midpoint** | **+0.568** | 52.3% | **94.9%** | **13** |
| RR 3.0 | 0.50 midpoint | +0.506 | 40.9% | 85.6% | 15 |

At RR 1 price need only travel one stop-width, so a wide stop buys a wide target
noise can still reach — 61.4% win rate, the highest in the study. At RR 2 it needs
two stop-widths, so a wide stop puts the target out of reach inside 60 minutes.

RR 1 is still the wrong choice: 2.5× less edge and 17 more days per challenge for
9 points of win rate. It is the clearest illustration of §5 — win rate only pays
when it comes free.

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

## 8. The half-of-the-range rule

**Rule:** split the range box in half. Whichever half the final range bar closed
in is the only direction you may trade that session.

- closed in the **top half** → take an **up-break**, skip a down-break
- closed in the **bottom half** → take a **down-break**, skip an up-break

That is the whole filter, and it is what `InpMinClosePos = 0.50` computes. The
code still measures a 0–1 position for logging and for other threshold values,
but at 0.50 the two are the same test:

```
cp = (range_last_close − range_low) / (range_high − range_low)
up-break allowed   when cp ≥ 0.50   (closed in the top half)
down-break allowed when cp ≤ 0.50   (closed in the bottom half)
```

**Mechanism.** Breaking the half price already sat in is continuation. Breaking
the other half means price crossed the entire range first — a reversal wearing a
breakout's clothes, and those flips tend to keep flipping. Same failure that makes
New York unusable.

Rejection ends the day rather than waiting for a break the other way. Deliberate:
the opposite break is allowed by construction, so permitting it would turn every
rejection into a coin flip on the other side.

### The rule, measured directly

2026, Monday–Thursday, every break the engine saw, split by half
(`live_cp0.00.csv`, 2% risk, stop at the midpoint, 2R target, stop move +0.5R → −0.5R):

| Which half broke | n | Wins | WR | EV | Total R | Total % | Verdict |
|---|---|---|---|---|---|---|---|
| **Broke the half it closed in** | 72 | 38 | **52.8%** | **+0.615** | **+44.3** | **+88.6%** | trade |
| Broke the opposite half | 23 | 7 | 30.4% | +0.049 | +1.1 | +2.2% | skip |
| Every break, no filter | 95 | 45 | 47.4% | +0.478 | +45.4 | +90.9% | — |

The 23 skipped trades contributed **+1.1 R between them** — all of the variance,
none of the profit. Same money from 23 fewer trades at a 5.4-point higher win
rate, which is exactly the trade a pass-rate account wants.

### Evidence trail: how the threshold was picked

The sweep below is the original quadrant study that led to the midpoint. Kept for
the record — the 0–1 numbers are the research, the halves rule is the product.

#### Quadrants

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

#### Marginal cut at each step

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

**Chosen: 0.50 — the midpoint.** Two reasons, in order of importance:

1. **It is the only version a human can apply by eye.** "Did the candle close
   above or below the middle of the box?" needs no arithmetic at 00:15. A 0.25
   threshold requires measuring quarters live, which is where mistakes come from.
2. Below 0.25 is bad *in kind* — 0 wins from 7, −0.816 R. The 0.25–0.50 band is
   merely mediocre (19 trades, ≈ +0.20 R), so cutting it costs a little total
   profit and buys a higher win rate and a smoother equity curve.

The honest trade-off: 0.25 keeps slightly more total R, 0.50 gives the higher win
rate, the better pass rate and a rule you cannot misread. For a challenge account
the second set wins.

A separate test asked whether the same measurement predicts *direction* before any
break happens (`research/bias*.py`, 163 sessions, close of 00:14 against the
close an hour later). It does not, except at the top: a close in the top quarter
of the range precedes a higher price an hour later 72.9% of the time against a
54.0% base rate, while every other quadrant is noise and averaging the range
destroys the signal entirely (r² = 0.001). Nothing there changes the filter, so
it is recorded in the scripts rather than expanded here.

| | Off | Midpoint (live default) |
|---|---|---|
| EV | +0.333 | **+0.443** |
| Win rate | 42.0% | **46.2%** |
| Pass both | 81.6% | **89.4%** |
| Attempts per pass | 1.23 | **1.12** |
| Days | 18 | 21 |

(Full-sample columns, Friday included, for comparability with the sweep above.
The 2026 Monday–Thursday live configuration is the table at the top of this
section: 52.8% WR, +0.615 EV.)

### ⚠ This filter is a regime bet

Tested on a choppy market instead of a trending one, the effect **inverts**:
the bottom of the range becomes the *best* place to have closed and the top turns
negative — exactly backwards from what 2026 shows.

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
5. **Trade only the half it closed in.** If the range closed in the far half from the side that
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
12. **Do not trade Friday.** The only losing day of the week, at a 20.8% win rate.
    Dropping it improves expectancy, win rate, pass rate *and* speed at once.

---

## 12. Day of week

Live configuration, 112 trades.

| Day | n | EV | ±SE | Win rate | Total R |
|---|---|---|---|---|---|
| Monday | 23 | +0.657 | 0.303 | 52.2% | +15.12 |
| Tuesday | 22 | +0.310 | 0.281 | 36.4% | +6.83 |
| **Wednesday** | 24 | **+0.909** | 0.276 | **66.7%** | +21.80 |
| Thursday | 19 | +0.386 | 0.325 | 47.4% | +7.33 |
| **Friday** | 24 | **−0.241** | 0.240 | **20.8%** | **−5.78** |
| All | 112 | +0.404 | 0.132 | 44.6% | +45.30 |

Tested against the other four days combined:

| Day | Difference | t | Verdict |
|---|---|---|---|
| Monday | +0.318 | +0.95 | no |
| Tuesday | −0.117 | −0.37 | no |
| Wednesday | +0.642 | +2.05 | significant |
| Thursday | −0.023 | −0.06 | no |
| **Friday** | **−0.821** | **−2.91** | **significant** |

**Friday is the only losing day, and it is not marginal** — five winners from 24
trades, −5.78 R, and it drags the whole sample down.

### Effect of dropping it

| Config | n | Winners | Win rate | EV | ±SE | Pass both | ~Days |
|---|---|---|---|---|---|---|---|
| keep all five days | 112 | 50 | 44.6% | +0.404 | 0.132 | 87.0% | 19 |
| **drop Friday** | 88 | 45 | **51.1%** | **+0.581** | 0.150 | **95.5%** | **15** |
| drop Friday + Tuesday | 66 | 37 | 56.1% | +0.671 | 0.175 | 96.7% | 12 |

**Better on every axis including speed**, because the trades removed lose rather
than merely win less. That is the opposite of the 0.25 → 0.50 threshold question
in §8, where the cut removed winners.

### Why this one is believable

There is a mechanism, not just a number. Friday's Asia session is the last of the
week: by the time London opens, position-squaring into the weekend dominates. A
breakout at 00:15 UTC on a Friday has to survive a session driven by people
flattening rather than committing.

### Why Tuesday stays

Tuesday is the second-weakest day (36.4% win rate, +0.310) and cutting it *also*
improves every headline number. It stays anyway: `t = −0.37` against the other
days is nothing, its EV is clearly positive, and at 66 trades the estimate is
weaker than the improvement it appears to buy. **Cutting Tuesday is fitting the
calendar, not finding a pattern.**

Note the standard error growing with each cut — 0.132 → 0.150 → 0.175. Every
removal makes the remaining estimate less certain even as the average improves.

### Caveat

24 Friday trades, ±0.240, so the true value sits somewhere between −0.72 and
+0.24. Five days were tested, so the worst of five landing near two standard
errors out is partly what chance produces. What tips it: negative expectancy, a
20.8% win rate, a mechanism, and simultaneous improvement in both speed and pass
rate. That combination is rare enough to act on.

**Set `InpTradeFri = false`.**

---

## 13. US100.cash at the New York cash open

The last roadmap idea with a real argument behind it: an index's cash open is its
*primary* session, not a mid-session news spike the way 13:30 UTC is for gold.
Different instrument, different cost structure, structurally different event.

MT5 real ticks, 2026, 09:30 New York local (DST handled by `TimeZones.mqh`),
15-minute range, M1 signal, 15-minute entry window, 60-minute hold, stop move
+0.5R → −0.5R, Friday included, half-of-the-range rule off, 2% risk.

| Config | n | EV | ±SE | WR | sd(R) | Total R | Pass both | ~Days |
|---|---|---|---|---|---|---|---|---|
| RR 1 · SL 100% far side | 140 | −0.038 | 0.062 | 50.0% | 0.74 | −5.29 | 19.7% | 50 |
| RR 1 · SL 50% midpoint | 140 | −0.028 | 0.076 | 44.3% | 0.90 | −3.91 | 26.7% | 34 |
| **RR 2 · SL 100% far side** | 140 | **−0.016** | 0.069 | 49.3% | 0.82 | −2.30 | 28.1% | 43 |
| RR 2 · SL 50% midpoint | 140 | −0.052 | 0.089 | 36.4% | 1.05 | −7.35 | 21.4% | 27 |

**All four negative, all within one standard error of zero.** That is a coin flip
rather than a losing strategy — a different failure from gold's New York session,
which loses decisively.

### Costs are not the obstacle

| | Gold Asia | US100 NY |
|---|---|---|
| Median range | 1 141 pts | 13 775 pts |
| Median spread | 52 pts | 145 pts |
| **Spread as % of risk** | **9.5%** | **2.1%** |

US100 has the cheapest execution of anything tested here — spread is barely a
fifth of the burden gold carries. It still produces nothing. **The 15-minute
opening range carries no directional information at the index cash open**, and no
amount of cost advantage substitutes for that.

### Nothing in the calendar either

Best config by day: Monday −0.121, Tuesday −0.024, Wednesday +0.029, Thursday
+0.017, Friday +0.018. Three marginally positive, none above +0.03, all inside
noise on ~28 trades each.

### Verdict

**Not tradeable.** The far-side variant at −0.016 with a 49.3% win rate is the
least-bad thing found outside gold's Asia session, and it is still a coin flip.

This closes the roadmap's last argued idea. **Every session and symbol tested
outside Asia-on-gold has failed:** London (decisively negative), New York on gold
(negative at three range lengths, two UTC anchors, and in both directions), and
now US100 at its own cash open (flat).

The pattern across all of them is the same one §7 identified — a range that gets
violated in both directions carries no information, and neither wide ranges nor
cheap spreads change that.

---

## 14. Method and caveats

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

## 15. Roadmap

- ~~`US100.cash` on its own cash open.~~ **Done — §14. Flat, not tradeable.**
  With it, every session and symbol tested outside Asia-on-gold has failed. There
  is no obvious next candidate that is more than a guess; the productive direction
  is a different *signal*, not another market for this one.
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
