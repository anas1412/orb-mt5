# ORB — Opening Range Breakout for MetaTrader 5

A configurable opening-range breakout EA for MetaTrader 5, and the tooling to
backtest it: any session, any range length, any signal timeframe, any symbol,
with correct daylight-saving handling.

Install it, run a backtest, read the report. **The rules, the results and the
limits of each configuration live in its own report, not here** — every figure
there is generated from the run rather than typed:

| | |
|---|---|
| [Asia 00:00 UTC](https://anas1412.github.io/orb-mt5/) | the published configuration |
| [same, range filter off](https://anas1412.github.io/orb-mt5/asia-nofilter.html) | |
| [05:30 UTC, longs only](https://anas1412.github.io/orb-mt5/gold-0530-r60.html) | |
| [15:30 UTC+2, 1.2R](https://anas1412.github.io/orb-mt5/nydhal-1530.html) | |
| [Asia at a 2.5R target](https://anas1412.github.io/orb-mt5/1-step-full-report-2.5rr.html) | |

Each has a risk selector at the top; every percentage on the page follows it.
Account rules the pass rates are measured against:
[`fundingpips-1step-flex.md`](fundingpips-1step-flex.md).

---

## Install

Download the latest **[release](../../releases/latest)**, unzip, copy the `MQL5`
folder over your terminal's (**File → Open Data Folder**).

| From the zip | Goes to |
|---|---|
| `mql5/ORB.mq5` | `MQL5/Experts/` |
| `mql5/CheckBrokerOffset.mq5` | `MQL5/Scripts/` |
| `mql5/TimeZones.mqh` | `MQL5/Include/` |
| `mql5/Panel.mqh` | `MQL5/Include/` |

1. Open `mql5/ORB.mq5` in MetaEditor, press **F7**
2. Open an **XAUUSD M1** chart, drag **ORB** onto it, tick **Allow Algo Trading**
3. Turn on **AutoTrading** in the toolbar
4. The panel starts **OFF** — press **TRADING ON** when ready

Releases ship source, not a compiled `.ex5`: the code you run is the code you
can read. The `.ex5` runs on Windows and Linux/Wine alike.

---

## The on-chart panel

| Control | What it does |
|---|---|
| **TRADING ON / OFF** | Master switch. Starts OFF. Off stops new entries but keeps managing an open trade |
| **Risk per trade** | The number, plus a `%` / currency button: percent of balance or fixed cash |
| **Reward : risk** | The target, in R |
| **Session start** | `HH:MM` UTC |
| **Range length** | Minutes |
| **Break window** | Minutes after the range closes that a break still counts |
| **Stop move** | ON / OFF, with its two levels beneath |
| **Yesterday filter** | ON / OFF. Skips a break against the previous daily candle when its body is at least **Min body**. Off by default, not in the published numbers |

Settings lock while trading is on or a position is open, and persist across
restarts. Header: **IDLE**, **ONLINE**, **IN TRADE**, or **BLOCKED** if the
terminal refuses orders.

---

## Settings that matter

Defaults are the tested configuration.

| Input | Default | Meaning |
|---|---|---|
| `InpStartHour` / `Minute` | `0` / `0` | Session start, 00:00 UTC |
| `InpRangeMinutes` | `15` | Range length |
| `InpNoEntryAfterMin` | `15` | Stop looking at 00:29 |
| `InpMaxHoldMinutes` | `90` | Flat after 90 minutes |
| `InpMinClosePos` | `0.50` | The half-of-the-range rule |
| `InpTradeFri` | `false` | Friday off |
| `InpYdayFilter` / `MinBody` | `false` / `30` | Skip breaks against yesterday's daily candle. Measured, not published |
| `InpSLPercentOfRange` | `50` | Stop at the midpoint |
| `InpRR` | `2.0` | Target at 2R |
| `InpStopMoveAtR` / `ToR` | `0.5` / `-0.5` | At +0.5R, move to −0.5R |
| `InpLotMode` | percent | percent of balance, or fixed cash |
| `InpRiskPercent` | `2.0` | Risk per trade |
| `InpWinterOffset` | `2` | Your broker's winter offset from UTC |

**Check for your own broker:** `InpWinterOffset` (measured +2 on FTMO demo) and
`InpFollowsUSDST` (US or EU switch dates; they differ ~3 weeks in March, ~1 in
October). The included `CheckBrokerOffset` script measures both.

Sizing: lots round to the **nearest** step, so realised risk lands within ~9% of
target. A full stop costs slightly more than the risk figure (commission). If
the size needs more margin than is free, the EA sizes down and says so in the
journal.

---

## Reproduce the backtest

```bash
python3 orb.py run strategies/asia-gold.toml 2026.01.01 2026.09.11   # any spec → its own report
bash update.sh                                     # new days only: test, rebuild, audit, commit
bash update.sh --account accounts/ftmo.env         # with a specific broker login
```

- A **spec** is one TOML file: symbol, session, rules, risk, dates, benchmark.
  `strategies/asia-gold.toml` is the published configuration; a new one lists
  only what differs. See [`strategies/`](strategies/).
- Broker login comes from `accounts/*.env` (ignored by git; see
  `accounts/example.env`). Without one, the terminal's saved session is used.
- Results: `Common\Files\ORB_XAUUSD_*.csv`, one row per trade. Needs M1
  real-tick history.

The account rules every figure is measured against are in
[`fundingpips-1step-flex.md`](fundingpips-1step-flex.md).

The study is in [`research/`](research/); the one-off scripts behind
[`FINDINGS.md`](research/FINDINGS.md) are in [`research/studies/`](research/studies/).

---

## Control panel

```bash
python3 orb.py start           # then open http://127.0.0.1:8765
python3 orb.py stop
python3 orb.py status
python3 orb.py open            # start it first, then open a browser
python3 orb.py logs
```

Options on `start`:

```bash
python3 orb.py start --local           # use the MetaTrader on this machine
python3 orb.py start --slots 4 --port 8080
```

Same script for everything else:

```bash
python3 orb.py run strategies/asia-gold.toml 2026.01.01 2026.09.11   # one backtest
python3 orb.py runs                                                  # what MetaTrader did
python3 orb.py compile                                               # compile the EA
```

Windows is the same with `python` instead of `python3`. `stop` reads a pid file,
so there is no process pattern to get wrong.

| Tab | |
|---|---|
| Backtests | every spec with its last result, run / edit / duplicate / delete, and a link to its report |
| Accounts | add or remove a broker login |
| Runs | the queue, and what MetaTrader did on each run |

### Why it asks for nothing

The panel is on `127.0.0.1` and nowhere else. It holds a random token per start,
and every `/api` call needs it — **the page fetches that itself, so there is
nothing to copy or type.** It exists because a website you happen to visit can
POST to `localhost`, and without it that page could add a broker account or
delete a strategy. A browser will not let another origin read the token, so it
cannot.

Reach it from a phone over a private network such as Tailscale. Never a port
forward.

### Accounts

`POST /api/accounts` writes `accounts/<label>.env` at mode `600`, ignored by
git. No endpoint returns the password, no log line holds it, and a run record
stores the label. Running a backtest goes through a confirmation naming the
spec, the account, the window and the runner.

New and edited strategies land in `strategies/generated/`. Tracked specs cannot
be deleted from the panel; editing one saves a copy.

---

## Without Docker

Uses the MetaTrader already installed. Works on Windows and on Linux with Wine.

```bash
python3 research/run_local.py strategies/asia-gold.toml 2026.01.01 2026.09.11
python3 research/run_local.py --account accounts/ftmo.env SPEC FROM TO
python3 research/serve.py --local        # the panel, same runner
```

It looks for the terminal in the usual places:

| | |
|---|---|
| Windows | `C:\Program Files\MetaTrader 5\terminal64.exe` |
| Linux / Wine | `~/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe` |

Override when it guesses wrong:

```bash
MT5_TERMINAL="C:\Program Files\MetaTrader 5\terminal64.exe" python3 research/run_local.py ...
```

- Uses the terminal's saved session unless `--account` is given.
- A password reaches only a temporary `run.ini` inside the terminal folder,
  deleted whether the run succeeds or fails.
- Writes the same `research/runs/<id>.json` record as a container run.
- **Close the terminal first.** It holds the tester lock, and a second one
  launching while the first shuts down exits silently.

`research/report.sh` does the same thing but needs bash and Wine, so it is the
Linux path only. `run_local.py` is the one that works on both.

---

## Containers

The engine runs headless in Docker: Ubuntu 24.04, WineHQ, Xvfb, Python, the
MetaTrader binaries staged into `docker/mt5/` (ignored by git), the EA compiled
at build time — the image is refused if it does not compile.

Build:

```bash
docker build -f docker/Dockerfile -t orb-mt5 .    # ~15 min cold, seconds cached
```

Rebuild only when the Dockerfile or the staged binaries change. The repo is
bind-mounted at run time, so a spec or script change needs no rebuild.

One backtest:

```bash
docker run --rm --env-file accounts/ftmo.env \
  -v orb-bases-1:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Bases" \
  -v orb-tester-1:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Tester" \
  -v orb-config-1:"/root/.wine_mt5/drive_c/Program Files/MetaTrader 5/Config" \
  -v orb-common-1:"/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files" \
  -v "$HOME/.wine_mt5/drive_c/users/$USER/AppData/Roaming/MetaQuotes/Terminal/Common/Files:/bars:ro" \
  -v "$PWD:/root/orb/strategy" \
  orb-mt5 bash research/report.sh --id my-run strategies/asia-gold.toml 2026.01.01 2026.09.11
```

Several at once:

```bash
bash research/farm.sh --slots 3 --env accounts/ftmo.env strategies/*.toml
bash research/farm.sh --dry-run --slots 3 strategies/*.toml     # print, run nothing
python3 research/farm_stats.py --last 10                        # read the records back
```

### Volumes

| Volume | Per slot? | |
|---|---|---|
| `orb-bases-N` | yes | price history, 2.1 GB, seeded once from this machine |
| `orb-tester-N` | yes | the tester lock and the agent's private history copy |
| `orb-config-N` | yes | account and `tester.ini` |
| `orb-common-N` | yes | `run_window.sh` writes `new_cp*.csv` here |

Two terminals sharing `Tester/` fight and one exits without saying why, so
nothing is shared between slots. The host's `Common/Files` comes in read-only at
`/bars` and the entrypoint copies `bars_*.csv` and `d1_*.csv` across with
`cp -u`.

Seed a slot before its first run, or the tester re-imports every month of ticks:

```bash
docker volume create orb-bases-1
docker run --rm -v orb-bases-1:/b \
  -v "$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/Bases:/src:ro" \
  orb-mt5 sh -c 'cp -a /src/. /b/'
```

Remove a slot's state:

```bash
docker volume rm orb-bases-1 orb-tester-1 orb-config-1 orb-common-1
```

### Slot count

Bound by RAM, not cores: each tester agent wants a core and about a gigabyte.
Three slots on an 8-core machine with 5 GB free. Containers are capped at
`--cpus 1.5 --memory 2g`.

### Without an account

`tester not started because the account is not specified` in the journal means
the image works and only the login is missing. A container has no saved
MetaTrader session, so `--env-file` is required.

### Run records

Every run writes `research/runs/<id>.json` beside its log: spec, symbol, account
label, the window asked for against the one the tester covered, trade counts,
per-step seconds, status, and the journal lines worth reading. `farm_stats.py`
flags a clamped date range and a run that found no trades.

---

## Requirements and limits

- MetaTrader 5 build 6000 or newer
- M1 real-tick history for the symbol you test
- Windows, or Linux with Wine
- **The Strategy Tester cannot see today.** Its history server serves bars up to
  the last completed trading day, and it silently clamps the range you asked
  for. `SyncDump.mq5` plus `research/sim_offline.py` cover the current session.
- **One terminal at a time.** It holds the tester lock; a second one launching
  while the first shuts down exits without saying why. Containers get a slot
  each; local runs need the terminal closed.
- **A new symbol's first run is slow** — the tester imports every month of ticks
  before it tests anything.
- `InpFollowsUSDST` is unverified and matters for about one week each October.
  See [`CLAUDE.md`](CLAUDE.md).

Not financial advice. Test on demo first.

---

## Licence

MIT — see [LICENSE](LICENSE).
