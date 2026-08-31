# Data files

The raw bars are here, and so is every script that turns them into the rest. You
do not need MetaTrader to reproduce any of this — only to regenerate the raw
bars themselves, which is what `BarDump.mq5` does.

## bars_XAUUSD_2024_2026.csv

**The raw input. Everything else here is derived from this file.**

740,251 one-minute bars, 2 Jan 2024 to 31 Aug 2026, broker hours 01 to 18
(broker is UTC+3 in summer, UTC+2 in winter, so this covers roughly 22:00 to
16:00 UTC). Exported from MetaTrader with `BarDump.mq5`.

    time,open,high,low,close,ticks,volume
    2024.01.02 01:05,2063.10,2063.35,2062.95,2063.20,88,0

`time` is broker time, not UTC. `ticks` is tick volume, populated on every row.
`volume` is real volume, always 0 — the broker does not report it for CFDs, so
tick count is the only activity measure available.

40 MB, plain CSV, no compression. It is in the repo so you never need
MetaTrader or a broker feed to rebuild anything below it.

## sessions_2024_2026.csv

One row per Asia session, 688 of them. **This is the dataset for session-quality
modelling** — the question of whether a session is worth trading at all, rather
than which trades to filter.

Built by `build_sessions.py` from raw M1 bars.

| Feature (known at 00:15 UTC) | Meaning |
|---|---|
| `range_high` `range_low` `range_usd` | the 15-minute box |
| `price_ref` | close of the 00:14 candle, the reference price |
| `range_pct` | `range_usd / price_ref * 100` |
| `close_pos` | where the 00:14 candle closed in the box, 0 = low, 1 = high |
| `range_ticks` | tick volume during the range, an activity proxy |
| `range_dir` | last close minus first open across the range |
| `prev_range_pct` `med5_range_pct` `med20_range_pct` | rolling context, prior sessions only |
| `dow` | weekday |

| Label (what happened after) | Meaning |
|---|---|
| `broke` `break_min` `break_dir` | first M1 close outside the box, by 00:29 |
| `same_half` | did the break match the half the range closed in |
| `traded_by_ea` | would the EA have taken it |
| `R` `exit_kind` `spread_pts` | realised result, where one exists |

**No lookahead.** Every feature is computable at 00:15 UTC, before any entry
decision exists. The rolling columns use earlier sessions only.

**It reproduces the EA.** Filter to 2026 and Monday–Thursday: 137 eligible
sessions, 75 trades, 53.3% win rate, +0.627 R per trade, +47.0 R total —
identical to the MT5 backtest, reached from raw bars by a separate path.

**Rows cover Monday–Friday; the EA trades Monday–Thursday.** Filter on `dow`
before comparing.

## One row is not from the Strategy Tester

**`2026.08.31 03:16` in both trade files was replayed from the bars, not
tested.** Worth knowing before you diff anything against your own run.

MetaTrader's history server only serves bars up to the last *completed*
trading day. Today's bars exist in a live chart, because the terminal builds
them from the tick stream, but they never reach the history base the Strategy
Tester reads. So the tester quietly clamps its date range instead of failing,
and the current session is simply absent. The tell is a log line that disagrees
with the range you asked for:

    XAUUSD: history synchronized from 2023.01.03 to 2026.08.28

`research/sim_offline.py` replays the EA over raw bars to cover that one day.
Run it with no arguments and it checks itself against the tester across 2026:
it picks the same 74 days, in the same direction, and agrees within 0.10 R on
67 of them. The seven it misses are all intrabar ordering — an M1 bar cannot
say whether its high or its low came first, which matters when the stop move
and the stop sit inside the same minute. That ambiguity does not arise on
31 August: the trade was stopped five minutes in, having never traded close to
the +0.5R trigger.

R is set to −1.033, the mean of every full stop-out in 2026, so the row carries
the same commission and spread drag as the tested ones rather than a clean
−1.000 that would flatter the total.

Re-run the tester tomorrow and this row is replaced by a real one.

## trades_live_config.csv

270 trades, the configuration actually traded: half-of-the-range filter on at
0.50, Friday off, stop at the midpoint, 2R target, stop move +0.5R → −0.5R,
90-minute cap. 75 of these are 2026, and they are the headline numbers.

## trades_all_breaks.csv

364 trades, same configuration with the half filter **off**, so every break that
happened carries its outcome. Use this when you need both classes — the trades
the filter allowed and the ones it rejected.

Columns in both: `entry_time`, `range_pts`, `spread_pts`, `mins_after_range`,
`dir`, `entry`, `sl`, `risk_money`, `profit_money`, `R`, `exit`, `close_pos`.

Note `close_pos` here is direction-adjusted — already flipped for sells, so
≥ 0.50 always means "broke the half it closed in". In
`sessions_2024_2026.csv` it is raw, 0 = low and 1 = high. Different conventions,
same idea.

## A caveat on all of it

`R` divides realised money by the price risk at entry. Commission is inside the
money but not inside the risk, so a clean full stop reads about −1.03 to −1.05 R
rather than exactly −1.00.
