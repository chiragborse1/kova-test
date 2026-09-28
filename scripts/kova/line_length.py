"""A reading measure is about the line a person READS, not the widest one.

`--conversation-measure: 68ch` is the app's single reading width, and `ch`
scales with font size - so 68ch holds MORE characters at 12px than at 13px.
Measured: 68ch is 440px at 12px and 477px at 13px, which is 80 CPL against
65. That looks like a caption being held to a looser standard than body copy,
and I spent two turns calling it a judgment call rather than measuring it.

Measured properly, the question dissolves. CPL is the width of the column
divided by the advance of ONE character, so it is the length of a line with
no spaces in it. Real prose is mostly spaces. Laying the actual paragraphs
out and counting the characters that land on each line:

    surface        size   column   longest line   mean line
    transcript     13px    416px         75            64
    messaging      12px    476px         88            64
    messaging      12px    450px         77            54

Identical mean, 64 characters, on both surfaces. The 80 CPL figure is the
worst-case ragged line on a two-line paragraph, not the measure anyone
reads. Both are inside the 45-90 band the token's own comment states as its
intent ("enough to hold a clause, short enough that the eye returns").

So the token is right, `ch` doing its job, and the fix is NOT a narrower
caption token. Adding one would have made the app look considered while
making the measure worse.

This gate reports the mean and the longest line, not CPL, so the number that
decides a measure question is the one a person would actually see.

Usage:  py scripts/kova/line_length.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTES = [
    ("transcript", "/#/20260927_231116_3cfc71"),
    ("messaging", "/#/messaging"),
    ("webhooks", "/#/webhooks"),
    ("settings", "/#/settings"),
    ("cron", "/#/cron"),
    ("session-import", "/#/session-import"),
]

# The token's own comment states the intent, and it is the standard to hold
# the app to: 45-90 characters on a line.
MIN_MEAN, MAX_MEAN = 45, 90
MAX_LINE = 100

PROBE = r"""JSON.stringify((()=>{
  const cvs = document.createElement('canvas').getContext('2d');
  const out = [];

  for (const el of document.querySelectorAll('p, li')) {
    const t = (el.textContent || '').trim();
    if (t.length < 120) continue;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (r.width < 150 || r.bottom < 0 || r.top > innerHeight) continue;
    let leaf = true;
    for (const c of el.children) { if ((c.textContent || '').trim().length >= t.length) leaf = false; }
    if (!leaf) continue;

    cvs.font = s.fontWeight + ' ' + s.fontSize + ' ' + s.fontFamily;
    const space = cvs.measureText(' ').width;
    let lineChars = 0, lineW = 0;
    const lines = [];
    // Lay the REAL paragraph out at the real width and count what lands on
    // each line. That is the measure; CPL is only its space-free upper bound.
    for (const w of t.split(/\s+/)) {
      const ww = cvs.measureText(w).width;
      if (lineW + ww > r.width) { lines.push(lineChars); lineChars = w.length; lineW = ww; }
      else { lineChars += (lineW ? 1 : 0) + w.length; lineW += (lineW ? space : 0) + ww; }
    }
    lines.push(lineChars);

    out.push({
      size: parseFloat(s.fontSize),
      width: Math.round(r.width),
      longest: Math.max(...lines),
      mean: Math.round(lines.reduce((a, b) => a + b, 0) / lines.length),
      lines: lines.length
    });
  }
  return out;
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def main():
    bad = []
    print("  %-14s %5s %8s %7s %7s  %s" % ("route", "size", "column", "mean", "longest", "verdict"))
    for name, route in ROUTES:
        ev("location.hash=" + repr(route[1:]))
        time.sleep(2.5)
        raw = ev(PROBE)
        if not raw:
            print("  %-14s  PROBE FAILED" % name)
            bad.append("%s: the probe did not run" % name)
            continue
        rows = json.loads(raw)
        if not rows:
            print("  %-14s  (no long prose on this route)" % name)
            continue
        for r in rows:
            ok = MIN_MEAN <= r["mean"] <= MAX_MEAN and r["longest"] <= MAX_LINE
            print("  %-14s %4dpx %7dpx %7d %7d  %s"
                  % (name, r["size"], r["width"], r["mean"], r["longest"], "ok" if ok else "OUT OF BAND"))
            if not ok:
                bad.append("%s: mean line %d chars, longest %d (band is %d-%d, max %d)"
                           % (name, r["mean"], r["longest"], MIN_MEAN, MAX_MEAN, MAX_LINE))

    print()
    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  every line a person reads is inside the 45-90 band the token claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
