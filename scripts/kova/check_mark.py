"""Verify the emitted SVG geometry without an SVG rasteriser.

Checks each arm's path endpoints lie exactly on the intended radii/angles, so
a typo in the path string is caught here rather than surfacing as a malformed
icon in the app.
"""
import math, re, pathlib, sys

R_OUT, R_IN, HALF, CX, CY, CORE = 330, 250, 30, 512, 512, 118
fail = False

for variant in ("black", "white"):
    p = pathlib.Path(f"assets/kova/kova-mark-{variant}.svg")
    s = p.read_text(encoding="utf-8")
    paths = re.findall(r'<path d="M\s*([\d.]+ [\d.]+)\s*A[^A]*?([\d.]+ [\d.]+)\s*L\s*([\d.]+ [\d.]+)\s*A[^A]*?([\d.]+ [\d.]+)\s*Z"', s)
    print(f"{p.name}: {len(paths)} arms")
    if len(paths) != 3:
        print("  FAIL expected 3 arms"); fail = True; continue
    for i, quad in enumerate(paths):
        pts = [tuple(map(float, q.split())) for q in quad]
        mid = -90 + i * 120
        for (x, y), wr, wo in ((pts[0], R_OUT, -HALF), (pts[1], R_OUT, +HALF),
                               (pts[2], R_IN, +HALF), (pts[3], R_IN, -HALF)):
            r = math.hypot(x - CX, y - CY)
            off = (math.degrees(math.atan2(y - CY, x - CX)) - mid + 540) % 360 - 180
            if abs(r - wr) > 0.6:
                print(f"  FAIL arm{i} ({x},{y}) r={r:.1f} want {wr}"); fail = True
            if abs(off - wo) > 0.6:
                print(f"  FAIL arm{i} ({x},{y}) off={off:.1f} want {wo}"); fail = True
    m = re.search(r'<circle cx="(\d+)" cy="(\d+)" r="(\d+)"/>', s)
    if not m or tuple(map(int, m.groups())) != (CX, CY, CORE):
        print("  FAIL core circle"); fail = True

print()
print("GEOMETRY OK" if not fail else "PROBLEMS FOUND")
sys.exit(1 if fail else 0)
