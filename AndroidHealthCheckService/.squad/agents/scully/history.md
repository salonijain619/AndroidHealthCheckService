# scully — Learnings

## Project Context (seeded 2026-06-05)
- **Project:** Android GSA Client Service Health Check
- **User:** salonijain619 (Saloni)
- **Stack:** Investigation/SRE squad for the GSA Android client. Telemetry from server-side Kusto (NaasProd @ idsharedwus + idsharedscus for full set), client-side **App Insights `wd-prod-android-client`** (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c), Aria Kusto (GUID f0eaa94222894be599b7cd0bc1e2ed6f, opportunistic Android only), and Android-perf cluster `androidgsa.eastus.kusto.windows.net/Metric` (unverified).
- **Android client repo:** https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android
- **Onboarding doc:** https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **ICM team:** https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- **Report channel:** IDNA GSA → Livesite - Client (Teams), tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
- **Sister squads:** Windows (win_client_investigation_squad), Mac (HarryPotter)

## Summarized history (full content → `history-archive.md`)

### 2026-06-05 — Dashboard reverse-engineering + first Kusto introspection [SUMMARIZED]
Dashboard analysis, schema capture, initial starter queries (5 untested). See archive.

### 2026-06-05T12:00:52Z — Team update: bootstrap complete [SUMMARIZED]
Squad bootstrap, report template ready, Kusto foothold confirmed. See archive.

### 2026-06-05 (later) — Panel KQL unblock from Saloni [SUMMARIZED]
Verbatim panel query executed; key corrections on filter/format/routing. See archive.

## Current learnings (active)

### 2026-06-05T13:30Z — First executable NAAS-only 7d Android data run
Executed NAAS-server-side, Android-filtered, all-tenants slice of the ICM baseline workload against `idsharedwus` (NaasProd + NaasCloudPkiProd + NaasAgentServicesApsProd) for the 7d window ending 2026-06-05T13:26Z. Auth clean via `azure-mcp-kusto` default cred; 20 queries attempted, 17 passed, 5 recovered from column-discovery/casing, 0 final failures. All 22 ICM client-side queries DROPPED per Saloni's NAAS-only scope lock. Headline numbers Reyes can lift: 27,489 active Android devices / 1,241 active tenants (NOT 8 — that older number was an outdated ClientVersion cohort-filter artifact) / 130.05M tunnel events / 99.711% success / 0.289% failure overall. **P2 anchor finding:** daily tunnel failure-rate climbed ~5× (0.074% → sustained 0.36%) over the window — anomaly is real (failure volume +12× while traffic only +2.6×). Private Access fails 4× more than M365 (0.69% vs 0.17%); `PROFILE_UNDEFINED` ServiceType is 100% failure (4,003 events, 245 devices — config-bootstrap race). APS 99.997% / 270M events; APS-Ack 99.99966% / 268M; PKI 0.0007% errors (4 of 595,712) — both healthy ✅. **New data-quality findings for the report:** `FlowStatusError` / `FlowErrorClassification` / `LatencyMs` / `Msg` on `TunnelServerOperationEvents` are **ghost columns** (advertised in `getschema`, unqueryable — Kusto returns SEM0100); server-side latency p50/p95/p99 unavailable this cycle. `Region` casing duplicates (e.g. `westeurope`/`WestEurope`) imply two ingestion paths. APS sibling tables have divergent schemas (`HttpResponseStatusCode` present on GetSettings, absent on SettingsAck). PKI emits empty `DeviceId` for Android (use TenantId only). Filter idiom matrix expanded: Tunnel = `DeviceOs has_cs 'ANDROID'`, PKI = `OS == 'ANDROID'` (uppercase, case-sensitive), APS = `OS has_cs 'Android' or OSType has_cs 'Android'`. Output: `.squad/agents/scully/research/naas-7d-report-data-2026-06-05.md` (~27KB; ICM re-bucketing + Exec Summary + 12 per-query results + Failures + 3 cross-domain candidates Reyes/Doggett can extend). Decision filed: `decisions/inbox/scully-naas-7d-execution-20260605T1330Z.md`. **Queued for Reyes:** every server-side Key-Metrics row has a real number; Top Insight #1 candidate pre-anchored (Tunnel 5× ramp); 3 cross-domain chains pre-drafted. Client-side rows remain TBD until Defender-client-side scope is unlocked.

