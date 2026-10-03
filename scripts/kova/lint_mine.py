"""The files this branch touched must be lint-clean.

`npm run check:lint` fails on this repo - 123 errors across 114 files, all
but six of them predate this work. That is not a reason to skip it: it is a
reason to be precise about which errors are MINE.

For ten sessions I reported "verified" having run tsc, vitest and a set of
custom gates, and never once run eslint. Then, in the first session where CI
was able to run at all, the JS & TS job would have failed on six of my own
errors that every local command I had been using reported as clean:

  - an unused `SidebarGroupLabel` import left behind when the "Manage" band
    became a "More" row
  - five `perfectionist/sort-imports` orderings, from the route and dropdown
    imports I added

Both `tsc` and vitest pass on all of them. A lint rule is a different kind of
check from a type check or a test, and "my gates are green" was never
evidence about it.

So this gate answers the question that is actually actionable: not "is the
repo lint-clean" (it is not, and that is not this branch's business) but "did
I add any". It diffs against the merge base, lints only the changed files,
and fails only on errors in those.

Usage:  py scripts/kova/lint_mine.py [base]
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESKTOP = os.path.join(ROOT, "apps", "desktop")


def run(args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)


def changed_files(base):
    out = run(["git", "diff", "--name-only", "%s..HEAD" % base]).stdout
    return {f for f in out.split() if f.endswith((".ts", ".tsx"))}


def main(argv):
    base = argv[1] if len(argv) > 1 else "main"
    files = sorted(changed_files(base))
    if not files:
        print("  no changed .ts/.tsx files against %s" % base)
        return 0

    print("  %d changed source file(s) against %s\n" % (len(files), base))

    report = os.path.join(ROOT, ".eslint-mine.json")
    rel = [os.path.relpath(os.path.join(ROOT, f), DESKTOP).replace(os.sep, "/") for f in files]
    missing = [r for r in rel if not os.path.exists(os.path.join(DESKTOP, r))]
    if missing:
        print("  these changed files do not exist under apps/desktop:")
        for m in missing:
            print("    " + m)
        return 1
    res = run(
        "npx eslint %s -f json -o \"%s\"" % (" ".join('"%s"' % r for r in rel), report),
        cwd=DESKTOP,
    )
    if not os.path.exists(report):
        print("  eslint produced no report:")
        print(res.stdout[-1500:])
        print(res.stderr[-800:])
        return 1

    with open(report, encoding="utf-8-sig") as handle:
        data = json.load(handle)
    os.remove(report)

    errors = warnings = 0
    for entry in data:
        rel = entry["filePath"].split("kova-agent")[-1].replace("\\", "/").lstrip("/")
        for message in entry["messages"]:
            if message["severity"] == 2:
                errors += 1
                print("  ERROR    %s:%d  [%s] %s"
                      % (rel, message["line"], message.get("ruleId"), message["message"][:100]))
            else:
                warnings += 1
                print("  warning  %s:%d  [%s] %s"
                      % (rel, message["line"], message.get("ruleId"), message["message"][:100]))

    print()
    print("  %d error(s), %d warning(s) in the files this branch changed" % (errors, warnings))
    if errors:
        print()
        print("  tsc and vitest both pass on these, so nothing else you ran")
        print("  would have told you. Run eslint --fix, or fix them by hand.")
        return 1
    print("  nothing this branch changed introduces a lint error")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
