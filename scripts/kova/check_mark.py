#!/usr/bin/env python3
"""Verify the Kova mark without an SVG rasteriser's help.

There is no SVG rasteriser guaranteed on the build machine, so the mark is
checked structurally and numerically instead:

  * the SVGs parse as XML
  * the silhouette variants are a SINGLE self-closing <path>, because
    scripts/generate_icons.py lifts art out with
    re.search(r"<path\\b.*?/>") and a multi-element mark silently loses
    everything after the first shape
  * the silhouette uses fill-rule="evenodd", because the screen and the eyes
    are holes rather than additions
  * regenerating from the source artwork is byte-identical, so the committed
    SVG cannot drift from assets/kova/source/kova-logo.png
  * the traced rings actually enclose area (a degenerate walk that returns a
    sliver would still parse and still pass a size check)

Usage:  python scripts/kova/check_mark.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location(
    "mm", pathlib.Path(__file__).with_name("make_mark.py")
)
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

SVG = "{http://www.w3.org/2000/svg}"
fail = False


def check(condition: bool, message: str) -> None:
    global fail
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        fail = True


for variant, fill in (("black", "#000000"), ("white", "#ffffff")):
    path = pathlib.Path(f"assets/kova/kova-mark-{variant}.svg")
    print(path.name)
    raw = path.read_text(encoding="utf-8-sig")
    root = ET.fromstring(raw)                      # raises if malformed
    paths = root.findall(f"{SVG}path")
    print(f"  {len(paths)} path element(s)")
    check(len(paths) == 1,
          "the glyph is a single path element; generate_icons.py extracts only the first one")
    if len(paths) != 1:
        continue
    el = paths[0]
    check(el.get("fill") == fill, f"fill is {fill}")
    check(el.get("fill-rule") == "evenodd",
          "fill-rule is evenodd (the screen and eyes are holes)")
    d = el.get("d", "")
    subs = d.count("M ")
    # 3 outers (head, ear, antenna) + 3 holes (screen, two eyes). The eyes are
    # holes rather than additions so the mono mark keeps the artwork's own
    # reading: a face-shaped silhouette, not a solid blob.
    check(subs == 6, f"6 subpaths: 3 outers + 3 holes (got {subs})")
    check(d.rstrip().endswith("Z"), "every subpath is closed")
    check(len(d) > 4000, f"the traced outline is non-trivial ({len(d)} chars)")

    # A degenerate walk returns a sliver; require real enclosed area.
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", d)]
    xs, ys = nums[0::2], nums[1::2]
    area = 0.0
    for i in range(len(xs)):
        j = (i + 1) % len(xs)
        area += xs[i] * ys[j] - xs[j] * ys[i]
    check(abs(area) / 2 > 200_000,
          f"enclosed area is real ({abs(area) / 2:.0f} square units)")
    check(max(xs) <= 1024 and min(xs) >= 0, "the mark fits its 1024 viewBox")

colour = pathlib.Path("assets/kova/kova-mark-color.svg")
print(colour.name)
root = ET.fromstring(colour.read_text(encoding="utf-8-sig"))
parts = root.findall(f"{SVG}path")
# head(outer+screen hole), 2 blue, screen(outer + 2 eye holes), 2 green
check(len(parts) == 9, f"9 coloured parts, one per traced ring (got {len(parts)})")
fills = {p.get("fill") for p in parts}
check(fills == {mm.COLORS[n] for n in ("head", "blue", "screen", "green")},
      f"only brand colours are used: {sorted(fills)}")

# Drift guard: the committed SVG must be exactly what the generator produces.
print("regeneration")
parts_built = mm.build()
for name, expected in (
    ("kova-mark-black.svg", mm.silhouette_svg(parts_built, 1024, "#000000")),
    ("kova-mark-white.svg", mm.silhouette_svg(parts_built, 1024, "#ffffff")),
    ("kova-mark-color.svg", mm.color_svg(parts_built, 1024)),
):
    actual = pathlib.Path("assets/kova") / name
    check(actual.read_text(encoding="utf-8-sig") == expected,
          f"{name} matches a fresh trace of the source artwork")

print("FAIL" if fail else "PASS")
sys.exit(1 if fail else 0)
