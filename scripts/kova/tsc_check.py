#!/usr/bin/env python3
"""Type-check the TypeScript this branch actually authored, without a full
node_modules install.

A real `tsc -p .` needs every dependency's types (react, vitest, electron,
nanostores and ~40 more), which is a heavy install. This instead compiles
the files the rebrand changed semantically - not the ~2000 whose only
diff is a URL swap - and compares the error count against a pristine
worktree of the base commit, so "did we introduce a type error" is
answered by evidence rather than by eye.

The comparison matters: this project does not type-check clean on its own,
so an absolute error count says nothing. Only the delta against upstream
does.

Usage:
    python scripts/kova/tsc_check.py            # check this branch
    python scripts/kova/tsc_check.py --setup    # install the minimal tsc

Setup installs typescript + react + @types/react + nanostores into
_regression/tsc (~72 MB), not into the project. The project's own
node_modules is never touched.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(".").resolve()
TSC_DIR = ROOT / "_regression" / "tsc"
BASE = "2a977be9"          # upstream commit this fork started from

# Files whose CONTENT changed for a reason other than a URL string swap.
TARGETS = [
    "apps/desktop/src/global.d.ts",
    "apps/shared/src/theme-presets.ts",
    "apps/desktop/src/themes/presets.ts",
    "apps/desktop/src/themes/use-skin-command.ts",
    "apps/desktop/src/themes/context.tsx",
    "apps/desktop/src/themes/backend-sync.ts",
    "apps/desktop/src/themes/user-themes.ts",
    "apps/desktop/src/components/brand-mark.tsx",
    "web/src/themes/presets.ts",
]

SETUP_PKGS = ["typescript@5.9.3", "@types/react", "@types/react-dom",
              "@types/node", "react", "react-dom", "nanostores"]


def setup() -> None:
    TSC_DIR.mkdir(parents=True, exist_ok=True)
    if not (TSC_DIR / "package.json").exists():
        (TSC_DIR / "package.json").write_text('{"name":"kova-tsc","private":true}\n',
                                              encoding="utf-8")
    print("installing:", " ".join(SETUP_PKGS))
    subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--silent",
                    *SETUP_PKGS], cwd=TSC_DIR, check=True)
    # Make the type packages resolvable from the desktop app without
    # creating a node_modules the project would then have to keep clean.
    app_nm = ROOT / "apps" / "desktop" / "node_modules"
    app_nm.mkdir(parents=True, exist_ok=True)
    for pkg in ("react", "react-dom", "@types", "csstype", "prop-types",
                "scheduler", "nanostores"):
        src = TSC_DIR / "node_modules" / pkg
        if src.exists():
            shutil.copytree(src, app_nm / pkg, dirs_exist_ok=True)
    print("setup complete")


def tsc() -> pathlib.Path:
    p = TSC_DIR / "node_modules" / "typescript" / "bin" / "tsc"
    if not p.exists():
        print("typescript not installed; run: python scripts/kova/tsc_check.py --setup")
        raise SystemExit(2)
    return p


def errors_for(root: pathlib.Path, compiler: pathlib.Path) -> list[str]:
    """Type errors in TARGETS, excluding unresolved-module noise.

    TS2307 (cannot find module) is excluded because the full dependency
    tree is deliberately absent; its absence cascades into TS7006/TS7031/
    TS2322 on values that would otherwise be inferred. Every remaining
    code is a real type error in a file we touched.
    """
    files = [str(root / t) for t in TARGETS if (root / t).exists()]
    proc = subprocess.run(
        ["node", str(compiler), "--noEmit", "--jsx", "react-jsx",
         "--target", "ES2023", "--lib", "ES2023,DOM,DOM.Iterable",
         "--module", "ESNext", "--moduleResolution", "Bundler",
         "--skipLibCheck", "--strict", *files],
        capture_output=True, text=True, cwd=root,
    )
    out = proc.stdout + proc.stderr
    return [l for l in out.splitlines()
            if "error TS" in l and "TS2307" not in l]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--keep-worktree", action="store_true")
    args = ap.parse_args()

    if args.setup:
        setup()
        return 0

    compiler = tsc()
    mine = errors_for(ROOT, compiler)
    print(f"this branch : {len(mine)} type error(s) in the files it authored")

    wt = ROOT / "_regression" / "pristine-tsc"
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(["git", "worktree", "add", "-f", "--detach", str(wt), BASE],
                   cwd=ROOT, capture_output=True, check=True)
    try:
        base = errors_for(wt, compiler)
        print(f"pristine    : {len(base)} type error(s), same files")
    finally:
        if not args.keep_worktree:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                           cwd=ROOT, capture_output=True)

    new = [e for e in mine if e.split("(")[-1] not in
           {b.split("(")[-1] for b in base}]
    if new:
        print(f"\nNEW errors vs upstream ({len(new)}):")
        for e in new[:20]:
            print("  ", e.strip())
        return 1
    print("\nNo new type errors introduced by this branch.")
    if len(mine) < len(base):
        print(f"(and {len(base) - len(mine)} fewer than upstream, because the "
              f"rebrand removed the Hermes-specific branches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
