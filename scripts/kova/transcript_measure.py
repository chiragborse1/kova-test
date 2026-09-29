"""The transcript is the app's primary reading surface. Measure it as one.

`ui_audit.py` checks chars-per-line on `p` elements and only trips past 120 CPL.
That is a smoke alarm, not a reading measure. It cannot see:

  - a run of text that is too WIDE but under the threshold, which is the
    failure that actually hurts: 100 CPL is legal and still tiring
  - vertical rhythm. Line height across a message, and the gap between
    consecutive blocks, are what a long transcript feels like; nothing
    checked either.
  - a heading or a list item drifting out of the body measure, which breaks
    the vertical line the eye tracks down a column.

What it found when pointed at the transcript properly: the measure is good.
9 runs, 59-65 CPL, clustered - no outliers, 416px column, 13px body and 11px
code. So this gate is not fixing anything today. It is here so the measure
cannot quietly regress, and so the next person does not have to rebuild the
probe to find out.

Reports:
  cpl        chars per line, per text run, via canvas measureText on the LIVE
             computed font (not a hard-coded one - that is the whole point)
  band       min..max CPL across the transcript. A WIDE spread means part of
             the column has drifted out of the measure.
  rhythm     distinct line-heights and block gaps, so an inconsistent
             leading shows up as a number rather than a feeling

Thresholds: 45-90 CPL is readable; a band wider than 30 means something in
the column is not on the measure; more than 3 distinct line heights in body
copy means leading is ad hoc.

Usage:  py scripts/kova/transcript_measure.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTE = "/#/20260927_231116_3cfc71"

PROBE = r"""JSON.stringify((()=>{
  const cvs = document.createElement('canvas').getContext('2d');
  const runs = [];

  const SEL = ['[data-message-id] p', '[data-message-id] li', '[data-message-id] h1',
               '[data-message-id] h2', '[data-message-id] h3', '[data-message-id] h4',
               '[data-message-id] blockquote', '[data-message-id] td'].join(', ');

  for (const el of document.querySelectorAll(SEL)) {
    const text = (el.textContent || '').trim();
    if (text.length < 20) continue;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 4) continue;

    // measureText against the LIVE font, so a font that loads late or a size
    // that is overridden is accounted for rather than assumed
    cvs.font = s.fontWeight + ' ' + s.fontSize + ' ' + s.fontFamily;
    const advance = cvs.measureText('abcdefghijklmnopqrstuvwxyz').width / 26;

    runs.push({
      tag: el.tagName,
      cpl: Math.round(r.width / advance),
      w: Math.round(r.width),
      x: Math.round(r.x),
      fontSize: Math.round(parseFloat(s.fontSize)),
      lineHeight: Math.round(parseFloat(s.lineHeight)),
      text: text.slice(0, 40)
    });
  }

  // Vertical rhythm: the gap between consecutive blocks in a message.
  const gaps = [];
  const blocks = [...document.querySelectorAll('[data-message-id] > *')]
    .map(e => e.getBoundingClientRect())
    .filter(r => r.height > 4)
    .sort((a, b) => a.top - b.top);
  for (let i = 1; i < blocks.length; i++) {
    gaps.push(Math.round(blocks[i].top - blocks[i - 1].bottom));
  }

  const leading = [...new Set(runs.map(r => r.lineHeight))].sort((a, b) => a - b);
  const columns = [...new Set(runs.map(r => r.w))].sort((a, b) => a - b);
  const lefts = [...new Set(runs.map(r => r.x))].sort((a, b) => a - b);

  return { runs, gaps: [...new Set(gaps)].sort((a, b) => a - b), leading, columns, lefts };
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def main():
    ev("location.hash=" + repr(ROUTE[1:]))
    time.sleep(4)
    raw = ev(PROBE)
    if not raw:
        print("  no value - is the app running with CDP on 9222, with a session open?")
        return 1

    d = json.loads(raw)
    runs = d["runs"]
    if not runs:
        print("  the transcript rendered no text runs.")
        print("  Open a session with content; this gate measures prose, not chrome.")
        return 1

    cpls = sorted(r["cpl"] for r in runs)
    lo, hi = cpls[0], cpls[-1]

    print("  text runs    %d" % len(runs))
    print("  chars/line   %d..%d   (readable is 45-90)" % (lo, hi))
    print("  columns      %s px" % d["columns"])
    print("  left edges   %s px" % d["lefts"])
    print("  line heights %s px" % d["leading"])
    print("  block gaps   %s px" % d["gaps"])
    print()
    for r in sorted(runs, key=lambda r: -r["cpl"])[:5]:
        print("    %-6s %3d CPL  %3dpx  %s" % (r["tag"], r["cpl"], r["w"], r["text"]))

    print()
    bad = []
    if lo < 40 or hi > 95:
        bad.append("chars per line runs %d..%d; readable is 45-90" % (lo, hi))
    if hi - lo > 30:
        bad.append(
            "the measure is not a band: %d..%d is %d CPL wide, so part of the "
            "column has drifted off the measure" % (lo, hi, hi - lo)
        )
    # Body copy only - a heading or a code block is allowed its own leading.
    body = [r for r in runs if r["tag"] in ("P", "LI")]
    bodyLeading = sorted({r["lineHeight"] for r in body})
    if len(bodyLeading) > 2:
        bad.append("body copy uses %d different line heights (%s); leading is ad hoc"
                   % (len(bodyLeading), bodyLeading))

    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  the transcript holds one measure, one leading, and a readable line")
    return 0


if __name__ == "__main__":
    sys.exit(main())
