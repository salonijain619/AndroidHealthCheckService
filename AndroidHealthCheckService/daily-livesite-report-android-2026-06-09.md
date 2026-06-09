# 📋 GSA Android Daily Livesite Report — Tue Jun 09, 2026

> **Scope (v3):** Server-observed slice only — NAAS server-side telemetry (`idsharedwus` → `NaasProd`, `NaasAgentServicesApsProd`, `NaasCloudPkiProd`) over a fresh 7-day window `2026-06-02T00:00Z → 2026-06-09T00:00Z`. Defender-client-side telemetry (`mdatpandroidcluster / MDATPAndroidDB`) remains intentionally out of scope per the active scope lock. Sections that depend on client-side signal (per-build cascade attribution, crash/ANR, MAM/compliance, install-source split) are explicitly marked `TBD — Defender-client-side scope locked`.

> **v3 note (2026-06-09):** This cycle re-pulled NAAS telemetry in full (10/10 substantive queries succeeded; 1 deliberate ghost-column re-check reproduced verbatim). ICM data is **live as of 2026-06-08** — Scully confirmed zero state movement in the prior 24h, so v3 reuses the 06-08 envelope without a re-pull. Major v3 changes vs v2: (1) ramp anchor **strengthened, not stabilized** — second step up; (2) v1/v2 Microsoft-1P cross-domain candidate **falsified** and removed; (3) new `1.0.9003.0401` ring promoted to top single-version suspect; (4) detector silence now 3 consecutive pulls with zero auto-ICMs against a 6× ramp.

## 📟 On-Call Today
🔴 **Primary**    dileepkusuma
🟡 **Backup**     samirnen

*Source: `get_on_call_schedule_by_team_id` on team 106961, live 2026-06-08; unchanged across 3 consecutive pulls (06-06, 06-08, 06-09 — no rotation movement in 3 days).*

---

## 🚨 Active ICM Incidents

> **ICM Snapshot (live as of 2026-06-08, no movement in 24h)** — Scully's 06-08 envelope was byte-identical to the 06-06 envelope (5,335 bytes) and the lone active ICM's `lastModifiedDate` is frozen at `2026-06-06T06:01:04.97Z`. Coordinator confirmed no re-pull required for 06-09.

🔴 **Active+Mitigating: 1**  &nbsp;|&nbsp;  **Severity:** Sev1: 0 · Sev2: 0 · **Sev3: 1** · Sev4: 0  &nbsp;|&nbsp;  **Customer-reported (`type=CustomerReported`):** 1 · **System-detected:** 0  &nbsp;|&nbsp;  🧪 **TestICM-flagged:** 1  &nbsp;|&nbsp;  **Effective real-incident count: 0**

### 👤 Customer-Created Active

