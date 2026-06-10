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

### 2026-06-06 — HarryPotter ICM collector ported + first live pull on team 106961 [SUMMARIZED]
ICM collector ported (19/19 tests passed, D-138 discipline verified), live pull clean (0 real incidents, 1 TestICM litter). Bucketing bug found (source/type field mismatch), owning-team typo confirmed, detector silence flagged. See archive.

### 2026-06-08 — Daily refresh: ICM live ✅, NAAS BLOCKED on network [SUMMARIZED]
ICM: byte-identical envelope vs 06-06 (0 real incidents confirmed stable). NAAS: TCP-blocked on `idsharedwus.kusto.windows.net:443` (corp firewall, not auth/schema), zero data this cycle. See archive.

## Current learnings (active)

### 2026-06-05T13:30Z — First executable NAAS-only 7d Android data run
Executed NAAS-server-side, Android-filtered, all-tenants slice of the ICM baseline workload against `idsharedwus` (NaasProd + NaasCloudPkiProd + NaasAgentServicesApsProd) for the 7d window ending 2026-06-05T13:26Z. Auth clean via `azure-mcp-kusto` default cred; 20 queries attempted, 17 passed, 5 recovered from column-discovery/casing, 0 final failures. All 22 ICM client-side queries DROPPED per Saloni's NAAS-only scope lock. Headline numbers Reyes can lift: 27,489 active Android devices / 1,241 active tenants (NOT 8 — that older number was an outdated ClientVersion cohort-filter artifact) / 130.05M tunnel events / 99.711% success / 0.289% failure overall. **P2 anchor finding:** daily tunnel failure-rate climbed ~5× (0.074% → sustained 0.36%) over the window — anomaly is real (failure volume +12× while traffic only +2.6×). Private Access fails 4× more than M365 (0.69% vs 0.17%); `PROFILE_UNDEFINED` ServiceType is 100% failure (4,003 events, 245 devices — config-bootstrap race). APS 99.997% / 270M events; APS-Ack 99.99966% / 268M; PKI 0.0007% errors (4 of 595,712) — both healthy ✅. **New data-quality findings for the report:** `FlowStatusError` / `FlowErrorClassification` / `LatencyMs` / `Msg` on `TunnelServerOperationEvents` are **ghost columns** (advertised in `getschema`, unqueryable — Kusto returns SEM0100); server-side latency p50/p95/p99 unavailable this cycle. `Region` casing duplicates (e.g. `westeurope`/`WestEurope`) imply two ingestion paths. APS sibling tables have divergent schemas (`HttpResponseStatusCode` present on GetSettings, absent on SettingsAck). PKI emits empty `DeviceId` for Android (use TenantId only). Filter idiom matrix expanded: Tunnel = `DeviceOs has_cs 'ANDROID'`, PKI = `OS == 'ANDROID'` (uppercase, case-sensitive), APS = `OS has_cs 'Android' or OSType has_cs 'Android'`. Output: `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md` (~27KB; ICM re-bucketing + Exec Summary + 12 per-query results + Failures + 3 cross-domain candidates Reyes/Doggett can extend). Decision filed: `decisions/inbox/scully-naas-7d-execution-20260605T1330Z.md`. **Queued for Reyes:** every server-side Key-Metrics row has a real number; Top Insight #1 candidate pre-anchored (Tunnel 5× ramp); 3 cross-domain chains pre-drafted. Client-side rows remain TBD until Defender-client-side scope is unlocked.

### 2026-06-09 — NAAS 7d v3 refresh: cluster unblocked, ramp got WORSE
**Outcome:** ✅ GO. 10/10 substantive queries clean against `idsharedwus` (NaasProd + NaasAgentServicesApsProd + NaasCloudPkiProd). Yesterday's TCP-block lifted — same `azure-mcp-kusto` MCP path that timed out 06-08 is back online. Window: `2026-06-02T00:00:00Z` .. `2026-06-09T00:00:00Z` (closed 7-day). Drop: `.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md`.

