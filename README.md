# ORB — Opening Range Breakout for MetaTrader 5

A single configurable MQL5 expert advisor that trades the breakout of a session's
opening range. Every parameter is an input — session, timezone, range length,
signal timeframe, stop placement, target, stop management, risk — so one binary
covers any session on any symbol without recompiling.

Runs identically on **Windows** and on **Linux under Wine**. The backtests in
[`research/`](research/) are reproducible on either.

```
00:00 UTC ─── mark the 15-minute range ─── 00:15 ─── watch for an M1 close
              outside it, up to 00:29 ─── enter at market ─── stop at the range
              midpoint, target 2R ─── at +0.5R pull the stop to −0.5R ───
              close after 90 minutes if neither level is hit
```

## Results in one table

XAUUSD, Asia session, MT5 real ticks, 2% risk per trade, one trade per day.
Full analysis: **[research/report.html](research/report.html)** ·
**[research/FINDINGS.md](research/FINDINGS.md)**

| Period | Trades | EV / trade | Win rate | Median range |
|---|---|---|---|---|
| **2026** | 88 | **+0.580 R** | **51.1%** | 1 108 pts |

Results are regime-dependent. Gold's realised volatility ran above 50% in 2026
against a long-run norm near 15–16%, and the Asia opening range widened 6.4×.
The full three-year breakdown, including the periods this configuration loses,
is in [research/report.html](research/report.html).

Also tested and rejected: **London** loses in every configuration; **New York**
is flat at every range length despite having the widest ranges of the three
sessions.

## Install

Clone anywhere, then link or copy the sources into your terminal's `MQL5` tree:

```
MQL5/Include/TimeZones.mqh
MQL5/Experts/ORB.mq5
MQL5/Scripts/TestTimeZones.mq5
MQL5/Scripts/CheckBrokerOffset.mq5
MQL5/Experts/BarDump.mq5          # research tool, optional
```

**Linux/Wine** — symlinks work and keep git as the single source of truth:

```bash
MT5=~/.wine_mt5/drive_c/"Program Files"/"MetaTrader 5"
ln -sf "$PWD/TimeZones.mqh"         "$MT5/MQL5/Include/"
ln -sf "$PWD/ORB.mq5"               "$MT5/MQL5/Experts/"
ln -sf "$PWD/TestTimeZones.mq5"     "$MT5/MQL5/Scripts/"
ln -sf "$PWD/CheckBrokerOffset.mq5" "$MT5/MQL5/Scripts/"
```

**Windows** — copy, or use `mklink`:

```bat
set MT5=C:\Program Files\MetaTrader 5
copy TimeZones.mqh "%MT5%\MQL5\Include\"
copy ORB.mq5 "%MT5%\MQL5\Experts\"
copy TestTimeZones.mq5 CheckBrokerOffset.mq5 "%MT5%\MQL5\Scripts\"
```

## Compile

```bat
REM Windows
scripts\compile.bat
```

```bash
# Linux / Wine
scripts/compile.sh
```

Two things that will waste your afternoon otherwise:

- **`/compile:` must be a path relative to the terminal directory, and you must
  be standing in that directory.** An absolute `C:\...` path makes MetaEditor
  exit silently with no `.ex5` and no log — it looks like a hang, not an error.
- **MetaEditor returns exit code 1 on a clean compile.** Judge success by the
  log's `0 errors, 0 warnings` line, never by the exit code.

MT5 writes every log as UTF-16LE, so on Linux use
`iconv -f UTF-16LE -t UTF-8` before grepping.

## Verify before trading

```
TestTimeZones      → expect "18 passed, 0 failed"
CheckBrokerOffset  → prints your broker's UTC offset and DST ruleset
```

`TestTimeZones` asserts every session open against a known UTC answer across
every daylight-saving switch — Tokyo 09:00 must be 00:00 UTC on all dates, New
York 09:30 must be 14:30 UTC on EST and 13:30 on EDT, and so on. It needs no
broker connection. **Run it first.** If the clock layer is wrong, every range
opens at the wrong minute and the backtest is meaningless.

## Reproduce the backtest

Both platforms read the same [`tester.ini`](tester.ini).

```bat
REM Windows — close the GUI terminal first, MT5 refuses two instances
scripts\backtest.bat
```

```bash
# Linux / Wine
scripts/backtest.sh
```

Set `MT5_DIR` if your terminal is not at the default path. Requires **real tick
history** for the symbol — download it in the terminal before the first run.

Each closed trade appends a row to `Common\Files\ORB_<symbol>_<magic>_tester.csv`
with the range size, spread, minutes-after-range, realised R and exit reason.
That file is what the analysis scripts consume.

## Inputs

### Session

