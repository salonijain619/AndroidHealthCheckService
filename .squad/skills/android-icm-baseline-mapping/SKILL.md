# Skill: android-icm-baseline-mapping

**Owner:** Scully
**Created:** 2026-06-05
**Confidence:** MEDIUM — derived from a single ingest of the Defender-for-Android ICM baseline (30 queries) and one read of the daily-livesite-report template. Mapping is opinionated and will firm up after we use it against a real report cycle.

## Purpose

This skill is a **cross-reference table only**: it maps each query in the Defender-for-Android team's `IcmBaselineQueries.md` to the report section (in `.squad/templates/daily-livesite-report.md`) where its output belongs, and to the cluster/database/subtable it targets. It exists so future spawns do not re-derive this categorization from scratch.

## Source

- **Upstream queries:** `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/agent-docs/IcmBaselineQueries.md` (16 KB, 482 lines, 30 queries across sections A/B/C/D/E/N)
- **Schema context:** `…/agent-docs/Telemetry.md`, `…/agent-docs/TelemetrySubtables.md`
- **Adopted into:** `.squad/skills/android-kusto-starter/SKILL.md` Part 2 (as queries CL-A1…CL-N12)

## Cluster / database (all client-side queries below)

- Cluster: `https://mdatpandroidcluster.westus2.kusto.windows.net/`
- Database: `MDATPAndroidDB`
- Source table: `customEvents`; **prefer the routed subtable** when available (10 subtables — see Telemetry**Subtables**.md)
- Time column: `timestamp` (lowercase, App Insights / ADX convention)
- Implicit Android filter: entire cluster is Android — no `DeviceOs` / `env_os` / `App_Platform` filter needed

## Cross-reference table

