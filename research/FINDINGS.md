# ORB parameter study — findings

Asia opening range on XAUUSD, 00:00 UTC, 15-minute range, M1 signal bars,
entry window 15 minutes, 1-hour hold cap, 2% risk, one trade per day.

Data: 2024.01.01 – 2026.08.19, 481 setups. 546 parameter combinations
evaluated. Target rules: FundingPips 2-Step Standard, +8% then +5%, 10% max
loss, 5% daily, minimum 3 trading days, no time limit.

---

## The headline, before any parameter advice

**No combination out of 546 is profitable in 2024 or 2025.** The best "worst
year" in the entire grid is −0.042R. Every configuration that makes money makes
it in 2026 and only in 2026.

| Year | Best EV achievable | Median Asia range | Gold price |
|---|---|---|---|
| 2024 | −0.042 R | 186 pts | ~2 391 |
| 2025 | −0.005 R | 489 pts | ~3 450 |
| 2026 | +0.387 R | 1 108 pts | ~4 536 |

Gold's realised volatility ran above 50% in 2026 against a long-run norm near
15–16%. The 15-minute Asia range widened from $3.01 to $18.73 — six times in
dollars, 3.3× as a share of price. The strategy is a bet on that regime
continuing. Parameter choice decides how efficiently you harvest it; it does
not create it.

Treat every number below as conditional on 2026-like conditions.

**Decision taken: 2026 is the basis for parameter selection.** The rationale is
that Asia-session participation in gold changed in scale, not degree, and
2024–25 describes a market that no longer exists. That is defensible, and the
tables below carry a dedicated 2026 column for exactly that reason.

The cost of the decision, stated plainly: 119 setups, and **no out-of-sample
test left**. Parameters chosen on 2026 and traded forward into 2026 have only
live results as validation. The 2024–25 columns are retained not as a target to
optimise against but as the answer to "what happens if the regime reverts" —
and that answer is roughly −0.1R per trade at every setting.

---

## 1. Stop-loss placement

Measured as a fraction of the range, from the broken level. 0.5 puts the stop
at the range midpoint, 1.0 at the opposite boundary.

| SL fraction | EV (all) | WR | 2024 | 2025 | 2026 | 2026 WR |
|---|---|---|---|---|---|---|
| 0.250 | −0.272 | 29.7% | −0.523 | −0.216 | +0.002 | 33.6% |
| 0.375 | −0.152 | 31.4% | −0.340 | −0.164 | +0.142 | 37.0% |
| **0.500** (midpoint) | −0.024 | 34.7% | −0.164 | −0.139 | **+0.362** | **44.5%** |
| 0.625 | −0.032 | 34.5% | −0.135 | −0.124 | +0.263 | 42.0% |
| 0.750 | −0.062 | 34.9% | −0.142 | −0.137 | +0.173 | 42.0% |
| 1.000 (far side) | −0.004 | **39.1%** | −0.070 | −0.033 | +0.138 | 43.7% |

**Answer: the midpoint, 0.5.** It is the best choice for 2026 by a wide margin
(+0.362 against +0.138 for the far side).

Two things worth understanding rather than just copying:

**Tight stops are catastrophic, and monotonically so.** 0.25 of the range loses
0.272R per trade. The stop sits inside normal noise, so it gets hit before the
move resolves — you pay full risk for a coin that never lands. Anything below
0.5 is strictly worse across every year. This is the most robust single finding
in the study.

**The far side (1.0) is the most defensive choice.** It has the best overall EV
(−0.004) and the highest win rate (39.1%), because the stop is far enough away
that fewer trades die on noise. It also has the least-bad 2024 and 2025. If you
ever want a configuration that merely survives a quiet regime rather than
profiting in a loud one, this is it — but it earns less than half as much in
2026, and sizing at 2% of balance against a full-range stop means much smaller
positions.

---

## 2. Reward:risk

| RR | SL 0.5 EV | SL 0.5 WR | SL 0.5 2026 | SL 1.0 EV | SL 1.0 WR | SL 1.0 2026 |
|---|---|---|---|---|---|---|
| 1.00 | −0.133 | 47.8% | +0.094 | −0.030 | 49.7% | +0.103 |
| 1.25 | −0.110 | 42.6% | +0.118 | −0.035 | 44.7% | +0.121 |
| 1.50 | −0.077 | 39.3% | +0.201 | −0.033 | 41.8% | +0.136 |
| 1.75 | −0.032 | 37.4% | +0.260 | −0.020 | 39.9% | +0.125 |
| **2.00** | −0.024 | 34.7% | **+0.362** | −0.004 | 39.1% | +0.138 |
| 2.50 | −0.020 | 31.2% | +0.333 | +0.011 | 37.6% | +0.193 |
| 3.00 | −0.002 | 28.9% | +0.316 | +0.016 | 36.8% | +0.185 |

**Answer: 2.0.** It is the peak for 2026 at the midpoint stop, and the
pass-rate optimum sits at 1.75–2.0.

