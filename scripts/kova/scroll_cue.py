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

IT ALSO CHECKS THE THUMB IS VISIBLE, because "marked" turned out to be the
wrong question on its own. The cue existed and had a rule and painted at
1.30:1 - with 80% of a list hidden behind it. A rule existing is a claim about
markup; the cue exists to be SEEN. So the probe now resolves the colour the
browser composites for the thumb and scores it against the surface behind it,
failing under 3:1 (WCAG 1.4.11 non-text contrast; a scrollbar is a control
boundary, not text).

The maths runs in-page on purpose. Three earlier measurement scripts in this
project read a colour string in Python and produced confident nonsense - once
by treating oklch() 0..1 components as 0..255, once by falling through to a
hardcoded white on a transparent body. The browser has already resolved the
color-mix(); there is no reason to re-parse it.

Usage:  py scripts/kova\scroll_cue.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

import app_alive  # noqa: E402

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

    // 'marked' only proves a RULE exists. It said yes for a thumb painted at
    // 1.30:1 - a scrollbar nobody can see, which is the exact defect this gate
    // was written to prevent. So resolve the colour the browser actually paints
    // and score it. getComputedStyle(el, '::-webkit-scrollbar-thumb') returns
    // the composited color-mix() value with its alpha; the contrast maths runs
    // in-page so no Python here has to re-parse a colour string - which is how
    // three earlier probes in this project produced confident nonsense.
    const cv = document.createElement('canvas'); cv.width = cv.height = 1;
    const cx = cv.getContext('2d', { willReadFrequently: true });
    const norm = (c) => {
      if (!c) return null;
      cx.clearRect(0, 0, 1, 1); cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
      try { const d = cx.getImageData(0, 0, 1, 1).data;
            return { r: d[0], g: d[1], b: d[2], a: d[3] / 255 }; } catch { return null; }
    };
    const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const lum = (c) => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
    const over = (f, b) => ({ r: f.a * f.r + (1 - f.a) * b.r,
                              g: f.a * f.g + (1 - f.a) * b.g,
                              b: f.a * f.b + (1 - f.a) * b.b });
    const ratio = (a, b) => { const la = lum(a), lb = lum(b);
      return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };

    const thumb = norm(getComputedStyle(el, '::-webkit-scrollbar-thumb').backgroundColor);
    let contrast = null;
    if (thumb && thumb.a >= 0.05) {
      let surf = null, n = el;
      while (n) { const c = norm(getComputedStyle(n).backgroundColor);
                  if (c && c.a > 0.9) { surf = c; break; } n = n.parentElement; }
      if (!surf) surf = document.documentElement.classList.contains('dark')
        ? { r: 13, g: 13, b: 14, a: 1 } : { r: 255, g: 255, b: 255, a: 1 };
      contrast = Math.round(ratio(over(thumb, surf), surf) * 100) / 100;
    }

    // Stamp the node so the scroll-diff pass can address the SAME element
    // rather than re-querying by class and hoping the order matches.
    el.setAttribute('data-cue-probe', String(out.length));

    out.push({
      clipped,
      boxH: Math.round(r.height),
      contentH: el.scrollHeight,
      marked,
      contrast,
      cls: cls.slice(0, 70)
    });
  }
  return out;
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None



# ── Is a thumb actually PAINTED? ────────────────────────────────────────────
# Declared colour and painted thumb are different claims, and only one of them
# is what a person sees. The capabilities filter rail declares a 55% thumb,
# reserves the same 7px classic gutter as the card list beside it, computes the
# same colour - and paints NOTHING. It scrolls 285px. Reading the computed style
# cannot tell those apart, which is why this gate stayed green over a
# scrollbar nobody could see.
#
# The test that does distinguish them: hide the content, photograph the gutter,
# scroll, photograph it again. A painted thumb MUST move. Rows behind it must
# not, which is why the content is hidden first - otherwise the histogram diff
# is dominated by the list scrolling past.
#
# This is a screenshot diff on purpose. An earlier attempt used
# elementFromPoint and computed styles inside the page, which is the same class
# of claim that already lied: it reports what the cascade says, not what is on
# the screen.
GUTTER_BAND = 10


def _gutter_pixels(img, box, dpr):
    from PIL import Image  # noqa: F401  (documents the dependency of fresh_shot)
    import pixel_measure as PM
    right = int((box["x"] + box["w"]) * dpr)
    top = int(box["y"] * dpr)
    bottom = min(img.height, int((box["y"] + box["h"]) * dpr))
    if right <= 0 or bottom <= top:
        return None
    x0 = max(0, right - int(GUTTER_BAND * dpr))
    return img.crop((x0, top, right, bottom))


