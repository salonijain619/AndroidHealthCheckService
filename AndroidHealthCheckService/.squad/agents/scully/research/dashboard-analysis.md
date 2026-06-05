# Android GSA Kusto Dashboard — Analysis & Hypothesis

**Author:** Scully (Telemetry Analyst)
**Date:** 2026-06-05
**Status:** Hypothesis + partial ground-truth (Kusto introspection succeeded for `NaasProd` and `NaasAgentServicesApsProd`; dashboard panels themselves not directly fetched — auth wall).

Dashboard URL (canonical):
`https://dataexplorer.azure.com/dashboards/8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98`

---

## 1. Dashboard Structure Hypothesis

### 1.1 URL parameter dictionary
| URL param | Value seen | Meaning (hypothesized) | Likely panel control |
|---|---|---|---|
| `p-_startTime` | `7days` | Rolling window start | Date-range picker (default 7d) |
| `p-_endTime` | `now` | Rolling window end | Date-range picker |
| `p-_osType` | `v-ANDROID` | OS pivot, scoped to Android | Dropdown: `Windows / Android / iOS / macOS / All` |
| `p-_trafficProfile` | `all` | Network/traffic profile pivot | Dropdown: maps to `NetworkProfile` column in `NaasProd.EdgeDiagnosticOperationEvent` (`Internet`, `Private`, `M365`, `All`) |
| `p-_tenantId` | `all` | Tenant pivot | Dropdown: maps to `TenantId` column (GUID list, default `all`) |
| `p-device_id` | `v-DeviceIdPII_9ab9b07…` | Per-device drilldown (PII-hashed) | Free-text / search; populates device-level panel |
| Fragment `#45c11f5e-b0ae-40d7-bb48-c2b1936011cc` | — | Specific page/tab UUID within the multi-page dashboard | **Unknown — ask Saloni** |

The `v-` prefix on parameter values is a Kusto dashboard convention for *variable values* (vs free-text). `PII_…` hash pattern matches Microsoft's standard PII tokenization for DeviceId.

### 1.2 Probable dashboard pages (multi-page layout)
Based on the report skeleton + standard GSA dashboards I've seen the shape of, the dashboard likely has these pages, each with its own UUID in the URL fragment:

1. **Overview / Executive** — KPI tiles (Active Devices, Error %, Availability)
2. **Connectivity / Tunnel Health** — ZTNA tunnel + VPN-gateway panels
3. **Policy & APS** — APS delivery success, get-settings latency, ack rates
4. **Errors & Diagnostics** — error breakdown by `ResponseCode`, `OperationName`, `NetworkProfile`
5. **Per-Device Drilldown** — page that consumes `p-device_id` (the URL we got points *here*, given the device_id filter is set)
6. **Version Distribution** — client `env_appVer` histogram (Aria-side)

The fragment `#45c11f5e-…` is **most likely the per-device drilldown page**, since the URL also pins `p-device_id` to a specific PII hash. ⚠️ Needs confirmation.

### 1.3 Pivots: which apply to which panel
| Pivot | Applies to (hypothesis) |
|---|---|
| `osType` | All client-originated panels (filters via Aria `env_os` or via a DeviceId→OS join). Does **not** apply to pure server-only panels (Roxy/Talon/Tunnel gateway) unless they're joined to client telemetry. |
| `trafficProfile` | Traffic-bearing panels: Edge Diagnostic, Roxy HTTP, Tunnel insights. Maps to `NetworkProfile` column. |
| `tenantId` | All panels with `TenantId` column. Probably every server-side table has it. |
| `device_id` | Per-device drilldown panels only. |

---

## 2. Ground-truth Kusto findings (confirmed via `azure-mcp-kusto`)

### 2.1 Cluster `idsharedwus` is reachable
Visible databases (confirmed): `NaasProd`, `NaasAgentServicesApsProd`, `NaasAgentServicesCloudPkiProd`, `NaasCloudPkiProd`, `GSASyntheticTrafficLogs`, `ZTNAMgmtPlaneProd`, plus dev/test/PPE siblings.

