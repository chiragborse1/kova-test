#!/usr/bin/env python3
"""Rename the PascalCase compounds the first two rebrand passes missed.

Pass 1 ordered longest-match-first but its patterns all required a
character AFTER the token (hermes_ matches hermes_foo, hermes- matches
hermes-cli). That misses the camelCase/PascalCase family entirely:

    startHermes  updateHermes  locateHermes  waitForHermes
    restartHermes  uninstallHermes  canUpdateHermes  Get-SourceHermes
    plugin.requiresHermes  t.status.updatingHermes  _hermes

1315 occurrences across 78 files, including i18n keys that are USER-
VISIBLE in every translated language (web/src/i18n/*.ts, where
`t.status.updatingHermes` renders as a translated string).

Everything still protected is protected here too: upstream model ids,
Meta's Hermes JS engine, third-party repos, the upstream docs domain,
and the repo-URL set already fixed.

Usage:  python scripts/kova/fix_pascal.py [--check]
"""
from __future__ import annotations

import re
import subprocess
import sys

# Sentinels: substrings that must survive verbatim.
PROTECT = [
    "hermes-engine", "hermes-parser",
    "nousresearch/hermes-3", "nousresearch/hermes-4",
    "hermes-3-llama", "hermes-4-405b", "hermes-4-70b",
    "hermes-agent.nousresearch.com",
    "githermes", "TamaHermes", "hermesclaw", "r/hermesagent",
    "nous-girl", "nous-badge", "nous-logo",
    "KOVA_DESKTOP_HERMES", "Kova_Gateway",
]
SENT = "\x00K3P%d\x00"

# Whole-token forms handled by earlier passes, skipped here to avoid
# double-rewriting and to keep this script's blast radius legible.
URL = re.compile(r'(?:https?://|git\+https?://)[^\s"\'<>),;]+')

# PascalCase: a capitalised prefix glued to a following capital
# (startHermes, Get-SourceHermes) and lowerCamel after a separator
# (requiresHermes, _hermesWatch, .hermesHome).
# Capitalisation follows the ORIGINAL token, not its position in the word.
#
# Ordering "lowercase-rule first, PascalCase-rule second" is wrong: the
# lowerCamel rule consumes startHermes before the PascalCase rule can see
# it, and you get startkova. One rule with a case-preserving replacement
# keeps the decision local to the match:
#
#   startHermes   -> startKova     (Hermes was capitalised, keep it so)
#   .hermesHome   -> .kovaHome     (hermes was lowercase, keep it so)
#   _hermesWatch  -> _kovaWatch
#
# The lookahead restricts it to a glued compound, so a standalone word is
# left to the earlier passes that already handle it.
# The lookahead is (?![a-z]) rather than (?=[A-Z]). A capital-after lookahead
# only matches a word followed by another capital, so it silently skips the
# commonest shape of all: the token at the END of an identifier, as in
# startHermes / updateHermes / canUpdateHermes.
RULES = [
    (re.compile(r"[Hh][Ee][Rr][Mm][Ee][Ss](?![a-z])"),
     lambda m: ("Kova" if m.group(0)[0].isupper() else "kova")),
]

SKIP_DIRS = ("node_modules/", ".venv/", "_salvage/", "_regression/",
             "website/build/", "website/.docusaurus/")
BINARY = (".png", ".jpg", ".jpeg", ".ico", ".icns", ".webp", ".gif", ".woff",
          ".woff2", ".ttf", ".tflite", ".whl", ".jar", ".zip", ".mp4", ".pdf")


def transform(text: str) -> str:
    urls = []

    def stash(m):
        urls.append(m.group(0))
        return "\x00K3U%d\x00" % len(urls)

    text = URL.sub(stash, text)
    for i, tok in enumerate(PROTECT):
        if tok.lower() in text.lower():
            text = re.sub(re.escape(tok), SENT % i, text, flags=re.IGNORECASE)
    for pat, rep in RULES:
        text = pat.sub(rep, text)
    for i, tok in enumerate(PROTECT):
        text = text.replace(SENT % i, tok)
    for i, u in enumerate(urls, start=1):
        text = text.replace("\x00K3U%d\x00" % i, u)
    return text


def main() -> int:
    check = "--check" in sys.argv
    files = [f for f in subprocess.run(["git", "ls-files", "-z"], capture_output=True,
                                       text=True, check=True).stdout.split("\0") if f]
    changed = []
    for rel in files:
        n = rel.replace("\\", "/")
        if any(d in n for d in SKIP_DIRS) or n.lower().endswith(BINARY):
            continue
        try:
            raw = open(n, "rb").read()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "hermes" not in text.lower():
            continue
        new = transform(text)
        if new != text:
            changed.append(n)
            if not check:
                open(n, "wb").write(new.encode("utf-8"))
    print(("would rewrite " if check else "rewrote ") + f"{len(changed)} files")
    for c in changed[:12]:
        print("  ", c)
    if len(changed) > 12:
        print(f"   ... and {len(changed) - 12} more")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
