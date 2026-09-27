import pathlib, re
FILES = ["agent/prompt_builder.py", "flake.nix"]
PAIRS = [
    (re.compile(r"\(by Nous Research\)"),      "(by Neural Studios)"),
    (re.compile(r"framework by Nous Research"), "framework by Neural Studios"),
]
for f in FILES:
    p = pathlib.Path(f)
    if not p.exists(): continue
    s = p.read_text(encoding="utf-8", errors="replace"); o = s
    for rx, rep in PAIRS: s = rx.sub(rep, s)
    if s != o:
        p.write_text(s, encoding="utf-8"); print("updated", f)
