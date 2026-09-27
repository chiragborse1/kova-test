# Running the CLI and the desktop app locally

Short version. The 42k-test suite is not involved in either of these.

---

## CLI  (works right now, no install)

```powershell
cd C:\Users\chira\kova-agent
$env:PYTHONPATH = "."

.\.venv\Scripts\python.exe kova --version
.\.venv\Scripts\python.exe kova skin list
.\.venv\Scripts\python.exe kova chat
```

`kova` (no .py) is the repo's launcher wrapper and is the nicest entry point.
`python -m kova_cli.main ...` is exactly equivalent.

`$env:PYTHONPATH = "."` is required. The project is not pip-installed into
the venv, it runs from the source tree, so without it you get
`ModuleNotFoundError: kova_cli`.

Other things that need no API key:

```powershell
.\.venv\Scripts\python.exe kova doctor
.\.venv\Scripts\python.exe kova model --help
.\.venv\Scripts\python.exe kova dashboard --stop
```

---

## Desktop app (Electron)

### Before you start: free up disk

```
Free now: 2,511 MB
```

`node_modules` is currently only partially installed - 786 packages, 811 MB,
and **electron itself is missing**. A complete install needs roughly another
2-3 GB. On 2.5 GB free this will very likely fail partway.

Free space first. The quickest wins on this machine:

```powershell
# npm cache is usually the largest safe reclaim
npm cache clean --force

# the previous fork's leftovers, already verified as dead clones
# (only if you still have them; they were removed earlier)
```

Or just make sure you have ~6 GB free before continuing.

### Install

Dependencies are hoisted to the **repo root**, not to `apps/desktop`. This is
not optional - `scripts/assert-root-install.mjs` refuses to build otherwise,
and it is the difference between a clear error message and a confusing vite
failure.

```powershell
cd C:\Users\chira\kova-agent
npm ci
```

`npm ci` (not `npm install`) because `package-lock.json` is committed and you
want exactly the pinned tree.

### Run

```powershell
cd C:\Users\chira\kova-agent\apps\desktop
npm run dev
```

That starts two processes via `concurrently`:

- `dev:renderer` - vite dev server on http://127.0.0.1:5174
- `dev:electron` - waits for the renderer, then launches Electron pointed at it

The Python backend is found automatically: `source-python.ts` looks for
`.venv\Scripts\python.exe` at the repo root, which already exists. If it ever
fails, override it explicitly:

```powershell
$env:KOVA_DESKTOP_PYTHON = "C:\Users\chira\kova-agent\.venv\Scripts\python.exe"
npm run dev
```

### Build a production renderer only (no Electron)

Faster, and enough to check that the theme compiles:

```powershell
cd C:\Users\chira\kova-agent\apps\desktop
npm run build
```

### Web dashboard (lighter than the desktop app)

No Electron, so no 2-3 GB Electron download:

```powershell
cd C:\Users\chira\kova-agent
npm install
npm run build --workspace web
.\.venv\Scripts\python.exe kova dashboard        # port 9119
.\.venv\Scripts\python.exe kova dashboard --stop
```

---

## What "works" looks like

You are looking for **violet**, not gold. The shipped default was a GitHub
VS Code fork with a blue accent; the Kova default is the violet `kova` theme.

- Desktop: window chrome in violet `#6d3bf5` (light) / `#9d7bff` (dark)
- Sidebar/user bubbles tinted violet
- The mark: three arcs around a solid core, in the app icon
- `kova skin list` shows `kova` marked with `*` when active

If you see blue-grey chrome and gold terminal accents, the default did not
switch - that is upstream's `nous` skin, and `/skin kova` in the CLI fixes it.

---

## Common failures

| symptom | cause | fix |
|---|---|---|
| `ModuleNotFoundError: kova_cli` | `PYTHONPATH` unset | `$env:PYTHONPATH = "."` |
| desktop: "run npm ci from the repo root" | deps not hoisted | `npm ci` at repo root, not `apps/desktop` |
| desktop: vite cannot resolve an import | partial `node_modules` | `npm ci` at repo root |
| `ENOSPC` during npm install | 2.5 GB free is not enough | free ~6 GB first |
| Electron opens then exits | no GPU/display | try `npm run preview` to see the UI in a browser |
| gateway/doctor says python missing | wrong interpreter | set `KOVA_DESKTOP_PYTHON` |

---

## Fast tests (not the 42k suite)

If you want a quick regression check that runs in seconds:

```powershell
python scripts\kova\audit_residual.py     # every surviving "hermes" is justified
python scripts\kova\check_lock.py         # lockfile moved no versions
python scripts\kova\check_mark.py         # logo geometry
python scripts\kova\check_contrast.py     # WCAG AA on the palette
python scripts\generate_icons.py --check  # 36 icon targets
```

And a single fast test file:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\kova_cli\test_skin_palettes.py -q -p no:cacheprovider
```

---

## Honest note

The desktop app has **never been launched in this environment** - it is
Electron and there is no display server here. The theme change is confined to
`apps/shared/src/theme-presets.ts` and the two preset files, and the code
type-checks clean, but the rendered result is unverified. You are the first
person to see it; if something looks wrong, that is genuinely new
information, not a known issue.