**Deltas vs v1 (2026-06-05 baseline) — headline:**
- 7d events 130.05M → 131.87M (+1.4% flat); 7d failures **375K → 508K (+35%)**; overall fail-rate **0.289% → 0.385% (+33%)**. Quality regression, not traffic.
- Daily ramp: v1 plateau 0.36% on 6/02–6/04; v3 shows 6/05=0.354 → **6/06=0.416 → 6/07=0.431 → 6/08=0.447** (highest single-day in 11 days of observation). NOT stabilizing — second-step degradation.
- Active devices 27,489 → 27,744 (+0.9%); tenants 1,241 → 1,254 (+1%). Fleet unchanged; everything else got worse.
- ServiceType: M365 0.174→0.227, INTERNET 0.548→0.766, PRIVATE_ACCESS 0.688→**0.929**. PA:M365 ratio held at ~4×. Uniform +30–40% across profiles.
- Microsoft 1P share unchanged at 38%. PROFILE_UNDEFINED devices 245→345 (+41%) at 100% fail.
- ClientVersion `.04xx` ring: `1.0.9003.0401` +55% devices AND +131% fail-rate (0.271→0.626) — biggest single-version regression. Now the highest-fail high-volume version.
- Regions: germanywestcentral +67%, NorthEurope +61%, francecentral +57%, SwedenCentral +114%. EU cluster intensifying. UK South biggest absolute (118K fails).
- APS health unchanged (99.996%/99.99970%). PKI 0.0007% errors unchanged — BUT new 2× HTTP500 `Failed` class that didn't exist in v1.
- Ghost columns (FlowStatusError/FlowErrorClassification/LatencyMs/Msg) STILL ghost — 4 days no fix.

**Immediate actions for Mulder:**
- Investigate tenant `9cf9036f-5fc5-475d-846d-94ea941e4bfc` (105 fails/device, 45 devices) and `0e17f90f-…` (+40% failures, 165/device).
- Identify `.04xx` build flavor and `1.0.9003.0401` identity (likely internal ring, 2 tenants).

**3 key framing corrections applied:**
- The ramp is the v3 report's top insight. Anchor on "0.074% → 0.36% plateau → 0.42–0.45% second-step" with the failure-rate trend graph. At 0.447% on 6/08, a single +0.55pp day crosses 1% (the typical incident threshold).
- Drop the "Microsoft 1P / dogfood rollout" hypothesis. The non-1P data falsifies it.
- New tenant to flag for Mulder triage: `9cf9036f-5fc5-475d-846d-94ea941e4bfc` (105 fails/device, 45 devices, new top-15 entrant).

### 2026-06-09 — Android NAAS crash-report agent discovery + pull

Discovered the aggregate Android crash path: `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/agents/telemetry-query.agent.md`, backed by App Insights resource `wd-prod-android-client` / workspace `android-release-log-analytics-workspace`. Invocation that worked: `az monitor log-analytics query --workspace 056a9d06-a48b-40b7-ad62-170a39c09d7e --analytics-query '<KQL>'`. Per-issue follow-up skills found in the Android repo: `triage-jvm-crash`, `triage-native-crash`, and `fetch-native-crash`; those need a Play Console issue ID and are not the right first tool for weekly aggregate counts.

NAAS filter settled on: `AppEvents` where `Name == 'AppExitInfoReported'` and parsed `Description has '.vpn.VpnServiceOrchestrator'`, plus `Name == 'CrashReported'` where parsed `StackTrace has 'VpnServiceOrchestrator' or 'com.microsoft.scmx.vpn'`. Rationale: package/process `com.microsoft.scmx` catches the entire Defender app and is too broad; VPN orchestrator stack/description markers are tight to NAAS-on-Android service execution. Avoid `nativeEvents` keyword hits unless manually validated; current hits were Smart Screen / tenant-name false positives.

Result drop: `.squad/agents/scully/research/naas-crashes-2026-06-09.md`. Outcome GO: 18,518 NAAS AppExit/ANR events and 952 NAAS JVM crashes in the 7d window ending 2026-06-09; top signatures are VPN service orchestrator reason-6 ANR/user-request-after-error patterns, not new vs prior baseline, and not concentrated in the `1.0.9003.0401` `.04xx` ring.