| ICM ID | Sev | Age | Title | Status |
|---|---|---|---|---|
| [#810723164](https://portal.microsofticm.com/imp/v3/incidents/details/810723164/home) | 🟡 Sev3 🧪 TestICM | **5d+** (created 2026-06-03; last-modified 2026-06-06T06:01Z — untouched ~2.5 days) | `[Copilto testing] GSA Android client not working` | ACTIVE (**unacknowledged**) |

> ⚠️ **Bucketing note (v2.1 still pending):** Collector still buckets via HP's `source startswith "customer"` convention; ICMProd's payload actually uses the `type` field (returns `CustomerReported` / `LiveSite` / `Deployment`) and `source` is `None` for this queue. As shipped, this ICM lands in `system_created_active` in the raw envelope. **Workaround: classify on `type == "CustomerReported"` when reading the JSON.** The table above is bucketed correctly on `type`. Bug filed 06-06, still present in 06-08 collector — Doggett owns the one-line predicate swap for v2.1.

> 🏷️ **Owning team (verbatim):** `"GSA  Client - XPlat"` (double-space typo between "GSA" and "Client") — `owningTeamId=106961`. Same drift as 06-06 and 06-08; still not corrected upstream after 5 days. Reinforces the open queue-identity question (is 106961 an XPlat parent rather than an Android-only sub-queue?).

### 🤖 System-Created Active

| ICM ID | Sev | Age | Title | Status |
|---|---|---|---|---|
| — | — | — | _No system-detected (LiveSite / Deployment / detector-emitted) ICMs on team 106961_ | — |

### 🟡 Mitigated Highlights (last 7d)

| ICM ID | Sev | Age | Title | Status |
|---|---|---|---|---|
| — | — | — | _Zero mitigated ICMs returned for `owningTeamId=106961`_ | — |

> Empty result is a **real signal**, not a windowing regression — D-138 discipline preserved (no `dateRange`, `sortBy=LastModifiedDate Desc, top=50`). Either nothing has ever been mitigated under this team or mitigated work files under the `GSA Client - XPlat` parent. Same observation 3 pulls running.

**Patterns:**

- 🔴 **Detector silence is now a 3-pull confirmed pattern** (06-06, 06-08, 06-09). NAAS server-side fail-rate has ramped from a 0.074% baseline to **0.447% on 6/08** — a **6× ramp** with failure volume +35% week-on-week — and **zero auto-detector ICMs** have fired against team 106961. This is a control-plane gap, not a data-plane gap. Escalation already on books (Mulder/Skinner pending); v3 is the third corroborating data point.
- ➡️ **Real-incident count stays 0** after TestICM filter. The lone ACTIVE item (#810723164) is a 5+ day unacknowledged test ICM with `keywords: "[IcM Copilot] Test incident / no validated production issue"`. Same incident, same `lastModifiedDate`, third pull in a row.
- ⚠️ **Aging-without-ack hygiene gap persists.** TestICM has sat unacknowledged on `dileepkusuma`'s queue for 5+ days. Recommend close/non-actionable so it stops skewing active-count optics.
- ❓ **Queue-identity question still open** — `owningTeamName="GSA  Client - XPlat"` (typo intact). For Saloni: is there an Android-only child queue we should re-target? If so, v3's ICM section may be scoped to a parent.
- 🔁 **Collector bucketing bug ships for the 3rd consecutive pull.** Workaround is documented and stable, but downstream consumers still need to classify by `type` not `source` until v2.1.

---

## Executive Summary

🟠 **P2-trending-P1 — Tunnel server-side ramp is on its SECOND step up, not stabilizing.** ⬆️ Daily Android tunnel fail-rate progression: 6/05 = **0.354%** → 6/06 = **0.416%** → 6/07 = **0.431%** → **6/08 = 0.447%** (highest single day in 11 days of observation). 7-day fail-rate climbed **0.289% → 0.385% (+33%)**; failures **+35.1%** (375,714 → 507,643) while traffic only moved **+1.4%** — essentially pure quality degradation with traffic held constant. A single +0.55pp day would cross the 1% incident threshold. **Promote anchor severity.**

🔄 **Hypothesis falsified — regression is NOT a Microsoft 1P dogfood artifact.** With Microsoft (`72f988bf-…`) stripped from the daily series, non-1P fail-rate runs **0.49–0.60% range every day — HIGHER than the global headline rate** (which 1P traffic is *dampening*). v1/v2's "dogfood rollout" cross-domain candidate is **dropped**. The degradation is platform-wide.

🟠 **New top single-version anchor: `1.0.9003.0401` ring (`.04xx` flavor).** ⬆️ Devices +55% (646 → 1,003), fail-rate +131% (0.271% → **0.626%**) — the strongest single-version regression signal in the run. Concentrated in **2 tenants**. The mainstream `.01xx` builds (`8921.0101`, `9002.0102`) also moved +21–31% but stay in the 0.33–0.35 band — `.04xx` is a fairly clearly worse ring. **Doggett: identify what `.04xx` actually is** (early ring? internal-test cohort? specific tenant set?).

🌍 **EU regions are intensifying.** ⬆️ `germanywestcentral` +67% (0.322 → 0.539), `NorthEurope` +61%, `SwedenCentral` +114%, `WestEurope` (capital) +53% (0.449 → 0.685). `uksouth` still carries the biggest absolute load (118,657 fails / 7d). Geographic shape strengthening into a cluster, not a single hotspot.

✅ **APS + PKI still HEALTHY at headline.** APS Get-Settings 99.996%, APS Settings-Ack 99.99970%, PKI error rate 0.0007% (5/707,887). **But:** PKI introduced a **new failure class** this week (2× HTTP 500 `Failed/GetEnrollmentJobStatus`, n=2, low-volume watch item), and the `PROFILE_UNDEFINED` cohort grew **+41% in devices** (245 → 345) while still failing at 100% — more devices hitting the config-bootstrap race, not just more events per device.

🔁 **Data-quality recurring row — ghost columns + region casing duplicates still unfixed at day 4.** `FlowStatusError` / `FlowErrorClassification` / `LatencyMs` / `Msg` reproduced SEM0100 today; `WestEurope`/`westeurope`, `CentralUs`/`centralus`, etc. still split across two rows. Recommend filing schema and normalization tickets — these are silently degrading every report's latency and per-region rollup.

---

## Key Metrics

> **NAAS telemetry window (v3, fresh):** server-observed `2026-06-02T00:00Z → 2026-06-09T00:00Z`. Run completed 2026-06-09T09:12Z; 11 queries attempted, 10 passed, 1 intentional ghost re-check reproduced. **ICM data:** live as of 2026-06-08 (no movement in 24h).

| Metric | Value | Trend (vs v1 baseline 5/29→6/05) |
|--------|-------|----------------------------------|
| Active Android Devices (7d distinct, server-observed) | **27,744** | ➡️ +0.9% (essentially flat) |
| Active Android Tenants (7d distinct) | **1,254** | ➡️ +1.0% (flat) |
| Fleet Tunnel Events (7d) | **131,874,839** total — 131,367,196 success / **507,643 failure** | ⬆️ Events +1.4%, **failures +35.1%** — pure quality degradation. |
| Tunnel Health (server-side success) | **99.615%** overall (7d fail-rate **0.385%**) | ⬆️ Fail-rate +33% (0.289% → 0.385%); daily ramp 0.354% (6/05) → **0.447% (6/08)**. See Insight #1. |
| Tunnel Latency p50/p95/p99 | TBD — `LatencyMs` is still a ghost column on `TunnelServerOperationEvents` (SEM0100 reproduced 2026-06-09T09:12:49Z). | 🔴 Unfixed 4 days |
| APS Get-Settings Availability (7d) | **99.996%** (268,878,188 events / 268,867,194 success; 818K devices; 24,092 tenants) | ✅ Healthy (~flat). |
| APS Settings-Ack Success (7d) | **99.99970%** (267,230,479 / 267,231,292; 813 auth fails) | ✅ Healthy (~flat, -109 auth fails). |
| PKI Cert Enrollment Health (7d) | ✅ **5 errors / 707,887 events = 0.0007% error rate** (1,326+ tenants). **NEW failure class: 2× HTTP 500 `Failed/GetEnrollmentJobStatus`** (n=2, not present in v1). | ➡️ Rate flat; new low-volume failure mode to watch. |
| Android Client Version Distribution Health | Mainstream `.01xx` builds (`8921.0101`, `9002.0102`, `8913.0101`) in 0.33–0.48% band (+21–117%). **`.04xx` ring is now the worst high-volume cohort: `1.0.9003.0401` at 0.626% (+131%), devices +55%.** Long-tail pre-`8900` builds 0.87–2.67% (unchanged decay shape). | ⬆️ Regression on `.04xx` cohort; mainstream ramp is real but bounded. |
| Business Growth (7d) | Weekday floor: ~23K devices / ~1.1K tenants / ~21M events per day. Weekend dip (6/06–6/07) ~19–20K devices / ~11M events. | ➡️ Flat WoW on active devices; tenant + device counts essentially unchanged. |
| Client-side cascade (client version × auth × policy fetch × notification) | TBD — Defender-client-side scope locked, pending unlock. | TBD |

**Data Completeness Notes:**
- All values above are **server-observed** from NaasProd / APS / PKI databases on `idsharedwus`. Run completed 2026-06-09T09:12Z.
- The **APS device count (818K) is much larger than the Tunnel device count (27.7K)** — same shape as v1; APS counts every device that pings for settings while Tunnel only counts devices that reach the tunnel stage. Both correct for their surfaces; do not equate.
- The 2026-06-09 window edge (closed at `00:00:00Z`) catches a 187-event sliver tagged exactly at the boundary — negligible noise, called out for traceability.

---

## 🔍 Top 5 Insights

| # | Severity | Insight Title | Blast Radius | Action / Owner |
|---|----------|---------------|--------------|----------------|
| 1 | 🟠 **P2-trending-P1** | ⬆️ **Tunnel fail-rate is on a SECOND step up, not stabilizing.** Daily ramp: 6/05 = 0.354% → 6/06 = 0.416% → 6/07 = 0.431% → **6/08 = 0.447% (highest in 11d)**. 7d failures +35% on +1.4% traffic = **pure quality degradation**. Three additional bad days since v2's plateau read — anomaly is escalating, not self-resolving. | 507,643 failures / 7d across 27,744 active devices / 1,254 tenants. 6/08 alone: 95,112 failures, more than 15× the 5/29 baseline (6,315). | **Mulder:** escalate severity; promote to P1 if any single day crosses 1% (0.447% + 0.55pp away). **Doggett:** bisect ramp by `ClientVersion × Region × ServiceType × TenantId` with `.04xx` and EU regions as priority axes. **Scully:** standing daily fail-rate watch + per-region trend (deferred from v1). |
| 2 | 🟠 **P2** | ⬆️ **`1.0.9003.0401` (`.04xx` ring) is the new top single-version regression.** Cohort grew **+55% in devices** (646 → 1,003) AND fail-rate **+131%** (0.271% → **0.626%**) — the strongest single-version signal in the run. `1.0.8921.0401` also up +24%. Concentrated in 2 tenants total — strong "ring/channel" fingerprint, not a broad rollout. Mainstream `.01xx` builds also moved up (+21–31%) but stay in 0.33–0.35 band, so `.04xx` is a measurably worse ring. | 1,003 devices on the worst single version (`9003.0401`) failing at 0.626%. ~28,814 failures attributable to `9003.0401` alone (7d). | **Doggett:** identify what `.04xx` actually is — early ring? internal test channel? specific tenant set? Map suffix → ring/cohort metadata. If `.04xx` accounts for a measurable share of the global +35% jump, it becomes the next anchor candidate. **Scully:** per-day fail-rate trend split by `.04xx` vs `.01xx` next cycle. |
| 3 | 🟠 **P2** | ⬆️ **Every ServiceType degraded by the same fraction (~30–40%) — strong platform-component-degradation fingerprint.** M365: 0.174 → 0.227 (+30%). INTERNET: 0.548 → 0.766 (+40%). PRIVATE_ACCESS: 0.688 → **0.929 (+35%)**. The Private-Access:M365 ratio is unchanged at 4.09× (was 3.95×) — this is **NOT** a profile-specific bug; it's the whole tunnel pipeline degrading uniformly. | All four ServiceTypes; ~507K failures distributed across M365 (44%), PRIVATE_ACCESS (28%), INTERNET (27%), PROFILE_UNDEFINED (<1% but 100% fail). | **Doggett:** target shared-platform-component hypotheses (tunnel ingress, common auth, Talon / ZTNA shared path) over profile-specific code paths. SCUS hop to `NaaSVPNZtnaConnectionLogsEvent` / `TalonOperationEvent` warranted next cycle. **Mulder:** authorize SCUS scope. |
| 4 | 🟠 **P2** | 🌍 **EU regions intensifying — multi-region acceleration, not single hotspot.** ⬆️ `germanywestcentral` +67% (0.322 → 0.539), `NorthEurope` +61%, `SwedenCentral` +114%, `WestEurope` (capital) +53% (→ 0.685, worst in cohort), `francecentral` +57%. `uksouth` still the largest absolute (118,657 fails / 7d, 0.587%). Worst single rate: `SouthAfricaNorth` (capital) at 0.764%. | EU + UK South dominate absolute failure volume; 5+ regions accelerating in lockstep suggests a regional path component (likely cross-region shared infra) rather than per-region quirks. | **Doggett:** EU-path hypothesis — what shared component fronts these regions? Cross-check ClientVersion × Region (does `.04xx` concentrate in EU?). **Scully:** per-day Region trend (deferred from v1) — confirm whether EU degradation predates or follows the global ramp inflection. |
| 5 | 🟡 **P3 / watch** | ⬆️ **`PROFILE_UNDEFINED` device count up +41% (245 → 345) while events only +10%.** Still 100% failure (4,403 events / 345 devices). **More devices** hitting the config-bootstrap race, not just more events per device — config/onboarding bug suspect is widening. Low absolute volume but the device-count trend is the wrong shape. Pairs 1:1 with the empty-`TenantId` bucket. | 345 devices stuck in 100%-fail PROFILE_UNDEFINED state over 7d. Likely a config-bootstrap race (device connects before profile assignment lands) or a client onboarding bug. | **Doggett:** join Tunnel failures (empty TenantId) to APS GetSettings on `DeviceId` within ±5min to confirm race; measure first-non-empty-profile lag per device. Investigate as a **client config/onboarding bug** candidate given the device-count growth pattern. **Scully:** standing query — flag if devices crosses 500 next cycle. |

**Recurring / Info-level rows (carried from v1/v2, still open):**
- ⚠️ **Ghost columns on `TunnelServerOperationEvents`** (`FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg`) — **OPEN 4 DAYS, no upstream fix.** SEM0100 reproduced today at 09:12:49Z. Server-side latency p50/p95/p99 still unavailable. **Recommend filing a schema ticket with the NaaS data-platform team.** (Reyes will continue to surface in Data Quality Notes.)
- ⚠️ **Region casing duplicates** (`WestEurope`/`westeurope`, `CentralUs`/`centralus`, `NorthEurope`/`northeurope`, `SouthAfricaNorth`/`southafricanorth`) — **OPEN 4 DAYS, no normalization.** Fragmenting per-region rollups. **Recommend filing a normalization ticket** or sink-side `tolower(Region)`. Held as-emitted this cycle for cross-cycle comparability.

**Deferred (next-cycle Top-5 candidates, currently out of scope):**
- 🔴/🟠 Client-version-regression detection deep-dive (Android analog of Windows v2.28.96 playbook) — needs client-side `TelemetryVPNAndWebProtection` + ECS flag-evaluation telemetry.
- 🔴/🟠 NaaS call-site failure attribution (config vs IO/run phase; silent vs interactive auth) — `MDATPAndroidDB` queries CL-N1…CL-N12.

---

## 🔥 Cross-Domain Correlation Analysis

**Cross-domain candidates — UPDATED for v3:**

- ❌ ~~**Microsoft 1P dogfood rollout driving regression**~~ — **FALSIFIED today (Scully's S6b probe).** Stripping `72f988bf-…` from the daily series does NOT flatten the curve; non-1P fail-rate runs **0.49–0.60% every day, HIGHER than the global headline**. Microsoft's traffic is *dampening* the headline number. Removed from the cross-domain candidate list. Was v1/v2 candidate #1.
- ⬆️ **`.0401` / `.04xx` ring as primary failure source** — v1 weak signal, v3 strong. `1.0.9003.0401` cohort grew +55% AND fail-rate +131%; concentrated in 2 tenants. Replaces v1's `.0102` ring as the prime version-axis suspect. **Promote to anchor candidate.**
- ⬆️ **EU-region × client-version interaction** — multiple EU regions accelerating in lockstep (germanywestcentral, NorthEurope, SwedenCentral, WestEurope, francecentral). Hypothesis: an EU-region path component degraded between 6/02 and 6/08; possibly correlated with the `.04xx` cohort distribution. SCUS Talon/ZTNA cross-check still warranted (not in this scope-locked run).
- 🔴 **Detector silence vs ramp magnitude — control-plane gap, not data-plane gap.** 3 consecutive ICM pulls show zero auto-detector ICMs against a now-6× tunnel-fail-rate ramp from the v1 baseline. The data plane is screaming; the control plane is silent. This is structural, not transient. Escalation already on books (Mulder/Skinner pending).
- 🟡 **NEW: `PROFILE_UNDEFINED` device growth (+41%) + 100% fail = client config/onboarding bug suspect.** Device-count growing faster than event-count strongly suggests a widening cohort of misonboarded clients rather than a stable few outliers. Still small absolute (345 devices), but trending wrong.

**Primary Correlation Chain (v3, server-side only):**

```
Two-step tunnel fail-rate ramp (0.074% → 0.36% → 0.42–0.45%)
    ⟷  Uniform ServiceType degradation (+30 to +40% across M365 / INTERNET / PRIVATE_ACCESS)
    ⟷  `.04xx` ring single-version regression (+131% fail-rate, +55% devices, 2 tenants)
    ⟷  EU-region cluster acceleration (5+ regions +50–114%)
    ⟷  Detector silence (0 auto-ICMs, 3 pulls running)
```

**Timeline (server-observed, daily granularity — daily devices/tenants/events/failures across both windows):**

| Day (UTC) | Tunnel events | Failures | Fail% | Active devices | Active tenants | Notes |
|---|---|---|---|---|---|---|
| 2026-05-29 (v1 baseline) | 8,503,764 | 6,315 | **0.074%** | 20,791 | 1,014 | Pre-ramp baseline |
| 2026-06-02 | 21,748,579 | 78,347 | 0.360 | 22,978 | 1,102 | First plateau day |
| 2026-06-03 | 23,247,057 | 85,299 | 0.367 | 23,554 | 1,103 | Plateau |
| 2026-06-04 | 22,245,033 | 79,753 | 0.359 | 23,213 | 1,097 | Plateau |
| 2026-06-05 | 20,784,502 | 73,487 | **0.354** | 23,242 | 1,082 | End of plateau (full-day, supersedes v1 partial 0.329) |
| 2026-06-06 | 11,552,098 | 48,100 | **0.416** | 20,270 | 1,022 | ⬆️ **NEW** — step 2 begins (weekend) |
| 2026-06-07 | 11,043,141 | 47,544 | **0.431** | 19,465 | 1,014 | ⬆️ **NEW** |
| 2026-06-08 | 21,254,242 | **95,112** | **0.447** | 23,175 | 1,097 | ⬆️ **NEW** — worst single day in 11d of observation |
| 2026-06-09 (sliver) | 187 | 1 | 0.535 | 139 | 34 | Edge-of-window noise (1 stamp at `00:00:00Z`) |

**Evidence:**
- Failure-rate ramp is now **6×** from baseline (0.074% → 0.447%); failure volume on 6/08 alone is **15×** the 5/29 baseline.
- Week-on-week traffic is essentially flat (130M → 132M, +1.4%) while failures jumped +35% — **pure quality degradation**, not a traffic artifact.
- Non-1P daily fail-rate (S6b, NEW probe this cycle) runs higher than the global rate every day — falsifies the 1P-localization hypothesis.
- ServiceType degradation is uniform (~+30–40% across all four types) — points at a shared platform component, not a profile-specific code path.
- `.04xx` cohort: 1,003 devices on `9003.0401` failing at 0.626% across 2 tenants; concentration pattern matches an internal ring/channel.
- EU cluster: 5+ regions all accelerating +50–114% in the same window — regional path-component hypothesis is the cleanest explanation.

**Validation Steps (queued for next cycle):**
1. ⏳ Doggett: identify `.04xx` ring (channel? early ring? internal test cohort? specific tenant set?). Cross-tab against the 2 tenants holding the cohort.
2. ⏳ Scully: per-day Region trend (still deferred from v1) — confirm EU degradation onset vs global ramp inflection.
3. ⏳ SCUS hop to `NaaSVPNZtnaConnectionLogsEvent` / `TalonOperationEvent` for Private Access + EU path attribution. Mulder authorization required.
4. ⏳ Doggett: PROFILE_UNDEFINED join — Tunnel failures (empty TenantId) ↔ APS GetSettings on `DeviceId` within ±5min to confirm config-bootstrap race; measure first-non-empty-profile lag per device.
5. ⏳ Mulder/Skinner: detector-silence escalation — why is no auto-ICM firing on a 6× server-side ramp? (3 pulls of corroboration.)
6. ⏳ Client-side cascade — **deferred until Defender-client-side scope is unlocked.** Cannot confirm whether the ramp has a client-side antecedent (new build, ECS flag flip) without `MDATPAndroidDB`.

---

## 📊 Data Quality Notes

- **Telemetry sources (this cycle):** Kusto `idsharedwus.kusto.windows.net` — databases `NaasProd` (TunnelServerOperationEvents), `NaasAgentServicesApsProd` (AgentGetSettingsOperationEvent, AgentSettingsAckOperationEvent), `NaasCloudPkiProd` (EnrollCertificateOperationSummary). Auth via `azure-mcp-kusto` default credential (Azure CLI) — clean, no auth walls; yesterday's TCP-timeout block is cleared.
- **Out of scope (active scope lock):**
  - `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (all Defender client-side; 22 ICM baseline queries CL-A1…CL-N12 still deferred).
  - `naas-idsharedscus` (full 37-table NaasProd) — not consulted this cycle; needed for Private Access / EU path attribution next cycle.

### Recurring DQ Row (escalating visibility — open 4 days, no upstream fix)

| # | Issue | First Seen | Status | Recommended Action |
|---|-------|-----------|--------|---------------------|
| 1 | **Ghost columns on `TunnelServerOperationEvents`** — `FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg` advertised in `getschema` but return `SEM0100: Failed to resolve scalar expression` at query time. Server-side latency p50/p95/p99 silently unavailable. SEM0100 reproduced today at 2026-06-09T09:12:49Z. | 2026-06-05 (v1) | 🔴 **OPEN 4d, no upstream fix** | **File schema ticket with NaaS data-platform team.** Owner: Skinner/Mulder. Reyes continues surfacing each cycle until closed. |
| 2 | **Region casing duplicates** — `WestEurope`/`westeurope`, `CentralUs`/`centralus`, `NorthEurope`/`northeurope`, `SouthAfricaNorth`/`southafricanorth` all still split across two rows from two ingestion paths. Aggregating by `tolower(Region)` recommended but not done in raw drop (preserved as-emitted for cross-cycle comparability). | 2026-06-05 (v1) | 🔴 **OPEN 4d, no normalization** | **File normalization ticket** (canonical casing decision + sink-side `tolower` OR ingestion-path fix). Owner: Doggett to identify the two paths. |

### Other DQ items (carried forward, lower urgency)

- **APS sibling-table schema divergence** — `HttpResponseStatusCode` present on `AgentGetSettingsOperationEvent`, absent on `AgentSettingsAckOperationEvent`. Worked around using `ResultStatus` only. Same as v1.
- **PKI `DeviceId` placeholder for Android** — Android enrollments return `Devices=1` (placeholder). Use TenantId for valid per-tenant counts (1,326). Same as v1.
- **Upstream string typos preserved as emitted** — `ClientFailureAuthenticaiton` (APS GetSettings), `ProcceedSuccessfully` + `ClientFailureAuth` (APS Ack). Not silently corrected; Doggett's upstream team owns.
- **Owning-team typo** — ICM returns `owningTeamName="GSA  Client - XPlat"` (double-space) for `owningTeamId=106961`, still uncorrected upstream after 5 days. Cosmetic but reinforces queue-identity open question.

### ICM Integration (v3 cycle — 3rd live pull)

- **Source:** `agency mcp icm` (collector ported from HarryPotter) → `search_incidents` (Active+Mitigating, Mitigated×Desc), `get_on_call_schedule_by_team_id`. ICM data live as of **2026-06-08**, no movement in 24h (envelope byte-identical to 06-06).
- **Raw output:** `tools/icm/runs/icm-run-2026-06-08.json` (5,335 bytes).
- **Collector bug v2.1 STILL PRESENT** (3 pulls running): bucketing predicate uses HP's `source startswith "customer"` heuristic but ICMProd's payload uses the `type` field (`CustomerReported` / `LiveSite` / `Deployment`) with `source: None`. **Workaround for downstream consumers: classify by `type == "CustomerReported"` when reading JSON.** Bucketing fix owed in v2.1 (one-line predicate swap, Doggett).

### Open Questions

1. Should Play Store vs sideload/MAM channel adoption be segmented? (Cannot answer without client-side install-source telemetry.)
2. Android OS-version split health tracking — baseline expectations by API level? (Client-side.)
3. Device model/OEM error variance — reportable signal or noise? (Client-side.)
4. Is the 6× tunnel-failure ramp driven by a client build rollout? (Cannot answer without client-side `ClientVersion × time` pivot — though `.04xx` is the new lead.)
5. **Confirm 106961 is the correct Android queue, or re-target to an Android-only sub-queue.** `owningTeamName="GSA  Client - XPlat"` suggests parent-queue routing; an Android-only child queue may exist that we're missing. (Open since v2; still unanswered.)
6. **Why is no detector firing on a 6× server-side ramp?** 3 consecutive ICM pulls have shown zero auto-detector ICMs. Either no Android detectors are wired in, or routing is misdirecting them to a different queue. (Open since v2; escalation in flight.)

---

## Contributors

- **Mulder** — scope/lead; NAAS-only scope lock; pending detector-silence + severity-promotion calls.
- **Scully** — data execution (v3 NAAS pull: 11 queries attempted, 10 passed, 1 deliberate ghost re-check reproduced; new S6b non-1P probe falsified the v1/v2 1P hypothesis; see `.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md` + `icm-team-106961-data-2026-06-08.md`).
- **Doggett** — telemetry architecture (NaaS-server vs Defender-client boundary); v2 HarryPotter ICM port-plan + `icm-queue-ingest` skill; pending: identify `.04xx` ring, file region-normalization ticket, ship v2.1 collector bucketing fix.
- **Skinner** — pending: detector-silence escalation; schema-ticket filing for ghost columns.
- **Reyes** — v3 report assembly (NAAS refreshed + ICM reused at 06-08 freshness + headline severity promotion + cross-domain candidate refresh).
- **Scribe** — git/orchestration; session log + decision-file processing.

**Timestamp:** 2026-06-09T14:46+05:30 (Tuesday, June 9, 2026 — v3 assembled atop NAAS server-observed window `2026-06-02T00:00Z → 2026-06-09T00:00Z`; ICM data fresh as of 2026-06-08, no movement in 24h)
**Report Version:** v3
**Report Assembled By:** Reyes (Report Writer)
