#!/usr/bin/env python3
"""One command for the whole thing. Works on Windows and on Linux.

    python3 orb.py start                 start the control panel
    python3 orb.py stop                  stop it
    python3 orb.py status                is it running, and where
    python3 orb.py restart
    python3 orb.py open                  open it in a browser
    python3 orb.py logs                  tail the panel's output

    python3 orb.py start --local         use the MetaTrader on this machine
    python3 orb.py start --slots 4 --port 8080

    python3 orb.py run SPEC FROM TO      one backtest, no panel
    python3 orb.py runs                  what MetaTrader did on each run
    python3 orb.py compile               compile the EA

`stop` reads a pid file, so there is no pkill pattern to get wrong -- one that
matched a heredoc mentioning the script killed the shell that wrote it.
"""
import os, sys, json, time, signal, socket, subprocess, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "research", "runs")
PID = os.path.join(RUNS, "panel.pid")
LOG = os.path.join(RUNS, "panel.log")
WINDOWS = os.name == "nt"
PY = sys.executable


def read_pid():
    try:
        with open(PID) as fh:
            d = json.load(fh)
        return d if alive(d["pid"]) else None
    except (OSError, ValueError, KeyError):
        return None


def alive(pid):
    if WINDOWS:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                             capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start(argv):
    got = read_pid()
    if got:
        print("already running on port %d (pid %d)" % (got["port"], got["pid"]))
        print("  %s" % url(got))
        return 0
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
    slots = int(argv[argv.index("--slots") + 1]) if "--slots" in argv else 3
    local = "--local" in argv
    if listening(port):
        print("port %d is already in use by something else" % port)
        return 1
    os.makedirs(RUNS, exist_ok=True)
    cmd = [PY, os.path.join("research", "serve.py"), "--port", str(port), "--slots", str(slots)]
    if local:
        cmd.append("--local")
    out = open(LOG, "ab")
    kw = dict(cwd=HERE, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    if WINDOWS:
        kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    p = subprocess.Popen(cmd, **kw)
    for _ in range(40):
        if listening(port):
            break
        if p.poll() is not None:
            print("the panel exited immediately. last lines:")
            print(tail(LOG, 15))
            return 1
        time.sleep(0.25)
    else:
        print("the panel did not come up within 10s. last lines:")
        print(tail(LOG, 15))
        return 1
    d = dict(pid=p.pid, port=port, slots=slots, local=local)
    with open(PID, "w") as fh:
        json.dump(d, fh)
    print("panel running: %s" % url(d))
    print("  runner: %s   slots: %d" % ("this machine's terminal" if local else "containers", slots))
    print("  stop with: %s orb.py stop" % os.path.basename(PY))
    return 0


def url(d):
    return "http://127.0.0.1:%d" % d["port"]


def stop(_argv):
    got = read_pid()
    if not got:
        if os.path.exists(PID):
            os.unlink(PID)
        print("not running")
        return 0
    pid = got["pid"]
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except OSError:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    for _ in range(20):
        if not alive(pid):
            break
        time.sleep(0.2)
    else:
        if not WINDOWS:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    if os.path.exists(PID):
        os.unlink(PID)
    print("stopped (pid %d)" % pid)
    return 0


def status(_argv):
    got = read_pid()
    if not got:
        print("panel: not running")
        return 1
    print("panel: running")
    print("  url    %s" % url(got))
    print("  pid    %d" % got["pid"])
    print("  slots  %d" % got["slots"])
    print("  runner %s" % ("this machine's terminal" if got["local"] else "containers"))
    return 0


def tail(path, n):
    try:
        with open(path, "rb") as fh:
            return b"".join(fh.readlines()[-n:]).decode("utf-8", "replace").rstrip()
    except OSError:
        return "(no log yet)"


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    cmd, rest = a[0], a[1:]
    if cmd == "start":   return start(rest)
    if cmd == "stop":    return stop(rest)
    if cmd == "status":  return status(rest)
    if cmd == "restart":
        stop(rest); return start(rest)
    if cmd == "open":
        got = read_pid()
        if not got:
            print("not running -- start it first")
            return 1
        webbrowser.open(url(got))
        print(url(got))
        return 0
    if cmd == "logs":
        print(tail(LOG, int(rest[0]) if rest else 40))
        return 0
    if cmd == "runs":
        return subprocess.run([PY, os.path.join("research", "farm_stats.py")] + rest,
                              cwd=HERE).returncode
    if cmd == "run":
        if len(rest) < 3:
            print("usage: orb.py run SPEC FROM TO [--account FILE]")
            return 2
        return subprocess.run([PY, os.path.join("research", "run_local.py")] + rest,
                              cwd=HERE).returncode
    if cmd == "compile":
        return compile_ea()
    print("unknown command: %s\n" % cmd)
    print(__doc__.strip())
    return 2


def compile_ea():
    """MetaEditor exits 1 on a clean compile, so the log is the only verdict."""
    mt5 = os.environ.get("MT5_TERMINAL")
    mt5 = os.path.dirname(mt5) if mt5 else None
    for c in ([r"C:\Program Files\MetaTrader 5"] if WINDOWS else
              [os.path.expanduser("~/.wine_mt5/drive_c/Program Files/MetaTrader 5")]):
        mt5 = mt5 or (c if os.path.isdir(c) else None)
    if not mt5:
        print("no MetaTrader found. Set MT5_TERMINAL to terminal64.exe")
        return 1
    ed = os.path.join(mt5, "MetaEditor64.exe")
    rel = os.path.join("MQL5", "Experts", "ORB.mq5")
    cmd = [ed, "/compile:" + rel, "/log"]
    if not WINDOWS:
        cmd = ["wine"] + cmd
    subprocess.run(cmd, cwd=mt5, capture_output=True,
                   env=dict(os.environ, WINEDEBUG="-all"))
    log = os.path.join(mt5, "MQL5", "Experts", "ORB.log")
    try:
        txt = open(log, "rb").read().decode("utf-16-le", "ignore")
    except OSError:
        print("no compile log at %s" % log)
        return 1
    line = [l.strip() for l in txt.splitlines() if l.strip().startswith("Result:")]
    print(line[-1] if line else "no Result line in the log")
    return 0 if line and "0 errors" in line[-1] else 1


if __name__ == "__main__":
    sys.exit(main())