| ICM ID | Our ID | Subtable | Report section(s) | What it answers | Notes |
|---|---|---|---|---|---|
| A1 | CL-A1 | TelemetryGeneral | Exec Summary; Key Metrics → Fleet Errors | Hourly volume of `SevereLog` + `ErrorScenario` (24h) | Lead signal — first to spike on most incidents |
| A2 | CL-A2 | customEvents | Exec Summary; Key Metrics → Fleet Errors | Top 25 error/failure/exception/crash event names (24h) | Use to pick the next drill-down query |
| A3 | CL-A3 | TelemetryAppLifecycle | Exec Summary (client stability) | Crashes / ANRs / boot anomalies by AppVersion (24h) | Pivot by `AppVersion` → version distribution insight |
| B1 | CL-B1 | customEvents | Drilldown (per-tenant) | All event counts + device dcount for a tenant in window | Use after tenant identified |
| B2 | CL-B2 | customEvents | Drilldown (per-tenant); Top Insights | Error events for a tenant (7d) | Narrows from B1 to errors only |
| B3 | CL-B3 | customEvents | Key Metrics → Active Android Clients; Business Growth | Daily device dcount per tenant (14d) | Establishes per-tenant baseline |
| C1 | CL-C1 | customEvents | Drilldown (per-device) | Last 200 events for an androidId (7d) | ⚠ `androidId` may be truncated by 3 chars — retry pattern in skill |
| C2 | CL-C2 | customEvents | Drilldown (per-device) | Last 200 events for a `machineId` (7d) | `machineId` lives in `EventProperty` nested JSON |
| C3 | CL-C3 | TelemetryAppLifecycle | Drilldown (per-device); Data Quality | App + OS + Ring + Audience for a device | Use to confirm device cohort before attributing an incident |
| D1 | CL-D1 | TelemetryAuth | Top Insights → auth regression | Auth failure breakdown for a tenant (24h) | Pairs with N3/N4 (NaaS-specific auth) |
| D2 | CL-D2 | TelemetryHeartbeat | Key Metrics → APS Availability (client proxy) | Heartbeat reported vs failed (24h) | Closest client-side signal to APS health |
| D3 | CL-D3 | TelemetryVPNAndWebProtection | Key Metrics → Tunnel Health (broad) | All VPN/web-protection errors (24h) | Broader than NaaS-specific; use as Tunnel umbrella |
| D4 | CL-D4 | TelemetryMalwareScan | (off-charter for GSA report) | Scan failures | Defender-side; ignore unless cross-org incident |
| D5 | CL-D5 | TelemetryCompliance | Drilldown (per-org); Top Insights | TVM / AppInventory issues for an orgId | Defender side but can correlate w/ GSA tenant |
| D6 | CL-D6 | TelemetryCompliance | Top Insights → MAM/enrollment | MAM / Enrollment / Compliance failures per tenant (7d) | Useful for cross-domain (auth → MAM → enrollment chain) |
| E1 | CL-E1 | TelemetryAppLifecycle | Key Metrics → Version Distribution Health | Device count by `AppVersion` per tenant (24h) | The "Android Client Version Distribution Health" row in the template |
| E2 | CL-E2 | TelemetryConfiguration | Cross-Domain Correlation | ECS/config refresh events for a device (7d) | Use in correlation chains where a config push preceded errors |
| E3 | CL-E3 | customEvents | Data Quality Notes | Find an event name by substring (24h) | Schema-discovery utility; not a metric |
| N1 | CL-N1 | TelemetryVPNAndWebProtection | Key Metrics → Tunnel Health (client failure attribution) | NaaS VPN failures split Config vs IO/Run phase (24h) | First NaaS triage query |
| N2 | CL-N2 | TelemetryVPNAndWebProtection | Key Metrics → Tunnel Health | Top distinct NaaS failure messages per phase (24h) | Pinpoints JNI/config-setup exception class |
| N3 | CL-N3 | TelemetryVPNAndWebProtection | Top Insights → auth regression (silent path) | NaaS silent auth MSAL breakdown (24h) | Pairs with D1 (general auth) |
| N4 | CL-N4 | TelemetryVPNAndWebProtection | Top Insights → auth regression (interactive path) | NaaS interactive auth failures by tenant + appId (24h) | Use w/ N5 for funnel |
| N5 | CL-N5 | TelemetryVPNAndWebProtection | Cross-Domain Correlation | NaaS auth funnel silent vs interactive vs success (7d per tenant) | Anchor query for the "Timeline" section of cross-domain analysis |
| N6 | CL-N6 | TelemetryVPNAndWebProtection | Key Metrics → Tunnel Health | DNSServerExtractionFailed on network change (24h) | Captures WiFi/network-change-triggered failures |
| N7 | CL-N7 | TelemetryVPNAndWebProtection | Key Metrics → Tunnel Health | Captive portal lifecycle DETECTED vs CONNECTED (24h) | Conversion ratio = captive-portal success metric |
| N8 | CL-N8 | TelemetryVPNAndWebProtection | Top Insights → policy delivery | `NaaSAdminConfigSet` `Message ∈ {true,false}` distribution (24h) | `false` at connect time = misconfiguration |
| N9 | CL-N9 | TelemetryVPNAndWebProtection | Key Metrics → PKI Health (client cross-check) | NaaS cert handler errors (24h) | Client side of PKI — server side via starter #8 |
| N10 | CL-N10 | TelemetryVPNAndWebProtection | Top Insights → feature/policy change | GSA Private Access toggle source: user vs admin (7d) | Detects admin policy push that flipped PA off |
| N11 | CL-N11 | TelemetryVPNAndWebProtection | Top Insights → feature/policy change | NaaS client master-toggle enable/disable (7d) | User-initiated counter to N10 |
| N12 | CL-N12 | TelemetryVPNAndWebProtection | Cross-Domain Correlation | Full call-site-annotated NaaS timeline for a device (3d) | Deepest per-device evidence chain |

## Mapping rationale (so future spawns can extend it)

