# Skill: android-kusto-starter

**Owner:** Scully
**Created:** 2026-06-05
**Last reconciled:** 2026-06-05 (against verbatim panel KQL from dashboard `8a1fa78a-…` AND the upstream GSA Kusto Catalog from `Identity-gsa-client-marketplace`)
**Confidence (overall):** MEDIUM-HIGH — table + Android filter + version semantics confirmed via `azure-mcp-kusto` against live `idsharedwus / NaasProd`, AND cross-confirmed by the canonical upstream catalog (which adds the PKI route, the App Insights resource name, and the Android perf-metrics cluster). Queries 1, 2, 5, 6, 7 schema-validated; #6 executed. PKI (query 4) is now UNBLOCKED at the routing level — query body still needs schema-introspection before run. APS (query 3) still owes schema introspection. NEW queries 8 (PKI), 9 (App Insights customEvents), 10 (perf rollups), 11 (Aria errorevent cross-check) added below from catalog discovery.

## Canonical conventions (post-reconciliation)

| What | Value |
|---|---|
| Cluster | `idsharedwus.kusto.windows.net` |
| Database | `NaasProd` |
| Primary table for tunnel KPIs | `TunnelServerOperationEvents` |
| Time column | `TIMESTAMP` (uppercase) |
| **Android filter (canonical)** | `\| where DeviceOs has_cs 'ANDROID'` |
| Version column | `ClientVersion` (format `1.0.NNNN.NNNN`, NOT SemVer) |
| Tenant pivot | `TenantId` |
| Traffic-profile pivot | `ServiceType` (URL says `trafficProfile`; column says `ServiceType`) |
| Device pivot | `DeviceId` |
| Default lookback | 7 days, anchored at 12:00 UTC daily (matches dashboard) |

**Standard parameter header for every query:**
```kusto
let _endTime   = startofday(now()) + 12h;            // today 12:00 UTC
let _startTime = _endTime - 7d;                       // 7 days back, also 12:00 UTC
let _osType    = 'ANDROID';
let _tenantId  = dynamic(null);                       // null = all tenants
let _trafficProfile = dynamic(null);                  // null = all service types
// _application_Version: hard-code dashboard's 37-build allowlist OR omit
// (open question — see decision file)
```

---

## 1. Active Android Devices (7d distinct) — MIRROR of panel pattern (NEW #7 below replaces this header)

**Confidence:** MEDIUM (was: LOW)
**STATUS:** Schema-validated. Use query #7 — kept here for narrative continuity.

**Reconciliation note:** Original query used `EdgeDiagnosticOperationEvent` and assumed there was no `osType` column. That table genuinely has no `DeviceOs` column, but `TunnelServerOperationEvents` DOES — and the dashboard panel proves that's the right table for Android-scoped device counts. **Use query #7.** Old `EdgeDiagnosticOperationEvent` version is preserved for cases where Edge Diagnostic is the actual signal of interest (e.g., HTTP-layer errors); in that case still need a DeviceId-based join.

---

## 2. Fleet Errors (7d) — Android cohort

**Confidence:** MEDIUM (was: LOW)
**STATUS:** Schema-validated; not yet executed.
**Reconciliation:** Pivoted to `TunnelServerOperationEvents` since it both (a) carries `DeviceOs` natively and (b) exposes `Status`, `FlowStatusError`, `FlowErrorClassification`. Dropped the `ResponseCode >= 400` heuristic since this table doesn't carry HTTP response codes (it's a tunnel/L4 view). For HTTP-layer errors a parallel query against `EdgeDiagnosticOperationEvent` / `RoxyHttpOperationEvent` is still needed — but those panels likely live behind a different filter; ask Saloni for that panel's KQL too.

```kusto
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
let _osType    = 'ANDROID';
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| where isnotempty(FlowStatusError) or isnotempty(FlowErrorClassification) or Status !in ('Success','OK','Completed','')
| summarize ErrorCount   = count(),
            DistinctDevs = dcount(DeviceId),
            DistinctTens = dcount(TenantId)
            by FlowErrorClassification, OperationName
| order by ErrorCount desc
| take 50
```

**Caveats:**
- Success-value enum for `Status` is a guess — confirm by running `| summarize count() by Status` once.
- Doesn't cover Edge/Roxy HTTP-layer errors — those panels need separate queries.

---

## 3. APS Availability (Get-Settings success rate)

**Confidence:** LOW-MEDIUM (unchanged)
**STATUS:** untested — column names still guesses; **Android filter pattern on APS tables is unknown** (does `AgentGetSettingsOperationEvent` carry `DeviceOs`? Likely not — APS tables are Aria-style. Pending schema introspection.).

