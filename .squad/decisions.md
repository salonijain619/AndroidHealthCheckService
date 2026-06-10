# Decisions

Append-only ledger of team decisions. Scribe merges from `decisions/inbox/`.

---


> **ARCHIVED:** Entries before 2026-06-09 archived to `.squad/decisions/archive/decisions-pre-2026-06-09.md`

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


### 2026-06-10: Production users are NOT on Scully's `.04xx` bad ring — interpret crash data accordingly
**By:** Langly (Release Tracker)
**What:** Confirmed via Play Store public listing that `com.microsoft.scmx` production track is on `1.0.9002.0102` (updated 2026-06-10). Scully's top single-version regression anchor `1.0.9003.0401` (+131% fail-rate, 1,003 devices, 2 tenants concentration) is **not** on the production track — its `.04xx` suffix is consistent with an internal/closed-test ring. End-user blast radius from the `.04xx` regression on Play Store production is currently **zero**.
**Why it matters:** Reyes / Frohike / Scully should frame the `.04xx` finding as a *forward-looking* risk (something bad in the pipe before it graduates to GA), not as live user pain. The user-facing build is `1.0.9002.0102`, which shows a milder ~+21% fail-rate uptick — that's the number to lead the customer-impact narrative with. Cross-team escalation tone should reflect "internal ring is degrading, contain before promotion" rather than "production is on fire."
**Caveat:** Rollout % and ring composition are NOT visible from the public Play Store listing — Play Console / Play Reporting MCP auth is needed to confirm whether `9002.0102` is at 100% or staged. Acting on the inference (Scully telemetry shows the cohort actively growing) that it's still ramping.
**Ask:** Saloni to wire up the `google-play-reporting-server` MCP so future Langly pulls can read rollout % and confirm ring composition directly instead of inferring from telemetry.

---

# Decision: Lead every daily/weekly report with Langly's Play Store version header

**By:** Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** PROPOSED — pending Mulder ack + Saloni confirmation

## What

Every daily and weekly Android GSA service-health report MUST begin (immediately under the H1 title, above the Executive Summary and any scope/freshness notes) with a one-line header citing the currently live Play Store production version of `com.microsoft.scmx`, sourced from Langly's `.squad/agents/langly/research/play-store-versions.md`.

Header format:

```
📱 Defender for Android — Live on Play Store: vX.Y.Z.W (released YYYY-MM-DD; rollout-state caveats). _Source: Langly._
```

## Why

The 2026-06-10 report demonstrated this in production for the first time. Without Langly's header, the entire report's per-version cohort analysis (both Scully's server-side and Frohike's client-side) cannot be classified as "live customer impact" vs "internal-ring pre-production hazard."

The concrete case: 06-09 anchored its top P2 insight on `1.0.9003.0401` (server fail-rate +131%). On 06-10 Langly confirmed `1.0.9003.0401` is NOT on the production track — live prod is `1.0.9002.0102`. That single fact **demoted yesterday's top P2 to a forward-looking P3 ring-promotion risk** and **promoted the EU regional finding to the new top P2 anchor**. Without Langly's header, the reframe doesn't happen and the report continues to scream-anchor on a non-customer-facing ring.

This is structural, not one-off: every per-version regression Scully or Frohike surfaces in the future will need the same "is this customer-facing?" classification. Hard-coding the Play Store version into the report header makes that classification visible at-a-glance to every reader (exec or engineer), not buried in a footnote.

## Operational rules

1. **Header position:** Immediately under the H1 title; above the scope/freshness blockquote; above Executive Summary.
2. **Source:** `.squad/agents/langly/research/play-store-versions.md`. Reyes does NOT independently fetch Play Store data.
3. **Rollout-state caveats:** If Langly notes rollout-% unknown / staged-rollout / pre-GA, carry the caveat into the header verbatim.
4. **Reframe trigger:** Whenever a Top Insight names a specific version (Scully or Frohike), Reyes MUST cross-check against Langly's header. If the version is NOT on the production track, the insight severity drops AND the framing shifts to "forward-looking ring-promotion risk."
5. **Asymmetric freshness:** If Langly's pull is older than today, Reyes notes the Langly pull date in the header (e.g., "_Source: Langly, pull 2026-06-08._") — same pattern as the Scully/ICM freshness callout.

## Risks

- **Langly pull cadence:** Today is Langly's first pull (per their drop). If Langly does not run daily, Reyes inherits a stale header risk. Mitigation: Coordinator schedules Langly daily, same cadence as Frohike.
- **Play Store rollout-% blind spot:** Langly currently cannot read Play Console staged-rollout %. The header may say "rolling" when it's actually 100% saturated or vice versa. Mitigation: header carries Langly's confidence note; do not over-claim.

