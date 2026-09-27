import pathlib
targets = ["kova_cli/gateway.py", "kova_cli/gateway_windows_legacy.py"]
for f in targets:
    p = pathlib.Path(f)
    s = p.read_text(encoding="utf-8")
    n = s.count("Kova_Gateway")
    s = s.replace("Kova_Gateway", "Kova_Gateway")
    p.write_text(s, encoding="utf-8")
    print(f"{f}: {n} occurrence(s) -> Kova_Gateway")