**Reconciliation:** Old filter `ClientOs == "Android"` is wrong (no such column confirmed). Need to introspect `AgentGetSettingsOperationEvent` schema and decide: `env_os == 'Android'` (Aria-style) or join to a device-OS lookup. Query body unchanged pending that decision.

```kusto
// Database: NaasAgentServicesApsProd
// !! Android-cohort filter is a TODO — see reconciliation note above.
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
AgentGetSettingsOperationEvent
| where TIMESTAMP between (_startTime .. _endTime)
// | where ???   // <-- canonical Android filter for APS tables: TBD
| summarize Total = count(),
            Successes = countif(ResultType == "Success")
            by bin(TIMESTAMP, 1h)
| extend AvailabilityPct = todouble(Successes) * 100.0 / Total
| order by TIMESTAMP desc
```

---

## 4. PKI Health

**Confidence:** LOW-MEDIUM (was ZERO — UPGRADED via catalog)
**STATUS:** Routing UNBLOCKED. Catalog identifies `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (time column `PreciseTimeStamp`) as the Cloud PKI server-side audit table; it serves all platforms (Win/Mac/iOS/Android). Same cluster we already auth into. Schema-introspect column list before running — the Android-cohort filter idiom (column-based vs DeviceId-join) is unknown.

See query #8 below for the starter shape.

---

## 5. Tunnel Health (ZTNA connection success + latency)

**Confidence:** MEDIUM (unchanged) — but now we have a SECOND, BETTER table.
**STATUS:** Original query against `NaaSVPNZtnaConnectionLogsEvent` is still valid (that table really does carry `env_os`). However, for the daily report's "Tunnel Health" row we should prefer `TunnelServerOperationEvents` because (a) it's what the dashboard panels use, (b) it has a native `LatencyMs` column, and (c) it carries the Android filter as `DeviceOs has_cs 'ANDROID'` directly.

**Replacement (preferred):**
```kusto
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
let _osType    = 'ANDROID';
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| summarize Total       = count(),
            Failures    = countif(isnotempty(FlowStatusError)),
            p50Latency  = percentile(LatencyMs, 50),
            p95Latency  = percentile(LatencyMs, 95),
            p99Latency  = percentile(LatencyMs, 99)
            by bin(TIMESTAMP, 1h), Region
| extend SuccessPct = todouble(Total - Failures) * 100.0 / Total
| order by TIMESTAMP desc
```

**Companion (gateway-side ZTNA view, original — keep):**
```kusto
NaaSVPNZtnaConnectionLogsEvent
| where env_time between (ago(7d) .. now())
| where env_os == "Android"
| summarize Total = count(),
            Connects = countif(TraceLevel <= 2),
            Failures = countif(TraceLevel >= 4)
            by bin(env_time, 1h), Region
| extend SuccessPct = todouble(Connects) * 100.0 / Total
```

**Caveats:**
- Two views (server-op vs ZTNA gateway log) should agree within ingest-lag tolerance; if they diverge, that's a finding to chase.
- `Status` enum still needs `summarize count() by Status` to nail down the success-value list.

---

## 6. Active Android Tenants (7d distinct) — VERBATIM panel mirror ✅

**Confidence:** HIGH
**STATUS:** Schema-validated AND executed successfully via `azure-mcp-kusto` on 2026-06-05. Returned 8 distinct tenants for the window 2026-05-29 12:00 UTC → 2026-06-05 12:00 UTC. This IS the dashboard panel.
**Source:** Saloni pasted KQL from the production dashboard panel.

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
let _tenantId  = dynamic(null);
let _trafficProfile = dynamic(null);
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| where ClientVersion in (_application_Version)
| where isempty(_trafficProfile) or ServiceType in (_trafficProfile)
| where isempty(_tenantId)       or TenantId    in (_tenantId)
| distinct TenantId
| count
```

**Caveats:**
- The 37-build version allowlist is hard-coded; if a new Android build ships and isn't appended, this query silently under-counts. Dynamic-discovery alternative: drop the `ClientVersion in (...)` line entirely (broader cohort).

---

## 7. Active Android Devices (7d distinct) ✨ NEW

