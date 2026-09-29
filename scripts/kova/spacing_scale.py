"""Tailwind's spacing scale must stay monotonic.

The redesign retargeted Tailwind's whole spacing scale onto an 8-step rhythm
(`--spacing-N: var(--ui-space-N)`), on the theory that naming the steps would
make density a choice. But `--spacing-N` is what backs EVERY `p-N` / `h-N` /
`gap-N` / `m-N` utility, and the rhythm's values are not Tailwind's:

    step   Tailwind   the rhythm   what h-N now renders
    5        20px        24px          24px
    6        24px        32px          32px
    7        28px        48px          48px

Worse, the scale stops at 7, so `h-8` through `h-10` fall back to Tailwind's
defaults - which makes the scale NON-MONOTONIC. Measured on the running app:

    h-6  32px     h-7  48px     h-8  32px     h-9  36px     h-10  40px

`h-7` is taller than `h-10`. Any layout that assumed these were ordinary
Tailwind heights is wrong, and nothing errors: the classes all resolve, they
just resolve to the wrong number.

The cost was not abstract. A sidebar nav row asks for `h-7` and rendered 48px
tall, so eleven rows pushed the session search to y=643 of a 925px viewport
and left ONE session row visible.

This gate reads the tokens and fails if any step is not strictly less than
the next, which is the property the scale has to have to be usable as a
scale at all.

Usage:  py scripts/kova/spacing_scale.py
"""
import re
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = os.path.join(ROOT, "apps", "desktop", "src", "styles.css")

# The utility steps the app actually uses, and what each must be for the
# scale to read as a scale.
EXPECTED = {0: 0.0, 1: 4.0, 2: 8.0, 3: 12.0, 4: 16.0, 5: 20.0, 6: 24.0, 7: 28.0}

REM = re.compile(r"--ui-space-(\d+):\s*([0-9.]+)rem")
ALIAS = re.compile(r"--spacing-(\d+):\s*var\(--ui-space-\d+\);")


def px(rem):
    return round(float(rem) * 16.0, 2)


def main():
    css = open(CSS, encoding="utf-8").read()

    steps = {int(n): px(v) for n, v in REM.findall(css)}
    aliased = {int(n) for n in ALIAS.findall(css)}

    if not steps:
        print("  no --ui-space-N tokens found - the scale moved")
        return 1

    bad = []

    print("  %-6s %-10s %-10s %s" % ("step", "declared", "tailwind", "verdict"))
    for step in sorted(set(steps) | set(aliased)):
        declared = steps.get(step)
        want = EXPECTED.get(step)
        if declared is None:
            verdict = "not declared" if step in aliased else ""
        elif want is None:
            verdict = "no expectation"
        elif abs(declared - want) < 0.01:
            verdict = "ok"
        else:
            verdict = "off by %+.0fpx" % (declared - want)
            bad.append((step, declared, want, verdict))
        print("  %-6s %-10s %-10s %s" % (
            "--spacing-%d" % step,
            "%gpx" % declared if declared is not None else "-",
            "%gpx" % want if want is not None else "-",
            verdict,
        ))

    # The property that makes a scale usable: each step strictly larger.
    ordered = [(s, steps[s]) for s in sorted(steps)]
    for (a, av), (b, bv) in zip(ordered, ordered[1:]):
        if bv <= av:
            bad.append((b, bv, av, "not larger than step %d" % a))

    print()
    if bad:
        for step, declared, want, verdict in bad:
            if verdict.startswith("not larger"):
                print("  ATTENTION  --spacing-%d (%gpx) is %s" % (step, declared, verdict))
            else:
                print("  ATTENTION  --spacing-%d is %gpx, Tailwind's is %gpx (%s)"
                      % (step, declared, want, verdict))
        print()
        print("  These back every p-N/h-N/gap-N/m-N utility, so the whole app")
        print("  is laid out on numbers that are not the ones the class names")
        print("  promise. Fix the tokens rather than the call sites.")
        return 1

    print("  the spacing scale is monotonic and matches Tailwind's steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())

