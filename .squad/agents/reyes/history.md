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

### 2026-06-10T12:45+05:30 — First 3-source daily assembled (Scully + Frohike + Langly fusion)

Assembled `daily-livesite-report-android-2026-06-10.md` (25,082 bytes) — first daily that fuses three parallel research sources. Pattern crystallized:

**3-source assembly pattern:**
1. **Langly's Play Store version header goes FIRST** (right under the title, above Executive Summary). It is the anchor that contextualizes every per-version number downstream. Without it, server-side and client-side version cohorts cannot be classified as "live customer" vs "internal ring."
2. **Scully (server-side NAAS) + Frohike (client-side Play Vitals) are PEERS, not nested.** Key Metrics now has TWO labeled subsections ("Server-side / Scully" and "Client-side / Frohike") — never merge their denominators. Server denominator = NAAS sessions; client denominator = whole-app `com.microsoft.scmx` installs. The "Denominator framing rule" callout is mandatory.
3. **Frohike gets its own top-level section** ("NAAS Client Stability (Google Play Vitals)") placed AFTER Key Metrics and BEFORE Top Insights. Per-version table is PRIMARY; top crashes/ANRs are top-3 with hypothesis (NOT all 8); subsystem breakdown is the closer.
4. **Cross-Domain section gets a new "Server↔Client per-version alignment" table.** First time we can show same-shape corroboration on a per-version axis. The .04xx ring (server +131% fail-rate ⟷ client 33.7% native SIGSEGV concentration ⟷ Langly "not on prod track") was the cleanest dual-signal example to date.

