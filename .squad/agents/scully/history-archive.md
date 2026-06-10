# scully — Learnings Archive

## Summarized entries (moved from history.md 2026-06-08)

### 2026-06-05 — Dashboard reverse-engineering + first Kusto introspection [SUMMARIZED]
Dashboard `8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` URL params decoded (`p-_osType=v-ANDROID`, `p-_trafficProfile`, `p-_tenantId`, `p-device_id`); `v-` prefix = variable-value. `azure-mcp-kusto` works against `idsharedwus.kusto.windows.net` with default creds. Schemas captured for `EdgeDiagnosticOperationEvent` (no `osType` col), `NaaSVPNZtnaConnectionLogsEvent` (carries Aria envelope `env_os` / `env_appVer`). PKI lookups returned empty (misleading — actual table located in catalog cycle). Wrote `.squad/agents/scully/research/dashboard-analysis.md`, initial 5 starter queries in `.squad/skills/android-kusto-starter/SKILL.md` (all `STATUS: untested`), decision `scully-dashboard-as-source-of-truth.md`.

### 2026-06-05T12:00:52Z — Team update: bootstrap complete [SUMMARIZED]
Squad standardized on `claude-opus-4.7`. Report template + example ready (Reyes). Telemetry foothold confirmed (Kusto MCP against `idsharedwus`). Dashboard `8a1fa78a-…` proposed as canonical source of truth. Defender-for-Android reuse blocked on VSTS access. Decisions: model standardization, report skeleton, dashboard-as-source-of-truth, reuse-Defender-assets.

### 2026-06-05 (later) — Panel KQL unblock from Saloni [SUMMARIZED]
Saloni pasted verbatim KQL from "Active Android Tenants (7d)" panel; executed against `idsharedwus/NaasProd/TunnelServerOperationEvents` and returned 8 distinct tenants (7d window ending 2026-06-05 12:00 UTC). **Key corrections:** primary table is `TunnelServerOperationEvents` (not Edge/ZTNA); canonical Android filter is `| where DeviceOs has_cs 'ANDROID'` (case-sensitive, no `v-` prefix); Android `ClientVersion` is `1.0.NNNN.NNNN` 4-segment numeric (NOT Windows SemVer); URL↔column drift `osType→DeviceOs`, `trafficProfile→ServiceType`, `device_id→DeviceId`. `TunnelServerOperationEvents` is rich enough (`DeviceId, ClientVersion, ServiceType, TenantId, LatencyMs, Status, FlowStatusError, FlowErrorClassification, OperationName, Region`) to source most daily-report rows without joins. Edge=HTTP-layer, Tunnel=L4/flow-layer — complementary. Some `TunnelServerOperationEvents` cols came back malformed from schema introspection (e.g., `SournnerFlowDestinationPort`); re-introspect needed. Reconciled `android-kusto-starter` queries 1–5; added #6 (verbatim panel mirror, executed) and #7 (active devices). Decision `scully-canonical-android-filter.md` filed.

## Current learnings - 2026-06-05 (archivedat 2026-06-08, pre-2026-06-06 work)

### 2026-06-05 (later still) — GSA Kusto Catalog ingested

