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
    ├── TestTimeZones.mq5   asserts the time model
    └── ORB.mq5             the EA (not written yet)
```

Symlinked to:

```
<MT5>/MQL5/Include/TimeZones.mqh
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
opens an hour wrong for exactly that stretch and nowhere else. Settle it by
reading a late-October M1 bar out of `Bases/<BROKER>/history`.

---

## Status

| # | Step | State |
|---|---|---|
| 1 | Time module | written, compiles clean — **not yet run** |
| 2 | `ORB.mq5` | not started |
| 3 | Compile toolchain | working headless under Wine |
| 4 | M1 + real tick history | cached for EURUSD, GBPUSD, USDCHF, USDJPY, XAUUSD, US100.cash |
| 5 | One backtest by hand | blocked on 2 |
| 6+ | Full backtest, optimize, deploy | — |

**Step 1 is the gate.** Run `TestTimeZones` on any chart and confirm every
assertion passes before writing a line of trading logic.

### Blocked on the user

- Working demo login — both FTMO demos expired ("Invalid account")
- First symbol and first session to test

Neither blocks steps 1–3.

---

## Conventions

- Act on **closed bars only**. Index 0 is still forming.
- The EA must be **restart-safe**: rebuild state from history in `OnInit` and
  check `PositionSelect` by magic number. Recompiling reloads a live EA and
  wipes its memory.
- Skip a day cleanly when the range window has no bars (holiday, session break)
  rather than building a range from whatever happens to be there.
- Never commit `creds.txt`.
