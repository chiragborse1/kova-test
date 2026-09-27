KOVA AGENT — REBUILD PLAN
Generated: 2026-09-27 05:26
=====================================================================

## 1. CI FAILURE ROOT CAUSE (why the project was dropped)

The failing workflow is 'Install & Update E2E' -> job 'Pick release tags':
    error: no release tags found in /home/runner/work/kova/kova
    ##[error]Process completed with exit code 1.

CAUSE: A GitHub fork does NOT inherit upstream git tags. Upstream's
release pipeline (scripts/sandbox/pick-release-tags.sh) assumes tags
exist. On the fork it dies immediately. This is infrastructure, not
your code. It has been failing on a ~12h schedule since at least
Sept 24, failing every single run.

The repo carries 30-34 workflows inherited from upstream, most of which
are release/publish/e2e plumbing irrelevant to a fork. The fix is to cut
CI down to a small trustworthy set, NOT to fix failing tests.

## 2. LOCAL REGRESSION BASELINE (previous attempt's data, salvaged)

From tools/rebrand/gate*_report.txt:
    upstream baseline : 29710 tests, 522 already failing
    previous attempt  :  8968 tests, 413 failing, 225 NEWLY broken

KEY INSIGHT: 522 tests fail on PRISTINE upstream hermes. A green build is
not the target. The target is <= 522 failures and ZERO newly-broken.

The 225 newly-broken were almost all rebrand collateral, e.g.:
  - skills/autonomous-ai-agents/kova-agent -> dangling related_skills
    (the rename moved a skill dir but not its references)
  - tool alias renames: 'kova_search_files' vs 'search_files'
  - model-family detection: 'nousresearch/hermes-4-405b' no longer matches
  - transport registries returning None (bedrock/anthropic lookup broken
    because a module path was renamed out from under the registry)
  - CLI skin color/symbol assertions (frozen literals not updated)

FIX: rename tokens in ONE ordered pass, then fix references, then diff
failure sets against the upstream baseline. Never eyeball test counts.

## 3. DISK IS THE BLOCKING CONSTRAINT

C: drive: 510 GB used, ~520 MB FREE. Cloning is impossible right now.
5 stale clones occupy ~13.3 GB:
  AppData\Local\kova\hermes-agent      5,273 MB  (live install, venv+node_modules)
  kova-neon-ui                        3,485 MB  (ORPHANED worktree - see below)
  AppData\Local\KovaAgent\kova-agent  3,163 MB  (renamed clone install)
  Projects\kova                       1,119 MB  (dev clone, has rebrand engine)
  Projects\kova-old-ref                 226 MB  (stale duplicate)

## 4. ORPHANED WORKTREE (would have been lost silently)

kova-neon-ui/.git contains:
    gitdir: C:/Users/chira/kova-agent-new/.git/worktrees/kova-neon-ui
Parent repo 'kova-agent-new' NO LONGER EXISTS. This is a 3.5 GB dead
worktree - git commands there all fail with 'not a git repository'.
It still holds: tools/rebrand/ (regression harness), theme presets,
and the neon theme work. SALVAGED to _salvage/ before any deletion.

## 5. SALVAGE INVENTORY (already saved to C:\Users\chira\kova-agent\_salvage)

  _salvage/rebrand_tools/  18 files  (regression harness + gate reports)
  _salvage/rebrand_engine/  3 files  (your rebrand engine, mjs+py)
  _salvage/neon_ui/         6 files  (theme presets, tui textInput, banner)
  _salvage/*.txt                     (dry-run outputs)

## 6. PROPOSED PHASES

P0  Disk + clone
    - delete 5 stale clones above (needs your approval - irreversible)
    - shallow clone upstream -> C:\Users\chira\kova-agent
    - single clean 'Initial commit', no upstream history, no
      contributors/, no .mailmap

P1  CI triage (the thing that killed you last time)
    - delete all upstream release/publish/e2e workflows
    - keep a minimal set: lint, unit tests, js tests
    - pin CI to the 522-failure baseline; gate on NEWLY-broken == 0

P2  Rebrand
    - re-run salvaged rebrand engine, ONE ordered pass
    - then sweep: dangling skill refs, tool aliases, model-family strings,
    transport registries, CLI skin literals
    - verify by diffing failure set vs baseline, not by eyeballing

P3  UI
    - new shell, not a recolor (see notes)

P4  Publish
    - single squashed commit -> chiragborse1/kova-test

## 7. ATTRIBUTION / HISTORY - WHAT I WILL AND WON'T DO

WILL: new repo starts from one clean commit. No upstream commit history,
    no contributors/ dir, no .mailmap. MIT requires the copyright notice;
    it will live in LICENSE/NOTICE.

WON'T: treat 'hide the origin' as the goal. The fork is public; GitHub's
    network graph exposes the relationship regardless of history. UI is
    what users actually notice, and that is P3.
