# reyes — Learnings

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

- On-Call section: keep the table, drop the sourcing/freshness prose. Saloni wants the data, not the metadata.
- v3 trim — Saloni wants ICM data-first (table over prose), no on-call section in weekly cadence, no DQ tail. Pattern for v4+: lead with data, push commentary into Top Insights / Cross-Domain only.

### 2026-06-05: Daily Livesite Report Skeleton Established
**Template files created:**
- `.squad/templates/daily-livesite-report.md` — canonical skeleton with placeholders for metrics, insights, and correlations
- `.squad/templates/daily-livesite-report-EXAMPLE.md` — fully-filled example (Android v6.2.1 auth regression scenario) to show narrative flow and how data fills in

**Template structure (mirrors Windows squad):**
1. Header with date/day and on-call roster (Primary/Backup)
2. Executive Summary — 3–4 critical/high issues + fleet health + 1 additional insight (emojis + blast radius)
3. Key Metrics table — 7 rows: active clients, fleet errors (7d), APS availability, PKI, tunnel, Android version distribution health, business growth (7d)
4. Top 5 Insights — severity table with title, blast radius, owner/action columns
5. Cross-Domain Correlation Analysis — primary chain + timeline + evidence + validation steps
6. Data Quality Notes — sources, completeness caveats, open questions, schema drift flags
7. Contributors footer + timestamp

**Placeholder tokens introduced:**
- `{TBD — pending Scully telemetry}` for all metric values (active devices, error counts, availability %)
- `{TBD — pending Skinner}` for incident severity/classification
- `{TBD — pending Doggett}` for technical diagnosis (auth, policy, cascade analysis)
- `{TBD}` for narrative / open unknowns

