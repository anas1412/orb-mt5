"""The control panel: accounts, backtests, and what MetaTrader did.

    python3 research/serve.py                 # containers, 3 slots, :8765
    python3 research/serve.py --slots 4 --port 8080
    python3 research/serve.py --local          # this machine's terminal instead

Runs go to containers by default, one isolated terminal per slot. The terminal
on this machine holds the tester lock and the live EA's saved session, so a
backtest must not reach into it. A container has no saved session, so a run
needs an account -- add one on the Accounts tab.

Binds to loopback only, and prints a token that every /api call must carry.
It writes broker credentials to accounts/<label>.env with mode 600, so it must
never be reachable from anywhere but this machine -- reach it from a phone over
Tailscale, never a port forward.

A password arrives once, on the way in. It is written to the account file and
never read back out: no endpoint returns it, no log line contains it, and a run
record stores only the label.
"""
import os, sys, json, csv, glob, queue, shutil, secrets, threading, subprocess
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "lib"))
import spec as S

WEB      = os.path.join(HERE, "web")
RUNS     = os.path.join(HERE, "runs")
ACCOUNTS = os.path.join(REPO, "accounts")
STRATS   = os.path.join(REPO, "strategies")
GENDIR   = os.path.join(STRATS, "generated")
MT5H     = os.path.expanduser("~/.wine_mt5/drive_c/Program Files/MetaTrader 5")
CT       = "/root/.wine_mt5/drive_c/Program Files/MetaTrader 5"
CTC      = "/root/.wine_mt5/drive_c/users/root/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
HOSTC    = os.path.expanduser("~/.wine_mt5/drive_c/users/%s/AppData/Roaming/MetaQuotes/"
                              "Terminal/Common/Files" % os.environ.get("USER", ""))

TOKEN = os.environ.get("ORB_TOKEN") or secrets.token_urlsafe(18)
SLOTS = 3
CONTAINERS = True          # --local opts out; see main()
IMAGE = os.environ.get("IMAGE", "orb-mt5")

JOBS = {}                      # id -> dict, the queue and its history
Q = queue.Queue()
LOCK = threading.Lock()


# ---------------------------------------------------------------- accounts
def account_labels():
    out = []
    for p in sorted(glob.glob(os.path.join(ACCOUNTS, "*.env"))):
        label = os.path.basename(p)[:-4]
        if label == "example":
            continue
        server = login = ""
        try:
            for line in open(p):
                k, _, v = line.partition("=")
                if k.strip() == "MT5_SERVER": server = v.strip()
                if k.strip() == "MT5_LOGIN":  login = v.strip()
        except OSError:
            pass
        # the login is shown masked so two accounts on one server are tellable
        out.append(dict(label=label, server=server,
                        login=("*" * max(len(login) - 3, 0) + login[-3:]) if login else ""))
    return out


def account_write(body):
    label = (body.get("label") or "").strip()
    if not label.replace("-", "").replace("_", "").isalnum():
        raise ValueError("label must be letters, digits, - or _")
    for k in ("server", "login", "password"):
        if not (body.get(k) or "").strip():
            raise ValueError("%s is required" % k)
    os.makedirs(ACCOUNTS, exist_ok=True)
    p = os.path.join(ACCOUNTS, label + ".env")
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("# written by the control panel; keep out of git\n")
        fh.write("MT5_SERVER=%s\nMT5_LOGIN=%s\nMT5_PASSWORD=%s\n"
                 % (body["server"].strip(), body["login"].strip(), body["password"]))
    os.chmod(p, 0o600)
    return label


# ---------------------------------------------------------------- specs
def spec_summary(path):
    try:
        s = S.load(path)
    except Exception as e:
        return dict(file=os.path.basename(path), name=os.path.basename(path), error=str(e))
    ses, ru, ri, da = s["session"], s["rules"], s["risk"], s["dates"]
    to = "today" if da["to"] == "today" else da["to"].isoformat()
    return dict(file=os.path.relpath(path, REPO), name=s["name"], symbol=s["symbol"],
                start=ses["start"], tz=ses["tz"], range_min=ses["range_min"],
                signal_tf=ses["signal_tf"], entry_window=ses["entry_window_min"],
                hold=ses["hold_min"], rr=ru["rr"], sl_pct=ru["sl_pct_of_range"],
                direction=ru["direction"], half=ru["half_filter"],
                min_range_pct=ru["min_range_pct"], days=ru["days"],
                risk=ri["per_trade"], frm=da["from"].isoformat(), to=to,
                output=s["report"]["output"] or None, generated="generated/" in path)


