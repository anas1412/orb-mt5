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

## 5. Entry cutoff and hold time

Swept together, because a later cutoff means later entries with less time left
to reach target. SL 0.5, RR 2, stop move +0.5R to -0.5R, 2026 data, 679 setups
scanned with a 120-minute window.

### When the break actually happens

| Minutes after range close | Setups | Share |
|---|---|---|
| 0-5 | 266 | 39.2% |
| 5-10 | 137 | 20.2% |
| 10-15 | 78 | 11.5% |
| 15-20 | 57 | 8.4% |
| 20-30 | 62 | 9.1% |
| 30-60 | 71 | 10.4% |
| 60-120 | 8 | 1.2% |

Nearly 40% of breaks arrive within five minutes. By minute 15 you have 71% of
them.

### Entry cutoff

| Cutoff | 2026 setups | EV at 90-min hold |
|---|---|---|
| 5 min | 76 | +0.332 |
| 10 min | 106 | +0.367 |
| **15 min** | **119** | **+0.375** |
| 20 min | 127 | +0.330 |
| 30 min | 142 | +0.255 |
| 45 min | 154 | +0.201 |
| 60 min | 162 | +0.181 |
| 120 min | 163 | +0.191 |

**Answer: 15 minutes.** A real peak, not a plateau edge.

**A late breakout is a bad breakout.** The 29% of setups that break after minute
15 are net harmful: including them drags EV from +0.375 down to +0.181. A range
that takes half an hour to give way is not breaking out, it is drifting. Cutting
at 15 keeps 71% of the opportunities and all of the edge.

### Hold cap

| Hold | 2026 EV | Pass both |
|---|---|---|
| 15 min | +0.118 | - |
| 30 min | +0.205 | - |
| 45 min | +0.334 | 83.4% |
| 60 min | +0.362 | 84.2% |
| **90 min** | **+0.375** | **85.2%** |
| 120 min | +0.373 | 85.0% |
| 180 min | +0.370 | 85.0% |

**Answer: 90 minutes is the peak; 60 costs almost nothing** - +0.013R and one
point of pass rate. Keep 60 if the clean one-hour rule is worth more than that.

Do not go below 60. At 45 minutes winners start being truncated, and 15 minutes
destroys the strategy outright (+0.118) because almost nothing reaches a 2R
target that fast.

### Correction to the duration estimate

Earlier sections quote a median of 13 days to pass both phases. That assumed a
setup every trading day. With a 15-minute cutoff only ~72% of days produce one,
so the honest figure is **~18 trading days**, about 3.6 calendar weeks.

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

~~Gold's peak volume window is the London–New York overlap, so on prior grounds
London should produce wider ranges relative to spread than Asia.~~
**Measured and wrong — see §12.** In 2026 London's range is 0.80x Asia's, and
neither London nor New York carries an edge at any parameter setting.

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

---

## 10. The rolling range filter — MT5 verified

**Rule:** skip the day unless the 15-minute range is at least `X` times the
median range of the previous 20 sessions. The yardstick uses only sessions
strictly before today, and includes days that never broke out, so there is no
lookahead — unlike the within-year ranking in §9.

All figures below are **MT5, real ticks, 2024.01-2026.08**, not simulation.

| Threshold | Trades | Kept | EV all | +/-SE | WR | 2024 | 2025 | 2026 | Pooled pass | 2026 pass | 2026 days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| off | 455 | 100% | -0.005 | 0.059 | 31.6% | -0.060 | -0.176 | +0.333 | 31.0% | 81.2% | 18 |
| 1.00 | 230 | 51% | +0.074 | 0.085 | 36.1% | +0.019 | -0.143 | +0.454 | 44.9% | 90.1% | 31 |
| **1.25** | **141** | **31%** | **+0.141** | 0.107 | 39.7% | **+0.154** | -0.070 | **+0.512** | **58.9%** | **94.5%** | **52** |
| 1.50 | 96 | 21% | +0.275 | 0.130 | 45.8% | +0.317 | +0.059 | +0.645 | 80.5% | 97.6% | 72 |

