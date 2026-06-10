# Defender for Android — GSA Module Discovery Plan

**Author:** Doggett (Android Engineer)
**Date:** 2026-06-05T17:30:52+05:30
**Repo (target, auth-restricted):** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android
**Status:** HYPOTHESIS — repo not yet readable from this environment. **Partially unblocked 2026-06-05** by the `Identity-gsa-client-marketplace` clone — see "Marketplace Discovery (2026-06-05)" section near the end of this file for what was resolved vs. what is still blocked.

## Access attempts (what I tried, what happened)

1. **Direct web_fetch of VSTS repo root** → returned an anonymous sign-in stub
   (`[Anonymous] [Sign out]`). No HTML tree, no file listing. VSTS requires
   interactive Entra auth; no usable content is reachable without credentials
   or an ADO MCP/PAT.
2. **GitHub code search** for distinctive GSA/Defender identifiers
   (`GlobalSecureAccess Android Defender`, `SuccessSettingsNotFound GSA`,
   `WD.Client.Android GsaTunnel`) → **0 results** across all three queries.
   No public mirror of the repo exists; nothing scrape-able from GitHub.
3. **No Azure DevOps / VSTS MCP** is registered in this environment, so we
   cannot list refs, fetch blobs, or run pipelines from here.

**Net:** Everything below the access section is structured hypothesis.
We need Saloni (or any teammate with VSTS read) to either grant access,
paste file listings, or run the grep patterns below and return results.

---

## a. Existing assets to inventory (file patterns to run against the repo)

Reusable squad infrastructure may already exist inside WD.Client.Android.
Before we build anything new, run these patterns and report hits:

### Squad / agent definitions
- `**/squad.agent.md`
- `**/.squad/**` (any directory tree)
- `**/.ai-team/**`
- `**/agents/*/charter.md`
- `**/agents/*/history.md`
- `**/AGENTS.md`, `**/AGENT.md`

### Skills
- `**/.copilot/skills/**`
- `**/skills/*/SKILL.md`
- `**/skills/*/skill.yaml`
- `**/.github/skills/**`

### Plugins / extensions
- `**/plugins/**`
- `**/.copilot/plugins/**`
- `**/extensions/**` (filter for Copilot/agent-related, not Android lib extensions)
- In any root-level `package.json`: look for `"squad"`, `"copilot"`, `"agents"` keys
- In any root-level `*.csproj` / `build.gradle*`: look for tooling deps named `*copilot*`, `*squad*`

### Copilot instructions
- `.github/copilot-instructions.md`
- `**/copilot-instructions.md`
- `**/.github/instructions/**`
- `**/CLAUDE.md`, `**/GEMINI.md` (other AI agent guides occasionally co-exist)

### Telemetry helpers
- Filenames matching `*Telemetry*`, `*Logger*`, `*Aria*`, `*AppInsights*`,
  `*OneDS*`, `*Diagnostic*Event*`
- Constants files: `*EventName*`, `*EventNames*`, `*TelemetryEvents*`
- Look specifically for an `enum class` or `object` listing event-name strings —
  that is what we will map error codes back to.

### Crash / ANR reporting
- `*Crash*`, `*Anr*`, `*Breakpad*`, `*Tombstone*`, `*StackTrace*`
- AppCenter / Firebase Crashlytics integration files (`*Crashlytics*`,
  `*AppCenter*`)
- Custom Defender crash uploader (likely OneDS or in-house)

### KQL / dashboards in source
- `**/*.kql`
- `**/*.csl`
- `**/dashboards/**`
- `**/queries/**`
- `**/*.workbook` / `**/*.workbook.json` (Azure Workbooks definitions)

---

## b. GSA module location hypothesis (within WD.Client.Android)

Defender for Android is a large multi-module app. GSA was integrated rather
than shipped as a standalone APK. Likely subfolder candidates:

