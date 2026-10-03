"""Restore the nousresearch provider alias the rebrand turned into openkova.

agent/*, kova_cli/* and the nous provider plugin all accept three spellings
of the Nous provider: "nous", "nous-portal" and one more. Upstream's third
was "nousresearch" - the organisation's name. The blanket
nousresearch -> openkova rule rewrote it, so a config that says

    provider = nousresearch

no longer matches, and the agent falls through to a different API mode.

Unlike branding, this is a VALUE users write into their config, so both
spellings are accepted: the original so existing configs keep working, and
"openkova" because it is what the rebrand already put in the tree and any
config written against this fork may use it.

Usage:  python scripts/kova/fix_provider_alias.py [--check]
"""
import pathlib, subprocess, sys

SITES = [
    "agent/agent_init.py",
    "agent/agent_runtime_helpers.py",
    "agent/auxiliary_client.py",
    "agent/auxiliary_reasoning_floor.py",
    "agent/chat_completion_helpers.py",
    "kova_cli/model_switch.py",
    "kova_cli/models_reasoning_caps.py",
    "kova_cli/providers.py",
    "plugins/model-providers/nous/__init__.py",
]
OLD = '{"nous", "nous-portal", "openkova"}'
NEW = '{"nous", "nous-portal", "nousresearch", "openkova"}'
OLD_TUPLE = '("nous-portal", "openkova")'
NEW_TUPLE = '("nous-portal", "nousresearch", "openkova")'

changed = []
for f in SITES:
    p = pathlib.Path(f)
    if not p.exists():
        continue
    s = p.read_text(encoding="utf-8-sig")
    orig = s
    s = s.replace(OLD, NEW).replace(OLD_TUPLE, NEW_TUPLE)
    if s != orig:
        changed.append(f)
        if "--check" not in sys.argv:
            p.write_text(s, encoding="utf-8")

print(("would update" if "--check" in sys.argv else "updated") + f" {len(changed)} files")
for c in changed:
    print("  ", c)
