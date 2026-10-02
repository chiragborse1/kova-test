#!/usr/bin/env python3
"""
Parse-check TypeScript/TSX sources with a real TypeScript grammar.

There is no node_modules in this checkout and installing one is heavy, so
`tsc` is not available locally. tree-sitter parses TypeScript directly and
catches syntax errors (the class of mistake an unvalidated bulk edit makes,
such as a stray non-ASCII character inside a hex literal).

Usage:  python scripts/kova/ts_check.py [paths...]
        no args -> checks every tracked .ts/.tsx file
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_typescript as tsts

LANGS = {
    ".ts": Language(tsts.language_typescript()),
    ".tsx": Language(tsts.language_tsx()),
}
SKIP = ("node_modules/", ".venv/", "_salvage/", "_regression/",
        "website/build/", "website/.docusaurus/", "dist/")


def check(paths: list[str]) -> int:
    bad = 0
    for rel in paths:
        p = Path(rel)
        if any(s in rel.replace("\\", "/") for s in SKIP):
            continue
        lang = LANGS.get(p.suffix)
        if lang is None or not p.exists():
            continue
        src = p.read_bytes()
        tree = Parser(lang).parse(src)
        errs: list = []

        def walk(n):
            if n.type == "ERROR" or n.is_missing:
                errs.append((n.start_point[0] + 1, src[n.start_byte:n.end_byte][:70]))
            for c in n.children:
                walk(c)

        walk(tree.root_node)
        if errs:
            bad += 1
            print(f"FAIL {rel}")
            for line, frag in errs[:6]:
                print(f"     line {line}: {frag!r}")
    print(f"\nchecked {len(paths)} files, {bad} with syntax errors")
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) > 1:
        return check(sys.argv[1:])
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    files = [f for f in out.split("\0") if f.endswith((".ts", ".tsx"))]
    return check(files)


if __name__ == "__main__":
    raise SystemExit(main())
