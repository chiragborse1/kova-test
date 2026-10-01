"""Replace the fabricated nousresearch.com host with the real upstream host.

The rebrand mapped nousresearch.com -> nousresearch.com, inventing a domain
nobody owns. That produced ~900 dead links across 349 files: docs, install
instructions, badge targets, the Nous Portal integration and the OAuth
entry points.

There is no Kova-hosted docs site or install endpoint, so pointing these at
a plausible-looking domain would be worse than pointing them at the host
that actually serves the content. The rebrand keeps the product name; the
infrastructure is still Nous Research's until Kova runs its own.

  hermes-agent.nousresearch.com   -> hermes-agent.nousresearch.com   (docs/install)
  nousresearch.com              -> nousresearch.com              (org home)
  portal.nousresearch.com       -> portal.nousresearch.com       (Nous Portal API)

Usage:  python scripts/kova/fix_hostnames.py [--check]
"""
from __future__ import annotations

import subprocess
import sys

# Longest first: portal.nousresearch.com must be handled before the bare host.
RULES = [
    ("hermes-agent.nousresearch.com", "hermes-agent.nousresearch.com"),
    ("portal.nousresearch.com", "portal.nousresearch.com"),
    ("nousresearch.com", "nousresearch.com"),
]

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


def main() -> int:
    check = "--check" in sys.argv
    changed: list[str] = []
    for rel in tracked():
        norm = rel.replace("\\", "/")
        if any(d in norm for d in SKIP_DIRS) or norm.lower().endswith(BINARY_EXT):
            continue
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
        if "nousresearch.com" not in text:
            continue
        new = text
        for old, rep in RULES:
            new = new.replace(old, rep)
        if new != text:
            changed.append(norm)
            if not check:
                open(norm, "wb").write(new.encode("utf-8"))

    verb = "would rewrite" if check else "rewrote"
    print(f"{verb} {len(changed)} files")
    for c in changed[:12]:
        print("  ", c)
    if len(changed) > 12:
        print(f"   ... and {len(changed) - 12} more")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
