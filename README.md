# ORB — Opening Range Breakout for MetaTrader 5

Trades the first breakout of the Asia session range on gold. One trade a day,
flat within 90 minutes, Monday to Thursday.

**[📊 Full report and every trade →](https://anas1412.github.io/orb-mt5/)**

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
| 9 | **Monday–Thursday only.** Friday is the only losing day |
| 10 | Risk the same amount every trade. No compounding |

**The half-of-the-range rule (#2) in plain terms:** closed in the top half →
you may only take an up-break. Closed in the bottom half → only a down-break.
Breaks the other way are skipped. That single filter is worth 5 points of win
rate for 1 R of give-up.

---

## Results

XAUUSD, real ticks, 2026 (2 Jan – 21 Aug), 2% risk per trade.

| | |
|---|---|
| Trades | **72** from 132 eligible sessions |
| Win rate | **54.2%** — 39 wins, 33 losses |
| Expectancy | **+0.654 R** per trade (±0.166 standard error) |
| Total | **+47.1 R** = **+94%** of the account |
| Worst drawdown | **6.3%** |
| Longest losing run | **3** |

**Challenge pass rate** — FundingPips two-step, +8% then +5%, 10% max loss,
simulated 40 000 times on the 2026 outcomes:

| Risk per trade | Pass both phases | Trades needed | Trading days |
|---|---|---|---|
| 1.0% | 99.9% | 19 | ~35 |
| 1.5% | 98.9% | 12 | ~22 |
| **2.0%** | **96.5%** | **9** | **~16** |
| 3.0% | 89.4% | 6 | ~11 |

How the 72 trades ended:

| Exit | Trades | Total |
|---|---|---|
| Target hit (+2R) | 32 | +65.3 R |
| Stopped out | 33 | −27.6 R |
| 90-minute cap | 7 | +6.6 R |

---

## Install

Download the latest **[release](../../releases/latest)** and unzip it. The
folder mirrors the MetaTrader tree, so copy its contents straight into your
terminal's `MQL5` folder:

| From the zip | Goes to |
|---|---|
| `MQL5/Experts/ORB.mq5` | `MQL5/Experts/` |
| `MQL5/Experts/CheckBrokerOffset.mq5` | `MQL5/Experts/` |
| `MQL5/Include/TimeZones.mqh` | `MQL5/Include/` |
| `MQL5/Include/Panel.mqh` | `MQL5/Include/` |

Find that folder with **File → Open Data Folder** in MetaTrader.

Then:

1. Open `ORB.mq5` in MetaEditor and press **F7** to compile
2. Open an **XAUUSD M1** chart and drag **ORB** onto it
3. Tick **Allow Algo Trading**, press OK
4. Turn on **AutoTrading** in the toolbar (the button must be green)
5. The panel appears. It starts **OFF** — press **TRADING ON** when ready

> Releases ship **source, not a compiled `.ex5`**. Compiling takes one keystroke,
> and it means the code you run is the code you can read — no binary to trust.
> The resulting `.ex5` is platform-neutral and runs on Windows and Linux/Wine
> alike.

---

## The on-chart panel

Everything is adjustable without reopening the inputs dialog.

| Control | What it does |
|---|---|
| **TRADING ON / OFF** | Master switch. Starts OFF. Turning it off stops new entries but keeps managing an open trade |
| **Risk per trade** | The number, plus a `%` / currency button to switch between percent of balance and a fixed cash amount |
| **Reward : risk** | The target, in R |
| **Session start** | `HH:MM` UTC |
| **Range length** | Minutes |
| **Break window** | Minutes after the range closes that a break still counts |
| **Stop move** | ON / OFF, with its two levels beneath |

Settings are locked while trading is on or a position is open, and are
remembered across restarts. The header reads **IDLE**, **ONLINE**, **IN TRADE**,
or **BLOCKED** if the terminal will not let an order through.

---

## Settings that matter

The defaults are the tested configuration. These are the ones worth knowing:

| Input | Default | Meaning |
|---|---|---|
| `InpStartHour` / `Minute` | `0` / `0` | Session start, 00:00 UTC |
| `InpRangeMinutes` | `15` | Range length |
| `InpNoEntryAfterMin` | `15` | Stop looking at 00:29 |
| `InpMaxHoldMinutes` | `90` | Flat after 90 minutes |
| `InpMinClosePos` | `0.50` | The half-of-the-range rule |
| `InpTradeFri` | `false` | Friday off |
| `InpSLPercentOfRange` | `50` | Stop at the midpoint |
| `InpRR` | `2.0` | Target at 2R |
| `InpStopMoveAtR` / `ToR` | `0.5` / `-0.5` | At +0.5R, move to −0.5R |
| `InpLotMode` | percent | percent of balance, or fixed cash |
| `InpRiskPercent` | `2.0` | Risk per trade |
| `InpWinterOffset` | `2` | Your broker's winter offset from UTC |

### Two you must check for your own broker

- **`InpWinterOffset`** — the EA reads broker time and converts to UTC. Get this
  wrong and it trades the wrong hour. Measured +2 on FTMO demo (so +3 in summer).
- **`InpFollowsUSDST`** — whether your broker switches DST on US or EU dates.
  They disagree for ~3 weeks in March and ~1 week in October. Run the included
  `CheckBrokerOffset` script to settle it.

Lot sizes round to the **nearest** step, not down, so realised risk lands within
about 9% of your target instead of occasionally half of it. Note a full stop
loses slightly more than your risk figure, the difference being commission.

---

## Reproduce the backtest

```bash
cd "<terminal folder>" && wine terminal64.exe /portable /config:tester.ini
```

On Windows, drop `wine`. Results land in `Common\Files\ORB_XAUUSD_*.csv`, one
row per trade. Needs M1 real-tick history for XAUUSD.

Research scripts and the full study are in [`research/`](research/).

---

## Requirements

- MetaTrader 5 build 6000 or newer
- M1 real-tick history for the symbol you test
- Windows, or Linux with Wine

---

## Honest limits

- **One symbol, one session, one year.** The edge was measured on gold at the
  Asia open in 2026. London and New York were tested and do not work.
- **It is a regime bet.** The filter depends on ranges that trend rather than
  chop. If the 15-minute range drops below 0.15% of price, the edge is gone.
- **72 trades is a small sample.** The ±0.166 standard error on expectancy is
  real, and so is the chance that 2026 was kind.

Not financial advice. Test on demo first.

## Licence

MIT — see [LICENSE](LICENSE).
