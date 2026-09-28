"""A filter rail that needs scrolling has to admit it.

The capabilities facet rail is `overflow-y-auto`, so nothing is strictly
unreachable - you can scroll to it. But measured on the running app it holds
**1492px of content in a 783px box**: 709px clipped, and the entire Tags
section starts at y=1119, past the 906px fold. A rail whose third section
begins 200px below the window, in a column with no visible scrollbar, reads
as a list that ends at "Web" - and the tags below it are simply not there as
far as anyone can tell.

That is the defect: not "content is clipped" but "the rail does not look like
it continues". A person cannot filter by tag if they cannot tell tags exist.

Compare the two precedents already in the same file:
  - `catalogTags` limits its long tail (`limit`, plus anything selected), and
    its comment says the search covers the rest.
  - `catalogCategories` has no limit at all - it renders every category, and
    on this catalog that is 30 rows, the last 8 of them at y=915+.

So the fix is not "make it scroll nicer". It is the one the tags facet
already made: show the rows that matter, keep the rest reachable through the
search that is already in the toolbar, and never let a section begin below
the fold without the rail looking scrollable.

Reports, per route:
  railH    the scroll box height
  contentH how much content it holds
  clipped  how many px are past the fold
  sections how many start below the fold

Usage:  py scripts/kova/facet_rail.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

ROUTE = "#/capabilities"

PROBE = r"""JSON.stringify((()=>{
  const catRow = [...document.querySelectorAll('button')]
    .find(b => /^Creative/.test((b.textContent || '').trim()));
  if (!catRow) return { found: false };

  let scroller = null;
  for (let e = catRow.parentElement; e; e = e.parentElement) {
    if (/auto|scroll/.test(getComputedStyle(e).overflowY)) { scroller = e; break; }
  }
  if (!scroller) return { found: false, reason: 'no scroll container' };

  const box = scroller.getBoundingClientRect();
  const fold = window.innerHeight;

  // Section dividers, and whether each begins past the fold.
  const sections = [];
  for (const el of scroller.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.textTransform !== 'uppercase') continue;
    const t = (el.textContent || '').trim();
    if (!t || t.length > 20) continue;
    sections.push({ label: t, y: Math.round(el.getBoundingClientRect().top) });
  }

  // Does anything LOOK scrollable? Checking `overflow-y: scroll` is not the
  // test: this app hides every scrollbar until hover, so a rail can be
  // scrollable and still read as ending at its last visible row. What matters
  // is whether a thumb is actually painted, which is what the caller sees.
  const thumbRule = [...document.styleSheets]
    .flatMap(sheet => { try { return [...sheet.cssRules]; } catch { return []; } })
    .flatMap(rule => (rule.cssRules ? [...rule.cssRules] : [rule]))
    .filter(rule => rule.selectorText && /scrollbar-thumb/.test(rule.selectorText))
    .find(rule => {
      try { return scroller.matches(rule.selectorText.replace(/::.*/, '')); } catch { return false; }
    });
  const thumbColour = thumbRule ? thumbRule.style.backgroundColor || thumbRule.style.background : '';
  const scrollbarVisible =
    scroller.offsetWidth - scroller.clientWidth > 0 &&
    Boolean(thumbColour) &&
    !/transparent|rgba\(0, 0, 0, 0\)/.test(thumbColour);

  return {
    found: true,
    railH: scroller.clientHeight,
    contentH: scroller.scrollHeight,
    clipped: Math.max(0, scroller.scrollHeight - scroller.clientHeight),
    fold,
    sections,
    belowFold: sections.filter(s => s.y > fold).length,
    scrollbarVisible
  };
})())"""


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


def main():
    ev("location.hash=" + repr(ROUTE[1:]))
    time.sleep(4)
    raw = ev(PROBE)
    if not raw:
        print("  no value - is the app running with CDP on 9222?")
        return 1

    d = json.loads(raw)
    if not d.get("found"):
        print("  the facet rail did not render (%s)" % d.get("reason", "not found"))
        return 1

    print("  rail box      %dpx" % d["railH"])
    print("  content       %dpx" % d["contentH"])
    print("  clipped       %dpx  (%.0f%% of the content is past the fold)"
          % (d["clipped"], 100.0 * d["clipped"] / max(1, d["contentH"])))
    print("  window fold   %dpx" % d["fold"])
    print("  scrollbar visible: %s" % d["scrollbarVisible"])
    print()
    for s in d["sections"]:
        flag = "BELOW FOLD" if s["y"] > d["fold"] else ""
        print("    %-16s y=%-6d %s" % (s["label"], s["y"], flag))

    print()
    bad = []
    if d["belowFold"]:
        bad.append("%d section(s) start below the fold" % d["belowFold"])
    if d["clipped"] > d["railH"] * 0.25 and not d["scrollbarVisible"]:
        bad.append(
            "%dpx clipped in a %dpx rail with no visible scrollbar - it reads as ending early"
            % (d["clipped"], d["railH"])
        )

    if bad:
        for b in bad:
            print("  ATTENTION  " + b)
        return 1
    print("  the rail fits, or admits that it scrolls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
