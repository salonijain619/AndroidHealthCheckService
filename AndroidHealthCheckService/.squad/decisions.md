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