**Confidence:** MEDIUM-HIGH
**STATUS:** Schema-validated (`DeviceId` column confirmed present on `TunnelServerOperationEvents`). Same shape as #6 with `dcount(DeviceId)`.

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
let _tenantId  = dynamic(null);
let _trafficProfile = dynamic(null);
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType
| where ClientVersion in (_application_Version)
| where isempty(_trafficProfile) or ServiceType in (_trafficProfile)
| where isempty(_tenantId)       or TenantId    in (_tenantId)
| summarize ActiveDevices = dcount(DeviceId)
```

**Caveats:**
- "Active" definition here = "any tunnel-server operation event in the window." If the dashboard panel uses a stricter definition (e.g., must have at least one successful flow), our number will run hot. Open question for Saloni.
- Daily breakdown variant: replace the trailing summarize with `summarize ActiveDevices = dcount(DeviceId) by bin(TIMESTAMP, 1d) | order by TIMESTAMP desc`.

---

## 8. PKI Cert Enrollment Health (NEW — catalog-derived) ✨

**Confidence:** LOW-MEDIUM
**STATUS:** Routing confirmed via upstream catalog. Schema NOT YET introspected — column names and Android filter are TBDs. Do NOT run without first running `kusto_table_schema` on `EnrollCertificateOperationSummary`.

**Cluster / DB / Table:** `idsharedwus.kusto.windows.net` / `NaasCloudPkiProd` / `EnrollCertificateOperationSummary`
**Time column:** `PreciseTimeStamp` (NOT `TIMESTAMP`).

```kusto
// !! Run kusto_table_schema first. Replace <android_filter> with the right column.
// Catalog says all platforms emit; column may be DeviceOs / Platform / OsType, OR
// Android scoping may require DeviceId-join against TunnelServerOperationEvents.
let _endTime   = startofday(now()) + 12h;
let _startTime = _endTime - 7d;
EnrollCertificateOperationSummary
| where PreciseTimeStamp between (_startTime .. _endTime)
// | where <android_filter>           // <-- TBD after schema introspection
| summarize Total      = count(),
            Successes  = countif(<status_col> in ('Success','OK','Completed'))
            by bin(PreciseTimeStamp, 1h)
| extend SuccessPct = todouble(Successes) * 100.0 / Total
| order by PreciseTimeStamp desc
```

**Caveats:**
- `<status_col>` and `<android_filter>` are placeholders. Will be resolved next round when schema is introspected.
- This is the server-side view (every PKI API request). A client-side cross-check would be the AI `wd-prod-android-client / customEvents` filtered to cert-enrollment events (query #9).

---

## 9. Android App Insights — Active devices + error rate (NEW — catalog-derived) ✨

**Confidence:** LOW-MEDIUM
**STATUS:** Routing confirmed (catalog: `android-appinsights / wd-prod-android-client`). Endpoint is the App Insights REST API (`https://api.applicationinsights.io/v1/apps/<appId>/query`), NOT a Kusto cluster URL. Use AI portal "Logs" blade or AI REST API; `azure-mcp-kusto` will NOT route here. Schema is standard App Insights (`customEvents`, `exceptions`, `traces`, `requests`, `dependencies`, `customMetrics`).

```kusto
// Active Android devices (7d) — App Insights
customEvents
| where timestamp between (ago(7d) .. now())
| extend AndroidId = tostring(customDimensions['AndroidId'])
| extend TenantOrgName = tostring(customDimensions['TenantOrgName'])
| where isnotempty(AndroidId)
| summarize ActiveDevices = dcount(AndroidId),
            ActiveTenants = dcount(TenantOrgName)
            by bin(timestamp, 1d)
| order by timestamp desc
```

```kusto
// Android exception rate by version (7d) — App Insights
exceptions
| where timestamp between (ago(7d) .. now())
| summarize Exceptions = count() by application_Version, bin(timestamp, 1d)
| order by timestamp desc, Exceptions desc
```

**Caveats:**
- `application_Version` on AI is the same `1.0.NNNN.NNNN` Android build format as on `TunnelServerOperationEvents.ClientVersion`.
- `AndroidId` is the catalog's recommended device-identity key for AI; verify the exact `customDimensions` key matches the live AI schema before relying on it (catalog says `AndroidId`, but customDimensions key casing varies by emitter).
- Need AI app-id (the `<appId>` GUID for `wd-prod-android-client`) before this can run. Sub is `fb633419-…`; resource name `wd-prod-android-client`.

---

## 10. Android Perf Rollups (CPU / Memory / Throughput) (NEW — catalog-derived) ✨

**Confidence:** LOW
**STATUS:** Routing per catalog: `androidgsa.eastus.kusto.windows.net / Metric / {MemoryCPUUsage, UploadDownloadSpeed}`. **Catalog flag: not live-verified** — DNS resolution failed during catalog generation. Validate cluster reachability before relying on it.

```kusto
// Per-version CPU/mem rollup, 7d
MemoryCPUUsage
| where ingestion_time() > ago(7d)
| summarize avg_cpu = avg(<cpu_col>),
            avg_mem = avg(<mem_col>)
            by AppVersion, bin(ingestion_time(), 1d)
| order by ingestion_time() desc
```

