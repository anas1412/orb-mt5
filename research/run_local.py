"""Run a spec on the MetaTrader already installed on this machine. No Docker.

    python3 research/run_local.py strategies/asia-gold.toml 2026.01.01 2026.09.11
    python3 research/run_local.py --account accounts/ftmo.env SPEC FROM TO
    python3 research/run_local.py --id my-run SPEC FROM TO

Works on Windows and on Linux with Wine. The bash path (report.sh) needs both a
shell and wine, so Windows had no way in; this launches the terminal directly
and then runs the same four build steps, and writes the same run record.

Point it at a terminal explicitly when it guesses wrong:

    MT5_TERMINAL="C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    MT5_TERMINAL="$HOME/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"

It uses the terminal's saved session unless an account file is given, and the
password only ever reaches a temporary run.ini inside the terminal folder, which
is deleted whether the run succeeds or fails.
"""
import os, sys, glob, json, shutil, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "lib"))
import spec as S
from mt5paths import COMMON

WINDOWS = os.name == "nt"
CANDIDATES = ([r"C:\Program Files\MetaTrader 5\terminal64.exe",
               r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"] if WINDOWS else
              [os.path.expanduser("~/.wine_mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"),
               os.path.expanduser("~/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe")])


def terminal():
    p = os.environ.get("MT5_TERMINAL")
    if p:
        if not os.path.exists(p):
            sys.exit("MT5_TERMINAL is set to %s, which does not exist" % p)
        return p
    for c in CANDIDATES:
        if os.path.exists(c):
            return c
    sys.exit("no MetaTrader found. Set MT5_TERMINAL to terminal64.exe:\n  " +
             "\n  ".join(CANDIDATES))


def launch(exe, cfg_name, seconds=900):
    """Start the terminal on a config and wait. tester.ini sets
    ShutdownTerminal=1, so it exits on its own when the run finishes."""
    d = os.path.dirname(exe)
    cmd = [exe, "/portable", "/config:" + cfg_name]
    if not WINDOWS:
        env = dict(os.environ, WINEPREFIX=os.environ.get(
            "WINEPREFIX", os.path.expanduser("~/.wine_mt5")), WINEDEBUG="-all")
        cmd = ["wine"] + cmd
    else:
        env = dict(os.environ)
    try:
        return subprocess.run(cmd, cwd=d, env=env, timeout=seconds,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except subprocess.TimeoutExpired:
        return -1


def journal_text(path, since=0):
    """Every MetaTrader log is UTF-16LE; grep finds nothing until it is decoded."""
    try:
        with open(path, "rb") as fh:
            fh.seek(since)
            return fh.read().decode("utf-16-le", "ignore")
    except OSError:
        return ""


def set_keys(path, pairs):
    """Rewrite ini keys in place, keeping every other line as it was."""
    lines = open(path).read().splitlines()
    want = dict(pairs)
    out, seen = [], set()
    for ln in lines:
        k = ln.split("=", 1)[0].strip()
        if k in want:
            out.append("%s=%s" % (k, want[k])); seen.add(k)
        else:
            out.append(ln)
    missing = set(want) - seen
    if missing:
        # The sweep trap from CLAUDE.md: a key the ini does not carry is
        # silently ignored and every pass returns the compiled default.
        sys.exit("mql5/config/tester.ini has no line for: %s" % ", ".join(sorted(missing)))
    open(path, "w").write("\n".join(out) + "\n")


def main():
    a = sys.argv[1:]
    account = id_ = None
    pos = []
    while a:
        x = a.pop(0)
        if x == "--account": account = a.pop(0)
        elif x == "--id":    id_ = a.pop(0)
        elif x.startswith("-"): sys.exit("unknown option: " + x)
        else: pos.append(x)
    if len(pos) != 3:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    specfile, frm, to = pos
    s = S.load(os.path.join(REPO, specfile) if not os.path.isabs(specfile) else specfile)
    name, symbol = s["name"], s["symbol"]
    id_ = id_ or "%s-%s" % (name, dt.datetime.now().strftime("%Y%m%d-%H%M%S"))

    label = "saved session"
    if account:
        path = account if os.path.isabs(account) else os.path.join(REPO, account)
        if not os.path.exists(path):
            sys.exit("no such account file: " + path)
        for ln in open(path):
            k, _, v = ln.partition("=")
            if k.strip().startswith("MT5_"):
                os.environ[k.strip()] = v.strip()
        label = os.path.basename(path)[:-4] if path.endswith(".env") else os.path.basename(path)

    exe = terminal()
    mt5dir = os.path.dirname(exe)
    ini = os.path.join(REPO, "mql5", "config", "tester.ini")
    runs = os.path.join(HERE, "runs"); os.makedirs(runs, exist_ok=True)
    outdir = os.path.join(HERE, "out", name); os.makedirs(outdir, exist_ok=True)
    log = open(os.path.join(runs, id_ + ".log"), "w")

    def say(*t):
        line = " ".join(str(x) for x in t)
        print(line); log.write(line + "\n"); log.flush()

    say("==", id_, "==")
    say("spec %s on %s, account: %s, %s..%s" % (name, symbol, label, frm, to))
    say("terminal:", exe)

    t0 = dt.datetime.now()
    tkeys = S.tester(s); tkeys["FromDate"], tkeys["ToDate"] = frm, to
    pairs = [(k, S.fmt(v)) for k, v in tkeys.items()]
    pairs += [(k, S.fmt(v)) for k, v in S.inputs(s).items()]
    set_keys(ini, pairs)

    tlog = os.path.join(mt5dir, "Tester", "logs",
                        dt.date.today().strftime("%Y%m%d") + ".log")
    actual = None
    t_test = dt.datetime.now()
    for cp in ("0.00", "0.50"):
        set_keys(ini, [("InpMinClosePos", cp)])
        for f in glob.glob(os.path.join(COMMON, "ORB_%s_*_tester.csv" % symbol)):
            os.unlink(f)
        os.makedirs(os.path.dirname(tlog), exist_ok=True)
        open(tlog, "wb").close()
        cfg = os.path.join(mt5dir, "run.ini")
        shutil.copyfile(ini, cfg)
        if os.environ.get("MT5_LOGIN"):
            with open(cfg, "a") as fh:
                fh.write("\n[Common]\nLogin=%s\nPassword=%s\nServer=%s\n"
                         % (os.environ["MT5_LOGIN"], os.environ["MT5_PASSWORD"],
                            os.environ["MT5_SERVER"]))
        try:
            rc = launch(exe, "run.ini")
        finally:
            if os.path.exists(cfg):
                os.unlink(cfg)          # it may hold a password
        txt = journal_text(tlog)
        hit = [l for l in txt.splitlines()
               if "testing of Experts" in l and ("from %s 00:00" % frm) in l]
        if not hit:
            say("the tester never ran the window starting %s -- is another terminal open?" % frm)
            record(id_, s, label, frm, to, actual, None, "failed",
                   "the tester never started", t0, None, None, tlog)
            sys.exit(1)
        actual = hit[-1].split()[-1]
        found = glob.glob(os.path.join(COMMON, "ORB_%s_*_tester.csv" % symbol))
        dst = os.path.join(COMMON, "new_cp%s.csv" % cp)
        if found:
            shutil.move(found[0], dst)
        else:
            open(dst, "w").write("entry_time,range_pts,spread_pts,mins_after_range,dir,"
                                 "entry,sl,risk_money,profit_money,R,exit,close_pos\n")
        n = max(sum(1 for _ in open(dst)) - 1, 0)
        say("  close-pos %s  %s..%s -> %d trades" % (cp, frm, actual, n))
    set_keys(ini, [("InpMinClosePos", "0.50")])
    secs_test = int((dt.datetime.now() - t_test).total_seconds())
    if actual != to:
        say("  note: asked for %s, the tester would only go to %s" % (to, actual))

    for cp in ("0.50", "0.00"):
        shutil.copyfile(os.path.join(COMMON, "new_cp%s.csv" % cp),
                        os.path.join(outdir, "live_cp%s.csv" % cp))

    t_build = dt.datetime.now()
    env = dict(os.environ, ORB_SPEC=os.path.join(REPO, specfile))
    for step in ("report_data.py", "all_trades.py", "build_report.py", "check_charts.py"):
        p = subprocess.run([sys.executable, step], cwd=HERE, env=env,
                           capture_output=True, text=True)
        for line in (p.stdout or "").splitlines():
            say(" ", line)
        if p.returncode:
            say((p.stderr or "").strip()[-2000:])
            record(id_, s, label, frm, to, actual, None, "failed", step + " failed",
                   t0, secs_test, None, tlog)
            sys.exit(1)
    secs_build = int((dt.datetime.now() - t_build).total_seconds())
    record(id_, s, label, frm, to, actual, True, "ok", None, t0, secs_test, secs_build, tlog)
    say("  record: research/runs/%s.json" % id_)


def record(id_, s, label, frm, to, actual, ran, status, msg, t0, t_test, t_build, tlog):
    """The same shape report.sh writes, so farm_stats.py reads either."""
    def rows(p):
        try:
            return max(sum(1 for _ in open(p)) - 1, 0)
        except OSError:
            return None
    NOISE = ("Virtual Hosting", "MQL5.community", "Data Folder")
    notable = []
    for l in journal_text(tlog).splitlines():
        t = " ".join(l.split())
        if any(k in t for k in NOISE) or len(t) > 300:
            continue
        if any(k in t for k in ("history synchronized", "authorization on", "not specified",
                                "no history", "error", "failed", "Experts")):
            notable.append(t)
    now = dt.datetime.now()
    j = dict(id=id_, spec=s["name"], spec_path=None, symbol=s["symbol"], account=label,
             asked_from=frm, asked_to=to, tester_reported_to=actual, status=status,
             message=msg, started=int(t0.timestamp()), finished=int(now.timestamp()),
             seconds=int((now - t0).total_seconds()), seconds_tester=t_test,
             seconds_build=t_build, runner="local",
             trades=(dict(cp050=rows(os.path.join(COMMON, "new_cp0.50.csv")),
                          cp000=rows(os.path.join(COMMON, "new_cp0.00.csv"))) if ran else None),
             log=id_ + ".log", journal=notable[-12:])
    with open(os.path.join(HERE, "runs", id_ + ".json"), "w") as fh:
        json.dump(j, fh, indent=1)


if __name__ == "__main__":
    main()