### 2.2 `NaasProd` tables (server-side, confirmed)
Grouped by subsystem:
- **Edge / Diagnostic:** `EdgeDiagnosticOperationEvent`, `EdgeDiagnosticServiceDebug`
- **Roxy (HTTP proxy):** `RoxyHttpRequest`, `RoxyHttpOperationEvent`, `RoxyStreamRequest`, `RoxyStreamOperationEvent`, `RoxyDebug`
- **Talon (connection broker):** `TalonOperationEvent`, `TalonDebug`, `TalonProxyChainAccess`, `TalonProxyChainDebug`
- **Tunnel / VPN:** `TunnelServerOperationEvents`, `TunnelServerDebug`, `NaaSVPNTunnelInsightEvent`, `NaaSVPNZtnaConnectionLogsEvent`, `NaaSVPNGatewayFlowLogsEvent`, `NaaSVPNIkeLogsTableTraceEvent`, `NaaSVPNIkePacketLogsTableTraceEvent`, `NaaSVPNDatapathPacketsInsightEvent`, `NaaSVPNConfigurationLogsEvent`, `NaaSVPNTenantLogsEvent`
- **Control plane:** `ControlTowerOperationEvent`, `ControlTowerDebug`, `PortoFrontendOperationEvent`, `PortoFrontendDebug`
- **Policy:** `PolicyBrokerDebug`
- **DNS / Threat / Categories:** `DnsProxyOperationEvent`, `DnsProxyDebug`, `ThreatIntelDebug`, `WebCategoriesDebug`
- **ZTNA branch:** `ZTNABranchHealthEvent`
- **Feature flags:** `FeatureFlagDebug`

### 2.3 `EdgeDiagnosticOperationEvent` schema (confirmed)
Key columns: `TIMESTAMP, PreciseTimeStamp, DeviceId, TenantId, UserId, OperationName, NetworkProfile, ResponseCode, DurationInMilliseconds, RequestPath, DestinationFqdn, SourceIp, DestinationIp, BytesSent, BytesReceived, ConnectionId, FlowCorrelationId, NaasSDPRing, RegionName, HttpProtocol`.
⚠️ **No `osType` column visible.** Android scoping must come from one of:
  - (a) Joining `DeviceId` against a device-registry table that records OS, or
  - (b) Aria client telemetry (`env_os = "Android"`) filtered first, then joined back by `DeviceId`, or
  - (c) Dashboard parameter is just decorative on this panel and only filters client-side panels.

### 2.4 `NaaSVPNZtnaConnectionLogsEvent` schema (confirmed)
Key columns: `env_time, env_os, env_osVer, env_appId, env_appVer, env_cloud_role, env_cloud_location, GatewayBuildVersion, TenantGatewayId, TenantVNetId, VpnInstanceId, PublicIp, GatewayId, Region, Description, Title, TraceLevel`.
✅ **`env_os` IS present here** — so this table CAN be filtered to `Android` directly. Confirms hypothesis (b) is at least partly real for VPN/ZTNA telemetry (uses Aria-style `env_*` envelope).

### 2.5 `NaasAgentServicesApsProd` tables (APS — confirmed)
- `PoliciesApi` — likely outbound policy API calls
- `AgentGetSettingsOperationEvent` — agent settings fetch (probable APS availability metric)
- `AgentSettingsAckOperationEvent` — agent ack (closes the loop; gives apply-success metric)
- `DirObjectSyncOperationEvent`, `UASyncOperationEvent`, `ResourcesUpdateOperationEvent` — sync events
- `Heartbeat`, `CounterMetrics`, `DefaultEventTable` — health/metrics

