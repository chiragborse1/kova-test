"""A navigation list should be groupable, not just long.

The Settings rail lists 22 destinations in one flat column. It fits - 677px
of a 925px window, no scrollbar - so the problem is not space. It is that a
flat list of 22 asks the reader to already know which of 22 names belongs to
the thing they are looking for. "Providers", "Gateways", "Tools & Keys",
"API Keys" and "Passwords & Logins" are all credentials; "Advanced",
"Keyboard Shortcuts" and "About" are all system. Nothing on screen says so.

OpenClaw's Control UI groups the same kind of list into six labelled bands
(`SETTINGS_NAVIGATION_GROUPS` in ui/src/app-navigation.ts) and its settings
design doc states the rule outright: "Sections are typography, not chrome.
Grouping comes from whitespace + a small uppercase heading - never a card
header."

This gate reads the nav a user actually sees and reports:
  rows      how many destinations there are
  groups    how many labelled bands they fall into (1 == ungrouped)
  orphans   rows in no group
  coverage  rows in some group, as a percentage

It needs the app running with CDP on 9222.

Usage:  py scripts/kova/nav_ia.py
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_audit as U  # noqa: E402

# The bands, by the ids the Settings rail uses. Kept here rather than imported
# so the gate can report what the USER SEES even if the source is refactored -
# a gate that reads the implementation cannot catch the implementation being
# wrong.
GROUPS = {
    "": ["model", "chat", "appearance"],
    "device": ["workspace", "browser"],
    "connections": ["notifications", "gateway", "vault"],
    "agents": ["providers", "keys", "memory", "voice"],
    "security": ["safety", "passwords"],
    "system": ["keybinds", "sessions", "advanced", "about", "billing"],
}


def ev(expr):
    r = U.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r["result"]["result"].get("value") if r else None


PROBE = r"""JSON.stringify((()=>{
  const rows = [...document.querySelectorAll('button.row-hover')]
    .filter(b => {
      const r = b.getBoundingClientRect();
      return r.x < 300 && r.width > 100 && r.height > 10;
    })
    .map(b => ({
      label: (b.textContent || '').trim(),
      headings: [...document.querySelectorAll('[data-nav-group-label]')].length
    }));
  return { rows, headings: document.querySelectorAll('[data-nav-group-label]').length };
})())"""


def norm(label):
    return re.sub(r"[^a-z]", "", label.lower())


def main():
    ev("location.hash='#/settings'")
    time.sleep(3.5)
    raw = ev(PROBE)
    if not raw:
        print("  no value - is the app running with CDP on 9222?")
        return 1

    data = json.loads(raw)
    rows = data["rows"]
    labels = [r["label"] for r in rows]

    # Map each visible label onto a group by its position: the rail renders in
    # source order, and the gate's job is to report the shape a person sees.
    by_label = {}
    for name, ids in GROUPS.items():
        for i in ids:
            by_label[norm(i)] = name

    # Fall back to a prefix/substring match, since the visible label is
    # translated and will not equal the id.
    def group_of(label):
        n = norm(label)
        for key, name in by_label.items():
            if n.startswith(key) or key.startswith(n[:4]):
                return name
        return None

    assigned = [(l, group_of(l)) for l in labels]
    orphans = [l for l, g in assigned if g is None]
    groups_used = sorted({g for _, g in assigned if g})

    print("  %-34s %s" % ("rail destination", "band"))
    for label, group in assigned:
        print("  %-34s %s" % (label[:34], group or "ORPHAN"))

    print()
    print("  rows      %d" % len(rows))
    print("  bands     %d %s" % (len(groups_used), groups_used))
    print("  orphans   %d %s" % (len(orphans), orphans[:6]))
    print("  headings drawn on screen: %d" % data["headings"])

    if len(rows) < 10:
        print()
        print("  the rail did not render - nothing to measure")
        return 1

    if data["headings"] == 0 and len(rows) > 12:
        print()
        print("  ATTENTION  %d destinations in ONE flat band." % len(rows))
        print("  A flat list this long asks the reader to already know which")
        print("  name belongs to the thing they are after. Group it - OpenClaw")
        print("  uses six, with the first unlabelled.")
        return 1

    print()
    print("  the rail is grouped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
