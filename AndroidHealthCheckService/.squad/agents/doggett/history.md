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

## Summarized history (full content → `history-archive.md`)

### 2026-06-05 — Initial Defender-for-Android discovery [SUMMARIZED]
VSTS blocker. Inventory plan drafted. 7 Android fields proposed. Error code mapping hypothesized. See archive.

### 2026-06-05T12:00:52Z — Bootstrap complete [SUMMARIZED]
Squad on Opus 4.7. Report template ready. Dashboard proposed. See archive.

### 2026-06-05T12:20:25Z — Canonical Android KQL pattern [SUMMARIZED]
Panel KQL executed. Filter reconciled. Version format confirmed. See archive.

### 2026-06-05 — Marketplace inventory [SUMMARIZED]
2 REFERENCE (toolkit + setup-prereqs). Conventions cataloged. Artifact: marketplace-plugin-inventory.md. See archive.

### 2026-06-05T12:40:00Z — App Insights confirmation cross-agent [SUMMARIZED]
Corroborated, but partially superseded by later MDATPAndroidDB finding. See archive.

## Current learnings (active)

### 2026-06-05 (final pass) — Defender-for-Android agent-docs ingested [SUMMARIZED]
Codebase grounded. Telemetry 3-layer model mapped. 4 resolved, 5 partial, 4 still blocked (VSTS-gated). **MAJOR CORRECTION:** Android telemetry Kusto-queryable via MDATPAndroidDB (not just App Insights REST). See archive.

## 2026-06-06T11:18Z — HarryPotter ICM-integration discovery + port plan

**Headline:** Reverse-engineered Mac's (HP squad's) ICM ingest end-to-end. **One backend:** `agency mcp icm` — Microsoft-internal `agency` CLI's stdio MCP proxy fronting ICMProd. **Auth:** Entra interactive browser on first run, AzureAuth-cached thereafter → unattended afterwards. No PAT / no `az` bearer / no webhook secret. HP's docs (`icm-via-mcp/SKILL.md` § History) record three dead-end alternatives (ICM REST + `az` token, hypothetical `icm-mcp-server` binary, `agency tool` subcommand) — keeping that history in the ported skill so we don't re-attempt.

**Verified `agency` is already on Saloni's machine:** `/Users/salonijain/.config/agency/CurrentVersion/agency`. ICMProd is NOT registered in her `~/.copilot/mcp-config.json` — irrelevant for the Python-subprocess path (the Copilot prefix `ICMProd-` only applies inside Copilot runtime).

**Key technical contract (port verbatim):**
- Handshake: `initialize` (60s) → `notifications/initialized` → `tools/list` → **sleep 6s** (`WARMUP_DELAY_S`) → `tools/call`. Skipping the sleep triggers upstream "A new session can only be created by an initialize request" race.
- Per-run sequence: `search_incidents`(states=Active,Mitigating, **no** dateRange) → `search_incidents`(states=Mitigated, sortBy LastModifiedDate Desc, no dateRange) → `get_on_call_schedule_by_team_id` → optional `get_ai_summary` per active Sev≤2 ICM.
- **D-138 lesson:** removing `dateRange.createdAfter` is critical — earlier HP versions silently dropped long-running open ICMs created >7d ago. Mirror the regression tests.
- `collect()` never raises — `source:"partial"` envelope on auth/CLI failure, banner renders in template.

