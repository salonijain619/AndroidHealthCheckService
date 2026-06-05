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
