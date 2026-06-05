# Skill: android-kusto-starter

**Owner:** Scully
**Created:** 2026-06-05
**Confidence (overall):** LOW — schemas partially confirmed via `azure-mcp-kusto` introspection on `idsharedwus`, but the exact dashboard-equivalent queries have NOT been validated against the production dashboard panels. All queries below are **starter scaffolds** intended to be reviewed by Saloni (or compared against a dashboard panel query export) before being trusted.

**Common header for every query:**
```kusto
// Cluster: idsharedwus.kusto.windows.net
// Default lookback: 7d (matches dashboard p-_startTime=7days)
let _start = ago(7d);
let _end   = now();
// _osType=Android — see caveat: server-only tables don't carry osType natively
```

---

## 1. Active Android Devices (weekday rolling)

**Confidence:** LOW
**When to use:** Filling the "Active Android Clients (weekday)" KPI row in the daily report.
**STATUS:** untested — needs ground-truth schema from Saloni (Aria cluster / AppInsights component) or a sample query export from the dashboard's "Active Devices" tile.

```kusto
// HYPOTHESIS — preferred path is Aria client telemetry; this NaasProd version
// only works if a device→OS lookup function exists (placeholder: AndroidDeviceIds()).
// If AndroidDeviceIds() does NOT exist, this returns ALL devices and over-counts.
let _start = ago(7d);
EdgeDiagnosticOperationEvent
| where PreciseTimeStamp between (_start .. now())
| where isnotempty(DeviceId)
// | where DeviceId in (AndroidDeviceIds())   // <-- enable when lookup confirmed
| summarize ActiveDevices = dcount(DeviceId) by bin(PreciseTimeStamp, 1d)
| order by PreciseTimeStamp desc
```

**Caveats:**
- `EdgeDiagnosticOperationEvent` has no `osType` column (verified). Android filtering requires either an Aria-side query or a join.
- "Active" definition matters — see open question 6 in `dashboard-analysis.md`.
- Weekday-only filtering not applied yet (add `| where dayofweek(PreciseTimeStamp) between (1d .. 5d)` once definition is locked).

---

## 2. Fleet Errors (7d) — Android cohort

**Confidence:** LOW
**When to use:** Filling the "Fleet Errors (7d)" row in the daily report.
**STATUS:** untested — same Android-cohort filter problem as #1.

```kusto
let _start = ago(7d);
EdgeDiagnosticOperationEvent
| where PreciseTimeStamp between (_start .. now())
| where ResponseCode >= 400
// | where DeviceId in (AndroidDeviceIds())   // enable when confirmed
| summarize ErrorCount = count(),
            DistinctDevices = dcount(DeviceId)
            by ResponseCodeBucket = bin(ResponseCode, 100), OperationName
| order by ErrorCount desc
| take 50
```

**Caveats:**
- `ResponseCode` is `real` in schema — buckets it to 4xx/5xx ranges.
- Doesn't yet cross `RoxyHttpOperationEvent` errors; dashboard likely unions both.
- Drop/timeout errors may NOT have a `ResponseCode` — need to check `OperationName` enum for `Timeout`/`Dropped` values.

---

## 3. APS Availability (Get-Settings success rate)

**Confidence:** LOW-MEDIUM
**When to use:** Filling the "APS Availability" row. Table name confirmed; column names guessed.
**STATUS:** untested — column names (`ResultType`/`Success`/`StatusCode`) are guesses; need schema introspection on `AgentGetSettingsOperationEvent`.

```kusto
// Database: NaasAgentServicesApsProd
let _start = ago(7d);
AgentGetSettingsOperationEvent
| where TIMESTAMP between (_start .. now())
// | where ClientOs == "Android"  // ASSUMED column — confirm name
| summarize Total = count(),
            // success criteria assumed: StatusCode 2xx OR ResultType == "Success"
            Successes = countif(ResultType == "Success")
            by bin(TIMESTAMP, 1h)
| extend AvailabilityPct = todouble(Successes) * 100.0 / Total
| order by TIMESTAMP desc
```

**Caveats:**
- Real schema not yet introspected — column names `ResultType`, `ClientOs` are placeholders.
- Likely also useful: `AgentSettingsAckOperationEvent` for end-to-end policy apply success (vs. just fetch).
- Example report mentions a "SuccessSettingsNotFound" response — that response code text likely lives in `ResultType` or `Description`.

---

## 4. PKI Health

**Confidence:** ZERO
**When to use:** Filling the "PKI Health" row.
**STATUS:** 🔴 BLOCKED — both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd` on `idsharedwus` returned zero tables via `kusto_table_list`. The PKI panel must read from a different cluster, or this account lacks permission.

```kusto
// PLACEHOLDER — DO NOT RUN.
// Need from Saloni:
//   1. Real cluster URI for PKI telemetry
//   2. Real database + table name
//   3. Success-definition (cert issued? renewed? validation passed?)
//
// Sketch once known:
//   <PkiTable>
//   | where TIMESTAMP > ago(7d) and ClientOs == "Android"
//   | summarize Total=count(), Failures=countif(Status != "Success") by bin(TIMESTAMP, 1h)
//   | extend HealthPct = (1.0 - todouble(Failures)/Total) * 100
```

**Caveats:** All of the above is hypothetical until source is identified.

---

## 5. Tunnel Health (ZTNA connection success + latency)

**Confidence:** MEDIUM
**When to use:** Filling the "Tunnel Health" row. This table DOES carry `env_os` — Android filtering is real here.

```kusto
// Database: NaasProd
let _start = ago(7d);
NaaSVPNZtnaConnectionLogsEvent
| where env_time between (_start .. now())
| where env_os == "Android"
| summarize Total = count(),
            // success heuristic — refine once we know which TraceLevel = success
            Connects = countif(TraceLevel <= 2),
            Failures = countif(TraceLevel >= 4)
            by bin(env_time, 1h), Region
| extend SuccessPct = todouble(Connects) * 100.0 / Total
| order by env_time desc
```

Companion query for tunnel latency / insight:
```kusto
let _start = ago(7d);
NaaSVPNTunnelInsightEvent
| where TIMESTAMP between (_start .. now())
// | where env_os == "Android"   // verify column presence
| summarize p50 = percentile(DurationInMilliseconds, 50),
            p95 = percentile(DurationInMilliseconds, 95),
            p99 = percentile(DurationInMilliseconds, 99)
            by bin(TIMESTAMP, 1h)
| order by TIMESTAMP desc
```

**Caveats:**
- `TraceLevel` semantics are guessed — need to confirm which integer values = success vs failure.
- `NaaSVPNTunnelInsightEvent` schema NOT introspected yet; `DurationInMilliseconds` column presence assumed by analogy.
- ZTNA log captures gateway-side view; if a client never establishes a connection at all, it won't appear here — pair with client-side Aria to spot fully-broken installs.

---

## How to harden these queries (next steps)

1. Get one panel query export from the dashboard for any of the metrics above — that locks the real schema/joins.
2. Run `kusto_table_schema` on `AgentGetSettingsOperationEvent`, `NaaSVPNTunnelInsightEvent`, `RoxyHttpOperationEvent` (cheap calls).
3. Find or create the `AndroidDeviceIds()` lookup (probably a `.create function` in NaasProd or a join to a registry table).
4. Confirm Aria cluster + database for client-side `env_os == "Android"` filtering.

Once those four items land, queries #1, #2, #3, #5 graduate from "starter" to "production" — and #4 (PKI) can be drafted.
