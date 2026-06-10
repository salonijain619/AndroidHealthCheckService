# 📋 GSA Android Daily Livesite Report — Fri Jun 05, 2026

> **Scope (v1):** Server-observed slice only. This cycle is built from NAAS-server-side telemetry (`idsharedwus` — `NaasProd`, `NaasAgentServicesApsProd`, `NaasCloudPkiProd`) over a 7-day window ending **2026-06-05T13:26 UTC**. Defender-client-side telemetry (`mdatpandroidcluster / MDATPAndroidDB`) is **intentionally out of scope** for this cycle per the active scope lock. Sections that depend on client-side signal (client-version regression detail, NaaS call-site failure attribution, crash/ANR, MAM/compliance, tray-icon-equivalent cascade) are explicitly marked `TBD — Defender-client-side scope locked, pending unlock`.

## 📟 On-Call Today
🔴 **Primary**    TBD
🟡 **Backup**     TBD

*Rotation not yet configured for Android squad — assigning owners is an open Mulder/Saloni item for v2.*

---

## Executive Summary

🟡 **P2 — Tunnel server-side failure-rate climbing ~5× over the window.** Daily Android tunnel failure % rose from **0.074% (5/29)** to a sustained **~0.36% (6/02–6/04)**; absolute failure volume jumped **12×** (6,315 → 79,753/day) while traffic only grew ~2.6×. Below the 1% incident threshold but trending wrong — anchor signal of the week.

