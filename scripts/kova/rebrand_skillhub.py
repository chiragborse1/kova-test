import pathlib
# User-facing installer panel text. Distinct from per-skill `author:` fields,
# which credit named individuals and their adapting org - those stay.
p = pathlib.Path("kova_cli/skills_hub.py")
s = p.read_text(encoding="utf-8-sig", errors="replace")
old = "This is an official optional skill maintained by Nous Research."
new = "This is an official optional skill maintained by Kova."
assert old in s
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("skills_hub.py: installer panel text -> Kova")

# The DESCRIPTION.md line describes the collection, not an individual author.
q = pathlib.Path("optional-skills/DESCRIPTION.md")
t = q.read_text(encoding="utf-8-sig", errors="replace")
o = t
t = t.replace("Official skills maintained by Nous Research",
              "Official skills maintained by Kova")
if t != o:
    q.write_text(t, encoding="utf-8"); print("optional-skills/DESCRIPTION.md updated")
