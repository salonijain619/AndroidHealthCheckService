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