### This breaks the regime dependence

Section "The headline" states that no configuration out of 546 was profitable in
2024 or 2025. **The filter at 1.50 is the exception**: +0.317, +0.059 and +0.645
across the three years, with a pooled +0.275 +/- 0.130 that clears its own noise.

It is the first result in the project that does not rest on the 2026 regime.

### But throughput points the other way

Passes per year, assuming 2026-like conditions:

| Threshold | Days per challenge | Pass rate | Passes per year |
|---|---|---|---|
| off | 18 | 81.2% | **11.3** |
| 1.00 | 31 | 90.1% | 7.3 |
| 1.25 | 52 | 94.5% | 4.5 |
| 1.50 | 72 | 97.6% | 3.4 |

**No filter wins on calendar speed. The filter wins on fees per pass and on
surviving a quiet market.** Which matters depends on the binding constraint:

- **Fees are the constraint** -> filter hard. At 1.50 you need 1.02 attempts per
  pass against 1.23 with no filter.
- **Calendar time is the constraint** -> filter lightly or not at all.
- **A pool of accounts run in parallel** -> calendar time per account is not the
  bottleneck, because many run at once. This argues for the higher threshold.

### Decision: 1.25

- 1.00 leaves 2025 clearly negative (-0.143). Still a regime bet.
- 1.50 is the only all-years-positive setting, but rests on **96 trades over
  2.6 years** — 37 a year — and 72 days per challenge.
- 1.25 puts 2024 solidly positive (+0.154), 2025 near flat (-0.070), 2026 at
  +0.512, and nearly doubles pooled pass rate against no filter.

**The time cost is temporary.** The filter's only real drawback is fewer setups,
and that is exactly what the London and New York sessions fix. Three filtered
sessions produce roughly three times the setups of one, which brings 1.25 back
to about 18 calendar days — the unfiltered speed, at the filtered pass rate.
Revisit 1.50 once those are running.

### Judged on 2026 alone: not worth it

The decision to select on 2026 changes the answer. MT5 real ticks, 165 trading
days:

| Threshold | n | 2026 EV | +/-SE | WR | Pass both | Days | vs no filter | t | Passes/yr | Fees/pass |
|---|---|---|---|---|---|---|---|---|---|---|
| **off** | 119 | +0.333 | 0.127 | 42.0% | 81.1% | **18** | - | - | **11.2** | 1.23 |
| 1.00 | 63 | +0.454 | 0.177 | 47.6% | 90.2% | 31 | +0.122 | 0.56 | 7.2 | 1.11 |
| 1.25 | 35 | +0.512 | 0.229 | 51.4% | 94.5% | 52 | +0.179 | 0.68 | 4.6 | 1.06 |
| 1.50 | 23 | +0.645 | 0.285 | 56.5% | 97.6% | 72 | +0.313 | 1.00 | 3.4 | 1.02 |

**Not one improvement clears its own noise.** The t-values are 0.56, 0.68 and
1.00 against a threshold of roughly 2.0. The sample collapses from 119 trades to
23, and passes per year fall from 11.2 to 3.4.

**The filter earned its keep in 2024 and 2025** — those are the years it turned
from negative to positive. Selecting on 2026 alone discards precisely the
evidence that justified it.

**Default set to off** (`InpRangeLookback = 0`).

Keep the code. It is the correct insurance if the regime turns quiet again: at
threshold 1.50 all three years are positive and pooled pass rate is 80.5%
against 31%. Turning it on is a one-input change, and the trigger to do so is
watching realised range compress — not a backtest.

### The interesting asymmetry

