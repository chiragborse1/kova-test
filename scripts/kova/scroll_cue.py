"""A scroll container whose overflow is CONTENT must say so.

The app hides every scrollbar until hover. That is a good default: a surface
you are already dragging does not need a persistent stripe down its edge. It
is wrong wherever the overflow is not a gesture but the shape of the content -
a list of destinations, a column of facets - because then the container reads
as ending at its last visible row.

Measured on the running app before this gate existed:

    capabilities facet rail   1492px of rows in a 783px box (48% clipped)
    messaging platform list   1314px of rows in a 740px box (574px clipped)

Neither is strictly unreachable - both scroll. Both also present as a short
list, because the thumb only paints on hover. In the capabilities rail the
entire Tags section began 200px BELOW the window, so tag filtering did not
exist as far as anyone could tell.

Walks every route, finds every scroll container that is clipping, and checks
whether its thumb is actually painted without a pointer over it. The test is
the computed `::-webkit-scrollbar-thumb` colour rather than `overflow-y`, so
an opt-in class that overrides the global hover-only rule counts as marked.

Usage:  py scripts/kova\scroll_cue.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTES = [
    ("chat", "/#/20260927_231116_3cfc71"),
    ("capabilities", "/#/capabilities"),
    ("artifacts", "/#/artifacts"),
    ("messaging", "/#/messaging"),
    ("settings", "/#/settings"),
    ("cron", "/#/cron"),
]

# Containers that scroll a DOCUMENT (the transcript) are gestures - you drag
# them - and the hover-only scrollbar is correct there. Only navigation and
# facet columns are in scope.
SKIP = ("transcript", "message-stream", "log-tail")

PROBE = r"""JSON.stringify((()=>{
  const SKIP = ["transcript", "message-stream", "log-tail"];
  const out = [];

  // Every rule that paints a thumb, so we can ask which one applies here.
  const thumbRules = [];
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch { continue; }
    const walk = list => {
      for (const rule of list) {
        if (rule.cssRules && rule.selectorText === undefined) { walk(rule.cssRules); continue; }
        if (!rule.selectorText || !/scrollbar-thumb/.test(rule.selectorText)) continue;
        const colour = rule.style.backgroundColor || rule.style.background || '';
        // A hover-scoped rule only marks the container while hovered.
        const hoverOnly = /:hover/.test(rule.selectorText);
        // A bare `::-webkit-scrollbar-thumb` has no selector, so the stripped
        // base is "". el.matches("") THROWS, and an exception inside this
        // expression surfaces as "no value" - which read as "nothing clipping"
        // on every route. Record the universal selector explicitly instead.
        const base = rule.selectorText.replace(/:hover.*$/, '').replace(/::.*$/, '') || '*';
        thumbRules.push({ base, colour, hoverOnly });
      }
    };
    walk(rules);
  }

  for (const el of document.querySelectorAll('body, body *')) {
    const cs = getComputedStyle(el);
    if (!/auto|scroll/.test(cs.overflowY)) continue;
    const clipped = el.scrollHeight - el.clientHeight;
    if (clipped <= 8) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 120 || r.height < 120) continue;
    if (r.bottom < 0 || r.top > innerHeight) continue;

    const cls = (el.className || '').toString();
    if (SKIP.some(s => cls.includes(s))) continue;

    // Does a NON-hover thumb rule paint for this element?
    let marked = false;
    for (const rule of thumbRules) {
      if (rule.hoverOnly) continue;
      if (/transparent|rgba\(0,\s*0,\s*0,\s*0\)/.test(rule.colour)) continue;
      try {
        if (el.matches(rule.base)) {
          marked = true;
          break;
        }
      } catch { /* a selector we cannot test - treat as unmatched */ }
    }

    out.push({
      clipped,
      boxH: Math.round(r.height),
      contentH: el.scrollHeight,
      marked,
      cls: cls.slice(0, 70)
    });
  }
  return out;
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def main():
    bad = []
    print("  %-14s %8s %8s %8s  %s" % ("route", "clipped", "box", "content", "marked"))
    for name, route in ROUTES:
        ev("location.hash=" + repr(route[1:]))
        time.sleep(2.5)
        raw = ev(PROBE)
        if not raw:
            # A probe that throws is NOT a route with nothing clipping. Say so
            # rather than printing a pass.
            print("  %-14s PROBE FAILED (threw or returned nothing)" % name)
            bad.append("%s: the scroll-cue probe did not run" % name)
            continue
        rows = json.loads(raw)
        if not rows:
            print("  %-14s %8s %8s %8s  (nothing clipping)" % (name, "-", "-", "-"))
            continue
        for r in rows:
            print("  %-14s %8d %8d %8d  %s" % (
                name, r["clipped"], r["boxH"], r["contentH"], "yes" if r["marked"] else "NO"))
            if not r["marked"]:
                bad.append("%s: %dpx clipped in a %dpx box with no visible scrollbar (%s)"
                           % (name, r["clipped"], r["boxH"], r["cls"][:44]))

    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        print()
        print("  These read as shorter lists than they are. Either cap the")
        print("  content, or mark the scroll - see .scrollbar-cue in styles.css.")
        return 1
    print("  every clipping container paints a scrollbar without hover")
    return 0


if __name__ == "__main__":
    sys.exit(main())