def result_for(s):
    """Headline numbers from the spec's own report_data.json, if it has run."""
    d = os.path.join(HERE, "data") if s.get("name") == "asia-gold" \
        else os.path.join(HERE, "out", s.get("name") or "")
    p = os.path.join(d, "report_data.json")
    if not os.path.exists(p):
        return None
    try:
        j = json.load(open(p))
    except (OSError, ValueError):
        return None
    H = j.get("headline") or {}
    sw = {round(x["risk"], 2): x for x in (j.get("sweep") or [])}
    row = sw.get(round(float(s.get("risk") or 0), 2)) or {}
    out = os.path.join(REPO, s.get("output") or "")
    return dict(trades=H.get("trades"), wr=H.get("wr"), ev=H.get("ev"),
                total=H.get("total"), sessions=H.get("sessions"),
                pass_pct=row.get("pass_pct"), to_pass=row.get("trades"),
                worst_run=(j.get("streaks") or {}).get("worst_loss"),
                run_cost=row.get("run_cost"),
                report=os.path.basename(out) if s.get("output") and os.path.exists(out) else None,
                built=int(os.path.getmtime(p)))


def specs():
    ps = sorted(glob.glob(os.path.join(STRATS, "*.toml")))
    ps += sorted(glob.glob(os.path.join(GENDIR, "*.toml")))
    out = []
    for p in ps:
        d = spec_summary(p)
        if not d.get("error"):
            d["result"] = result_for(d)
        out.append(d)
    return out


TOML_KEYS = [("session", ["start", "range_min", "entry_window_min", "hold_min", "signal_tf"]),
             ("rules",   ["rr", "sl_pct_of_range", "stop_move_at_r", "stop_move_to_r",
                          "half_filter", "direction", "min_range_pct", "days"]),
             ("risk",    ["per_trade"])]


def toml_value(v):
    if isinstance(v, bool):  return "true" if v else "false"
    if isinstance(v, list):  return "[" + ", ".join('"%s"' % x for x in v) + "]"
    if isinstance(v, (int, float)): return repr(v)
    return '"%s"' % v


def spec_write(body):
    """Build a spec from the form, validate it, and keep it under generated/."""
    name = (body.get("name") or "").strip()
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("name must be letters, digits, - or _")
    lines = ["# written by the control panel", 'name = "%s"' % name,
             'symbol = "%s"' % (body.get("symbol") or "XAUUSD")]
    for section, keys in TOML_KEYS:
        got = {k: body[k] for k in keys if k in body and body[k] not in ("", None)}
        if not got:
            continue
        lines.append("\n[%s]" % section)
        for k, v in got.items():
            lines.append("%s = %s" % (k, toml_value(v)))
    lines.append('\n[dates]\nfrom = %s' % (body.get("frm") or "2026-01-01"))
    lines.append('to   = %s' % ('"today"' if (body.get("to") or "today") == "today" else body["to"]))
    lines.append('\n[report]\noutput = "%s.html"\ntitle  = "%s"' % (name, name))
    os.makedirs(GENDIR, exist_ok=True)
    p = os.path.join(GENDIR, name + ".toml")
    open(p, "w").write("\n".join(lines) + "\n")
    try:
        S.load(p)                      # the schema is the validator; no second copy of it
    except Exception as e:
        os.unlink(p)
        raise ValueError(str(e))
    return os.path.relpath(p, REPO)


# ---------------------------------------------------------------- runs
def spec_fields(name):
    for p in (os.path.join(GENDIR, name + ".toml"), os.path.join(STRATS, name + ".toml")):
        if os.path.exists(p):
            d = spec_summary(p)
            d["editable"] = p.startswith(GENDIR)
            return d
    return None


def spec_delete(name):
    """Only the panel's own specs. The tracked ones are the repo's, not the UI's."""
    p = os.path.join(GENDIR, name + ".toml")
    if not os.path.exists(p):
        raise ValueError("only strategies created here can be deleted")
    os.unlink(p)
    return name


def run_records():
    out = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        try:
            out.append(json.load(open(p)))
        except (OSError, ValueError):
            pass
    return sorted(out, key=lambda r: r.get("started") or 0, reverse=True)


def window_for(specfile):
    s = S.load(os.path.join(REPO, specfile))
    d = s["dates"]
    to = (dt.date.today() + dt.timedelta(days=1)) if d["to"] == "today" else d["to"]
    return d["from"].strftime("%Y.%m.%d"), to.strftime("%Y.%m.%d")