The filter is worthless inside a loud market and decisive across a mixed one.
That is not a contradiction: it removes quiet days, and 2026 barely has any.
Which makes the filter a **regime detector you do not need while the regime is
obvious** — and the one thing that would have saved 2024 and 2025.

### Simulator validation

The offline sweep predicted +0.068 pooled and +0.426 for 2026 at threshold 1.00.
MT5 returned **+0.074 and +0.454**. Far closer than the unfiltered validation in
the Method section, which supports using the sweep to shortlist and MT5 to
confirm.

---

## 12. Sessions compared: Asia, London, New York

The roadmap asserted that London would carry the widest gold ranges. **That was a
prior, not a measurement, and it is wrong.**

### Range and activity, measured

Median 15-minute opening range. 1 point = $0.01. Ticks = M1 tick count over the
15-minute window.

| Year | Asia 00:00 | London 07:00 | New York 13:30 |
|---|---|---|---|
| 2024 | 177 pts / 0.075% | 268 / 0.111% | **610 / 0.245%** |
| 2025 | 504 / 0.143% | 506 / 0.143% | **846 / 0.247%** |
| 2026 | **1141 / 0.247%** | 910 / 0.205% | **1630 / 0.364%** |

2026 ticks: Asia 2852, London 2765, New York 4494.

**In 2026 London is 0.80x Asia by range and 0.97x by activity — it is now the
quietest of the three.** Asia's range grew 6.4x since 2024 against London's 3.4x.
That is consistent with the 2026 rally being Asian and ETF-driven: participation
moved into Asian hours.

### Does the edge follow the range? No.

Same engine, each session given its **own** parameter search (48 combinations of
stop distance, target and stop movement):

| Session | Best pooled EV | Best 2026 EV | 2026 pass rate | Verdict |
|---|---|---|---|---|
| Asia | -0.014 | **+0.387** | 84.4% | the only session with an edge |
| London | -0.068 +/- 0.050 | **-0.111** | 4.6% | dead — every one of 48 combinations negative in 2026 |
| New York | +0.030 +/- 0.064 | +0.048 | 20.9% | flat; its best year was 2025 |

**New York has the widest ranges of any session and produces no edge.** 0.364% of
price in 2026, well past the 0.15% line from §11, and still nothing.

### Correction: the first session test ignored DST

The comparison above initially anchored each session to a **fixed UTC hour** —
07:00 for London, 13:30 for New York. Those are the summer opens. In winter
London opens at 08:00 UTC and New York at 14:30 UTC, so roughly five months of
every year measured an hour before the real open: London during the pre-open,
New York during US pre-market.

Re-run with each zone on its own local clock and its own DST rule:

| Session | Anchor | DST rule |
|---|---|---|
| Asia | 00:00 UTC | none |
| London | 08:00 London | EU dates, last Sun Mar to last Sun Oct |
| New York | 09:30 New York | US dates, 2nd Sun Mar to 1st Sun Nov |

| Session | Pooled EV, fixed UTC | Pooled EV, DST-correct | 2026 |
|---|---|---|---|
| Asia | -0.024 | -0.024 (unchanged) | +0.362 |
| London | -0.137 | **-0.207** | -0.293 |
| New York | -0.036 | **-0.082** | -0.051 |

Asia is identical, as it must be. **Both other sessions got worse**, so the
sloppy version had been flattering them. Best of 16 settings in 2026: Asia
+0.387, London -0.205, New York +0.024.

The verdict is unchanged and now rests on correct data.

Note the EA itself was never affected — `TimeZones.mqh` resolves London and New
York through their own switch dates and `TestTimeZones` asserts it. The fault was
in the offline comparison only. `research/sessionsim2.py` is the corrected
version; `sessionsim.py` is kept for the fixed-UTC contrast.

### The correction this forces

Section 11 established that range size predicts the Asia edge, and offered 0.15%
of price as a monitoring line. New York clears that line in all three years and
fails anyway.

**So range size is necessary but not sufficient.** It is a filter on Asia days,
not a law about sessions.

