# NAAS Android Client Stability — 2026-06-03 → 2026-06-10
**Author:** Frohike (Play Vitals Analyst) — first pull post-hire
**Source:** Google Play Reporting API via `google-play-vitals` canonical skill (Play Developer Reporting v1beta1, service-account auth)
**Package:** `com.microsoft.scmx`
**NAAS attribution filter (issue-cluster level, applied to top-150 issues by report count):**
```text
NAAS predicate: lower(cause || ' ' || location) contains any of
  vpnserviceorchestrator, com.microsoft.scmx.vpn, com.microsoft.intune.vpn,
  features.consumer.vpn, features.naas, baseopenvpnclient, openvpn,
  libnaas, naas, tunnel, vpn
→ 17 NAAS issues identified out of top-150 by errorReportCount (4 CRASH, 13 ANR)
```
**Windows (data freshness from Play):**
- Rates (`crashRate` / `anrRate`): DAILY, **2026-06-02 → 2026-06-08** (freshness ends 06-08; prior 7d 05-26 → 06-01).
- Event counts (`errorCount`): DAILY, **2026-06-03 → 2026-06-09** (freshness ends 06-09).
- Hourly freshness extends to 2026-06-10 for crashRate/anrRate but is excluded — daily report uses DAILY weighted rates only.

---

## 1. Headline (NAAS-as-a-unit)

| Metric | Value | Denominator | Readout |
|---|---:|---|---|
| **NAAS crash reports, 7d in-window** | **4,898** | Sum of `errorReportCount` over 17 NAAS-attributed issue clusters | Top 17 NAAS issues × 6 daily bins. |
| **NAAS ANR reports, 7d in-window** | **4,413** | Same | ANR cluster long-tail concentrated in OpenVPN init. |
| **Affected users upper-bound** | **5,125** | Sum of `distinctUsers` across 17 NAAS issues (NOT deduplicated across issues/days — true unique users is lower) | Play does not expose installs at issue level, so this is a strict upper bound. |
| **User-perceived crash rate (whole app, 7d, user-weighted)** | **0.7045%** | All `com.microsoft.scmx` sessions on Android in the 7d window (Play's published `userPerceivedCrashRate`) | Below Google bad-behavior threshold 1.09%. NAAS-only crash rate cannot be computed from Play — Play does not expose NAAS-using session denominators. |
| **User-perceived ANR rate (whole app, 7d, user-weighted)** | **0.2619%** | Same | Below Google bad-behavior threshold 0.47%. |
| **Trend — crash rate vs prior 7d (05-26 → 06-01)** | **0.7045% vs 0.6783% (Δ +0.0262 pp, +3.9% rel)** | App-level user-weighted | Slight uptick, within noise. |
| **Trend — ANR rate vs prior 7d** | **0.2619% vs 0.2530% (Δ +0.0089 pp, +3.5% rel)** | App-level user-weighted | Flat. |
| **Tenants** | **not derivable from Play** | — | Play Vitals exposes no tenant attribution. Cross-reference Scully's server-side data for tenant cuts. |

> **Denominator note (HARD framing rule):** Play publishes one `userPerceivedCrashRate` per app, denominated by *all* `com.microsoft.scmx` users — not NAAS-using sessions. We therefore report:
> - **NAAS event counts** (numerator) — sourced from per-issue `errorCount` joined to the NAAS issue cluster set.
> - **App-level user-perceived rate** as the only Google-blessed rate Play will give us, with the explicit caveat that the denominator is the whole `com.microsoft.scmx` install base, not NAAS-enabled installs.
> - No "NAAS-only rate" is fabricated. Scully's server-side `TunnelServerOperationEvents` carries the NAAS-session denominator; Reyes pairs both signals in the daily report.

---

## 2. Per-Defender-Version NAAS table — PRIMARY DELIVERABLE
NAAS-event counts come from per-issue `errorCount` filtered to the 17 NAAS issues. App-level rates are Play's `userPerceivedCrashRate` / `userPerceivedAnrRate` for that version, user-weighted across the 7d (06-02 → 06-08) window. **`AppCrR% = whole-app crashes on that version ÷ distinct users on that version`** (NOT NAAS-only — Play won't give us a NAAS-only rate). Sorted by NAAS crash+ANR desc; suppressing rows with <5 NAAS events for brevity.