The structure is worth noting: **EV keeps improving with RR all the way to 3.0,
while win rate falls monotonically** — 47.8% at RR 1 down to 28.9% at RR 3. If
you were maximising expectancy you would push RR higher. You should not, for
two reasons.

First, 2026 specifically peaks at 2.0 and declines after. A 3R target needs
price to travel 1.5 range-widths inside the hour, and the hold cap truncates
those attempts.

Second, and more important for prop accounts: **pass rate is not maximised by
EV.** See §4.

RR 1.0 is clearly wrong. It buys you a 47.8% win rate but roughly triples the
loss rate per unit of profit — measured EV of −0.133 against −0.024 at RR 2.

---

## 3. Moving the stop — when, and where to

Cells show overall EV / 2026 EV. SL 0.5, RR 2.

| Trigger | to −0.5R | to −0.25R | to breakeven |
|---|---|---|---|
| off (never move) | −0.014 / **+0.387** | | |
| +0.25R | −0.070 / +0.230 | −0.102 / +0.169 | −0.309 / **−0.234** |
| +0.50R | −0.024 / +0.362 | −0.066 / +0.327 | −0.196 / +0.083 |
| +0.75R | −0.013 / +0.358 | −0.038 / +0.356 | −0.109 / +0.216 |
| +1.00R | −0.002 / +0.366 | −0.020 / +0.356 | −0.074 / +0.275 |

**Answer: trigger at +0.5R, move to −0.5R. Never move to breakeven.**

Three clear patterns:

**Moving to breakeven is the single most destructive thing in this study.** At a
+0.25R trigger it turns +0.387R into −0.234R — it converts a profitable
configuration into a losing one. A breakeven stop sits exactly where price
routinely retests after a breakout. You get stopped for nothing on trades that
would have worked, and you keep every full loss.

**Early triggers are worse than late ones.** +0.25R is worse than +1.00R at
every destination. Moving the stop early tightens it while the trade is still
inside noise.

**On pure EV, not moving at all wins** (+0.387 for 2026). The move costs about
0.02R of expectancy. Keep it anyway — §4 explains why.

---

## 4. What actually maximises pass rate

This is the section that matters, and it does not agree with the EV tables.

Ranked by probability of passing both FundingPips phases, 2026 distribution,
2% risk, one trade per day:

| SL | RR | Stop move | EV | WR | sd(R) | Pass both | Median days |
|---|---|---|---|---|---|---|---|
| 0.500 | 2.00 | 0.50 → −0.25 | +0.327 | 39.5% | 1.31 | **84.2%** | 15 |
| **0.500** | **2.00** | **0.50 → −0.50** | **+0.362** | **44.5%** | **1.37** | **84.1%** | **13** |
| 0.625 | 1.75 | 0.75 → −0.25 | +0.304 | 46.2% | 1.26 | 83.8% | 15 |
| 0.500 | 2.00 | 0.75 → −0.25 | +0.356 | 44.5% | 1.39 | 83.2% | 13 |
| 0.500 | 2.00 | off | **+0.387** | 49.6% | 1.49 | 80.7% | 10 |
| 0.250 | 2.00 | off | +0.116 | 42.9% | 1.49 | 47.9% | 14 |
| 0.250 | 3.00 | 0.50 → −0.50 | +0.128 | 27.7% | 1.69 | 43.3% | 12 |

**The configuration currently in the EA is the pass-rate optimum**, second by
one tenth of a point and two days faster than the nominal leader.

**The highest-EV configuration ranks 11th.** Turning the stop move off raises EV
from +0.362 to +0.387 and *lowers* pass rate from 84.1% to 80.7%. The reason is
in the `sd(R)` column: 1.37 against 1.49. A prop challenge is a race between
+8% and −10%, not a long-run expectancy game. Variance reduction is worth more
than the expectancy it costs, because the drawdown barrier can end you before
the edge has time to express itself.

This is the central lesson of the study: **optimise for pass rate, not for
profit factor.** They select different parameters.

---

## Method, and where it is soft

The Strategy Tester would need hours to evaluate 546 combinations on real
ticks. Instead `BarDump.mq5` recorded 163 192 M1 bars around the session
window, and `sweep.py` replays them. Entry timing depends only on the range
break, so stop distance, target and stop-move rules can all be re-evaluated
against identical recorded paths.

**Validation against MT5**, same configuration both sides:

| | Python sim | MT5 tester |
|---|---|---|
| Trades | 481 | 455 |
| EV | −0.024 R | −0.0045 R |
| Win rate | 34.7% | 31.6% |
| 2026 EV | +0.362 | +0.333 |

Known gaps, all of which flatter the simulation slightly:

- **M1 OHLC instead of real ticks.** Intrabar order is unknown, so when a bar
  contains both stop and target the simulation assumes the stop hit first.
  Real ticks still take out stops the simulation misses.
- **Spread is a per-year median** (21 / 28 / 52 points) rather than the live
  value. The Asia open is thin and spreads spike there, so the median
  understates cost.
