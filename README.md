# ORB — Opening Range Breakout for MetaTrader 5

A configurable opening-range breakout EA, and the tooling to backtest it. Any
session, any range length, any signal timeframe, any symbol, with correct
daylight-saving handling.

```bash
python3 orb.py compile      # build the EA
python3 orb.py start        # control panel at http://127.0.0.1:8765
```

Rules, results and limits live in each configuration's own report, generated
from the run:

| Report | |
|---|---|
| [Asia 00:00 UTC](https://anas1412.github.io/orb-mt5/) | the published configuration |
| [Asia, range filter off](https://anas1412.github.io/orb-mt5/asia-nofilter.html) | |
| [Asia at 2.5R](https://anas1412.github.io/orb-mt5/1-step-full-report-2.5rr.html) | |
| [05:30 UTC, longs only](https://anas1412.github.io/orb-mt5/gold-0530-r60.html) | |
| [15:30 UTC+2, 1.2R](https://anas1412.github.io/orb-mt5/nydhal-1530.html) | |

Account rules behind the pass rates:
[`fundingpips-1step-flex.md`](fundingpips-1step-flex.md).

---

## Install

Copy `mql5/` into your terminal's data folder (**File → Open Data Folder**),
compile, attach to an **XAUUSD M1** chart. The panel starts **OFF**.

| From the zip | Goes to |
|---|---|
| `mql5/ORB.mq5` | `MQL5/Experts/` |
| `mql5/CheckBrokerOffset.mq5` | `MQL5/Scripts/` |
| `mql5/TimeZones.mqh` | `MQL5/Include/` |
| `mql5/Panel.mqh` | `MQL5/Include/` |

```bash
python3 orb.py compile     # or press F7 in MetaEditor
```

Releases ship source, not a compiled `.ex5`.

---

## Commands

`python` instead of `python3` on Windows. That is the only difference.

```bash
python3 orb.py start                    # control panel at http://127.0.0.1:8765
python3 orb.py stop
python3 orb.py status
python3 orb.py restart
python3 orb.py open
python3 orb.py logs

python3 orb.py start --local            # use this machine's MetaTrader, no Docker
python3 orb.py start --slots 4 --port 8080

python3 orb.py run strategies/asia-gold.toml 2026.01.01 2026.09.11
python3 orb.py runs                     # what MetaTrader did on each run
python3 orb.py compile

bash update.sh                          # new days only: test, rebuild, audit, commit
bash update.sh --account accounts/ftmo.env
```

Nothing to copy or paste: the panel's token is generated per start and the page
fetches it itself. It is there because a site you visit can POST to `localhost`.

| Panel tab | |
|---|---|
| Backtests | every strategy with its last result; run, edit, duplicate, delete |
| Accounts | add or remove a broker login |
| Runs | the queue, and what MetaTrader did |

Accounts are written to `accounts/<label>.env`, mode `600`, ignored by git. New
strategies land in `strategies/generated/`.

Reach the panel from a phone over Tailscale. Never a port forward.

---

## Without Docker

```bash
python3 orb.py start --local
python3 orb.py run strategies/asia-gold.toml 2026.01.01 2026.09.11
```

| Terminal found at | |
|---|---|
| Windows | `C:\Program Files\MetaTrader 5\terminal64.exe` |
| Linux / Wine | `~/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe` |
| Override | `MT5_TERMINAL=...` |

Close the terminal first — it holds the tester lock.

---

## Containers

```bash
docker build -f docker/Dockerfile -t orb-mt5 .        # ~15 min cold
python3 orb.py start                                  # containers are the default
bash research/farm.sh --slots 3 --env accounts/ftmo.env strategies/*.toml
bash research/farm.sh --dry-run --slots 3 strategies/*.toml
```

| Volume, per slot | |
|---|---|
| `orb-bases-N` | price history, 2.1 GB, seeded once from this machine |
| `orb-tester-N` | the tester lock and the agent's history copy |
| `orb-config-N` | account and `tester.ini` |
| `orb-common-N` | where the run writes its CSVs |

```bash
docker volume rm orb-bases-1 orb-tester-1 orb-config-1 orb-common-1   # reset a slot
```

Three slots on 8 cores with 5 GB free — each tester agent wants a core and a
gigabyte. `tester not started because the account is not specified` means the
image works and only the login is missing. Rebuild the image only for the
Dockerfile or the MetaTrader binaries; the repo is bind-mounted.

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

Settings lock while trading is on, and persist across restarts.

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

**Check for your own broker:** `InpWinterOffset` and `InpFollowsUSDST`. The
`CheckBrokerOffset` script measures both. Lots round to the nearest step, so
realised risk lands within ~9% of target.

---

## Requirements and limits

- MetaTrader 5 build 6000 or newer, and M1 real-tick history for your symbol
- Windows, or Linux with Wine
- **The tester cannot see today.** It clamps the range you asked for and says so
  in the run record. `SyncDump.mq5` + `research/sim_offline.py` cover the
  current session.
- **One terminal at a time** — it holds the tester lock. Containers get a slot
  each; local runs need the terminal closed.
- A new symbol's first run imports every month of ticks before it tests.
- `InpFollowsUSDST` is unverified; it matters for about a week each October.

Not financial advice. Test on demo first.

---

## Licence

MIT — see [LICENSE](LICENSE).
