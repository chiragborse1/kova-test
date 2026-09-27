#!/usr/bin/env python3
"""Verify the emitted Kova mark geometry without an SVG rasteriser.

There is no SVG rasteriser available on the build machine (cairosvg needs a
native cairo that is not installed), so the mark is validated numerically
instead: exactly one path element, four subpaths (three arms + the core),
and every arm endpoint sitting on the intended radius and angular offset.

Usage:  python scripts/kova/check_mark.py
"""
from __future__ import annotations

import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

import importlib.util

spec = importlib.util.spec_from_file_location("mm", pathlib.Path(__file__).with_name("make_mark.py"))
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

R_OUT, R_IN, ARC_HALF, CX, CY, CORE = mm.R_OUT, mm.R_IN, mm.ARC_HALF, mm.CX, mm.CY, mm.CORE_R
ARMS = mm.ARMS

fail = False
for variant in ("black", "white"):
    path = pathlib.Path(f"assets/kova/kova-mark-{variant}.svg")
    raw = path.read_text(encoding="utf-8")
    root = ET.fromstring(raw)                      # raises if malformed
    paths = root.findall("{http://www.w3.org/2000/svg}path")
    print(f"{path.name}: {len(paths)} path element(s)")

    if len(paths) != 1:
        print("  FAIL the glyph must be a single path element;"
              " generate_icons.py extracts only the first one")
        fail = True
        continue

    d = paths[0].get("d", "")
    subs = re.findall(r"M\s*([\d.]+ [\d.]+)\s*A.*?([\d.]+ [\d.]+)\s*L\s*([\d.]+ [\d.]+)\s*A.*?([\d.]+ [\d.]+)\s*Z", d)
    if len(subs) != ARMS:
        print(f"  FAIL expected {ARMS} arm subpaths, found {len(subs)}")
        fail = True
        continue

    for i, quad in enumerate(subs[:ARMS]):
        pts = [tuple(map(float, q.split())) for q in quad]
        mid = -90 + i * (360 / ARMS)
        for (x, y), wr, wo in ((pts[0], R_OUT, -ARC_HALF), (pts[1], R_OUT, +ARC_HALF),
                               (pts[2], R_IN, +ARC_HALF), (pts[3], R_IN, -ARC_HALF)):
            r = math.hypot(x - CX, y - CY)
            off = (math.degrees(math.atan2(y - CY, x - CX)) - mid + 540) % 360 - 180
            if abs(r - wr) > 0.6:
                print(f"  FAIL arm{i} ({x},{y}) radius {r:.1f} != {wr}"); fail = True
            if abs(off - wo) > 0.6:
                print(f"  FAIL arm{i} ({x},{y}) offset {off:.1f} != {wo}"); fail = True

    # The core is a full circle, drawn as two arcs, so it does not match the
    # arm pattern (M ... A ... L ... A ... Z). Pull it out on its own.
    core_m = re.search(
        r"M\s*([\d.]+ [\d.]+)\s*A\s*" + re.escape(f"{CORE}") + r"\s+" + re.escape(f"{CORE}") + r"\s+0 1 0",
        d,
    )
    if not core_m:
        print("  FAIL core circle subpath not found"); fail = True
    else:
        # A circle drawn as two arcs starts at its TOP point (centre - r on y),
        # not at the centre, so that is the coordinate to assert.
        cx, cy = map(float, core_m.group(1).split())
        want = (CX, CY - CORE)
        if (round(cx), round(cy)) != want:
            print(f"  FAIL core starts at ({cx},{cy}), want {want}"); fail = True
    print(f"  {ARMS} arms on r={R_OUT}/{R_IN}, core at centre r={CORE}")

print()
print("GEOMETRY OK" if not fail else "PROBLEMS FOUND")
sys.exit(1 if fail else 0)