1. **Triage section A maps to the Executive Summary** because A1/A2/A3 surface the "is anything burning right now" signal. A1 is the recommended lead line in the summary.
2. **Section B (tenant impact) feeds the Drilldown half of Top Insights**, not the Key Metrics table — Key Metrics rows are fleet-wide; B is per-tenant.
3. **Section C (device deep-dive) never goes in Key Metrics.** It is exclusively per-device evidence used inside Top Insights or Cross-Domain Correlation.
4. **Section D's mapping is split:** D1 (auth) and D6 (compliance) → Top Insights; D2 (heartbeat) → Key Metrics APS row as a client-side proxy; D3 (VPN/Web umbrella) → Tunnel Health; D4 (malware scan) is off-charter for GSA but kept for cross-org incidents; D5 (TVM) is org-level drilldown.
5. **Section E is utility:** E1 directly fills the "Version Distribution Health" row, E2 is correlation evidence, E3 is a schema-discovery tool that lives in Data Quality Notes only.
6. **Section N (NaaS call sites) is the densest cross-mapped section.** It splits across:
   - Tunnel Health failure attribution (N1, N2, N6, N7, N9)
   - Auth regression (N3, N4, N5)
   - Policy/feature toggle insights (N8, N10, N11)
   - Cross-domain correlation evidence (N5, N12)
7. **PKI Health row needs both sides:** server-side via starter #8 (`EnrollCertificateOperationSummary` on `idsharedwus / NaasCloudPkiProd`) + client-side via N9 (`NaaSCertificateHandleError` on `mdatpandroidcluster / MDATPAndroidDB / TelemetryVPNAndWebProtection`). If they diverge that's a finding for Doggett.
8. **APS Availability has only a client-side proxy in ICM** (D2 heartbeat). The authoritative APS metric is server-side via starter #3 (still owes schema introspection). Treat D2 as a complementary view, not a replacement.

## Coverage gaps (ICM does NOT cover these report rows)

| Report row | Why ICM does not cover it |
|---|---|
| Key Metrics → APS Availability (authoritative) | APS is a server-side service. ICM is client-only. Use starter #3 (server-side). |
| Key Metrics → PKI Health (authoritative) | Server-side audit log lives in `NaasCloudPkiProd`. ICM only covers client-side cert errors (N9). Use starter #8 + N9 together. |
| Key Metrics → Server-side tunnel success / latency | ICM has client-side failure attribution (N1/N2). Server success rate + p50/p95/p99 latency = starter #5. |
| Active Android Tenants (server-defined) | ICM measures tenants impacted client-side; the dashboard panel uses server-side `TunnelServerOperationEvents`. Use starter #6 for the report row. |
| Aria cross-check for Android errors | Outside Defender ADX. Use starter #11 (`mnap_xplat_telemetryprod_errorevent`). |
| Android perf rollups (CPU/mem/throughput) | Different cluster (`androidgsa.eastus`). Use starter #10. |

## How to use

1. Identify the report section you are filling.
2. Look it up in the column "Report section(s)" above; collect all matching query IDs.
3. For each query ID, open `.squad/skills/android-kusto-starter/SKILL.md` (Part 2 for `CL-…` IDs, Part 1 for `#N` IDs) — body and placeholders are there.
4. If the section has both server-side (`#N`) and client-side (`CL-…`) queries listed, run both and reconcile — divergence is itself a Top-Insight candidate (raise to Doggett).
5. If your section is not listed, check "Coverage gaps" — that table tells you which starter to reach for instead.

## When to update

- A new query is added upstream to `IcmBaselineQueries.md` — extend the cross-reference table here AND add the query body to `android-kusto-starter / Part 2`.
- A report-template row changes — re-categorize affected queries.
- A reconciliation run finds a server↔client signal divergence — annotate it in "Mapping rationale" as a known caveat.

## Out of scope

- Query bodies (live in `android-kusto-starter/SKILL.md`).
- Cluster routing for non-Defender clusters (live in `gsa-kusto-catalog-android-slice/SKILL.md`).
- Report layout (lives in `.squad/templates/daily-livesite-report.md`).
- Decisions about which signal "wins" in a divergence — that is Doggett (cross-domain) or Mulder (judgment), not Scully.
