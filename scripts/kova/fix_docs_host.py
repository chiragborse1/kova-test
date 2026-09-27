"""Point the docs/install host at the subdomain that actually exists.

The rebrand renamed the subdomain along with the product, producing
kova-agent.nousresearch.com. That host does not resolve - DNS NXDOMAIN -
so every docs link, badge and install instruction broke.

  kova-agent.nousresearch.com      NXDOMAIN
  hermes-agent.nousresearch.com   HTTP 200 (/docs/ and /install.sh too)

The subdomain is upstream's infrastructure, not our branding: it is the
site that serves the documentation and the install script this fork
still points at. Only the label around it is ours.
"""
import subprocess, sys

OLD = "kova-agent.nousresearch.com"
NEW = "hermes-agent.nousresearch.com"

SKIP_DIRS = ("node_modules/", ".venv/", "_salvage/", "_regression/",
             "website/build/", "website/.docusaurus/")
BINARY_EXT = (".png", ".jpg", ".jpeg", ".ico", ".icns", ".webp", ".gif",
              ".woff", ".woff2", ".ttf", ".tflite", ".whl", ".jar", ".zip",
              ".mp4", ".webm", ".pdf")

files = [f for f in subprocess.run(["git", "ls-files", "-z"], capture_output=True,
                                   text=True, check=True).stdout.split("\0") if f]
changed = []
for rel in files:
    n = rel.replace("\\", "/")
    if any(d in n for d in SKIP_DIRS) or n.lower().endswith(BINARY_EXT):
        continue
    try:
        raw = open(n, "rb").read()
    except OSError:
        continue
    if b"\0" in raw[:4096]:
        continue
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        continue
    if OLD not in text:
        continue
    new = text.replace(OLD, NEW)
    changed.append(n)
    if "--check" not in sys.argv:
        open(n, "wb").write(new.encode("utf-8"))

verb = "would rewrite" if "--check" in sys.argv else "rewrote"
print(f"{verb} {len(changed)} files")
for c in changed[:10]:
    print("  ", c)