def seed_slot(slot):
    for v in ("bases", "tester", "config", "common"):
        subprocess.run(["docker", "volume", "create", "orb-%s-%d" % (v, slot)],
                       capture_output=True)
    empty = subprocess.run(["docker", "run", "--rm", "-v", "orb-bases-%d:/b" % slot, IMAGE,
                            "sh", "-c", "ls -A /b 2>/dev/null | head -1"],
                           capture_output=True, text=True).stdout.strip()
    if not empty:
        subprocess.run(["docker", "run", "--rm", "-v", "orb-bases-%d:/b" % slot,
                        "-v", "%s/Bases:/src:ro" % MT5H, IMAGE, "sh", "-c", "cp -a /src/. /b/"],
                       capture_output=True)


def command(job, slot):
    spec_in_repo = job["spec"]
    if CONTAINERS:
        args = ["bash", "research/report.sh", "--id", job["id"]]
        if job.get("account"):
            pass                       # credentials go in through --env-file, not a path
        seed_slot(slot)
        d = ["docker", "run", "--rm", "--name", "orb-panel-%d" % slot,
             "--cpus", "1.5", "--memory", "2g",
             "-v", "orb-bases-%d:%s/Bases" % (slot, CT),
             "-v", "orb-tester-%d:%s/Tester" % (slot, CT),
             "-v", "orb-config-%d:%s/Config" % (slot, CT),
             # Common/Files is per slot because run_window.sh writes new_cp*.csv
             # there; the bar dumps come in read-only and the entrypoint copies them.
             "-v", "orb-common-%d:%s" % (slot, CTC),
             "-v", "%s:/bars:ro" % HOSTC,
             "-v", "%s:/root/orb/strategy" % REPO]
        if job.get("account"):
            d += ["--env-file", os.path.join(ACCOUNTS, job["account"] + ".env")]
        return d + [IMAGE] + args + [spec_in_repo, job["from"], job["to"]]
    # Local runs go through run_local.py, not the bash script: it launches the
    # installed terminal directly, so this path works on Windows as well as on
    # Linux with Wine.
    args = [sys.executable, "research/run_local.py", "--id", job["id"]]
    if job.get("account"):
        args += ["--account", os.path.join("accounts", job["account"] + ".env")]
    return args + [spec_in_repo, job["from"], job["to"]]


def worker(slot):
    while True:
        jid = Q.get()
        job = JOBS.get(jid)
        if not job or job["state"] == "cancelled":
            Q.task_done(); continue
        with LOCK:
            job.update(state="running", slot=slot, started=int(dt.datetime.now().timestamp()))
        try:
            p = subprocess.run(command(job, slot), cwd=REPO, capture_output=True, text=True)
            with LOCK:
                job["state"] = "done" if p.returncode == 0 else "failed"
                job["exit"] = p.returncode
                job["tail"] = (p.stdout or p.stderr or "")[-4000:]
        except Exception as e:
            with LOCK:
                job.update(state="failed", exit=-1, tail=str(e))
        finally:
            with LOCK:
                job["finished"] = int(dt.datetime.now().timestamp())
            Q.task_done()


