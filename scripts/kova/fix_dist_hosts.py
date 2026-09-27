import pathlib
# These dist/ bundles are COMMITTED and not gitignored, so they ship with the
# product and their doc links are user-facing. fix_hostnames.py skips dist/
# because it assumes build output is regenerated; these two are checked in.
for f in ["plugins/kanban/dashboard/dist/index.js",
          "plugins/kova-achievements/dashboard/dist/index.js"]:
    p = pathlib.Path(f)
    s = p.read_text(encoding="utf-8")
    n = s.count("openkova.com")
    s = s.replace("kova-agent.openkova.com", "hermes-agent.nousresearch.com")
    s = s.replace("openkova.com", "nousresearch.com")
    p.write_text(s, encoding="utf-8")
    print(f"{f}: {n} -> nousresearch.com")
