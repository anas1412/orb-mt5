"""Audit the published pages. Exits non-zero if anything is wrong.

`check_charts.py` audits the ORB's trade charts against the tester CSV. This is
the other half: the things that go wrong across all the pages at once, every
one of which has actually shipped broken at least once.

    python3 research/check_pages.py

  one stylesheet   no page inlines CSS; every page links site.css
  one nav          exactly one site nav, every entry resolving, the page
                   itself marked current
  sections         numbered 1..n in document order, no gaps
  charts           every image referenced exists, and every image on disk is
                   referenced -- an orphan is a picture of a trade that has
                   since changed
  percentages      every data-pct span is rendered server-side at ITS OWN
                   page's risk. account.html runs at 2% and the rest at 2.5%,
                   and the wrong default shipped once with JavaScript hiding it
  totals           a table that totals R carries the percentage beside it
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# page -> (the risk its percentages are rendered at, the gallery it owns)
PAGES = {
    "index.html":   (2.5, None),
    "orbnq.html":   (2.5, None),
    "orb.html":     (2.5, "trades"),
    "pdfade.html":  (2.5, "trades-gold"),
    "nqfade.html":  (2.5, "trades-nq"),
    "account.html": (2.0, None),
}
NAV_LINKS = len(PAGES)

bad = []


def fail(page, msg):
    bad.append("%-14s %s" % (page, msg))


def check(name, risk, web, s):
    if s.count("<style>"):
        fail(name, "inlines CSS; every rule belongs in site.css")
    if 'href="site.css"' not in s:
        fail(name, "does not link site.css")

    navs = re.findall(r'<nav class="site">.*?</nav>', s, re.S)
    if len(navs) != 1:
        fail(name, "has %d site navs, expected 1" % len(navs))
    elif navs[0].count("<a ") != NAV_LINKS:
        fail(name, "nav has %d links, expected %d" % (navs[0].count("<a "), NAV_LINKS))
    cur = re.findall(r'<a href="([^"]+)" aria-current="page"', s)
    if cur != [name]:
        fail(name, "marks %s as the current page" % (cur or ["nothing"])[0])

    for link in sorted(set(re.findall(r'href="([a-z0-9_.-]+\.html)"', s))):
        if not os.path.exists(os.path.join(REPO, link)):
            fail(name, "dead link to %s" % link)

    nums = [int(n) for n in re.findall(r'<span class="num">(\d+)</span>', s)]
    if nums and nums != list(range(1, len(nums) + 1)):
        fail(name, "sections numbered %s, not 1..%d" % (nums, len(nums)))

    imgs = re.findall(r'src="(trades[^"]+\.png)"', s)
    for i in imgs:
        if not os.path.exists(os.path.join(REPO, i)):
            fail(name, "missing chart %s" % i)
    if web:
        used = set(re.findall(r'src="%s/([^"]+\.png)"' % web, s))
        have = {f for f in os.listdir(os.path.join(REPO, web)) if f.endswith(".png")}
        for f in sorted(have - used):
            fail(name, "orphan chart %s/%s -- not referenced by any card" % (web, f))
        for f in sorted(used - have):
            fail(name, "card points at %s/%s, which is not on disk" % (web, f))

    # Rendered server-side so a reader without JavaScript gets a real report,
    # which means the number in the file has to be right on its own.
    for m in re.finditer(r'data-pct="(-?[\d.]+)"[^>]*>\s*([+-][\d.]+)\s*<', s):
        r, shown = float(m.group(1)), float(m.group(2))
        if abs(shown - risk * r) > 0.06:
            fail(name, "percentage %s rendered for %s R, which is %+.1f at %g%%"
                 % (m.group(2), m.group(1), risk * r, risk))
            break

    # A column of R multiples means nothing until it is translated. Judge the
    # CELLS, not the header: "Total return" is already a percentage, and an
    # earlier version of this check flagged it every run.
    for t in re.findall(r'<table.*?</table>', s, re.S):
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', t, re.S)
        # a DATA cell is nothing but the number; prose that happens to mention
        # "+0.5R" is not a column of totals
        has_r = any(re.fullmatch(r'[+-][\d.]+\s*R', re.sub(r'<[^>]+>', '', c).strip())
                    for c in cells)
        if has_r and "data-pct" not in t:
            head = " ".join(re.sub(r'<[^>]+>', '', c).strip()
                            for c in cells[:8] if c.strip())[:60]
            fail(name, "table totals R with no percentage beside it: %s" % head)


def main():
    for name, (risk, web) in PAGES.items():
        p = os.path.join(REPO, name)
        if not os.path.exists(p):
            fail(name, "does not exist"); continue
        check(name, risk, web, open(p).read())
    if bad:
        print("check_pages: %d problem%s\n" % (len(bad), "" if len(bad) == 1 else "s"))
        for b in bad:
            print("  " + b)
        sys.exit(1)
    print("check_pages: %d pages, all clean" % len(PAGES))


if __name__ == "__main__":
    main()
