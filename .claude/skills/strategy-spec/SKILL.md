---
name: strategy-spec
description: Turn a plain-English description of an opening-range-breakout strategy variant into a validated TOML spec under strategies/, ready for the backtest runner. Use this whenever the user describes a strategy or a variant of the current one in words -- "try the London open", "what if the range was 30 minutes", "same thing on US100", "1% risk, no stop move", "test it since 2024", "new spec", "add a strategy" -- even when they never say "spec" or "TOML". If they are describing WHAT to test rather than asking for results, this is the skill.
---

# Strategy spec from English

A spec is one TOML file that fully describes a backtest. The runner reads it
instead of `tester.ini`, so writing one is how a new idea gets tested at all.

## Read the reference first

`strategies/asia-gold.toml` is the published configuration with every key
commented, and `strategies/README.md` is the schema. **Every key has a default
equal to the published config**, so a spec only names what differs. Write
`name`, then only the lines the user changed. A spec that repeats every default
hides which three things are actually being tested.

## Translate, don't interrogate

Users describe strategies the way traders talk. Map their words onto keys:

| They say | You write |
|---|---|
| "London open", "London session" | `[session] tz = "London"`, `start = "08:00"` |
| "New York open", "NY cash open" | `tz = "NewYork"`, `start = "09:30"` |
| "Tokyo open", "Asia open" | `tz = "UTC"`, `start = "00:00"` (the published session) |
| "30 minute range", "first half hour" | `range_min = 30` |
| "take breaks for an hour" | `entry_window_min = 60` |
| "hold to the close", "no time limit" | `hold_min = 0` |
| "1.5 to 1", "target 3R" | `[rules] rr = 1.5` / `rr = 3.0` |
| "stop at the other side of the range" | `sl_pct_of_range = 100` |
| "stop at the level", "tight stop" | `sl_pct_of_range = 0` (ask -- 25 may be what they mean) |
| "no stop move", "don't move the stop" | `stop_move_at_r = 0` |
| "move to breakeven at 1R" | `stop_move_at_r = 1.0`, `stop_move_to_r = 0` |
| "take both directions", "no half rule" | `half_filter = false` |
| "with yesterday's candle", "trend filter" | `yday_filter = true` |
| "include Fridays", "all week" | `days = ["Mon","Tue","Wed","Thu","Fri"]` |
| "1% risk" | `[risk] per_trade = 1.0` |
| "$100 a trade", "fixed 200 dollars" | `mode = "money"`, `per_trade = 100` |
| "since 2024", "last two years" | `[dates] from = 2024-01-01` |
| "FTMO rules" | `[report] benchmark = "ftmo-2step"` |
| "gold" / "nasdaq" / "US100" | `symbol = "XAUUSD"` / `"US100.cash"` |

Times are in the session's own zone, not the broker's -- the EA converts.
The only thing worth a question is a symbol you cannot infer, or a phrase that
maps two ways (a "tight stop" is 0 or 25). One question, then proceed. State
every default you relied on in one line afterwards so nothing is silent.

## Name it

Kebab-case, session then symbol then the distinguishing change:
`london-gold`, `asia-us100`, `asia-gold-30m`, `asia-gold-no-halfrule`. The name
becomes the report's directory, so it should read well in a list of twenty.

## Write, then validate -- always both

```bash
python3 research/spec.py validate strategies/<name>.toml
python3 research/spec.py inputs   strategies/<name>.toml
```

`validate` catches wrong keys, out-of-range values and quoted dates (TOML dates
are bare: `from = 2026-01-01`; only `to = "today"` is a string). `inputs` prints
the EA inputs the spec means -- show it to the user, because that is the actual
contract with the tester and it is where a translation mistake becomes visible.
Fix and re-validate rather than hand the user a file that fails.

## Run it, if they want results

```bash
SPEC=strategies/<name>.toml bash research/run_window.sh 2026.01.01 2026.09.08
```

That tests the spec over the window on real ticks and leaves the trades in
`new_cp0.50.csv` in MetaTrader's Common Files. The full report per spec is the
next phase of the pipeline; until then, the trade file is the result.

## Example

**Input:** "same as now but at the London open with a 30 minute range and 1.5R"

**Output** `strategies/london-gold-30m.toml`:

```toml
name = "london-gold-30m"

[session]
tz        = "London"
start     = "08:00"
range_min = 30

[rules]
rr = 1.5
```

Then: "Defaults kept: XAUUSD, 15-minute entry window, 90-minute hold, stop at
the midpoint, stop move +0.5R to -0.5R, half rule on, Mon-Thu, 2% risk, 2026,
FundingPips benchmark."
