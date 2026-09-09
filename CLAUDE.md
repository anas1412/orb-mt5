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

Everything a run produces lives inside the repo, once. The pipeline used to
write the report and the charts into `~/orb` and then copy them in for GitHub
Pages, which left two of each and no way to tell which was current.

```
~/orb/
├── orb-engine-plan.md      design doc
├── creds.txt               accounts, offsets, paths (gitignored, chmod 600)
└── strategy/               <- this repo, and the only place output lands
    ├── CLAUDE.md
    ├── TimeZones.mqh       broker time <-> UTC <-> session time
    ├── Panel.mqh           on-chart control panel (toggle + editable settings)
    ├── TestTimeZones.mq5   asserts the time model
    ├── CheckBrokerOffset.mq5  measures the two broker inputs
    ├── BarDump.mq5         exports M1 bars from the tester
    ├── SyncDump.mq5        exports M1 bars from a LIVE chart, today included
    ├── DumpD1.mq5          exports the daily candles the EA reads (yesterday filter)
    ├── ORB.mq5             the EA
    ├── update.sh           the one command; tester.ini / dump.ini / sync.ini / d1.ini beside it
    ├── index.html          THE report and the Pages landing page (generated)
    ├── full-report.html    a redirect to index.html, kept because the old URL is linked
    ├── client-example.html the $1,000-account explainer (generated)
    ├── fundingpips-1step-flex.md  the account rules the benchmark models
    ├── trades/             one chart per trade (generated, drawn straight here)
    ├── trades-<spec>/      the same for a spec report
    ├── accounts/           broker logins, one .env per account (ignored; example.env tracked)
    └── research/           the pipeline, the builders and the data
        ├── *.py            the scripts you run: report_data, all_trades, build_*,
        │                   check_charts, coverage, merge_*, replay_today, spec, sim_offline
        ├── lib/            modules they import, never run: ctx, mt5paths, curve,
        │                   rules_svg, halves_svg
        ├── data/           generated json: report_data, trade_index, halves, replayed, client_data
        ├── out/<spec>/     everything a spec report produces
        ├── *.csv           the shipped datasets, at top level because they are linked externally
        ├── mt5.sh          the ONLY MetaTrader launcher: login block, journal watch, reset
        ├── report.sh, run_window.sh, run_cp050_mt5.sh
        └── studies/        the one-off scripts behind FINDINGS.md, not part of the pipeline

A script in `research/` puts `lib/` on the path with two lines at the top; `lib`
modules import each other by bare name. `ctx.py` knows it sits one level down --
`HERE` is `research/lib`, `RESEARCH` and `REPO` are derived from it, and getting
that wrong writes the report somewhere nobody looks.
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

MT5 build 6140, **portable** install. Data sits beside the executable, not in
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
bash update.sh --full       # re-run the whole tester from scratch, ~20 min
bash update.sh --push       # skip the confirmation before pushing
bash update.sh --account accounts/ftmo.env   # log into that broker account; else the saved session
YDAY=true bash research/run_window.sh 2026.01.01 2026.09.08   # one-off: yesterday filter ON
```

**The published results are 2026 only** -- `dates.from` in `asia-gold.toml`,
enforced by `ctx.in_range`, so the edge is never claimed on 2024 or 2025. A
spec may ask for more: `gold-0530-r60.toml` runs 2024-2026 because consistency
across all three years is the only thing it claims. The tester still starts in
2024 because those trades label the session dataset in `research/`, where the
quiet years serve as negative examples -- they are inputs to that file and
nothing else.

