# doggett — Learnings

## Project Context (seeded 2026-06-05)
- **Project:** Android GSA Client Service Health Check
- **User:** salonijain619 (Saloni)
- **Stack:** Investigation/SRE squad for the GSA Android client.
- **Client repo:** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android (VSTS-gated; mirror `WD.Client.Android-icm-copilot` cloned locally with `agent-docs/`)
- **Telemetry clusters:** `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Android client, ADX); `naas-idsharedwus` + `naas-idsharedscus` (server-side); `aria-prod` (cross-checks, GUID `f0eaa94222894be599b7cd0bc1e2ed6f`); `androidgsa.eastus.kusto.windows.net / Metric` (perf rollups, unverified).
- **Onboarding doc:** https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **ICM team:** https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- **Report channel:** IDNA GSA → Livesite - Client (Teams), tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
- **Sister squads:** Windows (win_client_investigation_squad), Mac (HarryPotter)

## Summarized history (full archive → `history-archive.md`)

Prior entries (2026-06-05 through 2026-06-08) summarized to archive. See `history-archive.md` for HP ICM discovery, icm-queue-ingest skill authoring, and orchestration work.

## Current learnings (active)

### 2026-06-10T13:15Z — README four-sections port + Teams workflow scaffold

**Headline:** Ported four operational README sections (Quick Start / Where reports go / Daily Cadence / Manual Invocation) from Mac HarryPotter into Android README.md (new file). Mac repo inaccessible (404); used checkpoint-004 cached structure as fallback — structural alignment with Mac unverified. Scaffolded `.github/workflows/daily-livesite-report.yml` with `workflow_dispatch` + commented cron `0 14 * * 1-5`, Teams post step gated on `MOBILE_LIVESITE_TEAMS_WEBHOOK` secret (not yet created by Saloni).

**Files written:**

| File | Status | Notes |
|---|---|---|
| `README.md` | ✅ Created | Four sections + intro/overview + agent cast table |
| `.github/workflows/daily-livesite-report.yml` | ✅ Created | Scaffold; cron commented out; generator is placeholder |
| `.squad/decisions/inbox/doggett-mac-readme-inaccessible.md` | ✅ Created | Documents Mac repo inaccessibility + fallback approach |
| `.squad/decisions/inbox/doggett-teams-webhook-setup.md` | ✅ Created | Teams webhook gap + Saloni setup steps |

**Four README sections written (Android-adapted):**

1. **Quick Start** — Python venv prereqs, `gh` CLI, `agency` CLI (ICM/Entra one-time auth), Kusto access (`wdgvsoprod.westus.kusto.windows.net` + `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB`), Microsoft Defender Play Store API access (Frohike/Langly).

2. **Where Reports Go** — Local: `daily-livesite-report-android-YYYY-MM-DD.md` at repo root. Per-agent research drops under `.squad/agents/*/research/`. Teams: Livesite - Mobile Client channel with full metadata (Group ID, Tenant ID, Channel/thread ID, deep-link). Webhook gap noted.

3. **Daily Cadence** — Proposed cron `0 14 * * 1-5` (09:00 ET weekdays). Open-items callout: GitHub Actions cron not yet wired (known squad backlog). Cadence table: Langly first, then Scully (NAAS + ICM), then Frohike (Play Vitals NAAS-as-a-unit), then Reyes assembles. Lookback windows documented (7d rolling for all sources; Active ICMs: no dateRange per D-138).

4. **Manual Invocation (Copilot CLI)** — Single-agent pulls for Langly, Scully, Frohike, ICM. Full team-mode `gh copilot suggest` invocation. Squad session prompts. Notes on NAAS-as-a-unit framing rule, ICM auth prereq, Play Console access.

**GitHub Actions workflow scaffold:**
- `workflow_dispatch` (manual) with optional `report_date` input.
- `schedule:` cron block commented out (`0 14 * * 1-5`).
- Steps: checkout → Python setup → install deps → resolve date → generate report (placeholder) → post to Teams (`${{ secrets.MOBILE_LIVESITE_TEAMS_WEBHOOK }}`) → commit report.
- Graceful degradation: if `MOBILE_LIVESITE_TEAMS_WEBHOOK` not set, skip Teams post (exit 0).
- `TODO(saloni):` comments throughout covering webhook creation, secret storage, cron activation, report-generator build, ICM service-principal auth for CI.

**Teams webhook gap:**
- Channel deep-link captured; NOT the incoming webhook URL (secret in Mac HP repo — not derivable).
- `MOBILE_LIVESITE_TEAMS_WEBHOOK` must be created by Saloni (Incoming Webhook connector OR Power Automate flow on the channel, then stored as GH Actions secret).
- Mac HP pattern: secret by name in `daily-report.yml` (exact secret name not visible from Mac repo; assumed analogous pattern). Android mirrors this with `MOBILE_LIVESITE_TEAMS_WEBHOOK`.

**NAAS-as-a-unit framing applied throughout:** All CLI prompts, README sections, and workflow comments treat NAAS as one unit per the squad-wide hard rule.

**Did NOT do (per task rules):** committed nothing (Scribe's job); spawned no sub-agents; did not invent Mac README content (honest gap documented); did not hardcode webhook URL.

**Open items handed back to coordinator:**
1. Mac README structural alignment — unverified (Mac repo inaccessible). Low risk: content is correct.
2. Cron schedule `0 14 * * 1-5` proposed — needs Saloni/Mulder confirmation vs Mac's schedule.
3. `MOBILE_LIVESITE_TEAMS_WEBHOOK` secret — Saloni must create (blocking for automated Teams posts).
4. Report-generator build — placeholder step in workflow; Squad CLI not yet built.
5. ICM collector CI auth — `agency mcp icm` needs service-principal path for unattended CI runs.
6. Commit step in workflow — confirm Scribe vs auto-commit preference.


### 2026-06-10T14:46Z — Report generator orchestrator skeleton (Mulder §1–§8)

**Headline:** Built `tools/report_generator/` orchestrator skeleton per Mulder's 465-line architecture decision. 19/19 tests pass (8 pre-existing Reyes assembler tests + 11 new). `python -m tools.report_generator.cli --dry-run --date 2026-06-10` exits 0. `--validate-only` against the existing 06-10 report passes all 9 invariants.

## Learnings

**Orchestrator threading model.** Implemented Mulder's 3-wave model in `orchestrator.py`:
- Wave 1 (serial): Langly only — provides `live_play_version` into `ctx["prior_results"]` before downstream framing rules run.
- Wave 2 (`concurrent.futures.ThreadPoolExecutor(max_workers=3)`): Scully + Frohike + Skinner submitted concurrently; results collected via `as_completed`; per-future timeout enforced with `future.result(timeout=SECTION_TIMEOUT_S=300s)`. Stdlib-only, I/O-bound work — threads are correct (GIL irrelevant). Avoided asyncio per Mulder's anti-decision.
- Wave 3 (serial): Reyes' assembler — the only producer whose failure becomes `AssemblyError` and exits 1. All other producer failures are absorbed into `Status.FAIL` and the report still ships.
- Fail-soft backstop: `_invoke_producer` catches `Exception` last-resort, converts to `SectionResult(status=FAIL, errors=[...])`. Producers SHOULD catch their own per contract, but the orchestrator never lets a raise escape Wave 1/2.
- Duck-typing: accept producers that define their own local `SectionResult` fallback class (assembler does this; Langly did too). Re-hydrate by attribute, not isinstance. Necessary because producer modules land before/after `contracts.py` in a multi-agent codebase.

**Exit-code conventions** (per Mulder §1, wired in `cli.py`):
- `0` — report assembled (PARTIAL/SKIP sections are still success per fail-soft).
- `1` — `AssemblyError` (Reyes raised, file unwritable) OR validation failure (unless `--no-fail-on-validation`).
- `2` — reserved for `--fail-fast` (not yet wired; documented placeholder).
- `3` — bad `--date`, unknown `--skip-sections` token, mutually exclusive flags.

**Validation invariants** (9 from Mulder §8, in `validation.py`):
1. File exists at `--output`.
2. Size in `[5_000, 30_000]` bytes (06-10 is 25,489; 06-05 is 14,495 — band accommodates both).
3. H1 matches `^# .*[Dd]aily [Ll]ivesite [Rr]eport`.
4. Langly version line (`📱 **Defender for Android — Live on Play Store`) present in first 5 non-empty lines.
5. `## Executive Summary` present.
6. ≥1 markdown table of ≥3 consecutive rows.
7. `## Contributors` footer present.
8 + 9 (folded into one regex sweep): no `{date}` / `{TBD` / `{{` / `}}` / `/Users/` substrings.
- Writes `runs/{date}/validation.json` for post-run triage.
- Regression anchor test reads the committed `daily-livesite-report-android-2026-06-10.md` and asserts zero failures — if that ever flips, validation is wrong, not the report.

**Parallel-agent observations:** Scully/Frohike/Langly are writing concurrently. My stubs at `sections/scully_server_telemetry.py` and `sections/frohike_play_vitals.py` were wiped between two consecutive runs by another agent's write. Fail-soft caught it (ModuleNotFoundError → Status.FAIL → report still produced). This is exactly what the spec demands; no action needed.

**File inventory shipped:**
- `tools/report_generator/{__init__,__main__,cli,contracts,config,orchestrator,validation}.py`
- `tools/report_generator/sections/{__init__,scully_server_telemetry,frohike_play_vitals,skinner_icm}.py` (langly_version pre-existed; not touched)
- `tools/report_generator/tests/{test_orchestrator,test_cli,test_validation}.py`
- `requirements.txt` (pyyaml)
- `.gitignore` (+ `tools/report_generator/runs/`)
- `.github/workflows/daily-livesite-report.yml` — replaced placeholder echo with `python -m tools.report_generator.cli --date ... --output ...`; switched deps install to `-r requirements.txt`; cron stays disabled per the "manual workflow_dispatch first" rule.

**Did NOT touch:** `assembler.py` (Reyes), `sections/langly_version.py` (Langly). Stubs for Scully/Frohike are intentionally minimal SKIP returns — they overwrite freely.

---

### 2026-06-10 — Repo restructure (Option A): AHS is now its own git repo

**Root cause of the workflow invisibility (the bug Saloni hit when `gh workflow run` returned 404):**
The git root was `/Users/salonijain/workspace`, not the AHS project. That workspace-level git tracked AHS as a subdirectory and pushed `AndroidHealthCheckService/` as a top-level folder to `salonijain619/AndroidHealthCheckService`. GitHub Actions only scans `.github/workflows/` at the **repo root**, so the file at `AndroidHealthCheckService/.github/workflows/daily-livesite-report.yml` was invisible to Actions. The webhook was fine; the workflow definition simply did not exist as far as GitHub was concerned.

**Safety-belt pattern used for the destructive restructure:**
1. **Local bundle** of the workspace git before any change (`git bundle create --all`) — at `/Users/salonijain/workspace/.ahs-backups/ahs-workspace-backup-*.bundle`. Stored under the workspace dir (NOT `/tmp` — runtime forbids `/tmp` writes; the original plan said `/tmp`, we relocated).
2. **Remote backup branch** at the exact malformed SHA, created via `gh api -X POST .../git/refs` BEFORE the force-push. Branch: `pre-restructure-backup-2026-06-10` → `02e0434`. Recoverable forever with `git fetch origin pre-restructure-backup-2026-06-10`.
3. **`--force-with-lease=master:<expected-sha>`** on the push. Refuses to overwrite if someone else pushed in the meantime. The lease succeeded — remote was still at `02e0434`.

**New workflow Saloni should use:**
- `cd AndroidHealthCheckService && git ...` — the AHS project is now its OWN git repo whose root IS the project. No more `git -C /Users/salonijain/workspace ...` for AHS work.
- The workspace-level git at `/Users/salonijain/workspace` still exists for Saloni's other purposes, but its remote was renamed `origin` → `OLD-DO-NOT-USE-ahs` to prevent accidentally pushing the malformed layout back. It no longer tracks AHS contents (committed `Untrack AHS — …`).

**One gotcha during execution (and the workaround):**
The active `gh` token had scopes `gist, read:org, repo` but NOT `workflow`. The first `git push` was rejected with `refusing to allow an OAuth App to create or update workflow ... without 'workflow' scope`. Workaround:
- Amended the restructure commit to exclude `.github/workflows/daily-livesite-report.yml`, pushed everything else (succeeded — remote master is now `53ae74b`, the flat-root restructure).
- Re-added the workflow file as a SEPARATE local commit `b49e573` on master. It is **committed locally but unpushed**.
- Saloni needs to run interactively: `gh auth refresh -h github.com -s workflow` and then `cd AndroidHealthCheckService && git push origin master`. After that push, the workflow becomes visible to Actions and `gh workflow run` will work.

So: visibility is one `git push` away, blocked only on a token-scope refresh that requires Saloni's browser. Everything else (restructure, backup branch, local bundle, workspace cleanup, tests) is done.
