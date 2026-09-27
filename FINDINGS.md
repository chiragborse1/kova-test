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

=====================================================================
BRAND MARK + ICON PIPELINE
=====================================================================

THE MARK
  assets/kova/kova-mark-{black,white}.svg - three thick arc segments
  120 deg apart orbiting a solid core. Reads as a camera iris / aperture.
  scripts/kova/make_mark.py generates both variants plus PNG previews
  from one geometry definition, so they cannot drift.

  Tuning was done against RENDERED output, not source numbers. At the
  first-pass ring (330/250) the arms read as thin slivers beside the
  core once composited on the squircle; the ring is now 330/226 (104
  thick) with the core 118 -> 96, and sweep 30 -> 34 deg. Verified in
  the light and dark 256px marks and at 32px, where the gaps between the
  arms are what keep it legible instead of collapsing into a blob.

FOUR REAL PIPELINE BUGS FOUND (all by rendering, not by reading)

  1. The generator lifts art with a regex taking only the FIRST
     self-closing <path>. The first mark used 3 paths + a circle, so two
     arms vanished from every generated icon. The glyph is now a single
     path element with four subpaths.

  2. Arc sweep flags were inverted. SVG's y axis points down, so
     increasing angle is sweep-flag 0; the generator hardcoded 1/0. That
     drew the arms the long way round the circle.

  3. GIRL_VIEWBOX was 5487.0615 - the old character art's canvas. It
     normalises the rasterised alpha bbox back into SVG units, so the
     1024-grid mark would have been scaled 10.7x. Now 1024.

  4. drag_bottom_nodes() stretches the artwork's lowest nodes down so a
     portrait stands on the plate. A centred glyph has no bottom edge;
     it dragged the lower arm out of the tile. Now opt-in (JOIN_BOTTOM).

  Also switched xMidYMax -> xMidYMid (ART_ALIGN): portraits are
  bottom-anchored, a centred glyph is not.

VERIFICATION
  generate_icons.py --check   : all 36 targets generate + pass
  scripts/kova/check_mark.py : 1 path element, 3 arms on r=330/226,
                                core anchored at its top point
  10/10 WCAG AA contrast pairs : pass
  3953 tracked .ts/.tsx       : 4 errors, all pre-existing upstream

  There is still no SVG rasteriser on this machine (cairosvg needs a
  native cairo that is not installed), so the mark is validated
  numerically rather than by round-tripping through an SVG renderer.
  resvg-py IS available and is what generate_icons.py uses, so the
  pipeline itself renders for real - it was the composition step, not
  rasterisation, that was broken.

=====================================================================
REGRESSION HUNT (running the suite, not reading the diff)
=====================================================================

The rebrand was verified by grep. Running the suite against a pristine
2a977be9 worktree found three real defects that grep could not.

1. tests/test_packaging_metadata.py  ->  StopIteration
   pyproject's project name became kova-agent; uv.lock still said
   hermes-agent. Could not simply re-lock: `uv lock` failed with
   "Repository not found" because the rebrand had ALSO rewritten

     misaki[en] @ git+https://github.com/OpenKova/misaki.git@f03fd2b

   That is not our repo. Upstream maintains a fork of the misaki TTS
   package in their own org to raise its Python cap. Restored to
   NousResearch/misaki, then `uv lock` succeeded. scripts/kova/
   check_lock.py asserts the refresh moved nothing: 330 -> 330
   packages, zero version changes, only hermes-agent -> kova-agent.

2. 240 files with dead repository URLs
   The rebrand collapsed NousResearch/Hermes-Agent to the bare string
   "github.com/kova-agent", which names a GitHub USER, not an
   owner/repo pair. ~300 links were dead. scripts/kova/fix_repo_urls.py
   rewrites them to chiragborse1/kova-test, preserving each path.

3. agent/transports/codex.py::_RESERVED_TOOL_ALIAS_PREFIX = "hermes_"
   The rebrand's pattern needed a character AFTER "hermes", and this
   constant ENDS with the underscore, so it was missed. Its neighbours
   had moved (the xAI alias is already kova_web_search) and the tests
   already expected kova_<name>, so the wire alias map disagreed with
   itself.
     pristine: test_auxiliary_client.py 219 passed
     branch:   test_auxiliary_client.py 215 passed, 4 failed
   Now 219 passed, matching upstream exactly.

4. cron/lifecycle_guard.py - SECURITY RELEVANT
   The guard blocks the agent from killing/restarting its own gateway.
   Its patterns still matched \bhermes while its own comments already
   said "kova-gateway", so after the rename the block stopped matching
   the process it protects. A control that fails open is worse than one
   that is absent, because it still looks present in review.
   Fixed, plus the Windows scheduled-task name (Hermes_Gateway ->
   Kova_Gateway), which also names the .cmd/.vbs files written into the
   user's Startup folder.

