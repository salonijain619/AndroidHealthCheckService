# 📋 GSA Android Daily Livesite Report — Wed Jun 10, 2026

📱 **Defender for Android — Live on Play Store: `v1.0.9002.0102`** (released 2026-06-10; rollout % not visible — Play Console auth needed; active ramp inferred from +51% device growth WoW in server telemetry). _Source: Langly._

> **Scope (2026-06-10):** First daily that fuses three parallel sources — Scully (server-side NAAS telemetry, `idsharedwus / NaasProd`), **Frohike (Google Play Vitals, NAAS-as-a-unit)** — NEW, and Langly (Play Store production version tracker) — NEW. Server-side NAAS data is reused from the 2026-06-09 pull (window `2026-06-02T00:00Z → 2026-06-09T00:00Z`; Saloni did not request a re-pull). Client-side Play Vitals data is fresh today: rates daily `2026-06-02 → 2026-06-08`, event counts daily `2026-06-03 → 2026-06-09`. ICM data is reused from 2026-06-08 (no movement in 24h confirmed).

> **Headline reframe vs 06-09:** Langly confirmed live production is `1.0.9002.0102` — **NOT** `1.0.9003.0401`. The `.04xx` ring that anchored yesterday's top single-version regression is an **internal/closed-test ring**, not the production track. The `.04xx` server-side fail-rate spike (+131%) is therefore reframed as a **forward-looking ring-promotion risk**, not live customer pain. The customer-facing build (`9002.0102`) is up ~+21% (concerning but not crisis). Separately, Frohike's client-side data **independently corroborates** Scully's EU intensification — at user-perceived crash level, **Germany is 3.25% (over Google's 1.09% Play Console bad-behavior threshold)**.

## 📟 On-Call Today

| Role | Engineer |
|---|---|
| 🔴 Primary | dileepkusuma |
| 🟡 Backup | samirnen |

---

## Executive Summary

🔄 **`.04xx` REFRAMED — pre-production ring risk, NOT live customer pain.** Langly confirms `1.0.9002.0102` is the live Play Store production build. Scully's `.04xx` anchor (`1.0.9003.0401`, +131% fail-rate, 1,003 devices / 2 tenants) is an internal/closed-test ring — Play withholds per-version rate because its install base is sub-privacy-threshold. Frohike independently confirms the ring shape: the four `.04xx` SKUs (900300412, 892100412, 900200422, 900100422) are **crash-only clusters** with **0 ANR signal** and contribute 3.45% of NAAS crashes against ~0% of the install base. **Action:** treat as a ring-promotion blocker, not a live-incident anchor. The live-user anchor on the mainstream `.01xx` track is the milder +21% uptick on `9002.0102`.

🌍 **EU regional degradation is now cross-domain CORROBORATED — Germany at Google's bad-behavior threshold.** Server-side (Scully): `germanywestcentral` +67%, `NorthEurope` +61%, `SwedenCentral` +114%, `WestEurope` +53%, `francecentral` +57%. Client-side (Frohike, 7d user-weighted by country): **EU aggregate whole-app crash rate 1.387% vs non-EU 0.446% — 3.1× lift**, with **Germany alone at 3.25% on 29K users — over Google's 1.09% Play Console bad-behavior threshold.** Both vectors (server fail-rate AND user-perceived crash-rate) point at the same region cluster. **Risk:** sustained breach degrades Play Store visibility/ranking, independent of NAAS attribution.

🟠 **Server-side ramp still climbing — 7d fail-rate 0.289% → 0.385% (+33%), daily peak 0.447% on 6/08.** Failures +35% on +1.4% traffic = pure quality degradation. A single +0.55pp day crosses the 1% incident threshold. Carried forward from 06-09 (Scully); Saloni did not re-pull today.

🔬 **Server↔client correlation strongest at `libnaas_native_vpn.so` SIGSEGV.** Frohike's Top-Crash #3 (282 reports, 219 users) is **33.7% concentrated in the `.04xx` ring** (`900300412`: 95/282) — strongest single-version concentration in any NAAS cluster, and the most plausible client symptom of Scully's server-side tunnel-fail ramp. **Per the `.04xx` reframe, this is a pre-production hazard**, not live customer impact — but it is the cleanest signal we have that the ring-promotion risk is real and code-localized.

