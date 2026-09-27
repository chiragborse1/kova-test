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