It checks coverage before launching anything, so a run with nothing new costs
0.03s instead of a minute and a half. **Running it is the statement that the
session is over** -- it does not wait out the 90-minute cap before believing
you. Whether a trade really resolved is decided by the bars in
`sim_offline.session`, which refuses one it cannot carry to an exit. A day with no trade leaves no row, so
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
| "Up to date" when a trade just closed | The guard waited for the 90-minute cap. A stop at minute five is a finished trade; ask whether it **resolved**, never how long it has been |
| A trade vanishes from a fresh full-year run | **Margin, and it was a knife-edge.** With 2% risk and ~2% margin on gold, a day whose stop is under 0.04% of price needs more than the whole balance in margin -- at *any* account size, since lots and free margin both scale with it. 20 Jan 2026 sat at ratio 1.00: rejected in a fresh window (1.05 lots needing $9,803 against $9,795 free), accepted in the original run purely on lot rounding. **Raising `Deposit` does not fix it** -- it moved the rounding and passed by luck; raising `Leverage` hides a real live constraint. `LotsFor()` now fits lots to free margin (`OrderCalcMargin`, 0.95 headroom) and logs `margin: ... sized down`, so the trade is taken smaller instead of rejected; R is size-independent so nothing published moves. `Deposit` stays 10000 |
| `pkill -x` never matches the tester agent | Its file name is 16 characters; the kernel truncates process names to 15. Use `pkill -f` with a bracketed pattern (`mt5_reset` does) |
| A reset aborts half-way, Wine left dirty | The callers run under `set -e`; a `pkill` that finds nothing returns 1. Every line of a sourced helper needs `\|\| true` |
| A Bash command kills its own shell | `pkill -f PATTERN` in the same command as a heredoc whose *text* contains the matched name -- the command line includes the heredoc. Keep the literal out of the command, or split into two commands |
| A fake login appears in the Navigator | **Never test with made-up credentials.** MetaTrader saves every attempted account to `accounts.dat`; a bogus `Login=1` shows up in the user's GUI and can become the terminal's last-used account, disconnecting the live EA |
| The tester ignores the dates asked for | It **clamps `ToDate`** to its history and reports the clamped value. That clamped date is the coverage record, and it is an *exclusive* end -- the day it names is the day it did not test |

### Bar coverage decides which holds are testable

`dump.ini` records broker hours 1-18, which is why `bars_XAUUSD.csv` stopped at
18:59 and why a 13:30 UTC session could not be tested past a 60-minute hold: a
summer entry sits at broker 17:45 and the file ended 74 minutes later. Capping
the hold there and calling it a rule was a data limit wearing a decision's
clothes.

`evening.ini` is the same dump for broker hours 19-23. `BarDump` appends to the
same `bars_XAUUSD.csv`, so running it adds the evening without touching what is
there. After that the 15:30 session tests cleanly to a five-hour hold, and the
60-minute cap became a measured choice: expectancy peaks at 60-75 minutes and
the worst losing run more than doubles without it.

Before trusting any hold length, check the room: `s["last"] - entry` per trade,
and report `n` every time. Requiring the full window and dropping the trades
that do not fit keeps only the fast winners -- that is how an 87%-win-rate NY
setup got invented once.

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

### The template describes the spec, not Asia

`template.html` held the session identity in its own prose -- "The Asia Opening
Range", "Monday to Thursday" five times, "00:00 to 00:14 UTC", "every trade it
produced in 2026" -- so **every spec report was an Asia report with a different
title**. The 13:30 pages said `00:14` six times each. Worse, the "why each rule
exists" table was 11 hardcoded Asia rows, one of which argues that a 60-minute
range is worse than a 15-minute one, printed under a report whose range is 60
minutes.

Identity now comes from `ctx`: `H1`, `LEDE`, `SHORT`, `OPEN_TXT`, `RANGE_TXT`,
`LAST_CANDLE`, `BOX_DONE`, `ENTRY_LAST`, `DAYS_TXT`, `DAYS_DASH`, `OFF_TXT`,
`WEEKDAYS`, `DIRECTION`. Rules of thumb:

- **Reasoning belongs to the spec that measured it.** `[notes].why` is a list of
  `[rule, reason]` pairs. A spec with none gets a line saying so, not another
  strategy's argument.
- **A hand-drawn diagram must refuse to draw the wrong strategy.**
  `rules_svg.fits()` compares the spec against `DRAWN_FOR` (15 candles, 15-min
  window, 2R, 90-min cap, half filter on) and `build()` returns `""` otherwise;
  `build_report.rules_block()` then generates a table from the spec instead.
