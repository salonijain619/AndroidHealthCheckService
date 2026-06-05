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


### 2026-06-05 — Marketplace inventory: GSA client plugin marketplace structure
- **Inventory complete** for `Identity-gsa-client-marketplace` (`gsa-client-plugins`) skills in scope: `gsa-client-telemetry-toolkit` (parent) and `setup-prereqs`. Skipped `gsa-kusto-catalog` (Scully). Verdict: **0 ADOPT, 2 REFERENCE, 0 SKIP** — both maintained upstream and dependent on a sibling catalog + seven runtime-fetched IdentityWiki pages, so referencing by absolute path beats forking. Output: `.squad/agents/doggett/research/marketplace-plugin-inventory.md`, decision `.squad/decisions/inbox/doggett-marketplace-inventory.md`.
- **Marketplace structure conventions worth memorizing for re-use:**
  - **Two-tier marketplace model.** `gsa-plugins` (cross-cutting: PR review, git, planning, doc gen, livesite, generic Kusto, mcp-setup, skill-tester, skill-reviewer) vs. `gsa-client-plugins` (client-codebase / client-telemetry / on-device-debugging only). Same plugin must NOT be in both; pick one home per plugin to avoid drift. Scope test: "is this client-codebase or client-telemetry-specific?" If yes → client. If no → cross-cutting.
  - **Plugin layout (reference: `gsa-client-telemetry-toolkit`):** `plugins/<name>/.claude-plugin/plugin.json` (name/version/description/maintainers) + `README.md` + `skills/<skill>/SKILL.md` + optional `commands/` + optional `TESTING.md`. Register in repo-root `.claude-plugin/marketplace.json` under `plugins[]`.
  - **SKILL.md required sections (must-have all five):** `## KNOW` (background/prereqs/constraints), `## DO` (numbered `### Step N — Title`, imperative voice), `## CHECK` (`- [ ]` boxes pointing to evidence), `## Common Rationalizations` (table of excuses + rebuttals, ≥ 3 entries), `## Red Flags` (observable signs the skill is being violated, ≥ 3 items). Body **< 500 lines**. Frontmatter `description` (everything before "Load when:") **≤ 250 chars**.
  - **No inline reference dumps.** Long reference content (per-event field tables, error-code dictionaries, routing matrices, OEM mix) belongs in `references/*.json` next to SKILL.md OR on a wiki page fetched at runtime via `ADOProd-wiki_get_page_content`. The toolkit puts seven references on IdentityWiki and fetches on demand — a clean pattern when references change frequently.
  - **MCP-first / no installers.** Plugins should NOT ship per-plugin installers. Shared MCP servers (`ICMProd`, `ADOProd`, `AzureMCP`, `workiq`, `kusto`) are configured via `/mcp-setup` from `gsa-plugins`. If an installer is unavoidable: must be idempotent, take timestamped backups before mutating user files, bail safely on malformed input, ship `TESTING.md`.
  - **Catalogs as data, not prose.** Long-lived knowledge bases (clusters/tables/aliases) live as JSON/YAML next to SKILL.md, loaded on demand. Reverse-lookup `_indexes` block is the recommended access pattern (don't full-scan the catalog).
  - **Catalog-reuse rule.** GSA NaaS Kusto routing lives in `gsa-kusto-catalog/catalog.json` — other skills depend on it instead of redefining cluster URLs / database names / table mappings. Same principle Squad should adopt: one canonical catalog per concern, referenced by all consumers.
  - **Validation gates.** `/test-skill path=...` (format checks: description length, body length, sections present) and `review-skill` (agent-driven content review) — both from `gsa-plugins` — run before PR review.
  - **Install UX.** `/plugin marketplace add <repo-url>` + `/plugin install <plugin>@gsa-client-plugins`. Each marketplace registers as a named source so `@gsa-client-plugins` disambiguates from `@gsa-plugins`.
  - **Branch + PR convention.** `user/<alias>/feature/<plugin-name>`, PR to `main`, reviewers check marketplace registration parses + plugin layout + MCP-first design + SKILL.md format. Reference PRs are tabulated in `AGENTS.md` for benchmarking.
- **Android-specific signals harvested** (without WD.Client.Android access):
  - GSA Android client telemetry → App Insights cluster `android-appinsights`, database `wd-prod-android-client` (NOT Aria). The `wd-prod-` prefix corroborates "GSA is a module inside Defender for Android."
  - When Android signals appear in shared Aria tables (`mnap_xplat_telemetry*`), filter is `App_Platform == 'Android'` (exact-case literal). Aria prod DB GUID `f0eaa94222894be599b7cd0bc1e2ed6f` re-confirmed.
  - Identity rules pan-platform: `Client_Id` rotates on Entra repair/rejoin (can be empty for broken-auth devices); `DeviceInfo_Id` is the stable hardware-derived long-window key; **`UserInfo_Id` is access-restricted in Aria — never use it, returns HTTP 400**.
  - `Client_Id → owner` reverse-lookup via Microsoft Graph `/users/{upn}/ownedDevices` works for Android (`operatingSystem='Android' → App_Platform='Android'`). Scopes: `Device.Read.All` + `Directory.Read.All`.
  - iOS analog uses `ios-mdatp / MDATPiOSDB` (`customEvents`) — both mobile platforms ride Defender's mobile telemetry stack while desktop (Win/Mac) rides GSA's Aria pipeline. The asymmetry is structural.
- **Still blocked behind WD.Client.Android:** Android telemetry helper class names, on-device emitter (OneDS vs. App Insights direct vs. custom Defender uploader), crash-reporter implementation, any `.squad/` / `.copilot/` / `agents/` / `skills/` / `plugins/` dirs inside WD.Client.Android, Android-specific KQL/Workbook JSON, the Android `EventName` constants, and Defender's existing OEM-mix / Doze / foreground-service / work-profile dashboards. Note: `Identity-ZTNA-NaaS-Agent` is the GSA *agent* repo referenced by the toolkit's wiki — NOT WD.Client.Android.

## 2026-06-05T12:40:00Z — Cross-agent: App Insights confirmation propagated
- The `wd-prod-android-client` App Insights finding (independently surfaced from the marketplace toolkit SKILL.md while you were inventorying) corroborates Scully's catalog-derived routing. Two independent paths to the same fact — the Android client-side pipeline is App Insights, NOT Aria. Scully's earlier charter point #2 is wrong; correction owed in a future cycle.
- Server-side: `naas-idsharedwus / NaasProd` is a 2-table mirror only. Full NaasProd lives on `naas-idsharedscus`. If a future Android-client task wants to cross-check tunnel events against Roxy / Talon / ControlTower / CertMonitor server-side, route to SCUS.
- PKI routing now known: `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` — same cluster you already have a foothold on.
- Both decisions (yours: `doggett-marketplace-inventory.md`; Scully's: `scully-kusto-catalog-adopted.md`) merged to `decisions.md`, PROPOSED, pending Mulder ack.
