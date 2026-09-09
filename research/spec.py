"""A strategy spec: one TOML file that fully describes a backtest.

The EA already takes any symbol, session, range and rule set through its
inputs; the pipeline did not, because the config lived in tester.ini and the
research scripts assumed gold, Asia and 2026. The spec is the single source the
runner and the report read instead.

    python3 spec.py validate strategies/asia-gold.toml
    python3 spec.py inputs   strategies/asia-gold.toml      # Inp*=value lines
    python3 spec.py tester   strategies/asia-gold.toml      # [Tester] lines

Defaults are the published configuration, so a spec only names what differs.
Read with tomllib (stdlib); nothing else to install.
"""
import sys, tomllib, datetime as dt

TZ  = {"UTC": 0, "London": 1, "NewYork": 2, "Tokyo": 3, "Sydney": 4, "Broker": 5}
TF  = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385}
LOT = {"lots": 0, "percent": 1, "money": 2}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
BENCHMARKS = {
    # name: (phase 1 target %, phase 2 target %, max loss %, daily loss %, min days)
    "fundingpips-2step":      (8.0, 5.0, 10.0, 5.0, 3),
    "fundingpips-1step-flex": (12.0, None, 12.0, 3.0, 0),   # one phase, no minimum days
    "ftmo-2step":             (10.0, 5.0, 10.0, 5.0, 4),
    "none":                   None,
}
BENCH_TEXT = {
    "fundingpips-2step":      ("FundingPips two-step", "Targets +8% then +5%, 10% maximum loss, 5% daily"),
    "fundingpips-1step-flex": ("FundingPips 1 Step Flex", "Target +12%, 12% maximum loss, 3% daily, no minimum days"),
    "ftmo-2step":             ("FTMO two-step", "Targets +10% then +5%, 10% maximum loss, 5% daily"),
    "none":                   ("no challenge", "No pass-rate simulation"),
}

DEFAULTS = {
    "symbol": "XAUUSD",
    "server": "FTMO-Demo",
    "session": {"tz": "UTC", "start": "00:00", "range_min": 15, "entry_window_min": 15,
                "hold_min": 90, "force_close_min": 360, "signal_tf": "M1"},
    "rules":   {"rr": 2.0, "sl_pct_of_range": 50.0, "stop_move_at_r": 0.5, "stop_move_to_r": -0.5,
                "half_filter": True, "yday_filter": False, "yday_min_body": 30.0,
                "days": ["Mon", "Tue", "Wed", "Thu"], "max_trades_per_day": 1},
    "risk":    {"mode": "percent", "per_trade": 2.5, "deposit": 10000, "leverage": 100,
                "max_daily_loss_pct": 3.5},
    "dates":   {"from": dt.date(2026, 1, 1), "to": "today"},
    "report":  {"benchmark": "fundingpips-1step-flex", "title": "", "output": ""},
    "magic":   20260821,
}


class SpecError(Exception):
    pass


def load(path):
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    spec = {}
    for k, v in DEFAULTS.items():
        if isinstance(v, dict):
            spec[k] = {**v, **raw.get(k, {})}
            extra = set(raw.get(k, {})) - set(v)
            if extra:
                raise SpecError("[%s] has unknown keys: %s" % (k, ", ".join(sorted(extra))))
        else:
            spec[k] = raw.get(k, v)
    if "name" not in raw:
        raise SpecError("name is required")
    spec["name"] = raw["name"]
    unknown = set(raw) - set(DEFAULTS) - {"name"}
    if unknown:
        raise SpecError("unknown top-level keys: %s" % ", ".join(sorted(unknown)))
    validate(spec)
    return spec


