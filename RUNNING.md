# Running and testing Kova Agent

Everything below was executed on this machine to confirm it works. Commands
are PowerShell from the repository root (`C:\Users\chira\kova-agent`).

## 0. One-time setup

The virtualenv is already created. To rebuild it from scratch:

```powershell
cd C:\Users\chira\kova-agent
$env:UV_LINK_MODE = "copy"          # avoids a hardlink error on Windows
uv sync --frozen --python 3.14 --extra all --group dev `
        --extra anthropic --extra mistral --extra fal `
        --extra modal --extra daytona --extra parallel-web
```

That extra list is not decorative. It is copied from `.github/workflows/tests.yml`
and is what makes the suite collectible. A bare `uv sync` leaves aiohttp,
anthropic and acp uninstalled, which produces 62 collection errors that look
like broken code but are only missing packages.

Set `PYTHONPATH` in this shell before anything that imports the project:

```powershell
$env:PYTHONPATH = "."
```

Without it you get `ModuleNotFoundError: kova_cli` even though the package is
installed, because the project is not pip-installed into the venv - it is run
from the source tree.

## 1. Run the CLI

```powershell
.\.venv\Scripts\python.exe -m kova_cli.main --version
```

Expected:

```
Kova Agent v0.21.5+3579.gfde60de (2026.9.24) - upstream 6f7a7991 - local fde60dec (+28 carried commits)
```

The `(+28 carried commits)` is this fork's work on top of upstream, and
`Kova Agent` in the banner is the rebrand working.

Start an interactive chat (needs an API key configured - see section 4):

```powershell
.\.venv\Scripts\python.exe -m kova_cli.main chat
```

Useful commands that need no API key:

```powershell
.\.venv\Scripts\python.exe -m kova_cli.main --help
.\.venv\Scripts\python.exe -m kova_cli.main skin list
.\.venv\Scripts\python.exe -m kova_cli.main model --help
.\.venv\Scripts\python.exe -m kova_cli.main doctor
```

`skin list` should show `kova` registered as a builtin alongside the retained
upstream skins:

```
  kova             builtin  Kova violet - the brand identity
* default          builtin  Classic Kova - gold and kawaii
  ares             builtin  War-god theme - crimson and bronze
  ...
```

## 2. Run the tests