🔴 **Detector silence pattern still stands — 3+ pulls, zero auto-ICMs against a 6× server-side ramp + a Play-Console-threshold-breaching country.** Control-plane gap is structural, not transient. Mulder/Skinner escalation still pending.

---

## Key Metrics

> **Side-by-side framing:** Server-side rows come from Scully's 06-09 `TunnelServerOperationEvents` pull (denominator = NAAS sessions). Client-side rows come from Frohike's 06-10 Play Vitals pull (denominator = **whole-app** `com.microsoft.scmx` installs — Play does NOT expose a NAAS-only session denominator). The two views are complementary, not interchangeable.

### Server-side (Scully, NAAS telemetry, 7d window `2026-06-02 → 2026-06-09`, reused)

| Metric | Value | Trend |
|---|---|---|
| Active Android Devices (7d distinct, server-observed) | **27,744** | ➡️ +0.9% (flat) |
| Active Android Tenants (7d distinct) | **1,254** | ➡️ +1.0% (flat) |
| Fleet Tunnel Events (7d) | **131,874,839** — 131,367,196 success / **507,643 failure** | ⬆️ Events +1.4%, **failures +35.1%** — pure quality degradation |
| Tunnel Health (server-side success) | **99.615%** (7d fail-rate **0.385%**) | ⬆️ +33% (0.289 → 0.385); daily peak **0.447% on 6/08** |
| APS Get-Settings Availability (7d) | **99.996%** (268.9M events / 818K devices / 24,092 tenants) | ✅ Healthy, flat |
| APS Settings-Ack Success (7d) | **99.99970%** (267.2M / 267.2M; 813 auth fails) | ✅ Healthy, flat |
| PKI Cert Enrollment Health (7d) | ✅ **5 errors / 707,887 events = 0.0007%** (1,326+ tenants); new low-volume failure class: 2× HTTP 500 `Failed/GetEnrollmentJobStatus` | ➡️ Flat; new watch item |
| Android Client Version Distribution (server-side) | **Live prod `1.0.9002.0102`: 0.33–0.35% band (~+21%, mild).** Mainstream `.01xx` (8921.0101, 8913.0101) similar band. **Internal `.04xx` ring `1.0.9003.0401`: 0.626% (+131%, 1,003 devices / 2 tenants)** — pre-production, NOT live customer track per Langly. Long-tail pre-`8900` builds 0.87–2.67%. | ⬆️ `.04xx` regression confined to internal ring; live prod track milder |
| Tunnel Latency p50/p95/p99 | TBD — `LatencyMs` ghost-column on `TunnelServerOperationEvents` (SEM0100) | 🔴 Unfixed 4d |

### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit, 7d `2026-06-02 → 2026-06-08` rates / `2026-06-03 → 2026-06-09` counts)

| Metric | Value | Denominator | Readout |
|---|---|---|---|
| NAAS crash reports (7d in-window) | **4,898** | Sum of `errorReportCount` over 17 NAAS-attributed issue clusters | 17 NAAS issues identified out of top-150 by lifetime |
| NAAS ANR reports (7d in-window) | **4,413** | Same | ANR long-tail concentrated in OpenVPN init |
| Affected users (upper bound) | **5,125** | Sum of `distinctUsers` across 17 NAAS issues (NOT cross-issue deduped) | True unique-user count is lower |
| **App user-perceived crash rate (whole-app, 7d, user-weighted)** | **0.7045%** | All `com.microsoft.scmx` Android sessions in window | ✅ Below Google bad-behavior threshold 1.09% |
| **App user-perceived ANR rate (whole-app, 7d, user-weighted)** | **0.2619%** | Same | ✅ Below Google bad-behavior threshold 0.47% |
| Δ crash rate vs prior 7d (05-26 → 06-01) | **0.7045% vs 0.6783%** (+0.026pp / +3.9% rel) | App-level | ➡️ Slight uptick, within noise |
| Δ ANR rate vs prior 7d | **0.2619% vs 0.2530%** (+0.009pp / +3.5% rel) | App-level | ➡️ Flat |
| Tenant attribution | **Not derivable from Play** | — | Play Vitals exposes no tenant cut — use Scully for tenant slicing |