- **`report_data.py` reads `ctx.WEEKDAYS`,** never `weekday() > 3`.
- A multi-year spec gets **one row per year** in place of quarters
  (`out['qlabel']`), and month rows labelled `Jan 24`. Keying on the month alone
  reported three Januaries as one.

`InpTradeLongs` / `InpTradeShorts` on the EA back `rules.direction`
(`both` / `long` / `short`). Both default true, so the published config is
untouched. New EA inputs must also be added to `tester.ini` -- `run_window.sh`
refuses a spec key with no line there rather than letting the tester ignore it.

### Numbers live in report_data.json

Never hand-write a figure into README, the report or the client page. They are
all generated from `report_data.json`, which is how the exits table once ended
up summing to +44.3 R under a +47.1 R headline.

### The report's risk selector

`index.html` carries an input for risk per trade, default 2.5%, capped at 2.5%.
Percent is `R x risk`, so the page does that arithmetic itself: every live
figure is a `<span data-pct="<R>">` and one loop multiplies. Three things it
must never compute -- pass rate, trades-to-pass, days-to-pass -- come out of a
barrier simulation and are **precomputed per risk** into `out['sweep']`, looked
up by `data-sweep="<key>"`. Interpolating a probability would be inventing one.

Rules that keep it honest, each of which was violated first:

- **Never reconstruct a losing run from an average loss.** The stop move halves
  some losses, so the mean loss is -0.86 R while the five that actually landed
  in a row summed **-5.10 R**. Averaging reports 10.7% at 2.5% and calls it
  safe; the real run is 12.8% and breaks a 12% limit. `out['run_worst']` holds
  the worst real sequence per length.
- **The daily limit is a barrier, not a footnote.** One trade a day means one
  trade *is* the day, so a loss past the daily cap ends the attempt whatever the
  running total says. Omitting it put the pass rate at 3% risk at 93.8% when the
  honest figure is 30%.
- **Never rescale a rounded percent.** Store R (`maxdd_r`, `curve` in R,
  `loss_avg_abs` unrounded) and multiply once at the end.
- **Nothing on the page may depend on risk without a `data-*` hook**, and every
  hook is filled server-side at the default so a JS-disabled reader gets a real
  report rather than blanks.
- The scale stops at 2.5% because above it there is nothing to choose: the worst
  run already breaks the maximum loss, and past 2.74% one worst-case trade
  breaches the daily limit alone.

## Docker

The engine in a container: Ubuntu 24.04, WineHQ stable, Xvfb, python3 +
matplotlib, the terminal binaries staged from a working install into
`docker/mt5/` (ignored by git), the EA compiled at build time -- the image is
refused if it does not compile. The layout inside is the host's layout exactly
(`/root/.wine_mt5/drive_c/Program Files/MetaTrader 5`, repo at
`/root/orb/strategy`), so every script runs unchanged.

```bash
docker build -f docker/Dockerfile -t orb-mt5 .        # ~15 min cold, seconds cached
docker run --rm --env-file accounts/ftmo.env \
  -v orb-bases:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Bases" \
  -v orb-tester:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Tester" \
  -v orb-config:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Config" \
  -v "$PWD/out:/out" orb-mt5 \
  bash research/report.sh strategies/asia-gold.toml 2026.01.01 2026.09.09
```

History, tester caches and Config are volumes; the image holds no account and
no data. **Without `--env-file` the run stops at once** with
`tester not started because the account is not specified` -- that line in the
journal means the container works and only the login is missing. Results are
copied to `/out` by the entrypoint.

Two things learned building it: Docker `RUN` is dash, so `${var//x/y}` needs a
`SHELL` line -- placed *after* the expensive layers, or it invalidates their
cache and Wine reinstalls; and the terminal reports build 6182 inside although
6140 was staged, so it updates itself on first start.

---

## Conventions

- Act on **closed bars only**. Index 0 is still forming.
- The EA must be **restart-safe**: rebuild state from history in `OnInit` and
  check `PositionSelect` by magic number. Recompiling reloads a live EA and
  wipes its memory.
- Skip a day cleanly when the range window has no bars (holiday, session break)
  rather than building a range from whatever happens to be there.
- Never commit `creds.txt`.