The likely mechanism: the New York cash open is a two-sided, news-driven spike.
The opening range gets violated in *both* directions, so a breakout carries no
information. Asia's 2026 breakouts ride sustained one-way flow from the gold bull
market. Wide range without directional persistence is just whipsaw with a bigger
stop.

### Roadmap consequence

- **Drop London on gold.** Not a parameter problem; there is nothing there.
- **Drop New York on gold.** Break-even at best, and its only positive year was
  2025 — the reverse of Asia's profile, which is interesting but not tradeable.
- **`US100.cash` is still worth testing**, and the New York result does not
  condemn it. An index's cash open is its primary session rather than a
  mid-session news spike, which is a structurally different setup from gold at
  13:30 UTC.
- **Asia stays the only live configuration.**

One caveat on cost: the same per-year spread (21/28/52 points) was applied to
every session, measured at the Asia open. New York liquidity is deeper, so its
true spread is tighter — meaning the New York result is, if anything, flattered.
It still has no edge.

---

## 15. The close-position filter

**Rule:** at the moment the range closes, score how near price was to the side
it then breaks. Skip the trade if the score is below a threshold.

```
score = (range_last_close - range_low) / (range_high - range_low)      for an up-break
score = 1 - that                                                        for a down-break
```

A score of 1.0 means the final range bar closed right against the boundary that
then broke — a short journey, pressure already pointing that way. A score of 0.0
means it closed at the *opposite* boundary and had to traverse the entire range
before breaking out.

**Mechanism.** A high score is continuation. A low score is a reversal wearing a
breakout's clothes: price flipped across the whole range first, and those flips
tend to keep flipping. It is the same failure that makes New York unusable
(§12) — a range violated in both directions carries no information.

Rejection ends the day rather than waiting for a break the other way. That is
deliberate: it matches how the filter was measured, and the opposite break would
mechanically score `1 - score`, so allowing it would turn every rejection into a
coin flip on the other side.

### Threshold sweep — MT5 real ticks, Asia only, 2026

| Min score | Trades | Kept | n(2026) | EV | +/-SE | WR | sd(R) | Pass both | Days | Fees/pass |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 off | 455 | 100% | 119 | +0.333 | 0.127 | 42.0% | 1.39 | 81.6% | **18** | 1.23 |
| 0.10 | 440 | 97% | 114 | +0.388 | 0.130 | 43.9% | 1.39 | 85.8% | 19 | 1.17 |
| 0.20 | 432 | 95% | 114 | +0.388 | 0.130 | 43.9% | 1.39 | 85.7% | 19 | 1.17 |
| **0.25** | **423** | **93%** | **112** | **+0.404** | 0.132 | **44.6%** | 1.40 | **86.6%** | **19** | **1.15** |
| 0.35 | 393 | 86% | 106 | +0.420 | 0.136 | 45.3% | 1.40 | 87.7% | 20 | 1.14 |
| 0.50 | 345 | 76% | 93 | +0.443 | 0.145 | 46.2% | 1.40 | 89.4% | 21 | 1.12 |
| 0.75 | 234 | 51% | 68 | +0.529 | 0.173 | 50.0% | 1.43 | 92.7% | 26 | 1.08 |

### Where the trades actually sit — quadrant view

2026, grouped by score rather than by cumulative threshold:

| Quadrant | n | Share | EV | +/-SE | Win rate | Total R |
|---|---|---|---|---|---|---|
| **below 25%** | 7 | 5.9% | **-0.816** | 0.098 | **0.0%** | -5.71 |
| 25% - 50% | 19 | 16.0% | +0.217 | 0.317 | 36.8% | +4.12 |
| 50% - 75% | 25 | 21.0% | +0.210 | 0.260 | 36.0% | +5.24 |
| **above 75%** | 68 | 57.1% | **+0.529** | 0.173 | **50.0%** | +35.95 |