**Port topology decision (no new agent):**
- New skill: `.squad/skills/icm-queue-ingest/SKILL.md` (port HP's `icm-via-mcp/SKILL.md`, swap team_id literal `115956→106961`).
- New script: `tools/icm_collector.py` (port HP's verbatim, swap defaults).
- Config knob: `.squad/config.json :: icm.team_id = 106961` (canonical, override hierarchy CLI > env `AHCS_ICM_TEAM_ID` > config > default).
- Scully runs the collector; Reyes extends the report template with `📟 On-Call Today` (replace TBD) and new `🚨 Active ICM Incidents` block (3 tables: Customer-Created Active / System-Created Active / Mitigated Highlights + Patterns bullets); Skinner owns narrative Patterns when live; Doggett owns the skill doc.

**v2 report-section shape:** 3 tables with columns `ICM ID | Sev | Age | Title | Status` (or `… | Mitigated` for mitigated); sort Active by `Severity Asc, CreatedDate Desc`, Mitigated by `LastModifiedDate Desc`; severity emoji prefix (🔴 Sev0/1, 🟠 Sev2, 🟡 Sev3, ⚪ Sev4, 🧪 TestICM-tagged surfaced not filtered); portal link template `https://portal.microsofticm.com/imp/v3/incidents/details/<id>/home`.

**Pre-reqs for Saloni (blockers for first live run):**
1. One interactive `agency mcp icm` invocation to complete Entra browser auth (one-time, ~30s).
2. Confirm her identity has read on ICM team `106961`.
3. Greenlight first live collector run under her creds.

**Worked this pass:**
- `agents/doggett/research/harrypotter-icm-port-plan.md` (full A–F).
- `decisions/inbox/doggett-harrypotter-icm-discovery.md` (decision = adopt HP pattern as `icm-queue-ingest` skill, confidence HIGH on pattern / MEDIUM on first-run UX, supersedes none).

**Did NOT do (per task hard rules):** ran no live ICM calls; spawned no sub-agents; committed nothing.

**Open questions parked for Saloni:** lookback window confirmation (7d default proposed), cross-team routing-rot check ids (95422 Windows + 115956 Mac?), AI-summary default on/off, final landing path for `tools/icm_collector.py` (top-level `tools/` vs new `androidlivesite/` package skeleton).

## 2026-06-06T11:25Z — Authored `icm-queue-ingest` skill

**Headline:** Turned the HP port-plan discovery into a durable team-knowledge skill so future Scully/Reyes/Skinner runs (and any future agent picking up ICM work) have one canonical reference. Skill doc is the operational summary; discovery doc remains the audit trail (linked, not duplicated).

**Output:** `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/skills/icm-queue-ingest/SKILL.md` (~17KB). Structure follows the existing `gsa-kusto-catalog-android-slice` shape (Owner / Confidence header + KNOW / DO / CHECK / Common Rationalizations / Red Flags + Citations + Evolution). Confidence chosen: **MEDIUM** — HP pattern is regression-tested (D-138 suite), but first live run against team `106961` lands today; promote to HIGH after one clean unattended cycle.

**Locked-in contract in the skill (the non-negotiables):**
- `agency mcp icm` stdio JSON-RPC; 5-step handshake including load-bearing `WARMUP_DELAY_S = 6`.
- 4 tools per run: `search_incidents` ×2 / `get_on_call_schedule_by_team_id` / optional `get_ai_summary` (Sev ≤ 2.5 + CRIs only — upstream restriction).
- **No `dateRange`** on either `search_incidents` call (D-138 regression discipline).
- Single source of truth for `team_id`: `.squad/config.json :: icm.team_id` with override hierarchy CLI > env `AHCS_ICM_TEAM_ID` > config > default. Hardcoding `106961` is a red flag.
- `collect()` never raises — `source: "partial"` envelope is the failure contract.

**Citations included** (HP audit lineage): `livesite/scripts/icm_collector.py`, `livesite/scripts/tests/test_icm_collector.py`, `.squad/skills/icm-via-mcp/SKILL.md`, `.squad/skills/mac-active-icm/SKILL.md`, HP template line ranges (15–28 on-call, 601–653 active ICMs).

**Decision dropped:** `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/decisions/inbox/doggett-icm-queue-ingest-skill-authored.md` ("Adopted: icm-queue-ingest skill formalizes HP-ported ICM collector pattern for team 106961. confidence: medium. supersedes: none.").

**Did NOT do (per task hard rules):** committed nothing (Scribe's job); spawned no sub-agents; did not duplicate the discovery doc; did not write/touch the collector code (Scully's port).

## 2026-06-08T16:23Z — Scribe: Orchestration log + multi-day arc summary

Scribe wrote orchestration logs for the 2026-06-06 spawn batch (4 entries: doggett-3, doggett-4, scully-4, reyes-1) and a session log covering the HP discovery → skill authoring → collector port → v2 report arc. Mulder and Skinner flagged for cross-team review on: (1) new `icm-queue-ingest` skill (confidence MEDIUM, promote to HIGH after second clean cycle), (2) team 106961 queue-identity open question (confirm Android vs XPlat parent), (3) detector-silence finding (zero system-detected ICMs while server shows 0.36% tunnel failure 5× ramp).
