# Data files

Everything here is generated, and every generator is in this folder. If you want
to rebuild from scratch rather than trust these, `BarDump.mq5` exports the M1
bars and `run_cp050_mt5.sh` produces the trade CSVs.

## sessions_2024_2026.csv

One row per Asia session, 682 of them. **This is the dataset for session-quality
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

**It reproduces the EA.** Filter to 2026 and Monday–Thursday: 132 eligible
sessions, 72 trades, 54.2% win rate, +0.654 R per trade, +47.1 R total —
identical to the MT5 backtest, reached from raw bars by a separate path.

**Rows cover Monday–Friday; the EA trades Monday–Thursday.** Filter on `dow`
before comparing.

## trades_live_config.csv

267 trades, the configuration actually traded: half-of-the-range filter on at
0.50, Friday off, stop at the midpoint, 2R target, stop move +0.5R → −0.5R,
90-minute cap. 72 of these are 2026, and they are the headline numbers.

## trades_all_breaks.csv

361 trades, same configuration with the half filter **off**, so every break that
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