5. ~900 dead links from an INVENTED DOMAIN
   The rebrand mapped nousresearch.com -> nousresearch.com host-wide.
   Nobody owns that domain: 347 files pointed docs, install scripts,
   badges and the Nous Portal OAuth endpoints at nothing. There is no
   Kova-hosted site, so scripts/kova/fix_hostnames.py maps them back to
   the host that actually serves the content. PREPARED, NOT APPLIED -
   held for review rather than landed unreviewed.

METHOD THAT FOUND THESE
  Run the failing test against a pristine worktree of the base commit.
  Same counts on both sides = pre-existing. Different counts = ours.
  Every "is this my fault?" question in this project was answered that
  way rather than by reasoning about the diff.

  Confirmed pre-existing (identical on pristine 2a977be9):
    test_hermes_home_profile_warning  1 failed, 2 passed, 3 skipped
    test_hermes_logging               4 failed, 30 passed, 2 skipped
    test_scratch_dir                  1 failed, 4 passed, 12 skipped
    test_live_system_guard             3 failed, 5 passed
    test_compression_budget_rearm      3 failed
    test_auth_provider_failover        1 failed, 2 passed
    test_api_max_retries_config        1 failed
    test_account_policy_block          1 failed, 2 passed
    lifecycle_guard heredoc-walk       2 failed  (Windows path handling)
    gateway_windows schtasks live      1 failed  (access denied)

COLLECTION
  53 collection errors before the rebrand, 53 after - identical causes
  (pwd/termios/fcntl are Unix-only and cannot exist on Windows; CI runs
  the suite on Linux). The rebrand introduced ZERO new collection
  failures.

=====================================================================
INVENTED-INFRASTRUCTURE SWEEP (final)
=====================================================================

The rebrand applied two blanket rules that were right for branding and
wrong for anything that has to RESOLVE:

  nousresearch.com  -> openkova.com
  github.com/NousResearch -> github.com/kova-agent

Neither target exists. Verified live, not assumed:

  https://openkova.com
    HTTP 200 - but the page is
    "OpenKova.com for sale | Spaceship.com"
    A domain squatter's parking page.

  https://kova-agent.openkova.com
    DNS NXDOMAIN. Does not resolve at all.

So 921 references across 351 files were pointing users, OAuth clients
and the docs site at a parking page or at nothing.

WHAT WAS ACTUALLY BROKEN
  347 files   docs links, README badges, install instructions
  212 refs    portal.openkova.com - including the billing URL in
              agent/billing_links.py and the "out of credits" message
              shown to a user mid-conversation
   28 files   website pages linking the portal
   18 files   tests asserting the portal host
  oauth       client-metadata.json client_id + logo_uri 404'd.
              client_id is the OAuth client's identity, so the dynamic
              client registration at login could not complete.

A SECOND PASS caught what the first missed: after rewriting
openkova.com -> nousresearch.com, the subdomain was still wrong.
kova-agent.nousresearch.com is also NXDOMAIN, because the rebrand had
renamed the subdomain along with the product. Only the original
hermes-agent.nousresearch.com serves /docs/ and /install.sh.

FINAL HOST MAP (all verified HTTP 200)
  openkova.com                -> nousresearch.com
  portal.openkova.com         -> portal.nousresearch.com
  kova-agent.openkova.com     -> hermes-agent.nousresearch.com
  kova-agent.nousresearch.com -> hermes-agent.nousresearch.com
  openkova.github.io          -> nousresearch.github.io

There is no Kova-hosted infrastructure, and inventing another name
would repeat the same bug, so links point at what actually serves the
content until Kova runs its own.

THIRD PASS: the same rule damaged an IDENTIFIER
  The Nous provider accepts three spellings. Upstream's third was
  "nousresearch" (the org name); the rename turned it into "openkova"
  in all nine places the alias set is written. A config saying
  `provider = nousresearch` stopped matching. Both spellings are now
  accepted - the original so existing configs work, "openkova" because
  this tree already shipped it.

  Same class as the misaki URL: a rule that is correct for our own repo
  and wrong for anything that merely CONTAINS the org's name.

  Verified: all four spellings resolve; provider tests 74 passed.

CHECKS THAT NOW RUN
  scripts/kova/check_lock.py        lock refresh moved no versions
  scripts/kova/check_mark.py        mark geometry
  scripts/kova/check_contrast.py    WCAG AA on the palette
  scripts/kova/audit_hosts.py       every host the repo references
  scripts/kova/fix_repo_urls.py     --check finds 0 product files
  scripts/kova/fix_hostnames.py     --check finds 0 files
  scripts/kova/fix_provider_alias.py --check finds 0 files
