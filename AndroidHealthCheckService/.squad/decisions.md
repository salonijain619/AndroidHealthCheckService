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

# Decision: GSA Kusto Catalog adopted as canonical table/cluster reference for Android squad

**By:** Scully (Telemetry Analyst)
**Date:** 2026-06-05
**Status:** PROPOSED — pending Mulder ack

## What

Adopt the `gsa-kusto-catalog` skill from the `Identity-gsa-client-marketplace` plugin marketplace as the canonical, single-source-of-truth registry for **all** GSA / NaaS Kusto clusters, databases, tables, time columns, and platform-emission metadata used by this squad. Local skills route through it; they do not duplicate it.

**Upstream path:**
- `/Users/salonijain/workspace/Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-kusto-catalog/`
  - `SKILL.md` (how to consume)
  - `catalog.json` (clusters → databases → tables, aliases)
  - `catalog-semantics.json` (per-column semantics, value enums, join recipes, indexes)

**Local Android slice:** `.squad/skills/gsa-kusto-catalog-android-slice/SKILL.md` — derived subset, Android-relevant routes + filter idioms only. Confidence MEDIUM (derived, not independently re-verified).

## Why

- **Resolves three of our four standing unknowns in one pass:**
  1. PKI source — `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (we had it on the right cluster all along — earlier `kusto_table_list` returned empty for reasons still unclear; catalog routing is verified-good per its own note).
  2. AppInsights component — `wd-prod-android-client` under sub `fb633419-6bb2-4a7e-8993-fd9456d19c4c`. `AndroidId` lives in `customDimensions`, version in `application_Version`.
  3. Aria DB for Android — Android primarily lives in **App Insights**, not Aria. Aria `mnap_xplat_*` is Win/Mac primary; Android appears only opportunistically (e.g., `errorevent` via `App_Platform == 'Android'`). Our prior assumption that Aria is the Android client-side pipeline is **wrong**.
- **Discovers a new cluster we didn't know about:** `androidgsa.eastus.kusto.windows.net / Metric` — Android perf rollups (CPU, mem, throughput) per AppVersion per day. Two tables: `MemoryCPUUsage`, `UploadDownloadSpeed`.
- **Discovers that `naas-idsharedwus / NaasProd` is a 2-table mirror, not the full server-side database.** The full 37-table NaasProd lives on `naas-idsharedscus` (South Central US). Our current panel queries against WUS continue to work for the tunnel/edge tables, but Roxy / Talon / ControlTower / NaaSVPN* / CertMonitor cross-checks require SCUS routing.
- **Avoids drift:** the catalog is maintained by the GSA client team upstream; any cluster URL / db GUID / table change lands there first. Local hard-coding rots silently.
- **Reusable across the squad:** Doggett (Android client engineer), Reyes (report writer), and any future telemetry-touching agent can consume the same registry without re-asking "what's the cluster URL again?"

## Android-specific tables identified (final set after this pass)

| Domain | Cluster / DB / Table | Time column | Android filter |
|---|---|---|---|
| Tunnel (primary KPIs) | `naas-idsharedwus / NaasProd / TunnelServerOperationEvents` | `TIMESTAMP` | `DeviceOs has_cs 'ANDROID'` |
| Edge HTTP (cross-check) | `naas-idsharedwus / NaasProd / EdgeDiagnosticOperationEvent` | `TIMESTAMP` | (no DeviceOs — DeviceId join) |
| APS settings | `naas-idsharedwus / NaasAgentServicesApsProd / AgentGetSettingsOperationEvent` | `TIMESTAMP` | TBD |
| APS ack | `naas-idsharedwus / NaasAgentServicesApsProd / AgentSettingsAckOperationEvent` | `PreciseTimeStamp` | TBD |
| **PKI (was blocked)** | `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` | `PreciseTimeStamp` | TBD (column owed) |
| ZTNA gateway view | `naas-idsharedscus / NaasProd / NaaSVPNZtnaConnectionLogsEvent` | `env_time` | `env_os == "Android"` |
| **Android client-side (primary)** | `android-appinsights / wd-prod-android-client / customEvents` (App Insights REST API) | `timestamp` | implicit (entire pipeline is Android) |
| Android perf rollups (NEW) | `androidgsa.eastus.kusto.windows.net / Metric / MemoryCPUUsage`, `UploadDownloadSpeed` | `ingestion_time()` | implicit |
| Aria error-event cross-check | `aria-prod / naas-prod (db_guid f0eaa9…) / mnap_xplat_telemetryprod_errorevent` | `EventInfo_Time` | `App_Platform == 'Android'` |

## Operational rules

1. **Local skills do not hard-code cluster URLs or db GUIDs.** They name the cluster ID (`naas-idsharedwus`, `aria-prod`, etc.) and let the consumer resolve via catalog.
2. **Conflicts: upstream catalog wins.** If our local slice says one thing and `catalog.json` says another, fix the slice (or open a PR upstream) — don't paper over it.
3. **New routes discovered in our work get PR'd upstream**, not buried in our local `.squad/skills/`. Drift is the failure mode; the slice is for what's actually useful in *daily report* context, not new ground truth.
4. **Aria `database` parameter is the GUID, not the friendly name.** Hard-coding `naas-prod` for the database field returns 400. (Top rationalization in upstream `SKILL.md`.)
5. **Time-column awareness:** `TIMESTAMP` vs `PreciseTimeStamp` vs `env_time` vs `EventInfo_Time` vs `timestamp` vs `ingestion_time()` — wrong column silently returns nothing. Slice documents one per table.

## Tradeoffs / risks

- **Catalog freshness:** `_generated_at` and `_activity_window_days` in `catalog.json` declare a snapshot. If a table flips active → obsolete (or vice versa) between regenerations, our queries can go stale. Mitigation: re-run a cheap `kusto_table_list` weekly on the few tables in the daily report.
- **Slice maintenance burden:** every catalog regeneration upstream means re-deriving the slice. Mitigation: keep the slice small (Android-relevant only), so re-derivation is cheap.
- **Android perf-metrics cluster is catalog-flagged unverified** (DNS failed at generation). We should not promise the daily report uses this signal until we live-verify reachability + schema.
- **Aria-for-Android is exception-only.** The catalog clarifies most `mnap_xplat_*` tables are Win/Mac. If a future query treats Aria as a primary Android source, it will quietly under-count.

## Implications for other agents

- **Doggett:** can drop the open question "where does Android client telemetry land" — it's `wd-prod-android-client` App Insights. Crash signal still owed (Watson is Win32; Android needs Play Console / Crashlytics — open question).
- **Reyes:** the PKI Health report row now has a routing-confirmed source; can wire a `{TBD — pending Scully}` slot to a real cluster/DB/table reference rather than a blocker note. Final query body still owed.
- **Mulder:** ack would let me close two of the "open question" items in `agents/scully/research/dashboard-analysis.md` and refocus the next round on (a) actual KQL validation against PKI/AI/perf clusters and (b) APS schema introspection.

## Asks

- **Mulder:** ack the catalog as canonical so local hard-coding of routes is treated as a code-smell going forward.
- **Saloni:** no new ask — the catalog answered three of the four open routing questions on its own. Next round of validation can proceed against PKI + AI + perf without further unblocks.
# Decision: GSA client telemetry marketplace inventoried; recommended skills to adopt

**By:** Doggett (Android Engineer)
**Date:** 2026-06-05
**Status:** PROPOSED — pending Mulder ack and coordinator approval before any bulk-copy

## Subject

GSA client telemetry marketplace (`Identity-gsa-client-marketplace`) inventoried this cycle. Recommending **0 ADOPT, 2 REFERENCE, 0 SKIP** for the skills in scope (the third skill, `gsa-kusto-catalog`, is owned by Scully this cycle and excluded here).

## What

Inventoried the locally cloned `Identity-gsa-client-marketplace` (`gsa-client-plugins`) — the GitHub Copilot CLI / Claude Code plugin marketplace for the GSA client sub-system. Specifically the `gsa-client-telemetry-toolkit` plugin and its non-`gsa-kusto-catalog` skills. Full inventory: `.squad/agents/doggett/research/marketplace-plugin-inventory.md`.

### Skills in scope and verdicts

| Skill (path under marketplace clone) | Verdict | Justification (one-liner) |
|---|---|---|
| `plugins/gsa-client-telemetry-toolkit/skills/gsa-client-telemetry-toolkit/SKILL.md` | **REFERENCE** | Authoritative for Android telemetry routing (`android-appinsights / wd-prod-android-client`, NOT Aria), Aria's `App_Platform == 'Android'` filter, and `Client_Id` / `DeviceInfo_Id` / `UserInfo_Id` identity rules. Depends on a sibling catalog (`../gsa-kusto-catalog/`) and seven IdentityWiki pages we don't yet have wired up — copying the SKILL.md alone would break those paths. |
| `plugins/gsa-client-telemetry-toolkit/skills/setup-prereqs/SKILL.md` | **REFERENCE** | Canonical bootstrap (Node.js, `kusto-mcp-server`, MCP registration, `az login` per cluster, `gsa-plugins` marketplace, `mcp-setup`, optional `bluebird`). Maintained upstream — forking it invites drift. Link from `.squad/README.md` instead. |
| `plugins/gsa-client-telemetry-toolkit/skills/gsa-kusto-catalog/` | **DEFERRED** | Scully owns this read this cycle. Decision will follow her inventory. |

**Net adoption count:** 0 ADOPT, 2 REFERENCE, 0 SKIP.

### Concrete integration plan (no copies in this run)

1. **Update** `.squad/skills/android-kusto-starter/SKILL.md` to reference the toolkit SKILL by absolute path for routing/identity/Aria rules, and add a `## KNOW` callout that Android client telemetry actually lives in App Insights `wd-prod-android-client` — our existing seven NaasProd server-side queries are *complementary* to, not replacements for, that App Insights data. Retrofit the file to the marketplace's KNOW/DO/CHECK/Common Rationalizations/Red Flags shape on the next dedicated pass.
2. **Update** Scully's, Doggett's, and Skinner's charters to point at the toolkit SKILL for cross-platform identity rules and at `wd-prod-android-client` as the home of Android client telemetry.
3. **Link** to `setup-prereqs/SKILL.md` from `.squad/README.md` (or wherever onboarding lives). Do not author our own bootstrap doc.
4. **Adopt the marketplace's SKILL.md format** (KNOW / DO / CHECK / Common Rationalizations ≥3 / Red Flags ≥3, body < 500 lines, frontmatter description ≤ 250 chars) for any new `.squad/skills/` we author going forward, and retrofit existing skills opportunistically.

