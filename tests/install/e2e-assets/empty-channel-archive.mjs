// Driver-side release-channel archive for the Windows install/update E2E:
// a loopback host that publishes NOTHING, started as a LIBRARY (importing, not
// executing, so the dev-launcher block never runs) and publishing its URL to a
// file for the shell driver to consume.
//
// Usage: node empty-channel-archive.mjs <url-file>
//   Writes "<url-file>" with the base URL (http://127.0.0.1:<port>) once
//   listening, then stays alive until SIGINT or SIGTERM.
//
// WHY: `kova update` resolves its channel origin from
// kova_cli.source_releases._PUBLIC_BASE ("https://assets.neuralstudio.in") and
// reads releases/channels/<name>.json from it. For a source install a MISSING
// `main` record is the normal case: release_channels turns a 404 into
// ChannelNotFound and resolve_source_target falls back to following the branch,
// which is what this suite asserts. Any other status (a Cloudflare challenge, or
// a 403 on a runner's datacenter egress) raises
// ChannelError("Channel read unavailable: HTTP <code>"), which has no fallback
// and fails the update leg.
//
// This driver otherwise fakes nothing -- see the "no MITM proxy, no network
// fakery" note in windows-e2e.ps1 -- so the update leg reached the live CDN and
// inherited its availability. tests/e2e/core/upgrade/network/_seed.py,
// apps/desktop/e2e/update/github-edge.ts and tests/e2e/core/windows_update all
// fake this same host; this is the fourth instance of the same edge.
//
// Nothing is published here and no main.json is created: the point is the
// deterministic 404, not a record.

// @ts-check
import fs from 'node:fs';
import http from 'node:http';
import process from 'node:process';

const urlFile = process.argv[2];
if (!urlFile) {
  console.error('usage: node empty-channel-archive.mjs <url-file>');
  process.exit(1);
}

/** Every path 404s: the "no record published" state, recorded for the log. */
const reads = [];
const server = http.createServer((req, res) => {
  reads.push(`${req.method} ${req.url}`);
  console.log(`[empty-channel-archive] 404 ${req.method} ${req.url}`);
  res.writeHead(404, { 'content-type': 'application/json', 'content-length': '0' });
  res.end();
});

server.listen(0, '127.0.0.1', () => {
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}`;
  fs.writeFileSync(urlFile, url);
  console.log(`[empty-channel-archive] listening at ${url}`);
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => {
    console.log(`[empty-channel-archive] ${signal}; ${reads.length} read(s)`);
    server.close(() => process.exit(0));
  });
}

// A background shell starts with stdin at EOF; signals own this lifetime.
await new Promise(() => {});