Fast, targeted, and the right default for iterating:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\kova_cli\test_skin_palettes.py -q -p no:cacheprovider
```

Whole suite, one subprocess per file, bounded parallelism:

```powershell
.\.venv\Scripts\python.exe scripts\run_tests_parallel.py -j 4
```

That is the runner CI uses. It is per-FILE isolation, so it is slower than
xdist but has no cross-file state leakage. On this machine a full run is
~42,000 tests and takes hours; use `-j 4` or lower.

### What will fail locally, and why

**53 collection errors are expected on Windows and are not your fault.**
They are `pwd` (38), `termios` (5) and `fcntl` (4) - Unix-only modules that
do not exist on Windows at all. The suite targets Linux; that is why CI runs
it there. Do not try to fix them.

**11 test files fail on this machine for environment reasons**, confirmed
identical on a pristine upstream checkout:

| file | result |
|---|---|
| `tests/test_kova_home_profile_warning.py` | 1 failed, 2 passed, 3 skipped |
| `tests/test_kova_logging.py` | 4 failed, 30 passed, 2 skipped |
| `tests/test_scratch_dir.py` | 1 failed, 4 passed, 12 skipped |
| `tests/test_live_system_guard.py` | 3 failed, 5 passed |
| `tests/agent/test_compression_budget_rearm.py` | 3 failed |
| `tests/agent/test_auth_provider_failover.py` | 1 failed, 2 passed |
| `tests/agent/test_api_max_retries_config.py` | 1 failed |
| `tests/agent/test_account_policy_block.py` | 1 failed, 2 passed |
| `tests/cron/test_lifecycle_guard_heredoc_walk.py` | 2 failed (Windows paths) |
| `tests/kova_cli/test_gateway_windows.py` | 1 failed (`schtasks`: access denied) |

The last two are the clearest example of the rule that mattered most in this
work: to find out whether a failure is yours, run it against a pristine
upstream worktree and compare. Same counts both sides means pre-existing.

```powershell
git worktree add -f --detach _regression\pristine 2a977be9
cd _regression\pristine; $env:PYTHONPATH = "."
..\..\.venv\Scripts\python.exe -m pytest tests\agent\test_kova_logging.py -q
git worktree remove --force _regression\pristine
```

## 3. The verification suite

These are the checks written for the rebrand. Each one answers a specific
question, and each is cheap:

```powershell
python scripts\kova\audit_residual.py     # every surviving "hermes" is justified
python scripts\kova\check_lock.py         # the lockfile moved no versions
python scripts\kova\check_mark.py         # the logo geometry is correct
python scripts\kova\check_contrast.py     # WCAG AA on the theme palette
python scripts\generate_icons.py --check  # all 36 icon targets generate
python scripts\kova\tsc_check.py          # no NEW type errors vs upstream
python scripts\kova\fix_repo_urls.py  --check
python scripts\kova\fix_hostnames.py  --check
python scripts\kova\fix_pascal.py     --check
```

All should print a clean result. `tsc_check.py` needs its one-off setup
first (`python scripts\kova\tsc_check.py --setup`, ~72 MB).

## 4. Talking to a model

The agent needs a provider key. The easiest path is the hosted portal, which
the code already speaks to:

```powershell
.\.venv\Scripts\python.exe -m kova_cli.main chat
```

and follow the OAuth prompt, or set a key directly for any OpenAI-compatible
provider:

```powershell
$env:OPENAI_API_KEY = "sk-..."
.\.venv\Scripts\python.exe -m kova_cli.main chat --provider openai -m gpt-4o
```

`--provider nous` uses the Nous Portal, which is free-tier and needs no key.

## 5. The graphical apps

These need `npm install` first, which is a large download - expect several
minutes and a few GB:

### Web dashboard

```powershell
npm install
npm run build --workspace web
.\.venv\Scripts\python.exe -m kova_cli.main dashboard
```

The command is `dashboard` (port 9119); `kova dashboard --stop` shuts it
down again. `serve` is a different thing - the headless JSON-RPC/WebSocket
backend the desktop app talks to, which never opens a browser.

### Terminal UI (Ink)

```powershell
npm install
npm run build --workspace ui-tui
.\.venv\Scripts\python.exe -m kova_cli.main --tui
```

### Desktop app (Electron)

```powershell
cd apps\desktop
npm install
npm run dev
```

This is the one surface that has never been run in this environment - it is
Electron and there is no display server here. It type-checks cleanly
(`tsc_check.py`) but **has not been visually verified**. The theme change is
confined to `apps/shared/src/theme-presets.ts` and the two preset files, so
it is a small blast radius, but treat the layout as unproven until you look
at it.

## 6. Where things live

| what | where |
|---|---|
| why the old fork's CI was red | `FINDINGS.md` |
| rebrand engines + fixers | `scripts/kova/` |
| theme palette (single source of truth) | `apps/shared/src/theme-presets.ts` |
| desktop theme wrapper | `apps/desktop/src/themes/presets.ts` |
| CLI skins | `kova_cli/skin_engine.py` |
| the logo | `assets/kova/kova-mark-*.svg` |
| fork provenance | `NOTICE`, `LICENSE` |

## 7. Day-to-day

```powershell
git add -A
git commit -m "..."
git push kova-test HEAD:main
```

Two things that will bite you again:

- Do not re-clone with `--depth 1`. A shallow repo cannot be pushed; the
  remote needs the parent of the boundary commit. `git fetch --unshallow`.
- Large pushes reset over HTTPS on a flaky link. This repo is configured
  with `http.postBuffer 1GB` and `http.lowSpeedLimit 0` already.
