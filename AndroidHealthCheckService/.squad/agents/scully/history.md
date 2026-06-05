# scully — Learnings

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

### 2026-06-05 — Dashboard reverse-engineering + first Kusto introspection

**Dashboard URL anatomy** (`https://dataexplorer.azure.com/dashboards/8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98`):
- Standard Kusto dashboard params: `p-_startTime` (default `7days`), `p-_endTime` (`now`), `p-_osType=v-ANDROID`, `p-_trafficProfile=all`, `p-_tenantId=all`, `p-device_id=v-DeviceIdPII_<hash>`. The `v-` prefix = "variable value" (Kusto dashboard convention).
- Fragment `#45c11f5e-b0ae-40d7-bb48-c2b1936011cc` = a specific page UUID within a multi-page dashboard. Most likely the per-device drilldown page (since `device_id` is also pinned). **Unconfirmed — open question for Saloni.**

**Kusto access — what's real:**
- `azure-mcp-kusto` works against `idsharedwus.kusto.windows.net` with default credentials. Confirmed via `kusto_database_list`, `kusto_table_list`, `kusto_table_schema` (all cheap, read-only).
- `NaasProd` is rich: Edge/Roxy/Talon/Tunnel/Control-Tower/ZTNA/DNS/ThreatIntel/PolicyBroker tables all present.
- `NaasAgentServicesApsProd` has the APS tables (`AgentGetSettingsOperationEvent`, `AgentSettingsAckOperationEvent`, `PoliciesApi`, etc.) — backs the "APS Availability" report row.
- `EdgeDiagnosticOperationEvent` schema confirmed: has `DeviceId`, `TenantId`, `NetworkProfile`, `ResponseCode`, `DurationInMilliseconds`, `OperationName` — but **NO `osType` column**. Server-side Android filtering must come from a DeviceId→OS join or Aria-side prefilter.
- `NaaSVPNZtnaConnectionLogsEvent` DOES carry `env_os` / `env_appVer` (Aria envelope) → Android filtering is direct on this table.

**What's still hypothesis (NOT verified):**
- All panel-to-page mappings inside the dashboard.
- Exact KQL of every dashboard panel (auth wall prevents fetching).
- PKI telemetry source — both `NaasCloudPkiProd` and `NaasAgentServicesCloudPkiProd` returned zero tables on this account (permission or wrong cluster).
- Aria cluster database/table names for client-side telemetry.
- AppInsights component name within sub `fb633419-…`.
- Whether an `AndroidDeviceIds()` lookup function exists in `NaasProd`.

