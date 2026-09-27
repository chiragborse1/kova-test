import pathlib, re

# cron/lifecycle_guard.py - a hard block that refuses to let the agent kill or
# restart its own gateway. The comments already say "kova-gateway" but the
# patterns still matched \bkova, so after the rebrand the guard no longer
# recognises the process it is supposed to protect: the block silently stops
# matching and the bypass it closes reopens. A security control that fails
# open is worse than one that is absent, because it looks present.
p = pathlib.Path("cron/lifecycle_guard.py")
s = p.read_text(encoding="utf-8")
before = s
s = s.replace(r"\bkova[.\-]?gateway", r"\bkova[.\-]?gateway")
s = s.replace(r"\bkova\b[^\n]*\bgateway", r"\bkova\b[^\n]*\bgateway")
s = s.replace(r"\bgateway\b[^\n]*\bkova", r"\bgateway\b[^\n]*\bkova")
p.write_text(s, encoding="utf-8")
print("lifecycle_guard.py patterns updated" if s != before else "NO CHANGE")

# Session/instance id prefixes: these are opaque identifiers we mint ourselves.
for f, old, new in [
    ("plugins/platforms/dingtalk/adapter.py", 'f"kova_{uuid.uuid4().hex[:12]}"', 'f"kova_{uuid.uuid4().hex[:12]}"'),
    ("tools/browser_camofox.py", 'f"kova_{uuid.uuid4().hex[:10]}"', 'f"kova_{uuid.uuid4().hex[:10]}"'),
    ("tools/environments/singularity.py", 'f"kova_{uuid.uuid4().hex[:12]}"', 'f"kova_{uuid.uuid4().hex[:12]}"'),
]:
    q = pathlib.Path(f)
    t = q.read_text(encoding="utf-8")
    if old in t:
        q.write_text(t.replace(old, new), encoding="utf-8")
        print(f"{f}: id prefix -> kova_")
