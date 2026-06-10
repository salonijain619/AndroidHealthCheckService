# Android GSA Service Health Check

> **Repo:** `AndroidHealthCheckService`
> **Squad:** Android GSA Service Health Check (X-Files cast)
> **Owner:** Saloni Jain
> **ICM Queue:** [106961 — GSA Client - Android](https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961)

This repo houses the daily livesite health-check process for the **Global Secure Access (GSA) Android
client** (`com.microsoft.scmx`). The squad monitors server-side NAAS telemetry, Google Play Vitals
crash/ANR rates, active ICM incidents, and the currently shipping Play Store version — synthesizing
everything into a single daily Markdown report posted to the **Livesite - Mobile Client** Teams channel.

**Agent cast (X-Files):**

| Agent | Role |
|---|---|
| **Scully** | Server-side NAAS telemetry (Kusto/ADX) |
| **Frohike** | Google Play Vitals crash/ANR analysis (NAAS-as-a-unit) |
| **Langly** | Play Store version tracker (`com.microsoft.scmx`) |
| **Reyes** | Report assembly (fuses Scully + Frohike + Langly + ICM) |
| **Skinner** | ICM incident-process narrative |
| **Doggett** | Android/backend architecture, integration |
| **Mulder** | Cross-domain analysis, escalation |
| **Scribe** | Git commit + session log |

---

## Quick Start

### Prerequisites

1. **Python 3.11+** with a virtual environment:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install pyyaml
   ```

2. **`gh` CLI** (GitHub CLI) — needed for GitHub Actions dispatch and MCP invocations:
   ```bash
   brew install gh && gh auth login
   ```

3. **Microsoft `agency` CLI** — required for ICM ingest via `agency mcp icm`:
   - Expected location: `/Users/<you>/.config/agency/CurrentVersion/agency`
   - **One-time interactive Entra auth:** run `agency mcp icm` once in a terminal and complete the
     browser flow. The token caches via AzureAuth; subsequent runs are unattended.
   - Confirm your corp identity has **read access** on ICM team **106961** (`GSA Client - Android`).
   - See `.squad/skills/icm-queue-ingest/SKILL.md` for the full ICM integration reference.

4. **Kusto / ADX access** — two clusters required:
   - **NAAS server-side:** `wdgvsoprod.westus.kusto.windows.net` (corp network / VPN required)
   - **Android client telemetry:** `mdatpandroidcluster.westus2.kusto.windows.net` / db `MDATPAndroidDB`
   - Auth via corp SSO (`az login` or Entra interactive in Kusto Explorer / `kqlmagic`).
   - See `.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md` for the canonical KQL catalog.

5. **Microsoft Defender Play Store API access** — for Frohike (Play Vitals) and Langly (Play Store version):
   - Google Play Console access to `com.microsoft.scmx` (Play Vitals + Play Reporting).
   - Skill reference: `WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`.
   - Optional: wire the `google-play-reporting-server` MCP for automated rollout-% pulls
     (see decisions.md — Langly open item).

6. **VPN / corp network** — required for both Kusto clusters and `icm-mcp-prod.azure-api.net`.

### Running a report manually (today)

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. First-time only: complete ICM Entra auth (opens a browser tab; ~30 seconds)
agency mcp icm

# 3. Run the ICM collector directly (optional standalone check)
python3 tools/icm/icm_collector.py --team-id 106961 --timeout 60

# 4. Trigger a full report via Copilot CLI squad prompt
#    (see "Manual Invocation" section below)
```

> ⚠️ **ICM auth note:** Step 2 is a one-time action per machine. After the first successful Entra
> browser flow, `agency mcp icm` runs unattended from cached tokens.

---

## Where Reports Go

### Local (repo root)

Daily reports are written to the repo root as:

```
daily-livesite-report-android-YYYY-MM-DD.md
```

Examples:
- `daily-livesite-report-android-2026-06-10.md`
- `daily-livesite-report-android-2026-06-09.md`

