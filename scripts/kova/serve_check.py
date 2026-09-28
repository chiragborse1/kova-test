"""The dev server must actually compile every module the app imports.

`tsc --noEmit` was green while the running app showed "Something broke in the
interface". The cause was a stray paren in app/settings/index.tsx: Babel
refused the module, the dynamic import failed, and the route rendered the
error boundary. TypeScript did not catch it because it was reading a stale
incremental build, not because the file was valid.

That combination - green typecheck, broken app - has now happened twice in
this codebase (a JSX comment inside an expression, then this), and both times
the only thing that noticed was looking at the screen. So this gate looks at
the screen too: it asks the dev server for each module the app has actually
imported and fails if any of them comes back as an error page instead of
JavaScript.

Usage:  py scripts/kova/serve_check.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

DEV = os.environ.get("KOVA_DEV_SERVER", "http://127.0.0.1:5174")

# The modules a route pulls in. A parse error in ANY of these takes down the
# view that imported it, and none of them are covered by the typecheck.
MODULES = [
    "/src/app/settings/index.tsx",
    "/src/app/chat/sidebar/index.tsx",
    "/src/app/overlays/overlay-split-layout.tsx",
    "/src/components/ui/sidebar.tsx",
    "/src/i18n/en.ts",
    "/src/styles.css",
]


def main():
    print("  asking %s for %d modules" % (DEV, len(MODULES)))
    bad = []

    for path in MODULES:
        url = DEV + path
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                body = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
        except Exception as error:  # noqa: BLE001 - report, do not raise
            print("  ATTENTION  %s could not be fetched: %s" % (path, error))
            bad.append(path)
            continue

        # Vite serves a parse failure as an HTML error page carrying the
        # Babel message, never as the module the app asked for.
        message = None
        if body.lstrip().lower().startswith("<!doctype html"):
            found = re.search(r'"message":"(.*?)","stack"', body, re.S)
            message = (found.group(1) if found else "returned HTML, not JavaScript")
            message = message.encode().decode("unicode_escape", "replace")
        elif "[BabelError]" in body or "BABEL_PARSE_ERROR" in body:
            message = body[:200]

        if message:
            print("  ATTENTION  %s" % path)
            for line in message.splitlines()[:6]:
                print("              " + line)
            bad.append(path)
        else:
            print("    ok        %s" % path)

    print()
    if bad:
        print("  %d module(s) do not compile. The app is broken for whoever" % len(bad))
        print("  imports them, whatever tsc says.")
        return 1
    print("  every module compiles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
