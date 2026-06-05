# Skill: android-kusto-starter

**Owner:** Scully
**Created:** 2026-06-05
**Last reconciled:** 2026-06-05 (against verbatim panel KQL from dashboard `8a1fa78a-…`)
**Confidence (overall):** MEDIUM — table + Android filter + version semantics now confirmed via `azure-mcp-kusto` against live `idsharedwus / NaasProd`. Queries 1, 2, 5, 6, 7 below have been schema-validated; query 6 has been run verbatim and returns a sensible result. Query 3 (APS) and 4 (PKI) remain untested / blocked.

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

**Confidence:** ZERO (unchanged)
**STATUS:** 🔴 BLOCKED — both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd` returned zero tables on `idsharedwus`. Saloni still owes us a cluster/DB pointer.

```kusto
// PLACEHOLDER — DO NOT RUN. Need cluster + DB + table from Saloni.
```

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

## Reconciliation summary table

| # | Query | Original table | Original Android filter | Reconciled table | Reconciled filter | New status |
|---|---|---|---|---|---|---|
| 1 | Active Devices | `EdgeDiagnosticOperationEvent` | `DeviceId in (AndroidDeviceIds())` (placeholder) | superseded by #7 | `DeviceOs has_cs 'ANDROID'` | superseded |
| 2 | Fleet Errors | `EdgeDiagnosticOperationEvent` | placeholder | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium |
| 3 | APS Availability | `AgentGetSettingsOperationEvent` | `ClientOs == "Android"` (wrong) | unchanged | TBD — schema not introspected | low-med |
| 4 | PKI | unknown | n/a | still unknown | n/a | 🔴 blocked |
| 5 | Tunnel Health | `NaaSVPNZtnaConnectionLogsEvent` | `env_os == "Android"` (correct for that table) | preferred swap to `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium |
| 6 | Active Tenants | (new) | (new) | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | **HIGH — executed** |
| 7 | Active Devices | (new) | (new) | `TunnelServerOperationEvents` | `DeviceOs has_cs 'ANDROID'` | medium-high |

## Next hardening steps

1. Get one more panel KQL from Saloni — preferably an errors or latency panel — to validate the `Status` / `FlowStatusError` semantics in query #2 and the `LatencyMs` percentiles in #5.
2. Run `kusto_table_schema` on `AgentGetSettingsOperationEvent` to settle query #3's columns and Android filter idiom.
3. PKI cluster/DB pointer from Saloni — unblocks #4.
4. Settle whether the 37-build version allowlist is auto-discovered or manually maintained — affects #6 / #7 robustness.