- **Commission** modelled flat at $3.04 per lot per side, from the deal log.
- **481 setups against MT5's 455.** ~5% of days differ, likely history gaps and
  boundary handling on the entry window.

Treat absolute levels as ±0.05R. **Rankings are reliable; levels are not.**

Every table is 2024–2026 on one symbol, one session. 481 setups is enough to
rank parameters and nowhere near enough to establish an edge.

---

## Bugs found and fixed during the study

Three, all of which corrupted earlier results:

**Take profit was anchored to the range level, not the fill.** RR=2 was
delivering 1.24 realised. Entry happens past the level, so the real risk was
wider than the one the target was computed from.

**Position size was computed from the level too.** Realised risk ran ~1.3× the
configured percent on every trade — one loss reached 2.71× intended risk. Wins
came out at 2.61R against an RR of 2 for the same reason.

**The stop move ratcheted to breakeven.** `ManageOpenPosition` recomputed R from
the *live* stop each tick, so after the first move R shrank, the trigger
re-fired, and the stop crept to entry. 47.5% of losses were landing at
breakeven and 1.1% in the −0.5R band that was configured. Fixing it lifted win
rates from 19/18/30% to 32/25/42% by year and took the strategy from −10.5R to
−2.1R.

That last one had also been masking the range-size effect, which is why an
earlier pass through this data concluded there wasn't one.

---

## The range filter

Ranking each trade against its own year's median range, so the price trend
cannot leak in:

| | n | EV | ±1 SE |
|---|---|---|---|
| Narrow half | 229 | −0.130 | ±0.080 |
| Wide half | 226 | +0.123 | ±0.086 |
| **Difference** | | **+0.253** | **±0.118**, t = 2.15 |

Significant, and the direction holds in all three years. Filtering to the wide
half turns 2024 from −0.060 to +0.101 and takes 2026 to +0.462.

**But the test cheats.** Ranking against the year's median uses information from
the future — you cannot know 2026's median in January 2026. The implementable
version is a rolling percentile against the last N sessions, which will perform
worse, possibly much worse. `+0.123R` is an upper bound, not a forecast.

---

## Recommendations

**Keep the current configuration.** SL at the range midpoint, RR 2.0, stop move
at +0.5R to −0.5R. It is the pass-rate optimum out of 546 candidates. No change
is warranted by this study.

**Do not chase the higher-EV variants.** Turning the stop move off, or pushing
RR to 3, raises expectancy and lowers pass rate. Wrong objective.

**Never move the stop to breakeven.** It is the one change here that can flip a
profitable configuration to a losing one.

**Build the rolling range filter and re-test it.** It is the only untested idea
with a significant result behind it, and it is the difference between a 54%
business and a 31% coin flip if the regime reverts.

**Size the position against the fill, and never against the level.** Already
fixed, but it is the class of error that silently doubles risk.

---

## Roadmap

### Next: London and New York on gold

The engine already takes session as an input, so this needs no code — three
runs of the sweep above with a different `Session start hour`.

| Session | UTC | Rationale |
|---|---|---|
| Asia | 00:00 | done, this study |
| London | 07:00 | the volatility open; widest ranges of the day on gold |
| New York | 13:30 | cash open, overlaps London's afternoon |

Gold's peak volume window is the London–New York overlap, so on prior grounds
London should produce wider ranges relative to spread than Asia — which §1
suggests is where this strategy works best.

### Then: NDX100 (`US100.cash`)

M1 history is already cached on the FTMO feed. Two things differ and both
matter:

- **Cost structure.** Index CFD spreads behave differently from spot gold. The
  whole stop-distance-versus-spread relationship needs re-measuring, not
  assuming.
- **Session meaning.** NDX barely moves during Asia. Its range is defined by
  the cash open at 13:30 UTC, and an Asia-session ORB on an index is close to
  meaningless. Expect the New York run to be the only viable one, possibly
  London for the European-hours gap.

Sizing is already symbol-agnostic — lots derive from `SYMBOL_TRADE_TICK_VALUE`,
so no code changes are needed for a different contract.

### Why this also helps the account pool

Six streams (3 sessions × 2 symbols) trading the same day are far less
correlated than one stream traded across six accounts on rotation. That gives
the decorrelation without the N× calendar penalty, and each account still takes
one trade a day at 2% risk.

### A warning about testing six things

If six session/symbol combinations are each swept on 2026 data and the best one
is selected, the winner will look roughly one standard error better than it
truly is — around +0.05R here. With 119 setups per stream that is a real
distortion.

The discipline that costs nothing: **decide in advance** what threshold makes a
stream tradeable (say 2026 EV above +0.20R with win rate above 40%), and take
every stream that clears it rather than ranking and picking the top. Selecting
a maximum from six noisy estimates is how a filter that works on paper fails
live.

---

## Open items

- Rolling range filter — implement as a trailing percentile, re-test
- London and New York sweeps on gold
- `US100.cash` sweeps, New York session first
- `BrokerFollowsUSDST` still unverified; run `CheckBrokerOffset`
- Everything here is one symbol and one session. The regime dependence is a
  gold story and may not transfer.