**Android-specific adaptations vs. Windows template:**
- Metric: "Active Android Clients (weekday)" instead of generic "Active Devices"
- Added row: "Android Client Version Distribution Health" (tracks version-specific error rates; flagged v6.2.1 vs. v6.0.8 in example)
- Contributors: listed as Mulder, Scully, Doggett, Skinner (Reyes omitted since I assemble but don't author data)
- Cross-domain example: Android v6.2.1 auth → APS policy → notification channel (vs. Windows tray icon)
- Data Quality section includes Android-specific open questions (Play Store vs. sideload channel tracking, OS version health baselines, OEM/device model variance)

**Open Android questions for Scully to address in Data Quality Notes:**
1. Should Play Store vs. sideload/MAM channel adoption be segmented in the daily report? (Risk: loss of signal if channels run different client versions.)
2. Android OS version split health tracking — do we expect error rates to vary by API level? Baseline expectations?
3. Device model/OEM error variance — reportable signal or noise? (Example data: Samsung/Pixel 0.2% vs. Motorola/OnePlus 6.1% auth failure — locale/firmware impact?)

**Example scenario walkthrough (for reference):**
v6.2.1 auth token validation bug → 401/403 errors block APS policy fetch → offline cache exhausted → notification delivery fails (codes 634/635/636) → clients frozen in error state. Timeline: rollout 2026-06-04 18:30 UTC → first error spike 22:15 UTC → APS fail 23:45 UTC → notification spike 02:30 UTC (3.5h lag due to cache exhaustion). Blast: 50K v6.2.1 devices, 8.1% of that version's fleet, cascading to 98K dependent policy requests.

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

## 2026-06-08T16:23Z — Scribe: Session log + orchestration records

Scribe wrote a session log covering the 2026-06-06 multi-day arc (HP discovery, skill authoring, collector porting, v2 report assembly) and four orchestration logs for the agent spawns. Inbox decision files merged into `decisions.md`. Key metrics: 6 inbox files processed, 4 orchestration logs written, no archiving (all entries within 30-day threshold). Next cycle: confirm queue identity (106961 Android vs XPlat parent), investigate detector silence (0 system ICMs vs 5× tunnel failure ramp), v2.1 collector bucketing fix.


## 2026-06-05T12:55:00Z — Cross-agent: ICM baseline + Android telemetry architecture
Scully + Doggett ran in parallel against `WD.Client.Android-icm-copilot/agent-docs/`. Two convergent findings + two new skills:
- **CORRECTION:** Android client telemetry IS ADX-queryable via `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Kusto, via `azure-mcp-kusto`). Both agents independently confirmed this. Supersedes the prior "Android client = App Insights `wd-prod-android-client` REST endpoint only" assumption — AI is now cross-check status.
- **GSA's home subtable:** `TelemetryVPNAndWebProtection` (`Vpn*`/`Tunnel*`/`Naas*`/`Edge*` events route here via Kusto update policies + `bag_unpack`). 10 domain subtables total under MDATPAndroidDB.
- **22 of 30 Defender-vetted ICM queries** now mapped to specific daily-livesite-report sections — see Scully's new `android-icm-baseline-mapping/SKILL.md` and the section-index table at the top of `android-kusto-starter/SKILL.md`.
- **Version-regression detection pattern** for Android (analog of Windows v2.28.96 playbook) — see Doggett's new `android-version-regression-detection/SKILL.md` (confidence LOW; pairs Doggett+Scully on first use). Uses ECS feature-flag `ClientVersion`-targeting + per-version metric divergence.
- Decisions `scully-icm-baseline-adopted` + `doggett-android-telemetry-docs-ingested` merged to `decisions.md`, PROPOSED, pending Mulder ack. Clarification note appended to prior "GSA Kusto Catalog adopted" decision flagging the supersession.


## 2026-06-05T13:45Z — First executable Android NAAS-only daily livesite report assembled

Took Scully's NAAS 7-day data (`naas-7d-report-data-2026-06-05.md`) and produced the v1 report at `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-05.md`. Followed the Windows-reference report style (header + on-call + exec summary + key-metrics table + top-5 insights + cross-domain chain + data-quality + contributors). Every numeric value traces back to a specific Scully per-query result — no invention. Honest TBDs where Defender-client-side scope is locked (latency p50/p95/p99 via ghost columns, client-side cascade, install-source/OS/OEM splits) and where rotation isn't configured (on-call). Anchored Top Insight #1 on the tunnel failure-rate 5× ramp per Saloni's pre-instruction; used Scully's correlation chain #1 (ramp ⟷ weekday step ⟷ 1P concentration). Prominently surfaced the `FlowStatusError`/`FlowErrorClassification`/`LatencyMs`/`Msg` ghost-column defect in both Top Insights (#4) and Data Quality Notes so consumers know server-side latency is silently missing this cycle. No P0/P1 — three P2s + two info-level Top-5 items. Decision dropped at `.squad/decisions/inbox/reyes-first-naas-report-20260605T1345Z.md`; not committed (Scribe owns git).


## 2026-06-06T11:50Z — v2 daily report assembled (NAAS preserved + live ICM plugged in)

Assembled v2 of the daily livesite report at `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-06.md` (new dated file; v1 from 2026-06-05 untouched). NAAS telemetry was not re-pulled — Executive Summary, Key Metrics, Top 5 Insights, Cross-Domain Correlation, and Data Quality Notes carry over verbatim from v1, with a `> v2 note:` at the top and a window callout on Key Metrics making the reuse explicit. Three additions over v1: (1) `📟 On-Call Today` replaced `TBD/TBD` with the live roster (Primary `dileepkusuma`, Backup `samirnen`) from Scully's `get_on_call_schedule_by_team_id(106961)` pull; (2) brand-new top-level `🚨 Active ICM Incidents` section inserted between On-Call and Executive Summary, with counts strip + three tables (Customer-Created Active showing #810723164 [Copilto testing] Sev3 5d unacknowledged TestICM; System-Created Active empty; Mitigated Highlights empty with the D-138 "genuine empty, not a windowing regression" callout) + 5 Patterns bullets; (3) Data Quality Notes extended with an `ICM Integration (v2 — first cycle)` sub-section and 2 new Open Questions (queue identity, detector→ICM correlation). Bucketing footnote on the Customer-Created table calls out that the ported collector mis-buckets via HP's `source startswith "customer"` heuristic vs ICMProd's actual `type=CustomerReported` schema — table is bucketed on the correct `type` field; v2.1 will fix the collector. Queue-identity question surfaced prominently for Saloni: `owningTeamId=106961` returns `owningTeamName="GSA  Client - XPlat"` (double-space typo from ICM), so 106961 may be a parent queue rather than the Android-specific one. Contributors footer extended (Doggett v2: port-plan + skill; Scully v2: collector port + first pull; Reyes v2: assembly). Strict no-fabrication discipline: every ICM fact (#810723164, Sev3, 5d, unacknowledged, TestICM keywords, owningTeamName typo, 0 mitigated, 0 system-detected, on-call aliases) traces directly to Scully's data drop. Decision file dropped at `.squad/decisions/inbox/reyes-v2-naas-plus-icm-report-2026-06-06.md`. No git commit (Scribe owns), no sub-agents spawned, no queries re-run.


## 2026-06-09T14:46+05:30 — v3 daily report assembled (NAAS refreshed + ICM reused at 06-08 freshness)

Assembled v3 of the daily livesite report at `/Users/salonijain/workspace/AndroidHealthCheckService/daily-livesite-report-android-2026-06-09.md`. Unlike v2 (which preserved v1 NAAS verbatim), v3 has FRESH NAAS data (Scully's `naas-7d-report-data-2026-06-09.md`, window `2026-06-02 → 2026-06-09`) AND reused ICM (Scully's `icm-team-106961-data-2026-06-08.md`, no movement in 24h confirmed by Coordinator → no re-pull). Wrote `> v3 note:` callout at top making the asymmetric freshness explicit, and labeled the ICM section header "ICM Snapshot (live as of 2026-06-08, no movement in 24h)".

**Structural changes vs v2:**
1. **Headline severity promoted.** Anchor insight moved from 🟡 P2 to 🟠 **P2-trending-P1** per Scully's direction (6/05=0.354% → 6/06=0.416% → 6/07=0.431% → 6/08=0.447%, single +0.55pp day from 1% threshold). Added a stand-alone bullet to Exec Summary calling this out as a "second step up, not stabilization" — distinct framing from v1/v2's "5× ramp / sustained plateau" language.
2. **Cross-domain candidate REMOVED.** v1/v2 candidate #1 ("Microsoft 1P dogfood rollout driving regression") explicitly **struck through and labeled FALSIFIED** in the Cross-Domain section, with Scully's S6b non-1P probe cited as the falsifying evidence (non-1P fail-rate 0.49–0.60%, HIGHER than global). First time a v3 had to retract a prior-cycle hypothesis publicly — used strikethrough + bold "FALSIFIED today" to make the retraction unambiguous.
3. **New top single-version anchor swapped in.** v1 had flagged `.0102` ring; v3 promotes `1.0.9003.0401` (`.04xx` flavor) to Top Insight #2 — devices +55%, fail-rate +131%, concentrated in 2 tenants. Doggett task: "identify what `.04xx` actually is."
4. **EU regional cluster promoted to its own Top Insight (#4).** Multiple EU regions accelerating in lockstep (germanywestcentral +67%, NorthEurope +61%, SwedenCentral +114%, WestEurope +53%) — v1/v2 had buried this under Insight #2 (Private Access); v3 separates because the ServiceType-uniform-degradation finding now makes "Private Access path" too narrow a frame.
5. **NEW Insight #5: PROFILE_UNDEFINED widening.** Device count +41% (245→345) outpacing event count +10% — reframed from "low-volume race condition" (v1) to "client config/onboarding bug suspect" (v3). Severity 🟡 P3/watch.
6. **Data Quality recurring row escalated.** Created a dedicated "Recurring DQ Row" table inside Data Quality Notes with status `🔴 OPEN 4d, no upstream fix` and explicit "Recommended Action: file schema/normalization ticket" for both ghost columns and region casing. Previously buried as prose bullets in v1/v2.
7. **Detector silence escalated to 3-pull pattern.** ICM Patterns + Cross-Domain both call out "3 consecutive pulls with zero auto-ICMs against a 6× ramp" — v2 had 1 pull as a data point; v3 has structural pattern.
8. **Contributors footer extended** to list v3 deliverables (Scully's fresh NAAS + S6b probe; Reyes's v3 assembly with hypothesis retraction).

**Things that needed extra framing:**
- **Asymmetric data freshness.** NAAS is fresh today (06-09 run), ICM is 1 day old (06-08, no movement). Had to explicitly label both windows in the `> v3 note:` and on the ICM section header so a reader doesn't assume both pulled today. ICM Snapshot header wording is verbatim what Coordinator requested.
- **Falsification of prior hypothesis.** Strike-through + bold "FALSIFIED" was the cleanest way to retract candidate #1 without burying it. Kept the line in the cross-domain list (rather than silently deleting) so the reader can trace v1→v2→v3 reasoning.
- **6× ramp framing.** v1/v2 said "5× ramp" (0.074%→0.36%). v3 now spans 0.074%→0.447%, which is 6×. Updated all instances in v3 prose. Kept the v1 baseline reference for traceability.
- **TestICM aging from 5d to 5d+.** The TestICM hasn't been touched since 06-06, so on 06-09 it's actually 6d old (created 06-03), but lastModified is still 06-06. Wrote "5+ days, untouched ~2.5 days since 06-06" to capture both axes without overclaiming.
- **Bucketing bug at pull #3.** Restated workaround prominently (classify by `type == "CustomerReported"`) since downstream consumers need it every cycle until v2.1 ships.

Strict no-fabrication discipline: every NAAS number traces to Scully's v3 drop tables (S1+S2+S3, S6, S6b, S4, S7, S8, S9, S10, S11, S12); every ICM fact traces to the 06-08 envelope. No git commit (Scribe owns). No sub-agents spawned, no queries re-run.
