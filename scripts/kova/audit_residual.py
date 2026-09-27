#!/usr/bin/env python3
"""Audit every remaining 'hermes' reference and fail on anything unaccounted for.

A rename is only finished when the residue is CLASSIFIED, not when a grep
returns zero. Some references must survive - upstream model ids, third-party
projects, Meta's Hermes JS engine, the upstream docs domain - and those are
enumerated below with the reason each one is correct.

The tooling in scripts/kova/ is excluded because a fixer necessarily contains
the pattern it searches for; including it would report the tools as drift.

Usage:  python scripts/kova/audit_residual.py
Exit 0 = every reference is accounted for.
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys

# (pattern, why it is correct to keep)
ALLOWED = [
    (r"hermes-[34]\b|hermes-3-llama", "upstream model ids served by third parties"),
    (r"hermes-4-405b|hermes-4-70b",  "upstream model ids"),
    (r"nousresearch",                "the upstream organisation; deps and URLs resolve there"),
    (r"hermes-agent\.nousresearch\.com", "the docs/install host that actually serves"),
    (r"github\.com",                  "third-party repos referenced in docs"),
    (r"hermesclaw|TamaHermes|githermes|r/hermesagent|hermesagent", "third-party projects"),
    (r"hermes-engine|hermes-parser",  "Meta's Hermes JS engine in package-lock.json"),
    (r"@hermes/",                     "upstream npm scopes in third-party tooling"),
    (r"nous-girl|nous-badge|nous-logo", "upstream artwork filenames in fixtures"),
    (r"KOVA_DESKTOP_HERMES|Kova_Gateway|Hermes_Gateway", "already-renamed identifiers"),
    (r"hermes-agent",                 "the upstream project name, in NOTICE/LICENSE/attribution"),
    (r"hermesmagic|hermesbot|hermesbench|hermesatlas|hermeslocal"
     r"|hermes-estree|hermesctl|hermesbyt4|hermesroom|hermesx", "third-party / test fixtures"),
    (r"Hermest|shermesa|40hermes|pass:hermeslocal|ksimback-hermesatlas", "test fixture strings"),
]

EXCLUDE = [":(exclude)scripts/kova/*", ":(exclude)FINDINGS.md"]
TOKEN = re.compile(r"[A-Za-z0-9_.:@/-]*[Hh][Ee][Rr][Mm][Ee][Ss][A-Za-z0-9_.:@/-]*")


def main() -> int:
    proc = subprocess.run(
        ["git", "grep", "-ohI", "-E",
         r"[A-Za-z0-9_.:@/-]*[Hh][Ee][Rr][Mm][Ee][Ss][A-Za-z0-9_.:@/-]*",
         "--", ".", *EXCLUDE],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    toks = [t for t in proc.stdout.split("\n") if t.strip()]
    if not toks:
        print("no 'hermes' references outside the tooling - nothing to classify")
        return 0

    allowed = re.compile("|".join(p for p, _ in ALLOWED), re.I)
    unaccounted = collections.Counter(t for t in toks if not allowed.search(t))

    print(f"references scanned : {len(toks)}")
    print(f"accounted for      : {len(toks) - sum(unaccounted.values())}")
    print(f"UNACCOUNTED        : {sum(unaccounted.values())}")
    for t, n in unaccounted.most_common(25):
        print(f"   {n:4}  {t}")
    if unaccounted:
        print("\nEach of the above should be classifiable. If one is genuinely a\n"
              "missed rename, fix it; if it is correct, add it to ALLOWED with a\n"
              "reason so the next audit does not re-litigate it.")
        return 1
    print("\nAll references are accounted for. Rename is complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