## Why

- Saloni flagged that pre-built Squad-style assets for GSA already exist; the marketplace clone is exactly that asset class. Reusing by reference (a) avoids forking maintained upstream content, (b) lets the catalog-reuse rule from the marketplace's `AGENTS.md` apply unchanged to our squad, and (c) keeps our SKILL footprint small.
- The toolkit independently confirms Saloni's framing that GSA Android lives inside Defender's telemetry stack — the Android cluster name `wd-prod-android-client` carries the WD (Windows Defender) brand. This is the strongest evidence we've had to date that doesn't require WD.Client.Android repo access.
- Copying skills that depend on a sibling catalog (`../gsa-kusto-catalog/catalog.json`) and on `ADOProd-wiki_get_page_content` MCP tooling would be lossy. REFERENCE preserves the dependencies; ADOPT would break them.

## Tradeoffs / risks

- **Reference paths drift if the marketplace clone is moved or pruned.** Mitigation: the marketplace upstream URL is captured in the inventory file (`Identity-gsa-client-marketplace`); a re-clone restores the reference target.
- **No execution capability gained yet.** Reference-only adoption means our skills *cite* the toolkit's rules but don't execute against `kusto-execute_query` until `mcp-setup` is run by squad members. That is the same constraint we already have; not a regression.
- **Format retrofit is real work.** Adopting KNOW/DO/CHECK/Rationalizations/Red Flags everywhere is non-trivial. Proposing opportunistic retrofit, not a single-shot rewrite.