def validate(s):
    def need(cond, msg):
        if not cond:
            raise SpecError(msg)
    ses, ru, ri, da, re_ = s["session"], s["rules"], s["risk"], s["dates"], s["report"]
    need(s["name"].replace("-", "").replace("_", "").isalnum(), "name must be letters, digits, - or _")
    need(ses["tz"] in TZ, "session.tz must be one of %s" % ", ".join(TZ))
    hh, mm = ses["start"].split(":")
    need(0 <= int(hh) <= 23 and 0 <= int(mm) <= 59, "session.start must be HH:MM")
    need(1 <= ses["range_min"] <= 240, "session.range_min must be 1..240")
    need(0 <= ses["entry_window_min"] <= 240, "session.entry_window_min must be 0..240 (0 = no limit)")
    need(0 <= ses["hold_min"] <= 1440, "session.hold_min must be 0..1440 (0 = off)")
    need(ses["signal_tf"] in TF, "session.signal_tf must be one of %s" % ", ".join(TF))
    need(0 < ru["rr"] <= 20, "rules.rr must be in (0, 20]")
    need(0 <= ru["sl_pct_of_range"] <= 100, "rules.sl_pct_of_range must be 0..100")
    if ru["stop_move_at_r"]:
        need(ru["stop_move_to_r"] < ru["stop_move_at_r"], "rules.stop_move_to_r must sit below stop_move_at_r")
    need(all(d in DAYS for d in ru["days"]) and ru["days"], "rules.days must be a non-empty subset of %s" % DAYS)
    need(ru["yday_min_body"] > 0, "rules.yday_min_body must be positive")
    need(ri["mode"] in LOT, "risk.mode must be one of %s" % ", ".join(LOT))
    need(ri["per_trade"] > 0, "risk.per_trade must be positive")
    need(ri["deposit"] > 0, "risk.deposit must be positive")
    need(isinstance(da["from"], dt.date), "dates.from must be a date (YYYY-MM-DD, unquoted)")
    need(da["to"] == "today" or isinstance(da["to"], dt.date), "dates.to must be a date or \"today\"")
    need(re_["benchmark"] in BENCHMARKS, "report.benchmark must be one of %s" % ", ".join(BENCHMARKS))
    need(not re_["output"] or re_["output"].endswith(".html"), "report.output must end in .html")


def inputs(s):
    """The EA inputs this spec means, as the tester.ini keys."""
    ses, ru, ri = s["session"], s["rules"], s["risk"]
    hh, mm = ses["start"].split(":")
    out = {
        "InpTimeZone": TZ[ses["tz"]], "InpStartHour": int(hh), "InpStartMinute": int(mm),
        "InpRangeMinutes": ses["range_min"], "InpSignalTF": TF[ses["signal_tf"]],
        "InpEntryMode": 0, "InpNoEntryAfterMin": ses["entry_window_min"],
        "InpForceCloseMin": ses["force_close_min"], "InpMaxHoldMinutes": ses["hold_min"],
        "InpMaxTradesPerDay": ru["max_trades_per_day"],
        "InpMinClosePos": 0.50 if ru["half_filter"] else 0,
        "InpYdayFilter": "true" if ru["yday_filter"] else "false",
        "InpYdayMinBody": ru["yday_min_body"],
        "InpSLMode": 0, "InpSLPercentOfRange": ru["sl_pct_of_range"],
        "InpTPMode": 0, "InpRR": ru["rr"],
        "InpStopMoveAtR": ru["stop_move_at_r"], "InpStopMoveToR": ru["stop_move_to_r"],
        "InpRangeLookback": 0,
        "InpLotMode": LOT[ri["mode"]],
        "InpRiskPercent": ri["per_trade"] if ri["mode"] == "percent" else 2.0,
        "InpRiskMoney":   ri["per_trade"] if ri["mode"] == "money" else 100,
        "InpLots":        ri["per_trade"] if ri["mode"] == "lots" else 0.01,
        "InpMaxDailyLossPct": ri["max_daily_loss_pct"],
        "InpMagic": s["magic"], "InpWriteCsv": "true",
    }
    for d in DAYS:
        out["InpTrade" + d] = "true" if d in ru["days"] else "false"
    return out


def tester(s):
    """The [Tester] keys. ToDate is exclusive; 'today' means tomorrow's date."""
    da, ri = s["dates"], s["risk"]
    to = (dt.date.today() + dt.timedelta(days=1)) if da["to"] == "today" else da["to"]
    return {"Symbol": s["symbol"], "Period": "M1", "Model": 4,
            "FromDate": da["from"].strftime("%Y.%m.%d"), "ToDate": to.strftime("%Y.%m.%d"),
            "Deposit": ri["deposit"], "Currency": "USD", "Leverage": "1:%d" % ri["leverage"]}


def fmt(v):
    """One rendering per value, whatever the TOML wrote.

    `yday_min_body = 30` and the 30.0 default are the same setting, but printed
    as "30" and "30.0" they make `diff` claim two identical specs differ.
    """
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("validate", "inputs", "tester"):
        sys.exit(__doc__)
    cmd, path = sys.argv[1], sys.argv[2]
    try:
        s = load(path)
    except (SpecError, tomllib.TOMLDecodeError, FileNotFoundError, KeyError, ValueError) as e:
        sys.exit("%s: %s" % (path, e))
    if cmd == "validate":
        print("%s: ok  (%s on %s, %s %s, %s..%s)" % (path, s["name"], s["symbol"], s["session"]["start"],
              s["session"]["tz"], s["dates"]["from"], s["dates"]["to"]))
    else:
        for k, v in (inputs(s) if cmd == "inputs" else tester(s)).items():
            print("%s=%s" % (k, fmt(v)))


if __name__ == "__main__":
    main()
