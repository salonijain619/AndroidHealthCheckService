# Decisions

Append-only ledger of team decisions. Scribe merges from `decisions/inbox/`.

---

### 2026-06-05: Squad initialized
**By:** Saloni (via Coordinator)
**What:** Cast an X-Files-named investigation squad for the Android GSA client service health work, modeled after the Windows and Mac investigation squads.
**Why:** Need a parallel structure for Android client telemetry analysis, ICM tracking, and service health reporting.

---

### 2026-06-05: Standardize all team members on claude-opus-4.7
**By:** Saloni (via Coordinator)
**What:** All 7 agent charters (Mulder, Scully, Doggett, Skinner, Reyes, Scribe, Ralph) specify `claude-opus-4.7` as preferred model. Coordinator passes `model: claude-opus-4.7` when spawning via the `task` tool unless explicitly overridden.
**Why:** Saloni requested all squad members use the latest available Opus model instead of per-role mixed defaults (haiku/sonnet/auto).
**Tradeoff:** Opus 4.7 is higher-quality but slower and more expensive than Haiku. Background-runnable mechanical tasks (Scribe file ops, Ralph monitoring) will cost more per turn. Acknowledged.
**Parallelism note:** Agents continue to work independently in parallel via background mode. Model change does not affect orchestration topology.

---

### 2026-06-05: Android Daily Livesite Report Template Established
**By:** Reyes (Report Writer)
**What:** Established `.squad/templates/daily-livesite-report.md` as the canonical skeleton for daily Android GSA Client Service Health Check reports, mirroring the Windows squad format (Teams channel `IDNA GSA → Livesite - Client`). Also created `.squad/templates/daily-livesite-report-EXAMPLE.md` — a fully-filled reference example using a fabricated Android v6.2.1 auth regression scenario.
**Why:** Consistency with Windows/Mac squads, clear `{TBD — pending [Agent]}` ownership placeholders, Teams-ready markdown, reusable assembly.
**Structure:** Header (date/on-call), Executive Summary, 7-row Key Metrics table, Top 5 Insights, Cross-Domain Correlation Analysis (chain + timeline + evidence + validation), Data Quality Notes, Contributors.
**Android-specific adaptations:** "Active Android Clients (weekday)" metric; "Android Client Version Distribution Health" row; auth → APS → notification-channel cross-domain example; three open questions for Scully (Play Store vs. sideload split, OS version baselines, OEM/model variance).
**Ownership:** Scully → metric fills + telemetry notes; Skinner → severity classification; Doggett → cross-domain diagnosis; Mulder → review; Reyes → narrative + Teams publish.

---