🟡 **P2 — Private Access + `PROFILE_UNDEFINED` profiles concentrate failure.** Private Access fails at **0.688%** (≈4× M365's 0.174%), carrying 33% of all failures from just 12% of events. `PROFILE_UNDEFINED` is **100% failure** (4,003 events / 245 devices) — discrete config-bootstrap edge case.

✅ **Fleet status: healthy at headline.** 130.05M tunnel events / **99.711% server-side success**, **27,489 active Android devices**, **1,241 active tenants** across 7 days. APS and PKI both green.

⚠️ **Data-quality caveat (read before acting on rates):** `FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg` on `TunnelServerOperationEvents` are **ghost columns** — they appear in `getschema` but Kusto rejects them at query time. Server-side **latency p50/p95/p99 is unavailable** this cycle; richer error categorization is unavailable. See Data Quality Notes.

📌 **Tenant correction (supersedes prior "8 tenants" reading):** The historical 8-distinct-tenants number from dashboard panel `8a1fa78a-…` was an artifact of an outdated `ClientVersion in (...)` cohort filter. Real fleet is **1,241 tenants** (155× larger). Treat as the new baseline.

---

## Key Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Active Android Devices (7d distinct, server-observed) | **27,489** | ⚠️ Weekday floor ~22–23K; weekend dip to ~19–20K. |
| Active Android Tenants (7d distinct) | **1,241** | 📌 Corrected baseline (prior "8" was a stale cohort artifact). |
| Fleet Tunnel Events (7d) | **130,050,841** total — 129,675,127 success / 375,714 failure | ⬆️ Weekday volume ~22M/day; +~2.6× weekend→weekday step. |
| Tunnel Health (server-side success) | **99.711%** overall | 🟡 Daily fail% climbed 0.074% → ~0.36% (5× ramp; see Insight #1). |
| Tunnel Latency p50/p95/p99 | TBD — `LatencyMs` is a ghost column on `TunnelServerOperationEvents`; unavailable this cycle. | TBD |
| APS Get-Settings Availability (7d) | **99.997%** (270,307,940 events / 270,298,775 success; 825,511 devices; 24,216 tenants) | ✅ Healthy. |
| APS Settings-Ack Success (7d) | **99.99966%** (268,589,274 / 268,590,196; 922 auth fails) | ✅ Healthy. |
| PKI Cert Enrollment Health (7d) | **✅ 4 errors / 595,712 events = 0.0007% error rate** (1,326 tenants). | ✅ Healthy. |
| Android Client Version Distribution Health | Top-3 versions (`1.0.8921.0101`, `1.0.9002.0102`, `1.0.8913.0101`) all 0.22–0.27% fail — **uniform & healthy**. Long-tail pre-`8900` builds at 0.87–2.6% (5–10× modern baseline, stale-binary decay). No regression on current builds. | ➡️ Stable on current versions. |
| Business Growth (7d) | Weekday floor: 22K–23K devices / ~1.1K tenants / ~22M events per day. Weekend↔weekday step ~ +18% devices, +7% tenants, +~2× events (Sun→Mon). | ➡️ Flat WoW on active devices; growth signal is volume, not seat count. |
| Client-side cascade (client version × auth × policy fetch × notification) | TBD — Defender-client-side scope locked, pending unlock. | TBD |

**Data Completeness Notes:**
- All values above are **server-observed** from NaasProd / APS / PKI databases on `idsharedwus`. Run completed 2026-06-05T13:30Z; 20 queries attempted, 17 passed, 5 recovered (column-discovery / casing), 0 final failures.
- The **APS device count (825K) is much larger than the Tunnel device count (27.5K)** because APS counts every device that pings for settings — many consumer/unmanaged installs never reach the tunnel stage. Both numbers are correct for their respective surfaces; do not equate them.
- 6/05 is a **partial day** (cut at 13:26Z) — daily trend rows for 6/05 should not be compared directly with full days.

---

## 🔍 Top 5 Insights

| # | Severity | Insight Title | Blast Radius | Action / Owner |
|---|----------|---------------|--------------|----------------|
| 1 | 🟡 **P2** | **Android tunnel failure-rate ~5× ramp over 7d** (0.074% → 0.36% sustained, 12× absolute volume increase, traffic only 2.6×). Trend is genuine quality degradation, not a traffic artifact. | 79,753 failures/day on 6/04 across ~23K active devices / ~1.1K tenants. Microsoft 1P dogfood tenant alone contributes **37%** of failures (140,697 / 11,682 devices). | **Doggett:** bisect the ramp by `ServiceType` × `Region` × `ClientVersion` × `TenantId` (especially with/without 1P) to localize. **Scully:** re-run daily fail-rate trend excluding the 1P tenant — if curve flattens, regression is dogfood-localized; if not, broader platform. **Mulder:** escalate to P1 if sustained fail% crosses 1%. |
| 2 | 🟡 **P2** | **Private Access profile fails ~4× the M365 baseline** (0.688% vs 0.174%); 33% of all failures from 12% of events. | 105,778 failures / 8,990 devices on PRIVATE_ACCESS over 7d. Geographic co-incidence: UK South (0.465%) + West Europe (0.441%) are 2–3× WUS baseline (0.172%), and EU dominates Private Access traffic. | **Doggett:** confirm Private Access path component is responsible (Talon? policy distribution?) — requires a SCUS hop (`naas-idsharedscus`) to query `NaaSVPNZtnaConnectionLogsEvent` / `TalonOperationEvent`; not run this cycle. **Mulder:** authorize SCUS scope for next cycle. |
| 3 | 🟡 **P2** | **`PROFILE_UNDEFINED` ServiceType = 100% failure** (every single event fails). Pairs 1:1 with the empty-`TenantId` bucket in the failing-tenants list. | 4,003 events / 245 devices / 7d. Low volume but discrete bug — almost certainly a config-bootstrap race (device connects before profile assignment lands). | **Doggett:** join Tunnel failures (empty TenantId) to APS GetSettings on `DeviceId` within ±5min to confirm the race and measure time-from-first-APS-call to first-non-empty-profile per device. **Scully:** standing query for new occurrences. |
| 4 | ⚠️ **Info** | **Two ghost-column families on `TunnelServerOperationEvents`** (`FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg`) — advertised in schema, unqueryable at runtime. Server-side latency p50/p95/p99 and richer error categorization are **silently unavailable** today; any dashboard panel that depends on them is silently degraded. | Squad-wide observability gap; affects every future report's "Tunnel Latency" + "Failure Reason" rows until resolved. | **Skinner / Mulder:** file with the NaaS data-platform team (schema-vs-runtime divergence). **Reyes:** continue surfacing in Data Quality Notes until closed. |
| 5 | ⚠️ **Info** | **Region casing duplicates** in `TunnelServerOperationEvents.Region` — `WestEurope` vs `westeurope`, `NorthEurope` vs `northeurope`, `CentralUs` vs `centralus`, `SouthAfricaNorth` vs `southafricanorth`. Two ingestion paths are emitting the same physical region with different casing, fragmenting per-region rollups. | All multi-region rollups understate per-region volume unless callers `tolower()` or normalize. | **Doggett:** identify the two ingestion paths and decide on canonical casing or sink-side normalization. |

**Deferred (next-cycle Top-5 candidates, currently out of scope):**
- 🔴/🟠 Client-version-regression detection (Android analog of the Windows v2.28.96 playbook) — needs client-side `TelemetryVPNAndWebProtection` + ECS flag-evaluation telemetry.
- 🔴/🟠 NaaS call-site failure attribution (config vs IO/run phase; silent vs interactive auth) — `MDATPAndroidDB` queries CL-N1…CL-N12.

---

## 🔥 Cross-Domain Correlation Analysis

**Primary Correlation Chain (v1, server-side only):** Daily tunnel failure-rate 5× ramp ⟷ weekday traffic step (Sun→Mon) ⟷ Microsoft 1P dogfood tenant concentration (37% of all failures).

**Timeline (server-observed, daily granularity — finer-grained correlation requires client-side data):**

| Day (UTC) | Tunnel events | Failures | Fail% | Active devices | Active tenants |
|---|---|---|---|---|---|
| 2026-05-29 | 8,503,764 | 6,315 | **0.074%** | 20,791 | 1,014 |
| 2026-05-30 | 11,473,492 | 19,564 | 0.171% | 19,806 | 1,004 |
| 2026-05-31 (Sun) | 10,852,481 | 21,798 | 0.201% | 19,075 | 1,002 |
| 2026-06-01 (Mon) | 20,275,758 | 46,194 | 0.228% | 22,569 | 1,074 |
| 2026-06-02 | 21,748,579 | 78,347 | **0.360%** | 22,978 | 1,102 |
| 2026-06-03 | 23,247,057 | 85,299 | **0.367%** | 23,554 | 1,103 |
| 2026-06-04 | 22,245,033 | 79,753 | **0.359%** | 23,213 | 1,097 |
| 2026-06-05 (partial) | 11,712,888 | 38,525 | 0.329% | 22,310 | 1,056 |

**Evidence:**
- Failure-rate climbed **~5×** (0.074% → 0.36%), absolute failure volume **~12×** (6,315 → 79,753/day), while traffic only grew **~2.6×** (8.5M → 22M/day). **Traffic alone does not explain it** — there is a genuine quality deterioration superimposed on the weekday step.
- Failure concentration is uneven: **Microsoft Corp 1P (`72f988bf-…`) = 37%** of all failures (140,697 / 11,682 devices) — expected dogfood pattern but the dominant contributor. Two outliers worth eyes: `0e17f90f-…` (33,309 failures / 277 devices = 120 fails/device); `7e389af4-…` (3,787 failures / **2 devices** — almost certainly a broken test device, not a tenant-wide issue).
- Geographic concentration aligns with Insight #2: UK South (0.465%), West Europe (0.441%), SouthAfricaNorth (0.758%) all run 2–4× the WUS baseline (0.172%).

**Validation Steps (queued for next cycle):**
1. ⏳ Re-run S6 daily fail-rate trend with `TenantId != '72f988bf-…'` — if the curve flattens, ramp is 1P-localized.
2. ⏳ Per-day Region trend (not run this cycle) — to confirm whether the ramp is region-localized or fleet-wide.
3. ⏳ SCUS hop to `NaaSVPNZtnaConnectionLogsEvent` / `TalonOperationEvent` for Private Access path attribution (Insight #2).
4. ⏳ Client-side cascade analysis (auth → policy fetch → notification) — **deferred until Defender-client-side scope is unlocked**. Without `MDATPAndroidDB.TelemetryVPNAndWebProtection` / `TelemetryAuth` / `TelemetryHeartbeat`, we cannot confirm whether the server-side ramp has a client-side antecedent (e.g., a new client build, an ECS flag flip) or is purely an infrastructure regression.

---

## 📊 Data Quality Notes

- **Telemetry sources (this cycle):** Kusto `idsharedwus.kusto.windows.net` — databases `NaasProd` (TunnelServerOperationEvents), `NaasAgentServicesApsProd` (AgentGetSettingsOperationEvent, AgentSettingsAckOperationEvent), `NaasCloudPkiProd` (EnrollCertificateOperationSummary). Auth via `azure-mcp-kusto` default credential (Azure CLI) — clean, no auth walls.
- **Out of scope (v1 lock):**
  - `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (all Defender client-side; 22 ICM baseline queries CL-A1…CL-N12 deferred).
  - `naas-idsharedscus` (full-37-table NaasProd) — all v1 targets resolved on WUS; SCUS hop not required this cycle.
- **Ghost columns on `TunnelServerOperationEvents`:** `FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg` all appear in `getschema` output but return `SEM0100: Failed to resolve scalar expression` when referenced. Net effect this cycle:
  - **Tunnel latency p50/p95/p99 is unavailable** (the Key Metrics row is TBD).
  - **Richer error categorization is unavailable** — only the binary `Status ∈ {Success, Failure}` is usable. The dashboard panel that depended on these columns is **silently degraded**.
  - This is a real defect to surface upstream (Skinner / Mulder ask in Insight #4).
- **Schema divergence between sibling APS tables:** `AgentSettingsAckOperationEvent` lacks `HttpResponseStatusCode` (present on `AgentGetSettingsOperationEvent`). Worked around using `ResultStatus` only.
- **PKI `DeviceId` placeholder:** PKI returned `Devices=1` for Android enrollments — strongly suggests PKI emits empty/placeholder `DeviceId` for Android (Windows samples have real values). **Do not trust per-device PKI counts**; tenant counts (1,326) are valid.
- **Upstream typos preserved as emitted:** `ClientFailureAuthenticaiton` (APS GetSettings), `ProcceedSuccessfully` + `ClientFailureAuth` (APS Ack). Surfaced for traceability, not corrected.
- **Region casing duplicates:** see Insight #5.
- **Open questions for v2:**
  1. Should Play Store vs sideload/MAM channel adoption be segmented? (Cannot answer with server-side data alone — requires client-side install-source telemetry.)
  2. Android OS-version split health tracking — baseline expectations by API level? (Same — client-side.)
  3. Device model/OEM error variance — reportable signal or noise? (Same — client-side.)
  4. Is the 5× tunnel-failure ramp driven by a client build rollout? (Cannot answer without client-side `ClientVersion` × time pivot.)

---

## Contributors

- **Mulder** — scope/lead, NAAS-only v1 lock.
- **Scully** — data execution (20 queries; 17 passed, 5 recovered, 0 final failures; see `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md`).
- **Doggett** — telemetry architecture (Android telemetry routing model; NaaS-server vs Defender-client boundary).
- **Reyes** — report assembly.

*(Skinner did not contribute this cycle — no live incidents to triage; rotation/on-call still TBD.)*

**Timestamp:** 2026-06-05T13:30Z (Friday, June 5, 2026 — server-observed window `2026-05-29T13:26Z .. 2026-06-05T13:26Z`)
**Report Assembled By:** Reyes (Report Writer)
