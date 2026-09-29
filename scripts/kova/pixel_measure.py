"""Measure painted contrast from real pixels, with the failure modes named.

Four bugs produced confident, wrong numbers while measuring this by hand, and
every one of them is a trap a re-measurement will fall into again:

1. A STALE FRAME. `Page.captureScreenshot` can return the previous frame: the
   hash updates, the DOM updates, and two captures in a row come back
   BYTE-IDENTICAL. Every reading taken from such a frame is of a page that is no
   longer on screen. `fresh_shot()` forces a compositor frame at the REAL
   viewport size and returns the bytes so a caller can prove they are new.

2. A VIEWPORT MISMATCH. Forcing `1410x942` when the window is `1422x957` offsets
   every crop by (12, 15). Read `innerWidth/innerHeight` and force THOSE.

3. A STALE BOX. The DOM boxes read before a capture can describe a different
   layout than the frame. `boxes_for()` re-reads them after and returns None if
   they moved, so the caller cannot silently measure the wrong rectangle.

4. AN OVERLAY. A covered element measures whatever is painted on top of it, and
   the number is indistinguishable from a real regression - a dropdown left open
   over two rail headings reported 1.48:1 and 2.66:1, which read exactly like the
   bug this file exists to check. `covered()` is the check, and a reading taken
   on a covered element is not a reading at all.

The last one nearly caused an already-fixed bug to be re-reported as a
regression, so the checks are not optional garnish: each exists because it
caught something.

Usage:
    py scripts/kova/pixel_measure.py            -> self-test on this route
    from pixel_measure import fresh_shot, contrast_of
"""
import base64
import io
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402


def _ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    v = r["result"]["result"].get("value") if r else None
    for _ in range(4):          # the CDP bridge double-encodes JSON
        if not isinstance(v, str):
            return v
        try:
            v = json.loads(v)
        except (TypeError, ValueError):
            return v
    return v


def viewport():
    d = _ev("JSON.stringify({w: innerWidth, h: innerHeight, dpr: devicePixelRatio})")
    if not isinstance(d, dict):
        raise RuntimeError("could not read the viewport")
    return d


def fresh_shot(settle=1.5):
    """Capture a frame the compositor has actually drawn.

    A DOM nudge (opacity flip + forced reflow) does NOT do it - the capture came
    back byte-identical. Resizing the viewport does. Returns (PIL image, png
    bytes) so a caller can hash the bytes and prove two captures differ.
    """
    from PIL import Image

    vp = viewport()
    U.call("Emulation.setDeviceMetricsOverride",
           {"width": vp["w"], "height": vp["h"], "deviceScaleFactor": 1, "mobile": False})
    time.sleep(settle)
    try:
        r = U.call("Page.captureScreenshot", {"format": "png"})
        raw = base64.b64decode(r["result"]["data"])
    finally:
        U.call("Emulation.clearDeviceMetricsOverride")
    return Image.open(io.BytesIO(raw)).convert("RGB"), raw


def boxes_for(selector, key=lambda e: (e.textContent or "").strip()):
    """Read element boxes, and re-read them to prove they did not move.

    Returns the boxes, or None if the layout shifted under the read - in which
    case any measurement taken from the capture would be of the wrong rectangle.
    """
    js = """JSON.stringify([...document.querySelectorAll(%s)].map(e => {
      const r = e.getBoundingClientRect();
      return {t: (e.textContent || '').trim(), x: r.x, y: r.y, w: r.width, h: r.height};
    }))""" % json.dumps(selector)
    before = _ev(js)
    fresh_shot()
    after = _ev(js)
    if before != after:
        return None
    return before or []


def covered(selector, index):
    """Why this element cannot be measured, or None when it can.

    An element under an overlay still computes a colour, and that colour is the
    OVERLAY's - which is how a dropdown left open over two rail headings read as
    1.48:1 and 2.66:1, indistinguishable from a real regression.

    The test is whether the element is the topmost thing at its own centre, not
    a search for role attributes: the real offender was a menu wrapper carrying
    no role I was checking for, and a synthetic overlay carries none at all.
    Asking "is this the top of the stack here" cannot miss.

    Resolves the element IN-PAGE by index so identity is compared directly
    rather than reconstructed from coordinates. Returns a STRING reason rather
    than a bare False, so a caller who forgets to check still gets something
    truthy - and an exception inside the page is itself a reason, never a
    silent pass. The first version of this function did exactly that: a
    non-finite rect made elementFromPoint throw, the error came back as an
    object, and every box read as fine.
    """
    js = """(()=>{try{
      const el = document.querySelectorAll(%s)[%d];
      if (!el) return 'element-gone';
      const b = el.getBoundingClientRect();
      if (!isFinite(b.x) || !isFinite(b.y) || !isFinite(b.width) || !isFinite(b.height))
        return 'non-finite-box';
      if (b.width <= 0 || b.height <= 0) return 'zero-size';
      if (b.bottom < 0 || b.top > innerHeight) return 'off-screen';
      const x = Math.min(innerWidth - 1, Math.max(0, b.x + b.width / 2));
      const y = Math.min(innerHeight - 1, Math.max(0, b.y + b.height / 2));
      const top = document.elementFromPoint(x, y);
      if (!top) return 'nothing-at-point';
      if (top === el || el.contains(top) || top.contains(el)) return 'ok';
      return 'covered-by-' + top.tagName.toLowerCase();
    } catch (e) { return 'probe-threw'; }})()""" % (json.dumps(selector), index)
    reason = _ev(js)
    if reason == "ok":
        return None
    return reason if isinstance(reason, str) else "probe-failed"


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _lum(p):
    return 0.2126 * _lin(p[0]) + 0.7152 * _lin(p[1]) + 0.0722 * _lin(p[2])


