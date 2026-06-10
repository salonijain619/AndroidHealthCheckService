# Android Telemetry Data Model — Reference

**Author:** Doggett (Android Engineer)
**Date:** 2026-06-05
**Audience:** Reyes (report writer), Skinner (severity), Mulder (review), Scully (telemetry cross-check)
**Purpose:** Single-page mental model of how GSA-on-Defender-Android telemetry flows from device to dashboard. Cite this when writing report sections; cite the source files for deep-dives.

---

## TL;DR

```
Device code (Kotlin/Java)
   │  MDAppTelemetry.trackEvent(EventName, EventProperties [, Flags.CRITICAL])
   │  MDAppTelemetry.trackEventException(EventName, throwable)
   ▼
┌──────────────────────────────────────────────────────────────────┐
│ Backend split (by event class, not by feature):                  │
│   • Defender events    → 1DS                                     │
│   • Tunnel events      → Aria                                    │
│ Always-appended props: AndroidId, TelemetryCorrelationId,        │
│   Persona, EnrollmentType, SessionIdTenantId, TenantIdPII,       │
│   MachineId, TenantLicenseType, TenantOrgName (if allowSensitive)│
└────────────┬──────────────────────────────────────┬──────────────┘
             ▼                                      ▼
   ADX: mdatpandroidcluster.westus2          Aria: prod DB
        / MDATPAndroidDB                          f0eaa94222894be599b7cd0bc1e2ed6f
        / customEvents (raw, JSON props)          (mnap_xplat_telemetry*,
             │                                     filter: App_Platform == 'Android')
             │ Update policies (one per subtable)
             │ | where name in (...) | evaluate bag_unpack(EventProperty)
             ▼
   10 domain subtables (each event lives in exactly ONE):
     1.  TelemetryMalwareScan         (76  evts ~1.45B/7d)  Scan*, Threat*, ML*
     2.  TelemetryAuth                (41  evts ~1.25B/7d)  SignIn*, Auth*, MSAL*, Token*, PRT*
     3.  TelemetryCompliance          (63  evts ~1.15B/7d)  MAM*, TVM*, Enrollment*, EDR registration
     4.  TelemetryVPNAndWebProtection (96  evts ~1.5B/7d)   Vpn*, Tunnel*, Naas*, Edge*, LDNS*, Antiphishing*  ◀── GSA
     5.  TelemetryAppLifecycle        (89  evts ~1.05B/7d)  App*, Service*, Onboarding*, Permission*, FRE/EULA
     6.  TelemetryHeartbeat           (16  evts ~800M/7d)   Heartbeat*, EdrHeartbeat*
     7.  TelemetryNetworkMonitoring   (29  evts ~580M/7d)   Network*, Wifi*, CA*, Trusted*
     8.  TelemetryConfiguration       (12  evts ~460M/7d)   ECS*, Config*, Feature*, Admin*       ◀── flag rollouts
     9.  TelemetryProductHeartbeat    (1   evt  ~1.8M/7d)   ProductHeartbeat (isolated)
     10. TelemetryGeneral             (209 evts ~820M/7d)   catch-all (UI, billing, ITP, upsell)
             │
             │ Optional layer (developer-authored Python configs)
             ▼
   Aggregated tables in "dashboard" folder
   (KustoQueryFunc Azure Function, hourly, hoursSinceEpoch % interval == 0)
             │
             ▼
   Alerts in "alerts" folder (AlertResults table)
```

---

## Where GSA signal lives — the routing cheat-sheet

| Signal class | Subtable (1DS / ADX) | Aria fallback |
|---|---|---|
| Tunnel start / stop / state | `TelemetryVPNAndWebProtection` (`Tunnel*`, `Vpn*`, `Naas*`) | `mnap_xplat_telemetry*` w/ `App_Platform == 'Android'` |
| Auth (MSAL, PRT, token acquisition) | `TelemetryAuth` (`MSAL*`, `Auth*`, `Token*`, `SignIn*`, `PRT*`) | same |
| Edge / web-protection integration | `TelemetryVPNAndWebProtection` (`Edge*`, `LDNS*`, `Antiphishing*`, `CaptivePortal*`) | n/a |
| ECS / feature-flag evaluation | `TelemetryConfiguration` (`ECS*`, `Config*`, `Feature*`, `Admin*`) | n/a |
| App / service lifecycle (foreground-service kills, onboarding, permissions) | `TelemetryAppLifecycle` | n/a |
| Heartbeat health | `TelemetryHeartbeat` + `TelemetryProductHeartbeat` | n/a |
| Exceptions (`trackEventException`) | Routed by event name like any other event | same |
| Server-side tunnel events (Roxy / Talon / Cert) | NOT in MDATPAndroidDB — `naas-idsharedscus / NaasProd` | n/a |

**Always-on dimensions** (in addition to event-specific props after `bag_unpack`):
`name`, `timestamp`, `AndroidId`, `TelemetryCorrelationId` (correlate request → response chain), `Persona`, `EnrollmentType`, `SessionIdTenantId`, `TenantIdPII`, `MachineId`, `TenantLicenseType`, `TenantOrgName` (sensitive — gated). Add **`ClientVersion`** (4-segment `1.0.NNNN.NNNN`, per Scully) as the canonical version pivot — present on every row by virtue of being part of common properties.

---

## Pre-aggregated tables vs. ad-hoc queries