> **Denominator framing rule:** "NAAS crash/ANR" are **counts**, not rates. Play does not publish a NAAS-using-session denominator; only Scully's `TunnelServerOperationEvents` carries it. The two user-perceived rates above are app-wide, NOT NAAS-only.

---

## 🆕 NAAS Client Stability (Google Play Vitals)

_Frohike's first daily — NAAS-attributed via cluster-level predicate match on `vpnserviceorchestrator | com.microsoft.scmx.vpn | com.microsoft.intune.vpn | features.consumer.vpn | features.naas | baseopenvpnclient | openvpn | libnaas | naas | tunnel | vpn` against top-150 issues by `errorReportCount`. 17 NAAS issues identified (4 CRASH, 13 ANR)._

### Headline (NAAS-as-a-unit)

- **4,898 NAAS crash reports / 4,413 NAAS ANR reports** over the 7-day window, **upper-bound 5,125 affected users**.
- App-level user-perceived rates (only Google-blessed rate; denominator = whole `com.microsoft.scmx` install base, NOT NAAS-only): **crash 0.7045%**, **ANR 0.2619%** — both **below** Google's bad-behavior thresholds (1.09% / 0.47%) at the app aggregate level.
- **No NAAS-only rate is fabricated.** For NAAS-attributed rate signal, pair with Scully's server-side `TunnelServerOperationEvents` (0.385% 7d / 0.447% peak day).

### Per-Defender-version NAAS table (PRIMARY)

NAAS-event counts from per-issue `errorCount` filtered to 17 NAAS issues. App rates from Play `userPerceivedCrashRate` / `userPerceivedAnrRate`, user-weighted across 7d (06-02 → 06-08). Rows with <5 NAAS events suppressed. Sorted by NAAS crash + ANR desc.