- `app/src/main/java/**/gsa/**`
- `app/src/main/java/**/globalsecureaccess/**`
- `app/src/main/java/**/network/tunnel/**`
- `app/src/main/java/**/network/vpn/**` (Android VPNService-based tunnel)
- `app/src/main/java/**/auth/conditionalaccess/**`
- `app/src/main/java/**/auth/entra/**`
- A dedicated module: `modules/gsa/`, `features/gsa/`, `gsa-client/`
- Kotlin package patterns: `com.microsoft.scmx.gsa.*`,
  `com.microsoft.scmx.features.gsa.*`,
  `com.microsoft.intune.mam.* + GSA` cross-cutting

**Grep-anywhere fallback:** case-insensitive search for `gsa`, `globalsecureaccess`,
`global_secure_access`, `entra.*tunnel` across the full tree, then filter out
generic VPN/Intune false positives.

**AndroidManifest hints to capture:**
- Any `<service>` that extends `android.net.VpnService` — that is the tunnel entry.
- Any `<receiver>` for `BOOT_COMPLETED` / package replacement — restart logic.
- `android:foregroundServiceType="..."` declarations (Android 14+ rules apply).

---

## c. Android-specific report fields to propose

These do not exist in the Windows report because they are Android-platform
realities. **Each is a PROPOSAL — confirm value and feasibility with Saloni /
dashboard owners before adding to the daily report.**

| # | Proposed Field | Why Android-specific | Status |
|---|----------------|---------------------|--------|
| 1 | **Install channel: Play Store vs sideload vs MAM/Intune-managed** | Enterprise rollout patterns differ wildly; sideload skews crash/version distribution | PROPOSAL — confirm with Saloni |
| 2 | **Android OS API level distribution (e.g., API 31 / 33 / 34 / 35 buckets)** | VPNService, foreground service, and Doze rules all changed across these levels; regressions often cluster by API | PROPOSAL — confirm with Saloni |
| 3 | **Device OEM / manufacturer mix (Samsung / Pixel / Xiaomi / other)** | OEM-specific battery managers (Samsung, Xiaomi, OnePlus) aggressively kill VPN services; known industry issue | PROPOSAL — confirm with Saloni |
| 4 | **Battery optimization / Doze-mode kill rate** | VPN-based clients silently die when Doze restrictions apply; Android-only failure mode with no Windows analog | PROPOSAL — confirm with Saloni |
| 5 | **Foreground service notification health (Android 14+)** | Android 14 enforces strict `foregroundServiceType` declarations; missing or wrong type triggers `ForegroundServiceDidNotStartInTimeException` | PROPOSAL — confirm with Saloni |
| 6 | **Work profile (managed) vs personal profile split** | GSA-in-Defender often runs in work profile via Intune; failure rates and policy delivery differ between profiles | PROPOSAL — confirm with Saloni |
| 7 | **Defender app version × GSA module version pairing** | GSA is shipped inside Defender — a Defender update can carry an unintended GSA change | PROPOSAL — confirm with Saloni |

---

## d. Android equivalents of Windows error codes (open questions)

Windows report references: error **505** (auth), **631 / 632** (tray icon),
APS **SuccessSettingsNotFound**.

| Windows Code | Surface on Windows | Hypothesized Android Equivalent | Notes |
|--------------|--------------------|---------------------------------|-------|
| 505 | Client auth failure | Likely **same numeric code** server-side (shared APS/CA backend). Client-side it surfaces as MSAL/`AcquireToken*` failure, broker-app error, or Entra `AADSTS*` code | Validate by grepping for `505` constant or MSAL exception handlers in GSA module |
| 631 / 632 | System tray icon state | **No direct analog** — Android has no tray. Closest equivalents: (a) persistent foreground-service notification missing/dismissed, (b) `NotificationChannel` disabled by user, (c) tunnel `VpnService` not in `STATE_CONNECTED` while UI thinks it is | Propose new Android code(s) for "tunnel UI/state divergence"; needs design conversation |
| APS `SuccessSettingsNotFound` | Policy fetch returned success but no settings payload | **Likely identical server-side string** since APS is shared. Client-side handling differs: Android probably logs to OneDS/Aria with the same event name. Worth confirming the exact event name token used in the Kotlin telemetry helper | Cross-check with Scully's Kusto event names |