# ---------------------------------------------------------------- http
class H(BaseHTTPRequestHandler):
    server_version = "orb-panel"

    def log_message(self, *a):
        pass                            # a request line could carry a query string

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else str(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json")

    def _auth(self):
        if self.headers.get("X-Orb-Token") == TOKEN:
            return True
        self._json(dict(error="bad or missing token"), 401)
        return False

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(WEB, "index.html"), "rb").read(),
                              "text/html; charset=utf-8")
        if path == "/token":            # so the page can bootstrap on this machine
            return self._send(200, TOKEN, "text/plain")
        if path.startswith("/report/"):
            # the generated reports live at the repo root; serve them read-only
            fn = os.path.basename(unquote(path[len("/report/"):]))
            fp = os.path.join(REPO, fn)
            if not fn.endswith(".html") or not os.path.exists(fp):
                return self._send(404, "no such report", "text/plain")
            return self._send(200, open(fp, "rb").read(), "text/html; charset=utf-8")
        if path.startswith("/trades"):
            rel = unquote(path.lstrip("/"))
            fp = os.path.normpath(os.path.join(REPO, rel))
            if not fp.startswith(REPO) or not os.path.exists(fp) or not fp.endswith(".png"):
                return self._send(404, "no such chart", "text/plain")
            return self._send(200, open(fp, "rb").read(), "image/png")
        if not path.startswith("/api/"):
            return self._json(dict(error="not found"), 404)
        if not self._auth():
            return
        if path == "/api/state":
            with LOCK:
                jobs = sorted(JOBS.values(), key=lambda j: j.get("queued", 0), reverse=True)[:40]
                jobs = [dict(j, tail=None) for j in jobs]
            return self._json(dict(accounts=account_labels(), specs=specs(),
                                   runs=run_records()[:40], jobs=jobs,
                                   slots=SLOTS, containers=CONTAINERS))
        if path.startswith("/api/runs/") and path.endswith("/log"):
            rid = unquote(path.split("/")[3])
            p = os.path.join(RUNS, rid + ".log")
            if not os.path.exists(p):
                return self._json(dict(error="no log"), 404)
            return self._send(200, open(p, "rb").read()[-20000:], "text/plain; charset=utf-8")
        if path.startswith("/api/specs/"):
            d = spec_fields(unquote(path.split("/")[3]))
            return self._json(d or dict(error="no such strategy"), 200 if d else 404)
        if path.startswith("/api/jobs/"):
            jid = unquote(path.split("/")[3])
            with LOCK:
                j = JOBS.get(jid)
            return self._json(j or dict(error="no job"), 200 if j else 404)
        return self._json(dict(error="not found"), 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._auth():
            return
        try:
            body = self._body()
        except ValueError:
            return self._json(dict(error="bad json"), 400)
        try:
            if path == "/api/accounts":
                return self._json(dict(label=account_write(body)), 201)
            if path == "/api/specs":
                return self._json(dict(file=spec_write(body)), 201)
            if path == "/api/runs":
                sf = body.get("spec")
                if not sf:
                    return self._json(dict(error="spec is required"), 400)
                if not os.path.exists(os.path.join(REPO, sf)):
                    return self._json(dict(error="no such spec"), 400)
                f, t = window_for(sf)
                f = body.get("from") or f
                t = body.get("to") or t
                name = S.load(os.path.join(REPO, sf))["name"]
                jid = "%s-%s" % (name, dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
                job = dict(id=jid, spec=sf, name=name, account=body.get("account") or None,
                           **{"from": f}, to=t, state="queued", slot=None,
                           queued=int(dt.datetime.now().timestamp()))
                with LOCK:
                    JOBS[jid] = job
                Q.put(jid)
                return self._json(job, 202)
            if path.startswith("/api/jobs/") and path.endswith("/cancel"):
                jid = unquote(path.split("/")[3])
                with LOCK:
                    j = JOBS.get(jid)
                    if j and j["state"] == "queued":
                        j["state"] = "cancelled"
                        return self._json(j)
                return self._json(dict(error="only a queued job can be cancelled"), 409)
        except ValueError as e:
            return self._json(dict(error=str(e)), 400)
        except Exception as e:
            return self._json(dict(error="%s: %s" % (type(e).__name__, e)), 500)
        return self._json(dict(error="not found"), 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not self._auth():
            return
        if path.startswith("/api/specs/"):
            try:
                return self._json(dict(deleted=spec_delete(unquote(path.split("/")[3]))))
            except ValueError as e:
                return self._json(dict(error=str(e)), 400)
        if path.startswith("/api/accounts/"):
            label = unquote(path.split("/")[3])
            p = os.path.join(ACCOUNTS, label + ".env")
            if label == "example" or not os.path.exists(p):
                return self._json(dict(error="no such account"), 404)
            os.unlink(p)
            return self._json(dict(deleted=label))
        return self._json(dict(error="not found"), 404)


def main():
    global SLOTS, CONTAINERS
    a = sys.argv[1:]
    port = int(a[a.index("--port") + 1]) if "--port" in a else 8765
    if "--slots" in a:
        SLOTS = int(a[a.index("--slots") + 1])
    # Containers by default. A run must not reach into the terminal the live EA
    # sits in: it holds the tester lock, it carries the saved session, and a
    # reset or a recompile touches it. --local is for when there is no image.
    CONTAINERS = "--local" not in a
    os.makedirs(RUNS, exist_ok=True)
    for i in range(1, SLOTS + 1):
        threading.Thread(target=worker, args=(i,), daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print("control panel  http://127.0.0.1:%d/?token=%s" % (port, TOKEN))
    print("  slots: %d    runner: %s" % (SLOTS, "containers" if CONTAINERS else "this machine"))
    print("  loopback only. reach it from a phone over Tailscale, never a port forward.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
