"""How far the study is covered, and whether there is anything new to fetch.

Prints two lines:

    covered_through  YYYY.MM.DD    exclusive -- the first day NOT yet accounted for
    want_through     YYYY.MM.DD    exclusive -- the first day not yet finished

Exits 0 if there is work to do, 1 if everything is already current, so the
caller can skip launching MetaTrader at all.

A day with no trade leaves no row, so the trade files cannot answer this on
their own -- coverage comes from the tester's own reported range plus whatever
was replayed on top of it.
"""
import datetime as dt, json, os, sys
from mt5paths import COMMON as D

HERE = os.path.dirname(os.path.abspath(__file__))


def covered_through():
    """First date not yet accounted for, from the tester marker plus replays."""
    d = None
    p = os.path.join(D, "tested_through.txt")
    if os.path.exists(p):
        txt = open(p).read().strip()
        if txt:
            d = dt.datetime.strptime(txt, "%Y.%m.%d").date()
    r = os.path.join(HERE, "replayed.json")
    if os.path.exists(r):
        rows = json.load(open(r)).get("rows", [])
        if rows:
            last = max(dt.date.fromisoformat(x["date"]) for x in rows)
            d = max(d, last + dt.timedelta(days=1)) if d else last + dt.timedelta(days=1)
    return d


def want_through(now=None):
    """First date not worth asking about yet.

    Deliberately does NOT wait out the 90-minute cap. Running the pipeline is
    itself the statement that the session is over, and a trade stopped at
    minute five is finished whatever the clock says. Whether it really resolved
    is decided by the bars, in sim_offline.session, which refuses a trade it
    cannot carry to an exit.
    """
    now = now or dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    day = now.date()
    # Only Monday to Thursday can produce a trade; anything later in the week
    # is already accounted for once Thursday is.
    while day.weekday() > 3:
        day -= dt.timedelta(days=1)
    return day + dt.timedelta(days=1)


def main():
    have, want = covered_through(), want_through()
    print("covered_through  %s" % (have.strftime("%Y.%m.%d") if have else "nothing"))
    print("want_through     %s" % want.strftime("%Y.%m.%d"))
    if have and have >= want:
        print("up to date")
        sys.exit(1)
    print("behind by %d day(s)" % ((want - have).days if have else 0))


if __name__ == "__main__":
    main()