**Queries: real vs hypothesis**
- All 5 starter queries in `.squad/skills/android-kusto-starter/SKILL.md` are marked `STATUS: untested`.
- Tunnel Health query (#5) has the highest confidence — `env_os == "Android"` filter is grounded in the confirmed `NaaSVPNZtnaConnectionLogsEvent` schema.
- PKI query (#4) is fully blocked — placeholder only.

**Top open questions for Saloni (also in `research/dashboard-analysis.md`):**
1. Which dashboard page is fragment `#45c11f5e-…`?
2. Where does PKI telemetry actually live?
3. How does the dashboard implement `osType == Android` on `EdgeDiagnosticOperationEvent` (lookup function or just hide panel)?
4. Aria cluster database + relevant Android client telemetry table(s)?
5. AppInsights component/app-id under sub `fb633419-…`?
6. Canonical definition of "Active Android device"?
7. Valid enum values for `NetworkProfile` / `trafficProfile`?
8. **Easiest unblock:** one panel query export from the dashboard UI.

**Artifacts produced this session:**
- `.squad/agents/scully/research/dashboard-analysis.md` — full hypothesis doc
- `.squad/skills/android-kusto-starter/SKILL.md` — 5 starter KQL queries (all `STATUS: untested`)
- `.squad/decisions/inbox/scully-dashboard-as-source-of-truth.md` — decision proposal to mirror the existing dashboard rather than fork query semantics

---

## 2026-06-05T12:00:52Z — Team update: bootstrap complete

Squad bootstrap arc closed. State of the team as of this checkpoint:

- **Cast:** Mulder, Scully, Doggett, Skinner, Reyes, Scribe, Ralph — all standardized on `claude-opus-4.7`.
- **Report template:** `.squad/templates/daily-livesite-report.md` + `daily-livesite-report-EXAMPLE.md` ready (Reyes). `{TBD — pending [Agent]}` slots make ownership unambiguous.
- **Telemetry foothold:** `azure-mcp-kusto` confirmed against `idsharedwus / NaasProd` + `NaasAgentServicesApsProd`. Real schemas captured for `EdgeDiagnosticOperationEvent` and `NaaSVPNZtnaConnectionLogsEvent`. Five starter KQL queries in `.squad/skills/android-kusto-starter/SKILL.md` (untested). Existing Android GSA Kusto dashboard `8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` proposed as canonical source of truth.
- **Defender-for-Android reuse:** discovery plan authored by Doggett, but **VSTS access wall** blocks repo inventory. Reuse-first posture is proposed, not yet executed.
- **Open dependencies on Saloni:** (1) confirm dashboard-as-source-of-truth + export a panel query; (2) unblock VSTS access. **Open dependency on Mulder:** ack the two proposed decisions.
- **Decisions merged this cycle:** model standardization, report skeleton, dashboard-as-source-of-truth, reuse-Defender-assets. See `.squad/decisions.md`.

---

### 2026-06-05 (later) — Panel KQL unblock from Saloni

**What changed:**
- Saloni pasted verbatim KQL from one panel of dashboard `8a1fa78a-…` (the "Active Android Tenants (7d)" tile).
- Schema-validated `TunnelServerOperationEvents` lives on `idsharedwus / NaasProd` (our primary cluster — no new cluster hop needed).
- Ran the panel query verbatim through `azure-mcp-kusto`. **Returned 8 distinct active Android tenants** for the 2026-05-29 12:00 UTC → 2026-06-05 12:00 UTC window. Query is executable, schema is real, auth path works.

**Corrections to prior hypotheses (this is the important part):**
- **Correct table:** `TunnelServerOperationEvents` (we had `EdgeDiagnosticOperationEvent` and `NaaSVPNZtnaConnectionLogsEvent` — both real, but neither was the dashboard's primary backing table for tenant/device counts).
- **Correct Android filter (canonical):** `| where DeviceOs has_cs 'ANDROID'` — case-sensitive, value is literal `ANDROID` with no `v-` prefix. Earlier hypotheses (`env_os == 'Android'`, `osType == 'v-ANDROID'`) are wrong for this table family.
- **Version format differs from Windows:** Android `ClientVersion` is `1.0.NNNN.NNNN` (4-segment numeric build, e.g. `1.0.7203.0401`). Windows uses `v2.28.96`. Same column name, fundamentally different format. Reyes's report template needs to know.
- **URL ↔ column drift to remember:** `osType` → `DeviceOs`; `trafficProfile` → `ServiceType`; `device_id` → `DeviceId`. URL uses snake/camel, table uses Pascal.
- **`TunnelServerOperationEvents` is richer than expected** — carries `DeviceId, ClientVersion, ServiceType, TenantId, LatencyMs, Status, FlowStatusError, FlowErrorClassification, OperationName, Region` natively. Most daily-report rows can be sourced from this single table without joins. This collapses several hypothetical join queries.
- **Edge vs Tunnel are complementary, not alternates.** Edge = HTTP-layer (ResponseCode, DurationInMilliseconds). Tunnel = L4/flow-layer (LatencyMs, FlowStatusError). For tunnel-success / latency, prefer Tunnel. For HTTP 4xx/5xx, prefer Edge. Edge has NO `DeviceOs` column.

**What's still unknown after this unblock:**
- Errors/latency panel KQL (this first panel was a simple distinct-count and doesn't reveal how errors are surfaced).
- PKI source — unchanged.
- Whether the 37-build `_application_Version` allowlist is manually curated or auto-discovered (affects query robustness).
- APS-table Android-filter idiom (does `AgentGetSettingsOperationEvent` carry `DeviceOs`? Likely not — Aria-style envelope. Schema introspection needed.).
- A handful of `TunnelServerOperationEvents` columns came back from schema introspection looking malformed/concatenated (e.g., `SoTransportProtocol`, `SournnerFlowDestinationPort`, `DestinatiedAt`). Either real schema corruption or MCP-response artifact — re-introspect next session.

**Artifacts touched this turn:**
- `.squad/skills/android-kusto-starter/SKILL.md` — full rewrite. Reconciled queries 1–5 against ground truth, added query #6 (verbatim panel mirror, executed) and #7 (active devices variant).
- `.squad/agents/scully/research/dashboard-analysis.md` — appended "## Ground Truth From Panel KQL (2026-06-05)" section. Refreshed open-questions list. Marked panel-mappings CONFIRMED / CONTRADICTED / STILL HYPOTHESIS.
- `.squad/decisions/inbox/scully-canonical-android-filter.md` — new decision proposal.

**Next ask of Saloni:** one more panel KQL, ideally an errors-or-latency panel, to lock down query #2 / #5 semantics.
