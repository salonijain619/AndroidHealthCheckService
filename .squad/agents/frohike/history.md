# Frohike — History

## Day-1 Context

**Project:** Android GSA Client Service Health Check
**User:** Saloni (salonijain619)
**Hired:** 2026-06-10

**What the squad does:** Service health monitoring and reporting for the GSA (Global Secure Access) Android client, which ships as the NAAS subsystem inside Microsoft Defender for Android. The squad pulls telemetry, tracks ICM incidents (team 106961), and produces daily/weekly service health reports.

**Why Frohike exists:** Saloni needed a dedicated owner for Google Play Console crash data, framed strictly as NAAS-only (not Defender-general). The squad iterated on crash reporting 4 times before this role was created — the lesson was: NAAS-as-a-unit framing is non-negotiable, and Play Vitals must be the source of truth over AppEvents.

**Key collaborators:**
- **Scully** — server-side NAAS telemetry (NaasProd Kusto). Cross-reference her `.04xx` ring findings against client crash data.
- **Reyes** — assembles the final daily report. Frohike's drop feeds Reyes's "Google Crash Report" / "NAAS Client Stability" section.
- **Langly** — provides current Play Store Defender version so Frohike knows what's live vs what's seeing crashes.

**Canonical skill:** `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md` — read this first on every pull.

**Prior crash drops (pre-Frohike, Scully-authored):**
- `.squad/agents/scully/research/naas-crashes-2026-06-09.md` — 4-iteration deep dive that established the per-Defender-version table format and `.04xx` ring over-index finding (13–14× client crash concentration corroborating server-side anchor)

## Learnings

### 2026-06-10 — First pull (Day-1) executed cleanly. Pattern verified.

**Auth path (verified working):**
- The `mcp_google-play-r_*` MCP tools are NOT exposed in this Copilot CLI session — fell back to direct API per the canonical skill's documented fallback.
- Service account path: `$GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` env var is set to `/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json`. The MCP server's own venv at `WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server/.venv/bin/python` has `googleapiclient` + `google.oauth2` installed — system Python does not. Always use that venv for Play API calls.
- Direct API pattern: import `src.auth.GooglePlayAuth` + `src.reporting_client.ReportingClient` from `WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server`, prepend that path to `sys.path`, set `GOOGLE_PLAY_PACKAGE_NAME=com.microsoft.scmx`, instantiate `ReportingClient(GooglePlayAuth())`, then call `_auth.get_service()` to get the raw `googleapiclient` service for arbitrary query bodies.

**Query mechanics (gotchas hit):**
1. **`countryCode` is NOT a valid dimension on `errorCountMetricSet`**. Valid dims are `versionCode, issueId, isUserPerceived, apiLevel, deviceModel, deviceBrand, deviceType, deviceRamBucket, deviceSocMake/Model, deviceCpuMake/Model, deviceGpuMake/Model/Version, deviceVulkanVersion, deviceGlEsVersion, deviceScreenSize, deviceScreenDpi`. For country cuts, use `crashRate` / `anrRate` (which DO support `countryCode`).
2. **`crashRate` / `anrRate` do NOT support `aggregationPeriod = FULL_RANGE`.** Only DAILY and HOURLY. To get a 7d-aggregated rate per dimension, pull DAILY and user-weight-average locally.
3. **`ReportingClient.query_metrics()` has `max_pages=3` hard-coded** (line 286 of `reporting_client.py`). This is far too few for `errorCount × issueId` (50k+ issues). Either bypass and call `_auth.get_service()` directly with your own pagination loop, OR — much better — pull per-issue `errorCount` with `filter='issueId = "X"'` and `aggregationPeriod='FULL_RANGE'`. That gives one tight pull per NAAS issue, returns the 7d total broken down by versionCode in <10 rows, and avoids the unbounded pagination problem entirely.
4. **`errorIssues:search` returns top-N by lifetime `errorReportCount`, NOT by 7d count.** I pulled the top-150 (6 pages × 25); only 17 carried NAAS markers. A NAAS issue that exists but isn't in the top-150 by lifetime is invisible to this approach. Next iteration: paginate deeper if NAAS issue count seems low for the window.
5. **`type` field uses Play's enum strings, not short codes.** ANR issues come back as `type: "APPLICATION_NOT_RESPONDING"`, not `"ANR"`. Crashes are `"CRASH"`. Filter on the full string.
6. **`distinctUsers` summed across issues is NOT a deduplicated user count.** It's an upper bound for the "affected users" headline. Play does not expose a NAAS-wide deduplicated unique user count.

**Framing gotcha (HARD rule reinforcement):**
- Play publishes ONE `userPerceivedCrashRate` per app, denominated by *all* `com.microsoft.scmx` users — not NAAS-using sessions. **There is no NAAS-only rate available from Play.** Always state denominator explicitly. Report NAAS event *counts* with the whole-app rate as context. Scully's server-side `TunnelServerOperationEvents` carries the NAAS-session denominator; the daily report pairs both.
- `.04xx` ring versions (900300412, 892100412, 900200422, 900100422) have install bases below Play's privacy floor, so Play returns **no per-version rate** for them. The lift number for `.04xx` MUST come from Scully's server-side cohort math; we cannot reconstruct it from Play alone. Note this caveat explicitly.

**EU regional signal verified client-side (new):**
- Pulling `crashRate` by `countryCode` for the 7d window showed **EU aggregate 1.39% vs non-EU 0.45% — 3.1× lift**. Germany alone is 3.25% on 29k users — **above Google's 1.09% bad-behavior threshold**. This corroborates Scully's server-side EU intensification finding (qualitatively; client country-rate is whole-app, not NAAS-only).

