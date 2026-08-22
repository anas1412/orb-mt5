#!/usr/bin/env python3
"""Build the release zip.

This is the same script CI runs, so it can be tested locally before tagging:

    python3 .github/scripts/package.py v1.0.0 /tmp/out
"""
import hashlib, os, sys, zipfile

# The zip mirrors the MetaTrader tree, so a user copies MQL5/ over theirs and
# is done -- no deciding which file belongs where.
LAYOUT = {
    "MQL5/Experts/ORB.mq5":               "ORB.mq5",
    "MQL5/Experts/CheckBrokerOffset.mq5": "CheckBrokerOffset.mq5",
    "MQL5/Experts/TestTimeZones.mq5":     "TestTimeZones.mq5",
    "MQL5/Include/TimeZones.mqh":         "TimeZones.mqh",
    "MQL5/Include/Panel.mqh":             "Panel.mqh",
    "README.md":                          "README.md",
    "LICENSE":                            "LICENSE",
    "tester.ini":                         "tester.ini",
}

# Anything here missing is a failed release, not a warning. A zip without the
# EA in it looks fine until someone downloads it.
REQUIRED = ["MQL5/Experts/ORB.mq5", "MQL5/Include/TimeZones.mqh",
            "MQL5/Include/Panel.mqh", "README.md", "LICENSE", "INSTALL.txt"]

INSTALL = """ORB {tag}

1. In MetaTrader: File > Open Data Folder
2. Copy the MQL5 folder from this zip over the one you find there
3. In MetaEditor open MQL5/Experts/ORB.mq5 and press F7 to compile
4. Back in the terminal: Navigator > right-click > Refresh
5. Drag ORB onto an XAUUSD M1 chart and tick "Allow Algo Trading"
6. Turn on AutoTrading. The panel starts OFF - press TRADING ON when ready

Releases ship source, not a compiled .ex5, so the code you run is the code you
can read. Compiling is one keystroke.

The defaults are the tested configuration. Two settings depend on YOUR broker
and should be checked before trading real money:

  InpWinterOffset    hours your broker is ahead of UTC in winter
  InpFollowsUSDST    whether it switches DST on US or EU dates

Run the included CheckBrokerOffset script to measure both.

Full report: https://anas1412.github.io/orb-mt5/
"""


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: package.py <tag> [outdir]")
    tag = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pkg = "ORB-%s" % tag
    os.makedirs(out, exist_ok=True)
    zpath = os.path.join(out, pkg + ".zip")

    written = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for dest, src in sorted(LAYOUT.items()):
            path = os.path.join(root, src)
            if not os.path.exists(path):
                sys.exit("missing source file: %s" % src)
            z.write(path, "%s/%s" % (pkg, dest))
            written.append(dest)
        z.writestr("%s/INSTALL.txt" % pkg, INSTALL.format(tag=tag))
        written.append("INSTALL.txt")

    for req in REQUIRED:
        if req not in written:
            sys.exit("required file absent from the package: %s" % req)

    digest = hashlib.sha256(open(zpath, "rb").read()).hexdigest()
    open(zpath + ".sha256", "w").write("%s  %s\n" % (digest, os.path.basename(zpath)))

    print("%s  (%.1f KB)" % (zpath, os.path.getsize(zpath) / 1024.0))
    for name in sorted(zipfile.ZipFile(zpath).namelist()):
        print("   ", name)
    print("sha256  %s" % digest)


if __name__ == "__main__":
    main()
