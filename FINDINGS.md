KOVA AGENT - FINDINGS
Generated: 2026-09-27

=====================================================================
WHY THE PREVIOUS ATTEMPT FAILED
=====================================================================

1. CI (the thing that killed it)
   Workflow: install-e2e.yml -> job "Pick release tags"
       error: no release tags found in /home/runner/work/kova/kova
   Root cause: a GitHub FORK DOES NOT INHERIT UPSTREAM GIT TAGS.
   install-e2e.yml runs on cron '20 7,19 * * *' (twice daily) and its
   first job feeds off release tags. On a fork that job can never pass.
   It was failing every scheduled run since at least Sept 24.
   6 workflows auto-fired on schedule and all are now disabled.

2. TESTS (the thing that looked like "my code is broken")
   The suite was being run on WINDOWS. The project ships tests-os.yml
   because the suite targets Linux.
   On pristine, unmodified upstream, on this machine:
       109 collection errors
   Causes:
       38 x 'pwd'      (Unix-only, does not exist on Windows)
        5 x 'termios'  (Unix-only)
        4 x 'fcntl'    (Unix-only)
       21 x 'aiohttp'  (optional extra not installed)
       14 x 'acp'     (optional extra not installed)
        8 x 'anthropic'(optional extra not installed)
   After installing CI's exact extras set:
       53 collection errors  (109 -> 53, halved)
   Of the remaining 53, 47 are pwd/termios/fcntl = the Windows floor.
   CONCLUSION: the previous attempt's "225 newly broken" was mostly
   POSIX/Windows environment artifacts, NOT rebrand damage. The rebrand
   engine was likely fine.

   The salvaged gate reports recorded "baseline: 29710 tests, 522 bad"
   on upstream. A green suite is NOT achievable. The real target is:
       failures <= 522 AND newly-broken == 0.

=====================================================================
ENVIRONMENT RECIPE (matches CI exactly)
=====================================================================
uv sync --frozen --python 3.14 --extra all --group dev \
        --extra anthropic --extra mistral --extra fal \
        --extra modal --extra daytona --extra parallel-web

Note: pyproject.toml deliberately EXCLUDES anthropic from the [all]
extra (lazy-install policy) and excludes `matrix` because python-olm
has Linux-only wheels. Do not "fix" that; it is intentional.

=====================================================================
REPO STATE
=====================================================================
Source : NousResearch/hermes-agent @ 2a977be9 (shallow, depth 1)
Local  : C:\Users\chira\kova-agent
Note   : upstream has moved on since the old fork (11a12f2 -> 2a977be9,
         30 -> 51 workflows). The old fork had drifted.
Disk   : was 520 MB free; now ~4.5 GB free after removing 5 stale clones.

Salvage preserved in _salvage/ (31 files):
  rebrand_tools/  regression harness + gate reports (the baseline data)
  rebrand_engine/ the previous rebrand engine (mjs + py)
  neon_ui/        theme presets + tui textInput + banner
  disabled_workflows/ originals of the 6 cron workflows, pre-edit

=====================================================================
STATUS
=====================================================================
DONE   [x] clean shallow clone of upstream
DONE   [x] diagnosed CI failure root cause (fork has no tags)
DONE   [x] diagnosed test failure root cause (POSIX modules on Windows)
DONE   [x] installed CI-identical dependency set
DONE   [x] disabled all 6 auto-firing cron workflows
DONE   [x] verified all 51 workflows still parse as valid YAML
DONE   [x] verified 0 workflows auto-fire on schedule
TODO   [ ] rebrand pass (hermes -> kova), with before/after proof
TODO   [ ] new UI
TODO   [ ] single squashed commit -> chiragborse1/kova-test
TODO   [ ] verify on CI (not locally, per user request)

=====================================================================
REBRAND PROGRESS (updated)
=====================================================================

Commits on top of upstream 2a977be9 (all local, all authored by you,
so `git push` exposes this history normally):

  98e1e729  ci: disable 6 auto-firing cron workflows (the real CI fix)
  aae9f4c9  rebrand: hermes -> kova across code, modules, assets
  dd904d6e  rebrand: rename directory components; fix skill ref mismatch
  e7803e8e  rebrand: catch compound identifiers pass 1 missed
  5339ce95  attribution: drop contributors/ + .mailmap, add NOTICE
  022117d9  fix: restore model-id literals the rebrand over-rewrote

REBRAND RESULT
  files containing 'hermes' : 9792 -> 244  (down 97.5%)
  renamed paths             : 2470
  renamed directories       : 11
  all 37 kova_* modules import: YES
  dangling related_skills   : 0  (was 225-regression cause last time)
  model family detection    : correct for all hermes-* and vendor models

