"""Rebrand the PROSE attribution to Neural Studios.

Scope is deliberately narrow: only displayed prose. Two things are left
alone because they must keep resolving:

  - the Discord invite URL (https://discord.gg/...) - the slug is the
    product's, and rewriting it would 404
  - any nousresearch.com link, which points at the host that actually
    serves the docs, the portal and the model catalogue

What changes is the sentence around them: who is credited with building
the product.
"""
import pathlib, re, subprocess

FILES = [
    "README.md", "README.es.md", "README.zh-CN.md", "README.ur-pk.md",
    "CONTRIBUTING.md", "CONTRIBUTING.es.md",
    "website/docs/index.mdx",
    "website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/index.mdx",
    "website/docs/developer-guide/prompt-assembly.md",
]

# Displayed-prose patterns only. Each must not span a URL.
PAIRS = [
    # badge alt/label
    (re.compile(r"Built%20by-Nous%20Research"), "Built%20by-Neural%20Studios"),
    # markdown link text
    (re.compile(r"\[Nous Research\]\(https://nousresearch\.com\)"),
                  "[Neural Studios](https://nousresearch.com)"),
    # bare prose
    (re.compile(r"built by Nous Research"),        "built by Neural Studios"),
    (re.compile(r"Built by Nous Research"),        "Built by Neural Studios"),
    (re.compile(r"created by Nous Research"),      "created by Neural Studios"),
    (re.compile(r"Created by Nous Research"),      "Created by Neural Studios"),
    # discord label (the URL itself is left intact by the URL guard below)
    (re.compile(r"\[Nous Research Discord\]"),     "[Kova Discord]"),
]

changed = []
for f in FILES:
    p = pathlib.Path(f)
    if not p.exists():
        continue
    s = p.read_text(encoding="utf-8", errors="replace")
    orig = s
    for rx, rep in PAIRS:
        s = rx.sub(rep, s)
    if s != orig:
        p.write_text(s, encoding="utf-8")
        changed.append(f)
print(f"updated {len(changed)} files:")
for c in changed:
    print("  ", c)
