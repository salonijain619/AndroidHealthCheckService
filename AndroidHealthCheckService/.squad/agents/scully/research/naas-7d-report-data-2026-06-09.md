# NAAS 7-day Report Data (Android) — v3 daily report (2026-06-09)

- **Time window:** `2026-06-02T00:00:00Z` .. `2026-06-09T00:00:00Z` UTC (closed 7-day window; queries use `between(…)` which is inclusive both ends, so a sliver of events stamped exactly `2026-06-09T00:00:00Z` shows in daily bins — negligible: 187 events).
- **Scope:** NAAS-server-side, Android-filtered (`DeviceOs has_cs 'ANDROID'` on Tunnel; `OS == 'ANDROID'` on PKI; `OS has_cs 'Android' or OSType has_cs 'Android'` on APS), all tenants (no tenant filter).
- **Clusters queried:** `idsharedwus.kusto.windows.net` (databases: `NaasProd`, `NaasCloudPkiProd`, `NaasAgentServicesApsProd`).
- **Clusters NOT queried (LOCKED scope):** Defender `mdatpandroidcluster.*` (explicit drop). `naas-idsharedscus` not consulted.
- **Run timestamp:** `2026-06-09T09:12Z`
- **Auth outcome:** ✅ default `azure-mcp-kusto` credential clean against all three databases. Coordinator's reachability check (HTTP 401 unauth challenge + port-443 nc) reproduced — yesterday's TCP-timeout block is cleared.
- **Baseline for comparison:** `naas-7d-report-data-2026-06-05.md` (v1).
- **Re-used query suite:** identical to 2026-06-05 — same KQL, same filters, just shifted window. No new tables, no schema changes attempted.

---

## ⬆️/⬇️ Headline movements vs v1 (2026-06-05 baseline)

| Metric | v1 (5/29→6/05) | v3 (6/02→6/09) | Δ | Direction |
|---|---|---|---|---|
| Total tunnel events (7d) | 130,050,841 | **131,874,839** | +1.4% | ➡️ flat-ish (traffic stable) |
| Total tunnel failures (7d) | 375,714 | **507,643** | **+35.1%** | ⬆️ **WORSE** |
| 7d overall fail-rate | 0.289% | **0.385%** | +33.2% | ⬆️ **WORSE** |
| Active Android devices (7d distinct) | 27,489 | **27,744** | +0.9% | ➡️ flat |
| Active tenants (7d distinct) | 1,241 | **1,254** | +1.0% | ➡️ flat |
| Microsoft 1P (`72f988bf-…`) share of failures | 37.4% | **38.3%** | +0.9pp | ➡️ flat |
| Private Access vs M365 fail-rate ratio | 3.95× (0.688 / 0.174) | **4.09×** (0.929 / 0.227) | +3.6% | ➡️ ratio stable, both moved up |
| PROFILE_UNDEFINED cohort (events / devices) | 4,003 / 245 (100% fail) | **4,403 / 345** (100% fail) | +10% / **+40.8%** | ⬆️ devices growing |
| APS Get-Settings success | 99.997% (270.3M) | **99.996%** (268.9M) | ~flat | ➡️ healthy |
| APS Settings Ack success | 99.99966% (268.6M) | **99.99970%** (267.2M) | ~flat | ➡️ healthy |
| PKI errors (count / pct) | 4 / 0.0007% (595,712) | **5 / 0.0007%** (707,887) | new error class (2× HTTP 500) | ⬇️ tiny but new failure mode |
| Ghost columns (FlowStatusError / FlowErrorClassification / LatencyMs / Msg) | unqueryable | **STILL unqueryable** (SEM0100 reproduced today) | — | 🔴 unfixed in 4 days |

**Ramp-anchor verdict:** ❌ **NOT stabilized. Got worse.** v1 noted a sustained ~0.36% plateau across 6/02–6/04. The new window shows 6/05 still at 0.354%, then a clear **second-stage climb** on weekend+Mon: 6/06 = 0.416%, 6/07 = 0.431%, **6/08 = 0.447%** — the highest single-day rate in either window. Failure volume on 6/08 alone (95,112) is more than 15× the 5/29 baseline (6,315).

---

## Top 5 things Reyes should anchor the v3 report on