**What changed:**
- Saloni cloned `Identity-gsa-client-marketplace` locally; its `gsa-kusto-catalog` skill (`SKILL.md` + `catalog.json` + `catalog-semantics.json`) is the canonical registry for every GSA / NaaS Kusto cluster, database, table, time column, and platform-emission flag.
- Adopted as ground truth. Wrote a local Android slice (`.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md`), reconciled `agents/scully/research/dashboard-analysis.md`, bumped query confidences in `android-kusto-starter`, added four new starter queries (#8 PKI, #9 App Insights, #10 perf rollups, #11 Aria errorevent cross-check), filed decision `decisions/inbox/scully-kusto-catalog-adopted.md`.

**Big resolutions (three of four standing unknowns closed):**
- **PKI source:** `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (time col `PreciseTimeStamp`). Same cluster we already use — earlier "empty table list" was misleading. Routing UNBLOCKED; query body still needs schema introspection.
- **AppInsights component:** `wd-prod-android-client` under sub `fb633419-…`. `AndroidId` in `customDimensions`, version in `application_Version`. Endpoint is the App Insights REST API, NOT a Kusto cluster URL — `azure-mcp-kusto` will not route to it.
- **Android client-side pipeline:** is **App Insights**, NOT Aria. The catalog explicitly says so. Earlier hypothesis that `mnap_xplat_telemetryprod_*` was Android-primary was wrong — those tables are Win/Mac primary. Android appears in Aria only opportunistically (errorevent via `App_Platform == 'Android'`).

**Big surprises:**
- `naas-idsharedwus / NaasProd` is a **2-table mirror** (`TunnelServerOperationEvents`, `EdgeDiagnosticOperationEvent`). The full 37-table NaasProd lives on **`naas-idsharedscus`** (`https://idsharedscus.southcentralus.kusto.windows.net`). For Roxy / Talon / ControlTower / NaaSVPN* / CertMonitor cross-checks, must hop to SCUS.
- New Android-specific cluster: `androidgsa.eastus.kusto.windows.net / Metric`. Two tables: `MemoryCPUUsage`, `UploadDownloadSpeed` — perf rollups by AppVersion + day. Catalog-flagged as not live-verified (DNS failed during catalog generation).
- Aria's `database` parameter must be the **GUID** (`f0eaa94222894be599b7cd0bc1e2ed6f`), not the friendly name `naas-prod`. Friendly name returns 400.
- Time columns inconsistent across the family: `TIMESTAMP` vs `PreciseTimeStamp` vs `env_time` vs `EventInfo_Time` vs `timestamp` vs `ingestion_time()`. Wrong column silently returns zero rows.

### 2026-06-05 — Catalog structure (for future spawns)

**`catalog.json` is for routing; `catalog-semantics.json` is for meaning.** Routing-only questions — `catalog.json` alone is enough. Composing a novel query — load both. Start with `catalog-semantics.json._indexes` for discovery.

**All four lookup levels are dicts keyed by name, not arrays.** Iterate with `.items()`.

**`platforms` array on a table is the observation set, not the contract.** If absent, don't bet on it; verify with `summarize count() by App_Platform` for certainty.

**Aria `database` parameter is the GUID, every time.** Prod = `f0eaa94222894be599b7cd0bc1e2ed6f`. Sandbox = `632690c28fc843478e52c697bba7a7ae`. Friendly names → 400. #1 documented failure mode upstream.

**Catalog cluster URLs include the App Insights placeholder.** `clusters.android-appinsights.url` literally contains `<appId>`; it's the AI REST API, not Kusto.

**`status: obsolete` means "zero rows AT CATALOG GENERATION", not "broken".** Re-verify with a fresh activity query.

**Cross-marketplace structure:** `Identity-gsa-client-marketplace` = client sub-system (Win32/macOS/Android/iOS); `Identity-GSA-Marketplace` (`gsa-plugins`) = cross-cutting. Reuse the catalog rather than duplicating — explicit "shared references" pattern in marketplace `AGENTS.md`.

**Three filter idioms coexist:** `DeviceOs has_cs 'ANDROID'` (server-side Tunnel/Edge family), `env_os == "Android"` (Aria-envelope tables on SCUS), `App_Platform == 'Android'` (Aria `mnap_xplat_*` cross-checks). Pick by table family. Full matrix in `.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md`.

**WUS NaasProd is a 2-table mirror, not the source.** Future spawns will be tempted to look for `RoxyHttpOperationEvent` / `TalonOperationEvent` / `NaaSVPN*` on `idsharedwus` and hit "table not found". The full set is on `idsharedscus`. Route accordingly.

### 2026-06-05 (final pass) — Defender-for-Android ICM baseline ingested

**What changed:**
- Saloni surfaced a second canonical clone (`WD.Client.Android-icm-copilot`). Its `agent-docs/IcmBaselineQueries.md` is the Defender-for-Android team's production-vetted livesite KQL set (30 queries) — adopted as canonical starting point for client-side telemetry in the daily report.
- Categorized all 30 queries to report sections; 22 map directly to specific Key Metrics / Top Insights / Cross-Domain / Drilldown rows; 2 are utility (E3 search, C1 device-lookup); 1 is off-charter for GSA (D4 malware-scan); the rest serve drilldown.
- Restructured `android-kusto-starter/SKILL.md` into Part 1 (server-side, retained) + Part 2 (client-side, 30 new queries CL-A1…CL-N12 at HIGH confidence). Server-side starters (#1–#8, #10, #11) were COMPLEMENTED, not replaced — they cover signals (server tunnel success, PKI, APS, Aria, perf) the ICM client-side baseline cannot.
- New skill `android-icm-baseline-mapping/SKILL.md` captures the cross-reference table so future spawns don't re-derive it.
- Filed decision `decisions/inbox/scully-icm-baseline-adopted.md`.

**Big resolution:**
- **Android client-side telemetry IS Kusto-queryable.** Catalog said AI REST endpoint (`wd-prod-android-client`, requires App Insights REST client, not our MCP path). ICM confirms an ADX cluster `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` carries the same SDK emissions and is reachable via `azure-mcp-kusto`. AI demoted to cross-check status.

### 2026-06-05 — Schema patterns from Defender-for-Android Telemetry.md

**SDK shape.** All Android client telemetry is emitted via `MDAppTelemetry.trackEvent(eventName, eventProperties[, Flags])` from Kotlin. Two telemetry pipelines: **1DS** for Defender telemetry, **Aria** for Tunnel telemetry. Event names and property keys MUST come from generated Kotlin classes (`WD.Mobile.Xplat.Infra` repo) — hard-coded strings are prohibited. PascalCase enforced for both names and properties.

**Always-appended properties:** `AndroidId`, `TelemetryCorrelationId`, `Persona`, `EnrollmentType`, `SessionIdTenantId`, `TenantIdPII`, `MachineId`, `TenantOrgName`, `TenantLicenseType`.

**Subtable infrastructure:** 10 routed subtables via update policies with `bag_unpack`. Always query the subtable when you know the domain — faster, properties unpacked into typed columns. Subtables: TelemetryGeneral (209), TelemetryAuth (41), TelemetryVPNAndWebProtection (96 — **NaaS/GSA here**), TelemetryAppLifecycle (89), TelemetryHeartbeat (16), TelemetryMalwareScan (76), TelemetryCompliance (63), TelemetryConfiguration (12), TelemetryNetworkMonitoring (29), TelemetryProductHeartbeat (1).

**NaaS-specific:** `EventProperty.SubEvent = "NaaS"` (filter) and `EventProperty.Message = <free-form>` (site distinction). When unsure, filter `tostring(EventProperty.SubEvent) == "NaaS"` first.

**Gotchas:** Cluster auth smoke-test owed. Time column `timestamp` (lowercase, unlike NaasProd's `TIMESTAMP`). `androidId` 3-char truncation for PII boundaries — cross-cluster joins need fallback.
