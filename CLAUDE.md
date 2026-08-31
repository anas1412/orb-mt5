# ORB — Opening Range Breakout EA

One configurable MQL5 Expert Advisor: any session (Asia / London / New York),
any range length, any signal timeframe, any symbol, with correct daylight
saving handling.

Full design lives in `~/orb/orb-engine-plan.md`. Read it before changing
behaviour. This file covers how to *work on* the code.

---

## Hard rule: OS-agnostic, always

The EA must compile and run unchanged on Windows and on Linux/Wine. The `.ex5`
is platform-neutral bytecode; keeping the source neutral takes four rules:

| Rule | Why |
|---|---|
| **No host clock** | `TimeGMT()` / `TimeLocal()` read the OS. Windows and Wine disagree, and the Strategy Tester lies about both. Derive UTC from `TimeCurrent()` via `TimeZones.mqh` |
| **No absolute paths** | Use `MQL5\Files\` through `FileOpen()`, which resolves per-terminal. Never a drive letter, never a `~` |
| **No OS calls** | No `ShellExecuteW`, no `WinExec`, no DLL imports. DLLs break under Wine and need a permissions toggle on Windows |
| **Relative `tester.ini`** | Keep it beside the EA; reference reports by name, not path |

The tempting violation is logging. Use `Print()` to the Experts journal, not a
file at a path you invented.

---

## Layout

Source of truth is this repo. Files are **symlinked** into the MT5 tree —
verified working under Wine, so there is no copy step and no `docker cp`.

```
~/orb/
├── orb-engine-plan.md      design doc
├── creds.txt               accounts, offsets, paths (gitignored, chmod 600)
└── strategy/               <- this repo
    ├── CLAUDE.md
    ├── TimeZones.mqh       broker time <-> UTC <-> session time
    ├── Panel.mqh           on-chart control panel (toggle + editable settings)
    ├── TestTimeZones.mq5   asserts the time model
    ├── CheckBrokerOffset.mq5  measures the two broker inputs
    ├── BarDump.mq5         exports M1 bars from the tester
    ├── SyncDump.mq5        exports M1 bars from a LIVE chart, today included
    ├── ORB.mq5             the EA
    └── research/           the study, the builders and the data
```

Symlinked to:

```
<MT5>/MQL5/Include/TimeZones.mqh
<MT5>/MQL5/Include/Panel.mqh
<MT5>/MQL5/Scripts/TestTimeZones.mq5
<MT5>/MQL5/Experts/ORB.mq5
```

Re-create a link after adding a file:

```bash
MT5=~/.wine_mt5/drive_c/"Program Files"/"MetaTrader 5"
ln -sf ~/orb/strategy/ORB.mq5 "$MT5/MQL5/Experts/ORB.mq5"
```

---

## Terminal

MT5 build 6090, **portable** install. Data sits beside the executable, not in
`AppData/Roaming`.

| | path |
|---|---|
| Linux/Wine (this box) | `~/.wine_mt5/drive_c/Program Files/MetaTrader 5/` |
| Windows portable | the install dir |
| Windows standard | `%APPDATA%\MetaQuotes\Terminal\<hash>\` |

Every launch needs `/portable` on this box, or MT5 loads a different data
directory and appears to have lost the EA and all history.

---

## Commands

### Compile

```bash
cd ~/.wine_mt5/drive_c/"Program Files"/"MetaTrader 5" && \
WINEPREFIX=~/.wine_mt5 WINEDEBUG=-all wine MetaEditor64.exe \
  /compile:"MQL5\Scripts\TestTimeZones.mq5" /log
