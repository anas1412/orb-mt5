# ORB — Opening Range Breakout for MetaTrader 5

Trades the first breakout of the Asia session range on gold. One trade a day,
flat within 90 minutes, Monday to Thursday.

**[📊 Full report, every trade, and a risk selector →](https://anas1412.github.io/orb-mt5/)**

Set risk per trade at the top of the report and every percentage on the page
follows. Variant: [the same rules at a 2.5R target](https://anas1412.github.io/orb-mt5/1-step-full-report-2.5rr.html).

---

## The rules

| # | Rule |
|---|---|
| 1 | At **00:00 UTC**, mark the high and low of the next **15 one-minute candles** |
| 2 | Split that box in half. Whichever half the **00:14 candle closed in** is the only direction you may trade |
| 3 | Wait for an M1 candle to **close** outside the box, up to **00:29**. Nothing by then → no trade |
| 4 | Enter **at market** on the next candle |
| 5 | Stop at the **midpoint** of the range. That distance is your 1R |
| 6 | Target at **2R**, measured from the actual fill |
| 7 | At **+0.5R**, pull the stop to **−0.5R**. Once only |
| 8 | Still open after **90 minutes**? Close at market |
| 9 | **Monday–Thursday only** |
| 10 | Risk the same amount every trade. No compounding |

Rule 2 in one line: top half → up-breaks only, bottom half → down-breaks only,
the other way is skipped.

---

## Results

XAUUSD, real ticks, 2026 (2 Jan – 10 Sep), 2.5% risk per trade.

| | |
|---|---|
| Trades | **75** from 144 eligible sessions |
| Win rate | **52.0%** — 39 wins, 36 losses |
| Expectancy | **+0.582 R** per trade (±0.165 standard error) |
| Profit factor | **2.40** — won +74.7 R against -31.1 R lost |
| Total | **+43.6 R** = **+109%** of the account |
| Worst drawdown | **15.4%** |
| Longest losing run | **6** |

**Challenge pass rate** — FundingPips 1 Step Flex: +12% target, 12% max loss,
3% daily loss, no minimum days. Each row is a barrier simulation over the real
trade outcomes, not arithmetic. ⚠ marks a risk where the worst losing run on
record would break the maximum loss.

| Risk per trade | Pass | Trades | Days | Return | Worst drawdown | Worst run costs |
|---|---|---|---|---|---|---|
| 1% | 100.0% | 19 | ~36 | +44% | 6.2% | 6.1% |
| 1.5% | 99.5% | 13 | ~25 | +65% | 9.2% | 9.2% |
| 2% | 98.4% | 9 | ~17 | +87% | 12.3% | 12.2% ⚠ |
| 2.25% | 97.4% | 8 | ~15 | +98% | 13.8% | 13.8% ⚠ |
| **2.5%** | **96.8%** | **7** | **~13** | **+109%** | **15.4%** | **15.3% ⚠** |

How the 75 trades ended:

| Exit | Trades | Total |
|---|---|---|
| Stopped out | 36 | -31.1 R |
| Target hit (+2R) | 35 | +71.3 R |
| 90-minute cap | 4 | +3.3 R |

---

## Install

Download the latest **[release](../../releases/latest)**, unzip, copy the `MQL5`
folder over your terminal's (**File → Open Data Folder**).

| From the zip | Goes to |
|---|---|
| `MQL5/Experts/ORB.mq5` | `MQL5/Experts/` |
| `MQL5/Experts/CheckBrokerOffset.mq5` | `MQL5/Experts/` |
| `MQL5/Include/TimeZones.mqh` | `MQL5/Include/` |
| `MQL5/Include/Panel.mqh` | `MQL5/Include/` |

1. Open `ORB.mq5` in MetaEditor, press **F7**
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
bash update.sh                                     # new days only: test, rebuild, audit, commit
bash update.sh --account accounts/ftmo.env         # with a specific broker login
bash research/report.sh strategies/<name>.toml 2026.01.01 2026.09.09   # any spec → its own report
```

- A **spec** is one TOML file: symbol, session, rules, risk, dates, benchmark.
  `strategies/asia-gold.toml` is the published configuration; a new one lists
  only what differs. See [`strategies/`](strategies/).
- The engine also runs in **Docker** — Wine, headless, EA compiled at build.
  Commands in [`CLAUDE.md`](CLAUDE.md).
- Broker login comes from `accounts/*.env` (ignored by git; see
  `accounts/example.env`). Without one, the terminal's saved session is used.
- Results: `Common\Files\ORB_XAUUSD_*.csv`, one row per trade. Needs M1
  real-tick history.

The account rules every figure is measured against are in
[`fundingpips-1step-flex.md`](fundingpips-1step-flex.md).

The study is in [`research/`](research/); the one-off scripts behind
[`FINDINGS.md`](research/FINDINGS.md) are in [`research/studies/`](research/studies/).

---

## Requirements

- MetaTrader 5 build 6000 or newer
- M1 real-tick history for the symbol you test
- Windows, or Linux with Wine

---

## Limits

- **One symbol, one session, one year.** Gold at the Asia open in 2026. London
  and New York were tested and do not work.
- **No trend awareness.** Five straight losses in Sep 2026 were buys into a
  $280 fall. Breaks *with* the previous daily candle won 59%, against it 33%.
  The yesterday filter exists for that; it is off until it has out-of-sample
  evidence.
- **That run breaks the account at the default risk.** Those five losses summed
  −5.10 R: **12.8% at 2.5% risk, past the 12% limit**. 2.25% is the most that
  survives it. Above 2.74% a single worst-case loss breaches the 3% daily limit
  on its own, which is why the selector stops at 2.5%.
- - **75 trades is a small sample.** The standard error on expectancy is in the
  table above, and so is the chance that 2026 was kind.

Not financial advice. Test on demo first.

## Licence

MIT — see [LICENSE](LICENSE).