### 2026-06-06 — HarryPotter ICM collector ported + first live pull on team 106961

**Port (verbatim, per Doggett's plan):** Copied HP `livesite/scripts/icm_collector.py` (commit `d35a114`) and `tests/test_icm_collector.py` into `tools/icm/` under squad root. Substitutions: `team_id 115956→106961`, `team_name "GSA Client - MacOS"→"GSA Client - Android"`, env `HP_ICM_TEAM_ID→AHCS_ICM_TEAM_ID`, client name `hp-icm-collector→ahcs-icm-collector`, import paths `livesite.scripts→tools.icm`, default config `livesite/scripts/config.yml→.squad/config.json`. **NO change** to JSON-RPC handshake, `WARMUP_DELAY_S=6`, tools/list-then-sleep-then-tools/call ordering, D-138 no-`dateRange` discipline, severity normalization, age calculation. Created `.squad/config.json` with `icm.team_id=106961` as single source of truth (CLI > env > config > default, per HP D-117/D-118).

**Tests:** `python3 -m pytest tools/icm/tests/ -v` → **19/19 passed**, including the 3 D-138 regression tests (`test_active_query_omits_date_range`, `test_mitigated_query_omits_date_range`, `test_mitigated_query_sorts_by_last_modified_desc`). Port verified clean.

**Live run:** `python3 -m tools.icm.icm_collector --config .squad/config.json --timeout 120`. Exit 0, **26s elapsed** (warm Entra cache, no browser flow). `source: "live"`, `_meta.errors: []`. Raw JSON: `tools/icm/runs/icm-run-2026-06-06.json`.

**Headline counts:** 1 active (Sev3, customer-reported but flagged `[Copilto testing]` TestICM, #810723164, unacknowledged, 5d old) · 0 mitigated · on-call primary=`dileepkusuma`, backup=`samirnen` (live, no cache fallback). Effective real-incident count after TestICM filter = **0**.

**3 findings worth flagging:**
1. **Bucketing bug (port-faithful, not introduced by me):** HP collector buckets active ICMs by `source startswith "customer"`, but ICMProd's payload uses `type` (`CustomerReported`/`LiveSite`/`Deployment`) and returns `source: None`. The lone customer-reported ICM currently lands in `system_created_active`. Raw `type` preserved per-incident — Doggett/Reyes 1-line re-bucket fix in v2.1.
2. **Owning-team display drift:** `owningTeamId=106961` → `owningTeamName="GSA  Client - XPlat"` (double-space typo). Need Saloni confirm 106961 is the Android queue vs an XPlat parent (could mean we're missing an Android-only sub-queue).
3. **Detector silence is suspicious, not reassuring:** zero system-detected ICMs while server-side NaaS 7d (own 2026-06-05 pull) shows 0.36% sustained tunnel failure rate (5× ramp). Either no Android-tagged detector exists or rotation isn't routing detector-emitted incidents here.

**Outputs (for Reyes v2 report):** `.squad/agents/scully/research/icm-team-106961-data-2026-06-06.md` (full structured drop with On-Call, Counts, Customer/System/Mitigated tables, 6-bullet Patterns, raw cross-check counts, D-138 provenance). Decision filed: `.squad/decisions/inbox/scully-icm-106961-first-pull-2026-06-06.md` (confidence: medium, verify on second pull).

## 2026-06-08T16:23Z — Scribe: Orchestration log + session summary

Scribe wrote orchestration logs for the 2026-06-06 spawn batch (4 entries: doggett-3, doggett-4, scully-4, reyes-1) and a session log covering the HP discovery → skill authoring → collector port → v2 report arc. Mulder and Skinner flagged for cross-team review on: (1) new `icm-queue-ingest` skill (confidence MEDIUM, promote to HIGH after second clean cycle), (2) team 106961 queue-identity open question (confirm Android vs XPlat parent), (3) detector-silence finding (zero system-detected ICMs while server shows 0.36% tunnel failure 5× ramp). Decision inbox merged into `decisions.md` (6 files processed).

### 2026-06-08 — Daily refresh: ICM live ✅, NAAS BLOCKED on network

**ICM (team 106961):** Clean live pull, exit 0, ~30s, `_meta.errors=[]`, `fetched_at=2026-06-08T12:01:45Z`. Queue **state-unchanged** vs 06-06: same lone Sev3 TestICM #810723164, identical `lastModifiedDate=2026-06-06T06:01Z` (nobody has touched it for ~2.5 days), same on-call (primary `dileepkusuma`, backup `samirnen`), 0 mitigated, 0 system-detected. Owning-team name `"GSA  Client - XPlat"` double-space typo **still present** upstream — not fixed in 2.5 days. Bucketing bug (`source startswith "customer"` vs ICMProd's `type` field) **still ships** — re-flagged in today's drop with explicit guidance to Reyes: classify on `type == "CustomerReported"`. Effective real-incident count = **0** (TestICM excluded). Two consecutive byte-identical envelopes (5,335 bytes) is a useful "queue is dead-stable" signal *and* a reminder that detector-silence persists despite v1's 5× tunnel-failure ramp. Drop: `.squad/agents/scully/research/icm-team-106961-data-2026-06-08.md`. Skill `icm-queue-ingest/SKILL.md` followed verbatim (5-step handshake + 6s warmup), no deviations, no code changes since port.

**NAAS 7d (idsharedwus):** **BLOCKED on TCP-layer reachability.** `azure-mcp-kusto kusto_query` against `https://idsharedwus.kusto.windows.net` returned HTTP 503 / `Operation timed out (idsharedwus.kusto.windows.net:443)` on first attempt; spec-mandated single retry returned same error after a 20s pause. Direct `curl -m 20 https://idsharedwus.kusto.windows.net/v1/rest/mgmt` also TCP-timed-out at port 443. DNS healthy (`172.185.50.226`), general internet healthy (`bing.com` 200), ICM endpoint healthy (same env, same Entra creds). **Diagnosis:** corp-VPN/firewall blocks egress to `*.kusto.windows.net` from this Copilot run env — NOT auth, NOT a query bug, NOT a 5/05 schema regression. Zero queries reached the cluster; **zero NAAS data this cycle**. Drop documents the failure verbatim and reproduces the v1 baseline for Reyes to use as last-known-good with a 🟧 staleness banner. **No fabricated cells anywhere.** Decision/inbox file dropped flagging the blocker for Saloni unblock.

**Learnings worth carrying forward:**
1. The `azure-mcp-kusto` MCP and the `agency mcp icm` MCP go through different network paths — ICM via `icm-mcp-prod.azure-api.net` (worked), Kusto via `*.kusto.windows.net` direct (blocked). When one fails, do NOT assume the other is also blocked; probe each independently. Today's run was a clean A/B: ICM ✅, Kusto ❌, in the same shell, same minute.
2. The "two pulls in a row, byte-identical envelope size" pattern is a strong stability signal for ICM — when nothing in the queue moves, the JSON is deterministic byte-for-byte. Useful as a sanity check (if size differs but counts don't, something subtle changed — investigate; if size matches and counts match, queue is genuinely quiet).
3. The bucketing bug (filed 06-06) still ships and would have silently routed customer-reported ICMs into the system-created bucket twice in a row if Reyes weren't reading these drops. Worth promoting to a higher-priority Doggett fix — it's not a future hypothetical, it's affecting consecutive reports.
4. Detector silence is now a **multi-pull observation** (06-05 + 06-08 server-side anomalies; 06-06 + 06-08 ICM detector pulls). Mulder/Skinner thread should treat this as a firm finding, not a one-off suspicion. If the v1 5× tunnel-failure-rate ramp didn't trip a detector, the detector either doesn't exist or isn't routed to team 106961.
5. The TestICM #810723164 going untouched for ~2.5 days is its own minor signal — on-call (`dileepkusuma`) is not actively triaging the queue, even casually. For a real customer-reported Sev3 with 5d unack, that would be a finding; for a TestICM with no real impact, it's just litter, but the rotation discipline is the same in either case.

### 2026-06-09 — NAAS 7d v3 refresh: cluster unblocked, ramp got WORSE
**Outcome:** ✅ GO. 10/10 substantive queries clean against `idsharedwus` (NaasProd + NaasAgentServicesApsProd + NaasCloudPkiProd). Yesterday's TCP-block lifted — same `azure-mcp-kusto` MCP path that timed out 06-08 is back online. Window: `2026-06-02T00:00:00Z` .. `2026-06-09T00:00:00Z` (closed 7-day). Drop: `.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md`.

**Deltas vs v1 (2026-06-05 baseline) — headline:**
- 7d events 130.05M → 131.87M (+1.4% flat); 7d failures **375K → 508K (+35%)**; overall fail-rate **0.289% → 0.385% (+33%)**. Quality regression, not traffic.
- Daily ramp: v1 plateau 0.36% on 6/02–6/04; v3 shows 6/05=0.354 → **6/06=0.416 → 6/07=0.431 → 6/08=0.447** (highest single-day in 11 days of observation). NOT stabilizing — second-step degradation.
- Active devices 27,489 → 27,744 (+0.9%); tenants 1,241 → 1,254 (+1%). Fleet unchanged; everything else got worse.
- ServiceType: M365 0.174→0.227, INTERNET 0.548→0.766, PRIVATE_ACCESS 0.688→**0.929**. PA:M365 ratio held at ~4×. Uniform +30–40% across profiles.
- Microsoft 1P share unchanged at 38%. PROFILE_UNDEFINED devices 245→345 (+41%) at 100% fail.
- ClientVersion `.04xx` ring: `1.0.9003.0401` +55% devices AND +131% fail-rate (0.271→0.626) — biggest single-version regression. Now the highest-fail high-volume version.
- Regions: germanywestcentral +67%, NorthEurope +61%, francecentral +57%, SwedenCentral +114%. EU cluster intensifying. UK South biggest absolute (118K fails).
- APS health unchanged (99.996%/99.99970%). PKI 0.0007% errors unchanged — BUT new 2× HTTP500 `Failed` class that didn't exist in v1.
- Ghost columns (FlowStatusError/FlowErrorClassification/LatencyMs/Msg) STILL ghost — 4 days no fix.
- Region casing duplicates STILL split — 4 days no fix.

**Surprises:**
1. **Hypothesis falsification — Microsoft 1P is DAMPENING the curve, not driving it.** Ran a new probe (S6b) stripping `72f988bf` from the daily series. Non-1P fail-rate runs 0.49–0.60% (HIGHER than the 0.39% global rate every day). v1's cross-domain candidate #1 ("WoW traffic shift unmasked dogfood-only regression") is **wrong** — the regression is platform-wide. Remove from v3 report.
2. **Two-step ramp.** Expected either plateau-continuation or partial recovery; got a second clear step up. Failure-rate hit 0.447% on a day when traffic was normal Monday-volume — 11d arc is monotonically up with no recovery signal.
3. **One v1 outlier self-resolved.** Tenant `7e389af4-…` (2 devices / 1.9K failures each — "looks like a misconfigured test device") dropped out of top-15. First counterexample to "everything in this report just gets worse." Useful sanity check that the queries DO see clearing signals when they happen.
4. **One v1 small-signal got big.** `.04xx` client-version ring was weak/curiosity in v1; today it's the strongest single-version regression signal in the run. Worth Doggett asking "what is `.04xx`?" — 2 tenants concentrated.

**New queries that worked:**
- S6b: `where TenantId != '72f988bf-86f1-41af-91ab-2d7cd011db47'` cleanly partitions out 1P traffic for the daily trend. Use this idiom whenever a single big tenant might be dominating an aggregate.
- `getschema | where ColumnName has_any('Result','Error','Reason','Code') | project ColumnName, DataType` — quick filter to confirm there's no alternate error column we missed on a table (returned 0 rows on `TunnelServerOperationEvents` — exhaustive negative result).

**Nothing failed.** Single ghost-column re-check was an intentional reproduction, not a real failure. Confirmed SEM0100 verbatim, 4 days unchanged.

**Decision-inbox file:** `.squad/decisions/inbox/scully-naas-ramp-second-step-20260609.md`.

**Key carry-forwards for Reyes:**
- The ramp is the v3 report's top insight. Anchor on "0.074% → 0.36% plateau → 0.42–0.45% second-step" with the failure-rate trend graph. At 0.447% on 6/08, a single +0.55pp day crosses 1% (the typical incident threshold).
- Drop the "Microsoft 1P / dogfood rollout" hypothesis. The non-1P data falsifies it.
- New tenant to flag for Mulder triage: `9cf9036f-5fc5-475d-846d-94ea941e4bfc` (105 fails/device, 45 devices, new top-15 entrant).
- New version-suffix anchor: `.0401`/`.04xx` ring — Doggett identify.
- Ghost columns are now a 4-day recurring DQ note; promote to standing row in the report.
