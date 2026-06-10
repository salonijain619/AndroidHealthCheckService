# NAAS 7-day Report Data (Android) — 2026-06-08

> ⚠️ **STATUS: BLOCKED — network unreachability to `idsharedwus.kusto.windows.net`.**
> Two retries via `azure-mcp-kusto kusto_query` returned HTTP 503 / `Operation timed out (idsharedwus.kusto.windows.net:443)`. Direct `curl -m 20 https://idsharedwus.kusto.windows.net/v1/rest/mgmt` also TCP-timed-out at port 443 (DNS resolves to `172.185.50.226`; general internet works — `https://www.bing.com` returned 200).
> **Diagnosis:** corp-VPN/firewall reachability issue, NOT auth, NOT a bad query. Same MCP path that worked on 2026-06-05.
> **No fabricated numbers below.** Today's targeted KPI cells are marked `[BLOCKED]`. The 2026-06-05 v1 baseline is reproduced verbatim so Reyes has the last-known-good reference and can clearly indicate "no telemetry refresh today" in the v3 report header.

- **Intended window:** `2026-06-01T00:00:00Z` .. `2026-06-08T00:00:00Z` UTC (7d, locked per Saloni)
- **Intended scope:** NAAS-server-side, Android (`DeviceOs has_cs 'ANDROID'` on Tunnel; `OS == 'ANDROID'` on PKI; `OS has_cs 'Android' or OSType has_cs 'Android'` on APS)
- **Intended clusters/DBs:** `idsharedwus / NaasProd | NaasCloudPkiProd | NaasAgentServicesApsProd` (NO Defender, NO SCUS — locked per Saloni)
- **Run timestamp:** `2026-06-08T~12:00Z` (data-pull attempts; ICM pull succeeded against same Entra creds at `2026-06-08T12:01:45Z`, so it's not a generic identity outage)
- **Auth outcome:** N/A — never reached the query layer; TCP handshake to `:443` did not complete.

---

## Failure mode (full detail for Reyes / Mulder)

| # | Action | Result |
|---|---|---|
| 1 | `azure-mcp-kusto kusto_query` against `https://idsharedwus.kusto.windows.net` | `HTTP 503 — Operation timed out (idsharedwus.kusto.windows.net:443)` |
| 2 | `curl -m 10 https://idsharedwus.kusto.windows.net/` | `curl: (28) Connection timed out after 10005 ms` |
| 3 | `nslookup idsharedwus.kusto.windows.net` | `172.185.50.226` (DNS healthy) |
| 4 | `curl -m 10 https://www.bing.com/` | `HTTP 200` (general internet OK) |
| 5 | Sleep 20s, retry `azure-mcp-kusto kusto_query` (per spec — one retry) | `HTTP 503 — Operation timed out` (same TCP failure) |
| 6 | `curl -m 20 https://idsharedwus.kusto.windows.net/v1/rest/mgmt` | `curl: (28) Connection timed out after 20003 ms` |
| 7 | ICM collector `agency mcp icm` (control: same env, different endpoint) | ✅ Exit 0, live data, `_meta.errors: []` |

**Conclusion:** the Kusto cluster `idsharedwus` is unreachable from this run environment at the TCP layer. The most likely causes (in order):
1. Corp-VPN session expired or routing change blocking `*.kusto.windows.net` egress.
2. The cluster temporarily off-net (would also affect the dashboard at `dataexplorer.azure.com/clusters/idsharedwus`).
3. NSG / firewall change on the cluster side.

**Saloni unblock ask:** verify VPN reachability to `https://idsharedwus.kusto.windows.net/v1/rest/mgmt` from the same machine; if OK from another window, the issue is local to this Copilot run env and a re-run will succeed.

---

## What Reyes should do for the 2026-06-08 v3 report

1. **Header banner:** mark "Server-side telemetry NOT refreshed today — last successful pull 2026-06-05 v1 baseline" so readers understand the Key Metrics row is stale.
2. **Key Metrics table:** use the v1 baseline numbers (reproduced below) and prefix the row with a 🟧 staleness emoji + footnote `(no refresh — pull blocked 2026-06-08, see Data Quality Notes)`.
3. **Top Insights:** the 5× failure-rate ramp finding from v1 is the most recent verified server-side anomaly. Carry it forward as **"Pending re-confirmation — last pull 2026-06-05"**, do NOT escalate severity beyond what v1 set.
4. **Cross-domain candidates:** keep the v1 candidates listed (still actionable) but note none have been refreshed against new data.
5. **ICM section:** fully live (see sister drop `icm-team-106961-data-2026-06-08.md`) — Reyes can confidently render that part.

---

## v1 baseline — reproduced verbatim (last-known-good, 2026-05-29 .. 2026-06-05)

These are the numbers Reyes already has access to in `naas-7d-report-data-2026-06-05.md`; restated here in compact form so the v3 assembly doesn't have to cross-reference.

### Headline (from v1 pull)

| Metric | v1 baseline (window 5/29 .. 6/05) | v3 (window 6/01 .. 6/08) |
|---|---|---|
| Active Android devices | **27,489** | `[BLOCKED]` |
| Active Android tenants | **1,241** | `[BLOCKED]` |
| Total Tunnel events | **130.05M** | `[BLOCKED]` |
| Tunnel server-side success % | **99.711%** | `[BLOCKED]` |
| Tunnel server-side failure % | **0.289%** (overall 7d) | `[BLOCKED]` |
| Daily fail-rate trend (anchor) | **0.074% (5/29) → 0.36% sustained (6/02–6/04)** — ~5× ramp, +12× failure volume vs 2.6× traffic | `[BLOCKED]` |
| Microsoft 1P contribution (Tenant `72f988bf-…`) | **37% of all failures** (140,697 of 375,714) | `[BLOCKED]` |
| Private Access vs M365 fail ratio | **0.688% vs 0.174% → ~4× higher** | `[BLOCKED]` |
| `PROFILE_UNDEFINED` ServiceType | **100% fail, 4,003 events, 245 devices** | `[BLOCKED]` |
| APS Get-Settings success | **99.997%** (270.3M events, 825K devices, 24K tenants) | `[BLOCKED]` |
| APS Settings Ack success | **99.99966%** (268.6M events) | `[BLOCKED]` |
| PKI cert enrollment errors | **4 of 595,712 = 0.0007%** (1,326 tenants) | `[BLOCKED]` |
| Top failing region | **South Africa North 0.758%**, then UK South 0.465%, brazilsouth 0.468%, WestEurope 0.449% | `[BLOCKED]` |

### Headline movement (v1 → v3)
**Cannot compute.** The single delta-bearing finding from this run is that Part A failed; movements vs v1 baseline will land in v4 or in a re-run when network reachability returns.

---

## Per-query intent (queries that would have run, recorded so re-run is mechanical)

Same query suite as v1, with the date predicates re-anchored to the explicit window `[2026-06-01T00:00:00Z .. 2026-06-08T00:00:00Z]` (Saloni-locked, NOT `ago(7d)`) so two adjacent runs are reproducibly comparable.

| ID | DB / Table | Query (one-liner) |
|---|---|---|
| S1 | `NaasProd / TunnelServerOperationEvents` | `... \| where DeviceOs has_cs 'ANDROID' \| summarize dcount(TenantId)` |
| S2 | same | `... \| summarize dcount(DeviceId)` |
| S3 | same | `... \| summarize Events=count() by Status` |
| S4 | same | `... \| summarize Total=count(), Failures=countif(Status=='Failure'), Devices=dcount(DeviceId), Tenants=dcount(TenantId) by Region \| extend FailurePct=round(todouble(Failures)*100/Total,3) \| order by Total desc \| take 25` |
| S5 | same | daily `bin(TIMESTAMP,1d)` of `dcount(DeviceId)`, `dcount(TenantId)`, `count()` |
| S6 | same | daily `bin(TIMESTAMP,1d)` of total + failures → `FailurePct` |
| S7 | same | `Status=='Failure' \| summarize by TenantId \| order by Failures desc \| take 15` |
| S8 | same | by `ClientVersion`, top 25 by Devices |
| S9 | same | by `ServiceType` (M365 / Internet / Private Access / PROFILE_UNDEFINED) |
| S10 | `NaasAgentServicesApsProd / AgentGetSettingsOperationEvent` | filter `OS has_cs 'Android' or OSType has_cs 'Android'`, success rate from `ResultStatus startswith 'Success' or HttpResponseStatusCode == '200'` |
| S11 | `NaasAgentServicesApsProd / AgentSettingsAckOperationEvent` | filter same, summarize by `ResultStatus` |
| S12 | `NaasCloudPkiProd / EnrollCertificateOperationSummary` | filter `OS == 'ANDROID'`, count by `ResultStatus, OperationName, HttpResponseStatusCode` |

All 12 are exactly the v1 shape — no schema changes attempted this round (v1 already worked), so a re-run when network returns should be turn-key.

---

## Ghost-column / data-quality status (carry-forward, NOT re-tested)

The four ghost columns from the 2026-06-05 finding **remain unverified today** (we never reached `getschema`):

- `FlowStatusError` on `TunnelServerOperationEvents` — was advertised, returned `SEM0100` on use
- `FlowErrorClassification` — same
- `LatencyMs` — same → server-side latency p50/p95/p99 unavailable
- `Msg` — same

If/when Part A re-runs, **first action** should be a 1-row `take 1 | project FlowStatusError, FlowErrorClassification, LatencyMs, Msg` to confirm whether the data-platform team has shipped a fix. If it succeeds, that's a Top-5 Insights candidate ("server-side latency now available; here are the p50/p95/p99 numbers"). If it still fails, no change.

Region-casing duplicates (`westeurope` vs `WestEurope`, `NorthEurope` vs `northeurope`, `centralus` vs `CentralUs`, `SouthAfricaNorth` vs `southafricanorth`) — also not re-tested. Carry forward the v1 finding.

APS sibling-table schema divergence (`HttpResponseStatusCode` present on `AgentGetSettingsOperationEvent`, absent on `AgentSettingsAckOperationEvent`) — carry forward.

PKI emitting empty/placeholder `DeviceId` for Android — carry forward.

---

## New anomalies vs v1 baseline

**None observed this run** — Part A never executed. The "no new anomalies" statement here is a **negative result by lack of attempt**, not by data: do not interpret as "the service is stable" — it just wasn't measured today.

---

## Run accounting

| Bucket | Attempted | Passed | Failed (network) | Failed (final) |
|---|---|---|---|---|
| Tunnel (NaasProd) | 0 | 0 | 0 (never started) | 12 (blocked upstream) |
| APS (NaasAgentServicesApsProd) | 0 | 0 | 0 | 3 (blocked upstream) |
| PKI (NaasCloudPkiProd) | 0 | 0 | 0 | 3 (blocked upstream) |
| Connectivity probes | 4 | 1 (bing.com 200) | 3 (idsharedwus :443 timeout x2 + curl) | — |
| **Totals** | **4** | **1** | **3** | **18** (none reached cluster) |

Zero queries reached the cluster. Zero results returned. **No fabricated cells** anywhere in this drop.
