# Skill: android-kusto-starter

**Owner:** Scully
**Created:** 2026-06-05
**Last reconciled:** 2026-06-05 (against the Defender-for-Android team's `IcmBaselineQueries.md` — production-vetted livesite queries — AND against the upstream GSA Kusto Catalog AND against verbatim panel KQL from dashboard `8a1fa78a-…`)
**Confidence (overall):** MEDIUM-HIGH. Server-side queries (1–8, 11) are catalog- and panel-confirmed; #6 has been live-executed. Client-side queries (CL-A through CL-N, formerly query #9) are ADOPTED VERBATIM from the Defender-for-Android ICM baseline — production-vetted but not yet re-executed by this squad. Confidence levels are per-query below.

---

## Canonical routing — by cluster family

The Android GSA daily-report draws from **three Kusto surfaces** (plus one external AI REST endpoint that is now demoted to "cross-check only"):

| Surface | Cluster URL | Database | Used for | Filter idiom | Time col |
|---|---|---|---|---|---|
| **Server-side primary** | `idsharedwus.kusto.windows.net` | `NaasProd` | Tunnel KPIs, active devices/tenants, edge errors | `DeviceOs has_cs 'ANDROID'` | `TIMESTAMP` |
| **Server-side full set** | `idsharedscus.southcentralus.kusto.windows.net` | `NaasProd` | Roxy, Talon, ControlTower, NaaSVPN*, CertMonitor | mixed (see slice) | mixed |
| **Server-side PKI** | `idsharedwus.kusto.windows.net` | `NaasCloudPkiProd` | Cert enrollment | TBD (catalog says all platforms emit) | `PreciseTimeStamp` |
| **Server-side APS** | `idsharedwus.kusto.windows.net` | `NaasAgentServicesApsProd` | Get-settings / ack success | TBD (likely env_os) | `TIMESTAMP` / `PreciseTimeStamp` |
| **Client-side primary** ✨ NEW | `mdatpandroidcluster.westus2.kusto.windows.net` | `MDATPAndroidDB` | All Android client events incl. NaaS/GSA call sites | (implicit — entire cluster is Android) | `timestamp` |
| Aria xplat (cross-check) | `kusto.aria.microsoft.com` | `f0eaa94222894be599b7cd0bc1e2ed6f` | Cross-check only — Android opportunistic in `mnap_xplat_*` | `App_Platform == 'Android'` | `EventInfo_Time` |
| Android perf rollups | `androidgsa.eastus.kusto.windows.net` | `Metric` | CPU/mem/throughput per AppVersion | (implicit) | `ingestion_time()` |
| App Insights (deprioritized) | `https://api.applicationinsights.io/v1/apps/<appId>/query` | `wd-prod-android-client` | Cross-check only — most signal duplicates the ADX cluster | (implicit) | `timestamp` |

**Why two client-side routes?** The GSA Android client ships inside the Defender for Android app. Its telemetry is emitted via `MDAppTelemetry.trackEvent(…)`. The Defender ADX cluster (`mdatpandroidcluster`) is the operationally-vetted query surface used by their livesite team — and is Kusto-native (queryable via `azure-mcp-kusto`). The catalog's `wd-prod-android-client` AI resource is most likely a sibling export of the same events; until verified, treat ADX as primary and AI as cross-check.

**Server-side primary table** (`TunnelServerOperationEvents`) conventions — unchanged from prior reconciliation:

| What | Value |
|---|---|
| Primary table for tunnel KPIs | `TunnelServerOperationEvents` |
| Time column | `TIMESTAMP` (uppercase) |
| Android filter (canonical) | `\| where DeviceOs has_cs 'ANDROID'` |
| Version column | `ClientVersion` (`1.0.NNNN.NNNN`, 4-segment numeric — NOT SemVer) |
| Tenant pivot | `TenantId` |
| Traffic-profile pivot | `ServiceType` |
| Device pivot | `DeviceId` |
| Default lookback | 7 days, anchored at 12:00 UTC daily |

---

## Section index — aligned to daily-livesite-report skeleton

| Report section | Server-side queries | Client-side queries (ICM baseline) |
|---|---|---|
| **Executive Summary** (signals to lead with) | #6, #7 | CL-A1, CL-A2, CL-A3 |
| **Key Metrics → Active Android Clients** | #6, #7 | CL-E1, CL-B3 |
| **Key Metrics → Fleet Errors (7d)** | #2 | CL-A1, CL-A2 |
| **Key Metrics → APS Availability** | #3 (server) | CL-D2 (client heartbeat proxy) |
| **Key Metrics → PKI Health** | #8 | *(not covered — server-side only)* |
| **Key Metrics → Tunnel Health** | #5 (server success/latency) | CL-N1, CL-N2, CL-N6, CL-N7, CL-N8, CL-N9 (client failure attribution) |
| **Key Metrics → Version Distribution** | (`ClientVersion` summarize on #6/#7) | CL-E1 |
| **Key Metrics → Business Growth (7d)** | #6 by day | CL-B3 |
| **Top Insights → Auth regression** | — | CL-D1, CL-N3, CL-N4, CL-N5 |
| **Top Insights → APS / config degradation** | #3 | CL-D2, CL-D6, CL-E2 |
| **Top Insights → Feature toggle / policy changes** | — | CL-N10, CL-N11, CL-N8 |
| **Cross-Domain Correlation** | server + client by `TenantId` / `DeviceId` join | CL-N5, CL-N12, CL-E2 |
| **Drilldowns (per-tenant / per-device)** | filter #2/#5/#6 by tenant | CL-B1, CL-B2, CL-C1, CL-C2, CL-C3, CL-D5, CL-N12 |
| **Data Quality Notes** | schema-introspection followups | CL-E3, CL-C1 caveat (androidId truncation) |
| Aria cross-check | — | #11 |
| Perf rollups (not in daily KPIs today) | — | #10 |

---

# Part 1 — Server-side queries (NaasProd family)

Sources cited per query: **panel-derived** (Saloni's verbatim dashboard KQL), **catalog-derived** (upstream `gsa-kusto-catalog`), or **squad-original**.

## 1. Active Android Devices — Edge Diagnostic variant (superseded)
**Source:** squad-original • **Confidence:** LOW • **Status:** superseded by #7. Kept only as a placeholder if HTTP-layer Edge data ever becomes the cohort source. Use #7.

## 2. Fleet Errors (7d) — Android cohort
**Source:** squad-original (panel-aligned) • **Confidence:** MEDIUM • **Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents` • **Answers:** Server-side L4/tunnel error breakdown by classification.

```kusto
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
let _osType    = 'ANDROID';
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| where isnotempty(FlowStatusError) or isnotempty(FlowErrorClassification) or Status !in ('Success','OK','Completed','')
| summarize ErrorCount=count(), DistinctDevs=dcount(DeviceId), DistinctTens=dcount(TenantId)
            by FlowErrorClassification, OperationName
| order by ErrorCount desc
| take 50
```

## 3. APS Availability — server-side (Get-Settings)
**Source:** squad-original • **Confidence:** LOW-MEDIUM • **Cluster/DB/Table:** `idsharedwus / NaasAgentServicesApsProd / AgentGetSettingsOperationEvent` • **Status:** Android filter idiom TBD — schema introspection still owed.

```kusto
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
AgentGetSettingsOperationEvent
| where TIMESTAMP between (_startTime .. _endTime)
// | where <android_filter>   // <-- TBD
| summarize Total=count(), Successes=countif(ResultType == "Success") by bin(TIMESTAMP, 1h)
| extend AvailabilityPct = todouble(Successes) * 100.0 / Total
| order by TIMESTAMP desc
```

## 4. PKI (routing placeholder)
**Source:** catalog-derived • **Confidence:** LOW-MEDIUM (routing only) • Superseded operationally by #8 (same routing, with sketch). See #8.

## 5. Tunnel Health — server-side success + latency
**Source:** panel-derived + catalog-aligned • **Confidence:** MEDIUM • **Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents` • **Answers:** Success rate + p50/p95/p99 latency by region.

```kusto
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
let _osType    = 'ANDROID';
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| summarize Total=count(),
            Failures=countif(isnotempty(FlowStatusError)),
            p50Latency=percentile(LatencyMs, 50),
            p95Latency=percentile(LatencyMs, 95),
            p99Latency=percentile(LatencyMs, 99)
            by bin(TIMESTAMP, 1h), Region
| extend SuccessPct = todouble(Total - Failures) * 100.0 / Total
| order by TIMESTAMP desc
```

**Companion ZTNA-gateway view** (`naas-idsharedscus / NaasProd / NaaSVPNZtnaConnectionLogsEvent`, filter `env_os == "Android"`, time `env_time`) — same shape as before. Keep for cross-checks.

## 6. Active Android Tenants (7d distinct) — verbatim panel mirror ✅
**Source:** panel-derived (verbatim from dashboard `8a1fa78a-…`) • **Confidence:** HIGH — executed 2026-06-05, returned 8 distinct tenants • **Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`

```kusto
let _application_Version = dynamic([
  '1.0.6329.0101','1.0.6404.0102','1.0.6423.0101','1.0.6508.0101','1.0.6521.0101',
  '1.0.6611.0101','1.0.6611.0401','1.0.6620.0101','1.0.6620.0401','1.0.6704.0101',
  '1.0.6704.0401','1.0.6716.0101','1.0.6716.0401','1.0.6812.0101','1.0.6812.0401',
  '1.0.6829.0101','1.0.6910.0102','1.0.6910.0402','1.0.6919.0401','1.0.7001.0101',
  '1.0.7001.0401','1.0.7004.0103','1.0.7004.0403','1.0.7015.0102','1.0.7015.0403',
  '1.0.7105.0101','1.0.7105.0401','1.0.7112.0102','1.0.7119.0401','1.0.7125.0401',
  '1.0.7127.0401','1.0.7128.0101','1.0.7128.0401','1.0.7128.0402','1.0.7203.0101',
  '1.0.7203.0104','1.0.7203.0401'
]);
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
let _osType    = 'ANDROID';
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| where ClientVersion in (_application_Version)
| distinct TenantId
| count
```

## 7. Active Android Devices (7d distinct)
**Source:** squad-original (panel-aligned) • **Confidence:** MEDIUM-HIGH • Same as #6, swap final two lines for `summarize ActiveDevices = dcount(DeviceId)`.

## 8. PKI Cert Enrollment Health
**Source:** catalog-derived • **Confidence:** LOW-MEDIUM (routing confirmed; schema TBD) • **Cluster/DB/Table:** `idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` • **Time col:** `PreciseTimeStamp`

```kusto
// !! Run kusto_table_schema first. Replace placeholders.
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
EnrollCertificateOperationSummary
| where PreciseTimeStamp between (_startTime .. _endTime)
// | where <android_filter>           // <-- TBD
| summarize Total=count(),
            Successes=countif(<status_col> in ('Success','OK','Completed'))
            by bin(PreciseTimeStamp, 1h)
| extend SuccessPct = todouble(Successes) * 100.0 / Total
| order by PreciseTimeStamp desc
```

## 10. Android Perf Rollups (CPU / Memory / Throughput)
**Source:** catalog-derived • **Confidence:** LOW • **Cluster/DB/Table:** `androidgsa.eastus.kusto.windows.net / Metric / {MemoryCPUUsage, UploadDownloadSpeed}` • **Status:** Cluster not yet reachability-verified (catalog flag: DNS failed at generation). Not currently on the daily-report metric list — keep for future perf section.

## 11. Aria Cross-Check — Android error events
**Source:** catalog-derived (alias `gsa-android-errors-1h`) • **Confidence:** MEDIUM • **Cluster/DB/Table:** `kusto.aria.microsoft.com / f0eaa94222894be599b7cd0bc1e2ed6f / mnap_xplat_telemetryprod_errorevent` • **Time col:** `EventInfo_Time` • **Filter:** `App_Platform == 'Android'`. Use only when App Insights / ADX ingest is suspect.

---

# Part 2 — Client-side queries (Defender-for-Android ICM baseline)

All queries below are **adopted verbatim from the Defender-for-Android team's `IcmBaselineQueries.md`** (production-vetted, run during real livesite incidents). They target:

- **Cluster:** `https://mdatpandroidcluster.westus2.kusto.windows.net/`
- **Database:** `MDATPAndroidDB`
- **Source table:** `customEvents` — but always prefer the routed subtable when available (faster, pre-unpacked properties)

**Subtable directory** (from `TelemetrySubtables.md`):

| Subtable | Domain | Events |
|---|---|---|
| `TelemetryMalwareScan` | scan/threat/ML | 76 |
| `TelemetryAuth` | sign-in/MSAL/token | 41 |
| `TelemetryCompliance` | MAM/TVM/enrollment/EDR-registration | 63 |
| `TelemetryVPNAndWebProtection` | VPN/antiphishing/**NaaS**/Edge/captive-portal | 96 |
| `TelemetryAppLifecycle` | app states/onboarding/permissions/FRE | 89 |
| `TelemetryHeartbeat` | heartbeat reporting + EDR heartbeat | 16 |
| `TelemetryNetworkMonitoring` | network/WiFi/CA certs | 29 |
| `TelemetryConfiguration` | ECS/admin configs/feature flags | 12 |
| `TelemetryProductHeartbeat` | dedicated product heartbeat | 1 |
| `TelemetryGeneral` | catch-all (incl. `SevereLog`, `ErrorScenario`) | 209 |

**Placeholders** (replace before run): `__TENANT__`, `__ANDROID_ID__`, `__MACHINE_ID__`, `__ORG_ID__`, `__START__`, `__END__`, `__SEARCH_TERM__`.

**Confidence on every query in this section: HIGH** (source is production-vetted ICM baseline). Re-execution by this squad is owed as a smoke-test in the next round, but the query bodies are not in doubt.

## Triage — "Is something burning?"

### CL-A1. Overall error volume — last 24h
*Report use:* Executive Summary lead signal; Fleet Errors metric.

```kql
TelemetryGeneral
| where timestamp > ago(24h)
| where name in ("SevereLog", "ErrorScenario")
| summarize Count=count() by bin(timestamp, 1h), name
| order by timestamp asc
```

### CL-A2. Top error events — last 24h
```kql
customEvents
| where timestamp > ago(24h)
| where name has "Error" or name has "Failed" or name has "Exception" or name has "Crash"
| summarize Count=count() by name
| order by Count desc
| take 25
```

### CL-A3. App crashes / lifecycle anomalies — last 24h
*Report use:* Executive Summary; client-stability headline.

```kql
TelemetryAppLifecycle
| where timestamp > ago(24h)
| where name has_any ("Crash", "Anr", "Boot", "ServiceLifeCycle")
| summarize Count=count() by name, AppVersion=tostring(EventProperty.AppVersion)
| order by Count desc
| take 50
```

## Tenant / Customer Impact

### CL-B1. All activity for a tenant — incident window
```kql
customEvents
| where timestamp between (datetime(__START__) .. datetime(__END__))
| where tenantId == "__TENANT__"
| summarize Count=count(), Devices=dcount(androidId) by name
| order by Count desc
```

### CL-B2. Error events for a tenant (7d)
```kql
customEvents
| where timestamp > ago(7d)
| where tenantId == "__TENANT__"
| where name has_any ("Error", "Failed", "Exception")
| summarize Count=count() by name
| order by Count desc
```

### CL-B3. Affected device count vs. baseline (14d trend per tenant)
*Report use:* Business Growth metric (per-tenant); Active Android Clients drill-down.

```kql
customEvents
| where timestamp > ago(14d)
| where tenantId == "__TENANT__"
| summarize Devices=dcount(androidId) by bin(timestamp, 1d)
| order by timestamp asc
```

## Single Device Deep-Dive

### CL-C1. Recent events for a device (`androidId`)
*Data-quality caveat:* If 0 rows, `androidId` is often truncated by 3 chars. Retry:
`where androidId startswith substring("__ANDROID_ID__", 0, strlen("__ANDROID_ID__") - 3)`

```kql
customEvents
| where timestamp > ago(7d)
| where androidId == "__ANDROID_ID__"
| project timestamp, name, EventProperty
| order by timestamp desc
| take 200
```

### CL-C2. Events for a `machineId` (nested in `EventProperty`)
```kql
customEvents
| where timestamp > ago(7d)
| where tostring(EventProperty.machineId) == "__MACHINE_ID__"
| project timestamp, name, androidId, tenantId, EventProperty
| order by timestamp desc
| take 200
```

### CL-C3. App + OS version of a device
```kql
TelemetryAppLifecycle
| where timestamp > ago(7d)
| where androidId == "__ANDROID_ID__"
| project timestamp, name,
          AppVersion=tostring(EventProperty.AppVersion),
          OsVersion=tostring(EventProperty.OsVersion),
          Ring=tostring(EventProperty.Ring),
          Audience=tostring(EventProperty.Audience)
| order by timestamp desc
| take 20
```

## Domain-Specific

### CL-D1. Authentication failures for a tenant (24h)
*Report use:* Top Insights → auth regression.

```kql
TelemetryAuth
| where timestamp > ago(24h)
| where tenantId == "__TENANT__"
| where name has_any ("Failed", "Error", "Cancelled")
| summarize Count=count() by name, ErrorCode=tostring(ErrorCode)
| order by Count desc
```

### CL-D2. Heartbeat health — last 24h
*Report use:* APS/policy degradation proxy (client-side heartbeat is the closest client signal to APS health).

```kql
TelemetryHeartbeat
| where timestamp > ago(24h)
| summarize Reported=countif(name == "HeartbeatReported"),
            Failures=countif(name startswith "HeartbeatFailure")
            by bin(timestamp, 1h)
| extend FailureRate = round(100.0 * Failures / (Reported + Failures), 2)
| order by timestamp asc
```

### CL-D3. VPN / Web protection errors (broad)
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name has_any ("Error", "Failed", "Disconnect")
| summarize Count=count() by name, Reason=tostring(EventProperty.Reason)
| order by Count desc
| take 30
```

### CL-D4. Malware scan failures
```kql
TelemetryMalwareScan
| where timestamp > ago(24h)
| where name has_any ("Failed", "Error") or name == "ScanAborted"
| summarize Count=count() by name
| order by Count desc
```

### CL-D5. TVM app inventory issues for an org (7d)
```kql
TelemetryCompliance
| where timestamp > ago(7d)
| where tostring(EventProperty.orgId) == "__ORG_ID__"
| where name has_any ("TVM", "AppInventory")
| project timestamp, name, androidId, tenantId, EventProperty
| order by timestamp desc
| take 100
```

### CL-D6. Compliance / enrollment failures (per tenant, 7d)
```kql
TelemetryCompliance
| where timestamp > ago(7d)
| where tenantId == "__TENANT__"
| where name has_any ("MAM", "Enrollment", "Compliance")
| where name has_any ("Failed", "Error")
| summarize Count=count() by name
| order by Count desc
```

## Correlation Helpers

### CL-E1. App version distribution for affected tenant
*Report use:* Version Distribution Health metric.

```kql
TelemetryAppLifecycle
| where timestamp > ago(24h)
| where tenantId == "__TENANT__"
| summarize Devices=dcount(androidId) by AppVersion=tostring(EventProperty.AppVersion)
| order by Devices desc
```

### CL-E2. ECS / config refresh events for a device (7d)
```kql
TelemetryConfiguration
| where timestamp > ago(7d)
| where androidId == "__ANDROID_ID__"
| project timestamp, name, EventProperty
| order by timestamp desc
| take 50
```

### CL-E3. Find an event-name by search term (schema discovery)
*Report use:* Data Quality Notes; never put in metric rows directly.

```kql
customEvents
| where timestamp > ago(1d)
| where name has "__SEARCH_TERM__"
| summarize Count=count(), Devices=dcount(androidId) by name
| order by Count desc
```

## NaaS — Call-Site-Targeted (Section N from ICM baseline)

All NaaS events fire via `NaaSTelemetrySender.logTelemetry(...)` which sets `EventProperty.SubEvent = "NaaS"` (stable filter), `EventProperty.DeviceId`, `EventProperty.Message` (free-form — **uniquely identifies call site** when event name is shared).

**Call-site → event map** (preserved from ICM baseline — re-derive only if `features/naas-vpn/` adds new call sites):

| Call site | Event `name` | Distinguishing field |
|---|---|---|
| `NaaSDNSResolver.kt:72` | `DNSServerExtractionFailed` | — |
| `NaaSVPNClient.kt:213` (connect) | `NaaSAdminConfigSet` | `Message` ∈ {"true","false"} |
| `NaaSVPNClient.kt:218` (startMgmtService) | `NaasVPNFailure` | `Message` starts with `"Connecting failed"` |
| `NaaSVPNClient.kt:243` (performIo) | `NaasVPNFailure` | `Message` starts with `"Running failed"` |
| `NaaSAuthenticator.kt:243` (silent) | `NaasSilentAuthenticationFailure` | MSAL fields + `tenantId`, `request` |
| `NaaSAuthenticator.kt:311` (interactive) | `NaasAuthenticationFailure` | `tenantId`, `tenantName`, `appId`, `msalErrorCode` |
| `ConnectFragment.kt:114` | `GSAPAUpdated` | `Message` starts with `"NaaS PA updated by user"` |
| `AppConfigChangeEventListener.kt:63` | `GSAPAUpdated` | `Message` starts with `"NaaS PA Updated from admin config"` |
| `AppConfigChangeEventListener.kt:74` | `GSAPAUpdated` | `Message` starts with `"NaaS Private Channel Updated from admin"` |
| `NetworkChangeEventListener.kt:83,95` | `NaaSCaptivePortal` | `Status` ∈ {DETECTED, CONNECTED} |
| `NaaSCertificateHandler.kt:253` | `NaaSCertificateHandleError` | `Message` = error text |
| `NaaSViewModel.kt:146` | `NaaSClientToggleUpdated` | `Message` = `"NaaS Client toggle <state>"` |

### CL-N1. NaaS VPN failure — config phase vs run/IO phase
*Report use:* Tunnel Health (client-side failure attribution).

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaasVPNFailure"
| extend Phase = case(
    tostring(EventProperty.Message) startswith "Connecting failed",  "Config",
    tostring(EventProperty.Message) startswith "Running failed",     "IO/Run",
    "Other")
| summarize Count=count(), Devices=dcount(androidId) by Phase
| order by Count desc
```

### CL-N2. NaaS VPN failure — top distinct error messages per phase
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaasVPNFailure"
| extend Phase = iff(tostring(EventProperty.Message) startswith "Connecting failed", "Config", "IO/Run"),
         ErrorTail = extract(@":\s*(.+)$", 1, tostring(EventProperty.Message))
| summarize Count=count(), Devices=dcount(androidId) by Phase, ErrorTail
| order by Count desc
| take 30
```

### CL-N3. NaaS silent auth failures — MSAL error breakdown
*Report use:* Top Insights → auth regression (silent-token path).

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaasSilentAuthenticationFailure"
| extend MsalErrorCode     = tostring(EventProperty.msalErrorCode),
         MsalErrorCategory = tostring(EventProperty.msalErrorCategory),
         MsalErrorMessage  = tostring(EventProperty.msalErrorMessage),
         TenantId          = tostring(EventProperty.tenantId)
| summarize Count=count(), Devices=dcount(androidId)
            by MsalErrorCode, MsalErrorCategory, MsalErrorMessage
| order by Count desc
| take 25
```

### CL-N4. NaaS interactive auth failures — by tenant + appId
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaasAuthenticationFailure"
| extend TenantId   = tostring(EventProperty.tenantId),
         TenantName = tostring(EventProperty.tenantName),
         AppId      = tostring(EventProperty.appId),
         MsalCode   = tostring(EventProperty.msalErrorCode)
| summarize Count=count(), Devices=dcount(androidId) by TenantId, TenantName, AppId, MsalCode
| order by Count desc
| take 25
```

### CL-N5. NaaS auth funnel — silent vs interactive (per tenant, 7d)
*Report use:* Cross-Domain Correlation timeline.

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(7d)
| where tenantId == "__TENANT__"
| where name in ("NaasSilentAuthenticationFailure",
                 "NaasAuthenticationFailure",
                 "NaasAuthenticationSuccess")
| extend Kind = case(name == "NaasSilentAuthenticationFailure", "SilentFail",
                     name == "NaasAuthenticationFailure",      "InteractiveFail",
                     "Success")
| summarize Count=count(), Devices=dcount(androidId) by bin(timestamp, 1h), Kind
| order by timestamp asc
```

### CL-N6. DNS extraction failed on network change
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "DNSServerExtractionFailed"
| summarize Count=count(), Devices=dcount(androidId), Tenants=dcount(tenantId)
            by bin(timestamp, 1h)
| order by timestamp asc
```

### CL-N7. Captive portal lifecycle (detected vs connected)
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaaSCaptivePortal"
| extend Status = tostring(EventProperty.Status)
| summarize Count=count(), Devices=dcount(androidId) by Status, bin(timestamp, 1h)
| order by timestamp asc
```

### CL-N8. Admin-config delivery — was NaaS configured at connect time?
*Report use:* Top Insights → policy-delivery anomalies.

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaaSAdminConfigSet"
| extend IsAdminConfigSet = tostring(EventProperty.Message)
| summarize Connects=count(), Devices=dcount(androidId), Tenants=dcount(tenantId)
            by IsAdminConfigSet, bin(timestamp, 1h)
| order by timestamp asc
```

### CL-N9. Certificate handler errors (mTLS / cert pinning)
*Report use:* PKI Health (client-side cross-check; server-side via #8).

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "NaaSCertificateHandleError"
| extend Err = tostring(EventProperty.Message)
| summarize Count=count(), Devices=dcount(androidId) by Err
| order by Count desc
| take 25
```

### CL-N10. GSA Private Access toggle source — user vs admin policy
*Report use:* Top Insights → feature toggle / policy change.

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(7d)
| where name == "GSAPAUpdated"
| extend Source = case(
    tostring(EventProperty.Message) startswith "NaaS PA updated by user",                     "User",
    tostring(EventProperty.Message) startswith "NaaS PA Updated from admin config",           "AdminPolicy_PA",
    tostring(EventProperty.Message) startswith "NaaS Private Channel Updated from admin",     "AdminPolicy_PrivateChannel",
    "Other")
| summarize Count=count(), Devices=dcount(androidId) by Source, bin(timestamp, 1d)
| order by timestamp asc
```

### CL-N11. NaaS client master toggle (user-initiated enable/disable)
```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(7d)
| where name == "NaaSClientToggleUpdated"
| extend State = extract(@"NaaS Client toggle (\w+)", 1, tostring(EventProperty.Message))
| summarize Count=count(), Devices=dcount(androidId), Tenants=dcount(tenantId)
            by State, bin(timestamp, 1d)
| order by timestamp asc
```

### CL-N12. Full NaaS timeline for a single device (call-site annotated)
*Report use:* Cross-Domain Correlation (per-device evidence chain).

```kql
TelemetryVPNAndWebProtection
| where timestamp > ago(3d)
| where androidId == "__ANDROID_ID__"
| where tostring(EventProperty.SubEvent) == "NaaS"
| extend CallSite = case(
    name == "NaasVPNFailure" and tostring(EventProperty.Message) startswith "Connecting failed", "NaaSVPNClient.startMgmtService",
    name == "NaasVPNFailure" and tostring(EventProperty.Message) startswith "Running failed",     "NaaSVPNClient.performIo",
    name == "NaasAuthenticationFailure",                                                          "NaaSAuthenticator.signInResult",
    name == "NaasSilentAuthenticationFailure",                                                    "NaaSAuthenticator.logSilentAuthFailureTelemetry",
    name == "DNSServerExtractionFailed",                                                          "NaaSDNSResolver",
    name == "NaaSCaptivePortal",                                                                  "NetworkChangeEventListener",
    name == "NaaSCertificateHandleError",                                                         "NaaSCertificateHandler",
    name == "NaaSAdminConfigSet",                                                                 "NaaSVPNClient (connect)",
    name == "NaaSClientToggleUpdated",                                                            "NaaSViewModel (user)",
    name == "GSAPAUpdated" and tostring(EventProperty.Message) startswith "NaaS PA updated by user",            "ConnectFragment (user)",
    name == "GSAPAUpdated" and tostring(EventProperty.Message) startswith "NaaS PA Updated from admin config",  "AppConfigChangeEventListener (admin PA)",
    name == "GSAPAUpdated" and tostring(EventProperty.Message) startswith "NaaS Private Channel Updated",       "AppConfigChangeEventListener (admin PrivateCh)",
    "Other/Unknown")
| project timestamp, name, CallSite,
          Message=tostring(EventProperty.Message),
          MsalCode=tostring(EventProperty.msalErrorCode),
          Status=tostring(EventProperty.Status),
          TenantId=tostring(EventProperty.tenantId)
| order by timestamp asc
```

---

## Symptom → Query index (ICM baseline)

| Incident symptom | Query |
|---|---|
| "Users can't connect at all" | CL-N1, CL-N2, CL-N8 |
| "Connection drops mid-session" | CL-N1 (`IO/Run`), CL-N2, CL-N7 |
| "Auth prompt fails" | CL-N4, CL-N5 |
| "Silent re-auth keeps failing in background" | CL-N3, CL-N5 |
| "Connectivity broken after WiFi change" | CL-N6, CL-N7 |
| "Cert errors" | CL-N9 (client) + #8 (server PKI) |
| "VPN says not configured" | CL-N8 (`IsAdminConfigSet == 'false'`) |
| "Feature was on, now off" | CL-N10, CL-N11 |
| "Deep-dive one device" | CL-N12, CL-C1, CL-C2 |
| "Tenant-wide spike" | CL-B1, CL-B2, CL-E1 |
| "What's burning right now" | CL-A1, CL-A2, CL-A3 |
| "Heartbeat / compliance issues" | CL-D2, CL-D6 |
| "TVM inventory missing" | CL-D5 |

---

## Upstream Sources

The query bodies, routing, and call-site map in **Part 2** are adopted from:

- **`/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/agent-docs/IcmBaselineQueries.md`** (Defender-for-Android team's production ICM baseline — source of truth for client-side livesite queries)
- `…/agent-docs/Telemetry.md` (telemetry emission rules — PascalCase, codegen, always-appended props incl. `AndroidId`, `TenantOrgName`, `MachineId`)
- `…/agent-docs/TelemetrySubtables.md` (10-subtable routing infrastructure under `MDATPAndroidDB`)

Server-side routing (**Part 1**) is anchored on:

- Upstream `gsa-kusto-catalog` skill (in `Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-kusto-catalog/`)
- This squad's local slice: [`.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md`](../gsa-kusto-catalog-android-slice/SKILL.md)
- Dashboard `8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` (verbatim panel KQL for #6)

Mapping from ICM queries to report sections is captured in: [`.squad/skills/android-icm-baseline-mapping/SKILL.md`](../android-icm-baseline-mapping/SKILL.md)

**Precedence when sources disagree:** ICM baseline (production-vetted) > catalog (registry) > squad-original (locally derived). Open a finding rather than silently overriding.

---

## Reconciliation summary — what changed in this pass

| Area | Before this pass | After |
|---|---|---|
| Client-side primary cluster | `wd-prod-android-client` AI REST (catalog-derived, not Kusto-queryable from our MCP) | `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Kusto-native, queryable via `azure-mcp-kusto`) |
| Client-side query count | 1 sketch (old #9) | 30 production-vetted queries (CL-A1…CL-N12) |
| NaaS client-side coverage | none | full call-site map + 12 NaaS-targeted queries |
| Subtable awareness | none | 10 routed subtables — query the right one for speed |
| Auth signal (client) | none | CL-D1, CL-N3, CL-N4, CL-N5 |
| Heartbeat signal (client) | none | CL-D2 |
| Server-side starters (#1–#8, #10, #11) | as-is | unchanged — they complement, do not duplicate |

## Next hardening steps

1. Smoke-test 3–5 ICM client-side queries against `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` via `azure-mcp-kusto` to confirm cluster reachability and our auth posture.
2. Schema-introspect `AgentGetSettingsOperationEvent` to close query #3's Android-cohort gap.
3. Schema-introspect `EnrollCertificateOperationSummary` to close query #8.
4. Verify reachability of `androidgsa.eastus.kusto.windows.net` (catalog flag).
5. Decide whether the legacy AI route (`wd-prod-android-client`) is needed at all once ADX route is confirmed live.
6. Open question: does `mdatpandroidcluster` retain Android events for a usable lookback (7d/14d)? Defender's queries assume yes — verify.
