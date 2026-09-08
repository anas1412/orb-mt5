# Strategy specs

One TOML file per strategy. `asia-gold.toml` is the published configuration
and doubles as the reference: every key, its default, and what it means.
A new spec only needs `name` plus whatever differs.

    python3 research/spec.py validate strategies/<name>.toml
    python3 research/spec.py inputs   strategies/<name>.toml    # the EA inputs it means

| Section | Keys |
|---|---|
| top | `name`, `symbol`, `server` |
| `[session]` | `tz`, `start` (HH:MM in that zone), `range_min`, `entry_window_min`, `hold_min`, `signal_tf` |
| `[rules]` | `rr`, `sl_pct_of_range`, `stop_move_at_r`, `stop_move_to_r`, `half_filter`, `yday_filter`, `yday_min_body`, `days` |
| `[risk]` | `mode` (percent / money / lots), `per_trade`, `deposit` |
| `[dates]` | `from` (unquoted date), `to` (date or `"today"`) |
| `[report]` | `benchmark` (fundingpips-2step / ftmo-2step / none) |

Dates are unquoted TOML dates: `from = 2026-01-01`. `to` is exclusive.