## Not deciding

- Anything about `gsa-kusto-catalog` — Scully owns that this cycle, separate decision will follow.
- Whether to publish a Squad-authored plugin upstream into `gsa-client-plugins`. Premature; needs at least one stable, tested squad asset before we'd consider it.
- Final shape of the `android-kusto-starter` retrofit — proposing the link-and-callout step now; the structural retrofit is a separate scoped task.

## Asks

- **Mulder:** ack the REFERENCE-only posture and the integration plan above (charter updates, README link, starter-skill callout). No bulk-copy until you ack.
- **Coordinator:** schedule the three charter updates and the `android-kusto-starter` callout as a follow-up batch.
- **Saloni:** when ready, unblock WD.Client.Android — that's still the gating dependency for the on-device emitter / crash reporter / `EventName` constant inventory. The marketplace does not substitute.

## Cited paths

- Marketplace root: `/Users/salonijain/workspace/Identity-gsa-client-marketplace/`
- Marketplace `AGENTS.md`: `/Users/salonijain/workspace/Identity-gsa-client-marketplace/AGENTS.md`
- Toolkit README: `/Users/salonijain/workspace/Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/README.md`
- Toolkit SKILL.md: `/Users/salonijain/workspace/Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-client-telemetry-toolkit/SKILL.md` (Android routing line 96, App_Platform rule line 69, identity rules line 70)
- Setup-prereqs SKILL.md: `/Users/salonijain/workspace/Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/setup-prereqs/SKILL.md`
- Inventory artifact: `.squad/agents/doggett/research/marketplace-plugin-inventory.md`
- Discovery delta: `.squad/agents/doggett/research/defender-android-discovery.md` § "Marketplace Discovery (2026-06-05)"

---


---

> **CLARIFICATION (appended 2026-06-05T12:55:00Z by Scribe):** the line above (in the "GSA Kusto Catalog adopted" decision) stating that "Android client-side primary = App Insights `wd-prod-android-client` REST endpoint" is **partially superseded** by the 2026-06-05 ICM baseline adoption decision below. Both Scully and Doggett independently confirmed `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` as the canonical Android client telemetry cluster — Kusto-queryable via `azure-mcp-kusto`. App Insights `wd-prod-android-client` is demoted to cross-check status. Prior entry left intact for historical context.

---

### 2026-06-05: Defender-for-Android ICM baseline queries adopted as canonical client-side starting point
**By:** Scully (Telemetry Analyst)
**Status:** PROPOSED — pending Mulder ack
**Supersedes (partially):** the "App Insights `wd-prod-android-client` REST endpoint is primary for Android client telemetry" element of the prior "GSA Kusto Catalog adopted" decision above. Catalog routing is still valid as reference; ICM-vetted ADX routing is now operationally preferred.

**What:** Adopt the Defender-for-Android livesite team's `IcmBaselineQueries.md` (30 KQL queries across triage / tenant / device / domain / correlation / NaaS-call-site sections) as the canonical starting point for **client-side** telemetry in the daily Android GSA livesite report. 22 of 30 queries map directly to specific report sections (Key Metrics, Top Insights, Cross-Domain, Drilldown); 2 are utility (E3 search, C1 device-lookup); 1 is off-charter (D4 malware-scan); rest serve drilldown.

**Source:** `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/agent-docs/IcmBaselineQueries.md` (+ Telemetry.md, TelemetrySubtables.md for schema).

**Why:**
- **Production-vetted** by the Defender-for-Android livesite team — higher confidence than any locally-derived starter.
- **Kusto-native client-side surface.** ICM points to `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` — an ADX cluster reachable via `azure-mcp-kusto`. Unblocks programmatic execution of Android client telemetry queries from our MCP toolchain.
- **NaaS coverage built-in.** Section N (12 queries) maps Android NaaS call sites (NaaSVPNClient, NaaSAuthenticator, NaaSDNSResolver, NaaSCertificateHandler, NetworkChangeEventListener, NaaSViewModel, etc.) to event names + distinguishing fields.
- **Subtable routing built-in.** ICM uses MDATPAndroidDB's 10 routed subtables (TelemetryAuth, TelemetryVPNAndWebProtection, TelemetryHeartbeat, …) — pre-unpacked properties, faster than `customEvents | bag_unpack`.

