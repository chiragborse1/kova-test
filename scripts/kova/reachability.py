"""Every navigable destination in the shell must be reachable from the shell.

The Kova sidebar shows five rows: New session, Capabilities, Messaging, Artifacts,
Scheduled jobs. The app defines twelve core routes. Six of them -- webhooks,
profiles, agents, starmap, command-center, session-import -- appear nowhere in
the chrome, so a user who never learns the command palette cannot tell the app
has them. `/webhooks` had exactly ONE reference in the whole tree, a statusbar
item that only renders on some layouts.

This is the same class of defect as the ones `ui_audit.py` catches, one level up:
not "this surface is painted wrong" but "this destination does not exist to the
person using the app". A route you cannot find is not a route.

Usage:  py scripts/kova/reachability.py

Exits non-zero when a core route has no shell entry point, so it gates a build
the way kova_contrast.py and ui_audit.py already do.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "apps", "desktop", "src")
ROUTES_TS = os.path.join(SRC, "app", "routes.ts")

# Where a route has to be reachable from. Alternatives, not requirements: a
# route is fine if it appears in ANY listed surface.
#
# `command-palette` is deliberately NOT an accepted surface. It is the escape
# hatch for people who already know the app; relying on it is the bug.
SURFACES = {
    "sidebar": "apps/desktop/src/app/chat/sidebar",
    "statusbar": "apps/desktop/src/app/shell/hooks/use-statusbar-items.tsx",
    "shell": "apps/desktop/src/app/shell",
    "titlebar": "apps/desktop/src/app/shell/titlebar-controls.tsx",
}

ROUTE_RE = re.compile(r"^export const (\w+_ROUTE) = '([^']+)'", re.M)

# Routes that are chrome rather than destinations to hunt for: '/' is where the
# app opens, and settings is on the statusbar of every layout.
NOT_DESTINATIONS = ("NEW_CHAT_ROUTE", "SETTINGS_ROUTE")


def source_files():
    for base, dirs, names in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for name in names:
            if name.endswith((".ts", ".tsx")):
                yield os.path.join(base, name)


def read(path):
    with open(path, encoding="utf-8-sig") as handle:
        return handle.read()


def main():
    routes = ROUTE_RE.findall(read(ROUTES_TS))
    if not routes:
        print("  no core routes parsed - the routes file changed shape")
        return 1

    cache = {}
    for path in source_files():
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if ".test." in rel:
            continue
        cache[rel] = read(path)

    def refs(symbol):
        return [rel for rel, body in cache.items() if symbol in body and rel != "apps/desktop/src/app/routes.ts"]

    def surface_of(rel):
        for name, prefix in SURFACES.items():
            if rel == prefix or rel.startswith(prefix.rstrip("/") + "/"):
                return name
        return None

    unreachable = []
    print("  %-24s %-16s %s" % ("route", "path", "referenced from"))
    for symbol, path in routes:
        where = sorted({surface_of(r) or r for r in refs(symbol)})
        visible = [w for w in where if w in SURFACES]
        print("  %-24s %-16s %s" % (symbol, path, ", ".join(where) or "(nothing)"))
        if not visible and symbol not in NOT_DESTINATIONS:
            unreachable.append((symbol, path, where))

    print()
    if unreachable:
        for symbol, path, where in unreachable:
            fallback = "command palette only" if any("command-palette" in w for w in where) else "nowhere"
            print("  ATTENTION  %s (%s) is reachable from the %s" % (symbol, path, fallback))
        return 1
    print("  every core route has an entry point in the shell")
    return 0


if __name__ == "__main__":
    sys.exit(main())


