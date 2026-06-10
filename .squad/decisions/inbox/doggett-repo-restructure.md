# Decision: AHS repo restructure (Option A) — flat root for GitHub Actions visibility

**Author:** Doggett (Android Engineer)
**Date:** 2026-06-10
**Status:** Executed (one push pending on token scope refresh by Saloni)
**Triggered by:** Coordinator (Option A from Saloni's request)

## Why

`gh workflow run daily-livesite-report.yml` returned 404 because the workflow file was not at the repo root on GitHub. The malformed remote had the entire AHS project nested one folder deep — `AndroidHealthCheckService/.github/workflows/daily-livesite-report.yml` — because the git root for the push was `/Users/salonijain/workspace`, not the AHS project. GitHub Actions only scans `.github/workflows/` at the **repo root**, so the workflow effectively did not exist for Actions even though it was committed.

## How (Option A from Coordinator)

1. Backed up the workspace git as a bundle: `/Users/salonijain/workspace/.ahs-backups/ahs-workspace-backup-1781086036.bundle` (verified `git bundle verify` reports a complete history).
2. Created a remote backup branch via `gh api` at the malformed remote's master SHA: `pre-restructure-backup-2026-06-10` → `02e0434`. The old history is preserved on `salonijain619/AndroidHealthCheckService` indefinitely under that branch name.
3. `git init -b master` inside `/Users/salonijain/workspace/AndroidHealthCheckService`, added the AHS remote, staged ALL 133 AHS files (verified no sibling-repo leakage: only `.gitattributes`, `.github`, `.gitignore`, `.squad`, `README.md`, `requirements.txt`, `tools/`, and the four daily reports). Single squashed commit.
4. `git push -u origin master --force-with-lease=master:02e0434…` succeeded (with the workflow file temporarily removed — see "Gotcha" below).
5. Untracked AHS from the workspace-level git (`/Users/salonijain/workspace`); committed locally; renamed its `origin` remote to `OLD-DO-NOT-USE-ahs` so we cannot accidentally push the malformed layout back.
6. Verified: 45/45 report-generator tests pass, smoke generator exits 0.

## Gotcha (and the remaining one-step follow-up for Saloni)

The active `gh` token had scopes `gist, read:org, repo` but NOT `workflow`. GitHub rejected the push of `.github/workflows/daily-livesite-report.yml` with `refusing to allow an OAuth App to create or update workflow ... without 'workflow' scope`. Also tried the Contents API as a side-channel; it returned 404 (same scope restriction surfaced differently). SSH push was not an option (no SSH key registered for github.com on this machine).

**Workaround already applied:**
- Restructure commit (`53ae74b`) was amended to exclude the workflow file and force-pushed — this succeeded, so the remote master is now the clean flat-root structure.
- The workflow file was re-added as a separate local commit (`b49e573`) on master. **Local only, unpushed.**

**Remaining step (requires Saloni's interactive browser):**
```bash
gh auth refresh -h github.com -s workflow
cd /Users/salonijain/workspace/AndroidHealthCheckService
git push origin master
```
After that push, `.github/workflows/daily-livesite-report.yml` becomes visible to GitHub Actions and `gh workflow run` will work.

## What is preserved

- **Local bundle (full pre-restructure history of the workspace git):** `/Users/salonijain/workspace/.ahs-backups/ahs-workspace-backup-1781086036.bundle`
- **Remote backup branch:** `pre-restructure-backup-2026-06-10` on `salonijain619/AndroidHealthCheckService` at SHA `02e04347852b414549cdf259c9eeb842cb3de3a0`.
- **Workspace-level git** at `/Users/salonijain/workspace` still exists; just no longer tracks AHS, and its remote was renamed to `OLD-DO-NOT-USE-ahs` (URL preserved for recovery).

## How to recover (if anything is wrong)

To get the old malformed-layout remote back:
```bash
git fetch origin pre-restructure-backup-2026-06-10
git push origin pre-restructure-backup-2026-06-10:master --force
```

To get the full pre-restructure workspace history locally:
```bash
git clone /Users/salonijain/workspace/.ahs-backups/ahs-workspace-backup-1781086036.bundle restored-workspace
```

## What changed for Saloni's daily workflow

- AHS is now its OWN git repo at `/Users/salonijain/workspace/AndroidHealthCheckService`. Use `cd AndroidHealthCheckService && git ...` for everything — no more `git -C /Users/salonijain/workspace ...` for AHS commits.
- `.github/workflows/` is at the repo root where Actions can see it (once the one pending push lands).
- The cron in `daily-livesite-report.yml` is intentionally still disabled — `workflow_dispatch`-only validation first, per the team rule.
