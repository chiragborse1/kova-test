import subprocess, re, collections
out = subprocess.run(["git","grep","-ohI","-E","https?://[a-zA-Z0-9._-]+","--","."],
                     capture_output=True,text=True,encoding="utf-8",errors="replace").stdout
hosts = collections.Counter(l.split("//",1)[1].split("/")[0] for l in out.split("\n") if "//" in l)
print("distinct hosts:", len(hosts))
internal = [h for h in hosts if "nousresearch" in h]
print("\n=== nousresearch hosts this repo depends on ===")
for h in sorted(internal): print(f"  {hosts[h]:5}  {h}")
print(f"\n=== {len(hosts)-len(internal)} third-party hosts ===")
for h,n in sorted(((h,n) for h,n in hosts.items() if h not in internal), key=lambda x:-x[1])[:10]:
    print(f"  {n:5}  {h}")