**Open questions to resolve once we have repo access:**
1. Does Android emit the literal string `SuccessSettingsNotFound`, or an
   Android-renamed equivalent (`PolicyEmptyResponse`, etc.)?
2. Is there an Android-only code for tunnel-state-divergence we should
   surface in the report?
3. Are MSAL broker failure codes (e.g., from Authenticator/Company Portal)
   bucketed under 505 or kept distinct?

---

## What needs to happen next

This plan is unblocked only when we can read the repo. See the
"What Doggett Needs From Saloni" punch list below.

---

## What Doggett Needs From Saloni (punch list)

1. **VSTS read access** to `microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android`
   — either an org-level grant, a PAT scoped to Code (Read), or simply
   pasting the output of the grep patterns in section (a) for now.
2. **Pointer to the GSA module's root path** within the repo
   (so we don't have to grep the whole tree to find it).
3. **Directory listings** for `.squad/`, `.copilot/`, `.ai-team/`, `agents/`,
   `skills/`, `plugins/` if any exist at repo root or under `tools/`.
4. **Name of the Android team's telemetry helper class** (likely something
   like `TelemetryLogger`, `AriaLogger`, `OneDSLogger`, or
   `ScmxTelemetryClient`) so we know what symbol to grep for.
5. **Confirmation of which crash reporter is wired up** (OneDS? AppCenter?
   Firebase Crashlytics? In-house?) — drives where we look for crash signal.
6. **Whether KQL queries / Azure Workbook JSON are checked into the repo**
   under `dashboards/` or `queries/` — these are reusable for Scully.
7. **Sign-off** (with Mulder) on the seven proposed Android-specific report
   fields in section (c) before we ask Reyes to add them to the template.

---

## Marketplace Discovery (2026-06-05)

A second VSTS asset became available locally: `Identity-gsa-client-marketplace` (`gsa-client-plugins`), the **plugin marketplace for the GSA / NaaS client** (Win32, macOS, Android, iOS). Cloned at `/Users/salonijain/workspace/Identity-gsa-client-marketplace/`. Full inventory in `.squad/agents/doggett/research/marketplace-plugin-inventory.md`. This section records what that clone resolved versus what stays blocked behind WD.Client.Android.

### Resolved (no longer hypothesis)

