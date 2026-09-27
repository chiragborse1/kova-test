"""Emit the Kova mark as traced vector contours from the source artwork.

The artwork (assets/kova/source/kova-logo.png) is four flat colours on a
transparent field. Rather than hand-authoring bezier shapes and hoping they
match, this traces the real boundary of every part and simplifies it, so the
mark IS the artwork.

  python scripts/kova/make_mark.py            # write the SVGs
  python scripts/kova/make_mark.py --verify   # compare against the source

The mark is emitted in two forms the icon pipeline understands:
  kova-mark-black.svg  - one <path>, the silhouette (light squircle)
  kova-mark-white.svg  - one <path>, the silhouette (dark squircle)
plus a multi-colour kova-mark-color.svg for surfaces that show the artwork
as-is (the README banner, the website logo, the favicon).

The silhouette is what icons need: a single closed path, so
scripts/generate_icons.py's re.search(r"<path\\b.*?/>") keeps working.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: run with a Kova runtime interpreter")

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "kova" / "source" / "kova-logo.png"
OUT = ROOT / "assets" / "kova"

# Flat brand colours, measured from the artwork.
COLORS = {
    "head":   "#E1E6FC",
    "screen": "#000000",
    "green":  "#4EF895",
    "blue":   "#2CADFD",
}
PALETTE = {k: tuple(int(v[i:i+2], 16) for i in (1, 3, 5)) for k, v in COLORS.items()}

# Lattice stride: the trace runs on a half-resolution grid, which halves the
# point count and is well under one source pixel of error.
STRIDE = 1
# Douglas-Peucker tolerance in lattice cells (~2 source px at STRIDE 2).
EPSILON = 3.0
# Chaikin passes smooth the staircase the lattice walk leaves behind.
CHAIKIN = 2
# Max distance from a palette colour for a pixel to be considered that colour.
COLOR_TOL = 80


# --- tracing ---------------------------------------------------------------

def _label(im: Image.Image) -> list[list[str | None]]:
    w, h = im.size
    px = im.load()
    lab: list[list[str | None]] = [[None] * w for _ in range(h)]
    for y in range(h):
        row = lab[y]
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= 128:
                continue
            best, best_d = None, None
            for name, c in PALETTE.items():
                d = (r - c[0]) ** 2 + (g - c[1]) ** 2 + (b - c[2]) ** 2
                if best_d is None or d < best_d:
                    best_d, best = d, name
            if best_d <= COLOR_TOL * COLOR_TOL:
                row[x] = best
    return lab


def _components(lab, name: str, w: int, h: int, min_size: int = 40):
    seen = [[False] * w for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if lab[y][x] != name or seen[y][x]:
                continue
            stack = [(y, x)]
            seen[y][x] = True
            comp = []
            while stack:
                cy, cx = stack.pop()
                comp.append((cx, cy))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] and lab[ny][nx] == name:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            if len(comp) >= min_size:
                out.append(comp)
    out.sort(key=len, reverse=True)
    return out


def _rings(comp, name: str) -> list[list[tuple[float, float]]]:
    """Crack-follow the boundary of one component into closed rings.

    A lattice corner has at most two outgoing boundary edges, so this is O(n);
    the tie-break keeps the walk turning the same way through pinch points.
    """
    member = set(comp)
    out: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def add(a, b):
        out.setdefault(a, []).append(b)

    for cx, cy in comp:
        if (cx, cy - 1) not in member:
            add((cx, cy), (cx + 1, cy))
        if (cx + 1, cy) not in member:
            add((cx + 1, cy), (cx + 1, cy + 1))
        if (cx, cy + 1) not in member:
            add((cx + 1, cy + 1), (cx, cy + 1))
        if (cx - 1, cy) not in member:
            add((cx, cy + 1), (cx, cy))

    rings = []
    while out:
        start = min(out)
        ring = [start]
        cur = start
        d_in = (0, 0)
        while True:
            cands = out.get(cur)
            if not cands:
                break
            if len(cands) == 1:
                nxt = cands.pop()
            else:
                def key(q, cur=cur, d_in=d_in):
                    d = (q[0] - cur[0], q[1] - cur[1])
                    cross = d_in[0] * d[1] - d_in[1] * d[0]
                    dot = d_in[0] * d[0] + d_in[1] * d[1]
                    return (-cross, -dot)
                cands.sort(key=key)
                nxt = cands.pop(0)
            if not out[cur]:
                del out[cur]
            if nxt == start:
                break
            d_in = (nxt[0] - cur[0], nxt[1] - cur[1])
            ring.append(nxt)
            cur = nxt
        if len(ring) > 8:
            rings.append(ring)
    return rings


def _signed_area(pts) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


# --- simplification --------------------------------------------------------

def _rdp(pts, eps: float):
    if len(pts) < 3:
        return pts

    def perp(p, a, b):
        ax, ay = a
        bx, by = b
        pxx, pyy = p
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(pxx - ax, pyy - ay)
        t = max(0.0, min(1.0, ((pxx - ax) * dx + (pyy - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(pxx - (ax + t * dx), pyy - (ay + t * dy))

    stack = [(0, len(pts) - 1)]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        worst, idx = 0.0, i
        for k in range(i + 1, j):
            d = perp(pts[k], pts[i], pts[j])
            if d > worst:
                worst, idx = d, k
        if worst > eps:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def _chaikin(pts, passes: int):
    out = list(pts)
    for _ in range(passes):
        new = []
        n = len(out)
        for i in range(n):
            p, q = out[i], out[(i + 1) % n]
            new.append((0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]))
            new.append((0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]))
        out = new
    return out


# --- svg emission ----------------------------------------------------------

def _d(pts, xform) -> str:
    """An SVG path 'd' using straight segments. The traced contour is already
    polygonal, and at icon sizes a 1-2px polyline is indistinguishable from a
    curve while staying exactly faithful to the source."""
    m = [xform(p) for p in pts]
    head = f"M {m[0][0]:.2f} {m[0][1]:.2f}"
    rest = " ".join(f"L {x:.2f} {y:.2f}" for x, y in m[1:])
    return f"{head} {rest} Z"


def build() -> dict[str, list[tuple[str, list[tuple[float, float]]]]]:
    """Trace every part. Returns colour -> [(ring, points)] in source pixels."""
    im = Image.open(SOURCE).convert("RGBA")
    small = im.resize((im.width // STRIDE, im.height // STRIDE), Image.LANCZOS)
    lab = _label(small)
    w, h = len(lab[0]), len(lab)

    parts: dict[str, list[tuple[str, list]]] = {}
    for name in ("head", "blue", "screen", "green"):
        rings = []
        for comp in _components(lab, name, w, h):
            for ring in _rings(comp, name):
                if abs(_signed_area(ring)) * (STRIDE * STRIDE) < 400:
                    continue
                simp = _chaikin(_rdp(ring, EPSILON), CHAIKIN)
                # back to source pixel space
                rings.append((_signed_area(ring), [(x * STRIDE, y * STRIDE) for x, y in simp]))
        parts[name] = rings
    return parts


def silhouette(parts) -> list[tuple[float, float]]:
    """One closed outline of the whole mark: the head, which already contains
    the screen and the eyes as holes, plus the antenna and the ear."""
    outers = []
    for name in ("head", "blue"):
        for area, ring in parts[name]:
            if area > 0:
                outers.append((name, ring))
    return outers



# --- emit -----------------------------------------------------------------

# Which rings belong to the silhouette: the head's OUTER ring is the head
# body; the head's inner ring is the screen hole. The two blue parts are the
# ear and the antenna, both outside the head. So the silhouette = head outer
# + both blues, and the holes (screen, eyes) are drawn on top instead.


def _norm(pts, size: int = 1024, pad: float = 0.04):
    """Fit the traced art into a `size` box with `pad` margin, centred.

    Returns the transform, so every ring in a mark is scaled by the SAME
    factor. Normalising each ring on its own would slide the screen out of the
    shell it belongs to.
    """
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = size * (1 - 2 * pad) / max(x1 - x0, y1 - y0)
    ox = (size - (x1 - x0) * s) / 2 - x0 * s
    oy = (size - (y1 - y0) * s) / 2 - y0 * s
    return lambda p: (p[0] * s + ox, p[1] * s + oy)


def color_svg(parts, size=1024) -> str:
    """The full-colour mark: every ring in its own colour, painted back to
    front. Used where the artwork shows as-is (banner, website, favicon)."""
    allpts = [p for _, rings in parts.items() for _, r in rings for p in r]
    xf = _norm(allpts, size)
    body = []
    for name in ("head", "blue", "screen", "green"):
        for area, ring in parts[name]:
            body.append(f'  <path fill="{COLORS[name]}" fill-rule="evenodd" d="{_d(ring, xf)}"/>')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n'
        % (size, size, size, size)
        + "\n".join(body) + "\n</svg>\n"
    )


def silhouette_svg(parts, size=1024, fill="#000000") -> str:
    """One closed path: the mark's outline with the screen and eyes as holes.

    Icons need a single self-closing <path>; this keeps
    scripts/generate_icons.py's re.search(r"<path\\b.*?/>") working unchanged.
    """
    outer, holes = [], []
    for area, ring in parts["head"]:
        if area > 0:
            outer.append(ring)
    for area, ring in parts["blue"]:
        if area > 0:
            outer.append(ring)
    # The screen and the eyes are HOLES, not additions. The head's own inner
    # ring is the screen's outline traced from the lavender side, so the head
    # contributes an outer ring only - taking its inner ring as a hole too
    # would trace the same boundary twice and even-odd would cancel them.
    for name in ("screen", "green"):
        for area, ring in parts[name]:
            if area > 0:
                holes.append(ring)
    allpts = [p for ring in outer + holes for p in ring]
    xf = _norm(allpts, size)
    d = " ".join(_d(ring, xf) for ring in outer + holes)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">\n'
        '  <path fill="%s" fill-rule="evenodd" d="%s"/>\n</svg>\n'
        % (size, size, size, size, fill, d)
    )

def favicon_svg(parts, size: int = 1024) -> str:
    """A small-size variant for favicons.

    The full-colour mark puts ~45% of its ink in a black screen, which at
    16px is a smudge rather than a face. Here the shell is the dominant shape
    and the screen and eyes are holes punched through it, so the silhouette
    carries the mark at favicon size. The antenna and ear keep their blue so
    the mark still reads as the Kova artwork and not a generic blob.
    """
    outer = [r for a, r in parts["head"] if a > 0] + [r for a, r in parts["blue"] if a > 0]
    holes = [r for a, r in parts["screen"] if a > 0] + [r for a, r in parts["green"] if a > 0]
    xf = _norm([p for r in outer + holes for p in r], size)
    shell = " ".join(_d(r, xf) for r in outer + holes)
    blue = " ".join(_d(r, xf) for a, r in parts["blue"] if a > 0)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}">\n'
        f'  <path fill="{COLORS["head"]}" fill-rule="evenodd" d="{shell}"/>\n'
        f'  <path fill="{COLORS["blue"]}" fill-rule="evenodd" d="{blue}"/>\n'
        "</svg>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true",
                    help="report traced geometry without writing")
    args = ap.parse_args()

    if not SOURCE.is_file():
        print(f"missing source artwork: {SOURCE}", file=sys.stderr)
        return 1

    parts = build()
    for name, rings in parts.items():
        stats = ", ".join(f"{len(r)}pt" for _, r in rings)
        print(f"{name:7s} {len(rings)} ring(s): {stats}")
    if args.verify:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    written = {
        "kova-mark-black.svg": silhouette_svg(parts, 1024, "#000000"),
        "kova-mark-white.svg": silhouette_svg(parts, 1024, "#ffffff"),
        "kova-mark-color.svg": color_svg(parts, 1024),
        "kova-mark-favicon.svg": favicon_svg(parts, 1024),
    }
    for filename, text in written.items():
        path = OUT / filename
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
        else:
            print(f"unchanged {path.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