**Artifacts:**
- `.squad/skills/android-kusto-starter/SKILL.md` restructured: Part 1 server-side (#1–#8, #10, #11 retained, sourced/confidence-tagged) + Part 2 client-side (30 new CL-A1…CL-N12 at HIGH confidence). Section-index table at top maps every report row to feeding query IDs.
- `.squad/skills/android-icm-baseline-mapping/SKILL.md` — NEW (confidence MEDIUM). Cross-reference table ICM query → report section → cluster/subtable + rationale + coverage-gap notes.
- `.squad/agents/scully/research/dashboard-analysis.md` — appended "ICM Baseline Catalog (2026-06-05)" section.

**Conflicts called out explicitly:** App Insights routing demoted to cross-check (both routes likely view same underlying SDK emissions — Defender uses `MDAppTelemetry`, ADX is the routed/exported view; operational preference is ADX). Starter #9's standalone AI query is folded into the demoted-AI cross-check row. ICM CL-A3 unblocks the previously-missing crash signal. PKI Health row now runs starter #8 (server) AND CL-N9 (client) — divergence is itself a finding.

**Tradeoffs:**
- One repo's vetting ≠ our vetting; some queries (CL-D4) are off-charter and tagged in the mapping skill.
- Coupling to upstream churn — re-read `IcmBaselineQueries.md` at the Defender team's cadence.
- `androidId` may be truncated by 3 chars (ICM footnote) — cross-cluster joins on `DeviceId`/`androidId` must handle.
- `mdatpandroidcluster` reachability from our MCP not yet smoke-tested — owed.

**Asks:** Mulder — ack precedence rule (ICM > catalog > squad-original). Doggett — pair server+client signals in correlation. Reyes — use the section-index in `android-kusto-starter` as source of truth for "which query fills which row." Saloni — confirm `azure-mcp-kusto` can auth against `mdatpandroidcluster.westus2.kusto.windows.net`.

---

### 2026-06-05: Defender-for-Android telemetry docs ingested; discovery questions resolved
**By:** Doggett (Android Engineer)
**Status:** PROPOSED — pending Mulder ack
**Independently confirms:** `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` as the canonical Android client telemetry cluster (same as Scully's ICM-derived finding). Two independent paths to the same fact strengthens confidence on the supersession of the prior App-Insights-only assumption.

**What:** Ingested the `agent-docs/` directory from the locally-cloned `WD.Client.Android-icm-copilot` mirror (8 docs: Telemetry, TelemetrySubtables, TelemetryNewTable, AggregatedTableInfra, FeatureFlags, CodingStandards, BuildSteps, Testing). New squad artifacts:
- `.squad/agents/doggett/research/android-telemetry-model.md` — 1-page mental model + routing cheat-sheet + starter KQL for Reyes / Skinner / Mulder / Scully.
- `.squad/skills/android-version-regression-detection/SKILL.md` — NEW (confidence LOW). Android analog of the Windows v2.28.96 version-regression playbook: ClientVersion pivot + ECS flag-evaluation diff + flag-gating concentration test + mitigation routing.
- Updated `.squad/agents/doggett/research/defender-android-discovery.md` with "ICM-Copilot Doc Discovery (2026-06-05)" section closing 13 open questions (4 RESOLVED / 5 PARTIAL / 4 STILL-BLOCKED).

**Why:** The marketplace clone (prior pass) gave *destination* routing. The icm-copilot mirror gives the *full pipeline* — emit conventions, raw → subtable → aggregated infra, feature-flag rollout model, build/test conventions. Unblocks every discovery question that didn't strictly require WD.Client.Android *source*.

**Key resolutions (RESOLVED 4):**
1. **Android telemetry helper:** `MDAppTelemetry.trackEvent(name, props[, Flags])` + `.trackEventException(name, throwable)`. Higher-level wrappers `TelemetryUtils.track()` / `CombinedTelemetryUtils.trackCombinedEvent()` (mockkStatic-testable). Event names + property keys codegen'd from `WD.Mobile.Xplat.Infra`; hardcoded strings PR-blocking.
2. **On-device emitter:** **1DS for Defender events, Aria for Tunnel events.** Both via `MDAppTelemetry`. `wd-prod-android-client` AI is downstream of 1DS, not a direct emitter.
3. **KQL checked into repo:** Yes — embedded in `libraries/AggregatedTables/*.py` (aggregation) and `libraries/Alerts/*.py` (alerts). PR-validated via `ValidateKqlQueryADX.py`. Outputs to `"dashboard"` + `"alerts"` folders in MDATPAndroidDB.
4. **Pipeline architecture:** 3 layers, 1 cluster. `customEvents` (raw, JSON props) → 10 domain subtables (update policies + `bag_unpack`) → aggregated tables (Azure Function `KustoQueryFunc`, hourly modulo-scheduled). Cluster: **`mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB`**. GSA lives in `TelemetryVPNAndWebProtection`. ECS feature flags target by `ClientVersion` — enables Windows-v2.28.96-style version-regression detection on Android.

**Still blocked (4):** VSTS read on WD.Client.Android; sign-off on the seven proposed Android-specific report fields; out-of-band crash uploader confirmation (Crashlytics suspected); `.squad/`/`skills/`/`plugins/` dir enumeration inside WD.Client.Android.

**Risks:** icm-copilot mirror may be a snapshot, not live; verify against upstream once VSTS lands. Version-regression skill unvalidated against a real regression (confidence LOW; pair with Scully on first use). Event/property names in starter KQL illustrative — `bag_unpack | take N` check required before relying on them.

**Asks:** Mulder — ack. Reyes — cite `android-telemetry-model.md` for any report section touching Android telemetry routing.

---

---

### 2026-06-05: First executable Android NAAS-only daily livesite report assembled
**By:** Reyes (Report Writer)
**Date:** 2026-06-05T13:45Z
**Status:** PROPOSED — pending Mulder/Saloni review
**Confidence:** medium-high (real data from Scully's NAAS-only execution; scope-limited; 0 fabricated numbers)
**Supersedes:** none (additive — v1 is the first executable report cycle)

**What:** Assembled the first executable Android GSA Daily Livesite Report against Scully's freshly-executed NAAS 7-day data, in the Windows-reference report style.

**Sections filled with real numbers:** Active Devices (27,489) / Active Tenants (1,241) / Tunnel Events (130.05M) / Tunnel Health (99.711%) / APS (99.997% Get-Settings / 99.99966% Ack) / PKI Health (✅ 0.0007% error) / Version Distribution Health / Business Growth (weekday/weekend patterns).

**P-level findings:**
- **P2 (anchor):** Tunnel server-side failure-rate ~5× ramp over 7d (0.074% → 0.36%). Top Insight #1.
- **P2:** Private Access ~4× M365 failure rate (0.688% vs 0.174%).
- **P2:** `PROFILE_UNDEFINED` 100% failure (4,003 events / 245 devices) — config-bootstrap race.
- **Info:** Ghost-column defect on `TunnelServerOperationEvents` (`FlowStatusError`, `LatencyMs`, `Msg` unqueryable).

**TBD count:** 4 explicit markers — all gated by Defender-client-side scope lock or schema defects.

**Report file:** `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-05.md`

**Asks:** Mulder ack format/scope. Saloni review v2 unblockers: (1) Defender-client-side scope unlock, (2) SCUS hop authorization, (3) on-call config, (4) ghost-column defect filed.

---

### 2026-06-05: NAAS-only 7d Android report data captured
**By:** Scully (Telemetry Analyst)
**Date:** 2026-06-05T13:30Z
**Status:** Adopted
**Confidence:** medium-high (real data from live clusters; 0 fabricated numbers)
**Supersedes:** none (additive — first executable data run)

**What:** Executed the NAAS-server-side, Android-filtered, all-tenants slice for a 7-day window (2026-05-29T13:26Z .. 2026-06-05T13:26Z UTC).

**Clusters hit:** `idsharedwus.kusto.windows.net` — 3 databases (`NaasProd`, `NaasCloudPkiProd`, `NaasAgentServicesApsProd`).

**Queries:** 20 attempted, 17 passed, 5 recovered (column discovery/casing), 0 final failures. All 22 ICM client-side queries dropped per scope lock (NAAS-only).

**Key findings:**
1. Tunnel failure ~5× ramp (0.074% → 0.36% sustained); 12× volume growth vs 2.6× traffic growth.
2. Fleet: 27,489 active devices / 1,241 tenants / 130.05M events / 99.711% success.
3. Private Access fails 4× vs M365 (0.69% vs 0.17%); `PROFILE_UNDEFINED` = 100% failure (4,003 events).
4. APS: 270.3M Get-Settings at 99.997%; 268.6M Ack at 99.99966%.
5. PKI: 595,712 events, 4 errors (0.0007%) — healthy.

**Caveats:** Ghost columns on `TunnelServerOperationEvents` (`FlowStatusError`, `LatencyMs`, `Msg`). Region casing duplicates. APS schema diverges (missing `HttpResponseStatusCode`). PKI `DeviceId` empty on Android.

**Data file:** `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md`

---

### 2026-06-06: First live ICM pull for team 106961
**By:** Scully (Telemetry Analyst)
**Date:** 2026-06-06T10:07Z (ICM server timestamp)
**Status:** PROPOSED — pending Mulder ack
**Confidence:** medium (first live run; verify on second pull next cycle)

**What:** First live ICM data pull executed for queue **106961** ("GSA Client - Android") via the HarryPotter-pattern collector, ported into `tools/icm/` under squad root.

**How:**
1. Ported `livesite/scripts/icm_collector.py` (HP commit d35a114) → `tools/icm/icm_collector.py` with `team_id 115956→106961`, `team_name`, `env AHCS_ICM_TEAM_ID`, `client-name`, config path `.squad/config.json`. No change to: JSON-RPC handshake, `WARMUP_DELAY_S=6`, `tools/list`-then-sleep-then-`tools/call` ordering, D-138 no-`dateRange` discipline.
2. Ported test suite (19 tests) → `tools/icm/tests/test_icm_collector.py`. **All 19 tests pass**, including 3 D-138 regression tests.
3. Created `.squad/config.json` with `icm.team_id=106961` as single source of truth (CLI > env > config > default).
4. Live run: 26s elapsed, exit 0, raw JSON at `tools/icm/runs/icm-run-2026-06-06.json`.

**Headline numbers:**
- **Active+Mitigating:** 1 ICM (Sev3, customer-reported, TestICM-flagged [#810723164], 5d old, unacknowledged).
- **Mitigated:** 0
- **On-call:** Primary `dileepkusuma`, Backup `samirnen`.
- **Effective real-incident count after TestICM filter:** **0**

**Caveats:**
- **Bucketing bug (port-faithful):** collector buckets by `source startswith "customer"`; ICMProd returns `type=CustomerReported`. Lone ICM lands in `system_created_active` array. Raw `type` preserved — Doggett/Reyes can re-bucket v2.1.
- **Team-name drift:** `owningTeamId=106961` returns `owningTeamName="GSA  Client - XPlat"` (double-space typo). Saloni to confirm 106961 is Android vs XPlat parent.
- **Detector silence is suspicious:** Zero system-detected ICMs while NaaS shows 0.36% tunnel failure (5× ramp). Mulder/Skinner ack owed.

**Collector:** `tools/icm/icm_collector.py`
**Tests:** `tools/icm/tests/test_icm_collector.py`
**Config:** `.squad/config.json`
**Raw JSON:** `tools/icm/runs/icm-run-2026-06-06.json`
**Structured data:** `.squad/agents/scully/research/icm-team-106961-data-2026-06-06.md`

---

### 2026-06-06: icm-queue-ingest skill authored
**By:** Doggett (Android Engineer)
**Date:** 2026-06-06T11:25Z
**Status:** Adopted
**Confidence:** MEDIUM

**What:** Authored `.squad/skills/icm-queue-ingest/SKILL.md` formalizing the HP-ported ICM collector pattern (`agency mcp icm` stdio JSON-RPC, 5-step handshake with 6s warmup, 4-tool sequence: `search_incidents` ×2 / `get_on_call_schedule_by_team_id` / optional `get_ai_summary`, no `dateRange` per D-138) for ICM team `106961` ("GSA Client - Android").

Single source of truth for `team_id` is `.squad/config.json :: icm.team_id` with override hierarchy: CLI > env `AHCS_ICM_TEAM_ID` > config > default. Confidence MEDIUM because upstream pattern is regression-tested by HP but our first live run lands today; promote to HIGH after one clean unattended cycle.

**Implications for squad:**
- **Scully** executes the collector per report run; skill is her operational reference.
- **Reyes** consumes the envelope to populate `📟 On-Call Today` and `🚨 Active ICM Incidents`.
- **Skinner** owns `Patterns:` narrative bullets once live incident lands.
- **Doggett** owns skill-doc maintenance; future MCP drift, auth modes, or upstream ICM changes are skill-doc updates.

**Artifacts:** Skill at `.squad/skills/icm-queue-ingest/SKILL.md`. Discovery lineage in `.squad/agents/doggett/research/harrypotter-icm-port-plan.md`.

---

### 2026-06-06: Adopt HarryPotter's `agency mcp icm` pattern as new skill icm-queue-ingest
**By:** Doggett (Android Engineer)
**Date:** 2026-06-06T11:18Z
**Status:** Adopted
**Confidence:** HIGH on pattern (fully reverse-engineered from working sibling-squad implementation with passing tests); MEDIUM on first-run UX (depends on Saloni completing one-time Entra browser auth)
**Supersedes:** none

**Context:** Reyes's v1 Android livesite report ships with no Active ICMs section and explicit `TBD` for On-Call. Saloni's ICM team queue `106961` is corp-SSO-walled. HarryPotter sister squad solved the equivalent problem for macOS team `115956` at `/Users/salonijain/workspace/HarryPotter`.

**Decision:**

Adopt HP's pattern wholesale, parameterized on our team id:

1. **Auth/transport:** drive Microsoft-internal `agency mcp icm` (stdio JSON-RPC, Entra interactive auth on first run, token cached thereafter). Reject three dead-end alternatives HP proved out (ICM REST + `az` token, hypothetical `icm-mcp-server` binary, `agency tool` subcommand) — keep their history-of-removed-paths in our ported skill doc.
2. **Code port:** copy `livesite/scripts/icm_collector.py` (290 lines mechanics, 290 lines orchestration) and `tests/test_icm_collector.py` near-verbatim. Substitute `team_id 115956→106961`, `team_name`, env `HP_ICM_TEAM_ID→AHCS_ICM_TEAM_ID`.
3. **Skill port:** create `.squad/skills/icm-queue-ingest/SKILL.md` from HP's `icm-via-mcp/SKILL.md` (24-tool catalog, handshake with `WARMUP_DELAY_S=6`, failure-mode table, history).
4. **Template port:** Reyes adds two sections to report template — `📟 On-Call Today` (replacing `TBD`) and `🚨 Active ICM Incidents` with three sub-tables + Patterns bullets.
5. **Topology:** no new agent. Scully runs collector; Doggett owns skill; Reyes owns template; Skinner owns narrative. Config at `.squad/config.json :: icm.team_id` with CLI/env override hierarchy.
6. **Port D-138 verbatim:** Active and Mitigated `search_incidents` calls must not include `dateRange.createdAfter`. Use `top:50` + `sortBy LastModifiedDate Desc` for Mitigated. Mirror regression tests.

**Rationale:** HP's collector battle-tested (12 unit tests, D-138 coverage, partial-degrade contract). `agency` CLI already present. No new secrets/PATs/webhooks. Pattern is the only path HP found that works; their `History` documents three failed alternatives.

**Pre-reqs (asks of Saloni):**
1. One-time interactive `agency mcp icm` to complete Entra browser auth.
2. Confirm corp identity has read on ICM team `106961`.
3. Greenlight first live collector run under her credentials.

**Out of scope:** Teams/Email delivery (separate); `.squad/cache/icm-last-good.json` cache layer (defer to v3); cross-reference active ICMs with KQL telemetry (narratively, v3 programmatic).

**Discovery artifact:** `.squad/agents/doggett/research/harrypotter-icm-port-plan.md`

---

### 2026-06-06: v2 NAAS + ICM Report Assembled
**By:** Reyes (Report Writer)
**Date:** 2026-06-06T11:50Z
**Status:** PROPOSED — pending Mulder ack
**Supersedes:** none

**What:** v2 of the daily livesite report assembled at `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-06.md`. NAAS analysis from v1 preserved verbatim (window: 2026-05-29T13:26Z → 2026-06-05T13:26Z). Three new live-ICM sections added, sourced from Scully's first pull against team 106961 via ported HarryPotter collector.

**What's new vs v1:**

1. **`📟 On-Call Today`** — replaced `TBD/TBD` with live roster: Primary `dileepkusuma`, Backup `samirnen`, from `get_on_call_schedule_by_team_id(106961)`.
2. **New top-level `🚨 Active ICM Incidents`** section with:
   - Counts (1 active total, Sev3, customer-reported, TestICM-flagged)
   - Three tables: Customer-Created Active (1 row, #810723164), System-Created Active (empty), Mitigated Highlights last 7d (empty, genuine per D-138)
   - Bucketing footnote on `source` vs `type` mismatch; v2.1 fix queued
   - 5 Patterns bullets: detector-silence, aging-without-ack, queue-identity open question
3. **`Data Quality Notes`** extended with `ICM Integration (v2 — first cycle)` sub-section + 2 new Open Questions (queue identity, detector→ICM correlation).
4. **Contributors** appended with Doggett (port-plan + skill), Scully (collector port + first pull), Reyes (v2 assembly).

**Headline ICM situation:** **Effective real-incident count on team 106961 = 0** (one Active Sev3 is TestICM), but **detector silence on a 5× tunnel-failure ramp is itself a finding** — flagged for Mulder/Skinner.

**Queue identity question for Saloni:** `owningTeamId=106961` returns `owningTeamName="GSA  Client - XPlat"`, not "GSA Client - Android". Confirm 106961 is the right Android queue vs an XPlat parent with Android sub-queue. If sub-queue exists, entire ICM section scoped to wrong target.

**For v2.1/v3:**
- **v2.1 (collector):** swap bucketing from `source startswith "customer"` to `type == "CustomerReported"`.
- **v2.1 (scope):** re-target ICM pull to Android sub-queue once Saloni confirms.
- **v3:** wire detector → ICM correlation (cross-check NAAS ramps vs ICM creation).
- **v3:** re-pull telemetry alongside ICM each cycle.

**Report file:** `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-06.md`
**Raw JSON:** `tools/icm/runs/icm-run-2026-06-06.json`
**Structured data:** `.squad/agents/scully/research/icm-team-106961-data-2026-06-06.md`

---

## 2026-06-08 — NAAS Kusto reachability blocker (RESOLVED)

**Filed by:** Scully  
**Status:** RESOLVED — cluster reachability restored 2026-06-09  
**Source:** `.squad/decisions/inbox/scully-naas-kusto-reachability-blocker-2026-06-08.md`

**Incident:** `idsharedwus.kusto.windows.net` cluster unreachable at TCP layer on 2026-06-08T12:00Z. Two `azure-mcp-kusto` queries and direct `curl` attempts all returned HTTP 503 / `Operation timed out (idsharedwus.kusto.windows.net:443)`.

**Root cause:** Corporate VPN/firewall egress filtering. Cleared overnight 2026-06-09 by Saloni.

**Verification:** 2026-06-09T09:11Z — HTTP 401 unauth challenge confirmed (port 443 TCP reachable), all three Kusto databases queried successfully.

**Impact on reporting:**
- 3 days of NAAS telemetry (2026-06-06..2026-06-08) unavailable for real-time analysis
- v1 baseline (last-good = 2026-06-05) served as "no movement detected" floor
- v3 NAAS pull executed post-unblock with fresh 7d window (2026-06-02..2026-06-09)

**Legacy artifacts:** `naas-7d-report-data-2026-06-08.md` retained as blocked-stub (documented yesterday's attempt; superseded by 06-09 drop).

---

## 2026-06-09 — NAAS tunnel failure-rate ramp escalating: second-step confirmed, 1P hypothesis falsified (ACTIVE)

**Filed by:** Scully  
**Status:** ACTIVE — P2 trending toward P1  
**Source:** `.squad/decisions/inbox/scully-naas-ramp-second-step-20260609.md`

**Headline:** Re-running v1 query suite over 2026-06-02..2026-06-09 (7d closed window) confirms tunnel failure-rate ramp continues past v1 plateau, reaching **0.447% on 2026-06-08** (highest single-day rate in 11d observation).

**Key findings:**
1. **Ramp escalation confirmed:** 0.074% (5/29) → 0.36% plateau (6/02–6/04) → **0.385% (7d total), +35% failures vs prior 7d** — all-quality-driven (traffic essentially flat).
2. **Microsoft 1P hypothesis FALSIFIED:** S6b non-1P probe shows fail-rate 0.49–0.60%, HIGHER than 0.39% global. Regression is platform-wide, not dogfood-rollout artifact.
3. **Strongest single-version anchor:** `1.0.9003.0401` (`.04xx` ring) cohort +55% growth, fail-rate +131% (0.271% → 0.626%). Concentrated in 2 tenants (likely internal ring).
4. **EU regions intensifying:** germanywestcentral +67%, NorthEurope +61%, SwedenCentral +114%. UK South remains largest absolute (118K fails/7d).
5. **Detector silence confirmed across 3-pull span** (06-05, 06-06, 06-08): no ICM incidents flagged while server-side ramp crosses 0.44%.
6. **Ghost columns unfixed 4 days:** `FlowStatusError`, `FlowErrorClassification`, `LatencyMs`, `Msg` still SEM0100 on `TunnelServerOperationEvents`. Recurring DQ issue upstream.

**Immediate actions:**
- **Mulder (triage):** Investigate tenant `9cf9036f-5fc5-475d-846d-94ea941e4bfc` (105 fails/device, 45 devices) and `0e17f90f-…` (+40% failures, 165/device).
- **Doggett (ring owner):** Identify `.04xx` build flavor and `1.0.9003.0401` identity (likely internal ring, 2 tenants).
- **Skinner (incidents):** Treat detector silence as confirmed routing gap; escalate to platform team.
- **Platform (escalation):** Ghost columns + Region casing upstream defects, 4 days unfixed.

**Source files:**
- Current drop: `.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md`
- v1 baseline: `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md`

---

### 2026-06-09: Canonical Android crash source is google-play-vitals
**By:** Scully (Telemetry Analyst)
**What:** Canonical Android crash source for this assignment is the `google-play-vitals` skill at `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`, not `telemetry-query` / AppEvents.
**Why:** Use Play Console vitals for user-perceived crash and ANR rates, affected users, and Play-deduped issue clusters. Keep AppEvents / CrashReported only as supplementary internal exit telemetry.

---

### 2026-06-09: Android NAAS crash filter decision — VPN orchestrator marker
**By:** Scully (Telemetry Analyst)
**What:** Use Android App Insights workspace `android-release-log-analytics-workspace` / `AppEvents` as the aggregate NAAS crash source, filtered by `.vpn.VpnServiceOrchestrator` in `AppExitInfoReported.Description` or `CrashReported.StackTrace`.
**Why:** Package/process `com.microsoft.scmx` is too broad; Google Play crash skills require known issue IDs and are better for follow-up triage. The VPN orchestrator marker is a tighter NAAS-on-Android predicate for weekly reporting.
**Result:** 18,518 AppExit/ANR events and 952 JVM crash events in the 7d window ending 2026-06-09. Top signatures are not new versus prior baseline and do not align with the `1.0.9003.0401` `.04xx` server-side fail anchor.

---

### 2026-06-09: Publish NAAS Android crash root-cause pattern in v3 report with caveats
**By:** Scully (Telemetry Analyst)
**Status:** GO for v3 / next-week report
**What:** Google Play vitals issue-level depth now explains the NAAS crash causes, not just volumes. The dominant crash subsystem is `VpnServiceOrchestrator`: Android foreground-service enforcement kills the VPN service when `onStartCommand()` starts foreground work but does not reach `startForeground()` in time, with a smaller related `pthread_create` resource-exhaustion cluster. The dominant ANR subsystem is `OpenVPN/BaseOpenVpnClient`: native VPN library load/init blocks the main thread during app/service startup.
**Caveats:**
- Play exposes issue-level distinct users but not issue-level installs.
- Native `libnaas_native_vpn.so` SIGSEGV needs symbolication for exact function.
- OEM/OS findings are concentration-only until normalized by install base.
- `.04xx` over-indexes in crash rate and native SIGSEGV share, but is not the dominant absolute crash-volume driver.

---

### 2026-06-10: Team expansion — Frohike + Langly hired
**By:** Saloni (via Copilot/Squad)
**What:** Two new team members added to cover client-side reporting gaps.
- **Frohike (Play Vitals Analyst)** — owns Google Play Console crash/ANR analysis, NAAS-filtered. Replaces Scully's ad-hoc ownership of Play Vitals data. Source-of-truth skill: `WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`. Drops at `.squad/agents/frohike/research/naas-crashes-{date}.md`.
- **Langly (Release Tracker)** — pulls current Play Store version of `com.microsoft.scmx` on every report cycle. Surfaces as a one-line header in every daily/weekly report. Lightweight, recurring role.
**Why:** (1) Saloni wanted NAAS-only Play Console crash reporting as a permanent first-class section in the daily report, not a one-off Scully task. (2) Reports need to anchor against the currently shipping Defender version — otherwise crash data lacks context.
**Routing change:** Reyes now pulls from Scully (server) + Frohike (Play crashes) + Langly (current version) in parallel for every report. ICM investigations now also fan out to Frohike for client crash signature.
**Framing rule (carries over from Scully's crash-iteration learnings):** All Play Vitals output MUST be NAAS-as-a-unit, never Defender-filtered-to-NAAS. Per-Defender-version table is the PRIMARY deliverable, not an appendix.

