import pathlib
files = ["tests/kova_cli/test_gateway.py",
         "tests/kova_cli/test_gateway_start_attestation.py",
         "tests/kova_cli/test_gateway_windows.py",
         "tests/kova_cli/test_legacy_launchers_windows_live.py",
         "website/docs/user-guide/messaging/index.md",
         "website/docs/user-guide/windows-native.md"]
for f in files:
    p = pathlib.Path(f)
    s = p.read_text(encoding="utf-8")
    n = s.count("Hermes_Gateway")
    if n:
        p.write_text(s.replace("Hermes_Gateway", "Kova_Gateway"), encoding="utf-8")
        print(f"{f}: {n}")