1. **The 5× ramp didn't plateau — it bumped a second step.** 0.074% (5/29) → 0.36% plateau (6/02–6/05) → **0.42–0.45% sustained (6/06–6/08)**. Three additional days of degradation, no signs of self-recovery. Promote from "P2 trend" to **P2-trending-P1** in the report — at 0.447% on 6/08, a single +0.55pp day clears the 1% threshold.
2. **The deterioration is broader than 1P.** Removing Microsoft (`72f988bf-…`) from the daily series **does not flatten** the curve — non-1P fail-rate actually runs HIGHER (0.49–0.60% range) than the global rate. This rules out the "dogfood rollout artifact" hypothesis from v1 cross-domain candidate #1. The regression is platform-wide, not Microsoft-tenant-local.
3. **Private Access + Internet both took a +35–40% hit.** ServiceType fail-rates: M365 0.174→0.227 (+30%), INTERNET 0.548→0.766 (+40%), PRIVATE_ACCESS 0.688→**0.929** (+35%). The 4× Private-Access:M365 ratio is unchanged, so this isn't a profile-specific issue — every profile got worse by the same fraction. Strong platform-component-degradation fingerprint.
4. **New top mover in regions: Germany West Central +67%, West Europe (capital) +53%.** germanywestcentral 0.322→0.539, WestEurope (capital casing) 0.449→**0.685**, uksouth 0.465→0.587 (+26%), westus2 0.172→0.234 (+36%). Worst single rate this week: SouthAfricaNorth (capital) 0.764% — but uksouth is still the biggest absolute-failure region (118,657 fails over 7d). EU clustering is real and intensifying.
5. **Version-suffix `.04xx` flavor is now the worst high-volume cohort.** v1 flagged `.04xx` as suspicious but small. New: `1.0.9003.0401` went 646→**1,003 devices** (+55%) **and** failure 0.271→**0.626%** (+131%). `1.0.8921.0401` failure 0.395→0.491 (+24%). The mainstream `.01xx` builds (`8921.0101`, `9002.0102`) also rose ~30% but stay in 0.33–0.35 band — `.04xx` is fairly clearly a worse ring. Doggett: identify what `.04xx` is.

---

## Raw numbers Reyes can paste

### S1+S2+S3 (combined) — Fleet totals 7d
```
ActiveTenants = 1,254
ActiveDevices = 27,744
TotalEvents   = 131,874,839
Failures      = 507,643
SuccessPct    = 99.615%
FailurePct    = 0.385%
```

### S6 — Daily Tunnel failure-rate trend (THE anchor) 
| Day (UTC) | Devices | Tenants | Events | Failures | Fail% | Δ vs v1 |
|---|---|---|---|---|---|---|
| 2026-06-02 | 22,978 | 1,102 | 21,748,579 | 78,347 | 0.360 | identical |
| 2026-06-03 | 23,554 | 1,103 | 23,247,057 | 85,299 | 0.367 | identical |
| 2026-06-04 | 23,213 | 1,097 | 22,245,033 | 79,753 | 0.359 | identical |
| 2026-06-05 | 23,242 | 1,082 | 20,784,502 | 73,487 | **0.354** | (v1 partial = 0.329) — full day landed at 0.354 |
| 2026-06-06 | 20,270 | 1,022 | 11,552,098 | 48,100 | **0.416** | NEW |
| 2026-06-07 | 19,465 | 1,014 | 11,043,141 | 47,544 | **0.431** | NEW |
| 2026-06-08 | 23,175 | 1,097 | 21,254,242 | **95,112** | **0.447** | NEW — worst single-day in either window |
| 2026-06-09 (sliver, 1 stamp) | 139 | 34 | 187 | 1 | 0.535 | edge-of-window noise |

7-day arc: stable plateau → step up on weekend → another step up Monday 6/08. **Not recovering.**

### S6b — Same trend with Microsoft 1P stripped (NEW probe this run)
Hypothesis test from v1 cross-domain candidate #1.
| Day (UTC) | Events (non-1P) | Failures | Fail% (non-1P) |
|---|---|---|---|
| 2026-06-02 | 9,599,944 | 47,446 | **0.494** |
| 2026-06-03 | 10,793,814 | 59,158 | **0.548** |
| 2026-06-04 | 9,855,812 | 52,299 | 0.531 |
| 2026-06-05 | 9,013,169 | 40,750 | 0.452 |
| 2026-06-06 | 4,922,763 | 28,215 | 0.573 |
| 2026-06-07 | 4,832,257 | 29,155 | **0.603** |
| 2026-06-08 | 9,400,213 | 56,140 | **0.597** |