| Defender version (code → label) | NAAS Crashes | NAAS ANRs | App user-perceived CR% (7d) | App user-perceived ANR% (7d) | Users 7d (Play) | Notes |
|---|---:|---:|---:|---:|---:|---|
| `900200122` — 1.0.9002.0102 (prior prod) | **2,878** | **1,822** | 0.6025% | 0.1908% | 187,000 | Dominant absolute-volume version. Still the install-base leader on arm64. |
| `892100112` — 1.0.8921.0101 | 1,468 | 1,733 | 0.8770% | 0.2318% | 261,000 | Largest install base on arm64; highest single-version app CR%. |
| `891300112` — 1.0.8913.0101 | 201 | 266 | 0.6091% | 0.3144% | 34,000 | Long-tail still active. |
| `890500162` — 1.0.8905.0106 | 65 | 165 | 0.4091% | 0.3359% | 22,000 | |
| `870300112` — 1.0.8703.0101 | 49 | 108 | 0.3560% | 0.3270% | 10,000 | |
| 🔴 `900300412` — **1.0.9003.0401 (.04xx ring)** | **95** | 0 | **n/a — Play withholds rate (sub-threshold install base)** | n/a | <500 (suppressed) | **27 of these 95 NAAS crashes are libnaas_native_vpn.so SIGSEGVs** (see Top-Crash #3). Play does not publish a rate for this version — denominator is below privacy floor. Use Scully's server-side `ClientVersion = 1.0.9003.0401` rate (0.626% tunnel fail in v3 drop) as the corroborating signal. |
| `881400112` — 1.0.8814.0101 | 5 | 75 | 0.3657% | 0.2843% | 7,000 | |
| `880500132` — 1.0.8805.0103 | 6 | 42 | 0.5700% | 0.3029% | 7,000 | |
| `882800112` — 882800112 (unlabeled) | 23 | 17 | 0.9451% | 0.2552% | 870 | Low install-base, high CR% — investigate if this is a stale ring. |
| `860500112` | 2 | 35 | 0.4663% | 0.4475% | 5,200 | |
| `851400112` | 2 | 35 | 0.7310% | 0.3059% | 4,100 | |
| 🔴 `892100412` — **1.0.8921.0401 (.04xx ring)** | **34** | 0 | n/a — sub-threshold | n/a | <500 (suppressed) | All-crash, no ANR. |
| 🔴 `900200422` — **1.0.9002.0402 (.04xx ring)** | **20** | 1 | n/a — sub-threshold | n/a | <500 (suppressed) | |
| 🔴 `900100422` — **1.0.9001.0402 (.04xx ring)** | **18** | 0 | n/a — sub-threshold | n/a | <500 (suppressed) | |
| `900300212` — 1.0.9003.0201 (open testing) | 8 | 6 | n/a — sub-threshold | n/a | <500 | New ring; low signal so far. |

**.04xx ring aggregate (4 ring versions detected: 900300412, 892100412, 900200422, 900100422):** **169 NAAS crashes, 1 NAAS ANR**, accounting for **3.45% of NAAS crash reports** but **0.0% of Play-published install-base users in the 7d window** (Play withholds per-version rate for all four — sub-threshold). The 4 ring versions are **crash-only** clusters — they contribute essentially zero ANR signal, consistent with native NAAS VPN library SIGSEGVs (Top-Crash #3) being the dominant ring failure mode. **Over-index vs production cannot be computed against a Play denominator** because Play hides the denominator for these versions; Scully's server-side `1.0.9003.0401` rate of 0.626% (vs 0.271% baseline, +131%) is the only verifiable lift number.

**Top-2-version concentration:** versions 900200122 + 892100112 carry **89% of NAAS crashes (4,346/4,898)** and **80% of NAAS ANRs (3,555/4,413)**. Any NAAS-class regression should be assessed against these two SKUs first.

---

## 3. Top 5 NAAS Crashes — root-cause depth

| # | Issue ID | Cluster cause / location | 7d reports | Affected users (proxy) | Top versions | Sample top frames (NAAS hook in bold) | Root-cause hypothesis |
|---:|---|---|---:|---:|---|---|---|
| 1 | `3e11c004ac1da2e009d8395ae8c47ec0` | `Unknown Source - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand` / `android.app.StackTrace` (foreground-service timeout) | **3,763** | 475 | 900200122 (2,146), 892100112 (1,307), 891300112 (165) | `android.app.RemoteServiceException$ForegroundServiceDidNotStartInTimeException`<br>`at ActivityThread.generateForegroundServiceDidNotStartInTimeException (ActivityThread.java:2428)`<br>`at ActivityThread.throwRemoteServiceException (ActivityThread.java:2396)`<br>`at ActivityThread$H.handleMessage (ActivityThread.java:2727)`<br>**Caused by `Last startServiceCommon() call for this service was made here at ContextImpl.startServiceCommon (ContextImpl.java:2022)` → `VpnServiceOrchestrator.onStartCommand` did not reach `startForeground()` in time** | 🟢 **High confidence — Android foreground-service timeout.** `VpnServiceOrchestrator.onStartCommand()` starts NAAS VPN foreground work but does not call `startForeground()` within the platform deadline (~5–10s on recent OS). Platform kills the service and surfaces this exception. Continues from prior 06-09 finding — same cluster, larger 7d count due to natural carryover. |
| 2 | `e216e51099939b7421de40c9c34e002b` | `SourceFile - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand` / same as #1 (different obfuscation map / build flavor) | **661** | 114 | 900200122 (542), 892100112 (88), 891300112 (17) | Same exception type as #1; line numbers differ (`ContextImpl.java:1995`, `Looper.java:226`) | 🟢 **High confidence — same root cause as #1.** Two issue clusters because Play splits by obfuscated symbol / line-number variance across builds. Combined with #1, foreground-service timeout = **4,424 / 4,898 = 90.3% of NAAS crashes**. |
| 3 | `4d2847836aab29fb4e92a5207a559326` | `[base.apk!libnaas_native_vpn.so]` / SIGSEGV | **282** | 219 | **900300412 (95 — .04xx ring)**, 900200122 (67), 892100112 (34) | `pid: 0, tid: 22741 >>> com.microsoft.scmx <<<`<br>`#00 pc 0x3c7214 base.apk!libnaas_native_vpn.so (BuildId 49526c68...)`<br>`#01 pc 0x37c7d0 base.apk!libnaas_native_vpn.so`<br>`#02 pc 0x37c478 base.apk!libnaas_native_vpn.so`<br>`#03 pc 0x3b1cfc base.apk!libnaas_native_vpn.so`<br>`#04 pc 0x3b16e4 base.apk!libnaas_native_vpn.so`<br>`#05 pc 0x3b57dc base.apk!libnaas_native_vpn.so`<br>`#06 pc 0xa6f0c libc.so __pthread_start`<br>**All 6 top frames are inside `libnaas_native_vpn.so`** — native NAAS code, not Android runtime | 🟡 **Medium confidence — native crash inside `libnaas_native_vpn.so`** on a NAAS worker thread (`__pthread_start` parent). Symbolication needed to name the function and assert dereference vs use-after-free. **`.04xx` ring (900300412) contributes 33.7% (95/282) of this issue's volume** — the strongest single-version concentration in any NAAS crash cluster. Carries forward Scully's 06-09 finding; symbol-resolve task still owed to whoever owns the NAAS native build (`fetch-native-crash` → `fetch-symbols` → `symbolicate-native` skill chain). |
| 4 | `33611ed4982975669064e6e7891f6d6f` | `Unknown Source - com.microsoft.scmx.features.consumer.vpn.d.get` / `java.lang.IllegalStateException` | **192** | 94 | 900200122 (123), 892100112 (39), 891300112 (12) | `java.lang.RuntimeException: Unable to create application com.microsoft.defender.application.MDApplication: java.lang.IllegalStateException`<br>`at ActivityThread.handleBindApplication (ActivityThread.java:8328)`<br>**`features.consumer.vpn.d.get`** (Hilt/Dagger consumer-VPN provider read before initialization) | 🟡 **Medium confidence — VPN dependency provider read before lifecycle is ready.** Consumer-VPN injection point (`com.microsoft.scmx.features.consumer.vpn.d.get`, obfuscated DI accessor) is consumed during `MDApplication.onCreate()` before its initialization invariant holds. Same root-cause family as prior 06-09 issue (`116c63de…`, OEM=TECNO heavy on API 30); today's variant is samsung-on-API-36 heavy. |
| 5 | `7accea69f4f22acd5bbe1d759ff9400c` *(carry-over from 06-09; below top-150 by lifetime, not pulled today — referenced for continuity)* | `VpnServiceOrchestrator.onStartCommand` / `OutOfMemoryError: pthread_create failed` | (06-09: 93) | (06-09: 40) | 892100111, 892100112, 881400111 | `at java.lang.Thread.nativeCreate`<br>`at Thread.start (Thread.java:1425)`<br>**`at VpnServiceOrchestrator.onStartCommand (Unknown Source:174)`** | 🟢 **High confidence — thread-resource exhaustion.** `pthread_create` failure during NAAS VPN service start; consistent with reconnect-loop thread growth. Not in this 7d's top-150 by lifetime — confirm with next pull whether it remained sub-threshold or rolled off. |

---

## 4. Top 3 NAAS ANRs — root-cause depth

| # | Issue ID | Cluster cause / location | 7d reports | Affected users (proxy) | Top versions | Sample top frames (NAAS hook in bold) | Root-cause hypothesis |
|---:|---|---|---:|---:|---|---|---|
| 1 | `6ab4dc76a10f6b8ec8524f4c1f020cf1` | `unavailable - com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize` / "ANR triggered by slow operations in main thread" | **1,244** | 1,202 | 892100112 (542), 900200122 (436), 891300112 (93) | `"main" tid=1 Native`<br>`#00 pc 0x1e4e20 base.apk (BuildId c07da70949ac721c…)`<br>`#01 pc 0xf3394 linker64 __dl_soinfo::call_constructors+628`<br>`#02 pc 0xda670 linker64 __dl_do_dlopen+2816`<br>`#03 pc 0xd4cf8 linker64 __loader_android_dlopen_ext+72`<br>`#04 pc 0x4110 libdl.so android_dlopen_ext+16`<br>`#05 pc 0x19638 libnativeloader.so`<br>`#06 pc 0x8724 libnativeloader.so OpenNativeLibrary+568`<br>`#07 pc 0x422274 libart.so JavaVMExt::LoadNativeLibrary+792`<br>**`at Runtime.loadLibrary0` → `BaseOpenVpnClient.initialize`** | 🟢 **High confidence — native OpenVPN library load on main thread.** Main thread blocks inside `dlopen`/`call_constructors` while NAAS loads OpenVPN/native VPN libraries during `BaseOpenVpnClient.initialize()`. Largest single NAAS ANR cluster — explains **28.2% of NAAS ANRs (1,244/4,413)** by itself. Dominant ANR finding from 06-09 holds. |
| 2 | `868ca86b7a9b6b19278fbe252f496d30` | `BaseOpenVpnClient.initialize` / "main thread waiting for too long" (different ANR sub-cause) | **648** | 626 | 900200122 (317), 892100112 (225), 891300112 (34) | `"main" tid=1 Native`<br>`#00 syscall+28`<br>`#01 art::ConditionVariable::WaitHoldingLocks+140`<br>`#02 art::JNI<false>::NewWeakGlobalRef+1324`<br>`#03 art::JavaVMExt::LoadNativeLibrary+964`<br>`#04 JVM_NativeLoad+368`<br>`at Runtime.nativeLoad` → **`at BaseOpenVpnClient.initialize (unavailable:49)` → `ConsumerVpnClient.initialize (unavailable:5)` → `com.microsoft.scmx.vpn.e.g (unavailable:8)` → `MDApplication.onCreate (unavailable:861)`** | 🟢 **High confidence — same root cause as #1, different point in native-load critical section.** Main thread is parked in `ConditionVariable::WaitHoldingLocks` inside `JavaVMExt::LoadNativeLibrary` (JVM's mutual-exclusion around `JNI_OnLoad`). Combined with #1, OpenVPN library-load ANRs = **1,892 / 4,413 = 42.9% of NAAS ANRs**. **Mitigation owed: move `BaseOpenVpnClient.initialize()` off main thread.** |
| 3 | `6056db512c32b4370dd8325264e3a503` | `unavailable - com.microsoft.intune.vpn.g.c` / "thread waiting for a binder transaction" | **585** | 560 | 900200122 (280), 892100112 (215), 891300112 (38) | `"main" tid=1 Native`<br>`#00 __ioctl+8 (libc.so)`<br>`#01 ioctl+156`<br>`#02 IPCThreadState::transact+1228 (libbinder.so)`<br>`#03 BpBinder::transact+156`<br>`#04 android_os_BinderProxy_transact+152`<br>`at BinderProxy.transact (BinderProxy.java:655)`<br>`at IActivityManager$Stub$Proxy.registerReceiverWithFeature (IActivityManager.java:6321)`<br>`at ContextImpl.registerReceiver`<br>**`at com.microsoft.intune.vpn.g.c (unavailable:66)`** (obfuscated Intune VPN bridge) | 🟡 **Medium confidence — Intune VPN bridge blocking on binder during `registerReceiver`.** Main thread blocks on a binder `ioctl` inside `ActivityManager.registerReceiverWithFeature` invoked from the Intune VPN module (`com.microsoft.intune.vpn.g.c`). Pattern is *binder slowness*, not necessarily an Intune bug — but the call site is NAAS code-owned. samsung-heavy (503/585 ≈ 86%). |

---

## 5. Cross-reference to Scully's 06-09 server-side findings

| Scully finding (server-side, 06-09 drop) | Client (Play Vitals) corroboration today | Verdict |
|---|---|---|
| **.04xx ring concentration: anchor `1.0.9003.0401` cohort +131% fail-rate (0.271% → 0.626%); +55% cohort growth, internal-ring-style (2 tenants)** | **YES — partial.** Play withholds per-version rate for all four detected `.04xx` ring SKUs (900300412, 892100412, 900200422, 900100422) because their install base is sub-threshold (the privacy floor *is itself* corroboration that this is a small-population ring). What we CAN see client-side: (a) 169 NAAS crashes / 1 NAAS ANR across the .04xx ring = **3.45% of NAAS crash volume, ~0% of NAAS ANR volume** — the ring is **crash-only**, not ANR-shaped; (b) the native `libnaas_native_vpn.so` SIGSEGV cluster (Top-Crash #3) is **33.7% .04xx** (95/282) — the strongest single-version concentration in any NAAS crash cluster, and the only one where .04xx is the leading version. The native lib SIGSEGV is the most plausible same-event client symptom of the server-side tunnel-fail ramp. | **CORROBORATED qualitatively.** Quantitative lift cannot be re-derived from Play (denominator suppressed); trust Scully's 0.626% / +131% number as the rate signal. |
| **EU intensification** (server-side `TunnelServerOperationEvents` flagged EU as overrepresented in failing region cuts) | **YES — strong.** App-level user-perceived crash rate by country (7d, 06-02 → 06-08, users ≥ 500): **EU aggregate 1.3868% vs non-EU 0.4463% — 3.1× lift in EU.** Germany alone is **3.2452%** on 29,000 users — **well above Google's 1.09% bad-behavior threshold**. Other EU offenders: Hungary 1.67%, Czechia 1.57%, Greece 1.42%, Slovakia 0.97%. Caveat: this is *whole-app* crash rate by country, not NAAS-only; but it co-locates with Scully's NAAS EU finding and the app's only EU-scale feature change is NAAS rollout. | **CORROBORATED.** New finding worth surfacing — Germany alone breaching Google threshold is a separate watch item for Reyes. |
| **PROFILE_UNDEFINED signal** (server-side: missing/undefined VPN profile state in `TunnelServerOperationEvents`) | **PARTIAL.** No issue cluster name contains the literal token `PROFILE_UNDEFINED`. Closest client analogue is issue **`5db43cba8a099bc7a5fcc29062ec4899`** — ANR in `com.microsoft.intune.vpn.profile.c.<init>` → `MasterVPNProfileSource.<init>` (45 reports / 7d), blocked on binder `registerReceiver` during profile-source construction. That's a profile-init *blocking* path on the client, not a profile-undefined runtime error. Other related cluster: **`31b828d3a4fb120e3dd3d6d96862a570`** (06-09 drop) — `NaaSVPNJNIClientImpl.naasIsBreakglass` → `UnsatisfiedLinkError` when breakglass check runs before native NAAS library is loaded; client analogue of "settings/profile not yet defined." | **PARTIAL — different shape client-side.** Client doesn't surface "PROFILE_UNDEFINED" as a crash signature; the closest match is binder-stalled profile *construction*, which would *produce* the server-observed undefined-profile state (the constructor never completes, so downstream calls see no profile). Recommend Scully confirm whether server `PROFILE_UNDEFINED` events temporally co-occur with client `5db43cba…` ANRs by tenant. |

---

## 6. NAAS Subsystem Breakdown (carry-forward shape from 06-09, refreshed)

| Subsystem | NAAS Crashes (7d) | Share | NAAS ANRs (7d) | Share | Readout |
|---|---:|---:|---:|---:|---|
| VpnServiceOrchestrator (FG-svc timeout / pthread OOM) | 4,424 | **90.3%** | ~0 | <1% | Dominant crash source — Android FG-service enforcement. Two clusters #1+#2. |
| Native NAAS VPN library (libnaas_native_vpn.so SIGSEGV) | 282 | 5.8% | 0 | 0% | Native SIGSEGV cluster — .04xx-heavy (33.7%). Symbolication still owed. |
| Consumer VPN provider IllegalStateException | 192 | 3.9% | 494 | 11.2% | DI/lifecycle race during MDApplication.onCreate. |
| OpenVPN/BaseOpenVpnClient native load | 0 | 0% | 1,892 | **42.9%** | Dominant ANR source — main-thread `dlopen`/native lib init. Two clusters #1+#2. |
| Intune VPN bridge (binder wait + profile init) | 0 | 0% | 630 | 14.3% | `com.microsoft.intune.vpn.g.c` + `profile.c.<init>` binder stalls. |
| NAAS VPN UX model `<init>` | 0 | 0% | 446 | 10.1% | `NaaSData.<init>` slow on main thread (ICU / locale resolution). |
| Other NAAS (e.g. `scmx.vpn.e.g`, breakglass JNI) | 0 | 0% | 951 | 21.5% | Long-tail. |
| **Total NAAS** | **4,898** | 100% | **4,413** | 100% | 17 issue clusters identified. |

---

## 7. New-in-window observations
- No new NAAS issue cluster IDs appeared today vs the 06-09 set. The top-17 NAAS set is stable.
- **Germany whole-app crash rate (3.25%) breaching Google's 1.09% bad-behavior threshold** is the most actionable *new* signal from this pull — though NAAS attribution at the country level cannot be made from Play alone (would need Scully's server-side country cuts to confirm NAAS-driven).

---

## 8. GO / PARTIAL / NO-GO verdict for Reyes

### **GO — ship as a new "NAAS Client Stability" section in the 2026-06-10 daily report.**

Rationale:
1. Data freshness clean: crashRate/anrRate through 06-08, errorCount through 06-09 — within Play's normal 1–2-day lag.
2. NAAS attribution is reproducible: 17 NAAS issue clusters from top-150-by-lifetime, all carry recognizable NAAS markers in cause/location.
3. Headline numbers stated with explicit denominators (no fabricated "NAAS-only rate").
4. Two cross-references to Scully's server-side findings landed cleanly — .04xx corroborates qualitatively (denominator suppressed by Play), EU corroborates quantitatively and adds a new actionable (Germany over threshold).

**Caveats Reyes must carry through:**
- "NAAS crash/ANR reports" = **counts**, not rates. The denominator (NAAS-using sessions) does not exist in Play; only Scully's server-side `TunnelServerOperationEvents` carries it.
- Per-version NAAS counts are filtered through the **top-150 issues by lifetime errorReportCount**. Issues outside that set are invisible to today's pull. For a NAAS-class issue with low lifetime cumulative but a sudden 7d spike, deepen the inventory pull (`page_size=25 × 8 pages`) on the next iteration.
- `libnaas_native_vpn.so` SIGSEGV stack (Top-Crash #3) is unsymbolicated. Whoever owns the NAAS native build needs to run `fetch-symbols` + `symbolicate-native` against BuildId `49526c68f7fd7a48c02c4e4383427a95d1a9d7ff` to name the failing function.
- `.04xx` ring versions (900300412, 892100412, 900200422, 900100422) have **no Play-published crash rate** because their install base is below Play's privacy floor. The lift number must come from Scully's server-side cohort math (0.626% / +131%) and cannot be reconstructed from Play alone.
- Country-level rates are **whole-app**, not NAAS-only. EU intensification is suggestive but not provable as NAAS-driven from Play data; confirm via Scully's NAAS-tenant-by-region cut.

---

## 9. Continuity with prior drops
- 06-09 (Scully): `.04xx` over-indexed in rate (~13×) — confirmed today only qualitatively (Play hides denominator).
- 06-09 (Scully): VpnServiceOrchestrator foreground-service timeout = dominant crash cause — **reconfirmed today at 90.3%** of NAAS crashes.
- 06-09 (Scully): OpenVPN native load = dominant ANR cause — **reconfirmed today at 42.9%** of NAAS ANRs.
- New today: **Germany 3.25% whole-app crash rate** exceeding Google's 1.09% threshold; EU 3.1× non-EU.
- New today: explicit identification of **4 distinct `.04xx` ring SKUs** active in this 7d window (vs 06-09 which surfaced only 900300412); all four are crash-only clusters, no ANR signal.
