# NAAS Android Client Stability — 2026-06-03 → 2026-06-10
**Author:** Frohike (Play Vitals Analyst), automated via `tools/report_generator/sections/frohike_play_vitals.py`
**Source:** Google Play Developer Reporting API v1beta1 (service-account auth)
**Package:** `com.microsoft.scmx`
**Live Play Store version (per Langly):** `1.0.9003.0101`
**NAAS attribution predicate (issue-cluster level):**
```text
NAAS predicate: lower(cause || ' ' || location) contains any of
  vpnserviceorchestrator, com.microsoft.scmx.vpn, com.microsoft.intune.vpn, features.consumer.vpn, features.naas, baseopenvpnclient, openvpn, libnaas, naas, tunnel, vpn
→ 15 NAAS issues identified
```

---

## 1. Headline + Per-Version Table (mirrors report section)

### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit, 7d `2026-06-03 → 2026-06-10`)

| Metric | Value | Denominator | Readout |
|---|---|---|---|
| NAAS crash reports (7d in-window) | **14** | Sum of `errorReportCount` over 15 NAAS-attributed issue clusters | 15 NAAS issues identified |
| NAAS ANR reports (7d in-window) | **2** | Same | ANR long-tail concentrated in OpenVPN init |
| Affected users (upper bound) | **5** | Sum of `distinctUsers` across 15 NAAS issues (NOT cross-issue deduped) | True unique-user count is lower |
| **App user-perceived crash rate (whole-app, 7d, user-weighted)** | **0.7237%** | All `com.microsoft.scmx` Android sessions in window | ✅ Below Google bad-behavior threshold 1.09% |
| **App user-perceived ANR rate (whole-app, 7d, user-weighted)** | **0.2574%** | Same | ✅ Below Google bad-behavior threshold 0.47% |
| Δ crash rate vs prior 7d | **0.7237% vs 0.7377%** (-0.014pp / -1.9% rel) | App-level | ⬇️ Down |
| Δ ANR rate vs prior 7d | **0.2574% vs 0.2526%** (+0.005pp / +1.9% rel) | App-level | ⬆️ Uptick |
| Tenant attribution | **Not derivable from Play** | — | Play Vitals exposes no tenant cut — use Scully for tenant slicing |

> **Denominator framing rule:** "NAAS crash/ANR" are **counts**, not rates. Play does not publish a NAAS-using-session denominator; only Scully's `TunnelServerOperationEvents` carries it. The two user-perceived rates above are app-wide, NOT NAAS-only.

### Per-Defender-version NAAS table (PRIMARY)

| Defender version | NAAS Crashes | NAAS ANRs | App CR% (7d) | App ANR% (7d) | Users 7d | Notes |
|---|---:|---:|---:|---:|---:|---|
| `1.0.7513.0101` | 7 | 1 | 0.0000% | 0.0000% | 60 |  |
| `1.0.7609.0102` | 6 | 0 | n/a — sub-threshold | n/a | <500 |  |

### Top NAAS crashes (top 3; full root-cause depth in Frohike's drop)

| # | Cluster cause / location | 7d reports | Affected users | Root-cause hypothesis |
|---:|---|---:|---:|---|
| 1 | `Unknown Source - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand` / `android.app.StackTrace` | **13** | 2 | See drop file (`3e11c004ac…`) |
| 2 | `SourceFile - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand` / `android.app.StackTrace` | **1** | 1 | See drop file (`e216e51099…`) |
| 3 | `Unknown Source - com.microsoft.scmx.features.consumer.vpn.d.get` / `java.lang.IllegalStateException` | **0** | 0 | See drop file (`33611ed498…`) |

### Top NAAS ANRs (top 3; full table in Frohike's drop)

| # | Cluster cause / location | 7d reports | Affected users | Root-cause hypothesis |
|---:|---|---:|---:|---|
| 1 | `Native method - android.os.MessageQueue.nativePollOnce` / `Executing service com.microsoft.scmx/.vpn.VpnServiceOrchestrator` | **2** | 2 | See drop file (`aeb5c10af4…`) |
| 2 | `unavailable - com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize` / `ANR triggered by main thread waiting for too long` | **0** | 0 | See drop file (`868ca86b7a…`) |
| 3 | `unavailable - com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize` / `ANR triggered by slow operations in main thread` | **0** | 0 | See drop file (`6ab4dc76a1…`) |

### Affected users / regions