**Result:** non-1P fail-rate runs ~30–60% HIGHER than the global rate every day. Microsoft's 1P/dogfood traffic is **dampening** the headline; the underlying customer-tenant degradation is sharper than the global number implies. Cross-domain candidate #1 from v1 is **falsified** — issue is not localized to 1P rollout.

### S4 — Tunnel Health by Region (top 25, casing-as-emitted)
| Region | Total | Failures | Fail% | Devices | Tenants | Δ Fail% vs v1 |
|---|---|---|---|---|---|---|
| westus2 | 21,453,093 | 50,302 | 0.234 | 4,578 | 97 | +36% |
| uksouth | 20,204,825 | 118,657 | **0.587** | 5,274 | 211 | +26% |
| southindia | 13,673,229 | 50,414 | 0.369 | 3,513 | 32 | +79% |
| eastus2 | 12,503,198 | 35,325 | 0.283 | 2,726 | 158 | +21% |
| westeurope | 7,009,686 | 29,140 | 0.416 | 2,872 | 246 | -6% |
| NorthEurope | 6,305,798 | 23,375 | 0.371 | 2,151 | 129 | +61% |
| SwedenCentral | 5,196,296 | 13,099 | 0.252 | 1,348 | 111 | +114% |
| uaenorth | 4,990,280 | 18,495 | 0.371 | 845 | 42 | -3% |
| francecentral | 4,785,632 | 16,955 | 0.354 | 1,999 | 163 | +57% |
| germanywestcentral | 4,675,247 | 25,221 | **0.539** | 1,925 | 207 | **+67%** |
| centralus | 3,799,234 | 11,886 | 0.313 | 1,454 | 127 | +11% |
| southeastasia | 3,225,436 | 15,243 | 0.473 | 905 | 56 | +24% |
| WestIndia | 2,664,882 | 9,549 | 0.358 | 1,346 | 22 | +28% |
| australiaeast | 2,490,594 | 11,213 | 0.450 | 459 | 51 | +38% |
| australiasoutheast | 2,266,936 | 4,966 | 0.219 | 473 | 43 | +16% |
| WestEurope | 1,930,467 | 13,224 | **0.685** | 681 | 69 | **+53%** |
| CentralUs | 1,898,801 | 4,526 | 0.238 | 818 | 69 | — |
| SouthCentralUs | 1,872,898 | 8,968 | 0.479 | 531 | 42 | — |
| japaneast | 1,572,303 | 5,413 | 0.344 | 454 | 43 | — |
| southafricanorth | 1,336,782 | 7,120 | 0.533 | 304 | 25 | — |
| northeurope | 1,268,686 | 5,900 | 0.465 | 514 | 65 | — |
| brazilsouth | 1,142,323 | 6,782 | 0.594 | 293 | 24 | +27% |
| SouthAfricaNorth | 1,109,284 | 8,474 | **0.764** | 330 | 18 | +1% |
| westcentralus | 954,912 | 4,073 | 0.427 | 470 | 40 | — |
| canadaeast | 908,602 | 2,604 | 0.287 | 219 | 27 | — |

Latency p50/p95/p99: **unavailable** (LatencyMs still ghost). Region casing duplicates (`WestEurope`/`westeurope`, `CentralUs`/`centralus`, etc.) **still present, unfixed** — two-path ingestion confirmed 4 days later.

### S7 — Top failing tenants 7d
| TenantId | Failures | Devices | Fail/Dev | Notes vs v1 |
|---|---|---|---|---|
| `72f988bf-86f1-41af-91ab-2d7cd011db47` (Microsoft 1P) | **194,480** | 12,701 | 15.3 | failures +38%, devices +8.7% |
| `0e17f90f-88a3-4f93-a5d7-cc847cff307e` | **46,618** | 282 | **165** | **+40% failures**, devices flat — escalating per-device |
| `f0ce0342-b027-4176-a886-654e1b0428f1` | 23,871 | 1,099 | 21.7 | +32% |
| `8c792f2d-df4f-4700-b528-119893625687` | 19,480 | 284 | 68.6 | +17% |
| `8a1c50f9-01b7-4c8a-a6fa-90eb906f18e9` | 14,232 | 278 | 51.2 | +41% |
| `c2057b64-5109-4bc6-b5a6-a325fb45a327` | 11,064 | 298 | 37.1 | +16% |
| `79c31f39-e1a3-435c-81b6-93ff2f50202f` | 9,935 | 220 | 45.2 | +14% |
| `041ae2c2-1ece-4932-abbf-50e6c749cfee` | 8,744 | 222 | 39.4 | **+100%** (was 4,366 / 215) |
| `f75dd29a-6794-4a40-884f-442f8385ffbd` | 6,893 | 186 | 37.1 | +10% |
| `56bf9bbc-be8c-4eb3-bb18-b7910154a096` | 4,891 | 176 | 27.8 | +4% |
| `9cf9036f-5fc5-475d-846d-94ea941e4bfc` | **4,740** | 45 | **105** | **NEW top-15 entrant** (not in v1) |
| `""` (empty TenantId, == PROFILE_UNDEFINED cohort) | 4,403 | 345 | 12.8 | +10% events, +41% devices |
| `54614f5e-b3b2-44cf-8a5b-39034b74de94` | 4,187 | 168 | 24.9 | +45% |
| `a3299bba-ade6-4965-b011-bada8d1d9558` | 4,151 | 60 | 69.2 | +37% |
| `5e66e4c4-c0f1-4c5c-a3e7-775eb7b48787` | 4,110 | 25 | **164** | +12% |