```

```bat
REM Windows
"C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"MQL5\Scripts\TestTimeZones.mq5" /log
```

### Read the compile log

Written next to the source, UTF-16LE, on both platforms:

```bash
iconv -f UTF-16LE -t UTF-8 "<...>/MQL5/Scripts/TestTimeZones.log" | tail -3
```

### Backtest

```bash
cd ~/.wine_mt5/drive_c/"Program Files"/"MetaTrader 5" && \
WINEPREFIX=~/.wine_mt5 wine terminal64.exe /portable /config:tester.ini
```

### GUI

```bash
WINEPREFIX=~/.wine_mt5 wine "C:\Program Files\MetaTrader 5\terminal64.exe" /portable
```

---

## Toolchain gotchas

These cost time to rediscover:

- **`/compile:` must be a path relative to the terminal directory, and you must
  `cd` there first.** An absolute `C:\...` path makes MetaEditor exit silently
  producing no `.ex5` and no log — it looks like a hang, not an error.
- **MetaEditor exits `1` on a clean compile.** Judge success by the log's
  `Result: 0 errors, 0 warnings` line, never by exit code.
- **Every MT5 log is UTF-16LE** — terminal journal, compile log, tester report.
  `grep` finds nothing until you `iconv`.
- **libEGL / pci id warnings on stderr are noise.** Wine talking to the GPU;
  unrelated to the compile.
- **A command-line compile does not refresh the running terminal.** MT5 caches
  the expert list in `MQL5/experts.dat`; the tester reads the cache, not the
  folder, so a freshly compiled EA is missing from the dropdown. Fix with
  Navigator > right-click > Refresh, or restart the terminal. Compiling with F7
  inside the GUI MetaEditor notifies the terminal and avoids it.
- **`tester.ini` bool inputs reject inline `;` comments.** `InpTradeFri=false ; note`
  parses as true and the run silently ignores the setting. Integers and doubles
  tolerate them; bools do not. Put the comment on its own line above.
- **A `sed`-driven parameter sweep fails silently if the key is absent from
  `tester.ini`.** Every pass then uses the compiled default and the results come
  back identical. Identical row counts across a sweep is the tell.
- Symlinked sources compile correctly. Verified, not assumed.

---

## Time model

`TimeZones.mqh` is the foundation everything else sits on. It never reads the
host clock — every function takes an instant from the caller.

```
broker time (TimeCurrent())
      |  BrokerWinterOffset + BrokerFollowsUSDST
     UTC        <-- single source of truth
      |  that zone's own DST rule