| Input | Default | Meaning |
|---|---|---|
| `InpTimeZone` | `TZ_UTC` | which clock the session follows — UTC / London / NewYork / Tokyo / Sydney / Broker |
| `InpStartHour`, `InpStartMinute` | `0`, `0` | session open, in that zone's local time |
| `InpRangeMinutes` | `15` | range length |
| `InpSignalTF` | `PERIOD_M1` | confirmation candle |
| `InpNoEntryAfterMin` | `15` | stop looking this many minutes after the range closes |
| `InpForceCloseMin` | `360` | flatten everything this long after the range closes (backstop) |
| `InpMaxHoldMinutes` | **`90`** | per-position cap, measured from its own fill |

`InpTimeZone` answers *"which clock does this session follow?"*, not *"where is
this asset from"*. Tokyo never observes DST, so `Tokyo 09:00` and `UTC 00:00` are
the same instant forever — while `NewYork 19:00` would drift an hour for eight
months of the year.

### Broker clock

| Input | Default | Meaning |
|---|---|---|
| `InpWinterOffset` | `2` | hours the broker's server sits ahead of UTC in winter |
| `InpFollowsUSDST` | `true` | broker switches on US dates; `false` for EU dates |

Find yours with `CheckBrokerOffset`, or compare a D1 candle's start time to UTC.

### Entry

| Input | Default | Meaning |
|---|---|---|
| `InpEntryMode` | market on close | market / stop resting at the level / limit retest |
| `InpMaxTradesPerDay` | `1` | counted from deal history, so it survives a reload |
| `InpMaxSpreadPoints` | `0` | skip if the spread is wider (0 = off) |
| `InpMinRangePoints`, `InpMaxRangePoints` | `0`, `0` | absolute range filters (0 = off) |
| `InpRangeLookback` | `0` | rolling filter: sessions to compare against (0 = off) |
| `InpMinRangeRatio` | `1.25` | rolling filter: range must be this multiple of their median |
| `InpMinClosePos` | **`0.50`** | trade only the half the range closed in — see below (0 = off) |
| `InpTradeMon` … `InpTradeThu` | `true` | day-of-week filter |
| `InpTradeFri` | **`false`** | Friday is the only losing day — 20.8% win rate |

**`InpMinClosePos` at `0.50` is the half-of-the-range rule:** split the range box
in half, and trade only in the direction of the half the final range bar closed
in. Closed in the top half → an up-break is tradeable and a down-break is
skipped; closed in the bottom half → the mirror image. No arithmetic needed at
the chart.

Breaking the other half means price crossed the entire range first — a reversal
wearing a breakout's clothes. On 2026 real ticks, Monday–Thursday:

| Which half broke | n | WR | EV | Total R | Total % | |
|---|---|---|---|---|---|---|
| **Broke the half it closed in** | 72 | **52.8%** | **+0.615** | **+44.3** | **+88.6%** | trade |
| Broke the opposite half | 23 | 30.4% | +0.049 | +1.1 | +2.2% | skip |
| Every break, no filter | 95 | 47.4% | +0.478 | +45.4 | +90.9% | — |

Skipping those 23 gives up 1.1 R and buys a 5.4-point higher win rate. Other
values are supported — the input is a 0–1 position, so `0.25` cuts only the
worst quarter — but `0.50` is the one you can apply by eye. Full sweep in
[§8 of the findings](research/FINDINGS.md).

### Stops, targets, risk

| Input | Default | Meaning |
|---|---|---|
| `InpSLMode` | percent of range | percent of range / fixed points |
| `InpSLPercentOfRange` | `50` | 50 = midpoint, 100 = opposite boundary |
| `InpStopMoveAtR` | `0.5` | move the stop once the trade reaches this many R (0 = off) |
| `InpStopMoveToR` | `-0.5` | where it goes, signed: 0 = entry, −0.5 = half the risk still on |
| `InpTPMode` | RR | RR / fixed points / multiple of range / none |
| `InpRR` | `2.0` | reward-to-risk multiple |
| `InpLotMode` | risk percent | fixed lots / percent of balance / **fixed cash** |
| `InpRiskPercent` | `2.0` | risk per trade, percent of the *current* balance — this compounds |
| `InpRiskMoney` | `100.0` | risk per trade in account currency, used when `InpLotMode = LOT_RISK_MONEY` |
| `InpShowPanel` | `true` | on-chart control panel (off in non-visual backtests regardless) |

### Which sizing mode to use

`LOT_RISK_PERCENT` takes 2% of the **current** balance, so the cash at risk grows
as the account grows. Every backtest in `research/` assumes the opposite: a flat
2% of the **starting** balance, never compounded. `LOT_RISK_MONEY` is what
reproduces those numbers live — on a 5 000 account, 100 a trade whether you are
up or down.

Verified on a fresh 5 000 account, 2026 only: 72 trades, risk 61.54–99.96 a
trade (lot rounding only ever rounds *down*), +47.1 R = **+4 708 = +94.2%** —
identical to the report.

One thing to know: a fixed cash risk with a *narrow* stop demands a *large*
position. A 2-point gold stop at 100 risk is about half a lot, roughly 2 400 of
margin at 1:100. Fine on a funded 5 000, but a drawn-down account can have an
order rejected with `10019 not enough money` — the trade is skipped and logged,
not silently mis-sized.

