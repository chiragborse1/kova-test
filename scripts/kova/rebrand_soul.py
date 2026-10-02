"""Credit Neural Studios in the agent's OWN identity strings.

These are the highest-value strings in the repo: they are the system
prompt the agent speaks to the model, and the SOUL files it is told to
adopt. If the agent says "I was built by Nous Research", the rebranding
has not actually reached the product's voice.

Only the attribution clause moves. The rest of each prompt is behaviour
and must not be touched.
"""
import pathlib, re

TARGETS = [
    "SOUL.md",
    "docker/SOUL.md",
    "agent/prompt_builder.py",
    "kova_cli/default_soul.py",
    "website/scripts/generate-llms-txt.py",
    "website/docs/developer-guide/prompt-assembly.md",
    "website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/developer-guide/prompt-assembly.md",
    "website/docs/user-guide/features/personality.md",
    "website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/personality.md",
]

PAIRS = [
    (re.compile(r"built by Nous Research"),        "built by Neural Studios"),
    (re.compile(r"created by Nous Research"),      "created by Neural Studios"),
    (re.compile(r"Built by Nous Research"),        "Built by Neural Studios"),
    (re.compile(r"Created by Nous Research"),      "Created by Neural Studios"),
]

changed = []
for f in TARGETS:
    p = pathlib.Path(f)
    if not p.exists():
        print("  missing:", f)
        continue
    s = p.read_text(encoding="utf-8-sig", errors="replace")
    orig = s
    for rx, rep in PAIRS:
        s = rx.sub(rep, s)
    if s != orig:
        p.write_text(s, encoding="utf-8")
        changed.append(f)
print(f"updated {len(changed)} files:")
for c in changed:
    print("  ", c)
