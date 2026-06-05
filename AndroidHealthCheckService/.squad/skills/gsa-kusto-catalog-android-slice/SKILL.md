# Skill: gsa-kusto-catalog-android-slice

**Owner:** Scully
**Created:** 2026-06-05
**Confidence:** MEDIUM — derived from a canonical upstream catalog. Not all rows are independently live-verified by this squad; validation queries are owed in the next round.

**Upstream (source of truth — DO NOT duplicate, link):**
- `Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-kusto-catalog/catalog.json`
- `…/catalog-semantics.json`
- `…/SKILL.md`

This skill is the **Android-only slice** of that catalog: which clusters / databases / tables are relevant to a daily Android GSA Client Service Health Report, and the canonical Android-cohort filter idiom for each. When a stakeholder question requires a cluster or table not listed here, fall back to the upstream catalog.

---

## KNOW

### Two-pipeline reality (do not conflate)

The cross-platform GSA client publishes telemetry through **two independent pipelines**:

1. **Aria / 1DS** — `mnap_xplat_telemetryprod_*` tables on `kusto.aria.microsoft.com`. **Primary for Windows + Mac. Carries Android only opportunistically** (e.g., `errorevent` includes Android rows; most other events are Win/Mac only).
2. **Application Insights** — `wd-prod-android-client` resource. **Primary for Android.** Standard AI schema (`customEvents`, `exceptions`, `traces`, `requests`, `dependencies`, `customMetrics`).

Server-side telemetry (NaaS edge, tunnel, APS, PKI) is shared — Android shows up in NaasProd tables alongside other platforms and is filtered with `DeviceOs has_cs 'ANDROID'`.

### Cluster directory — Android-relevant only

| Cluster ID (catalog) | URL | Category | Why we use it |
|---|---|---|---|
| `naas-idsharedwus` | `https://idsharedwus.kusto.windows.net` | server_side | Primary auth path today. Hosts `NaasProd` (mirror), `NaasAgentServicesApsProd`, `NaasCloudPkiProd`, `ZTNAMgmtPlaneProd`. |
| `naas-idsharedscus` | `https://idsharedscus.southcentralus.kusto.windows.net` | server_side | Full 37-table NaasProd. Use when the WUS mirror lacks the table (e.g., Roxy/Talon/ControlTower/CertMonitor). |
| `aria-prod` | `https://kusto.aria.microsoft.com` | client_side | Cross-checks only for Android; primary for Win/Mac. |
| `android-appinsights` | `https://api.applicationinsights.io/v1/apps/<appId>/query` (App Insights REST API — NOT a Kusto cluster URL) | client_side | **Primary for Android client telemetry.** AI resource: `wd-prod-android-client`, sub `fb633419-6bb2-4a7e-8993-fd9456d19c4c`. |
| `android-gsa-metric` | `https://androidgsa.eastus.kusto.windows.net` | client_side (perf) | Android perf rollups (CPU/mem/throughput per AppVersion per day). Catalog flag: not live-verified from contributor workstation. |

### Database routing (Aria special-case)

Aria's `database` parameter is **the GUID, not the friendly name**. For prod Android queries against Aria:

```
clusterUrl = https://kusto.aria.microsoft.com
database   = f0eaa94222894be599b7cd0bc1e2ed6f   ← prod GUID, not "naas-prod"
```

Friendly-name routing returns 400. (See upstream `SKILL.md` "Aria routing rule".)

### Table inventory — Android slice

#### Server-side (NaasProd family on `naas-idsharedwus`)

| Table | Database | Time column | Android filter | Used for |
|---|---|---|---|---|
| `TunnelServerOperationEvents` | `NaasProd` | `TIMESTAMP` | `DeviceOs has_cs 'ANDROID'` | Tunnel KPIs, Active Devices, Active Tenants, latency p50/p95/p99, flow errors. **Primary** table for daily report. |
| `EdgeDiagnosticOperationEvent` | `NaasProd` | `TIMESTAMP` | (no `DeviceOs` column — needs DeviceId join, OR query via idsharedscus) | HTTP-layer errors (`ResponseCode >= 400`). Cross-check only — Android filter awkward. |
| `AgentGetSettingsOperationEvent` | `NaasAgentServicesApsProd` | `TIMESTAMP` | TBD — schema-introspect | APS availability (settings-fetch success rate). |
| `AgentSettingsAckOperationEvent` | `NaasAgentServicesApsProd` | `PreciseTimeStamp` ⚠ | TBD — schema-introspect | APS apply-success / ack closure. |
| `EnrollCertificateOperationSummary` | `NaasCloudPkiProd` | `PreciseTimeStamp` | TBD (catalog states "Win/Mac/iOS/Android" — exact column owed) | **PKI Health row** — unblocks the previously-blocked metric. |