| Defender version | NAAS Crashes | NAAS ANRs | App CR% (7d) | App ANR% (7d) | Users 7d | Notes |
|---|---:|---:|---:|---:|---:|---|
| `1.0.9002.0102` ✅ **LIVE PROD** | **2,878** | **1,822** | 0.6025% | 0.1908% | 187,000 | Dominant absolute volume on arm64. Live Play Store production track (Langly). |
| `1.0.8921.0101` | 1,468 | 1,733 | 0.8770% | 0.2318% | 261,000 | Largest install base on arm64; highest single-version app CR% in the live cohort. |
| `1.0.8913.0101` | 201 | 266 | 0.6091% | 0.3144% | 34,000 | Long-tail still active. |
| `1.0.8905.0106` | 65 | 165 | 0.4091% | 0.3359% | 22,000 | |
| `1.0.8703.0101` | 49 | 108 | 0.3560% | 0.3270% | 10,000 | |
| 🔴 `1.0.9003.0401` **(.04xx INTERNAL RING)** | **95** | 0 | n/a — Play withholds (sub-threshold install base) | n/a | <500 (suppressed) | **27 of these 95 are `libnaas_native_vpn.so` SIGSEGVs** (Top-Crash #3). Use Scully's server-side rate (0.626% / +131%) for lift. **Not on production track** (Langly). |
| `1.0.8814.0101` | 5 | 75 | 0.3657% | 0.2843% | 7,000 | |
| `1.0.8805.0103` | 6 | 42 | 0.5700% | 0.3029% | 7,000 | |
| `882800112` (unlabeled) | 23 | 17 | 0.9451% | 0.2552% | 870 | Low install-base, high CR% — possible stale ring; flag to Doggett. |
| `860500112` | 2 | 35 | 0.4663% | 0.4475% | 5,200 | |
| `851400112` | 2 | 35 | 0.7310% | 0.3059% | 4,100 | |
| 🔴 `1.0.8921.0401` **(.04xx INTERNAL RING)** | **34** | 0 | n/a — sub-threshold | n/a | <500 | All-crash. |
| 🔴 `1.0.9002.0402` **(.04xx INTERNAL RING)** | **20** | 1 | n/a — sub-threshold | n/a | <500 | |
| 🔴 `1.0.9001.0402` **(.04xx INTERNAL RING)** | **18** | 0 | n/a — sub-threshold | n/a | <500 | |
| `1.0.9003.0201` (open testing) | 8 | 6 | n/a — sub-threshold | n/a | <500 | New ring; low signal so far. |

**`.04xx` ring aggregate (4 SKUs):** **169 NAAS crashes, 1 NAAS ANR** = 3.45% of NAAS crash volume / ~0% of NAAS ANR volume / ~0% of Play install-base users (all 4 below Play privacy floor). **Crash-only fingerprint** — consistent with native NAAS VPN library SIGSEGVs (Top-Crash #3) being the dominant ring failure mode. **Quantitative lift cannot be computed against Play denominator** (suppressed); Scully's server-side `1.0.9003.0401` rate of 0.626% (vs 0.271% baseline, +131%) is the only verifiable lift number.

**Top-2-version concentration:** `1.0.9002.0102` + `1.0.8921.0101` carry **89% of NAAS crashes (4,346/4,898)** and **80% of NAAS ANRs (3,555/4,413)**. Any NAAS-class regression should be assessed against these two SKUs first.

### Top NAAS crashes (top 3 of 5; full root-cause depth in Frohike's drop)

| # | Cluster cause / location | 7d reports | Affected users | Top versions | Root-cause hypothesis |
|---:|---|---:|---:|---|---|
| 1 | `VpnServiceOrchestrator.onStartCommand` / `ForegroundServiceDidNotStartInTimeException` (cluster `3e11c004…`) | **3,763** | 475 | 9002.0102 (2,146), 8921.0101 (1,307), 8913.0101 (165) | 🟢 **High confidence — Android foreground-service timeout.** `VpnServiceOrchestrator.onStartCommand()` does not call `startForeground()` within platform deadline (~5–10s); platform kills service. |
| 2 | Same as #1, different obfuscation map (cluster `e216e510…`) | **661** | 114 | 9002.0102 (542), 8921.0101 (88), 8913.0101 (17) | 🟢 Same root cause as #1. **Combined #1+#2 = 4,424 / 4,898 = 90.3% of NAAS crashes.** |
| 3 | `[base.apk!libnaas_native_vpn.so]` / SIGSEGV (cluster `4d284783…`) | **282** | 219 | **🔴 .04xx ring 900300412 (95)**, 9002.0102 (67), 8921.0101 (34) | 🟡 **Medium — native SIGSEGV inside `libnaas_native_vpn.so`** on NAAS worker thread (`__pthread_start` parent). All 6 top frames inside the NAAS native lib. **`.04xx` ring contributes 33.7%** — strongest single-version concentration in any NAAS cluster. Symbolication still owed (BuildId `49526c68…`). |

### Top NAAS ANRs (top 3 of 3; full table in Frohike's drop)

| # | Cluster cause / location | 7d reports | Affected users | Top versions | Root-cause hypothesis |
|---:|---|---:|---:|---|---|
| 1 | `BaseOpenVpnClient.initialize` / native lib `dlopen` on main thread (cluster `6ab4dc76…`) | **1,244** | 1,202 | 8921.0101 (542), 9002.0102 (436), 8913.0101 (93) | 🟢 **High — native OpenVPN library load blocking main thread.** Top 7 frames in `linker64::call_constructors → dlopen → JavaVMExt::LoadNativeLibrary`. **28.2% of NAAS ANRs alone.** |
| 2 | Same root as #1, different point in critical section (cluster `868ca86b…`) | **648** | 626 | 9002.0102 (317), 8921.0101 (225), 8913.0101 (34) | 🟢 Same root cause. **Combined #1+#2 = 1,892 / 4,413 = 42.9% of NAAS ANRs.** **Mitigation owed: move `BaseOpenVpnClient.initialize()` off main thread.** |
| 3 | `com.microsoft.intune.vpn.g.c` / binder wait in `registerReceiver` (cluster `6056db51…`) | **585** | 560 | 9002.0102 (280), 8921.0101 (215), 8913.0101 (38) | 🟡 **Medium — Intune VPN bridge blocking on binder during `registerReceiver`.** Pattern is binder slowness, not necessarily Intune bug — but the call site is NAAS code-owned. **samsung-heavy (86%).** |

### Affected users / regions

- **Affected NAAS users (upper bound):** 5,125 over 7d (across 17 NAAS issues, not deduplicated cross-issue).
- **🔴 Germany whole-app crash rate: 3.2452% on 29,000 users — OVER Google's 1.09% Play Console bad-behavior threshold.** Sustained breach risks Play Store visibility/ranking.
- **EU aggregate (whole-app, 7d, user-weighted): 1.387% vs non-EU 0.446% — 3.1× lift.** Other EU offenders above app-average: Hungary 1.67%, Czechia 1.57%, Greece 1.42%, Slovakia 0.97%.
- Caveat: country-level rates are whole-app, NOT NAAS-only. EU correlation with Scully's NAAS server-side EU intensification is **strong and same-shape** but Play cannot prove NAAS-attribution at country level — Scully NAAS-tenant-by-region cut still owed.

### NAAS subsystem breakdown (where the volume actually lives)

| Subsystem | Crashes (7d) | Share | ANRs (7d) | Share |
|---|---:|---:|---:|---:|
| VpnServiceOrchestrator (FG-svc timeout) | 4,424 | **90.3%** | ~0 | <1% |
| Native NAAS VPN library (libnaas_native_vpn.so SIGSEGV) | 282 | 5.8% | 0 | 0% |
| Consumer VPN provider IllegalStateException | 192 | 3.9% | 494 | 11.2% |
| OpenVPN / BaseOpenVpnClient native load | 0 | 0% | 1,892 | **42.9%** |
| Intune VPN bridge (binder + profile init) | 0 | 0% | 630 | 14.3% |
| NAAS VPN UX model `<init>` (ICU/locale) | 0 | 0% | 446 | 10.1% |
| Other NAAS long-tail | 0 | 0% | 951 | 21.5% |
| **Total** | **4,898** | 100% | **4,413** | 100% |

---

## 🔍 Top Insights

| # | Severity | Insight | Action / Owner |
|---|---|---|---|
| 1 | 🟡 **P3 / forward-looking** | 🔄 **`.04xx` ring REFRAMED — pre-production risk, NOT live customer pain.** Langly confirms live Play Store prod = `1.0.9002.0102`. Scully's anchor `1.0.9003.0401` (+131% server fail-rate) and Frohike's 4 ring SKUs (169 crash-only NAAS reports, 0 ANR, all <500 users → Play hides denominator) are an **internal/closed-test ring**, not the GA track. **Reframes 06-09's top P2 anchor.** The live-user version `9002.0102` is up ~+21% (mild). | **Doggett:** confirm `.04xx` ring identity (channel? early ring? specific tenant set?); block ring promotion until the `libnaas_native_vpn.so` SIGSEGV is symbolicated and fixed. **Mulder:** re-grade yesterday's P2 down to forward-looking risk; new P2 anchor is the cross-domain EU finding (#2). |
| 2 | 🟠 **P2 — cross-domain CORROBORATED** | 🌍 **EU regional degradation confirmed at BOTH server-side fail-rate AND user-perceived crash-rate levels.** Server (Scully): germanywestcentral +67%, NorthEurope +61%, SwedenCentral +114%, WestEurope +53%, francecentral +57%. Client (Frohike): EU 1.387% vs non-EU 0.446% (3.1×); **Germany 3.25% — OVER Google's 1.09% Play Console bad-behavior threshold.** **Risk:** sustained breach degrades Play Store visibility/ranking, independent of NAAS attribution. | **Doggett:** EU-path hypothesis — what shared component fronts these regions? **Scully:** NAAS-tenant-by-region cut to test whether the EU client crash-rate co-locates with NAAS-using tenants; per-day region trend (still deferred from v1). **Mulder/Skinner:** weigh whether Germany-over-threshold warrants its own incident-track item (independent of the NAAS ramp). |
| 3 | 🟡 **P3 / pre-prod** | 🔬 **`libnaas_native_vpn.so` SIGSEGV is the strongest server↔client correlation today — 33.7% concentrated in `.04xx` ring.** Frohike Top-Crash #3 (282 reports / 219 users): 95/282 reports come from `1.0.9003.0401`. All 6 top frames inside the NAAS native lib. This is the single cleanest evidence that the ring-promotion risk (#1) is code-localized. **Per the `.04xx` reframe, this is pre-production hazard**, not live customer impact. | **Doggett (native build owner):** symbolicate BuildId `49526c68f7fd7a48c02c4e4383427a95d1a9d7ff` (run `fetch-symbols` → `symbolicate-native`); identify failing function; assert dereference vs use-after-free. **Block** `.04xx` promotion until resolved. |
| 4 | 🟠 **P2** | ⬆️ **Server-side ramp still climbing (carried from 06-09).** 7d fail-rate 0.289% → 0.385% (+33%); daily peak 0.447% on 6/08; failures +35% on +1.4% traffic = pure quality degradation. A single +0.55pp day crosses the 1% incident threshold. | **Scully:** standing daily fail-rate watch; if 6/09 or 6/10 daily exceeds 0.50%, escalate. **Mulder:** promote to P1 on first day crossing 1%. |
| 5 | 🟡 **P3 / watch** | ⬆️ **`PROFILE_UNDEFINED` device count +41% (245 → 345) while events only +10% (carried from 06-09).** More devices hitting the config-bootstrap race, not just more events per device. Frohike client-side: no literal `PROFILE_UNDEFINED` cluster, but closest analogue is ANR `5db43cba…` (Intune `MasterVPNProfileSource.<init>` binder stall, 45 reports / 7d) — profile-init *blocking* path that would *produce* server-observed undefined-profile state. | **Doggett:** join Tunnel failures (empty TenantId) ↔ APS GetSettings on `DeviceId` ±5min to confirm race. **Scully:** confirm whether server `PROFILE_UNDEFINED` events temporally co-occur with client cluster `5db43cba…` by tenant. |
| 6 | ❌ FALSIFIED | ~~**Microsoft 1P dogfood rollout driving regression**~~ — **FALSIFIED 06-09 (Scully S6b).** Non-1P daily fail-rate runs 0.49–0.60%, HIGHER than the global headline (1P traffic *dampens* it). Carried forward to keep the retraction visible. | None — closed. |
| 7 | 🔴 **Structural** | 🚨 **Detector silence — 3+ pulls with zero auto-detector ICMs against a 6× server-side ramp AND a Play-Console-threshold-breaching country.** Control-plane gap is structural. Escalation still on books (Mulder/Skinner). | **Mulder/Skinner:** why is no auto-ICM firing? File detector-coverage gap as its own work item. |

---

## 🔥 Cross-Domain Correlation

**Three independent vectors now cross-validate. For the first time, server-side and client-side signals corroborate each other on the same two findings (`.04xx` ring, EU regional cluster).**

### Server fail-rate vs client crash-rate (per-version alignment)

| Version | Server fail-rate (Scully, 7d) | Server trend | Client NAAS crashes (Frohike, 7d) | Client app CR% (Play, 7d) | Same-shape? |
|---|---|---|---:|---|---|
| `1.0.9002.0102` ✅ live prod | ~0.33–0.35% band | +21% | 2,878 | 0.6025% | ✅ Yes — mild on both vectors |
| `1.0.8921.0101` | ~0.35% band | +24% | 1,468 | 0.8770% | ✅ Yes — slightly elevated on both |
| 🔴 `1.0.9003.0401` `.04xx` | **0.626%** | **+131%** | 95 (27 are native SIGSEGV) | n/a (Play hides; <500 users) | ✅ **Qualitative match** — Play denominator suppression *itself* confirms ring is small + closed; lift number must come from Scully |

### `.04xx` server anchor ↔ `.04xx` client SIGSEGV concentration

```
Server (Scully):  1.0.9003.0401 cohort   →  +131% fail-rate, +55% device growth, 2 tenants
                                         ⟷
Client (Frohike): 1.0.9003.0401 cohort   →  33.7% of libnaas_native_vpn.so SIGSEGVs (95/282)
                                         ⟷
Langly:           1.0.9003.0401          →  NOT on production track (internal ring)

→ Verdict: pre-production hazard, code-localized in NAAS native lib, blocking signal for ring promotion.
```

### EU server intensification ↔ EU client crash-threshold breach

```
Server (Scully):  germanywestcentral +67%, NorthEurope +61%, SwedenCentral +114%, WestEurope +53%
                                         ⟷
Client (Frohike): EU agg 1.387% vs non-EU 0.446% (3.1×); Germany 3.25% (over 1.09% Play threshold)

→ Verdict: regional degradation is real on BOTH vectors. Cleanest dual-signal we have.
   Open question: Scully NAAS-tenant-by-region cut to determine whether client EU crashes are
   NAAS-attributable (currently only whole-app crashes proven; NAAS-link is shape-only).
```

### Primary correlation chain (updated)

```
Server-side tunnel fail-rate ramp (0.074% → 0.447%, 6× from baseline)
    ⟷  Uniform ServiceType degradation (+30–40% across M365 / INTERNET / PRIVATE_ACCESS)
    ⟷  EU region cluster acceleration (5+ regions +50–114%)
                            ⟷  Client EU crash-rate breach (Germany 3.25% > 1.09%)
    ⟷  .04xx ring (server +131% fail / client 33.7% of native SIGSEGV / NOT on prod track)
    ⟷  Detector silence (0 auto-ICMs, 3 pulls running)
```

### New validation steps (queued for next cycle)

1. ⏳ **Doggett:** symbolicate `libnaas_native_vpn.so` BuildId `49526c68…` and identify the SIGSEGV function. Block `.04xx` promotion until fixed.
2. ⏳ **Scully:** NAAS-tenant-by-region cut to confirm whether Germany's whole-app crash breach is NAAS-attributable.
3. ⏳ **Scully:** confirm `PROFILE_UNDEFINED` (server) temporally co-occurs with `MasterVPNProfileSource.<init>` ANR cluster `5db43cba…` (client) by tenant.
4. ⏳ **Mulder/Skinner:** detector-silence escalation — 3+ pulls confirmed, server ramp + client country-threshold breach not auto-detecting.
5. ⏳ **Frohike (next pull):** deepen issue inventory beyond top-150 (`page_size=25 × 8 pages`) to catch low-lifetime / high-7d-spike NAAS clusters. Confirm Germany rate movement vs today's baseline.

---

## ICM Snapshot

_Live as of 2026-06-08, no movement in 24h confirmed. Queue: team 106961. Weekly cadence — next re-pull aligned to weekly cycle._

| Bucket | Count | Notes |
|---|---|---|
| 🔴 Active + Mitigating | 1 | Sev3 #810723164 (TestICM, unack'd 5+ days) |
| By Severity | Sev1: 0 · Sev2: 0 · Sev3: 1 · Sev4: 0 | — |
| Customer-reported (`type=CustomerReported`) | 1 | — |
| System-detected | 0 | 🔴 Detector silence — 3-pull confirmed |
| 🧪 TestICM-flagged | 1 | Excluded from real-incident count |
| Mitigated last 7d | 0 | Same observation 3 pulls running |
| **Effective real-incident count** | **0** | After TestICM filter |

> ICM data is pulled on a weekly cadence aligned to this report.

---

## Contributors

- **Langly** — Play Store version tracker; confirmed live production = `1.0.9002.0102`, reframing the `.04xx` ring from "top anchor" to "pre-production hazard." See `.squad/agents/langly/research/play-store-versions.md`.
- **Frohike** — first daily Play Vitals (NAAS-as-a-unit) drop; 17 NAAS issue clusters identified, per-version table primary deliverable, EU country-level crash-rate breach surfaced (Germany 3.25% > 1.09%). See `.squad/agents/frohike/research/naas-crashes-2026-06-10.md`.
- **Scully** — server-side NAAS telemetry (06-09 pull reused today per Saloni's direction; no re-pull requested). See `.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md`.
- **Mulder** — scope/lead; pending: re-grade yesterday's `.04xx` P2 anchor; detector-silence escalation.
- **Doggett** — pending: symbolicate `libnaas_native_vpn.so` SIGSEGV; identify `.04xx` ring; EU-path hypothesis; profile-bootstrap race join.
- **Skinner** — pending: detector-silence escalation; schema/normalization tickets for ghost columns + region casing (open 5+ days).
- **Reyes** — daily report assembly; first 3-source fusion (Scully + Frohike + Langly); `.04xx` reframe + cross-domain EU corroboration as the two headline narrative shifts vs 06-09.
- **Scribe** — git/orchestration; session log + decision-file processing.

**Timestamp:** 2026-06-10T12:45+05:30 (Wednesday, June 10, 2026)
**Report Assembled By:** Reyes (Report Writer)