**Output artifacts:** raw JSON pulls live in `.squad/agents/frohike/research/pull-2026-06-10/` (freshness, release_filter, per-version rates 7d+14d, per-NAAS-issue × version, per-NAAS-issue × deviceBrand, per-issue sample stack traces, country-crash, aggregates). Report at `.squad/agents/frohike/research/naas-crashes-2026-06-10.md`.

**Reusable pull script:** `pull-2026-06-10/pull.py` is the template — copy + bump dates for tomorrow's run. The per-NAAS-issue + per-country queries are not in `pull.py` (they were ad-hoc); next pass, fold them in.

2026-06-10: First Play Vitals pull (NAAS-filtered). GO verdict. 4,898 crashes / 4,413 ANRs / 7d / 17 clusters. Headline finding: Germany 3.25% whole-app crash, over Google's 1.09% bad-behavior threshold; EU 3.1× non-EU. `libnaas_native_vpn.so` SIGSEGV 33.7% concentrated in `.04xx` ring (pre-prod, not live).

### 2026-06-10 (post-hire, evening) — Section producer implemented + landed.

**What:** Built `tools/report_generator/sections/frohike_play_vitals.py` — the non-interactive, CLI-standalone, fail-soft section producer that automates what the morning's manual NAAS drop did. Conforms to Mulder's report-generator architecture (which landed silently between the morning's manual drop and this build); reads Langly's `live_play_version` from `ctx["prior_results"]` for the ✅ LIVE PROD row tag. 15 unit tests, all green; full repo suite still 64/64.

**Auth pattern (decision for CI):**
- Two env vars accepted, in priority order: `PLAY_CONSOLE_SA_KEY` (raw JSON contents OR filesystem path — auto-detected by leading `{`) then `GOOGLE_APPLICATION_CREDENTIALS` (path only). The JSON-contents-via-secret path is what CI will use (GitHub Actions secrets are strings, not files); the filesystem-path option is for local dev.
- "Auth not configured" → `Status.PARTIAL` with the documented onboarding-stub markdown, **NOT** `Status.SKIP`. This conflicts with the original task brief (which said SKIP) but conforms to Mulder §4 which classifies "auth not configured" as PARTIAL (real degradation) and reserves SKIP for deliberate `--skip-sections` / env-var overrides. Resolved by also adding `REPORT_GENERATOR_SKIP_FROHIKE=1` env-var path that does return SKIP per Mulder. Test kept the spec-required name `test_produce_skip_when_no_creds` with a docstring noting the PARTIAL semantics. Filed onboarding-ask at `.squad/decisions/inbox/frohike-play-vitals-onboarding.md`.

**Attribution-filter edge cases discovered while writing tests:**
- The NAAS predicate token `vpn` is intentionally permissive — it would match a non-NAAS issue whose location merely contains `vpn` (e.g. some third-party SDK named `MyVpnUtil`). Mitigation: the predicate runs on Play issue clusters that have *already* been narrowed to top-N by lifetime, where false positives are rare. Test `test_naas_attribution_filter_exclude_non_naas` keeps the non-NAAS dashboard cluster out, which is the case I care about; the long-tail `vpn`-substring false positive is acceptable.
- `type` enum normalization: Play returns `"APPLICATION_NOT_RESPONDING"` (not `"ANR"`). The producer maps both forms to a unified `"ANR"` so the Top-3 split-by-type works regardless of which form a payload uses.
- `.04xx` ring detector: lives off the *version code* (e.g. `900300412`) not the label, because the 4th-from-last-digit lookup is deterministic on the code. `is_04xx_ring()` is the public seam — tested directly.
- Version-code → label conversion is non-trivial: encoded minor `XYZW` decodes to `XZYW` (swap positions 1 and 2). E.g. `900200122` → body `90020012` → enc `0012` → minor `0102` → `1.0.9002.0102`. Caught this only when the LIVE-PROD-tag test failed initially; the canonical google-play-vitals SKILL.md table is the ground-truth source.

**Denominator-basis decision (HARD framing rule reinforcement):**
- `SectionResult.denominators["denominator_basis"] = "whole_app_sessions"` — stamped on every successful run.
- The "NAAS sessions" denominator that would yield a true NAAS-only rate is **not exposed by Play**; we add a second key `denominators["naas_session_basis"] = "not exposed by Play — see Scully TunnelServerOperationEvents"` so the assembler / future automation can never accidentally divide NAAS counts by whole-app users and call it a NAAS rate.
- The headline rates (`naas_crash_rate_pct`, `naas_anr_rate_pct`) in `metadata` are deliberately whole-app rates with explicit naming via the denominators dict — not a fabricated NAAS-only rate. The producer never invents a denominator Play doesn't publish.

**Implementation seams worth knowing for future iteration:**
- `ctx["client"]` test seam lets tests bypass the real Play API; `_FakeClient` in the test file is the reference shape.
- `ctx["drop_dir"]` test seam isolates the drop file under `tmp_path` so tests don't clobber the real `.squad/agents/frohike/research/` dir.
- Retry policy: 3 attempts, exponential backoff (1s/2s/4s), on connection / timeout / 5xx only. Auth 4xx fails fast.
- The CLI smoke test (no creds) overwrote the rich manual 06-10 drop with the PARTIAL stub — restored from git. Future runs with the SA wired should NOT do this destructively (the auto-generated drop is structurally the same as the manual one, just slightly less narrative depth).