#### Server-side (extras on `naas-idsharedscus`, when WUS mirror is insufficient)

| Table | Time column | Android filter |
|---|---|---|
| `NaaSVPNZtnaConnectionLogsEvent` | `env_time` | `env_os == "Android"` |
| `NaaSVPNTunnelInsightEvent` | `env_time` | `env_os == "Android"` |
| `NaaSVPNGatewayFlowLogsEvent` | `env_time` | `env_os == "Android"` |
| `RoxyHttpOperationEvent`, `TalonOperationEvent`, `ControlTowerOperationEvent` | `PreciseTimeStamp` | (no `DeviceOs`; needs DeviceId join) |

#### Client-side — primary Android pipeline

| Table | Cluster / DB | Time column | Notes |
|---|---|---|---|
| `customEvents` | `android-appinsights / wd-prod-android-client` | `timestamp` | Standard App Insights. `id` from `customDimensions['AndroidId']`. Tenant from `customDimensions['TenantOrgName']`. Version from `application_Version`. Sibling tables: `exceptions`, `traces`, `requests`, `dependencies`, `customMetrics`. |
| `MemoryCPUUsage` | `android-gsa-metric / Metric` | `ingestion_time()` | Pivot by `AppVersion` + day. |
| `UploadDownloadSpeed` | `android-gsa-metric / Metric` | `ingestion_time()` | Same shape as above. |

#### Client-side — Aria cross-checks only

Most `mnap_xplat_telemetryprod_*` tables are Win/Mac only. The one Android-bearing case worth knowing about:

| Table | Cluster / DB | Time column | Android filter |
|---|---|---|---|
| `mnap_xplat_telemetryprod_errorevent` | `aria-prod / naas-prod` (db_guid `f0eaa9…`) | `EventInfo_Time` | `App_Platform == 'Android'` |

(Other `mnap_xplat_*` tables list `platforms=['windows']` or `['mac']` in the catalog — query them only if you've confirmed they actually carry Android rows.)

### Useful upstream aliases

| Alias | Resolves to |
|---|---|
| `gsa-android-errors-1h` | `aria-prod / naas-prod` — error events with `App_Platform == 'Android'`, last 1h |
| `android-perf-cpu-memory-7d` | `android-gsa-metric / Metric` — CPU/mem rollups by AppVersion, 7d |
| `android-appinsights-naas-toggle-disable-7d` | `android-appinsights / wd-prod-android-client` — devices that toggled NaaS OFF, last 7d |

To expand any alias, follow upstream `SKILL.md` Step 3 (load `aliases.<name>` from `catalog.json`).

---

## DO

### Step 1 — Resolve a cluster/database for an Android query

1. Look up the table you need in the inventory above.
2. Read `clusterUrl` and `database` from the matching cluster row.
3. For Aria, `database` MUST be `f0eaa94222894be599b7cd0bc1e2ed6f` (GUID), never the friendly name.
4. If the table isn't in this slice, walk the upstream `catalog.json` (don't hard-code a route — fail closed if the table is genuinely unknown).

### Step 2 — Apply the canonical Android filter for the table family

Pick the filter from the inventory above. Common cases:

```kusto
// NaasProd / TunnelServerOperationEvents (and any DeviceOs-bearing op-event table)
| where DeviceOs has_cs 'ANDROID'

// NaaS VPN Aria-envelope tables on idsharedscus (env_os column)
| where env_os == "Android"

// Aria mnap_xplat_telemetryprod_errorevent (cross-check only)
| where App_Platform == 'Android'

// App Insights customEvents — Android pipeline is implicit; no filter needed
```

Do **not** mix idioms across table families. The same query should not contain both `DeviceOs has_cs 'ANDROID'` and `env_os == "Android"` unless joining two deliberately.

### Step 3 — Pick the right time column

Different tables use different time columns. Wrong column → "no data" silently:

- `TIMESTAMP` (uppercase) — most NaasProd op-event tables on idsharedwus.
- `PreciseTimeStamp` — `AgentSettingsAckOperationEvent`, `EnrollCertificateOperationSummary`, most idsharedscus debug/op-event tables.
- `env_time` — NaaS VPN (Aria-envelope) tables on idsharedscus.
- `EventInfo_Time` — Aria `mnap_xplat_*`.
- `timestamp` — App Insights.
- `ingestion_time()` — android-gsa-metric Metric tables.

### Step 4 — Handle WUS mirror vs SCUS source

`naas-idsharedwus.NaasProd` is a **2-table mirror**: only `TunnelServerOperationEvents` and `EdgeDiagnosticOperationEvent`. Need Roxy / Talon / ControlTower / CertMonitor / NaaSVPN* etc.? Route to `naas-idsharedscus.NaasProd` instead. Don't query a non-existent table on the WUS shard.