### 2.6 PKI databases empty (or permission-scoped)
`kusto_table_list` returned **zero tables** for both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd`. Either:
  - The account this MCP is auth'd as lacks read on those DBs, OR
  - The PKI signal lives in a different cluster (e.g., a dedicated PKI Kusto), OR
  - Those DB names are placeholders.
⚠️ **PKI Health metric is currently unblocked-by-schema.** Need Saloni to point at the real PKI telemetry source.

---

## 3. Panel-to-Report Mapping

For each `{TBD}` in `.squad/templates/daily-livesite-report.md`, the likely dashboard panel + likely backing table:

| Report row | Hypothesized dashboard panel | Likely table(s) | osType filter path | Confidence |
|---|---|---|---|---|
| Active Android Clients (weekday) | "Active Devices" tile on Overview page | `EdgeDiagnosticOperationEvent` distinct `DeviceId` (joined to Android cohort) **OR** Aria client-side `env_os == "Android"` distinct device | Aria preferred; NaasProd needs device→OS join | Medium |
| Fleet Errors (7d) | "Errors over time" + "Top error codes" panels | `EdgeDiagnosticOperationEvent` where `ResponseCode >= 400`; plus `RoxyHttpOperationEvent` | Same as above | Medium |
| APS Availability | "APS Get-Settings success %" tile | `NaasAgentServicesApsProd.AgentGetSettingsOperationEvent` (success vs total) | Probably has `DeviceId` or client UA; needs schema check | High (table confirmed, exact column TBD) |
| PKI Health | "PKI cert issue/renewal success" | **UNKNOWN — Pki DBs empty** | n/a | 🔴 Blocked |
| Tunnel Health | "ZTNA connection success", "Tunnel latency p50/p95" | `NaaSVPNZtnaConnectionLogsEvent`, `NaaSVPNTunnelInsightEvent`, `TunnelServerOperationEvents` | `env_os == "Android"` works directly on ZTNA table | High |
| Android Client Version Distribution Health | "Version histogram" + "Error % per version" | Aria client telemetry (`env_appVer`); cross-referenced with NaasProd errors via DeviceId | Native to Aria | Medium |
| Business Growth (7d) | "New devices over time" | distinct new `DeviceId` per day from any Android-scoped client table | Aria preferred | Medium |
| Data Completeness Notes | Ingest lag panels (typically `ingestion_time() - TIMESTAMP`) | All tables expose ingestion time | n/a | High |

---

## 4. Open Questions (for Saloni)

> **Refreshed punch list — 2026-06-05 post-panel-KQL unblock.** Several earlier items resolved by Saloni's panel paste. What REMAINS:
>
> 1. **Second panel KQL — preferably an errors or latency panel.** This first panel is a simple `distinct | count` (no error/latency logic), so it doesn't tell us whether the dashboard surfaces flow errors via `FlowStatusError`, `Status`, `OperationName`, or by joining to `EdgeDiagnosticOperationEvent`. One more export disambiguates query #2 and #5 in the skill.
> 2. **PKI cluster + database** — still unknown. Both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd` on `idsharedwus` returned zero tables on this account. Need explicit cluster URI + DB name + table name (or confirmation that the panel pulls from a non-Kusto source).
> 3. **`_application_Version` allowlist (37 builds) — auto-discovered or manually curated?** If auto, our queries should derive the list dynamically (e.g., `dcount(ClientVersion) | top-N by count`). If manual, hard-coding the panel's list is fine and we just need a process to update it when new builds ship.
>
> ---
>
> Earlier-version open questions, status after this unblock:

1. **Which dashboard page is `#45c11f5e-b0ae-40d7-bb48-c2b1936011cc`?** Best guess: per-device drilldown. Please confirm or share the page title.
2. **PKI Health telemetry source** — both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd` returned no tables. Is the PKI panel pulling from a different cluster, or do I need elevated permissions on this cluster?
3. **How does the dashboard implement `osType == Android` on server-only tables?** Specifically `EdgeDiagnosticOperationEvent`, `RoxyHttpOperationEvent` — is there a device-registry function we should `let osLookup = ...` against, or do those panels only display when `osType == all`?
4. **Aria cluster: which database?** The Aria cluster URI is known (`https://kusto.aria.microsoft.com/f0eaa94222894be599b7cd0bc1e2ed6f`) but not the database name or which tables hold the Android GSA client telemetry. Likely a Bond/SLAP-named table — please share the table list or one sample query.
5. **AppInsights resource name** — sub `fb633419-…` is known, but which AI component is the Android GSA client emitting to? Need component name + instrumentation key (or app ID) to write meaningful traces/exceptions queries.
6. **Canonical "Active" definition** — Active Android device = "any telemetry in last N days," or "completed at least one successful tunnel handshake," or "checked in with APS"? The number changes by 2–3× depending on definition.
7. **Traffic profiles enum** — what are the valid `NetworkProfile` values? Best guess: `Internet`, `Private`, `M365`, `Microsoft365`, `PrivateAccess`. Need the canonical list to avoid silent misfilters.
8. **One panel query export** — easiest unblock: in the dashboard UI, on any panel, "Edit → Share → View query" gives the exact KQL. One export per page would let me go from hypothesis to real in minutes.