- **Affected NAAS users (upper bound):** 5 over 7d (across 15 NAAS issues, not deduplicated cross-issue).
- **🔴 Germany whole-app crash rate: 3.5144%** — OVER Google's 1.09% Play Console bad-behavior threshold.
- **EU aggregate (whole-app, 7d, user-weighted): 1.491% vs non-EU 0.458% — 3.3× lift.**
- Caveat: country-level rates are whole-app, NOT NAAS-only. EU correlation with Scully's NAAS server-side EU intensification is **same-shape** but Play cannot prove NAAS-attribution at country level — Scully NAAS-tenant-by-region cut still owed.


---

## 2. Top NAAS issues — full detail

### Crashes

#### 1. `3e11c004ac1da2e009d8395ae8c47ec0`
- **Cause:** `Unknown Source - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand`
- **Location:** `android.app.StackTrace`
- **7d reports:** 13
- **Affected users (issue-local):** 2

#### 2. `e216e51099939b7421de40c9c34e002b`
- **Cause:** `SourceFile - com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand`
- **Location:** `android.app.StackTrace`
- **7d reports:** 1
- **Affected users (issue-local):** 1

#### 3. `33611ed4982975669064e6e7891f6d6f`
- **Cause:** `Unknown Source - com.microsoft.scmx.features.consumer.vpn.d.get`
- **Location:** `java.lang.IllegalStateException`
- **7d reports:** 0
- **Affected users (issue-local):** 0

#### 4. `4d2847836aab29fb4e92a5207a559326`
- **Cause:** `[base.apk!libnaas_native_vpn.so]`
- **Location:** `SIGSEGV`
- **7d reports:** 0
- **Affected users (issue-local):** 0

### ANRs

#### 1. `aeb5c10af4632311f9b31c78432fabae`
- **Cause:** `Native method - android.os.MessageQueue.nativePollOnce`
- **Location:** `Executing service com.microsoft.scmx/.vpn.VpnServiceOrchestrator`
- **7d reports:** 2
- **Affected users (issue-local):** 2

#### 2. `868ca86b7a9b6b19278fbe252f496d30`
- **Cause:** `unavailable - com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize`
- **Location:** `ANR triggered by main thread waiting for too long`
- **7d reports:** 0
- **Affected users (issue-local):** 0

#### 3. `6ab4dc76a10f6b8ec8524f4c1f020cf1`
- **Cause:** `unavailable - com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize`
- **Location:** `ANR triggered by slow operations in main thread`
- **7d reports:** 0
- **Affected users (issue-local):** 0

#### 4. `6056db512c32b4370dd8325264e3a503`
- **Cause:** `unavailable - com.microsoft.intune.vpn.g.c`
- **Location:** `ANR triggered by thread waiting for a binder transaction`
- **7d reports:** 0
- **Affected users (issue-local):** 0

#### 5. `5af926fa89de385b6e3cb2e0cf774633`
- **Cause:** `unavailable - com.microsoft.scmx.features.consumer.vpn.f.get`
- **Location:** `ANR triggered by slow operations in main thread`
- **7d reports:** 0
- **Affected users (issue-local):** 0

---

## 3. Country breakdown (whole-app rate, top 25)

| Country | App CR% (7d) | Users 7d |
|---|---:|---:|
| CY | 4.1150% | 80 |
| ZM | 3.9200% | 50 |
| DE | 3.5144% | 7,000 |
| GE | 3.2300% | 60 |
| RS | 2.9889% | 80 |
| MK | 2.1003% | 90 |
| HU | 1.8522% | 400 |
| JO | 1.8200% | 60 |
| NO | 1.7604% | 400 |
| SG | 1.6192% | 400 |
| IL | 1.5183% | 500 |
| EG | 1.5158% | 200 |
| CR | 1.5049% | 200 |
| CZ | 1.4683% | 400 |
| GR | 1.4484% | 300 |
| DO | 1.3539% | 200 |
| RO | 1.2533% | 200 |
| UA | 1.2136% | 100 |
| SK | 1.1903% | 100 |
| TR | 1.1800% | 1,000 |
| TW | 1.1656% | 200 |
| BG | 1.1140% | 300 |
| AE | 1.1084% | 300 |
| MY | 1.0530% | 700 |
| SV | 1.0200% | 50 |

---

## 4. Raw API payload manifest

- `date` (size: 10)
- `window` (size: 5)
- `freshness` (size: 1)
- `crash_rate_7d` (size: 1)
- `crash_rate_prior_7d` (size: 1)
- `anr_rate_7d` (size: 1)
- `anr_rate_prior_7d` (size: 1)
- `error_counts_by_issue_version` (size: 2)
- `error_issues` (size: 2)
- `crash_rate_by_country` (size: 1)
