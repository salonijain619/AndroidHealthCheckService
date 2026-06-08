# scully — Learnings

## Project Context (seeded 2026-06-05)
- **Project:** Android GSA Client Service Health Check
- **User:** salonijain619 (Saloni)
- **Stack:** Investigation/SRE squad for the GSA Android client. Telemetry from server-side Kusto (NaasProd @ idsharedwus + idsharedscus for full set), client-side **App Insights `wd-prod-android-client`** (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c), Aria Kusto (GUID f0eaa94222894be599b7cd0bc1e2ed6f, opportunistic Android only), and Android-perf cluster `androidgsa.eastus.kusto.windows.net/Metric` (unverified).
- **Android client repo:** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android
- **Onboarding doc:** https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **ICM team:** https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- **Report channel:** IDNA GSA → Livesite - Client (Teams), tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
- **Sister squads:** Windows (win_client_investigation_squad), Mac (HarryPotter)

## Summarized history (full content → `history-archive.md`)

### 2026-06-05 — Dashboard reverse-engineering + first Kusto introspection [SUMMARIZED]
Dashboard analysis, schema capture, initial starter queries (5 untested). See archive.

### 2026-06-05T12:00:52Z — Team update: bootstrap complete [SUMMARIZED]
Squad bootstrap, report template ready, Kusto foothold confirmed. See archive.

### 2026-06-05 (later) — Panel KQL unblock from Saloni [SUMMARIZED]
Verbatim panel query executed; key corrections on filter/format/routing. See archive.

## Current learnings (active)

### 2026-06-05T13:30Z — First executable NAAS-only 7d Android data run
Executed NAAS-server-side, Android-filtered, all-tenants slice of the ICM baseline workload against `idsharedwus` (NaasProd + NaasCloudPkiProd + NaasAgentServicesApsProd) for the 7d window ending 2026-06-05T13:26Z. Auth clean via `azure-mcp-kusto` default cred; 20 queries attempted, 17 passed, 5 recovered from column-discovery/casing, 0 final failures. All 22 ICM client-side queries DROPPED per Saloni's NAAS-only scope lock. Headline numbers Reyes can lift: 27,489 active Android devices / 1,241 active tenants (NOT 8 — that older number was an outdated ClientVersion cohort-filter artifact) / 130.05M tunnel events / 99.711% success / 0.289% failure overall. **P2 anchor finding:** daily tunnel failure-rate climbed ~5× (0.074% → sustained 0.36%) over the window — anomaly is real (failure volume +12× while traffic only +2.6×). Private Access fails 4× more than M365 (0.69% vs 0.17%); `PROFILE_UNDEFINED` ServiceType is 100% failure (4,003 events, 245 devices — config-bootstrap race). APS 99.997% / 270M events; APS-Ack 99.99966% / 268M; PKI 0.0007% errors (4 of 595,712) — both healthy ✅. **New data-quality findings for the report:** `FlowStatusError` / `FlowErrorClassification` / `LatencyMs` / `Msg` on `TunnelServerOperationEvents` are **ghost columns** (advertised in `getschema`, unqueryable — Kusto returns SEM0100); server-side latency p50/p95/p99 unavailable this cycle. `Region` casing duplicates (e.g. `westeurope`/`WestEurope`) imply two ingestion paths. APS sibling tables have divergent schemas (`HttpResponseStatusCode` present on GetSettings, absent on SettingsAck). PKI emits empty `DeviceId` for Android (use TenantId only). Filter idiom matrix expanded: Tunnel = `DeviceOs has_cs 'ANDROID'`, PKI = `OS == 'ANDROID'` (uppercase, case-sensitive), APS = `OS has_cs 'Android' or OSType has_cs 'Android'`. Output: `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md` (~27KB; ICM re-bucketing + Exec Summary + 12 per-query results + Failures + 3 cross-domain candidates Reyes/Doggett can extend). Decision filed: `decisions/inbox/scully-naas-7d-execution-20260605T1330Z.md`. **Queued for Reyes:** every server-side Key-Metrics row has a real number; Top Insight #1 candidate pre-anchored (Tunnel 5× ramp); 3 cross-domain chains pre-drafted. Client-side rows remain TBD until Defender-client-side scope is unlocked.

