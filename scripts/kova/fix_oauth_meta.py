import json, pathlib
p = pathlib.Path("website/static/oauth/client-metadata.json")
d = json.loads(p.read_text(encoding="utf-8-sig"))
# client_id and logo_uri are the OAuth client's identity. They must resolve to
# a document that actually exists, or the dynamic-client-registration flow the
# app performs cannot complete. The rebrand pointed them at an invented
# openkova.github.io host, which 404s; the upstream host serves the real file.
d["client_id"]  = "https://nousresearch.github.io/hermes-agent/docs/oauth/client-metadata.json"
d["logo_uri"]   = "https://nousresearch.github.io/hermes-agent/docs/img/logo.png"
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("client_id / logo_uri -> the host that serves them")