---

## Ground Truth From Panel KQL (2026-06-05)

Saloni pasted the verbatim KQL from one panel of the production dashboard. Treat the following as authoritative; previous hypotheses are reconciled below.

### Confirmed facts

| Fact | Value | Source |
|---|---|---|
| Primary table for tunnel/connection KPIs | `TunnelServerOperationEvents` | Panel KQL `FROM` clause |
| Cluster / Database | `idsharedwus` / `NaasProd` | `azure-mcp-kusto kusto_table_schema` succeeded there |
| Time column | `TIMESTAMP` (uppercase; `PreciseTimeStamp` also exists but unused by panel) | Panel KQL + live schema |
| Android filter (canonical) | `DeviceOs has_cs 'ANDROID'` | Panel KQL — case-sensitive `has_cs`, value literally `ANDROID` |
| Version column | `ClientVersion` (format `1.0.NNNN.NNNN`, e.g. `1.0.7203.0401`) | Panel KQL `_application_Version` allowlist (37 builds) |
| Tenant pivot column | `TenantId` | Panel KQL |
| Traffic-profile pivot column | `ServiceType` (URL says `trafficProfile` — DRIFT) | Panel KQL + schema |
| Device pivot column | `DeviceId` | Schema (column exists; panel doesn't use but #7 will) |
| Default time window | 7 days back, anchored at 12:00 UTC daily | Panel literals `2026-05-29T12:00:00Z` → `2026-06-05T12:00:00Z` |
| `_osType` URL value `v-ANDROID` | Dashboard-binding syntax — `v-` prefix means "value", real column value is just `ANDROID` | Panel KQL `let _osType = 'ANDROID'` |
| Panel verbatim execution result | 8 distinct active Android tenants in 7d window | Run via `azure-mcp-kusto kusto_query` |

### Schema introspection — `TunnelServerOperationEvents` columns relevant to daily report

- **Identity / scoping:** `TIMESTAMP`, `DeviceOs`, `DeviceOsVersion`, `ClientVersion`, `ClientOsType`, `ClientOsName`, `ClientOsVersion`, `ClientAgentVersion`, `TenantId`, `DeviceId`, `UserId`, `Region`, `NaasSDPRing`, `ServiceType`, `SkuType`
- **Operation / outcome:** `OperationName`, `Status`, `Msg`, `Message`, `error`, `stacktrace`, `FlowStatusError`, `FlowErrorClassification`, `LogType`
- **Performance:** `LatencyMs` (long) — gives us p50/p95/p99 latency natively; no separate insight-event join needed
- **Flow / correlation:** `FlowCorrelationId`, `flowId`, `originalFlowId`, `TunnelId`, `TunnelType`, `TunnelCorrelationId`, `SessionId`, `CorrelationId`
- **Network:** `SourceIp`, `SourcePort`, `DestinationIp`, `DestinationPort`, `DestinationFqdn`, `BranchSourceIp`, `Vip`, `NetworkProtocol`, `TransportProtocol`, `InnerFlow*` (8 columns)
- **Auth:** `Token1PClaims`, `Token3PUniqueId`, `Token3PIssuedAt`, `Token3PValidFrom`, `Token3PExpiry`, `Token3PRepScope`, `IsNoTokenFlow`
- **Schema notes:** A handful of columns appear corrupted/concatenated in the schema response (e.g. `SoTransportProtocol`, `TunnelTypNaasPolicyIds`, `SournnerFlowDestinationPort`, `DestinatiedAt`). Either the introspection truncated, or the table really has malformed column names. **Schema drift to flag** — re-run schema next session and confirm whether these are real or an MCP-response artifact.

### Relationship vs prior tables in our inventory

| Table | Relationship to `TunnelServerOperationEvents` |
|---|---|
| `EdgeDiagnosticOperationEvent` | **Complementary, not alternate.** Edge is the HTTP-layer (request/response/duration with `ResponseCode`); Tunnel is the L4/flow-layer view. For tunnel-success / latency / flow errors, prefer `TunnelServerOperationEvents`. For HTTP 4xx/5xx, prefer `EdgeDiagnosticOperationEvent`. Edge has NO `DeviceOs` column; Tunnel has it natively. |
| `NaaSVPNZtnaConnectionLogsEvent` | **Alternate (Aria-envelope) view of overlapping signal.** Carries `env_os = "Android"`; Tunnel carries `DeviceOs has_cs 'ANDROID'`. Two filter idioms in the codebase. ZTNA log is gateway-side; if a client never reaches a gateway, only client-side Aria sees it. Use ZTNA as a cross-check view, not the primary. |
| `NaaSVPNTunnelInsightEvent` | Likely complementary (per-flow insight rows), not yet schema-introspected. Open question whether it's needed once `LatencyMs` on `TunnelServerOperationEvents` is in play. |

### Panel-to-Report Mapping — reconciled

| Report row | Hypothesized panel | Hypothesized table | Reconciled status |
|---|---|---|---|
| Active Android Clients (weekday) | "Active Devices" tile | `EdgeDiagnosticOperationEvent` join + Aria | **CONTRADICTED** — actual mechanism (per Saloni's panel) is `TunnelServerOperationEvents | where DeviceOs has_cs 'ANDROID' | distinct DeviceId`. No join needed. The pasted panel was the tenant variant; device variant is the same shape (skill query #7). |
| Fleet Errors (7d) | "Errors over time" / "Top error codes" | `EdgeDiagnosticOperationEvent` ResponseCode | **STILL HYPOTHESIS** — Edge HTTP-layer errors not refuted, but the dashboard may also surface `FlowStatusError` from `TunnelServerOperationEvents`. Need a second panel query to disambiguate. |
| APS Availability | "APS Get-Settings success %" | `AgentGetSettingsOperationEvent` | **STILL HYPOTHESIS** — table confirmed, Android filter idiom on APS unknown (does `DeviceOs` apply?). |
| PKI Health | (unknown panel) | (unknown table) | **STILL HYPOTHESIS / blocked** — both `NaasCloudPkiProd` DBs empty for this account. |
| Tunnel Health | "ZTNA connection success" / "Tunnel latency" | `NaaSVPNZtnaConnectionLogsEvent` + `NaaSVPNTunnelInsightEvent` | **CONTRADICTED (partly)** — preferred backing table is `TunnelServerOperationEvents` itself (`LatencyMs` native, `DeviceOs` native). ZTNA log remains a useful cross-check. |
| Android Client Version Distribution Health | "Version histogram" | Aria | **CONTRADICTED (likely)** — `ClientVersion` lives on `TunnelServerOperationEvents` directly; histogram can be built server-side without touching Aria. Format is `1.0.NNNN.NNNN`, NOT SemVer. |
| Business Growth (7d) | "New devices over time" | Aria | **STILL HYPOTHESIS** — same query shape as #7 with first-seen logic; can be done server-side. |
| Data Completeness Notes | Ingest-lag panels | All tables | **STILL HYPOTHESIS** — unchanged. |

### URL-parameter ↔ column name drift (cheat sheet)

| Dashboard URL param | Real column on `TunnelServerOperationEvents` |
|---|---|
| `p-_osType=v-ANDROID` | `DeviceOs` (value `ANDROID`, no `v-` prefix) |
| `p-_trafficProfile=…` | `ServiceType` |
| `p-_tenantId=…` | `TenantId` |
| `p-device_id=v-DeviceIdPII_…` | `DeviceId` |
| `p-_startTime=7days` / `p-_endTime=now` | `TIMESTAMP between (now-7d .. now)`, anchored at 12:00 UTC |

### Window anchoring detail

Panel uses `_startTime = datetime(2026-05-29T12:00:00Z)` and `_endTime = datetime(2026-06-05T12:00:00Z)` — i.e. the dashboard rounds "now" to the most recent 12:00 UTC, then walks back exactly 7d. Our reusable header (`startofday(now()) + 12h`) reproduces this convention.

### Version-format note (Android vs Windows)

Android `ClientVersion` is a **4-segment numeric** build identifier (`1.0.7203.0401`). Windows uses a 3-segment SemVer-ish tag (`v2.28.96`). Reyes's daily report should NOT assume the same format string when filling the "Client Version Distribution" row across squads. The 37-build allowlist in this panel is *manually curated* in the dashboard parameter — open question whether new Android builds auto-append.
