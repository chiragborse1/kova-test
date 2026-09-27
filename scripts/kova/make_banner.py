"""Emit the Kova README banner.

    python scripts/kova/make_banner.py

The old banner was a gold HERMES-AGENT wordmark and it is the first thing
anyone sees in the repo README, so it is rebuilt in the supplied logo's
palette: the traced Kova mark beside a KOVA AGENT wordmark on the same
near-black ground the original used.

REPRODUCIBILITY

The wordmark is drawn with <text> and a font STACK, not a pinned font file.
A pinned Windows font would render differently on macOS and on CI, so the
committed PNG would stop matching what this script produces. The stack leads
with the fonts the wordmark is designed against and falls back through
common grotesques; the layout is metric-tolerant (the tagline is positioned
from the mark, not from the wordmark's width) so a fallback still composes.

GENERATED OUTPUTS ARE COMMITTED, matching the icon pipeline: builds consume
the PNG and never render, and .github/workflows/icons-freshness-check.yml
re-runs this and fails on any diff.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

try:
    from PIL import Image
    import resvg_py
except ImportError:
    sys.exit("Pillow and resvg-py are required: run with a Kova runtime interpreter")

ROOT = Path(__file__).resolve().parents[2]
MARK = ROOT / "assets" / "kova" / "kova-mark-color.svg"
OUT = [
    ROOT / "assets" / "banner.png",
    ROOT / "website" / "static" / "img" / "kova-agent-banner.png",
]

# Unchanged from the banner this replaces, so no consumer has to resize.
W, H = 1145, 196
BG = "rgb(20,20,20)"

# Brand palette, measured from the supplied artwork plus the kova skin accent.
LAV = "#E1E6FC"
VIOLET = "#6d3bf5"
VIOLET_HI = "#9d7bff"
MUTED = "#8f8aa3"

MARK_SIZE = 150.0
MARK_X = 26.0
TAGLINE = "the agent that evolves with you"

# Heavy grotesques first; every entry is a real face on a mainstream platform.
SANS = "Bahnschrift, 'Franklin Gothic Medium', 'Arial Narrow', Arial, Helvetica, sans-serif"


def svg() -> str:
    inner = MARK.read_text(encoding="utf-8")
    inner = inner.split(">", 1)[1].rsplit("</svg>", 1)[0]
    inner = "\n".join(line for line in inner.splitlines() if line.strip())
    mark_y = (H - MARK_SIZE) / 2
    text_x = MARK_X + MARK_SIZE + 30
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="wordmark" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{LAV}"/>
      <stop offset="55%" stop-color="{VIOLET_HI}"/>
      <stop offset="100%" stop-color="{VIOLET}"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <svg x="{MARK_X}" y="{mark_y}" width="{MARK_SIZE}" height="{MARK_SIZE}" viewBox="0 0 1024 1024" preserveAspectRatio="xMidYMid meet">
{inner}
  </svg>
  <text x="{text_x}" y="116" font-family="{SANS}" font-size="96" font-weight="700" letter-spacing="-1" fill="url(#wordmark)">KOVA AGENT</text>
  <text x="{text_x + 4}" y="152" font-family="{SANS}" font-size="27" font-weight="400" letter-spacing="1.5" fill="{MUTED}">{TAGLINE}</text>
</svg>
"""


def render() -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=svg(), width=W, height=H)
    return Image.open(io.BytesIO(data)).convert("RGB")


def main() -> int:
    if not MARK.is_file():
        print(f"missing {MARK}; run scripts/kova/make_mark.py first", file=sys.stderr)
        return 1
    image = render()
    import io as _io
    buf = _io.BytesIO()
    image.save(buf, "PNG", optimize=True)
    payload = buf.getvalue()
    for path in OUT:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and path.read_bytes() == payload:
            print(f"unchanged {path.relative_to(ROOT)}")
            continue
        path.write_bytes(payload)
        print(f"wrote {path.relative_to(ROOT)} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
