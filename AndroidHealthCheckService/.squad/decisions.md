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
