# doggett — Learnings

## Project Context (seeded 2026-06-05)
- **Project:** Android GSA Client Service Health Check
- **User:** salonijain619 (Saloni)
- **Stack:** Investigation/SRE squad for the GSA Android client.
- **Client repo:** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android (VSTS-gated; mirror `WD.Client.Android-icm-copilot` cloned locally with `agent-docs/`)
- **Telemetry clusters:** `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Android client, ADX); `naas-idsharedwus` + `naas-idsharedscus` (server-side); `aria-prod` (cross-checks, GUID `f0eaa94222894be599b7cd0bc1e2ed6f`); `androidgsa.eastus.kusto.windows.net / Metric` (perf rollups, unverified).
- **Onboarding doc:** https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **ICM team:** https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- **Report channel:** IDNA GSA → Livesite - Client (Teams), tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
- **Sister squads:** Windows (win_client_investigation_squad), Mac (HarryPotter)

## Summarized history (full content → `history-archive.md`)

### 2026-06-05 — Initial Defender-for-Android discovery [SUMMARIZED]
GSA Android is a module *inside* Microsoft Defender for Android (not a standalone APK). VSTS auth blocker hard. Drafted file-pattern inventory for the Defender repo (squad/agent/skill/plugin defs, telemetry helpers, crash reporters, KQL/dashboards). Proposed 7 Android-specific report fields (install channel, API level, OEM, Doze, FG-service notif, work-profile, Defender×GSA version pairing). Hypothesized error-code mapping (505 shared server-side; 631/632 has no Android analog — propose new "tunnel UI vs VpnService state divergence" code; `SuccessSettingsNotFound` likely same token). Wrote `agents/doggett/research/defender-android-discovery.md` + inbox decision `doggett-reuse-defender-assets.md`.

### 2026-06-05T12:00:52Z — Bootstrap complete [SUMMARIZED]
Squad on `claude-opus-4.7`. Report template ready (Reyes). Kusto MCP confirmed against `idsharedwus`. Dashboard `8a1fa78a-…` proposed as canonical source of truth. Decisions: model standardization, report skeleton, dashboard-as-SoT, reuse-Defender-assets.

### 2026-06-05T12:20:25Z — Canonical Android KQL pattern [SUMMARIZED]
Scully established `| where DeviceOs has_cs 'ANDROID'` (case-sensitive) on `idsharedwus/NaasProd/TunnelServerOperationEvents`. Android `ClientVersion` = `1.0.NNNN.NNNN` (NOT Windows SemVer). 7 starter queries reconciled.

### 2026-06-05 — Marketplace inventory [SUMMARIZED]
Inventoried `Identity-gsa-client-marketplace` (`gsa-client-plugins`). Verdict: **0 ADOPT, 2 REFERENCE, 0 SKIP** (toolkit + setup-prereqs; gsa-kusto-catalog deferred to Scully). REFERENCE-only because skills depend on sibling catalog + 7 IdentityWiki pages — copying breaks them. Output: `agents/doggett/research/marketplace-plugin-inventory.md`, decision `doggett-marketplace-inventory.md`. Key conventions for re-use: two-tier marketplace model (`gsa-plugins` cross-cutting vs `gsa-client-plugins` client-only — same plugin in only one); plugin layout `plugins/<n>/.claude-plugin/plugin.json` + `README.md` + `skills/<s>/SKILL.md`; mandatory SKILL.md sections KNOW/DO/CHECK/Common Rationalizations(≥3)/Red Flags(≥3), body <500 lines, description ≤250 chars; no inline reference dumps (use `references/*.json` or runtime wiki fetch); MCP-first, no installers; catalogs as data with reverse-lookup `_indexes`; PR convention `user/<alias>/feature/<plugin>`. Android signals: GSA Android → App Insights `wd-prod-android-client` (NOT Aria); Aria filter `App_Platform == 'Android'`; identity rules — `Client_Id` rotates, `DeviceInfo_Id` stable, **`UserInfo_Id` access-restricted, never use**; iOS analog `ios-mdatp/MDATPiOSDB`.

### 2026-06-05T12:40:00Z — App Insights confirmation cross-agent [SUMMARIZED]
`wd-prod-android-client` corroborated independently — but see CORRECTION below in latest entry; this finding is partially superseded.

## Current learnings (active)

### 2026-06-05 (final pass) — Defender-for-Android `agent-docs/` ingested

**Headline:** First real codebase grounding. Saloni cloned `WD.Client.Android-icm-copilot` locally; its `agent-docs/` directory (8 docs: Telemetry, TelemetrySubtables, TelemetryNewTable, AggregatedTableInfra, FeatureFlags, README, CodingStandards, BuildSteps, Testing) gives end-to-end visibility into how Android telemetry actually works. **4 RESOLVED / 5 PARTIAL / 4 STILL-BLOCKED** of the original open-question set; all remaining blockers reduce to "VSTS read on WD.Client.Android".

**MAJOR CORRECTION:** Android client telemetry is **Kusto-queryable directly** via `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` — same finding Scully arrived at independently from `IcmBaselineQueries.md`. The prior "Android client = App Insights `wd-prod-android-client` REST endpoint only" framing is partially wrong: `wd-prod-android-client` is downstream of 1DS, not the canonical Kusto-queryable surface. AI demoted to cross-check status.

**Telemetry pipeline — 3 layers, 1 cluster:**
1. **On-device:** `MDAppTelemetry.trackEvent(name, props[, Flags])` / `.trackEventException(name, throwable)`. **1DS for Defender events, Aria for Tunnel events** — both via `MDAppTelemetry`. Auto-stamps 9 common props (AndroidId, TelemetryCorrelationId, Persona, EnrollmentType, SessionIdTenantId, TenantIdPII, MachineId, TenantLicenseType, TenantOrgName).
2. **Raw landing:** 1DS → `MDATPAndroidDB.customEvents` on `mdatpandroidcluster.westus2.kusto.windows.net`. JSON props column = `EventProperty`.
3. **10 domain subtables (one event → one subtable):** `TelemetryMalwareScan`, `TelemetryAuth`, `TelemetryCompliance`, **`TelemetryVPNAndWebProtection`** (GSA's home — `Vpn*`/`Tunnel*`/`Naas*`/`Edge*`), `TelemetryAppLifecycle`, `TelemetryHeartbeat`, `TelemetryNetworkMonitoring`, **`TelemetryConfiguration`** (ECS flag evals), `TelemetryProductHeartbeat`, `TelemetryGeneral` (catch-all). Update policy idiom: `| where name in (...) | evaluate bag_unpack(EventProperty)`. 632 events total (Feb 2026 validation).
4. **Aggregations:** `libraries/AggregatedTables/*.py` configs → Azure Function `KustoQueryFunc`, hourly modulo-scheduled (`hoursSinceEpoch % interval == 0`), interval ∈ {6,12,24,48,72,168,720}. Server-side `.set-or-append`, zero egress. Outputs to `"dashboard"` folder; alerts to `"alerts"` (via `libraries/Alerts/*.py`). PR-validated against live ADX via `ValidateKqlQueryADX.py`. **No standalone `.kql` files — all KQL embedded in Python configs.**

**Discipline (strict):** PascalCase for event names + property keys (enforced). No hardcoded strings — names + keys come from codegen'd Kotlin classes in `WD.Mobile.Xplat.Infra` (`*EventProperties.NAME`); hardcoded literals are PR-blocking. `"dashboard"` + `"alerts"` are the only folders the engine mutates.

**Feature-flag model — `EcsManager` + `ConfigUtils`, 6-layer cleanup pattern.** Runtime: `EcsManager.isFeatureEnabled("Feature/Name", default)`. Hierarchical slash-separated names (`Tunnel/EnhancedConnectivity`, `Experiments/OnboardingFlow/StepOptimization`). **Audience predicates include `user type, enrollment, android version, device, tenant`** (FeatureFlags.md L11) — that's the version-rollout mechanism that creates Windows-v2.28.96-style regressions on Android. Cache pattern: `AtomicBoolean` in `@Singleton FeatureManager`, subscribed to `HANDLER_MSG_ECS_CONFIG_REFRESH` on `MDRxBus`. 6-layer footprint (per `ecs-cleanup.agent.md`): constant → `ConfigUtils` wrapper → `EcsManager` call → cached `AtomicBoolean`+refresh subscriber → gated `if/else` → test mocks. 100%-rolled-out flags must come down through all 6.

**Tests:** MockK is the law; PowerMock banned. All extend `MDBaseUnitTest`. Telemetry idiom: `mockkStatic(TelemetryUtils::class); every { TelemetryUtils.track(any()) } returns Unit` + `verify(exactly = 1) {...}`. For combined events: `mockkStatic(CombinedTelemetryUtils::class)`. **Unit tests do NOT cover subtable routing** (Kusto update policy — validate via `customEvents | where name == ... | bag_unpack | take 10`) **or aggregation correctness** (PR-time `ValidateKqlQueryADX.py`).

**Build:** Java 17 + NDK `25.2.9519653` (exact) + CMake `3.22.1` + Python 3.11 via `uv` + Conan `1.59.0` (exact, NOT 2.x) + Rust stable + `cargo-ndk`. Bootstrap `./init.sh` or `python3 init.py`. `local.properties` carries 9+ PAT/API keys — `vstsPassword` is the gate.

**Shared engine (NOT in WD.Client.Android — in `WD.Mobile.XPlat.Infra`):** `KustoQueryFunc/` (.NET 8 isolated-worker Azure Function) + `AutomationInfra/scripts/python/AggregatedTableInfra/` (Python validation + manifest gen) + 5-stage deploy pipeline.

**Gotchas worth memorizing:**
- Cluster reachability: `mdatpandroidcluster.westus2.kusto.windows.net` is `westus2`; auth posture should carry over from `idsharedwus`/`idsharedscus` (same tenant), but **smoke-test owed**.
- Time column on Defender ADX is **`timestamp` (lowercase)** — AI/standard ADX convention. Differs from NaasProd's `TIMESTAMP` (uppercase).
- `androidId` 3-char truncation (ICM C1 footnote) — cross-cluster joins keyed on `androidId` must fall back to `startswith substring(__ANDROID_ID__, 0, strlen(__ANDROID_ID__) - 3)`.
- NaaS call-site convention: `NaaSTelemetrySender.logTelemetry(...)` sets `EventProperty.SubEvent = "NaaS"` + `EventProperty.Message = <free-form>`. When in doubt about an Android NaaS event, filter by `tostring(EventProperty.SubEvent) == "NaaS"` first. `NaasVPNFailure` fires from two locations distinguished by `Message starts with "Connecting failed"` vs `"Running failed"`.

**Worked this pass:**
- Updated `agents/doggett/research/defender-android-discovery.md` with "ICM-Copilot Doc Discovery (2026-06-05)" section.
- NEW `agents/doggett/research/android-telemetry-model.md` — 1-page reference.
- NEW `.squad/skills/android-version-regression-detection/SKILL.md` — confidence LOW; Android analog of Windows v2.28.96 playbook. ClientVersion pivot + per-version metric divergence + ECS flag-eval diff + flag-gating concentration test + 3-way mitigation routing (flag rollback / version rollback / audience narrow). **First real use must pair with Scully.**
- Decision `decisions/inbox/doggett-android-telemetry-docs-ingested.md` (merged to `decisions.md` this scribe pass).

**Still blocked (all VSTS-gated):**
- GSA module exact path inside WD.Client.Android (only inferred via routing prefixes: `vpn`/`tunnel`/`naas`/`edge`).
- Internal `.squad/`/`.copilot/`/`agents/`/`skills/`/`plugins/` dirs inside WD.Client.Android.
- Out-of-band crash reporter confirmation (Firebase Crashlytics suspected from `FirebaseApiKeyDebug` in `local.properties`).
- Exact `*EventProperties.NAME` constants for GSA failure modes (505, `SuccessSettingsNotFound`, hypothesized 631/632 analog) — known to live in codegen'd classes in `WD.Mobile.Xplat.Infra`, exact strings need grep.
- Whether any of the 7 proposed Android-specific report fields already have `libraries/AggregatedTables/*.py` configs.

## 2026-06-05T12:55:00Z — Scribe cross-agent
Scribe summarized this history file (was 21,534 bytes, over the 15,360 gate). Full prior content preserved at `agents/doggett/history-archive.md`. Both new decisions (Scully's ICM baseline + Doggett's telemetry docs ingest) merged to `decisions.md` with explicit supersession clarification on the prior "GSA Kusto Catalog adopted" decision. Mulder/Reyes/Skinner histories updated with MDATPAndroidDB correction + GSA→`TelemetryVPNAndWebProtection` routing + 22 ICM-vetted queries mapped + version-regression skill availability.
