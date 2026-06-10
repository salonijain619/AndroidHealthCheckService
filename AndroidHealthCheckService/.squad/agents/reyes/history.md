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

### 2026-06-05: Daily Livesite Report Skeleton Established [SUMMARIZED]
Template files created (canonical skeleton + filled example). 7-row Key Metrics table, Android-specific adaptations (version distribution health, API level variance, OEM/device model signals). Open questions for Scully on channel tracking, OS version baselines, OEM variance. See archive.

### 2026-06-05T13:45Z — First executable Android NAAS-only daily livesite report assembled [SUMMARIZED]
v1 report assembled from Scully's NAAS 7d data. Followed Windows-reference style, traced every numeric value to Scully results. Anchored Top Insight #1 on tunnel failure-rate 5× ramp, used Scully's correlation chain #1. Surfaced ghost-column defect prominently. Three P2s + two info-level Top-5. See archive.

### 2026-06-06T11:50Z — v2 daily report assembled (NAAS preserved + live ICM plugged in) [SUMMARIZED]
v2 reused NAAS verbatim from v1. Added live ICM roster, brand-new Active ICM section with counts + tables, Data Quality ICM subsection. Bucketing footnote on Customer-Created table. Queue-identity open question surfaced for Saloni (`owningTeamId=106961` returns XPlat team name — may be parent queue). See archive.

## Current learnings (active)

### 2026-06-09T14:46+05:30 — v3 daily report assembled (NAAS refreshed + ICM reused at 06-08 freshness)

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

**Asymmetric freshness framing:** NAAS is fresh today (06-09 run), ICM is 1 day old (06-08, no movement). Explicitly labeled both windows in the `> v3 note:` and on the ICM section header.

### 2026-06-10 — Team expansion: Report now pulls from Scully + Frohike + Langly in parallel

Daily report assembly (Reyes) now pulls from three parallel sources: Scully (server-side NAAS telemetry), Frohike (Google Play Console crash/ANR analysis, NAAS-filtered), and Langly (current Play Store version of `com.microsoft.scmx`). Lead every daily/weekly report with Langly's one-line Play Store version header to anchor crash/ANR data to the currently shipping Defender version. Frohike replaces Scully's ad-hoc Play Vitals ownership and outputs `.squad/agents/frohike/research/naas-crashes-{date}.md`. ICM investigations also fan out to Frohike for client-side crash signature matching. Framing rule: all Play Vitals output MUST be NAAS-as-a-unit, never Defender-filtered-to-NAAS.