**Use pre-aggregated tables when:**
- A metric is checked daily or by dashboards.
- Volume is high (Tunnel / Auth events are 1B+ per 7d).
- The aggregation is deterministic and can be defined as `customEvents | where ... | summarize ...`.

**Author one** by adding a `.py` file under `libraries/AggregatedTables/` in the Android repo with `aggregation_config` + `kql_query`. Mandatory fields: `name`, `version` (`"MAJOR.MINOR"`, bump on schema change), `interval` (hours; one of `{6, 12, 24, 48, 72, 168, 720}`), `targetTable`, `schema` (list of `{"name", "type"}`). The hourly `KustoQueryFunc` Azure Function ingests via `.set-or-append` server-side. Validation at PR time via `ValidateAggregationConfig.py` + `ValidateKqlQueryADX.py` (live ADX). See `agent-docs/AggregatedTableInfra.md`.

**Use alerts when:**
- A condition should auto-fire when crossed (static: operator + threshold) or anomalous (dynamic: `series_decompose_anomalies`).
- Author under `libraries/Alerts/*.py` with `alert_config` + `alert_query`. `evaluationFrequency` restricted to `PT6H | PT12H | PT24H/P1D | PT48H/P2D`. Outputs land in the `AlertResults` table in the `"alerts"` folder.

---

## Event-naming + property-naming rules (enforced)

- **PascalCase only.** No `snake_case`, no `camelCase`. (`agent-docs/Telemetry.md`)
- **Names + property keys must come from codegen'd Kotlin classes in `WD.Mobile.Xplat.Infra`.** Hardcoded string constants are a PR-blocking violation.
- **PII discipline.** `TenantOrgName` gated on `allowSensitiveData`. `UserInfo_Id` is access-restricted in Aria and returns HTTP 400 on join — never use it (confirmed in marketplace findings).
- **Flags.** `Flags.NORMAL` (default) vs `Flags.CRITICAL` (immediate-attention events — security threats, severe failures).

---

## Querying patterns — for Scully / report sections

```kql
// 1. Tunnel-state distribution for the last 24h, by ClientVersion
TelemetryVPNAndWebProtection
| where timestamp > ago(24h)
| where name == "VpnClientState"
| summarize Count = count() by ClientVersion, State = tostring(EventProperty.State)
| order by ClientVersion desc, Count desc

// 2. Auth failure rate by version (regression-hunt baseline)
TelemetryAuth
| where timestamp > ago(7d)
| extend IsFailure = name in ("SignInFailed", "TokenAcquireFailed", "MSALError")
| summarize Total = count(), Failures = countif(IsFailure) by ClientVersion, bin(timestamp, 1d)
| extend FailureRate = todouble(Failures) / Total
| order by ClientVersion desc, timestamp desc

// 3. Feature-flag evaluation distribution (catches "flag flipped in version X")
TelemetryConfiguration
| where timestamp > ago(7d)
| where name in ("FeatureEvaluated", "ECSConfigRefresh")
| summarize Count = count() by ClientVersion,
    FeatureName = tostring(EventProperty.FeatureName),
    Value = tostring(EventProperty.Value)
| order by ClientVersion desc, Count desc

// 4. Find unmapped events (catch-all / new events not yet routed)
customEvents
| where timestamp > ago(7d)
| where name !in (/* known event list */)
| summarize Count = count() by name
| order by Count desc
```

All four are **starter queries** — column names like `EventProperty.State` are illustrative; verify exact property names via `customEvents | where name == "..." | evaluate bag_unpack(EventProperty) | take 1` first.

---

## Source-file pointers (deep-dive)

| Topic | Path |
|---|---|
| Telemetry conventions, MDAppTelemetry API, PascalCase, codegen requirement | `WD.Client.Android-icm-copilot/agent-docs/Telemetry.md` |
| 10-subtable architecture, update policies, routing rules | `WD.Client.Android-icm-copilot/agent-docs/TelemetrySubtables.md` |
| Full 632-event → subtable mapping with 7d volumes | `WD.Client.Android-icm-copilot/agent-docs/TelemetryNewTable.md` |
| Aggregated tables infra (Python configs, Azure Function, manifest, validation, schema evolution) | `WD.Client.Android-icm-copilot/agent-docs/AggregatedTableInfra.md` |
| Feature flags (EcsManager, ConfigUtils, 6-layer pattern, ECS_CONFIG_REFRESH subscriber, cleanup agent) | `WD.Client.Android-icm-copilot/agent-docs/FeatureFlags.md` |
| Build prerequisites, init scripts, gradle targets, ABI filters | `WD.Client.Android-icm-copilot/agent-docs/BuildSteps.md` |
| Coding standards (SOLID, Hilt/Dagger, MAM/MDM, lifecycle) | `WD.Client.Android-icm-copilot/agent-docs/CodingStandards.md` |
| Unit-test patterns, MockK telemetry mocking idiom, banned PowerMock | `WD.Client.Android-icm-copilot/agent-docs/Testing.md` |
| Cross-platform Kusto routing + identity rules (Client_Id, DeviceInfo_Id, UserInfo_Id ban) | `Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-client-telemetry-toolkit/SKILL.md` |
| Aria platform filter, server-side tunnel routing (SCUS vs WUS), PKI routing | same |
| Verified ClientVersion format + canonical `DeviceOs has_cs 'ANDROID'` filter | `.squad/skills/android-kusto-starter/SKILL.md` |

---

**Use this doc as the routing map; cite the source files when a report section needs depth.**