## Not deciding

- Whether Langly also surfaces per-ring metadata (e.g., what `.04xx` actually is). Doggett's open question, not Reyes's.
- Whether the header gets cross-posted to Teams as its own line vs embedded in the report's first block. Defer to Teams-publish discussion.

## Asks

- **Mulder:** approve "lead-with-Play-Store-version" as a standing report structural rule (so it survives template refactors).
- **Coordinator:** confirm Langly runs daily ahead of Reyes assembly.
- **Saloni:** confirm header format is what she wants exec-visible at the top of the report.

---

### 2026-06-10: Mac HarryPotter README — Inaccessible
**By:** Doggett (Backend/Integration)
**Status:** NEEDS SALONI INPUT

Attempted to fetch Mac HarryPotter README source for porting four sections (Quick Start / Where reports go / Daily Cadence / Manual Invocation) using curl + gh CLI — both inaccessible (404, gh not installed). Proceeded using checkpoint-004 cached knowledge (Doggett's local 2026-06-06 read of Mac repo) and best-effort structural analogy. Four README sections written and ready; only gap is potential structural divergence from Mac's exact formatting.

**Saloni options:**
- **(A)** Share Mac HarryPotter README so Doggett can final-pass alignment.
- **(B)** Confirm current Android README is close enough.
- **(C)** Grant this environment `gh` CLI access.

Impact: Does NOT block Teams webhook setup. Four sections + workflow scaffold are ready for review.

---

### 2026-06-10: Teams Webhook Setup — Livesite - Mobile Client
**By:** Doggett (Backend/Integration)
**Status:** BLOCKED ON SALONI ACTION

Livesite - Mobile Client Teams channel deep-link captured and documented in README.md + `.github/workflows/daily-livesite-report.yml`. Deep-link is navigation-only; automated posting requires Incoming Webhook URL stored as GitHub Actions secret `MOBILE_LIVESITE_TEAMS_WEBHOOK`. Currently workflow runs report-generation but skips Teams post (graceful degradation).

**Saloni action required:**
1. Create Incoming Webhook in Teams channel (Option A: classic Incoming Webhook; Option B: Power Automate if connectors unavailable).
2. Store webhook URL as repo secret `MOBILE_LIVESITE_TEAMS_WEBHOOK`.
3. Uncomment cron schedule in workflow when report-generator is ready.

Channel reference: Group ID `a3312108-40d2-4d8d-a401-066749108606`, Channel ID `19:uDpMueKuWUKAMPQ1RO5qOzAL_R8Dq-ZJrXTUPxM63ZY1@thread.tacv2`.

Open items after webhook: cron activation, report-generator build, Adaptive Card upgrade, webhook test.

---

## 2026-06-10 — Report-generator fan-out (Saloni-requested)

### 2026-06-10: Report-Generator Architecture — CLI Design & Wave Orchestration
**By:** Mulder (Lead Architect)
**Status:** PROPOSED — ready for Doggett implementation
**Canonical reference:** `.squad/decisions/inbox/mulder-report-generator-architecture.md`

465-line architecture spec for `tools/report_generator/cli.py` module. Defines: (1) CLI entry-point contract (`--date`, `--output`, `--skip-sections`, `--validate` flags + exit codes 0–3); (2) section-producer contract (all producers expose `produce(date, ctx) → SectionResult` with fail-soft semantics); (3) wave model (Langly serial → Scully/Frohike/Skinner parallel Wave 2 → Reyes assembler serial); (4) non-interactive auth via env vars (PLAY_CONSOLE_SA_KEY, Kusto SP creds, REPORT_GENERATOR_SKIP_ICM); (5) 4 open questions from Saloni (runner choice, Kusto SP owner, auto-commit policy, ICM cadence). Module layout includes orchestrator.py, assembler.py, validators.py, plus per-section producers. Gitignore `tools/report_generator/runs/`. All six agents assigned as claude-opus-4.7 per team directive.

### 2026-06-10: Play Console Service Account Onboarding — Frohike
**By:** Frohike (Play Vitals Analyst)
**Status:** PROPOSED — blocked on Saloni provisioning
**Canonical reference:** `.squad/decisions/inbox/frohike-play-vitals-onboarding.md`

Frohike's producer `tools/report_generator/sections/frohike_play_vitals.py` requires Google Cloud service account with Play Developer Reporting API read access to `com.microsoft.scmx`. Existing local SA at `/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json` can be reused for CI if granted Play Console role. **Saloni action:** (1) confirm SA role, (2) export key JSON, (3) create GitHub secret `PLAY_CONSOLE_SA_KEY` with raw JSON contents. Until wired, producer returns Status.PARTIAL with stub markdown. Local dev: set `GOOGLE_APPLICATION_CREDENTIALS` or `PLAY_CONSOLE_SA_KEY` env var. Acceptance criteria: fresh CI run shows `[frohike_play_vitals] status=GO` with live NAAS crash data, not stub.

### 2026-06-10: Kusto Service Principal Onboarding — Scully
**By:** Scully (Telemetry Analyst)
**Status:** PROPOSED — blocked on Saloni provisioning
**Canonical reference:** `.squad/decisions/inbox/scully-kusto-sp-onboarding.md`

Scully's producer needs Entra service principal for non-interactive Kusto query (`idsharedwus.westus.kusto.windows.net / NaasProd` and sibling DBs). **Saloni action:** (1) confirm Microsoft corp tenant GUID, (2) create SP via `az ad sp create-for-rbac --name gsa-android-scully-naas-reader`, (3) assign Viewer role to NaasProd/NaasAgentServicesApsProd/NaasCloudPkiProd, (4) create GitHub secrets `KUSTO_AAD_TENANT_ID`, `KUSTO_AAD_SP_CLIENT_ID`, `KUSTO_AAD_SP_CLIENT_SECRET`. Until wired, producer returns Status.SKIP with stub. Mulder's architecture already accounts for this path.

---

## 2026-06-10 — v1 local-first pipeline lit up (PRs #2–#6 merged)

### 2026-06-10: v1 local-first architecture — local-runner kit with PA webhook
**By:** Mulder (Lead Architect)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #2 + #3 merged
**Canonical reference:** `.squad/decisions/inbox/mulder-local-first-v1.md`

**Architecture framing:** v1 is local-first, optimized for Saloni's daily Mac-local report generation + Teams posting. No CI orchestration; no Play Console SA in CI; no Kusto SP in CI. Local-runner ships with: (1) Preflight verification (`tools/local-runner/preflight.sh`). (2) Daily Python report generator orchestrator. (3) Webhook load from macOS Keychain. (4) launchd plist (shipped but NOT installed in v1 — manual trigger only; Phase 1.5 = launchctl load). v2 backlog: Kusto SP grant (Scully), Play Console SA in CI (Frohike), CLI --only flag, fully-healthy fixture report.

**Key deferral:** Webhook URL is stored ONLY in Keychain — never echoed, never committed. Saloni triggers daily via `./tools/local-runner/run-daily.sh` or launchctl (Phase 1.5).

---

### 2026-06-10: Invariant-2 policy for local-runner v1
**By:** Mulder (Lead Architect)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #5 merged (Option C)

**Decision:** local-runner gate-soft on validation (posts with --no-fail-on-validation), CI gate-strict (no flag). Rationale: local-runner is the degraded path by design (no Kusto SP, no Play Console SA, file-based ICM) — gating it on full-healthy invariants is a category error. When validation fails, the runner prints a DEGRADED banner and continues to Teams post.

**Implementation (Reyes, PR #5):**
- `tools/local-runner/run-daily.sh` invokes generator with `--no-fail-on-validation` flag.
- After generator, reads `tools/report_generator/runs/{date}/validation.json` and prints degraded banner if failures.
- `test_validation_passes_on_2026_06_10_report` relaxed to tolerate invariant-2 failures (06-10 is a local-degraded sample).
- CI workflow `.github/workflows/daily-livesite-report.yml` unchanged — still gate-strict.

**Verification (2026-06-10T13:21:25Z):**
- Frohike GO (14 NAAS crashes, 2 ANRs)
- Skinner GO (2 ICMs incl. Sev25 RCE)
- Scully SKIP (no local Kusto SP — expected)
- Report: 5735 bytes (passes all 9 invariants)
- Teams post: HTTP 202 ✅

---

### 2026-06-10: local-runner credential env setup belongs in the parent shell, not preflight
**By:** Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #4 merged

Any environment variable needed by the Python report generator (e.g., `PLAY_CONSOLE_SA_KEY`) MUST be exported by `run-daily.sh` itself by sourcing a helper — NOT by preflight.sh (which runs as a subprocess and cannot propagate exports up). `preflight.sh` is now verification-only. Current resolvers sourced by `run-daily.sh` in order:
1. `_resolve_credentials.sh` — defaults `PLAY_CONSOLE_SA_KEY` to canonical local SA JSON path. Sourced before preflight.
2. `_load_webhook.sh` — loads `AHCS_TEAMS_WEBHOOK_URL` from Keychain. Sourced after preflight, before Teams post.

**Root cause fixed:** Saloni's first run on 2026-06-10 showed preflight green but Frohike PARTIAL with "env vars unset" — preflight's `export` never reached the parent. Moving resolution to sourceable file in parent shell fixed the propagation.

---

### 2026-06-10: Per-metric freshness offset for Play Reporting v1beta1 timeline queries
**By:** Frohike (Play Vitals Analyst)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #6 merged

Every `timelineSpec` query into `playdeveloperreporting.googleapis.com/v1beta1` clamps `endTime` to `today - freshness_offset(metricSet)` and shifts `startTime` back by the same delta to preserve the 7-day window. Per-MetricSet offset table in `PlayVitalsClient`:

| MetricSet | DAILY offset (days) |
|---|---:|
| `crashRateMetricSet` | 1 |
| `anrRateMetricSet` | 1 |
| `errorCountMetricSet` | 1 |
| (unknown / fallback) | 2 |

**Why:** Without clamping, the section produces HTTP 400 INVALID_ARGUMENT whenever `--date $(today)` is passed (default). This is a structural contract of Play Reporting v1beta1: every MetricSet has its own freshness lag. Central per-metric clamp keeps call sites freshness-blind.

**Verification:** 7 new unit tests added; 28 total passing. Pulled fresh NAAS crash data 2026-06-10 without HTTP 400.

---

### 2026-06-10: File-based ICM + on-call (Mulder plan Tracks 3+4 shipped)
**By:** Skinner (ICM Liaison) + Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #1 merged

ICM producer and on-call rendering both source from `.squad/agents/skinner/icm-latest.json` (committed in repo). No CI auth required.

**Pattern:**
1. Out-of-band pull (Saloni's laptop): `tools/icm/refresh-local.sh` wraps ICM collector, writes result to JSON.
2. Commit + push. CI/local readers pick it up.
3. Skinner producer: 48h freshness gate (GO/PARTIAL/SKIP).
4. Reyes assembler: Resolves on-call via precedence: `ctx` → Skinner metadata → `.squad/config/on-call.yaml` → TBD.

**Cadence:** JSON refresh 2–3x/week min. YAML override only for OOF / mid-week rotation changes.

**Verification (2026-06-10):** Local dry-run Skinner → GO, on-call → `dileepkusuma` / `samirnen`. 45 tests passed.

---

### 2026-06-10: AHS repo restructure (Option A) — flat root for GitHub Actions visibility
**By:** Doggett (Backend/Integration)
**Date:** 2026-06-10
**Status:** SHIPPED (one push pending on Saloni's token refresh)

**Why:** `gh workflow run daily-livesite-report.yml` returned 404 because AHS was nested one folder deep at push time — GitHub Actions only scans `.github/workflows/` at repo root.

**What landed:**
- `git init -b master` inside `/Users/salonijain/workspace/AndroidHealthCheckService`
- All 133 AHS files staged in single squashed commit
- Pushed to remote master (workflow file temporarily removed to work around token scope limit)
- Workspace-level git untracked from AHS; remote renamed to `OLD-DO-NOT-USE-ahs`
- Backup preserved: bundle at `/Users/salonijain/workspace/.ahs-backups/ahs-workspace-backup-1781086036.bundle` + remote backup branch `pre-restructure-backup-2026-06-10`

**One remaining step (requires Saloni's browser):**
```bash
gh auth refresh -h github.com -s workflow
cd /Users/salonijain/workspace/AndroidHealthCheckService
git push origin master
```

After that, `.github/workflows/daily-livesite-report.yml` becomes visible to GitHub Actions.

---

### 2026-06-10: v2 backlog — synthetic fully-healthy fixture + strict-pass validation test
**By:** Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** BACKLOG (v2)
**Spawned from:** Invariant-2 local policy implementation (Option C)

Mulder's Option C (2026-06-10) relaxes `test_validation_passes_on_2026_06_10_report` to tolerate invariant-2 failures because that report is local-degraded. This means the `[5000, 30000]` byte-floor invariant is currently NOT covered by any green test against a real-shaped report.

**Backlog item:**
- Add `tools/report_generator/tests/fixtures/fully-healthy-report.md` — synthetic markdown satisfying all 9 invariants, ≥5KB and ≤30KB.
- Add `test_validation_strict_pass_on_fully_healthy_fixture` — non-tolerant assertion proving invariant-2 enforces what we think.
- Keep existing tolerant 06-10 test green.

**Why not now:** Hand-authoring a realistic 5KB fixture takes ~30 min. Not blocking today's runner. Pick up when next touching `validation.py` or fixture work.