Per-agent **research drops** (raw collector output, intermediate KQL results, Play Vitals data) land
under each agent's research directory:

```
.squad/agents/<agent>/research/
```

Key research paths:

| Agent | Research path | Contents |
|---|---|---|
| Scully | `.squad/agents/scully/research/` | NAAS Kusto query results, anomaly analysis |
| Frohike | `.squad/agents/frohike/research/naas-crashes-YYYY-MM-DD.md` | Play Vitals NAAS crash/ANR pulls |
| Langly | `.squad/agents/langly/research/play-store-versions.md` | Current Play Store production version |
| Doggett | `.squad/agents/doggett/research/` | ICM port plans, Android architecture notes |
| Skinner | `.squad/agents/skinner/research/` | ICM incident narratives |

### Teams: Livesite - Mobile Client

The assembled daily report is posted to the **Livesite - Mobile Client** Teams channel:

| Field | Value |
|---|---|
| Channel name | Livesite - Mobile Client |
| Group ID | `a3312108-40d2-4d8d-a401-066749108606` |
| Tenant ID | `72f988bf-86f1-41af-91ab-2d7cd011db47` |
| Channel (thread) ID | `19:uDpMueKuWUKAMPQ1RO5qOzAL_R8Dq-ZJrXTUPxM63ZY1@thread.tacv2` |
| Deep-link | [Open in Teams](https://teams.microsoft.com/l/channel/19%3AuDpMueKuWUKAMPQ1RO5qOzAL_R8Dq-ZJrXTUPxM63ZY1%40thread.tacv2/Livesite%20-%20Mobile%20Client?groupId=a3312108-40d2-4d8d-a401-066749108606&tenantId=72f988bf-86f1-41af-91ab-2d7cd011db47&ngc=true) |

> ⚠️ **Webhook setup required (action for Saloni):** Automated posting requires an **Incoming Webhook URL**
> stored as GitHub Actions secret `MOBILE_LIVESITE_TEAMS_WEBHOOK`. The deep-link above is for human
> navigation only — it cannot post messages. See the
> [Teams Integration](#teams-integration) section and
> `.squad/decisions/inbox/doggett-teams-webhook-setup.md` for step-by-step setup.

---

## Daily Cadence

> ⚠️ **Open item — GitHub Actions cron not yet active:** The workflow scaffold exists at
> `.github/workflows/daily-livesite-report.yml` with the cron **commented out**. Two blockers must
> be resolved first: (1) the report-generator step is a placeholder (Squad CLI not yet built), and
> (2) `MOBILE_LIVESITE_TEAMS_WEBHOOK` secret has not been created. See
> `.squad/decisions/inbox/doggett-teams-webhook-setup.md`. Until then, reports are generated
> **manually** (see [Manual Invocation](#manual-invocation-copilot-cli) below).

### Proposed schedule

| Event | Time | Trigger |
|---|---|---|
| Automated daily report | **09:00 ET weekdays** (`0 14 * * 1-5` UTC) | GitHub Actions cron *(pending activation)* |
| Manual on-demand | Anytime | `workflow_dispatch` or Copilot CLI |

### What runs each cycle

Each daily report cycle runs the following steps in sequence:

1. **Langly** pulls the current Play Store production version of `com.microsoft.scmx`
   (anchors all per-version crash analysis as "customer-facing" vs "internal ring").
2. **Scully** queries NAAS server-side telemetry (`wdgvsoprod.westus.kusto.windows.net`, 7-day
   rolling window) and pulls active ICM incidents for team 106961.
3. **Frohike** pulls Google Play Vitals crash/ANR data — NAAS-as-a-unit; per-version table is the
   primary deliverable (see decisions.md: framing rule).
4. **Reyes** assembles the final report, leading with Langly's Play Store version header (see
   decisions.md: "Lead every daily/weekly report with Langly's Play Store version header").
5. Report is written to `daily-livesite-report-android-YYYY-MM-DD.md` at repo root.
6. Report is posted to the **Livesite - Mobile Client** Teams channel via
   `${{ secrets.MOBILE_LIVESITE_TEAMS_WEBHOOK }}`.

### Lookback windows

| Source | Window |
|---|---|
| Scully — NAAS server telemetry | 7 days rolling |
| Frohike — Play Vitals crash/ANR rates | 7 days rolling |
| Scully — ICM Active incidents | All open (no `dateRange` — per D-138 port from Mac HP) |
| Scully — ICM mitigated highlights | 7 days rolling |

---

## Manual Invocation (Copilot CLI)

Use these prompts to trigger a report manually from the GitHub Copilot CLI. Ensure you are in
the `AndroidHealthCheckService` repo directory with your virtual environment active.

### Single-agent pulls

```bash
# Pull current Play Store version (Langly) — run first; anchors all per-version analysis
gh copilot suggest "Langly, pull the current Play Store production version of com.microsoft.scmx"

# Pull NAAS server-side telemetry (Scully) — 7-day window
gh copilot suggest "Scully, pull today's NAAS server-side telemetry for the Android daily livesite report — 7-day window, cluster wdgvsoprod.westus.kusto.windows.net"

# Pull Play Vitals crash and ANR data (Frohike) — NAAS-as-a-unit
gh copilot suggest "Frohike, pull today's NAAS crash and ANR data from Google Play Vitals for com.microsoft.scmx — NAAS-as-a-unit, per-version table is the primary deliverable"

# Pull active ICM incidents (Scully + Skinner) — team 106961
gh copilot suggest "Scully, pull active ICM incidents for team 106961 (GSA Client - Android) and surface any on-call schedule"
```

### Full team-mode invocation (daily report)

```bash
# Trigger a full daily livesite report — all agents in parallel, Reyes assembles
gh copilot suggest "Run the Android GSA daily livesite report for today: Langly pull the current Play Store version of com.microsoft.scmx, Scully pull NAAS server-side telemetry and active ICMs for team 106961, Frohike pull NAAS crash and ANR data from Play Vitals as a unit, then Reyes assemble the report leading with Langly's version header and post to the Livesite - Mobile Client Teams channel"
```

### Squad session prompts (conversational, inside a Copilot CLI session)

```
"Scully, pull the daily livesite report data for today"
"Frohike, what are the top NAAS crash clusters from Play Vitals this week?"
"Langly, is com.microsoft.scmx on the latest Play Store production version?"
"Reyes, assemble today's Android livesite report from Scully's and Frohike's latest research drops"
"Run the full squad daily report cycle for 2026-06-10"
```

> **Notes:**
> - Replace `2026-06-10` with today's actual date.
> - NAAS data must always be reported as one unit — do not request per-component NAAS breakdown.
> - ICM pulls require `agency mcp icm` Entra auth to be completed at least once interactively.
> - Play Vitals pulls require Google Play Console access to `com.microsoft.scmx` (Frohike + Langly).

---

## Teams Integration

See [Where Reports Go → Teams: Livesite - Mobile Client](#teams-livesite---mobile-client) above for
the channel deep-link, Group ID, Tenant ID, and Channel (thread) ID.

Automated posting uses the GitHub Actions workflow at `.github/workflows/daily-livesite-report.yml`,
which posts via the secret:

```
${{ secrets.MOBILE_LIVESITE_TEAMS_WEBHOOK }}
```

**This secret must be created by Saloni before automated posting works.** See
`.squad/decisions/inbox/doggett-teams-webhook-setup.md` for:
- How to create an Incoming Webhook or Power Automate flow on the channel.
- How to store the resulting URL as the `MOBILE_LIVESITE_TEAMS_WEBHOOK` GitHub Actions secret.
- How to activate the cron schedule once the secret and report-generator are both ready.

> # TODO(saloni): verify section ordering + structure against Mac HarryPotter README once accessible
> (see `.squad/decisions/inbox/doggett-mac-readme-inaccessible.md` — Mac repo was unreachable during
> this authoring pass on 2026-06-10; content is Android-correct but structural alignment with Mac
> README is unverified).
