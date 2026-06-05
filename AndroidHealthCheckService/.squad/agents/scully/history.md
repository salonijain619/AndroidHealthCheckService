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

## Learnings

### 2026-06-05 — Dashboard reverse-engineering + first Kusto introspection [SUMMARIZED]
Dashboard `8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` URL params decoded (`p-_osType=v-ANDROID`, `p-_trafficProfile`, `p-_tenantId`, `p-device_id`); `v-` prefix = variable-value. `azure-mcp-kusto` works against `idsharedwus.kusto.windows.net` with default creds. Schemas captured for `EdgeDiagnosticOperationEvent` (no `osType` col), `NaaSVPNZtnaConnectionLogsEvent` (carries Aria envelope `env_os` / `env_appVer`). PKI lookups returned empty (misleading — actual table located in catalog cycle). Wrote `.squad/agents/scully/research/dashboard-analysis.md`, initial 5 starter queries in `.squad/skills/android-kusto-starter/SKILL.md` (all `STATUS: untested`), decision `scully-dashboard-as-source-of-truth.md`.

### 2026-06-05T12:00:52Z — Team update: bootstrap complete [SUMMARIZED]
Squad standardized on `claude-opus-4.7`. Report template + example ready (Reyes). Telemetry foothold confirmed (Kusto MCP against `idsharedwus`). Dashboard `8a1fa78a-…` proposed as canonical source of truth. Defender-for-Android reuse blocked on VSTS access. Decisions: model standardization, report skeleton, dashboard-as-source-of-truth, reuse-Defender-assets.

### 2026-06-05 (later) — Panel KQL unblock from Saloni [SUMMARIZED]
Saloni pasted verbatim KQL from "Active Android Tenants (7d)" panel; executed against `idsharedwus/NaasProd/TunnelServerOperationEvents` and returned 8 distinct tenants (7d window ending 2026-06-05 12:00 UTC). **Key corrections:** primary table is `TunnelServerOperationEvents` (not Edge/ZTNA); canonical Android filter is `| where DeviceOs has_cs 'ANDROID'` (case-sensitive, no `v-` prefix); Android `ClientVersion` is `1.0.NNNN.NNNN` 4-segment numeric (NOT Windows SemVer); URL↔column drift `osType→DeviceOs`, `trafficProfile→ServiceType`, `device_id→DeviceId`. `TunnelServerOperationEvents` is rich enough (`DeviceId, ClientVersion, ServiceType, TenantId, LatencyMs, Status, FlowStatusError, FlowErrorClassification, OperationName, Region`) to source most daily-report rows without joins. Edge=HTTP-layer, Tunnel=L4/flow-layer — complementary. Some `TunnelServerOperationEvents` cols came back malformed from schema introspection (e.g., `SournnerFlowDestinationPort`); re-introspect needed. Reconciled `android-kusto-starter` queries 1–5; added #6 (verbatim panel mirror, executed) and #7 (active devices). Decision `scully-canonical-android-filter.md` filed.

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

## 2026-06-05T12:40:00Z — Team reinforcement: catalog ingest reception
Cross-team note (reinforcement of own discovery, recorded for future spawn continuity):
- Android client telemetry pipeline correction (App Insights `wd-prod-android-client`, NOT Aria) and the three closed unknowns from this cycle propagated to mulder, reyes, skinner, doggett histories. Charter point #2 flagged as wrong; correction owed in a future cycle.
- Doggett independently corroborated the App Insights routing via the `wd-prod-` brand prefix — two independent paths strengthen confidence from MEDIUM toward HIGH for the routing fact (query-body confidence stays MEDIUM until live-validated).
- Decision `scully-kusto-catalog-adopted.md` merged to `decisions.md`, awaiting Mulder ack.

### 2026-06-05 (final pass) — Defender-for-Android ICM baseline ingested