### 2026-06-09 — Canonical Android crash source corrected to Google Play vitals
- **Canonical Android crash source:** google-play-vitals skill at `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md` — NOT telemetry-query. AppEvents / CrashReported is internal exit telemetry, not user-perceived Play vitals. Lesson: when Saloni names a skill, default to it.
- **NAAS filter predicate used verbatim:** `Package: com.microsoft.scmx; Issue query: apps/com.microsoft.scmx/errorIssues:search; Base filters: errorIssueType = CRASH; errorIssueType = ANR; Version cross-check filter: versionCode = 900300412 AND errorIssueType = <CRASH|ANR>; Local NAAS predicate over Play issue cause/location: lower(cause || ' ' || location) contains any of 'vpnserviceorchestrator', 'com.microsoft.scmx.vpn', 'naas', 'tunnel', 'vpn'`.
- **Validated outcome:** Play vitals pull completed via direct Google Play Developer Reporting API because the `mcp_google-play-r_*` tool names were not exposed in this Copilot CLI session. Drop overwritten at `.squad/agents/scully/research/naas-crashes-2026-06-09.md`; android-crash-pull skill confidence raised to medium and AppEvents demoted to fallback-only.

### 2026-06-09 — NAAS crash deepening: Play issue-level causes extracted
- **Endpoint split learned:** `apps/com.microsoft.scmx/errorIssues:search` is issue inventory/aggregate metadata only (issue id, type, cause, location, report/user counts, versions, OS bounds, last report, Play link). `apps/com.microsoft.scmx/errorReports:search` with `filter errorIssueId = "<issue-id>"` exposes representative per-report stack traces / ANR main-thread traces / native tombstone frames. `apps/com.microsoft.scmx/errorCountMetricSet:query` with `dimensions = reportType+issueId/versionCode/apiLevel/deviceBrand` provides 7d-scoped per-issue counts and version/OS/OEM distributions; issue-level installs are not exposed.
- **NAAS subsystem taxonomy for next week:** `VpnServiceOrchestrator`; `OpenVPN/BaseOpenVpnClient`; `NAAS native VPN library`; `Intune VPN bridge`; `Consumer VPN client/provider`; `NAAS VPN UX model`; `TunnelManager/flow`; `VPN general`; `Other NAAS-adjacent`.
- **Lesson:** Aggregates without causes are noise — always pull issue-level depth for Saloni. For this pull, top crash cause is `VpnServiceOrchestrator.onStartCommand()` foreground-service timeout/resource exhaustion; top ANR cause is OpenVPN/native library load/init on main thread.

### 2026-06-09 — 6× ramp framing + bucketing bug + detector silence (multi-observation)
- **6× ramp framing.** v1/v2 said "5× ramp" (0.074%→0.36%). v3 now spans 0.074%→0.447%, which is 6×. Updated all instances in v3 prose. Kept the v1 baseline reference for traceability.
- **TestICM aging from 5d to 5d+.** The TestICM hasn't been touched since 06-06, so on 06-09 it's actually 6d old (created 06-03), but lastModified is still 06-06. Wrote "5+ days, untouched ~2.5 days since 06-06" to capture both axes without overclaiming.
- **Bucketing bug at pull #3.** Restated workaround prominently (classify by `type == "CustomerReported"`) since downstream consumers need it every cycle until v2.1 ships.
- **Detector silence is now a multi-pull observation** (06-05 + 06-08 server-side anomalies; 06-06 + 06-08 ICM detector pulls). Mulder/Skinner thread should treat this as a firm finding, not a one-off suspicion. If the v1 5× tunnel-failure-rate ramp didn't trip a detector, the detector either doesn't exist or isn't routed to team 106961.

### 2026-06-10 — Team expansion: Frohike now owns Play Vitals, Scully hands off crash report ownership

Frohike (Play Vitals Analyst) hired as new team member to own Google Play Console crash/ANR analysis, NAAS-filtered. Replaces Scully's ad-hoc Play Vitals ownership. Frohike sources truth from `WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`, drops output at `.squad/agents/frohike/research/naas-crashes-{date}.md`. Scully retains server-side NAAS telemetry (TunnelServerOperationEvents, APS, PKI, AppEvents/CrashReported). Daily report assembly (Reyes) now pulls from Scully (server) + Frohike (Play crashes) + Langly (current version) in parallel. ICM investigations also fan out to Frohike for client-side crash signature matching. Framing rule inherited: All Play Vitals output MUST be NAAS-as-a-unit, never Defender-filtered-to-NAAS.
