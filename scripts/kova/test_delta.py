"""Compare two vitest JSON reports and report only NEW failures.

Usage:  py scripts/kova/test_delta.py <before.json> <after.json>

A full desktop run is ~18 minutes and ~34 files fail on a clean checkout
because the sandbox has no python3 and no electron packaging toolchain. Those
failures are real but they are not signal, so the only question that matters
when changing app code is whether the count or the SET grew. Counting files
alone hides a case where one pre-existing failure is fixed and a new one
appears.
"""
import json
import sys

def failed(path):
    data = json.loads(open(path, encoding="utf-8").read())
    return {r["name"] for r in data["testResults"] if r["status"] != "passed"}

def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    before, after = failed(argv[1]), failed(argv[2])
    new = sorted(after - before)
    fixed = sorted(before - after)

    print(f"  baseline failing files: {len(before)}")
    print(f"  current  failing files: {len(after)}")
    print(f"  NEW failures: {len(new)}")
    for f in new:
        print(f"    + {f}")
    print(f"  newly passing: {len(fixed)}")
    for f in fixed:
        print(f"    - {f}")

    if new:
        print("  REGRESSION - a change above landed on top of a broken file.")
        return 1
    print("  NO NEW FAILURES")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
