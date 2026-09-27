#!/usr/bin/env python3
"""
Kova rebrand engine.

Ordered longest-match-first token replacement across git-tracked text files,
renaming the kova-agent codebase to Kova Agent.

This is the corrected version of the previous attempt's engine. The previous
run produced 225 newly-broken tests; the cause was that it renamed tokens
carrying upstream semantics. This version protects them explicitly.

Usage:
    python scripts/kova/rebrand.py --root . [--apply] [--report]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

# --------------------------------------------------------------------------
# PROTECTED TOKENS - never rewrite these. Each entry is upstream-meaningful
# and renaming it breaks behaviour, not just branding.
# --------------------------------------------------------------------------
# 1. Upstream model identifiers. Family detection (agent/transports) maps
#    these strings to transport behaviour; renaming yields _model_family() ->
#    None, which is what broke test_family_detection last time.
PROTECTED_SUBSTRINGS = [
    "nousresearch/hermes-3-",
    "nousresearch/hermes-4-",
    "nousresearch/hermes-3-llama",
    "hermes-3-llama-3.1-405b",
    "hermes-3-llama-3.1-70b",
    "hermes-4-405b",
    "hermes-4-70b",
]

# 2. Lockfiles are generated; rewriting them corrupts the dependency graph.
#    package-lock.json also contains Meta's Kova JS engine
#    (hermes-engine / hermes-parser), which is entirely unrelated to this
#    project - renaming it would break React Native tooling.
SKIP_FILENAMES = {
    "uv.lock",
    "package-lock.json",
    "flake.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
}

# 3. Upstream contributor/attribution surface. Stripped wholesale in a
#    separate step rather than renamed (see prune_attribution.py).
PROTECTED_PATHS = (
    "contributors/",
    ".mailmap",
)

# 4. Files with no useful rebrand value / high breakage risk.
SKIP_PATHS = (
    "website/build/",
    "website/.docusaurus/",
    "node_modules/",
)

# --------------------------------------------------------------------------
# ORDERED REPLACEMENTS - longest and most specific first.
# --------------------------------------------------------------------------
ORDERED: list[tuple[str, str, str]] = [
    # --- upstream attribution + URLs (must precede generic 'kova') ---
    ("NousResearch/Kova-Agent", "kova-agent"),
    ("NousResearch/kova-agent", "kova-agent"),
    ("nousresearch/kova-agent", "kova-agent"),
    ("NousResearch", "OpenKova"),
    ("nousresearch", "openkova"),
    ("github\\.com/NousResearch", "github.com/OpenKova"),

    # --- domains / installers ---
    ("kova-agent\\.neuralstudio\\.in", "kova-agent.neuralstudio.in"),
    ("kova-agent\\.nousresearch\\.com", "kova-agent.neuralstudio.in"),
    ("setup-kova\\.sh", "setup-kova.sh"),
    ("setup-kova\\.ps1", "setup-kova.ps1"),

    # --- python package / module roots ---
    ("kova_cli", "kova_cli"),
    ("kova_platform", "kova_platform"),
    ("kova_agent", "kova_agent"),
    ("kova-agent", "kova-agent"),

    # --- env var prefix + SHOUTY ---
    ("KOVA_", "KOVA_"),
    ("\\bKova\\b", "KOVA"),
    ("\\bKova\\b", "Kova"),
    ("Kova(?=[A-Z])", "Kova"),

    # --- lowercase compounds ---
    ("kova_(?=[a-z0-9])", "kova_"),
    ("kova-(?=[a-z0-9])", "kova-"),
    ("kova\\.(?=[a-z])", "kova."),
    ("/kova\\b", "/kova"),
    ("\\bkova\\b", "kova"),
]


SENTINEL = "\x00KOVAPROT%d\x00"


def shield(text: str, stats: dict) -> tuple[str, list[str]]:
    """Replace protected tokens with sentinels so patterns cannot touch them.

    Detection alone is not enough: 'hermes-4-405b' contains 'kova', so the
    rename patterns would still rewrite it. The previous attempt did exactly
    that, which is what made _model_family() return None upstream.
    """
    hits: list[str] = []
    out = text
    for i, token in enumerate(PROTECTED_SUBSTRINGS):
        if token.lower() in out.lower():
            hits.append(token)
            out = re.sub(re.escape(token), SENTINEL % i, out, flags=re.IGNORECASE)
    if hits:
        stats["protected_hits"] += len(hits)
    return out, hits


def unshield(text: str) -> str:
    for i, token in enumerate(PROTECTED_SUBSTRINGS):
        text = text.replace(SENTINEL % i, token)
    return text


def build_patterns() -> list[tuple[re.Pattern[str], str, str]]:
    return [(re.compile(src), src, repl) for src, repl in ORDERED]


PATTERNS = build_patterns()


def transform(text: str, stats: dict, src: str) -> str:
    out = text
    for re_, raw, repl in PATTERNS:
        out, n = re_.subn(repl.replace("\\", "\\\\"), out)
        if n:
            stats["byPattern"][raw] = stats["byPattern"].get(raw, 0) + n
    return out


def should_skip(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name in SKIP_FILENAMES:
        return True
    norm = rel.replace("\\", "/")
    return any(norm.startswith(p) or ("/" + p) in norm for p in SKIP_PATHS)


def is_protected_path(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    return any(norm.startswith(p) for p in PROTECTED_PATHS)


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root, capture_output=True, check=True,
    )
    return [p.decode("utf-8", "surrogateescape") for p in out.stdout.split(b"\0") if p]


def is_binary(data: bytes) -> bool:
    return b"\0" in data[:4096]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    files = tracked_files(root)

    stats: dict = {
        "scanned": 0, "changed": 0, "skipped_binary": 0,
        "skipped_lockfile": 0, "skipped_protected": 0,
        "protected_hits": 0, "byPattern": {}, "changedPaths": [],
    }

    for rel in files:
        stats["scanned"] += 1
        if should_skip(rel):
            stats["skipped_lockfile"] += 1
            continue
        if is_protected_path(rel):
            stats["skipped_protected"] += 1
            continue

        abs_path = root / rel
        try:
            raw = abs_path.read_bytes()
        except (OSError, ValueError):
            continue
        if is_binary(raw):
            stats["skipped_binary"] += 1
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            stats["skipped_binary"] += 1
            continue

        shielded, hits = shield(text, stats)
        if hits:
            stats.setdefault("protectedExamples", [])
            for h in hits:
                if len(stats["protectedExamples"]) < 12:
                    stats["protectedExamples"].append(f"{rel} :: {h}")

        new = unshield(transform(shielded, stats, rel))
        if new != text:
            stats["changed"] += 1
            stats["changedPaths"].append(rel)
            if args.apply:
                abs_path.write_bytes(new.encode("utf-8"))

    if args.report:
        print(json.dumps(
            {k: v for k, v in stats.items() if k != "changedPaths"},
            indent=2,
        ))
        print(f"changed files: {len(stats['changedPaths'])}")
    else:
        print(f"scanned={stats['scanned']} changed={stats['changed']} "
              f"protected={stats['protected_hits']} binary={stats['skipped_binary']}")
        for k, v in sorted(stats["byPattern"].items(), key=lambda x: -x[1]):
            print(f"  {v:>7}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