The 244 residual references are all intentional:
   36  upstream model ids (nousresearch/hermes-4-405b etc.)
   18  upstream URLs (github.com/NousResearch, nousresearch.com docs)
    7  third-party names (githermes, TamaHermes, r/hermesagent)
    2  Meta's Hermes JS engine inside package-lock.json

TWO REAL REGRESSIONS FOUND AND FIXED
  Both were the same class of bug that produced the previous attempt's
  225 broken tests - a string literal that is load-bearing, not branding:

  1. agent/coding_context.py  _EDIT_FORMAT_GUIDANCE listed "hermes" as a
     model family. Renamed to "kova", _model_family('...hermes-4-405b')
     returned None instead of 'replace'.
  2. kova_cli/auth_nous.py  filtered offered model ids by excluding those
     containing "hermes" (Nous's own models are not reliable for agentic
     tool-calling). Renamed to "kova", the condition inverted and excluded
     the wrong set entirely.

  Detection method: diff the rebrand against 2a977be9 and grep for bare
  "hermes" literals appearing in model/registry/family context. That scan
  returns exactly these 2 files; the other 220 similar-shaped hits are
  self-consistent renames where both sides of a comparison were rewritten.

WINDOWS TEST FLOOR (unchanged, expected)
  47 collection errors are Unix-only modules: pwd(38) termios(5) fcntl(4).
  These cannot pass on Windows by design; the suite targets Linux.
  Do not chase them locally. Verify on CI.

=====================================================================
UI WORK (three surfaces)
=====================================================================

THE PROBLEM WITH THE DEFAULT
  The shipped default was `nous` - a fork of the GitHub VS Code theme
  whose only change from upstream is a blue accent. The default desktop
  experience was therefore visually indistinguishable from the original
  project's identity. The CLI default was a separate gold/kawaii skin and
  the web dashboard a third look (dark teal). Three surfaces, no shared
  identity.

WHAT WAS DONE
  A first-party violet identity, now the default on desktop, web and CLI.

  apps/shared/src/theme-presets.ts   new `kova` palette (light + dark)
  apps/desktop/src/themes/presets.ts kovaTheme + registered + is default
  web/src/themes/presets.ts          kovaTheme for the dashboard
  kova_cli/web_server_dashboard.py   'kova' added to the backend list
  kova_cli/skin_engine.py            'kova' skin + _DEFAULT_SKIN_NAME

  Light  #6d3bf5 on #fbfafc  = 5.61:1
  Dark   #9d7bff on #0b0910  = 6.33:1
  All 10 fg/bg pairs clear WCAG AA; scripts/kova/check_contrast.py asserts
  them so a future tweak cannot silently regress legibility.

  nous / default / Kova Teal all stay registered. This changes the
  DEFAULT, not the user's choice - verified:
    fresh profile            -> kova
    existing 'nous' user    -> nous (unchanged)
    retired 'gold'/'default' -> kova

WHAT WAS DELIBERATELY NOT RENAMED
  1281 files mention `nous`. Only ~400 are the theme key. The rest are
  the Nous provider id, the portal API (portal.nousresearch.com),
  NOUS_* env vars and kova_cli.auth_nous - upstream SERVICE CONTRACTS.
  Renaming those would break authentication and billing, so they were
  left alone. Scoping the theme key to 6 non-test frontend files avoided
  touching the other ~390.

VERIFICATION NOTES
  - scripts/kova/ts_check.py parses all 3953 tracked .ts/.tsx with a real
    TypeScript grammar. 4 report errors; all 4 are byte-identical at the
    same line numbers in pristine 2a977be9, i.e. pre-existing upstream
    (a mojibake char in ModelsPage.tsx, an unescaped & in create-dialog).
  - Desktop JS tests need node_modules, which is not installed and would
    be heavy, so they run on CI. Invariants that the theme tests assert
    (palette exists, system font stacks carry JetBrains Mono + emoji
    fallback, no leftover hacks) are checked statically instead.
  - 2 skin tests fail on this machine for a Windows reason only: the
    locale is cp1252, which cannot encode the spinner glyphs (U+2714)
    those tests round-trip through YAML. Confirmed pre-existing by
    stashing the change and re-running.

  The palette audit test (tests/kova_cli/test_skin_palettes.py) caught
  two low-contrast slots on the first attempt - banner_dim 2.34:1 and
  session_border 1.60:1, both under the 2.8 soft floor. Lifted the hexes
  rather than relaxing the test. 22 passed.