**Seven trades below 25%, and not one of them won.** The middle two quadrants are
indistinguishable from each other (+0.217 and +0.210) and both clearly worse than
the top.

### The same quadrants across all three years

| Quadrant | n | Share | EV all | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| below 25% | 32 | 7.0% | -0.140 | **+0.522** | -0.387 | **-0.816** |
| 25% - 50% | 78 | 17.1% | +0.110 | +0.395 | -0.101 | +0.217 |
| 50% - 75% | 111 | 24.4% | -0.173 | -0.345 | -0.203 | +0.210 |
| above 75% | 234 | 51.4% | +0.056 | -0.098 | -0.167 | **+0.529** |

**In 2024 the pattern inverts completely.** Below-25% was that year's *best*
quadrant at +0.522, and above-75% was negative. Exactly backwards from 2026.

That is mechanism, not noise. In a choppy market the range mean-reverts, so a
break away from where price was sitting pays. In a trending market the range is a
pause in a move, so a break continuing that move pays. **The filter is a
directional bet on which of those two regimes you are in** — a stronger statement
than "it makes 2024 worse". The sign flips, not just the size.

The practical consequence: if the monitoring rule in §11 ever tells you ranges
have compressed, this filter should be turned off or inverted, not merely
tolerated.

### Why 0.25 and not higher

The marginal cut at each step is what decides it:

| Step | Trades removed | Their average |
|---|---|---|
| 0.00 -> 0.10 | 5 | **-0.938 R** |
| 0.20 -> 0.25 | 2 | **-0.511 R** |
| 0.25 -> 0.35 | 6 | +0.132 R |
| 0.35 -> 0.50 | 13 | +0.256 R |
| 0.50 -> 0.75 | 25 | +0.210 R |

**Everything below 0.25 is genuinely bad. Everything above it is
profitable.** Seven trades in 119 account for the entire benefit, and five of
them average -0.938 R.

Past 0.25 the pass rate keeps climbing — 86.6% to 92.7% — but only because you
are taking fewer trades. You are buying a smoother ride by deleting winners, and
paying seven extra calendar days for it. Fees per pass improve by 0.07 across
that whole stretch, which does not cover it.

**Chosen: 0.25.** It removes the whole tail and nothing else.

### Effect summary

| | Off | 0.25 |
|---|---|---|
| EV per trade | +0.333 | **+0.404** |
| Win rate | 42.0% | **44.6%** |
| Pass both phases | 81.6% | **86.6%** |
| Days per challenge | 18 | 19 |
| Attempts per pass | 1.23 | **1.15** |

### Caveats

**It makes 2024 worse, and the quadrant table above shows why:** the effect
inverts. 2024 goes -0.060 -> -0.110, 2025 -0.176 -> -0.160, 2026 +0.333 ->
+0.404. Continuation breaks pay in a trending regime and reversal breaks pay in a
choppy one, so this is a directional regime bet rather than a law.

**It was one of five candidates.** Break strength, trend alignment (10-day drift)
and range efficiency were all rejected — non-monotone buckets, or effects that
failed to hold in both samples. A volume filter did survive testing (+0.391
against +0.080 for breaks on under 0.8x the range's median tick count) but was
dropped as impractical to judge in real time. Testing five filters across roughly
twenty buckets guarantees one looks good by chance; what earns this one a place
is that the direction holds in both samples and the mechanism states in a
sentence.

**Simulator agreement.** The offline sweep predicted 93% kept, +0.436 EV, 47.3%
WR and 89.1% pass at threshold 0.25. MT5 returned 93%, +0.404, 44.6% and 86.6% —
optimistic by the usual ~0.03 R.

### Implementation

`InpMinClosePos`, default `0.25`, `0` disables. The score is also written to
every row of the trade log as `close_pos`, so the threshold can be re-optimised
from a single backtest without re-running MT5.