**Caveats:**
- Column names (`<cpu_col>`, `<mem_col>`) are TBD — schema introspection owed.
- Catalog has an alias `android-perf-cpu-memory-7d` that resolves to this cluster/db; use the alias once cluster is reachable.

---

## 11. Aria Cross-Check — Android error events (NEW — catalog-derived) ✨

**Confidence:** MEDIUM
**STATUS:** Direct adoption of the upstream alias `gsa-android-errors-1h` (catalog-resolved). Aria is NOT primary for Android telemetry, but `mnap_xplat_telemetryprod_errorevent` does carry Android rows. Useful as a sanity-check view when App Insights ingest is suspect.

**Cluster / DB:** `https://kusto.aria.microsoft.com` / db_guid `f0eaa94222894be599b7cd0bc1e2ed6f` (NOT the friendly name `naas-prod`).
**Time column:** `EventInfo_Time`.

```kusto
mnap_xplat_telemetryprod_errorevent
| where EventInfo_Time > ago(1h)
| where App_Platform == 'Android'
| project EventInfo_Time, App_Version, DeviceInfo_Id, Data_df_ErrorCode, Data_df_ErrorString
| take 100
```

**Caveats:**
- The upstream alias uses `take 100`, not aggregation. For trend lines change to `summarize count() by Data_df_ErrorCode, bin(EventInfo_Time, 1h)`.
- Most other `mnap_xplat_*` tables list `platforms=['windows']` or `['mac']` in the catalog — do NOT generalize this Android-cross-check pattern to those tables; you'll get zero rows.

---

## Upstream Catalog

The canonical routing registry for GSA / NaaS Kusto lives in the `Identity-gsa-client-marketplace` plugin marketplace:

- Upstream skill: [`gsa-kusto-catalog`](file:///Users/salonijain/workspace/Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-kusto-catalog/) (`SKILL.md`, `catalog.json`, `catalog-semantics.json`)
- **Local Android slice:** [`.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md`](../gsa-kusto-catalog-android-slice/SKILL.md) — Android-only subset (clusters, table inventory, filter idioms, time-column matrix).

Treat the upstream catalog as ground truth. When this skill disagrees with the catalog about a cluster URL, db GUID, table name, or time column, **the catalog wins**. Open a PR upstream rather than diverging.

When you need a route this skill doesn't list (e.g., a SCUS-only NaasProd table like `RoxyHttpOperationEvent`), follow the slice's "Step 5 — defer to upstream" path.

---

## Reconciliation summary table

| # | Query | Original table | Original Android filter | Reconciled table | Reconciled filter | New status |
|---|---|---|---|---|---|---|
| 1 | Active Devices | `EdgeDiagnosticOperationEvent` | `DeviceId in (AndroidDeviceIds())` (placeholder) | superseded by #7 | `DeviceOs has_cs 'ANDROID'` | superseded |
| 2 | Fleet Errors | `EdgeDiagnosticOperationEvent` | placeholder | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium |
| 3 | APS Availability | `AgentGetSettingsOperationEvent` | `ClientOs == "Android"` (wrong) | unchanged | TBD — schema not introspected | low-med |
| 4 | PKI | unknown | n/a | `idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (catalog) | TBD (column owed) | low-med (routing UNBLOCKED) |
| 5 | Tunnel Health | `NaaSVPNZtnaConnectionLogsEvent` | `env_os == "Android"` (correct for that table) | preferred swap to `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium |
| 6 | Active Tenants | (new) | (new) | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | **HIGH — executed** |
| 7 | Active Devices | (new) | (new) | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium-high |

## Next hardening steps

1. Get one more panel KQL from Saloni — preferably an errors or latency panel — to validate the `Status` / `FlowStatusError` semantics in query #2 and the `LatencyMs` percentiles in #5.
2. Run `kusto_table_schema` on `AgentGetSettingsOperationEvent` to settle query #3's columns and Android filter idiom.
3. ~~PKI cluster/DB pointer from Saloni~~ — RESOLVED via upstream catalog (`idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary`). Now: schema-introspect this table to settle query #8's filter and status columns.
4. Get the App Insights `<appId>` GUID for `wd-prod-android-client` — unblocks query #9 (Android client-side via AI REST API). Also confirm the `customDimensions` key casing for `AndroidId` and `TenantOrgName`.
5. Verify reachability of `androidgsa.eastus.kusto.windows.net` (catalog flag: DNS failed at generation). If reachable, introspect column list of `MemoryCPUUsage` and `UploadDownloadSpeed` to settle query #10.
6. Settle whether the 37-build version allowlist is auto-discovered or manually maintained — affects #6 / #7 robustness.
7. Confirm Android crash signal source (Watson is Win32-only per catalog; Play Console / Crashlytics-equivalent is the right home, but not in catalog).
