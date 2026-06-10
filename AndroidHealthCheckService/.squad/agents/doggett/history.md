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