### 2026-06-05: Adopt existing Android GSA Kusto dashboard as canonical source of truth
**By:** Scully (Telemetry Analyst)
**Status:** PROPOSED — pending Saloni confirmation + Mulder ack
**What:** Treat the existing Kusto dashboard at `https://dataexplorer.azure.com/dashboards/8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98` as the canonical source of truth for every metric row in the daily livesite report. Scully's KQL work (in `.squad/skills/android-kusto-starter/`) is a *mirror* of dashboard panels, not an independent product; each query cites the panel it derives from.
**Why:** Dashboard encodes institutional knowledge (active-device definitions, table unions, Android filtering, retry/timeout exclusions); pivots (`osType`, `trafficProfile`, `tenantId`, `device_id`) map 1:1 to report needs; reconciliation is cheap (deep-link for second opinion); reduces drift (one source updated by dashboard owners).
**Operational rules:** Dashboard wins when it disagrees with a Scully query (Scully opens finding, doesn't silently override). Schema introspection via `azure-mcp-kusto` (confirmed working for `idsharedwus / NaasProd` and `NaasAgentServicesApsProd`) is encouraged; heavy custom queries that duplicate dashboard panels are avoided. For metrics the dashboard doesn't cover (e.g., PKI Health), Scully flags the gap to Mulder.
**Risks:** Dashboard is auth-walled (mitigated by Saloni exporting panel queries on demand); panels may change silently (mitigated by per-query panel citation + weekly diff check); PKI/Aria-side sources may not be in visible Kusto DBs (tracked as open questions in `agents/scully/research/dashboard-analysis.md`).

---

### 2026-06-05: Audit & reuse existing Defender-for-Android squad assets before building new
**By:** Doggett (Android Engineer)
**Status:** PROPOSED — BLOCKED on VSTS access
**What:** Before this squad authors any new agents, skills, plugins, telemetry helpers, or KQL assets, first inventory what already exists in the WD.Client.Android (Defender for Android) repo and reuse where it fits. Run the file-pattern inventory in `.squad/agents/doggett/research/defender-android-discovery.md` section (a), catalog pre-existing squad/agent/skill/plugin definitions + telemetry helpers + crash reporters + checked-in KQL/dashboards, and for each Doggett/Scully/Reyes deliverable check the inventory first: (a) reuse, (b) extend, or (c) document why a new asset is justified.
**Why:** Saloni flagged that the Defender repo already contains pre-existing agents/skills/plugins for telemetry, crashes, and Kusto. Reinventing forks institutional knowledge and risks drifting from how the Defender team actually emits/queries telemetry. GSA on Android is integrated *into* Defender, not standalone.
**Blocker:** WD.Client.Android lives on `microsoft.visualstudio.com` (VSTS), auth-gated. No VSTS MCP, no PAT/Entra, no public GitHub mirror (verified — 0 hits on `GlobalSecureAccess`, `SuccessSettingsNotFound GSA`, `WD.Client.Android GsaTunnel`). Anonymous fetch returns only sign-in stub. Cannot execute until Saloni grants VSTS access, pastes file listings, or runs the patterns themselves.
**Not deciding:** Specific telemetry library / KQL pattern / crash-reporter choice — those wait until inventory completes. Not committing to mirror Defender 1:1 — only to consider reuse before reinvention.
**Asks:** Mulder approve "reuse-first" posture (strict vs. case-by-case); Saloni unblock VSTS access.

---

# Decision: Canonical Android Filter for Squad KQL

**By:** Scully (Telemetry Analyst)
**Date:** 2026-06-05
**Status:** PROPOSED — pending Mulder ack

## What
The canonical Android-scoping clause for all server-side KQL produced by this squad is:

```kusto
| where DeviceOs has_cs 'ANDROID'
```

…run against `cluster('idsharedwus').database('NaasProd').TunnelServerOperationEvents` (and any other `NaasProd` table that exposes the `DeviceOs` column with the same convention).

Earlier hypothesis filters are **WRONG** for this table family and must not be used:
- ❌ `env_os == 'Android'` — that's the Aria envelope pattern; works on `NaaSVPNZtnaConnectionLogsEvent`, not on `TunnelServerOperationEvents`.
- ❌ `osType == 'v-ANDROID'` — `v-ANDROID` is dashboard-binding URL syntax (`v-` = "value"); the column never literally contains `v-`.
- ❌ `DeviceOs == 'Android'` (mixed case, equality) — column value is upper-case `ANDROID`, and the dashboard uses case-sensitive `has_cs`, so equality with `'Android'` would silently zero-out.

## Why
- Saloni pasted the verbatim KQL from one panel of the production Android GSA Kusto dashboard (`8a1fa78a-…`). It is authoritative ground truth.
- Schema introspection via `azure-mcp-kusto` against `idsharedwus / NaasProd / TunnelServerOperationEvents` confirmed the `DeviceOs` column exists (type `string`).
- Running the panel query verbatim through `azure-mcp-kusto` succeeded and returned a sensible single-row result (distinct active tenant count over the 7-day window). No syntax/permission/schema errors.

## Evidence (panel KQL excerpt)
```kusto
TunnelServerOperationEvents
| where TIMESTAMP between (_startTime .. _endTime)
| where DeviceOs has_cs _osType        // _osType = 'ANDROID'
| where ClientVersion in (_application_Version)
| where isempty(_trafficProfile) or ServiceType in (_trafficProfile)
| where isempty(_tenantId)        or TenantId    in (_tenantId)
```

## Implications

### 1. New canonical table on the inventory
`TunnelServerOperationEvents` (NaasProd) is added as the **primary** Android-scoping table for tunnel/connection KPIs. It is richer than expected — also carries `DeviceId`, `ClientVersion`, `ServiceType`, `TenantId`, `LatencyMs`, `Status`, `FlowStatusError`, `FlowErrorClassification`, `OperationName`. Most metric rows on the daily report can be sourced from this single table.

### 2. Version format differs from Windows
Android `ClientVersion` follows `1.0.NNNN.NNNN` (e.g., `1.0.7203.0401`) — fundamentally different from Windows `v2.28.96`. The dashboard's `_application_Version` allowlist enumerates 37 specific Android builds. When the report says "version", on Android it means a 4-segment numeric build, NOT a SemVer tag. Reyes's report template should reflect this when filling the "Android Client Version Distribution Health" row.

### 3. Pivot column-name drift vs URL parameter names
- Dashboard URL says `trafficProfile`; table column is `ServiceType`.
- Dashboard URL says `osType`; table column is `DeviceOs`.
- Dashboard URL says `device_id`; table column is `DeviceId`.
- Time column is uppercase `TIMESTAMP` (a `PreciseTimeStamp` also exists; the panel uses `TIMESTAMP`).

Document URL→column mapping wherever queries quote URL-style names so future readers don't trip on the rename.

### 4. Operator choice: `has_cs` (case-sensitive)
The dashboard uses `has_cs` (case-sensitive contains-token). For Android scoping this is functionally equivalent to `==` but cheaper on indexed tokens. The squad standardizes on `has_cs 'ANDROID'` to match dashboard semantics exactly. Do **not** lowercase to `'android'`.

## Tradeoffs / risks
- This filter only works on tables that carry `DeviceOs` (Tunnel family in `NaasProd`). Aria-envelope tables (`NaaSVPNZtnaConnectionLogsEvent`) still need `env_os == 'Android'` — we now have **two** filter idioms in the codebase, and reusable headers must pick one based on table.
- The `_application_Version` allowlist of 37 builds is hard-coded in the panel — open question whether the dashboard auto-discovers new builds or requires manual curation. Until clarified, our queries either hard-code (matches dashboard exactly) or omit the version filter (broader cohort, may double-count side-loaded debug builds).
- Schema may drift; re-run `kusto_table_schema` weekly via the existing dashboard-as-source-of-truth ceremony.

## Asks
- **Mulder:** ack this filter as canonical so Doggett/Reyes can rely on it.
- **Saloni:** confirm whether the 37-version allowlist is auto-curated or manually maintained (affects whether our queries should hard-code or derive dynamically).
