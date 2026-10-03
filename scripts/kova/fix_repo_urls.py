#!/usr/bin/env python3
"""Rewrite the project's own repository URLs to the fork's real home.

The rebrand mapped NousResearch/Kova-Agent -> "kova-agent", which is not a
valid owner/repo pair: it names a GitHub *user*, not an org holding a repo.
That produced ~300 malformed links across 240 files (docs cross-references,
skill references, issue and PR links, badge targets).

Only the project's own URLs are touched. Third-party repositories - forks
upstream maintains, vendor links, other people's projects - are left alone,
which is the same rule that fixes the misaki dependency.

Usage:  python scripts/kova/fix_repo_urls.py [--check]
"""
from __future__ import annotations

import re
import subprocess
import sys

OWNER = "chiragborse1"
REPO = "kova-test"
OLD = "github.com/kova-agent"

# Match the broken form and capture whatever path followed it.
PATTERN = re.compile(re.escape(OLD) + r"(?P<path>(?:\.git)?(?:/[^\s\"'<>),;]*)?)")

SKIP_DIRS = ("node_modules/", ".venv/", "_salvage/", "_regression/",
             # This directory and FINDINGS.md necessarily CONTAIN the patterns
             # being searched for, so a --check run would otherwise always
             # report itself as drift.
             "scripts/kova/", "FINDINGS.md",
             "website/build/", "website/.docusaurus/", "dist/")
BINARY_EXT = (".png", ".jpg", ".jpeg", ".ico", ".icns", ".webp", ".gif",
              ".woff", ".woff2", ".ttf", ".tflite", ".whl", ".jar", ".zip",
              ".mp4", ".webm", ".pdf")


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return [f for f in out.stdout.split("\0") if f]


def rewrite(text: str) -> str:
    def sub(m: re.Match) -> str:
        path = m.group("path")
        # A bare "kova-agent" with no path is the repo root itself.
        if path == ".git" or path == "/.git":
            return f"github.com/{OWNER}/{REPO}.git"
        if path in ("", "/"):
            return f"github.com/{OWNER}/{REPO}"
        return f"github.com/{OWNER}/{REPO}{path}"
    return PATTERN.sub(sub, text)


def main() -> int:
    check = "--check" in sys.argv
    changed: list[str] = []
    for rel in tracked():
        norm = rel.replace("\\", "/")
        if any(d in norm for d in SKIP_DIRS) or norm.lower().endswith(BINARY_EXT):
            continue
        p = rel if hasattr(rel, "read_text") else None
        try:
            raw = open(norm, "rb").read()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if OLD not in text:
            continue
        new = rewrite(text)
        if new != text:
            changed.append(norm)
            if not check:
                open(norm, "wb").write(new.encode("utf-8"))

    verb = "would rewrite" if check else "rewrote"
    print(f"{verb} {len(changed)} files")
    for c in changed[:15]:
        print("  ", c)
    if len(changed) > 15:
        print(f"   ... and {len(changed) - 15} more")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