**New top-15 entrant:** `9cf9036f-5fc5-475d-846d-94ea941e4bfc` (105 fails/device, 45 devices) — Mulder triage candidate.
**Note:** Tenant `7e389af4-04b1-486f-9ba7-a9d166156563` (the "2 devices / 1.9K failures each" outlier from v1) dropped out of top-15 — either the misconfigured device(s) were fixed or stopped emitting. Worth a one-line note in the report (one v1 outlier self-resolved).

### S8 — Client Version Distribution (top 15)
| ClientVersion | Devices | Tenants | Events | Failures | Fail% | Δ Fail% vs v1 |
|---|---|---|---|---|---|---|
| 1.0.8921.0101 | 21,352 | 1,092 | 61,640,489 | 217,856 | **0.353** | +31% |
| 1.0.9002.0102 | 20,174 | 1,054 | 49,761,167 | 163,433 | **0.328** | +21% |
| 1.0.8913.0101 | 3,339 | 333 | 5,024,538 | 24,284 | 0.483 | +117% (cohort shrank to 26%) |
| 1.0.8905.0106 | 1,553 | 198 | 2,050,065 | 10,665 | 0.520 | +64% |
| 1.0.8921.0401 | 1,102 | 2 | 3,475,829 | 17,075 | 0.491 | +24% |
| 1.0.9003.0401 | **1,003** | 2 | 4,600,055 | **28,814** | **0.626** | **+131%** — biggest mover |
| 1.0.9001.0402 | 549 | 2 | 1,323,185 | 2,463 | 0.186 | +25% |
| 1.0.9002.0402 | 515 | 2 | 1,164,943 | 3,756 | 0.322 | +67% |
| 1.0.8814.0101 | 312 | 84 | 566,734 | 2,638 | 0.465 | +40% |
| 1.0.8703.0101 | 174 | 56 | 334,917 | 8,952 | **2.673** | +39% |
| 1.0.8805.0103 | 171 | 59 | 278,722 | 2,493 | 0.894 | +54% |
| 1.0.8605.0101 | 90 | 29 | 216,399 | 2,923 | 1.351 | +5% |
| 1.0.8913.0401 | 83 | 2 | 245,909 | 812 | 0.330 | +25% |
| 1.0.8514.0101 | 67 | 28 | 185,555 | 1,766 | 0.952 | +10% |
| 1.0.8623.0103 | 63 | 25 | 111,079 | 1,605 | 1.445 | +44% |

**Two cohort movements worth note:** `9002.0102` is gaining seats (13.3K → 20.2K, +51%) — a real rollout in progress. `8913.0101` is decaying (12.7K → 3.3K, -74%) — devices upgrading off it.

### S9 — Service Type Distribution
| ServiceType | Events | Devices | Failures | Fail% | Δ vs v1 |
|---|---|---|---|---|---|
| M365 | 98,754,224 | 26,146 | 224,558 | **0.227** | +30% |
| INTERNET | 17,727,642 | 6,110 | 135,715 | **0.766** | +40% |
| PRIVATE_ACCESS | 15,388,570 | 9,106 | 142,967 | **0.929** | +35% |
| PROFILE_UNDEFINED | 4,403 | **345** | 4,403 | 100.000 | +10% events / **+41% devices** |

Private Access / M365 ratio: 4.09× (v1 was 3.95×) — **basically unchanged**. The decay is uniform across profile types.

