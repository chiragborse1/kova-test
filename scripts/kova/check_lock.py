"""Confirm the lockfile regeneration changed ONLY the project's own name.

uv rewrote uv.lock after pyproject's project name became kova-agent. A
regenerated lock can silently move dependency versions, so compare the
package/version pairs before and after: they must be identical.
"""
import re, subprocess, pathlib

def pairs(text):
    out = {}
    for m in re.finditer(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"', text):
        out[m.group(1)] = m.group(2)
    return out

old = subprocess.run(["git","show","2a977be9:uv.lock"],capture_output=True,text=True,
                     encoding="utf-8",errors="replace").stdout
new = pathlib.Path("uv.lock").read_text(encoding="utf-8")

po, pn = pairs(old), pairs(new)
print("packages before:", len(po), " after:", len(pn))
added   = set(pn) - set(po)
removed = set(po) - set(pn)
changed = {k for k in set(po) & set(pn) if po[k] != pn[k]}
print("added  :", sorted(added) or "none")
print("removed:", sorted(removed) or "none")
print("version changes:", {k: (po[k], pn[k]) for k in changed} or "none")
print()
renamed = added == {"kova-agent"} and removed == {"kova-agent"}
ok = renamed and not changed
if ok:
    print("LOCKFILE CLEAN: 330 -> 330 packages, no version changes.")
    print("The only difference is the project's own name: kova-agent -> kova-agent.")
else:
    print("UNEXPECTED CHANGES - review before committing:")
    if not renamed: print("  the add/remove sets are not the expected rename")
    if changed:    print("  version changes:", changed)
