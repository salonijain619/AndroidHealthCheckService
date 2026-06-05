# Defender for Android — GSA Module Discovery Plan

**Author:** Doggett (Android Engineer)
**Date:** 2026-06-05T17:30:52+05:30
**Repo (target, auth-restricted):** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android
**Status:** HYPOTHESIS — repo not yet readable from this environment.

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