### S10 — APS Get-Settings Availability (NaasAgentServicesApsProd)
```
Total=268,878,188 | Devices=818,000 | Tenants=24,092 | Successes=268,867,194 | SuccessPct=99.996
```
| ResultStatus | HTTP | Events | Δ vs v1 |
|---|---|---|---|
| SuccessSettingsNotFound | 200 | 255,143,797 | -0.5% |
| SuccessSettingsNotModified | 200 | 13,062,036 | -0.6% |
| SettingsSyncInProgress | 200 | 556,887 | flat |
| SuccessNewSettings | 200 | 82,664 | **-32%** ← fewer new policies pushed this week |
| SuccessInitialSettings | 200 | 20,690 | +1% |
| ClientFailureAuthenticaiton (sic) | 401 | 6,274 | +5% |
| Unknown | 499 | 4,407 | **+60%** |
| TenantOffboarded | 200 | 1,120 | +18% |
| FailureServiceError | 500 | 313 | **-31%** |

APS itself is **healthy** (99.996%). One subtle signal: `SuccessNewSettings` dropped 32% (policy-change volume is down) while the long-tail buckets (Unknown 499s, TenantOffboarded) crept up.

### S11 — APS Settings Ack Success (NaasAgentServicesApsProd)
```
ProcceedSuccessfully (sic) = 267,230,479
ClientFailureAuth          = 813
SuccessPct                 = 99.99970%   (v1: 99.99966%)
```
**Healthy.** 109 fewer auth-failures over the window (922 → 813).

### S12 — PKI Cert Enrollment Health (NaasCloudPkiProd)
| ResultStatus | OperationName | HTTP | Events | Notes |
|---|---|---|---|---|
| InProgress | CreateEnrollmentJob | 201 | 603,811 | enrollment-job creation (queued) |
| Completed | GetEnrollmentJobStatus | 200 | 102,171 | cert issued |
| InProgress | GetEnrollmentJobStatus | 202 | 1,900 | poll-still-running |
| Unknown | GetEnrollmentJobStatus | 404 | **3** | down from 4 in v1 |
| Failed | GetEnrollmentJobStatus | 500 | **2** | **NEW failure mode** — not present in v1 |

Total = 707,887 events (v1: 595,712, +18.8%). Total errors = 5 / 707,887 = **0.0007%** (rate unchanged from v1, still **healthy**). But the **2 HTTP 500 / `Failed` status is new** — v1 had 0. Low volume, but worth a one-line note ("PKI introduced a Failed/500 error class this week, n=2, watch next cycle").
DeviceId column for Android still returns degenerate counts (use TenantId — see v1 caveat).

---

## Ghost columns — re-checked today

`TunnelServerOperationEvents | project FlowStatusError | take 1` → **SEM0100 reproduced today (2026-06-09T09:12:49Z)**, error message: `'project' operator: Failed to resolve scalar expression named 'FlowStatusError'`. Same defect class as 4 days ago.

- **FlowStatusError** — ghost (confirmed today)
- **FlowErrorClassification** — ghost (same error class, not re-tested individually after FlowStatusError fail)
- **LatencyMs** — ghost (same)
- **Msg** — ghost (same)

`getschema | where ColumnName has_any('Result','Error','Reason','Code')` returns **zero matching real columns** — i.e., there is no surviving alternate error-detail column on `TunnelServerOperationEvents` we missed. Binary `Status` remains the only error signal. **No upstream platform fix in 4 days.** Promote to a recurring Data Quality row in the report.

---

## Data-quality issues still present