**Narrative reframes that came out of the 3-source fusion (would NOT have been possible with Scully alone):**
- **`.04xx` ring DEMOTED** from yesterday's top P2 anchor to forward-looking P3 ring-promotion risk. Langly's "live prod = 9002.0102, not 9003.0401" is the trigger; Frohike's "all 4 .04xx SKUs are sub-privacy-threshold install base, crash-only with 0 ANR" is the corroboration. Made explicit in Exec Summary lead-in.
- **EU finding PROMOTED** to top P2 cross-domain anchor. Frohike independently surfaced Germany 3.25% whole-app crash rate (over Google's 1.09% Play Console bad-behavior threshold) — same region cluster Scully sees server-side. Added new framing: "Play Store visibility/ranking risk, independent of NAAS attribution."
- **Server↔client correlation strongest at `libnaas_native_vpn.so` SIGSEGV** (Frohike Top-Crash #3, 33.7% .04xx). Cleanest code-localized evidence the ring-promotion risk is real.

**Structural rules that survived from v3 (06-09) into this report:**
- On-Call kept as compact 2-row table (no metadata prose).
- ICM reused at prior freshness with explicit "live as of X, no movement" header + weekly-cadence footnote.
- Microsoft 1P falsified hypothesis kept with strikethrough for retraction visibility.
- Detector silence pattern (3+ pulls, zero auto-ICMs) escalated each cycle.

**Removed per Saloni's approved 06-09 template:** Patterns section, Data Completeness Notes, Data Quality Notes tail. Did NOT re-introduce.

**Sizing:** Target was 18–22KB; landed at 25KB. The new "NAAS Client Stability" section is ~7KB on its own (per-version table + 2 top-N tables + subsystem breakdown). Acceptable on a first-fusion daily; can trim subsystem breakdown to prose next cycle if Saloni wants the bound enforced.

**Decision worth promoting:** Lead every future daily/weekly with Langly's one-line Play Store version header. Filed to `.squad/decisions/inbox/reyes-play-store-version-header-first.md`.

2026-06-10: Assembled v4 daily livesite report (25,489 bytes) integrating Frohike Play Vitals + Langly version data. Led with `.04xx` reframe + Germany 3.25% EU cross-domain finding. Proposed version-line header convention (decision filed).

### 2026-06-10T14:46+05:30 — Wave-3 assembler shipped (`tools/report_generator/assembler.py`)

Implemented Mulder's Wave-3 module per the architecture decision in `.squad/decisions/inbox/mulder-report-generator-architecture.md`. 8/8 tests passing.

## Learnings

**Assembly invariants (the rules the assembler enforces, lifted from the 06-10 manual report):**

1. **Langly version header sits immediately under H1, not under an H2.** This is the §8.4 validator invariant and Saloni's lead-with-Play-Store-version decision (2026-06-10 in `.squad/decisions.md`). The assembler emits it as the very first non-H1 block; if Langly FAILed, it falls back to a clearly-degraded line rather than omitting (per Mulder §7).
2. **Section order is closed.** H1 → Langly header → Scope → (optional Reframe) → On-Call → Exec Summary → Key Metrics (Scully then Frohike, in that order) → ICM → Contributors → Run Diagnostics. **Reyes does NOT introduce new sections without a new decision file.**
3. **Server-vs-client framing is mandatory.** Key Metrics has two labeled subsections ("Server-side / Scully" and "Client-side / Frohike"). Never merge their denominators. The assembler tolerates a producer including its own `###` header (passes through) or omitting one (assembler injects the canonical header).
4. **`scully_server_telemetry` vs `scully_server` alias.** Mulder's spec uses the long form; the task brief abbreviated. The assembler accepts both via `_SCULLY_KEYS` so producers and the orchestrator can converge without churn.
5. **Run Diagnostics table is at the very bottom.** Saloni triages failed runs from this single table — it must always render, regardless of section health.

**Exec-summary bullet selection rule:**

- Iterate `_ORDER = (langly, scully, frohike, skinner)` — fixed render order, matches the 06-10 narrative cadence (anchor first, server ramp, client cross-domain, structural/ICM).
- For each section: take `metadata['exec_bullet']` if present. If absent, **silently omit** — do not fabricate. This is the "DO NOT invent data" rule operationalised.
- If status is SKIP or FAIL: replace the bullet with `_⚠️ {section_name} unavailable this run — see logs._` (sentinel line for visibility without blocking the report).
- Prepend the section emoji ONLY if the producer didn't already lead with an emoji — preserves producers' tone (Scully's 🟠, Frohike's 🌍) while back-filling Langly's 📱 when omitted.

**Date format gotcha — captured in `format_date_header()`:**

- `%-d` is a GNU/POSIX extension. Doggett's Ubuntu CI runs it fine; Windows dev boxes do not.
- Three-tier fallback: `%-d` → `%#d` (Windows) → `%d` with manual leading-zero strip. The test `test_date_header_formatting` covers both two-digit (`Jun 10`) and one-digit (`Jun 5`) cases.

**Voice/tone notes from re-reading 06-10 (the things the assembler must NOT break):**

- **Data-forward, blunt, no hedging.** Exec bullets lead with the number, not the framing. The assembler doesn't add prose — it just stitches.
- **Emoji as severity grammar.** 🟠 = P2, 🟡 = P3, 🔴 = structural/blocking, ✅ / ⚠️ / ❌ for status. The Run Diagnostics table uses the same vocabulary so triage is consistent with the body.
- **Side-by-side server↔client framing.** The two Key Metrics subsections are PEERS — never nested. The assembler enforces this by always emitting both subsection headers in order, even when one section is degraded.
- **Stubs are explicit, not blank.** Per Mulder §7: a FAILed section becomes a blockquote pointing to `tools/report_generator/runs/{date}/errors.log`. A SKIPped section becomes a `⏭️` blockquote. ICM PARTIAL gets the canonical "_ICM data not refreshed in this run (CI auth limitation). Last manual pull: {date}._" phrasing — verbatim continuity with the 06-10 manual report so Saloni sees the same shape whether ICM ran or didn't.

**Defensive-imports pattern (worth keeping):** `contracts.py` is Doggett's file and was not yet in tree when this landed. The assembler does `try: from tools.report_generator.contracts import …` then falls back to a local `dataclass` mirror. This made my module standalone-testable; when Doggett ships contracts.py, the import flips automatically and the tests stay green because they import `SectionResult`/`Status` from the assembler (which re-exports whichever source won).

**Test-fixture sizing lesson:** First test run failed the 5KB floor because my fixture markdown was unrealistically thin (~3.7KB total). Real producers ship per-section tables of 1–7KB. Bumped Scully fixture to the 9-row metrics table from 06-10 and Frohike to the 7-row metrics table + 4-row per-version table. Now naturally lands ~7KB, well inside the 5–30KB validator band. **Takeaway:** test fixtures should approximate real producer output size, not just shape — otherwise the size invariant test is meaningless.
