**⚠️ EXAMPLE — NOT REAL DATA — For Template Reference Only**

---

# 📋 GSA Daily Livesite Report — Fri Jun 05, 2026

## 📟 On-Call Today
🔴 **Primary**    Eleanor Mulder (emulder)  
🟡 **Backup**     Dana Scully (dscully)

---

## Executive Summary

🔴 **CRITICAL:** Android client v6.2.1 authentication regression — 97.2% of auth failures concentrated on this version, affecting 8.1% of v6.2.1 fleet with 145x higher error rates than v6.0.8. This is a forced-upgrade path; fleet cannot downgrade safely.

🔴 **CRITICAL:** APS policy delivery degraded — 68.3% success (baseline 99.54%), 56M "SuccessSettingsNotFound" responses suggest MAM-enrolled device schema mismatch or bulk tenant policy changes during rollout window.

🔴 **Cross-domain correlation:** Auth (v6.2.1) + APS policy + notification channel — auth 401/403 errors blocking policy fetch; notification delivery spiking errors simultaneously, indicating client-side cascade preventing offline cache fallback.

🟡 **Fleet under stress** — 42K+ new devices in 7 days (+2.8%), Play Store channel adoption +11.3%, but error volume rising 31x faster than new device growth.

---

## Key Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Active Android Clients (weekday) | 612K (partial)* | ⚠️ -18.4% (incomplete telemetry) |
| Fleet Errors (7d) | 2.18B | ⬆️ +28.7% (401/403 auth dominates) |
| APS Availability | 68.3% success | 🔴 -31.2% (baseline 99.54%) |
| PKI Health | 99.8% | ✅ Healthy |
| Tunnel Health | 94.1% | 🟡 -4.2% |
| Android Client Version Distribution Health | v6.2.1: 🔴 47.2% of errors; v6.0.8: ✅ 0.3% error rate | ⬆️ v6.2.1 error spike |
| Business Growth (7d) | +42,156 devices | ⬆️ +2.8% |

*Expected ~670K when telemetry ingestion completes; June 5 AppInsights still buffering.

---

## 🔍 Top 5 Insights

| # | Severity | Insight Title | Blast Radius | Action / Owner |
|---|----------|---------------|-------------|-----------------|
| 1 | CRITICAL | v6.2.1 token validation failure in OAuth interceptor | 8.1% of v6.2.1 fleet (50K devices), cascading to 98K dependent policy requests | Doggett: Examine OAuth token refresh loop; confirm if cert pinning or OIDC endpoint schema drift. Mulder: prioritize v6.2.2 hotfix or emergency rollback exemption. |
| 2 | CRITICAL | APS policy batch schema incompatibility with MAM enrollment path | 56M failed policy apply calls, 71% on MAM-enrolled cohort, unrecognized "MobileApplicationManagement" policy metadata | Doggett: Compare policy schema v1.8 vs. v1.9; identify field drift. Scully: cross-check MAM tenant bulk-assign window (Jun 4 22:00–Jun 5 08:00 UTC). |
| 3 | CRITICAL | Notification channel delivery failure post-auth failure | Tray icon, toast, and badge delivery errors (634, 635, 636) spiking in auth-failed cohort; offline cache not populated due to early auth fail | Skinner: classify as cascade vs. independent; confirm 5-minute lag correlation between auth fail and notification spike. Doggett: implement offline policy cache priming during install. |
| 4 | HIGH | Play Store rollout velocity vs. sideload/MAM channels — new device adoption imbalance | +11.3% Play Store, +0.8% sideload, -2.1% direct MAM; new devices on Play Store seeing 3.2x higher auth fail rate (likely stale cache or delayed store sync) | Scully: segment error rates by install source; assess Play Store staged rollout percentages. Doggett: verify cache invalidation for Play Store updates. |
| 5 | MEDIUM | PKI cert renewal approaching; tunnel latency trending upward | PKI health nominal but renewal window opens in 6 days; tunnel p95 latency +340ms, may correlate with auth timeout thresholds | Skinner: flag PKI renewal for Mulder; coordinate with Windows/Mac teams on cert timing. Scully: monitor tunnel metrics during auth regression (p50/p95 spread widening). |

---

## 🔥 Cross-Domain Correlation Analysis