**What changed:**
- Saloni surfaced a second canonical clone (`WD.Client.Android-icm-copilot`). Its `agent-docs/IcmBaselineQueries.md` is the Defender-for-Android team's production-vetted livesite KQL set (30 queries) — adopted as canonical starting point for client-side telemetry in the daily report.
- Categorized all 30 queries to report sections; 22 map directly to specific Key Metrics / Top Insights / Cross-Domain / Drilldown rows; 2 are utility (E3 search, C1 device-lookup); 1 is off-charter for GSA (D4 malware-scan); the rest serve drilldown.
- Restructured `android-kusto-starter/SKILL.md` into Part 1 (server-side, retained) + Part 2 (client-side, 30 new queries CL-A1…CL-N12 at HIGH confidence). Server-side starters (#1–#8, #10, #11) were COMPLEMENTED, not replaced — they cover signals (server tunnel success, PKI, APS, Aria, perf) the ICM client-side baseline cannot.
- New skill `android-icm-baseline-mapping/SKILL.md` captures the cross-reference table so future spawns don't re-derive it.
- Filed decision `decisions/inbox/scully-icm-baseline-adopted.md`.

**Big resolution:**
- **Android client-side telemetry IS Kusto-queryable.** Catalog said AI REST endpoint (`wd-prod-android-client`, requires App Insights REST client, not our MCP path). ICM confirms an ADX cluster `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` carries the same SDK emissions and is reachable via `azure-mcp-kusto`. AI demoted to cross-check status.

## Learnings

### 2026-06-05 — Schema patterns from Defender-for-Android Telemetry.md (for future spawns)

**SDK shape.** All Android client telemetry is emitted via `MDAppTelemetry.trackEvent(eventName, eventProperties[, Flags])` from Kotlin. Two telemetry pipelines: **1DS** for Defender telemetry, **Aria** for Tunnel telemetry. Event names and property keys MUST come from generated Kotlin classes (`WD.Mobile.Xplat.Infra` repo) — hard-coded strings are prohibited. PascalCase enforced for both names and properties.

**Always-appended properties** (you don't have to add them; they are present on every event):
- `AndroidId`
- `TelemetryCorrelationId`
- `Persona`
- `EnrollmentType`
- `SessionIdTenantId`
- `TenantIdPII`
- `MachineId`
- `TenantOrgName` (only if `allowSensitiveData` is true)
- `TenantLicenseType`

Implication for KQL: `androidId`, `tenantId`, `machineId` (note: case-style is **lower** in the ADX projection of `customEvents`), `TenantOrgName` are reliable filter/pivot columns across every event. `TelemetryCorrelationId` enables stitched traces across events.

**Subtable infrastructure (`MDATPAndroidDB`).** `customEvents` is the source table; 10 routed subtables are populated via Kusto Update Policies that run `evaluate bag_unpack(EventProperty)`. **Always query the subtable when you know the domain** — properties are already unpacked into typed columns, query is faster, and `EventProperty.<x>` accessors degrade to first-class columns.

Subtable → domain map (memorize):
- `TelemetryGeneral` → `SevereLog`, `ErrorScenario`, and catch-all (209 events — largest)
- `TelemetryAuth` → `SignIn*`, `Auth*`, `MSAL*`, `Token*`, `PRT*` (41)
- `TelemetryVPNAndWebProtection` → `Vpn*`, `Tunnel*`, `LDNS*`, `Antiphishing*`, `Naas*`, `OpenVpn*`, `Edge*`, `CaptivePortal*` (96 — **NaaS / GSA lives here**)
- `TelemetryAppLifecycle` → `App*`, `Service*`, `Boot*`, `Onboarding*`, `Permission*`, `FRE*`, `EULA*`, includes crash/ANR events (89)
- `TelemetryHeartbeat` → `Heartbeat*`, `EdrHeartbeat*` (16)
- `TelemetryMalwareScan` → `Scan*`, `Threat*`, `Alert*`, `ML*`, `TFLite*` (76 — off-charter for GSA)
- `TelemetryCompliance` → `MAM*`, `TVM*`, `Enrollment*`, `Compliance*`, `Edr*Registration*` (63)
- `TelemetryConfiguration` → `ECS*`, `Config*`, `Feature*`, `Admin*` (12)
- `TelemetryNetworkMonitoring` → `Network*`, `Wifi*`, `CA*`, `Trusted*`, `Suspicious*` (29)
- `TelemetryProductHeartbeat` → just `ProductHeartbeat` (isolated for criticality)

Routing rule: **every event goes to exactly ONE subtable** (no duplicates). New properties auto-add columns (dynamic schema via `bag_unpack`).

**NaaS-specific call-site convention.** `NaaSTelemetrySender.logTelemetry(...)` sets `EventProperty.SubEvent = "NaaS"` (stable filter to scope to NaaS) and `EventProperty.Message = <free-form>` (distinguishes call sites that share an event name — e.g., `NaasVPNFailure` fires from two locations, distinguished by `Message starts with "Connecting failed"` vs `"Running failed"`). When in doubt about an Android NaaS event, filter by `tostring(EventProperty.SubEvent) == "NaaS"` first.

**Cluster reachability gotcha.** Defender ADX cluster `mdatpandroidcluster.westus2.kusto.windows.net` is in `westus2`; our other Kusto work has been on `idsharedwus` (also WUS) and `idsharedscus` (SCUS). Auth posture should carry over (same tenant), but smoke-test owed before relying on it.

**Time column on Defender ADX is `timestamp` (lowercase)** — App Insights / standard ADX convention. Different from NaasProd's `TIMESTAMP` (uppercase). Adds a fourth idiom to the existing three-idiom matrix; the time-column table in the starter skill now lists six total columns across our table family.

**`androidId` 3-char truncation gotcha.** ICM's own C1 footnote: device-lookup queries sometimes need to fall back to `startswith substring(__ANDROID_ID__, 0, strlen(__ANDROID_ID__) - 3)`. Likely a PII-hash boundary or upstream-collector quirk. Any future cross-cluster join keyed on `androidId` must handle this.