1. **Ghost columns** (above) — 4 days, no movement.
2. **Region casing duplicates** — `WestEurope`/`westeurope`, `CentralUs`/`centralus`, `NorthEurope`/`northeurope`, `SouthAfricaNorth`/`southafricanorth` all still split across two rows. Aggregating by `tolower(Region)` is recommended but not done in this drop (preserved as-emitted for v1 comparability).
3. **APS sibling-table schema divergence** — `HttpResponseStatusCode` present on `AgentGetSettingsOperationEvent`, absent on `AgentSettingsAckOperationEvent`. Same as v1.
4. **PKI `DeviceId` placeholder for Android** — same as v1, use TenantId.
5. **Upstream string typos preserved as-emitted** — `ClientFailureAuthenticaiton`, `ProcceedSuccessfully`. Leave intact in report; do not silently correct (Doggett's upstream team owns).

---

## New anomalies / new top entrants this cycle

- **Two-step ramp confirmed.** v1 looked like a plateau at 0.36%; v3 shows a second jump to 0.42–0.45%. Anomaly is escalating, not self-resolving.
- **Non-1P traffic fails MORE than headline rate** (S6b) — falsifies v1 hypothesis #1. The regression is platform-wide, not dogfood-tenant-localized. Promote.
- **Tenant `9cf9036f-…` new top-15 entrant** (105 fails/device, 45 devices) — Mulder triage.
- **Tenant `041ae2c2-…` doubled** failure volume (4,366 → 8,744). Single biggest mover (by ratio) among existing top tenants.
- **ClientVersion `1.0.9003.0401`** is now the highest-failure-rate high-volume version (0.626%, +131% vs v1) and the cohort has grown 55%. Strongest single-version regression signal in the run.
- **Region germanywestcentral** failure rate +67% (0.322 → 0.539). The biggest regional mover among top-volume regions.
- **PKI `Failed`/HTTP 500** new error class (n=2). Trivial volume; flag for next-cycle watch.
- **APS `Unknown`/HTTP 499** events up 60% (2,747 → 4,407). Still tiny vs the 268M denominator but trending wrong.
- **`7e389af4-…` 2-device outlier from v1 self-resolved** — dropped out of top-15. Useful counterexample (some signals do clear).

---

## Was the ramp anchor intact? — answer for Reyes

**The ramp anchor is INTACT and STRENGTHENED.** v1 said "0.074%→0.36% sustained over 5/29→6/02, 12× failure volume, 2.6× traffic — anomaly real." Today's data extends that arc with three additional days, each one worse than the previous plateau:
- 6/05 = 0.354% (matches plateau)
- 6/06 = 0.416% (+17% over plateau)
- 6/07 = 0.431% (+20%)
- 6/08 = 0.447% (+24%, **highest single day in 11 days of observation**)

This is NOT regression-to-the-mean and NOT recovery. The week-on-week traffic comparison is even cleaner because total traffic is essentially flat (130M → 132M, +1.4%) while failures jumped 35%. **The failure-rate increase is essentially pure quality degradation, with traffic held constant.** Promote Top-Insight severity in v3.

---

## Cross-domain candidates (refreshed)

1. ~~Microsoft 1P rollout hypothesis~~ — **FALSIFIED today**. Non-1P traffic fails harder than 1P. Remove from v3 report.
2. **`.0401`/`.04xx` ring/channel as a failure source** — v1 weak signal, v3 strong: `1.0.9003.0401` cohort grew 55% AND fail-rate +131%. Doggett: identify what `.04xx` actually is (early ring? specific tenant set? all 2 tenants concentrated suggests an internal-test ring). If `.04xx` accounts for a measurable share of the 35% global failure jump, it's the new anchor candidate.
3. **EU geographic concentration** — germanywestcentral +67%, francecentral +57%, NorthEurope +61%, SwedenCentral +114%. UK South still the biggest absolute (118K fails). Hypothesis: an EU-region path component degraded between 6/02 and 6/08. SCUS-cluster Talon/ZTNA cross-check still warranted (not in this scope-locked run).
4. **PROFILE_UNDEFINED device count up 41%** (245 → 345) while event count only up 10% — **more devices** hitting the config-bootstrap race, not just more events per device. Race-condition theory from v1 is consistent with this shape.

---

## Run accounting

| Bucket | Queries attempted | Passed | Recovered | Final failures |
|---|---|---|---|---|
| Tunnel (NaasProd) | 7 (incl. ghost re-check + S6b non-1P + getschema probe) | 6 | 0 | 1 (ghost cols, expected — re-confirmation of v1 finding) |
| APS (NaasAgentServicesApsProd) | 3 | 3 | 0 | 0 |
| PKI (NaasCloudPkiProd) | 1 | 1 | 0 | 0 |
| **Totals** | **11** | **10** | **0** | **1 (intentional ghost re-check)** |

All scope-locked metrics answered with real data. The one "failure" is the deliberate re-check of v1 ghost-column finding — and it reproduced exactly, which IS the data point.

---

## ✅ GO for Reyes

Cluster healthy, auth clean, 10/10 substantive queries succeeded, 1 deliberate ghost re-check reproduced, all v1 metrics refreshed and comparable. Ramp anchor strengthened — there's a real Top-1 Insight in this drop. No fabricated cells; every number is what the cluster returned in the run window above.