- **Android telemetry pipeline confirmed.** GSA Android client behavior is queried from App Insights cluster `android-appinsights`, database `wd-prod-android-client` — explicitly **NOT Aria**. iOS uses the parallel Defender-owned `ios-mdatp / MDATPiOSDB`. Source: `plugins/gsa-client-telemetry-toolkit/skills/gsa-client-telemetry-toolkit/SKILL.md` line 96. The `wd-prod-` prefix corroborates Saloni's framing that GSA Android lives inside Defender's mobile telemetry stack.
- **Aria platform filter for Android is `App_Platform == 'Android'`** (exact-case string literal) when Android signals appear in shared Aria tables like `mnap_xplat_telemetry*`. Prod Aria DB GUID `f0eaa94222894be599b7cd0bc1e2ed6f` re-confirmed.
- **Cross-platform identity rules apply unchanged to Android.** `Client_Id` is the join/dcount key but rotates on Entra repair/rejoin and can be empty for broken-auth devices; `DeviceInfo_Id` is the stable hardware-derived long-window key; **`UserInfo_Id` is access-restricted in Aria and returns HTTP 400 — never use it for any join, including Android sessions**.
- **`Client_Id → owner` reverse lookup recipe exists** via Microsoft Graph (`/users/{upn}/ownedDevices`, with `operatingSystem` → `App_Platform` mapping) and works for Android. Auth via `az login --scope https://graph.microsoft.com/Device.Read.All --scope https://graph.microsoft.com/Directory.Read.All`. Useful when we have a Client_Id from a crash trace and need the user.
- **Marketplace conventions Squad should mirror.** Plugin layout (`plugins/<name>/.claude-plugin/plugin.json` + `skills/<name>/SKILL.md`), SKILL.md format (KNOW/DO/CHECK/Common Rationalizations/Red Flags, body < 500 lines, frontmatter description ≤ 250 chars), MCP-first / no per-plugin installers, catalog-as-JSON-not-prose, runtime wiki fetch for long references, install via `/plugin marketplace add` + `/plugin install <plugin>@gsa-client-plugins`. The `mcp-setup@gsa-plugins` plugin owns shared MCP-server registration; we should not author our own.
- **Pre-built reusable skills exist.** `gsa-client-telemetry-toolkit` (Kusto routing + identity + Graph) and `setup-prereqs` (bootstrap checklist) — both proposed as **REFERENCE** (link by path, don't copy) since they depend on a sibling catalog and on `gsa-plugins`-side wiki pages and MCP servers we don't yet have wired up. `gsa-kusto-catalog` is being inventoried in parallel by Scully.

### Still blocked (require WD.Client.Android repo access)

The marketplace tells us *where* Android telemetry lands, not *how it is emitted from device*. These items from section (a) of the original plan remain open and unchanged:

- Android telemetry helper class name(s) inside Defender-for-Android (`*Telemetry*`, `*Logger*`, `*EventNames*`, `*OneDS*`, `*AppInsights*`).
- The on-device emitter — OneDS/1DS SDK vs. App Insights direct vs. custom Defender uploader.
- Crash-reporter implementation (Crashlytics / AppCenter / OneDS / in-house Defender) and its event taxonomy.
- Any pre-existing `.squad/`, `.copilot/`, `agents/`, `skills/`, or `plugins/` directories inside WD.Client.Android — the marketplace does not enumerate them. (Note: `Identity-ZTNA-NaaS-Agent` is the GSA *agent* codebase referenced by the toolkit's "Codebase Correlation" wiki, NOT WD.Client.Android.)
- Android-specific KQL / Workbook JSON checked into WD.Client.Android.
- The Android `EventName` constants used by the GSA module (mapping for 505, APS `SuccessSettingsNotFound`, hypothesized 631/632 analog, etc.).
- Defender's existing Android dashboards covering OEM mix, Doze/battery-optimization kill rate, foreground-service notification health, work-profile split, API-level mix.

### Net posture

Reuse-first stance is **partially executable now**: we can cite App Insights routing, identity rules, and Aria filtering immediately by reference path. The code-side discovery — emitter classes, crash reporter, internal squad/skill assets inside WD.Client.Android — still requires VSTS read access to that repo. No on-device inventory has been performed; nothing in the marketplace substitutes for it.

---

## ICM-Copilot Doc Discovery (2026-06-05)

Saloni cloned a sister repo, `WD.Client.Android-icm-copilot`, at `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/`. Its `agent-docs/` directory is the canonical Defender-Android AI-agent doc set (README + 8 reference docs covering telemetry, feature flags, build, coding, testing, aggregated tables). Unblocks most of the pipeline-side discovery questions even without WD.Client.Android source. Source paths cited below are relative to that clone.

### a. Telemetry pipeline architecture — raw → subtables → aggregated

**Three layers, all hosted on the same ADX cluster** (`mdatpandroidcluster.westus2.kusto.windows.net`, database `MDATPAndroidDB`):

1. **On-device emit (Layer 0).** Code calls `MDAppTelemetry.trackEvent(eventName, eventProperties)` / `MDAppTelemetry.trackEventException(...)` with `Flags.NORMAL` or `Flags.CRITICAL`. Two backend channels: **1DS for Defender** events, **Aria for Tunnel** events (`agent-docs/Telemetry.md`). Every event is auto-stamped with `AndroidId`, `TelemetryCorrelationId`, `Persona`, `EnrollmentType`, `SessionIdTenantId`, `TenantIdPII`, `MachineId`, `TenantLicenseType`, and `TenantOrgName` (last is gated on `allowSensitiveData`).
2. **Raw landing — `customEvents` (Layer 1).** All 1DS Defender events land in `MDATPAndroidDB.customEvents` as the source-of-truth raw table. Each event row carries `name`, `timestamp`, and a JSON `EventProperty` blob.
3. **Subtables (Layer 2).** 10 domain-specific subtables fed by Kusto update policies that `| where name in (...) | evaluate bag_unpack(EventProperty)`. `bag_unpack` dynamically materializes per-event property columns — schemas grow automatically as new properties appear. The 10 tables: `TelemetryMalwareScan`, `TelemetryAuth`, `TelemetryCompliance`, **`TelemetryVPNAndWebProtection`** (96 events — where GSA tunnel events live: `Vpn*`, `Tunnel*`, `Naas*`, `Edge*`, `Antiphishing*`, `OpenVpn*`, `LDNS*`, `CaptivePortal*`), `TelemetryAppLifecycle`, `TelemetryHeartbeat`, `TelemetryNetworkMonitoring`, **`TelemetryConfiguration`** (12 events — `ECS*`, `Config*`, `Feature*`, `Admin*`), `TelemetryProductHeartbeat`, `TelemetryGeneral` (catch-all). Each event lives in exactly one subtable. Routing patterns and the full 632-event list are in `agent-docs/TelemetrySubtables.md` + `agent-docs/TelemetryNewTable.md`.
4. **Aggregated tables (Layer 3, optional).** Developers create pre-computed tables in the `"dashboard"` ADX folder by checking in a Python file at `libraries/AggregatedTables/*.py` in the Android repo. A shared **Azure Function `KustoQueryFunc`** (in `WD.Mobile.XPlat.Infra/KustoQueryFunc/`, .NET 8 isolated worker) ingests these via `.set-or-append` server-side every hour (`hoursSinceEpoch % interval == 0`, with `interval ∈ {6, 12, 24, 48, 72, 168, 720}`). Stateless modulo scheduling, 3-layer dedup, orphan cleanup of the `"dashboard"` folder. Full lifecycle in `agent-docs/AggregatedTableInfra.md`.
5. **Alerts (Layer 3.5).** Same engine processes `libraries/Alerts/*.py` configs into an `AlertResults` table in the `"alerts"` folder. Static alerts (operator + threshold) or dynamic alerts (anomaly-detection KQL like `series_decompose_anomalies`).

**Tunnel/Aria caveat.** GSA tunnel-side telemetry rides Aria, not 1DS — so a subset of GSA signal lives outside the 10-subtable model and surfaces in shared Aria tables (`mnap_xplat_telemetry*`, `App_Platform == 'Android'`). This is consistent with the marketplace finding that `wd-prod-android-client` (App Insights) and Aria are *both* in-scope for Android GSA — the device-side emitter routes by event class, not by feature.

### b. Schema conventions — naming + columns

- **Event + property names: PascalCase, enforced.** No snake_case, no camelCase. Must come from **codegen'd Kotlin classes** in the `WD.Mobile.Xplat.Infra` repo (e.g., `EnhancedAEDeviceEnrolmentEventProperties.NAME` for the event name, `EnhancedAEDeviceEnrolmentEventProperties.DynamicEventProperties.IS_ACTIVE_ADMIN_PRESENT` for properties). **Hardcoded string constants are not allowed** (`Telemetry.md` lines 27–32).
- **Event name shape: `<Domain><Verb>` / `<Component><Outcome>`.** Examples: `AppLaunch`, `UserOnboardingStarted`, `FeatureEnabled`, `ErrorOccurred`, `ScanStarted`, `ThreatResolved`, `SignInSuccessful`, `VpnClientState`, `HeartbeatReported`, `NaasTunnelStartRequested` (Naas* events route to `TelemetryVPNAndWebProtection`).
- **Subtable routing is prefix-based.** First-token prefix maps to subtable (e.g., `Naas*` → `TelemetryVPNAndWebProtection`). Add a new event → pick the correct prefix → add to that subtable's update policy → re-validate via `customEvents | where name == 'NewEventName' | evaluate bag_unpack(EventProperty)`.
- **Aggregated table schema discipline.** Python config declares `name`, `version` (MAJOR.MINOR — must bump on schema change), `interval` (hours, restricted set), `targetTable`, `schema` (`[{"name": ..., "type": "string|long|int|real|bool|datetime|timespan|guid|dynamic|decimal"}]`). Version is persisted as the table docstring (`.alter table <name> docstring "version=X.Y"`). Schema evolution rules: add columns = automatic `.alter-merge`; drop columns = automatic `.drop column` with warning; **type changes are never auto-applied — they error and require manual migration**.
- **Managed-folder guard.** All mutating ADX commands check `folder ∈ {"dashboard", "alerts"}` before executing. Tables outside those folders are off-limits to the engine — a clean ownership boundary that we should mirror if we ever introduce squad-managed tables.
- **Retention / sampling.** Not centrally configured per-event; retention is set per-aggregated-table via the optional `retentionDays` field. Raw `customEvents` retention is whatever ADX cluster policy dictates — the docs don't pin a number; assume long enough for the 7d / 30d volume estimates in `TelemetryNewTable.md` (~3.5B 7d events) to be queryable but verify before relying on multi-month windows.

### c. Feature-flag → version mapping — version-regression detection model

**The flag-rollout model is ECS-side, not in-code.** `EcsManager.isFeatureEnabled("FeatureName", default)` queries the ECS (Experimentation Configuration Service) service at runtime. The ECS service evaluates audience predicates that explicitly include — per `FeatureFlags.md` line 11 — **"user type, enrollment, android version, device, tenant etc."** That means a flag can be rolled out to "Android client version ≥ 1.0.NNNN.NNNN" or "API level ≥ 33" or "tenant subset" without any code change.

**Where ClientVersion shows up.** Per Scully's verified finding, every Android telemetry row carries `ClientVersion` in the `1.0.NNNN.NNNN` 4-segment format. Combined with the always-appended `TelemetryCorrelationId`, `Persona`, `EnrollmentType`, `MachineId`, and `TenantIdPII`, we can pivot any error rate **by ClientVersion + flag-evaluation outcome** in the same query.

**Detecting a version-specific regression (Android analog of Windows v2.28.96):**
1. Identify the suspect version `Vx.Y.A.B` from `ClientVersion` distribution + error-rate spike.
2. Find flags that **changed evaluation** between `Vx.Y.(A-1).*` (or `(A).(B-1)`) and `Vx.Y.A.B`. The on-device hint is the `HANDLER_MSG_ECS_CONFIG_REFRESH` subscriber pattern (`FeatureFlags.md` lines 191–235) — feature managers fetch `EcsManager.isFeatureEnabled(...)` on refresh and cache via `AtomicBoolean`. Two ways the new version surfaces a regression: (a) **new audience predicate** (the flag started returning true for that version), or (b) **new code path** gated by an existing flag that the new version now compiles in.
3. Cross-reference with ECS config snapshots (`TelemetryConfiguration` subtable: `ECS*`, `Config*`, `Feature*`, `Admin*` events) — these emit when ECS refreshes or when a feature evaluates. Diff the evaluated-flag set between versions.
4. **Six-layer ECS pattern** (constant → `ConfigUtils` wrapper → `EcsManager` call → cached `AtomicBoolean` → gated logic → tests) tells you where to look in WD.Client.Android once we have repo access. The `ecs-cleanup` agent inside that repo (`.github/agents/ecs-cleanup.agent.md`) is the inverse operation and confirms the layer list.

This pattern is codified as a new skill — see `.squad/skills/android-version-regression-detection/SKILL.md`.

### d. Build / repo conventions — for future spawn work

- **Toolchain:** Java 17 + Android Studio + NDK `25.2.9519653` (exact) + CMake `3.22.1` + Python 3.11 via **`uv`** (not pip directly) + **Conan `1.59.0` exact** (not 2.x) + Rust stable + `cargo-ndk` + Git ≥ 2.0. `local.properties` carries 9+ PAT/API keys (VSTS PAT, Klondike debug, BD, PowerLift, Firebase debug, Aria debug ingestion, Singular x2, lab credentials).
- **Bootstrap:** `./init.sh` or `python3 init.py` (initializes git submodules, Conan deps, codegen, NaaS prerequisites, vcpkg bootstrap, Rust toolchain).
- **Build / test entry points:** `./gradlew assembleDevDebug` (debug), `./gradlew testDevDebugUnitTest` (unit tests). ABI filter defaults to `arm64-v8a;x86_64`. Lint / Checkstyle / Jacoco off by default; PR gates run them regardless.
- **Repo layout markers worth grep'ing for once VSTS access lands:** `libraries/AggregatedTables/`, `libraries/Alerts/`, `pipeline/PRGatePipeline.yaml`, `pipeline/job/AggregatedTableValidation.yaml`, `.github/copilot-instructions.md` (confirmed present in the icm-copilot mirror — likely present upstream), `.github/agents/ecs-cleanup.agent.md`, `.worklog/` (the icm-copilot mirror requires a per-branch workflow file at `.worklog/<git-branch>/<agent>/workflow.md` — a mandated agent-task ledger).
- **Coding conventions:** SOLID + DRY, Hilt/Dagger DI (`@Inject` constructors, EntryPoints for non-Hilt access), event-driven via `MDRxBus` / `HandlerBusEvent`, MAM/MDM/Android-Enterprise/Personal-Profile awareness baked in. UI in Compose with an `MDApplicationTheme` design system; see `agent-docs/FigmaToCode.md` (not read this pass — `MDText`, `MDButton`, `MDTopAppBar` are the named primitives).

### e. Test patterns — telemetry validation

- **Framework stack:** JUnit 4 + **MockK** (Kotlin, required) + Mockito (legacy Java only) + Robolectric + AndroidX test core. **PowerMock is banned.** All unit tests extend `MDBaseUnitTest`.
- **Telemetry-track mocking idiom** (`Testing.md` lines 131–139, 555–564):
  ```kotlin
  mockkStatic(TelemetryUtils::class)
  every { TelemetryUtils.track(any()) } returns Unit
  // ... exercise code under test ...
  verify(exactly = 1) { TelemetryUtils.track(any()) }
  ```
  For combined events: `mockkStatic(CombinedTelemetryUtils::class)` + `every { CombinedTelemetryUtils.trackCombinedEvent(any(), any(), any(), any<EventProperties>()) } returns Unit`.
- **What's verified:** that the right event was fired exactly N times, with the right properties. Combined with `EventProperties` capture (mockk slot), you can assert the property bag shape — useful for regression-guarding "did v1.0.NNNN.NNNN drop a property?".
- **What's NOT verified by unit tests:** subtable routing (that lives in Kusto update policy, validated in ADX via `customEvents | where name == ... | evaluate bag_unpack(EventProperty) | take 10` per `TelemetrySubtables.md`) or aggregation correctness (validated at PR time by `ValidateKqlQueryADX.py --mode syntax|alert|schema` against live ADX). Subtable + aggregation regressions need integration-style checks, not unit tests.

---

## Open-questions close-out (status as of 2026-06-05)

Below: every original "what we need from Saloni" / "still blocked" item, resolved against the new doc set.

### From "What Doggett Needs From Saloni" punch list

| # | Original ask | Status | Source / notes |
|---|--------------|--------|----------------|
| 1 | VSTS read access to WD.Client.Android | **STILL-BLOCKED** | The icm-copilot mirror gives us docs but not source. Code paths inside WD.Client.Android remain unreadable. |
| 2 | GSA module root path within the repo | **PARTIAL** | Not pinned, but the telemetry subtables show GSA-relevant code emits `Vpn*`, `Tunnel*`, `Naas*`, `Edge*` (→ `TelemetryVPNAndWebProtection`) + `MSAL*`, `Token*` (→ `TelemetryAuth`). Code likely lives under `app/src/main/java/**/vpn/**`, `**/tunnel/**`, `**/naas/**`. Confirming exact path still needs VSTS. |
| 3 | Directory listings for `.squad/` / `.copilot/` / `agents/` / `skills/` / `plugins/` | **PARTIAL** | The icm-copilot mirror has `.github/copilot-instructions.md` + a `.worklog/<branch>/<agent>/workflow.md` mandate + `.github/agents/ecs-cleanup.agent.md` (referenced in `FeatureFlags.md`). No `.squad/` or `skills/`. Upstream WD.Client.Android may or may not mirror this set. |
| 4 | Android telemetry helper class name | **RESOLVED** | `MDAppTelemetry` (`trackEvent(name, props, flags?)`, `trackEventException(name, exception)`). `TelemetryUtils.track(...)` + `CombinedTelemetryUtils.trackCombinedEvent(...)` are higher-level wrappers tested via `mockkStatic`. Event names + property keys come from codegen'd Kotlin classes in `WD.Mobile.Xplat.Infra`. |
| 5 | Which crash reporter is wired up | **PARTIAL** | `MDAppTelemetry.trackEventException` is the in-band exception path (1DS for Defender, Aria for Tunnel). Whether a separate Crashlytics / AppCenter / Breakpad uploader is also wired up is not stated in `agent-docs/`. `BuildSteps.md` mentions `FirebaseApiKeyDebug` and `AppCenter`-style keys absent — Firebase likely but unconfirmed. **Still requires repo access.** |
| 6 | KQL / Workbook JSON checked into the repo | **RESOLVED** | Yes — `libraries/AggregatedTables/*.py` carries the KQL alongside its schema, and `libraries/Alerts/*.py` carries alert queries. Both are validated at PR time against live ADX. No raw `.kql` / `.workbook` files mentioned — KQL is embedded in Python configs. |
| 7 | Sign-off on the seven proposed Android-specific report fields | **STILL-BLOCKED** | Needs Saloni + Mulder ack. Doc set neither confirms nor refutes the seven fields. |

### From "Still blocked (require WD.Client.Android repo access)" section

| # | Original blocked item | Status | Notes |
|---|----------------------|--------|-------|
| 1 | Android telemetry helper class name(s) | **RESOLVED** | `MDAppTelemetry`, `TelemetryUtils`, `CombinedTelemetryUtils`, `EventProperties`. |
| 2 | On-device emitter (OneDS vs App Insights direct vs custom Defender uploader) | **RESOLVED** | **1DS for Defender events, Aria for Tunnel events.** Both flow through `MDAppTelemetry`. App Insights `wd-prod-android-client` is the *downstream* App Insights resource fed by 1DS — not a direct on-device emitter. |
| 3 | Crash-reporter implementation + event taxonomy | **PARTIAL** | In-band: `MDAppTelemetry.trackEventException`. Out-of-band crash uploader unconfirmed. |
| 4 | Pre-existing `.squad/` / `.copilot/` / `agents/` / `skills/` / `plugins/` inside WD.Client.Android | **STILL-BLOCKED** | Not enumerated by docs. |
| 5 | Android-specific KQL / Workbook JSON | **RESOLVED** | Lives in `libraries/AggregatedTables/*.py` + `libraries/Alerts/*.py` (KQL embedded in Python). Aggregated outputs go to `MDATPAndroidDB` `"dashboard"` folder; alerts to `AlertResults` in `"alerts"` folder. |
| 6 | Android `EventName` constants for GSA (505, `SuccessSettingsNotFound`, hypothesized 631/632 analog) | **PARTIAL** | We now know the source-of-truth: codegen'd classes in `WD.Mobile.Xplat.Infra` (e.g., `*EventProperties.NAME`). The exact event names for GSA failure modes still need repo grep — but routing tells us they will fall under `Naas*` / `Tunnel*` / `MSAL*` / `Token*` prefixes. |
| 7 | Defender's existing Android dashboards (OEM mix, Doze, foreground-service, work-profile, API-level) | **PARTIAL** | The aggregated-table infrastructure exists and is the *mechanism* by which such dashboards would be built. Whether configs for those specific dimensions exist in `libraries/AggregatedTables/` still needs repo access to enumerate. |

**Net:** 4 RESOLVED, 5 PARTIAL, 4 STILL-BLOCKED. The remaining blockers all reduce to "VSTS read on WD.Client.Android" — no further unblock possible from docs alone.
