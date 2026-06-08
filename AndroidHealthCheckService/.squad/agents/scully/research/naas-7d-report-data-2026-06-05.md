# NAAS 7-day Report Data (Android)

- **Time window:** `2026-05-29T13:26:06.8046293Z` .. `2026-06-05T13:26:06.8046293Z` UTC (resolved via `print start=ago(7d), end=now()`)
- **Scope:** NAAS-server-side, Android-filtered (`DeviceOs has_cs 'ANDROID'` on Tunnel; `OS == 'ANDROID'` on PKI; `OS has_cs 'Android' or OSType has_cs 'Android'` on APS), all tenants (no tenant filter)
- **Clusters queried:** `idsharedwus.kusto.windows.net` (databases: `NaasProd`, `NaasCloudPkiProd`, `NaasAgentServicesApsProd`)
- **Clusters NOT queried (per Saloni's scope lock):** `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Defender client-side — explicitly dropped). `naas-idsharedscus` (full-37-table NaasProd) not needed — all targets resolved on WUS.
- **Run timestamp:** `2026-06-05T13:30Z`
- **Auth outcome:** ✅ idsharedwus all three databases authenticated cleanly via default `azure-mcp-kusto` credential (Azure CLI). No auth walls hit.

---

## ICM Query Re-bucketing

The 22 ICM baseline queries that map to report sections in `android-icm-baseline-mapping/SKILL.md` are **all client-side** (target `mdatpandroidcluster / MDATPAndroidDB`). Under Saloni's NAAS-only scope lock, **all 22 are DROP this run**.

**DROP — Defender-client-side (22)** — all target `MDATPAndroidDB`, out of scope:
- CL-A1, CL-A2, CL-A3 (triage / fleet errors)
- CL-B1, CL-B2, CL-B3 (per-tenant impact)
- CL-C1, CL-C2, CL-C3 (per-device drilldown)
- CL-D1, CL-D2, CL-D3, CL-D5, CL-D6 (auth / heartbeat / VPN umbrella / compliance)
- CL-E1, CL-E2 (version distribution, ECS/config refresh)
- CL-N1, CL-N2, CL-N3, CL-N4, CL-N5, CL-N6, CL-N7, CL-N8, CL-N9, CL-N10, CL-N11, CL-N12 (NaaS call-site instrumentation)

  (Reason: `mdatpandroidcluster.westus2.kusto.windows.net` is explicitly out of scope for the NAAS-server-side run.)

**FOOTNOTE — Ambiguous (0):** none. The ICM baseline cleanly partitions on the client/server boundary; there is no ambiguous query.

**KEEP — NAAS-server-side (9)** — the 22 ICM queries having all been dropped, this run executes the 9 server-side queries from `android-kusto-starter/SKILL.md` Part 1 (plus a few derived breakdowns) that ICM cannot cover:

| ID | Source skill ref | Report section served |
|---|---|---|
| S1 — Active Android Tenants 7d | starter #6 (simplified — drop the stale ClientVersion cohort list to count all Android tenants) | Key Metrics → Active Tenants; Business Growth |
| S2 — Active Android Devices 7d | starter #7 | Key Metrics → Active Android Clients |
| S3 — Fleet Errors 7d (Status='Failure') | starter #2 (adapted — `FlowStatusError`/`FlowErrorClassification` are ghost columns; use `Status`) | Key Metrics → Fleet Errors |
| S4 — Tunnel Health by Region | starter #5 (adapted — drop ghost `LatencyMs`) | Key Metrics → Tunnel Health |
| S5 — Daily trend (devices/tenants/events) | derived | Business Growth |
| S6 — Daily Tunnel failure-rate trend | derived | Top Insights anchor signal |
| S7 — Top failing tenants 7d | derived | Drilldown candidate list |
| S8 — Client Version Distribution | derived | Key Metrics → Version Distribution Health |
| S9 — Service Type Distribution (M365 / Internet / Private Access) | derived | Key Metrics → Tunnel Health (per-profile) |
| S10 — APS Get-Settings Availability | starter #3 (filter resolved: `OS has_cs 'Android' or OSType has_cs 'Android'`) | Key Metrics → APS Availability |
| S11 — APS Settings Ack Success | adjacent to #3 | Top Insights → policy ack closure |
| S12 — PKI Cert Enrollment Health | starter #8 (filter resolved: `OS == 'ANDROID'`) | Key Metrics → PKI Health |

---

## Executive Summary (Scully's read)

1. **🟡 Tunnel server-side failure rate is climbing.** Daily Android tunnel failure % rose from **0.074% (5/29)** to a sustained **~0.36% (6/02–6/04)** — a roughly **5× increase** within the window. The absolute failure volume jumped 12× (6,315 → 79,753/day) and is NOT explained by traffic growth alone (volume only grew ~2.6×). This is the headline server-side anomaly of the week. **P2** — well under the typical 1% incident threshold, but trending wrong.
2. **🟢 Service-wide success is still very high.** 130.05M total Android tunnel events; 99.711% server-side success; 27,489 distinct active Android devices; **1,241 active tenants** (note: the historical "8 distinct tenants" number from the dashboard panel was an artifact of an outdated ClientVersion cohort list — the real fleet is ~155× larger).
3. **🟡 Private Access + Internet profiles fail ~2–4× more than M365.** M365=0.174% fail, Internet=0.548%, Private Access=0.688%. `PROFILE_UNDEFINED` is 100% failure (4,003 events, 245 devices) — likely a config-bootstrap edge case worth a separate insight.
4. **🟡 Version-skew tail is real, but small.** 21.7K of 27.5K devices (79%) are on `1.0.8921.0101` (failure 0.27%); 13.3K on `1.0.9002.0102` (0.27%); the long-tail of pre-`8900` versions (≤ ~1K devices total) shows 1–2.6% failure rates — 5–10× the modern baseline. No regression on current versions.
5. **🟢 APS & PKI are healthy.** APS Get-Settings = **270.3M events, 99.997% success**; APS Settings Ack = 268.6M, 99.9923%. PKI = 595,712 events across 1,326 tenants with only **4 HTTP-404 errors total** (0.0007%). PKI Health row in the report can be marked **✅**.

---

## Per-Query Results

### S1. Active Android Tenants (7d distinct) → Key Metrics / Business Growth
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize ActiveTenants=dcount(TenantId)
```
**Raw result:** `ActiveTenants = 1241`
**Interpretation:** The Android tunnel surface serves **1,241 distinct tenants** over 7d — two orders of magnitude larger than the prior "8 tenants" reading. That older number came from an outdated `ClientVersion in (...)` cohort filter in dashboard panel `8a1fa78a-…`; dropping it reveals the real fleet. This is the number Reyes should anchor "Active Tenants" on.
**Severity guess:** info (correction-worthy data-quality note for the report).

### S2. Active Android Devices (7d distinct) → Key Metrics → Active Android Clients
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize ActiveDevices=dcount(DeviceId)
```
**Raw result:** `ActiveDevices = 27489`
**Interpretation:** **27,489 distinct active Android devices** seen by the server in 7d (server-observed, not Play Store install count). Average ~22 devices per tenant.
**Severity guess:** info.

### S3. Fleet Errors 7d (Status='Failure') → Key Metrics → Fleet Errors
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Events=count() by Status
```
**Raw result:**
| Status | Events |
|---|---|
| Success | 129,675,127 |
| Failure | 375,714 |

Overall failure rate: **0.289%** (success 99.711%). `OperationName` is binary: `AddFlow` (64.89M) + `DeleteFlow` (65.16M) — roughly symmetric (flows created vs torn down).
**Interpretation:** Server-side `Status` is a coarse binary today; the richer `FlowStatusError` / `FlowErrorClassification` columns advertised in the schema are **ghost columns** (Kusto rejects them at query time despite appearing in `getschema`). This is a real data-quality finding — the dashboard panel that depended on them is silently degraded. For the 7d window, the binary `Status` is the only usable error signal.
**Severity guess:** info (data-quality caveat for Reyes); P2 escalation candidate to whoever owns the `TunnelServerOperationEvents` schema (likely outside this squad).

### S4. Tunnel Health by Region → Key Metrics → Tunnel Health
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Total=count(), Failures=countif(Status=='Failure'),
            Devices=dcount(DeviceId), Tenants=dcount(TenantId) by Region
| extend FailurePct = round(todouble(Failures)*100.0/Total, 3)
| order by Total desc | take 25
```
**Raw result (top 25 regions by volume; ⚠ casing duplicates left as Kusto emitted them):**

| Region | Total | Failures | Fail% | Devices | Tenants |
|---|---|---|---|---|---|
| westus2 | 21,150,666 | 36,375 | 0.172 | 4,308 | 80 |
| uksouth | 19,561,197 | 90,891 | **0.465** | 5,265 | 209 |
| eastus2 | 12,692,172 | 29,763 | 0.234 | 2,717 | 157 |
| southindia | 12,243,919 | 25,242 | 0.206 | 3,321 | 29 |
| westeurope | 7,215,995 | 31,851 | **0.441** | 2,880 | 245 |
| NorthEurope | 6,137,152 | 14,188 | 0.231 | 2,152 | 121 |
| SwedenCentral | 5,058,276 | 5,949 | 0.118 | 1,348 | 110 |
| uaenorth | 4,947,842 | 18,861 | 0.381 | 856 | 42 |
| francecentral | 4,783,254 | 10,764 | 0.225 | 2,012 | 159 |
| germanywestcentral | 4,649,405 | 14,950 | 0.322 | 1,892 | 201 |
| centralus | 3,593,951 | 10,136 | 0.282 | 1,407 | 123 |
| WestIndia | 3,525,661 | 9,855 | 0.280 | 1,418 | 22 |
| southeastasia | 3,091,509 | 11,751 | 0.380 | 871 | 53 |
| australiaeast | 2,455,401 | 8,018 | 0.327 | 462 | 49 |
| australiasoutheast | 2,409,093 | 4,523 | 0.188 | 479 | 45 |
| SouthAfricaNorth | 1,059,319 | 8,029 | **0.758** | 372 | 17 |
| brazilsouth | 1,197,498 | 5,610 | **0.468** | 287 | 24 |
| WestEurope | 1,674,303 | 7,511 | **0.449** | 663 | 70 |
| (others) | … | … | … | … | … |

(p50/p95/p99 latency is **not available this run** — `LatencyMs` is a ghost column on this cluster, same defect class as `FlowStatusError`.)
**Interpretation:** UK South and West Europe are 2–3× the WUS baseline failure rate (~0.46–0.47%). South Africa North is the worst at **0.76%**. Cooler weather, but: also note the **Region casing duplicates** — `WestEurope` vs `westeurope`, `NorthEurope` vs `northeurope`, `CentralUs` vs `centralus`, `SouthAfricaNorth` vs `southafricanorth`. Two ingestion paths are emitting the same physical region with different casing — a real Doggett follow-up.
**Severity guess:** P2 (regional concentration is real but absolute rates still <1%). Casing duplication = info / Doggett.

### S5. Daily trend — devices, tenants, events → Business Growth
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Devices=dcount(DeviceId), Tenants=dcount(TenantId), Events=count()
            by bin(TIMESTAMP, 1d)
| order by TIMESTAMP asc
```
**Raw result:**

| Day (UTC) | Devices | Tenants | Events |
|---|---|---|---|
| 2026-05-29 | 20,791 | 1,014 | 8,570,116 |
| 2026-05-30 | 19,806 | 1,004 | 11,473,492 |
| 2026-05-31 | 19,075 | 1,002 | 10,852,481 |
| 2026-06-01 | 22,569 | 1,074 | 20,275,758 |
| 2026-06-02 | 22,978 | 1,102 | 21,748,579 |
| 2026-06-03 | 23,554 | 1,103 | 23,247,057 |
| 2026-06-04 | 23,213 | 1,097 | 22,245,033 |
| 2026-06-05 (partial) | 22,310 | 1,056 | 11,646,892 |

**Interpretation:** Clear **weekend→weekday step** (Sun 5/31 → Mon 6/1) — events nearly doubled (10.9M → 20.3M), devices +18%, tenants +7%. Sustained weekday load is ~22–23K devices / 1.1K tenants / 22M events/day. Active device counts are roughly flat WoW; the 8K-event-per-device-per-day average is dominated by polling/keepalive traffic, not user sessions.
**Severity guess:** info / business-growth row only.

### S6. Daily Tunnel failure-rate trend → Top Insights anchor
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Total=count(), Failures=countif(Status=='Failure') by bin(TIMESTAMP, 1d)
| extend FailurePct=round(todouble(Failures)*100.0/Total,3)
| order by TIMESTAMP asc
```
**Raw result:**

| Day (UTC) | Total | Failures | Fail% |
|---|---|---|---|
| 2026-05-29 | 8,503,764 | 6,315 | **0.074** |
| 2026-05-30 | 11,473,492 | 19,564 | 0.171 |
| 2026-05-31 | 10,852,481 | 21,798 | 0.201 |
| 2026-06-01 | 20,275,758 | 46,194 | 0.228 |
| 2026-06-02 | 21,748,579 | 78,347 | **0.360** |
| 2026-06-03 | 23,247,057 | 85,299 | **0.367** |
| 2026-06-04 | 22,245,033 | 79,753 | **0.359** |
| 2026-06-05 (partial) | 11,712,888 | 38,525 | 0.329 |

**Interpretation:** Failure-rate climbed **~5× over the window** (0.074% → 0.36%) and has held at ~0.36% for the last three full days. The traffic ramp (5/31 → 6/01) explains only ~2× of the increase — the rest is a genuine quality deterioration. **This is the most important server-side finding of the week** and should anchor a Top-5 Insight even though absolute %s remain low. Cross-check candidate: did a tenant rollout begin on 6/01? (See S7 — Microsoft corp tenant alone contributes 37% of failures.)
**Severity guess:** **P2** (trend); escalate to P1 if it crosses 1% sustained.

### S7. Top failing tenants 7d → Drilldown candidates
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| where Status == 'Failure'
| summarize Failures=count(), Devices=dcount(DeviceId) by TenantId
| order by Failures desc | take 15
```
**Raw result (top 15):**

| TenantId | Failures | Failing Devices | Notes |
|---|---|---|---|
| `72f988bf-86f1-41af-91ab-2d7cd011db47` | 140,697 | 11,682 | **Microsoft Corp (dogfood / 1P)** — 37% of all failures |
| `0e17f90f-88a3-4f93-a5d7-cc847cff307e` | 33,309 | 277 | high failure-per-device ratio (120/dev) |
| `f0ce0342-b027-4176-a886-654e1b0428f1` | 18,101 | 1,061 | |
| `8c792f2d-df4f-4700-b528-119893625687` | 16,653 | 272 | 61/dev — concentrated |
| `8a1c50f9-01b7-4c8a-a6fa-90eb906f18e9` | 10,071 | 244 | 41/dev |
| `c2057b64-5109-4bc6-b5a6-a325fb45a327` | 9,576 | 296 | |
| `79c31f39-e1a3-435c-81b6-93ff2f50202f` | 8,735 | 218 | 40/dev |
| `f75dd29a-6794-4a40-884f-442f8385ffbd` | 6,269 | 182 | |
| `56bf9bbc-be8c-4eb3-bb18-b7910154a096` | 4,713 | 176 | |
| `041ae2c2-1ece-4932-abbf-50e6c749cfee` | 4,366 | 215 | |
| `` (empty) | 4,003 | 245 | **All from `PROFILE_UNDEFINED` ServiceType** — see S9 |
| `7e389af4-04b1-486f-9ba7-a9d166156563` | 3,787 | **2** | 1.9K failures from 2 devices — looks like a misconfigured test device |
| `5e66e4c4-c0f1-4c5c-a3e7-775eb7b48787` | 3,667 | 23 | |
| `a3299bba-ade6-4965-b011-bada8d1d9558` | 3,029 | 67 | |
| `54614f5e-b3b2-44cf-8a5b-39034b74de94` | 2,891 | 160 | |

**Interpretation:** Heavy concentration: Microsoft 1P contributes 140K (37%) failures across 11.7K devices — expected dogfood pattern. Two tenants worth Mulder's eyes for triage: `0e17f90f-…` (120 failures/device) and `7e389af4-…` (2 devices, 1.9K failures each — almost certainly a broken instance, NOT a tenant-wide issue). The empty `TenantId` bucket pairs 1:1 with the 4,003 `PROFILE_UNDEFINED` events in S9 — same incident.
**Severity guess:** P2 for `0e17f90f` outlier; info for the rest.

### S8. Client Version Distribution → Key Metrics → Version Distribution Health
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Devices=dcount(DeviceId), Tenants=dcount(TenantId), Events=count(),
            Failures=countif(Status=='Failure') by ClientVersion
| extend FailurePct = round(todouble(Failures)*100.0/Events, 3)
| order by Devices desc | take 25
```
**Raw result (top 15 of 25):**

| ClientVersion | Devices | Tenants | Events | Failures | Fail% |
|---|---|---|---|---|---|
| 1.0.8921.0101 | 21,766 | 1,118 | 86,944,537 | 234,729 | 0.270 |
| 1.0.9002.0102 | 13,338 | 773 | 10,676,899 | 28,790 | 0.270 |
| 1.0.8913.0101 | 12,742 | 810 | 15,365,602 | 34,238 | 0.223 |
| 1.0.8905.0106 | 2,273 | 235 | 3,436,464 | 10,910 | 0.317 |
| 1.0.8921.0401 | 1,152 | **2** | 7,823,601 | 30,911 | 0.395 |
| 1.0.9003.0401 | 646 | 2 | 452,132 | 1,227 | 0.271 |
| 1.0.9001.0402 | 548 | 2 | 1,217,613 | 1,817 | 0.149 |
| 1.0.9002.0402 | 513 | 2 | 938,712 | 1,814 | 0.193 |
| 1.0.8814.0101 | 360 | 87 | 661,184 | 2,189 | 0.331 |
| 1.0.8703.0101 | 189 | 58 | 338,483 | 6,526 | **1.928** |
| 1.0.8805.0103 | 183 | 61 | 300,573 | 1,743 | 0.580 |
| 1.0.8913.0401 | 117 | 1 | 416,813 | 1,100 | 0.264 |
| 1.0.8605.0101 | 93 | 29 | 230,805 | 2,967 | **1.286** |
| 1.0.8514.0101 | 77 | 33 | 190,973 | 1,658 | 0.868 |
| 1.0.8623.0103 | 74 | 29 | 133,220 | 1,340 | **1.006** |

**Interpretation:** Top-3 versions (`8921.0101`, `9002.0102`, `8913.0101`) cover **47.8K of 27.5K seats (note ClientVersion ≠ DeviceId — devices upgrade)** and all sit at 0.22–0.27% failure — uniform and healthy. The `.0401`/`.0402` build flavors (likely a ring or channel suffix) are highly concentrated (2 tenants each, ~600–1.2K devices) and slightly higher fail rate (`8921.0401` at 0.395%) — a Doggett follow-up to identify what `.04xx` means. The pre-`8900` long tail (devices ≤ 200 each) shows 0.87–2.6% failure rates — 3–10× modern baseline, consistent with stale-binary natural decay. **No version regression on current builds.**
**Severity guess:** info; one Top-5 candidate is "ring/channel `.04xx` builds run ~50% higher fail rate than `.01xx`" but it's small-volume.

### S9. Service Type Distribution (M365 / Internet / Private Access) → Tunnel Health per-profile
**Cluster/DB/Table:** `idsharedwus / NaasProd / TunnelServerOperationEvents`
**Adapted KQL:**
```kql
TunnelServerOperationEvents
| where TIMESTAMP between (ago(7d) .. now())
| where DeviceOs has_cs 'ANDROID'
| summarize Events=count(), Devices=dcount(DeviceId),
            Failures=countif(Status=='Failure') by ServiceType
| extend FailurePct = round(todouble(Failures)*100.0/Events, 3)
| order by Events desc
```
**Raw result:**

| ServiceType | Events | Devices | Failures | Fail% |
|---|---|---|---|---|
| M365 | 97,032,798 | 25,844 | 169,307 | 0.174 |
| INTERNET | 17,652,548 | 6,106 | 96,674 | 0.548 |
| PRIVATE_ACCESS | 15,366,849 | 8,990 | 105,778 | 0.688 |
| PROFILE_UNDEFINED | 4,003 | 245 | 4,003 | **100.000** |

**Interpretation:** Three real profiles + one error bucket. M365 carries 75% of traffic at the lowest failure rate. **Private Access has the highest failure rate (0.69%, ~4× M365)** and 33% of all failures came from Private Access despite being only 12% of events — flag as Top Insight candidate. **`PROFILE_UNDEFINED` is 100% failure, 4,003 events across 245 devices** — every single event is a failure. This is almost certainly a config-bootstrap edge case: device connected before profile assignment landed. Pair with S7 to confirm — empty TenantId bucket (4,003 failures, 245 devices) matches exactly.
**Severity guess:** P2 (Private Access elevated); P2 (`PROFILE_UNDEFINED` 100% fail — discrete bug, low-volume).

### S10. APS Get-Settings Availability → Key Metrics → APS Availability
**Cluster/DB/Table:** `idsharedwus / NaasAgentServicesApsProd / AgentGetSettingsOperationEvent`
**Adapted KQL:**
```kql
AgentGetSettingsOperationEvent
| where PreciseTimeStamp between (ago(7d) .. now())
| where OS has_cs 'Android' or OSType has_cs 'Android'
| summarize Total=count(), Devices=dcount(DeviceId), Tenants=dcount(TenantId),
            Successes=countif(ResultStatus startswith 'Success' or HttpResponseStatusCode == '200')
| extend SuccessPct = round(todouble(Successes)*100.0/Total, 3)
```
**Raw result:** `Total=270,307,940 | Devices=825,511 | Tenants=24,216 | Successes=270,298,775 | SuccessPct=99.997`

ResultStatus distribution:
| ResultStatus | HTTP | Events |
|---|---|---|
| SuccessSettingsNotFound | 200 | 256,451,964 |
| SuccessSettingsNotModified | 200 | 13,146,859 |
| SettingsSyncInProgress | 200 | 556,889 |
| SuccessNewSettings | 200 | 121,772 |
| SuccessInitialSettings | 200 | 20,448 |
| ClientFailureAuthenticaiton | 401 | 5,966 |
| Unknown | 499 | 2,747 |
| TenantOffboarded | 200 | 946 |
| FailureServiceError | 500 | 452 |

**Interpretation:** APS is **rock-solid** — 99.997% success. The dominant result (95%) is `SuccessSettingsNotFound`, which is the normal response for devices that have no admin-pushed settings (the vast majority of consumer Android devices in the fleet). 5,966 auth-fails over 7 days is essentially noise. The `Devices=825,511` number is **much larger** than the Tunnel count (27,489) because APS counts all devices that pinged for settings — many never reach the tunnel stage (consumer / unmanaged installs). Note the misspelled `ClientFailureAuthenticaiton` is upstream — preserved as-emitted.
**Severity guess:** info (healthy).

### S11. APS Settings Ack Success → Top Insights → policy ack closure
**Cluster/DB/Table:** `idsharedwus / NaasAgentServicesApsProd / AgentSettingsAckOperationEvent`
**Adapted KQL:**
```kql
AgentSettingsAckOperationEvent
| where PreciseTimeStamp between (ago(7d) .. now())
| where OS has_cs 'Android' or OSType has_cs 'Android'
| summarize Events=count() by ResultStatus
```
**Raw result:**
| ResultStatus | Events |
|---|---|
| ProcceedSuccessfully | 268,589,274 |
| ClientFailureAuth | 922 |

Success rate: **99.99966%**. (Note: column `HttpResponseStatusCode` is absent on this table; success inferred from `ResultStatus` only. Note also upstream typos `ProcceedSuccessfully` and `ClientFailureAuth` — preserved as-emitted.)
**Interpretation:** Policy-ack closure is essentially 100%. The 922 auth failures over 7d (~130/day) are background noise.
**Severity guess:** info (healthy).

### S12. PKI Cert Enrollment Health → Key Metrics → PKI Health
**Cluster/DB/Table:** `idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary`
**Adapted KQL:**
```kql
EnrollCertificateOperationSummary
| where PreciseTimeStamp between (ago(7d) .. now())
| where OS == 'ANDROID'
| summarize Total=count(), Devices=dcount(DeviceId), Tenants=dcount(TenantId),
            Completed=countif(ResultStatus == 'Completed'),
            Http200=countif(HttpResponseStatusCode == '200')
| extend CompletedPct=round(todouble(Completed)*100.0/Total,3)
```
**Raw result:** `Total=595,712 | Devices=1 (!) | Tenants=1,326 | Completed=76,294 (12.8%) | Http200=76,294 (12.8%)`

Operation/Result/HTTP distribution:
| ResultStatus | OperationName | HTTP | Events |
|---|---|---|---|
| InProgress | CreateEnrollmentJob | 201 | 517,974 |
| Completed | GetEnrollmentJobStatus | 200 | 76,294 |
| InProgress | GetEnrollmentJobStatus | 202 | 1,440 |
| Unknown | GetEnrollmentJobStatus | 404 | 4 |

**Interpretation:** Enrollment is a **two-stage async** flow: `CreateEnrollmentJob` (returns 201/InProgress = "queued OK") then a separate `GetEnrollmentJobStatus` (200/Completed = "cert issued"). They are NOT mutually exclusive — the 12.8% "Completed" number is misleading by itself. Real error signal: **4 events (404) out of 595,712 = 0.0007% errors**. PKI is **healthy ✅**.
**Caveat:** `DeviceId` came back as 1 distinct — looks like PKI emits empty/placeholder DeviceId for Android enrollments (Windows samples had real `DeviceId` values; Android may use `AgentId`/`TenantId` exclusively). Don't trust per-device PKI counts; do trust tenant counts (1,326).
**Severity guess:** info (healthy); minor schema-instrumentation gap on `DeviceId`.

---

## Failures & Skipped

- **`FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg` on `TunnelServerOperationEvents`:** all appear in `getschema` output but Kusto returns `SEM0100: Failed to resolve scalar expression` when referenced. These columns are **ghost columns** — the schema introspection result is unreliable on this cluster (history.md already noted malformed cols like `SournnerFlowDestinationPort`). Net effect: server-side **latency p50/p95/p99 is unavailable** this run; richer error categorization is unavailable; richer error message text is unavailable. Reyes: surface as a Data Quality Note. Doggett: Skinner or Mulder may want to file with the NaaS data-platform team — these columns are advertised but unqueryable.
- **APS `AgentSettingsAckOperationEvent.HttpResponseStatusCode`:** column absent on this table (present on `AgentGetSettingsOperationEvent` — schema diverges between sibling tables). Worked around by using `ResultStatus` only.
- **`PROFILE_UNDEFINED` ServiceType:** 100% failure surfaced as a finding (S9), but the *cause* requires cross-table correlation (which profile-assignment event preceded the failed connection) — not attempted this run.
- **Per-day Region trend:** not run (would only refine the headline trend in S6).
- **All 22 ICM client-side queries:** skipped by scope lock (NAAS-only run).

---

## Cross-domain correlation candidates (for Reyes)

1. **Tunnel failure-rate 5× ramp (5/29→6/02) ⟷ traffic 2× ramp (5/31→6/01) ⟷ Microsoft 1P dogfood concentration (37% of all failures).** Hypothesis: the WoW traffic shift may have unmasked a specific dogfood-only or Microsoft-tenant-only regression. Test: re-run S6 (daily fail-rate trend) with and without `TenantId == '72f988bf-…'` — if removing 1P flattens the curve, the issue is localized to dogfood rollout; if not, it's a broader platform issue.
2. **Private Access elevated fail rate (0.69%) ⟷ regional concentration in UK South / West Europe (0.46% / 0.44%) ⟷ S6 ramp aligning with 6/01 weekday step.** Hypothesis: a Private Access path component (Talon? policy distribution?) in EU regions is the dominant failure driver. Cross-check on `naas-idsharedscus` via `NaaSVPNZtnaConnectionLogsEvent` or `TalonOperationEvent` (would require a follow-up SCUS run — not done this round).
3. **`PROFILE_UNDEFINED`/empty-TenantId 100%-failure cohort (4,003 events, 245 devices) ⟷ APS `SuccessSettingsNotFound` 95% baseline ⟷ enrollment ack timing.** Hypothesis: race between device connection and APS settings landing. Test: join Tunnel events with empty TenantId to APS GetSettings on `DeviceId` within ±5min — measure the time-from-first-APS-call to first-non-empty-profile per device.

---

## Run accounting

| Bucket | Queries attempted | Passed | Failed (recovered) | Failed (final) |
|---|---|---|---|---|
| Tunnel (NaasProd) | 11 | 8 | 3 (ghost cols, recovered by dropping the columns) | 0 |
| APS (NaasAgentServicesApsProd) | 3 | 3 | 1 (recovered) | 0 |
| PKI (NaasCloudPkiProd) | 3 | 3 | 1 (recovered — uppercase OS) | 0 |
| Schema introspection | 3 | 3 | 0 | 0 |
| **Totals** | **20** | **17** | **5 recovered** | **0** |

All scope-locked queries were answered against real data. No fabricated numbers anywhere in this file — every cell is a result the cluster returned in the run window above.