session time (UTC / London / NewYork / Tokyo / Sydney / Broker)
```

Two deliberate approximations, both documented at their call site:

- `BrokerOffsetSeconds` breaks the offset/DST circular dependency using the
  winter offset, so it can misread the switch instant itself — small hours of a
  Sunday, no session open. Do not "fix" it by feeding the result back in; that
  trades a harmless error for an oscillation.
- Sydney's switch hour lands inside the weekend market gap either way.

**Zone rules are hardcoded** — MQL5 has no timezone database.

| Zone | Base | DST |
|---|---|---|
| UTC | +0 | none |
| London | +0 | EU dates |
| NewYork | −5 | US dates |
| Tokyo | +9 | none, ever |
| Sydney | +10 | AU dates, spans new year |

### Broker offset — partially known

Measured on FTMO-Demo, August 2026: **server = UTC+3**, derived from terminal
logs (they stamp lines in PC time but report the previous authorization in
server time). Implies a +2 winter offset.

**`BrokerFollowsUSDST` is still unverified.** August is DST under both US and
EU rules, so the measurement cannot distinguish them. It matters for the ~1
week each autumn when the EU has fallen back and the US has not — the range
opens an hour wrong for exactly that stretch and nowhere else.

Run `CheckBrokerOffset` to settle it. It prints the weekly open in broker time
across the Oct 2025 and Nov 2025 switch weekends. The week opens at 17:00 New
York, which is 21:00 UTC on EDT and 22:00 UTC on EST, so:

- **constant** broker hour across both weekends -> broker follows **US** dates
- **shifts** at the end of October and back in November -> **EU** dates

Needs M1 history back to Oct 2025 for the probe symbol.

---

## Status

Shipped. The EA trades the Asia range on gold, is released, and the study is
published at `anas1412.github.io/orb-mt5`.

| # | Step | State |
|---|---|---|
| 1 | Time module | done, asserted by `TestTimeZones` |
| 1b | Broker offset probe | done — FTMO demo measured at UTC+3 summer, +2 winter |
| 2 | `ORB.mq5` | done, plus `Panel.mqh` for on-chart control |
| 3 | Compile toolchain | working headless under Wine |
| 4 | M1 + real tick history | cached 2024-01-02 onward for XAUUSD |
| 5 | Backtest | done — see `research/` and `report_data.json` |
| 6 | Deploy | live on an FTMO demo, panel starts OFF |

**`InpFollowsUSDST` is still unverified** and stays that way until an autumn
switch weekend has M1 history behind it. It matters for about one week each
October.

---

## Adding new trades

```bash
bash update.sh              # everything since the last run, ~1.5 min
bash update.sh --force      # rebuild even when nothing new has closed
bash update.sh --full       # re-test 2024 onward from scratch, ~20 min
bash update.sh --push       # skip the confirmation before pushing
```

It checks coverage before launching anything, so a run with nothing new costs
0.03s instead of a minute and a half. A day with no trade leaves no row, so
coverage cannot be read off the trade files -- it comes from the tester's own
reported range in `tested_through.txt` plus whatever `replayed.json` added on
top. Missing days need nothing special: it resumes from the marker and tests
everything since.

Nine steps: check the terminal is closed, pull today's bars from a live chart,
dump the days not on file, test the days not tested, replay what the tester
would not, rebuild every page, **audit**, refresh the shipped CSVs, commit and
push.

**Incremental by default**, because each session is independent -- one trade,
opened and closed inside 90 minutes, carrying nothing into the next. A few new
days test in under a second; 2024 onward takes about ninety seconds per
configuration and re-imports every month of ticks. Only position size is not
independent, so R comes from the tester and the dollar columns are re-derived
from the continuing balance in `merge_trades.py`.

`all_trades.py` redraws only what changed, keyed on a signature over the trade
row, that day's bars, its position in the year and the file's own contents --
so editing the drawing code redraws everything by itself. `--all` forces it.
Nothing in a chart may depend on the number of trades, or every chart goes
stale whenever one is added.

`check_charts.py` is the step that matters. It compares the charts, filenames,
gallery captions and totals back to the tester CSV and stops the run rather
than publishing. It exists because a wrong chart does not look wrong.

### Things that fail silently here

Every one of these looked like something else first.

| Symptom | Cause |
|---|---|
| A step "runs slowly" for ever | The `.ini` had no `[Tester]` section. MetaTrader opens the GUI and waits. Always launch through `run_mt5`, which checks the section and passes a timeout |
| An `.ini` edit empties the file | **Every `.ini` in the MT5 tree is a symlink back to this repo.** `sed x.ini > "$MT5/x.ini"` truncates its own input. Use `sed -i` on the repo copy |
| MetaTrader exits 0 and logs nothing | Wine is holding state after a `kill -9`. `wineserver -k` clears it; `update.sh` does this in step 1 |
| A window reports "0 trades" | A second terminal launched while one was still closing and exited immediately. `run_window.sh` verifies against the tester's own log, since an empty result is a legitimate answer |
| A wait loop never finishes | `pgrep -f "bash update.sh"` **matches its own command line.** Wait on a PID, or bracket a character: `pgrep -f 'update[.]sh'` |
| An error message never prints | `set -e` kills the script on a failed command substitution. `x=$(cmd || true)` |
| The tester ignores the dates asked for | It **clamps `ToDate`** to its history and reports the clamped value. That clamped date is the coverage record, and it is an *exclusive* end -- the day it names is the day it did not test |

### The Strategy Tester cannot see today

MetaTrader's history server only serves bars up to the last **completed**
trading day. Today's bars exist in a live chart, because the terminal builds
them from the tick stream, but they never reach the history base the tester
reads. The tester then **clamps its date range instead of failing**. The only
tell is a log line that disagrees with what was asked for:

    XAUUSD: history synchronized from 2023.01.03 to 2026.08.28

Opening the terminal and letting it sync does **not** fix this, so do not ask
the user to. Three caches stack up and clearing the wrong one looks like
progress:

| Cache | Goes stale? |
|---|---|
| `Bases/` | terminal's own, updated by a live chart |
| `Tester/bases/` | the agent's private copy — **yes**, wipe it after new data |
| `Tester/cache/*.tst` | preprocessed ticks, keyed by symbol and date range |

To include today: `SyncDump.mq5` on a live chart pulls the bars, then
`sim_offline.py` replays the EA over them. It self-checks against the tester
and prints the comparison. Mark any replayed row in `DATA.md` and replace it
with a real one on the next run.

### Three traps in the chart code

Each of these shipped a chart that disagreed with its own data.

- **A short's stop sits on the ASK; the candles draw the BID.** Walking bids
  only makes a short look like it survived a stop it really hit. 27 Aug 2026
  ran on to the target and drew its exit marker there, under a title reading
  `LOSS -1.03 R`. Adverse price for a sell is `high + spread`.
- **Never re-derive an outcome the run already recorded.** Only the exit *time*
  is unknown; take the kind and the level from the CSV. Anything computed twice
  from different data eventually disagrees, and the picture is what a reader
  trusts.
- **The -0.5R stop is not live until the trade has been +0.5R up.** Searching
  for that level from the entry bar "stops" trades before the move that created
  the level could have armed.

Intrabar ordering is the standing limitation: an M1 bar will not say whether
its high or its low came first, which decides whether the stop move armed
before the stop was hit. It affects the exit *time* on a handful of charts, not
the recorded result. Check it before trusting a replayed day.

### Numbers live in report_data.json

Never hand-write a figure into README, the report, the deck or the client page.
They are all generated from `report_data.json`, which is how the exits table
once ended up summing to +44.3 R under a +47.1 R headline.

---

## Conventions

- Act on **closed bars only**. Index 0 is still forming.
- The EA must be **restart-safe**: rebuild state from history in `OnInit` and
  check `PositionSelect` by magic number. Recompiling reloads a live EA and
  wipes its memory.
- Skip a day cleanly when the range window has no bars (holiday, session break)
  rather than building a range from whatever happens to be there.
- Never commit `creds.txt`.
