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
              close after 60 minutes if neither level is hit
```

## Results in one table

XAUUSD, Asia session, MT5 real ticks, 2% risk per trade, one trade per day.
Full analysis: **[research/report.html](research/report.html)** ·
**[research/FINDINGS.md](research/FINDINGS.md)**

| Period | Trades | EV / trade | Win rate | Median range |
|---|---|---|---|---|
| **2026** | 119 | **+0.333 R** | **42.0%** | 1 108 pts |

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
| `InpMaxHoldMinutes` | `60` | per-position cap, measured from its own fill |

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
| `InpTradeMon` … `InpTradeFri` | `true` | day-of-week filter |

### Stops, targets, risk

| Input | Default | Meaning |
|---|---|---|
| `InpSLMode` | percent of range | percent of range / fixed points |
| `InpSLPercentOfRange` | `50` | 50 = midpoint, 100 = opposite boundary |
| `InpStopMoveAtR` | `0.5` | move the stop once the trade reaches this many R (0 = off) |
| `InpStopMoveToR` | `-0.5` | where it goes, signed: 0 = entry, −0.5 = half the risk still on |
| `InpTPMode` | RR | RR / fixed points / multiple of range / none |
| `InpRR` | `2.0` | reward-to-risk multiple |
| `InpLotMode` | risk percent | fixed lots / percent of balance |
| `InpRiskPercent` | `2.0` | risk per trade |
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
