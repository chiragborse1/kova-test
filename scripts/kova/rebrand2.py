#!/usr/bin/env python3
"""
Kova rebrand pass 2: compound identifiers the first pass missed.

Pass 1 ordered its patterns longest-first but only handled:
    kova_cli, kova-agent, Kova_, Kova(?=[A-Z]), \\bkova\\b

That leaves camelCase and compound forms untouched, e.g.
    window.kovaDesktop   (532 refs in apps/desktop)
    KOVA_DESKTOP_HERMES    (compound env var; Kova_ needs a trailing _)
    __kovaWatch, .kova2, can_update_kova, kovaNpmLib

This pass targets exactly those, while protecting:
  - upstream model ids            (kova-3*, kova-4*)
  - Meta's Kova JS engine      (hermes-engine / hermes-parser)
  - third-party repos & handles  (github.com/*/kova*, reddit r/hermesagent,
                                   githermes, TamaHermes, alice_kova, ...)
  - upstream docs URLs           (hermes-agent.nousresearch.com)
  - contributors/ and .mailmap  (attribution pass handles these)
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(".")

SKIP_FILES = {"uv.lock", "package-lock.json", "flake.lock", "pnpm-lock.yaml", "Cargo.lock"}
SKIP_DIRS = ("node_modules/", ".venv/", "website/build/", "website/.docusaurus/",
             "_salvage/", "_regression/", "contributors/")
PROTECT_FILES = (".mailmap",)

# Sentinels for things that must survive verbatim.
PROTECTED_SUBSTRINGS = [
    "hermes-engine", "hermes-parser",
    "nousresearch/hermes-3", "nousresearch/hermes-4",
    "hermes-3-llama", "hermes-4-405b", "hermes-4-70b",
    "hermes-agent.nousresearch.com",
    "githermes", "TamaHermes", "hermesclaw",
    "r/hermesagent",
]
SENT = "\x00K2P%d\x00"


def shield(text: str) -> str:
    for i, tok in enumerate(PROTECTED_SUBSTRINGS):
        if tok.lower() in text.lower():
            text = re.sub(re.escape(tok), SENT % i, text, flags=re.IGNORECASE)
    return text


def unshield(text: str) -> str:
    for i, tok in enumerate(PROTECTED_SUBSTRINGS):
        text = text.replace(SENT % i, tok)
    return text


# github.com/<owner>/<repo> and generic URLs -> leave whole token alone
URL_RE = re.compile(r'(?:https?://|git\+https?://)[^\s"\'<>),;]+')
# bare npm scopes @kova/... and @kova-agent/...
SCOPE_RE = re.compile(r'@kova(?:-agent)?(?=/)')

ORDERED = [
    # env-var compounds: Kova anywhere in an ALLCAPS token
    (re.compile(r"Kova(?=[A-Z0-9_]*(?:[_A-Z0-9]|$))"), "KOVA"),
    # camelCase / lowerCamel: kovaFoo -> kovaFoo
    (re.compile(r"\bkova(?=[A-Z])"), "kova"),
    # private-ish underscore compounds: __kovaWatch, _kovaFoo
    (re.compile(r"(?<=[_@])kova(?=[A-Z])"), "kova"),
    # dotted members: .kovaDesktop, __kovaActHolder
    (re.compile(r"(?<=\.)kova(?=[A-Z])"), "kova"),
    # npm scopes
    (SCOPE_RE, "@kova"),
    # trailing-compound: .kova2, kova2
    (re.compile(r"\bkova(?=\d)"), "kova"),
    # _kovaFoo style identifiers with capital after underscore
    (re.compile(r"(?<=\b[a-zA-Z])_kova(?=[A-Z])"), "_kova"),
    # remaining plain identifier compounds like can_update_kova
    (re.compile(r"(?<=[a-z0-9])_kova(?![a-z0-9])"), "_kova"),
    # __kovaX / .__kovaX leading-underscore runs
    (re.compile(r"(__|\.)(__?)kova(?=[A-Z])"), r"\1\2kova"),
]


URL_SENT = "\x00K2U%d\x00"


def process(text: str, stats: dict) -> str:
    # Stash whole URLs so third-party repo names inside them survive intact.
    urls: list[str] = []

    def stash(m: re.Match) -> str:
        urls.append(m.group(0))
        return URL_SENT % len(urls)          # 1-based

    text = URL_RE.sub(stash, text)
    text = shield(text)

    for pat, repl in ORDERED:
        text = pat.sub(repl, text)

    text = unshield(text)
    for i, u in enumerate(urls, start=1):    # 1-based, matches stash
        text = text.replace(URL_SENT % i, u)
    return text


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split("\0") if p]


def main() -> None:
    apply = "--apply" in __import__("sys").argv
    changed = []
    for rel in tracked():
        n = rel.replace("\\", "/")
        if n.rsplit("/", 1)[-1] in SKIP_FILES or n in PROTECT_FILES:
            continue
        if any(n.startswith(d) or ("/" + d) in n for d in SKIP_DIRS):
            continue
        p = ROOT / n
        if not p.exists():
            continue
        raw = p.read_bytes()
        if b"\0" in raw[:4096]:
            continue
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new = process(txt, {})
        if new != txt:
            changed.append(n)
            if apply:
                p.write_bytes(new.encode("utf-8"))
    print(f"pass2: {len(changed)} files {'rewritten' if apply else 'would change'}")
    for c in changed[:25]:
        print("  ", c)


if __name__ == "__main__":
    main()