### On-chart panel

| Row | Control |
|---|---|
| `TRADING ON / OFF` | master switch, **starts OFF** |
| Risk per trade | value, plus a `%` / currency button that switches sizing mode |
| Reward : risk | the target, in R |
| Session start | `HH:MM` UTC — when the range begins |
| Range length | minutes the range spans |
| Break window | minutes after the range close that a break still counts (0 = no limit) |
| Stop move | `ON` / `OFF` |
| move at / move to | the two stop-move levels, greyed out while the stop move is off |

The `%` / currency button switches between percent of the current balance
(compounds) and a fixed cash risk (does not). The row label says which you are
in, so the number can never be ambiguous.

**Trading starts OFF.** Attaching the EA never opens a position on its own — you
switch it on deliberately. The one exception is when there is no panel to switch
it on with (a non-visual backtest, or `InpShowPanel = false`), where the inputs
govern and trading is enabled; otherwise every backtest would take zero trades.

Changing the session start or the range length applies **from the next session**,
not retroactively — the panel says so in the journal when you change them. The fields are locked unless trading is **off** *and* there is **no open
position** — the stop-move logic recovers a trade's original risk from its take
profit divided by RR, so letting RR change mid-trade would move the stop to the
wrong price. Locking removes the possibility instead of guarding against it.

Switching trading off stops **new entries only**. The stop move, the time cap and
the force close keep running, so an open position is never abandoned.

Settings persist per chart in terminal globals, so a recompile does not reset
them. The panel never loads or saves in the tester, so a live toggle cannot leak
into a backtest.
| `InpMaxDailyLossPct` | `3.5` | stop opening trades once the **account** is down this much today (0 = off) |
| `InpMagic` | `20260821` | give each chart its own value when running several instances |
| `InpWriteCsv` | `true` | write the per-trade research log |

`InpMaxDailyLossPct` sums every deal on the account since broker midnight,
not just this EA's, plus open floating P&L. Running one instance per session
means several EAs that cannot see each other — this is what stops the third
trade of the day breaching a prop firm's daily limit.

## What the study found

Ten rules, each measured rather than assumed. Detail and numbers in
[research/report.html](research/report.html).

1. **Only the Asia session works**, and only in the 2026 volatility regime.
2. **Shortest range, fastest candle.** 15 min / M1 beats 30 / M3 and 60 / M5.
3. **Never tighten the stop inside noise.** A quarter-range stop loses 0.27 R per
   trade; a breakeven stop-move turns a profitable configuration into a losing
   one.
4. **RR 2, never RR 1.** Roughly five times the expectancy.
5. **A late breakout is a bad breakout.** Breaks after minute 15 drag EV from
   +0.375 to +0.181.
6. **Optimise pass rate, not profit factor** — for a funded-account challenge
   they choose different parameters, and the highest-EV setup ranks eleventh.
7. **Win rate is worth paying for, but only if it comes free** — from better
   entries, not from a nearer target.
8. **Range size is necessary, not sufficient.** New York has the widest ranges of
   any session and no edge.
9. **Speed is nearly free; risk sizing is not.** More trades per day barely dents
   pass rate; changing risk per trade moves it 15–30 points.
10. **Distrust anything inside ±0.05 R** — the simulator's measured error against
    MT5.

## Repository layout

```
ORB.mq5                    the expert advisor
TimeZones.mqh              broker time ↔ UTC ↔ session time, DST-aware
TestTimeZones.mq5          18 assertions over the time model
CheckBrokerOffset.mq5      measures your broker's offset and DST ruleset
BarDump.mq5                records M1 bars for offline research
tester.ini                 backtest configuration, both platforms
dump.ini                   bar-recorder configuration
scripts/                   compile and backtest, .sh and .bat
research/                  the analysis harness and write-ups
  report.html              full research report
  FINDINGS.md              same content as markdown
  sweep.py                 offline replay engine, validated against MT5
  mt5paths.py              locates Common\Files; override with MT5_COMMON
```

The offline harness exists because the Strategy Tester needs ~90 seconds per
real-tick pass over 2.6 years, so 600 configurations would take hours. `sweep.py`
replays recorded M1 bars instead, and agrees with MT5 to within 0.03 R. Use it to
shortlist, MT5 to confirm.

On Windows, point the analysis scripts at your data folder:

```bat
set MT5_COMMON=%APPDATA%\MetaQuotes\Terminal\Common\Files
```

## Requirements

- MetaTrader 5 build 4000+ (developed on 6090)
- Real tick history for your symbol
- Python 3.9+ for the research scripts — standard library only, no dependencies

## Not financial advice

This is a research artefact. The headline result rests on 119 trades in a single
year on a single symbol, with no out-of-sample data left. Demo test thoroughly,
and read [§13 of the report](research/report.html) on where the numbers are soft
before risking anything.

## Licence

MIT
