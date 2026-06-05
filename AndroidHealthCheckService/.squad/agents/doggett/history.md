# doggett — Learnings

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

### 2026-06-05 — Initial Defender-for-Android discovery pass
- **Defender integration confirmed (per Saloni):** GSA Android client is a module *inside* Microsoft Defender for Android, not a standalone APK. Our scope is "the GSA code path within WD.Client.Android."
- **VSTS auth blocker (HARD):** `microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android` is gated behind Entra. Anonymous `web_fetch` returns only the sign-in stub. No ADO/VSTS MCP is available in this environment. GitHub code search for `GlobalSecureAccess`, `SuccessSettingsNotFound GSA`, and `WD.Client.Android GsaTunnel` returned **0 results** — no public mirror exists. Everything below is hypothesis until Saloni unblocks access.
- **Asset categories to inventory in the Defender repo** (per Saloni's note that agents/skills/plugins already exist there): squad/agent definitions (`**/squad.agent.md`, `**/.squad/`, `**/agents/*/charter.md`), skills (`**/.copilot/skills/`, `**/skills/*/SKILL.md`), plugins (`**/plugins/`, `**/.copilot/plugins/`), copilot instructions (`.github/copilot-instructions.md`), telemetry helpers (`*Telemetry*`, `*Aria*`, `*OneDS*`, `*AppInsights*`), crash reporters (`*Crash*`, `*Anr*`, Crashlytics/AppCenter), and checked-in KQL/dashboards (`**/*.kql`, `**/*.csl`, `**/dashboards/`).
- **Proposed Android-specific report fields:** install channel (Play / sideload / MAM-Intune); Android API level mix; OEM mix (Samsung/Pixel/Xiaomi — OEM battery managers kill VPNs); Doze/battery-optimization kill rate; foreground service notification health (Android 14+ stricter rules); work-profile vs personal-profile split; Defender app version × GSA module version pairing. All flagged PROPOSAL pending Saloni/dashboard confirmation.
- **Android equivalents of Windows error codes:** 505 likely shares the server-side code but surfaces client-side as MSAL/broker errors; 631/632 (tray icon) has *no* Android analog — propose new code(s) for "tunnel UI/VpnService state divergence"; APS `SuccessSettingsNotFound` likely emitted with the same/near-same event-name token, needs confirmation.
- **What I need from Saloni:** (1) VSTS read access or pasted file listings, (2) GSA module root path inside the repo, (3) listings of any `.squad/` / `.copilot/` / `agents/` / `skills/` dirs, (4) name of the Android telemetry helper class, (5) which crash reporter is wired up, (6) whether KQL/Workbook JSON is checked into the repo, (7) sign-off on the seven proposed Android-specific report fields.
- **Outputs:** `.squad/agents/doggett/research/defender-android-discovery.md`, `.squad/decisions/inbox/doggett-reuse-defender-assets.md`. No skill authored yet — too early without real repo access.

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