def ratio(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def contrast_of(img, box, dpr):
    """Contrast between the text and the surface inside one box.

    No vertical inset: a previous version inset by 8px and clipped the
    ascenders, which made a legible heading report no glyph at all.

    Anti-aliased edge pixels are included, which is the correct reading - the
    alternative is to be sensitive to whichever single stray pixel happens to
    land in the crop. A row that measures 3.86 on a stray pixel and 6.89 on its
    core colour is a row at 6.89.
    """
    x0, y0 = int(box["x"] * dpr), int(box["y"] * dpr)
    x1 = min(img.width, int((box["x"] + box["w"]) * dpr))
    y1 = min(img.height, int((box["y"] + box["h"]) * dpr))
    if x1 <= x0 or y1 <= y0:
        return None
    px = list(img.crop((x0, y0, x1, y1)).getdata())
    surface = Counter(px).most_common(1)[0][0]
    rest = [p for p in px
            if abs(p[0] - surface[0]) + abs(p[1] - surface[1]) + abs(p[2] - surface[2]) > 10]
    if not rest:
        return None
    glyph = max(Counter(rest).most_common(10), key=lambda kv: ratio(kv[0], surface))[0]
    return round(ratio(glyph, surface), 2)


def measure(selector, need=4.5, key=None):
    """Measure every matching element. Refuses to return a number it cannot
    defend: a covered box or a moved layout returns None rather than a reading.
    """
    boxes = boxes_for(selector)
    if boxes is None:
        return {"error": "layout moved between the box read and the capture"}
    img, _ = fresh_shot()
    dpr = viewport()["dpr"]
    out = []
    for i, b in enumerate(boxes):
        why = covered(selector, i)
        r = None if why else contrast_of(img, b, dpr)
        out.append({"t": b["t"], "contrast": r, "covered": why,
                    "pass": None if r is None else r >= need})
    return {"rows": out, "need": need}


if __name__ == "__main__":
    res = measure("[data-nav-group-label]")
    if "error" in res:
        print("  %s" % res["error"])
        sys.exit(1)
    for r in res["rows"]:
        state = "covered by %s" % r["covered"] if r["covered"] else (
            "%.2f %s" % (r["contrast"], "ok" if r["pass"] else "FAIL")
            if r["contrast"] is not None else "no glyph")
        print("  %-24s %s" % (r["t"][:24], state))


def scrollbar_thumb(img, box, dpr, surface=None, band=10):
    """Contrast of the painted scrollbar thumb in a scroller's gutter.

    Sampled by SCANNING the gutter outward from the element's right edge and
    keeping the strongest reading, not by cropping a guessed width. Two earlier
    attempts guessed 14px and got it wrong twice: the real gutter is
    `offsetWidth - clientWidth` (7px here), so a 14px crop was half list content
    and the content's colours won the modal-colour vote - reporting 1.1:1 for a
    thumb the frame plainly shows.

    The scan makes the number independent of exactly where the thumb sits
    inside the reserved band, which is the thing being guessed at.
    """
    right = int((box["x"] + box["w"]) * dpr)
    top = int(box["y"] * dpr)
    bottom = min(img.height, int((box["y"] + box["h"]) * dpr))
    if right <= 0 or bottom <= top:
        return None
    if surface is None:
        # The surface is the dominant colour of the first column in, which is
        # the list's own background rather than whatever the crop happens to hit.
        col = list(img.crop((right - int(2 * dpr), top, right, bottom)).getdata())
        surface = Counter(col).most_common(1)[0][0]
    best = 0.0
    glyph = None
    for off in range(0, band + 2):
        gx1 = right - int(off * dpr)
        gx0 = gx1 - max(1, int(dpr))
        if gx0 < 0:
            break
        col = list(img.crop((gx0, top, gx1, bottom)).getdata())
        rest = [p for p in col
                if abs(p[0] - surface[0]) + abs(p[1] - surface[1]) + abs(p[2] - surface[2]) > 12]
        if not rest:
            continue
        th = max(Counter(rest).most_common(5), key=lambda kv: ratio(kv[0], surface))[0]
        r = ratio(th, surface)
        if r > best:
            best, glyph = r, th
    return {"contrast": round(best, 2), "glyph": glyph, "surface": surface}