### 2026-06-06 — HarryPotter ICM collector ported + first live pull on team 106961

**Port (verbatim, per Doggett's plan):** Copied HP `livesite/scripts/icm_collector.py` (commit `d35a114`) and `tests/test_icm_collector.py` into `tools/icm/` under squad root. Substitutions: `team_id 115956→106961`, `team_name "GSA Client - MacOS"→"GSA Client - Android"`, env `HP_ICM_TEAM_ID→AHCS_ICM_TEAM_ID`, client name `hp-icm-collector→ahcs-icm-collector`, import paths `livesite.scripts→tools.icm`, default config `livesite/scripts/config.yml→.squad/config.json`. **NO change** to JSON-RPC handshake, `WARMUP_DELAY_S=6`, tools/list-then-sleep-then-tools/call ordering, D-138 no-`dateRange` discipline, severity normalization, age calculation. Created `.squad/config.json` with `icm.team_id=106961` as single source of truth (CLI > env > config > default, per HP D-117/D-118).

**Tests:** `python3 -m pytest tools/icm/tests/ -v` → **19/19 passed**, including the 3 D-138 regression tests (`test_active_query_omits_date_range`, `test_mitigated_query_omits_date_range`, `test_mitigated_query_sorts_by_last_modified_desc`). Port verified clean.

**Live run:** `python3 -m tools.icm.icm_collector --config .squad/config.json --timeout 120`. Exit 0, **26s elapsed** (warm Entra cache, no browser flow). `source: "live"`, `_meta.errors: []`. Raw JSON: `tools/icm/runs/icm-run-2026-06-06.json`.

**Headline counts:** 1 active (Sev3, customer-reported but flagged `[Copilto testing]` TestICM, #810723164, unacknowledged, 5d old) · 0 mitigated · on-call primary=`dileepkusuma`, backup=`samirnen` (live, no cache fallback). Effective real-incident count after TestICM filter = **0**.

**3 findings worth flagging:**
1. **Bucketing bug (port-faithful, not introduced by me):** HP collector buckets active ICMs by `source startswith "customer"`, but ICMProd's payload uses `type` (`CustomerReported`/`LiveSite`/`Deployment`) and returns `source: None`. The lone customer-reported ICM currently lands in `system_created_active`. Raw `type` preserved per-incident — Doggett/Reyes 1-line re-bucket fix in v2.1.
2. **Owning-team display drift:** `owningTeamId=106961` → `owningTeamName="GSA  Client - XPlat"` (double-space typo). Need Saloni confirm 106961 is the Android queue vs an XPlat parent (could mean we're missing an Android-only sub-queue).
3. **Detector silence is suspicious, not reassuring:** zero system-detected ICMs while server-side NaaS 7d (own 2026-06-05 pull) shows 0.36% sustained tunnel failure rate (5× ramp). Either no Android-tagged detector exists or rotation isn't routing detector-emitted incidents here.

**Outputs (for Reyes v2 report):** `.squad/agents/scully/research/icm-team-106961-data-2026-06-06.md` (full structured drop with On-Call, Counts, Customer/System/Mitigated tables, 6-bullet Patterns, raw cross-check counts, D-138 provenance). Decision filed: `.squad/decisions/inbox/scully-icm-106961-first-pull-2026-06-06.md` (confidence: medium, verify on second pull).

## 2026-06-08T16:23Z — Scribe: Orchestration log + session summary

Scribe wrote orchestration logs for the 2026-06-06 spawn batch (4 entries: doggett-3, doggett-4, scully-4, reyes-1) and a session log covering the HP discovery → skill authoring → collector port → v2 report arc. Mulder and Skinner flagged for cross-team review on: (1) new `icm-queue-ingest` skill (confidence MEDIUM, promote to HIGH after second clean cycle), (2) team 106961 queue-identity open question (confirm Android vs XPlat parent), (3) detector-silence finding (zero system-detected ICMs while server shows 0.36% tunnel failure 5× ramp). Decision inbox merged into `decisions.md` (6 files processed).
