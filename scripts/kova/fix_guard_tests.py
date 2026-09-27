import pathlib
p = pathlib.Path("tests/cron/test_lifecycle_guard_heredoc_walk.py")
s = p.read_text(encoding="utf-8")
n = s.count("hermes gateway restart")
s = s.replace("hermes gateway restart", "kova gateway restart")
p.write_text(s, encoding="utf-8")
print(f"updated {n} fixture command(s) to the real binary name")
