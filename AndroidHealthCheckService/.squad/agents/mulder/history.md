# mulder — Learnings

## Project Context (seeded 2026-06-05)
- **Project:** Android GSA Client Service Health Check
- **User:** salonijain619 (Saloni)
- **Stack:** Investigation/SRE squad for the GSA Android client. Telemetry from server-side Kusto (NaasProd @ idsharedwus), client-side AppInsights (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c), and Aria Kusto (f0eaa94222894be599b7cd0bc1e2ed6f).
- **Android client repo:** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android
- **Onboarding doc:** https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **ICM team:** https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- **Report channel:** IDNA GSA → Livesite - Client (Teams), tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
- **Sister squads:** Windows (win_client_investigation_squad), Mac (HarryPotter)

## Learnings

---

## 2026-06-05T12:00:52Z — Team update: bootstrap complete

Squad bootstrap arc closed. State of the team as of this checkpoint:

- **Cast:** Mulder, Scully, Doggett, Skinner, Reyes, Scribe, Ralph — all standardized on `claude-opus-4.7`.
- **Report template:** `.squad/templates/daily-livesite-report.md` + `daily-livesite-report-EXAMPLE.md` ready (Reyes). `{TBD — pending [Agent]}` slots make ownership unambiguous.
- **Telemetry foothold:** `azure-mcp-kusto` confirmed against `idsharedwus / NaasProd` + `NaasAgentServicesApsProd`. Real schemas captured for `EdgeDiagnosticOperationEvent` and `NaaSVPNZtnaConnectionLogsEvent`. Five starter KQL queries in `.squad/skills/android-kusto-starter/SKILL.md` (untested). Existing Android GSA Kusto dashboard `8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` proposed as canonical source of truth.
- **Defender-for-Android reuse:** discovery plan authored by Doggett, but **VSTS access wall** blocks repo inventory. Reuse-first posture is proposed, not yet executed.
- **Open dependencies on Saloni:** (1) confirm dashboard-as-source-of-truth + export a panel query; (2) unblock VSTS access. **Open dependency on Mulder:** ack the two proposed decisions.
- **Decisions merged this cycle:** model standardization, report skeleton, dashboard-as-source-of-truth, reuse-Defender-assets. See `.squad/decisions.md`.

## 2026-06-05T12:20:25Z — Cross-agent: canonical Android KQL pattern established
Scully confirmed via verbatim panel KQL execution against `idsharedwus/NaasProd/TunnelServerOperationEvents`:
- Canonical filter: `| where DeviceOs has_cs 'ANDROID'` (case-sensitive)
- Android `ClientVersion` format: `1.0.NNNN.NNNN` (4-segment numeric, NOT Windows SemVer)
- See `.squad/skills/android-kusto-starter/SKILL.md` (7 queries reconciled with ground truth)
- Decision in `.squad/decisions.md` (PROPOSED, pending Mulder ack)


## 2026-06-05T12:40:00Z — Cross-agent: catalog ingest + Android pipeline correction
Scully ingested upstream `gsa-kusto-catalog`; Doggett inventoried the rest of the marketplace. Three of four standing unknowns closed:
- **Android client telemetry pipeline = App Insights `wd-prod-android-client`, NOT Aria.** Scully's earlier charter point #2 (Aria `mnap_xplat_*` as Android-primary) is **wrong** — those tables are Win/Mac primary; Android appears in Aria only opportunistically (`errorevent` via `App_Platform == 'Android'`). Charter will be corrected in a future cycle. Doggett independently corroborated via the `wd-prod-` prefix.
- **PKI source known:** `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (time col `PreciseTimeStamp`). Routing unblocked; query body still owed.
- **Server-side hop:** `naas-idsharedwus / NaasProd` is a **2-table mirror** (Tunnel + Edge). For Roxy / Talon / ControlTower / NaaSVPN* / CertMonitor, hop to `naas-idsharedscus` (full 37-table NaasProd).
- New cluster discovered: `androidgsa.eastus.kusto.windows.net / Metric` (Android perf rollups; catalog-flagged unverified).
- Decisions: `scully-kusto-catalog-adopted.md`, `doggett-marketplace-inventory.md` (both PROPOSED, pending Mulder ack).


## 2026-06-05T12:55:00Z — Cross-agent: ICM baseline + Android telemetry architecture
Scully + Doggett ran in parallel against `WD.Client.Android-icm-copilot/agent-docs/`. Two convergent findings + two new skills:
- **CORRECTION:** Android client telemetry IS ADX-queryable via `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Kusto, via `azure-mcp-kusto`). Both agents independently confirmed this. Supersedes the prior "Android client = App Insights `wd-prod-android-client` REST endpoint only" assumption — AI is now cross-check status.
- **GSA's home subtable:** `TelemetryVPNAndWebProtection` (`Vpn*`/`Tunnel*`/`Naas*`/`Edge*` events route here via Kusto update policies + `bag_unpack`). 10 domain subtables total under MDATPAndroidDB.
- **22 of 30 Defender-vetted ICM queries** now mapped to specific daily-livesite-report sections — see Scully's new `android-icm-baseline-mapping/SKILL.md` and the section-index table at the top of `android-kusto-starter/SKILL.md`.
- **Version-regression detection pattern** for Android (analog of Windows v2.28.96 playbook) — see Doggett's new `android-version-regression-detection/SKILL.md` (confidence LOW; pairs Doggett+Scully on first use). Uses ECS feature-flag `ClientVersion`-targeting + per-version metric divergence.
- Decisions `scully-icm-baseline-adopted` + `doggett-android-telemetry-docs-ingested` merged to `decisions.md`, PROPOSED, pending Mulder ack. Clarification note appended to prior "GSA Kusto Catalog adopted" decision flagging the supersession.