def paint_check(index, route_hash):
    """True when the element's gutter changes when it scrolls."""
    import pixel_measure as PM
    try:
        ev("location.hash=" + repr(route_hash))
        time.sleep(2.0)
        # Do NOT hide the content. Hiding it collapses the scroller -
        # scrollHeight falls to clientHeight, scrollTop cannot move, and the
        # diff is zero for every element including ones with a working thumb.
        # That is how the first version of this check condemned the card list
        # alongside the rail.
        ev("""(()=>{const el=document.querySelector('[data-cue-probe="%s"]');
          if(!el) return 0;
          window.scrollTo(0,0);
          el.scrollTop = 0;
          return 1;})()""" % index)
        time.sleep(0.4)
        img, _ = PM.fresh_shot()
        box = _box_of(index)
        if box is None:
            return None
        before = _gutter_pixels(img, box, PM.viewport()["dpr"])
        ev("""(()=>{const el=document.querySelector('[data-cue-probe="%s"]');
          if(!el) return; el.scrollTop = Math.min(140, el.scrollHeight - el.clientHeight);})()""" % index)
        time.sleep(1.2)
        img2, _ = PM.fresh_shot()
        after = _gutter_pixels(img2, box, PM.viewport()["dpr"])
        ev("""(()=>{const el=document.querySelector('[data-cue-probe="%s"]');
          if(!el) return; el.scrollTop = 0;})()""" % index)
        time.sleep(0.6)
        if before is None or after is None:
            return None
        a = before.tobytes()
        b = after.tobytes()
        if len(a) != len(b):
            return True
        # A painted thumb is a solid bar that moves with the track, so the
        # reserved strip changes substantially. Measured on this app: a working
        # thumb changes ~4800 bytes, a non-painted one changes 0.
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff > 500
    except Exception:
        return None


def _box_of(index):
    raw = ev("""(()=>{const el=document.querySelector('[data-cue-probe="%s"]');
      if(!el) return null; const r=el.getBoundingClientRect();
      return JSON.stringify({x:r.x,y:r.y,w:r.width,h:r.height});})()""" % index)
    try:
        return json.loads(raw) if raw else None
    except (TypeError, ValueError):
        return None

def main():
    # A gate that measures a crashed renderer measures nothing. Proven: with the
    # error boundary on screen this gate exited 0 claiming every container
    # painted a scrollbar. Fail loudly instead.
    try:
        app_alive.alive()
    except RuntimeError as exc:
        print("  %s" % exc)
        return 1

    bad = []
    # WCAG 1.4.11 non-text contrast. A thumb is a control boundary, so 3:1 -
    # not the 4.5:1 that text needs. This is the number the ORIGINAL gate could
    # not produce: it asked whether a rule existed, and a 1.30:1 thumb has a rule.
    MIN_CONTRAST = 3.0
    print("  %-14s %8s %8s %8s  %6s  %8s  %7s  %s"
          % ("route", "clipped", "box", "content", "marked", "contrast", "painted",
             "verdict"))
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
        for idx, r in enumerate(rows):
            contrast = r.get("contrast")
            # The decisive check. A declared thumb is a claim about the cascade;
            # a painted one is a claim about the screen. The capabilities rail
            # declares 55% and paints nothing, so it is asked to prove it.
            painted = paint_check(idx, route[1:])
            r["painted"] = painted
            if painted is False:
                verdict = "NOT PAINTED (declares a thumb, draws none)"
            elif contrast is None:
                verdict = "FAINT (no thumb painted at rest)"
            elif contrast < MIN_CONTRAST:
                verdict = "FAINT %.2f:1 < %.1f" % (contrast, MIN_CONTRAST)
            else:
                verdict = "ok %.2f:1" % contrast
            print("  %-14s %8d %8d %8d  %6s  %8s  %7s  %s" % (
                name, r["clipped"], r["boxH"], r["contentH"],
                "yes" if r["marked"] else "NO",
                "-" if contrast is None else "%.2f" % contrast,
                "?" if painted is None else ("yes" if painted else "NO"),
                verdict))
            if not r["marked"]:
                bad.append("%s: %dpx clipped in a %dpx box with no visible scrollbar (%s)"
                           % (name, r["clipped"], r["boxH"], r["cls"][:44]))
            elif contrast is None:
                bad.append("%s: %dpx clipped but no thumb is painted at rest - a "
                           "scrollbar nobody can see (%s)"
                           % (name, r["clipped"], r["cls"][:44]))
            elif contrast < MIN_CONTRAST:
                bad.append("%s: the scroll cue is painted at %.2f:1, under the "
                           "%.1f:1 a control boundary needs. The thumb is there and "
                           "still invisible (%s)"
                           % (name, contrast, MIN_CONTRAST, r["cls"][:44]))
            if painted is False:
                bad.append("%s: %dpx clipped and the element DECLARES a scrollbar "
                           "thumb, but scrolling it changes nothing in the gutter - "
                           "no thumb is painted, so the cue does not exist (%s)"
                           % (name, r["clipped"], r["cls"][:44]))

    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        print()
        print("  These read as shorter lists than they are. Either cap the")
        print("  content, mark the scroll, or make the thumb VISIBLE - a bar at")
        print("  1.3:1 is the same as no bar. See .scrollbar-cue in styles.css.")
        return 1
    print("  every clipping container paints a scrollbar without hover, at a")
    print("  contrast a person can actually see")
    return 0


if __name__ == "__main__":
    sys.exit(main())