**Primary Correlation Chain:** Android v6.2.1 OAuth Token Validation → APS Policy Fetch Failure → Notification Delivery Blackout

**Timeline:**
- **2026-06-04 18:30 UTC:** Play Store rollout of v6.2.1 begins; 2.1K devices in first 2 hours, staggered deployment.
- **2026-06-04 22:15 UTC:** First auth error spike (401/403) detected in Kusto; 0.3% of v6.2.1 cohort (6 devices). OAuth token refresh loop showing repeating failures.
- **2026-06-04 23:45 UTC:** APS policy deliver requests begin failing; "SuccessSettingsNotFound" response code surfaces. Correlation with v6.2.1 identified.
- **2026-06-05 02:30 UTC:** Notification channel errors (634, 635, 636) spike; lag from auth failure is ~3.5 hours (likely cache exhaustion + offline fallback not triggered).
- **2026-06-05 08:00 UTC:** Fleet error volume reaches 2.18B cumulative; v6.2.1 error rate now 145x v6.0.8 baseline.
- **2026-06-05 12:00 UTC (NOW):** Rollout paused; investigating hotfix. v6.2.1 users unable to update policy or receive notifications; client is in "frozen" state.

**Evidence:**
- Kusto query (auth table): v6.2.1 cohort 97.2% of all 401/403 errors in past 24h (8.2K errors vs. 278 from v6.0.8).
- APS telemetry: policy success rate dropped 31.2 percentage points, correlating exactly with v6.2.1 rollout window.
- AppInsights: notification delivery error codes (634/635/636) spike 89 minutes after auth failures reach 50% of v6.2.1 cohort. Cross-device correlation: 96% of notification failures are in auth-failed devices.
- Device telemetry: 47.2% of all fleet errors in past 7d come from v6.2.1 (3.2% of population but 47% of errors).

**Validation Steps:**
1. ✅ **Confirm OAuth cert pinning mismatch:** AppInsights stack traces from auth failures; check if SSL certificate chain changed or OIDC endpoint drift. (Doggett — in progress)
2. ⏳ **Confirm token refresh loop exponential backoff:** Kusto session logs; measure time-to-first-success or permanent failure for 10-minute window post-install. (Doggett — pending)
3. ⏳ **Isolate MAM schema drift:** Compare policy schema metadata in v6.2.0 vs. v6.2.1 client code; identify if "MobileApplicationManagement" field is optional vs. required. (Doggett — pending)
4. ⏳ **Simulate offline cache behavior:** Reproduce auth failure → offline cache read scenario in lab; confirm notification channel fallback chain. (Doggett — pending)
5. ⏳ **Play Store vs. direct deployment comparison:** Segment error rates by install source; confirm if Play Store's delayed sync or stale binary cache is amplifying error rates. (Scully — pending)

---

## 📊 Data Quality Notes

- **Telemetry Source:** Kusto (NaasProd @ idsharedwus), AppInsights (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c), Aria Kusto (f0eaa94222894be599b7cd0bc1e2ed6f)
- **Completeness:** Active client count at 612K (down from expected 670K due to June 5 AppInsights buffer delay; estimate ~10% of cohort still ingesting). Telemetry lag <5 minutes for Kusto, <2 minutes for AppInsights exceptions.
- **Schema & Observations:**
  - APS "SuccessSettingsNotFound" is a legacy response code; may indicate schema versioning issue or stale client cache not refreshed.
  - Notification error codes 634–636 are non-standard; cross-reference against client source to confirm they map to expected channel delivery lifecycle stages.
  - MAM enrollment metadata availability is sparse; segmenting by enrollment status requires fuzzy matching on policy origin.
- **Open Questions:**
  - Should we track Play Store vs. sideload/MAM channel adoption separately in the daily report? (Currently aggregated; risk of signal loss if channels have different client versions.)
  - Android OS version split health tracking — do we expect error rates to vary by Android API level? (Currently unsegmented; may hide OS-specific regressions.)
  - Device model/OEM error variance — reportable signal or noise? (Preliminary data: Samsung and Google Pixel show 0.2% auth failure rate; Motorola/OnePlus at 6.1% — suggests locale/OEM firmware impact.)

---

## Contributors

Mulder, Scully, Doggett, Skinner

**Timestamp:** 2026-06-05 (Friday, June 5, 2026)  
**Report Assembled By:** Reyes (Report Writer)