### Step 5 — When in doubt, defer to upstream

If this slice and upstream `catalog.json` disagree, **upstream wins**. Update this slice (in PR review) rather than diverging silently. This file is a curated subset; it is not authoritative.

---

## CHECK

- [ ] Used the cluster URL + database value (Aria GUID, not friendly name) from this slice / upstream catalog, never hard-coded.
- [ ] Filter idiom matches the table family (`DeviceOs has_cs 'ANDROID'` vs `env_os == "Android"` vs `App_Platform == 'Android'` vs implicit).
- [ ] Time column matches the table's actual column (`TIMESTAMP` vs `PreciseTimeStamp` vs `env_time` vs `EventInfo_Time` vs `timestamp` vs `ingestion_time()`).
- [ ] Routed to idsharedscus (not the 2-table WUS mirror) when the table isn't in `naas-idsharedwus`.
- [ ] Recorded in the squad's `android-kusto-starter` skill any new query that depended on a row in this slice — for traceability.
- [ ] Did NOT copy upstream catalog content into this file; only the Android-relevant lookup table is here.

---

## Common Rationalizations

| Excuse | Rebuttal |
|---|---|
| "Aria has Android data — let me query `mnap_xplat_telemetryprod_authentication where App_Platform == 'Android'`." | The catalog's `platforms` field for that table is `['mac', 'windows']` — Android does not emit it. You'll get zero rows and call it an outage. Only `errorevent` (and a few others on a case-by-case basis) actually carries Android. For Android auth signal, use App Insights `wd-prod-android-client` instead. |
| "PKI is back — I'll just `EnrollCertificateOperationSummary | where DeviceOs has_cs 'ANDROID'`." | Catalog confirms the table exists and serves all platforms, but doesn't confirm a `DeviceOs` column. Schema introspection is owed first. Don't assume the column name; the table's filter idiom may be different (e.g., `Platform`, `OsType`, or DeviceId-join). |
| "WUS NaasProd has all the tables we need — no reason to ever hop to SCUS." | WUS is a 2-table mirror only (`TunnelServerOperationEvents`, `EdgeDiagnosticOperationEvent`). For Roxy / Talon / ControlTower / NaaSVPN* / CertMonitor you must go to `idsharedscus`. Querying a non-existent table on WUS gives a "table not found" error, not a graceful empty result. |
| "Watson FUN has crash data — I'll use that for Android crashes." | The catalog explicitly tags Watson as Windows Error Reporting — user-mode and kernel-mode Win32 minidumps. Android crashes go through Play Console / Firebase Crashlytics-equivalent (not in this catalog). Using Watson for Android crash signal will produce zero rows. |
| "App Insights and Aria duplicate Android error data — I'll just pick one." | They don't duplicate; App Insights is the primary Android error pipeline, and Aria's `errorevent` is a partial cross-check (only the cross-platform error path emits there). Use App Insights as primary; use Aria as a sanity check when you suspect AI ingest gap. |

---

## Red Flags

- A daily-report query routes to Aria for an Android-cohort metric without checking whether that specific Aria table emits from Android — likely silently returning zero.
- A query against `naas-idsharedwus.NaasProd` references `RoxyHttpOperationEvent` / `TalonOperationEvent` / `NaaSVPN*` — those are SCUS-only; this query will fail.
- A KQL block mixes `DeviceOs has_cs 'ANDROID'` and `env_os == "Android"` in unrelated `where` clauses on the same table — only one applies per table.
- A query uses `ago(7d)` against a table whose time column is `env_time` or `EventInfo_Time` but filters on `TIMESTAMP` — silently returns nothing.
- This slice is being treated as authoritative for a non-Android table — that's not what it's for; route via upstream `catalog.json`.
- The Aria `database` parameter is set to `naas-prod` instead of the GUID — Kusto will return 400.
- A new Android-relevant table is discovered locally and added here without a corresponding PR back to the upstream catalog — drift will compound.

---

## Upstream catalog — when to reach past this slice

If your need isn't in this file:

1. Open `catalog.json` from the upstream skill directory.
2. Use `clusters[<id>].databases[<db>].tables[<name>]` for routing.
3. Use `catalog-semantics.json._indexes.column_to_tables` for "which tables have column X".
4. Use `catalog-semantics.json.correlations[]` for multi-table join recipes.
5. If a route is missing entirely, file a PR against `Identity-gsa-client-marketplace` to add it — don't hard-code in our local skills.

This slice will be re-derived after material changes upstream. If the upstream catalog version skews significantly from what this file describes, refresh.
