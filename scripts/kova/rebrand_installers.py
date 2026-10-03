import pathlib

# Product-facing attribution. Per-skill `author:` rows and third-party
# quotes are left alone: they credit named people and organisations for
# work that is genuinely theirs.
EDITS = [
    # Windows + POSIX installers - an ASCII box the user reads while installing
    ("scripts/install.ps1",
     "|  An open source AI agent by Nous Research.              |",
     "|  An open source AI agent by Neural Studios.              |"),
    ("scripts/install.sh",
     "\u2502  An open source AI agent by Nous Research.              \u2502",
     "\u2502  An open source AI agent by Neural Studios.              \u2502"),
    # the product's own bundled skill, describing the product
    ("skills/autonomous-ai-agents/kova-agent/SKILL.md",
     "Kova Agent is an open-source AI agent framework by Nous Research that",
     "Kova Agent is an open-source AI agent framework by Neural Studios that"),
    ("website/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-kova-agent.md",
     "Kova Agent is an open-source AI agent framework by Nous Research",
     "Kova Agent is an open-source AI agent framework by Neural Studios"),
    # a test fixture that pins a prompt string
    ("tests/agent/test_anthropic_adapter.py",
     "Kova Agent by Nous Research uses kova-agent skills. ",
     "Kova Agent by Neural Studios uses kova-agent skills. "),
    # third-party quote from a real user's post - leave as written by them
]

for f, old, new in EDITS:
    p = pathlib.Path(f)
    if not p.exists():
        print("  missing:", f); continue
    s = p.read_text(encoding="utf-8-sig", errors="replace")
    if old in s:
        p.write_text(s.replace(old, new), encoding="utf-8")
        print(f"  updated {f}")
    else:
        print(f"  NO MATCH in {f}: {old[:50]!r}")
