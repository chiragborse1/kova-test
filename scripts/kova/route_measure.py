"""Every route gets the reading measure, not just the six I kept re-measuring.

The redesign fixed the transcript from 267 chars-per-line to 65 and left it
there. `ui_audit.py` checks six routes. The other six - the ones behind the
"More" menu I added - were never measured at all, on the grounds that they
were new code rather than old.

Pointed at them, `/webhooks` renders its own explanatory paragraph at:

    181 chars per line, 981px wide, 18px tall

That is worse than the 267 the entire redesign set out to fix, still live,
on a page I had described as "reachable now" and stopped thinking about. A
197-character sentence in a full-width Alert is one 981px line.

Nothing caught it because the six-route list in `ui_audit.py` is a list. This
gate derives the route list from `app/routes.ts` instead, so a route cannot be
added without being measured.

Reports per route: chars-per-line (widest long paragraph), clipped columns,
and whether the surface rendered at all - an overlay that mounts empty is a
failure that reads exactly like a route with no prose on it.

Usage:  py scripts/kova/route_measure.py
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTES_TS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "apps", "desktop", "src", "app", "routes.ts",
)

# Overlays that need a session, a gateway, or a capability the sandbox does
# not have. They are still visited - to prove they MOUNT - but a route that
# legitimately has no prose is not a reading-measure failure.
NO_PROSE_OK = {"session-import", "starmap"}

PROBE = r"""JSON.stringify((()=>{
  const cvs = document.createElement('canvas').getContext('2d');
  let worst = 0, worstW = 0, txt = '';
  for (const p of document.querySelectorAll('p, li, td')) {
    const t = (p.textContent || '').trim();
    if (t.length < 120) continue;
    const s = getComputedStyle(p), r = p.getBoundingClientRect();
    if (r.width < 200) continue;
    cvs.font = s.fontWeight + ' ' + s.fontSize + ' ' + s.fontFamily;
    const adv = cvs.measureText('abcdefghijklmnopqrstuvwxyz').width / 26;
    const cpl = Math.round(r.width / adv);
    if (cpl > worst) { worst = cpl; worstW = Math.round(r.width); txt = t.slice(0, 40); }
  }

  let clippedCols = 0;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (!/auto|scroll/.test(cs.overflowY)) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 120 || r.height < 120) continue;
    if (r.width >= innerWidth - 2) continue;   // the document scroller is fine
    if (el.scrollHeight > el.clientHeight + 8) clippedCols++;
  }

  return {
    cpl: worst, w: worstW, txt,
    clippedCols,
    mounted: document.body.innerText.trim().length > 0,
    crashed: /Something broke/.test(document.body.innerText)
  };
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def core_routes():
    """Read the route list from the source, so it cannot fall behind."""
    src = open(ROUTES_TS, encoding="utf-8").read()
    pairs = re.findall(r"^export const (\w+_ROUTE) = '([^']+)'", src, re.M)
    skip = {"NEW_CHAT_ROUTE"}
    return [(sym, path) for sym, path in pairs if sym not in skip]


def main():
    routes = core_routes()
    print("  %d core routes read from routes.ts\n" % len(routes))
    print("  %-16s %-8s %8s %7s  %s" % ("route", "path", "cpl", "clipped", "note"))

    bad = []
    for sym, path in routes:
        ev("location.hash=" + repr("#" + path))
        time.sleep(3)
        raw = ev(PROBE)
        if not raw:
            print("  %-16s %-8s  PROBE FAILED" % (sym.replace("_ROUTE", "").lower(), path))
            bad.append("%s: the probe did not run" % sym)
            continue
        d = json.loads(raw)

        note = ""
        if d["crashed"]:
            note = "CRASHED"
            bad.append("%s (%s) renders the error boundary" % (sym, path))
        elif not d["mounted"]:
            note = "did not mount"
            bad.append("%s (%s) mounted empty" % (sym, path))

        name = sym.replace("_ROUTE", "").lower()
        if d["cpl"] == 0 and name not in NO_PROSE_OK and d["mounted"] and not note:
            note = "no prose (ok if genuinely empty)"

        print("  %-16s %-8s %8s %7d  %s" % (name, path, d["cpl"], d["clippedCols"], note))

        if d["cpl"] > 120:
            bad.append("%s (%s): %d chars per line in a %dpx column - %s"
                       % (sym, path, d["cpl"], d["w"], d["txt"]))
        if d["clippedCols"]:
            bad.append("%s (%s): %d column(s) clipping content with no scroll cue"
                       % (sym, path, d["clippedCols"]))

    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  every core route holds a readable measure and mounts cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
