# FundingPips — 1 Step Flex

Source: <https://help.fundingpips.com/hc/en-us/articles/34501697434385-1-Step-Flex>
Read 9 September 2026. Rules change; re-read before relying on this.

The benchmark `fundingpips-1step-flex` in `research/spec.py` models the numbers
in **Structure** and **Hard breaches** below.

---

## Structure

| | |
|---|---|
| Phases | One evaluation phase, then the Master Account |
| Profit target | **12%**, Phase 1 |
| Minimum trading days | **None** |
| Time limit | **None** |
| Account sizes | $5K, $10K, $25K, $50K, $100K |
| Reward split | 85% bi-weekly, or 100% monthly (conditions below) |

## Hard breaches — immediate closure, no grace period

| Limit | Value | Basis |
|---|---|---|
| Max loss | **12%** | Of the **starting account size**. Static, not trailing |
| Daily loss | **3%** | Of the higher of opening **balance** or opening **equity**, fixed at day start |
| Inactivity | 30 days | No completed trade in 30 consecutive days |
| Striking system | **1%** | Floating loss on one trade idea. Master accounts only |

### Max loss

- 12% of the starting account size, not of current equity.
- **Open and closed losses both count.** Equity or balance may not touch the
  level at any point, including floating loss from open trades.
- $100K account → equity must never reach $88,000.

### Daily loss

- At the start of each trading day the system records balance and equity;
  the **higher becomes the baseline**.
- Equity may not fall more than 3% of that baseline at any point that day,
  **floating P&L included**.
- Resets **00:00 platform time (UTC+3)**.
- Baseline examples: balance $100K / equity $99K → baseline $100K, floor $97K.
  Balance $105K / equity $107K → baseline $107K, floor $103,790.

### Striking system — Master accounts only

Triggered when floating loss on **one trade idea** reaches **1% of account
size**, at every account size.

| Warning | Consequence |
|---|---|
| 1st | Warning issued |
| 2nd | Reward split halved |
| 3rd | Reward split drops to 20% |
| 4th | **Account breached and closed** |

- Warnings are **cumulative and never reset**, including between reward cycles.
- Profit from any warned trade idea is **deducted**.
- A "trade idea" is one trade, several trades on the same instrument in the same
  direction running together, or **any new trade opened within 10 minutes of
  closing a losing trade**. Their closed profits and losses are counted together.

---

## Profit Concentration Policy

Applies to evaluation accounts created **on or after 27 June 2026**.

- If a single trade idea accounts for **more than 60% of the profit target**
  during the evaluation, the resulting Master Account requires **4 minimum
  profitable days before each reward request**.
- Not a breach. Accounts already in Phase 2 on 27 June 2026 are exempt.

## Account reset

Available within **7 calendar days** of a breach.

| | |
|---|---|
| Evaluation reset | 15% off the purchase price |
| Master reset | 7% off, excluding $100K accounts |

Keeps the same account size and platform. A Master reset restarts from Phase 1.
A non-USD account resets as a USD account.

---

## Rewards

Minimum request is **1% of the Master Account size**, including FundingPips'
split ($1,000 on a $100K).

### Bi-weekly — 85% split

Request every two weeks once profit meets the 1% minimum.

### Monthly — 100% split

Evaluation accounts purchased on or after 15 August 2026. Every 30 calendar
days after the first executed trade on the Master Account.

- **35% consistency score**: no single trading day may account for more than
  35% of total profit.
- **At least 7 profitable days**, each **≥ 0.5%** of the starting Master
  Account size.
- Both reset after each processed reward.
- The 1% striking trigger is unchanged on either cycle.

---

## News and weekend holds

Official source is the Economic Calendar on the FundingPips dashboard.

**Deliberately trading during news or speeches in either phase is prohibited
and closes the account.**

### Evaluation phase

- No news restrictions. Trades may be held and managed through events.
- Weekend holds permitted, no restrictions.

### Master account — soft breach, profit deducted, not closure

- **Weekend holds currently NOT allowed** (temporary). Close everything before
  Friday market close; the system force-closes anything left. Not a hard breach.
- **10-minute restricted window** around restricted high-impact news on the
  affected currencies: no opening or closing from 5 minutes before to 5 minutes
  after. For speeches, 10 minutes before until 10 minutes after it ends.
- **5-hour exception**: trades opened 5 hours or more before an event may be
  closed inside the window and their profits count.
- Trades opened less than 5 hours before: profits do not count if closed in the
  window.
- Closing a partial order affects the whole order and flags it.
- Traders are liable if deductions push them past the daily or max loss limit.

---

## Trading conditions

### Commission

| Instrument | Standard | Swap-free (MT5) |
|---|---|---|
| Forex | $5 / lot | $10 / lot |
| Metals | $5 / lot | $10 / lot |
| Energies | none | none |
| Indices | none | none |
| Crypto | 0.04% | 0.04% |

Crypto formula: lot size × price × 0.04%.

### Leverage

| Instrument | Standard | Swap-free (MT5) |
|---|---|---|
| Forex | 1:100 | 1:30 |
| Metals | 1:30 | 1:10 |
| Energies | 1:10 | 1:5 |
| Indices | 1:20 | 1:5 |
| Crypto | 1:2 | 1:1 |

Crypto drops to 1:1 on the Master Account. It stays 1:2 during Phase 1.

### Temporary dynamic leverage — Metals, Indices, Energies on Master accounts

Effective 16 March 2026, 23:59 UTC+3. Applied cumulatively per tier.

| Lot size | Leverage |
|---|---|
| 0.00 – 0.05 | 1:50 |
| 0.05 – 0.10 | 1:30 |
| 0.10 – 0.15 | 1:25 |
| 0.15 – 0.25 | 1:20 |
| 0.25 – 0.50 | 1:10 |
| 0.50 and above | 1:5 |

### Other

- **20-lot hard limit per trade**, enforced at platform level. Crypto: 1 lot.
- Swap-free add-on: MT5 only, Forex and Metals only, selected at purchase.
  Energies, Indices and Crypto still incur swap.

---

## What these rules mean for this EA

Measured on the 78 real 2026 trades. Deepest floating loss on any trade is
**1.094 R** — the stop, since the position closes there.

| Risk | Worst day float | 3% daily | 1% strike (Master) |
|---|---|---|---|
| 0.50% | 0.55% | safe | 0 of 78 warn |
| 0.75% | 0.82% | safe | 0 of 78 warn |
| 1.00% | 1.09% | safe | 25 of 78 warn |
| 2.00% | 2.19% | safe | 50 of 78 warn |
| 2.50% | 2.74% | safe | 55 of 78 warn |

- **Evaluation: 2.5%.** The striking system does not apply. Worst day 2.74%
  against a 3% limit. Pass rate 96.3%, median 7 trades.
- **Master: 0.5%.** Four warnings close the account and they never reset, so
  any size at or above 1% ends it within days.
- The worst 5-loss run in the record summed −5.10 R = **12.8% at 2.5%**, past
  the 12% max loss. 2.25% is the highest that survives it.
- One trade at 2.5% is 5% of the account = 42% of the 12% target, under the 60%
  concentration threshold.
- Session is 00:00–01:45 UTC, flat daily, Monday–Thursday: no weekend holds, no
  scheduled high-impact news in that window, ~3.4 trades a week against the
  30-day inactivity rule.
