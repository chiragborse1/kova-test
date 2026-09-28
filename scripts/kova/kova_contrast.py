#!/usr/bin/env python3
"""Kova's two contrast gates.

TEXT contrast and SURFACE contrast are different questions, and only the
second one decides whether an interface needs outlines. This gate used to
check only the first, which is why it was content while every surface tier
sat at 1.03-1.15 and the app drew a border around everything. The boxes were
a symptom; the surfaces were the disease.

The palette is READ from apps/shared/src/theme-presets.ts rather than copied.
A gate that holds its own copy keeps checking colours the app stopped using,
which is how a green gate comes to mean nothing.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
THEME = ROOT / "apps/shared/src/theme-presets.ts"


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def load_kova_palette():
    """Read the kova theme's colours from the one file that defines them."""
    text = THEME.read_text(encoding="utf-8")
    start = text.find("  kova: {")
    if start < 0:
        raise SystemExit("could not find the kova theme in theme-presets.ts")
    nxt = re.search(r"\n  \w+: \{", text[start + 10:])
    block = text[start:start + 10 + nxt.start()] if nxt else text[start:]
    split = block.find("darkColors:")
    out = {"LIGHT": {}, "DARK": {}}
    for theme, part in (("LIGHT", block[:split]), ("DARK", block[split:])):
        for key, value in re.findall(r"\b(\w+): '(#[0-9a-fA-F]{6})'", part):
            out[theme][key] = value
    return out


# Surfaces that form a LADDER. accent and secondary are deliberately excluded:
# they are fills applied ON a tier, so they sit close to it on purpose, and
# judging them against the tier they sit on is the same mistake as judging a
# chip against its own card.
LADDER = ["background", "sidebarBackground", "card", "muted", "elevated", "popover"]
# A tier below this is invisible on its own, and the code reaches for a
# border to draw it - which is the grid-of-boxes look.
AGAINST_GROUND = 1.15

TEXT = [
    # accent is a FILL, not a text colour. The palette key that carries
    # tinted text is `primary`; checking `accent` produced a failure that
    # meant nothing, which is worse than no check at all.
    ("primary", 4.5), ("foreground", 4.5), ("mutedForeground", 4.5),
    ("primaryForeground on primary", 4.5), ("destructive", 4.5),
]


def main() -> int:
    palette = load_kova_palette()
    ok = True

    print("SURFACE LADDER  (each tier >= 1.15:1 against the ground)")
    for theme in ("LIGHT", "DARK"):
        colours = palette[theme]
        ground = colours["background"]
        print(f"  {theme}")
        for key in LADDER:
            colour = colours.get(key)
            if not colour:
                continue
            if key == "background":
                print(f"  --    {theme:5} {key:17} {colour}  (ground)")
                continue
            r = ratio(colour, ground)
            # A popover may move TOWARD the ground: a white dropdown on a
            # white canvas is correct. It is judged against the tier it
            # actually floats over instead.
            if key == "popover":
                over = colours.get("card", ground)
                r = ratio(colour, over)
                label = f"vs the card it floats over {over}"
            else:
                label = f"vs ground {ground}"
            passed = r >= (AGAINST_GROUND if key != "popover" else 1.15)
            ok &= passed
            print(f"  {'PASS' if passed else 'FAIL'}  {theme:5} {key:17} {colour}  "
                  f"{r:5.2f}:1  {label}")

    # --- accent FILLS, not surface tiers -------------------------------
    # A tint is a wash unless it clears the same bar a surface does. These
    # values were MEASURED off the running app (a probe element painted with
    # each token, read back through getComputedStyle), not modelled: reading
    # the color-mix by hand got the direction of the overlay wrong twice.
    #   tertiary    1.261:1 vs card   a real fill  -> no border needed
    #   quaternary  1.175:1 vs card   a real fill  -> no border needed
    #   quinary     1.114:1 vs card   a wash       -> the border earns it
    FILLS = [("tertiary", 1.261, True), ("quaternary", 1.175, True), ("quinary", 1.114, False)]
    print()
    print("ACCENT FILLS  (a wash still needs the border it has)")
    for name, measured, is_surface in FILLS:
        good = is_surface == (measured >= AGAINST_GROUND)
        ok &= good
        verdict = "a surface" if is_surface else "a wash - keep the border"
        print(f"  {'PASS' if good else 'FAIL'}  {name:12s} {measured:5.3f}:1 vs card  {verdict}")

    print()
    print("TEXT CONTRAST  (WCAG AA, 4.5:1)")
    for theme in ("LIGHT", "DARK"):
        c = palette[theme]
        for name, need in TEXT:
            if name == "primaryForeground on primary":
                fg, bg = c.get("primaryForeground"), c.get("primary")
            else:
                fg, bg = c.get(name), c["background"]
            if not fg or not bg:
                continue
            r = ratio(fg, bg)
            passed = r >= need
            ok &= passed
            print(f"  {'PASS' if passed else 'FAIL'}  {theme:5} {name:26} {r:6.2f}:1")

    print()
    print("ALL PASS" if ok else "SOME FAIL - the palette or the surface ladder needs adjusting")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
