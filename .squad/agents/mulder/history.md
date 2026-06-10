# mulder — Learnings

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


## 2026-06-05T12:55:00Z — Cross-agent: ICM baseline + Android telemetry architecture
Scully + Doggett ran in parallel against `WD.Client.Android-icm-copilot/agent-docs/`. Two convergent findings + two new skills:
- **CORRECTION:** Android client telemetry IS ADX-queryable via `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (Kusto, via `azure-mcp-kusto`). Both agents independently confirmed this. Supersedes the prior "Android client = App Insights `wd-prod-android-client` REST endpoint only" assumption — AI is now cross-check status.
- **GSA's home subtable:** `TelemetryVPNAndWebProtection` (`Vpn*`/`Tunnel*`/`Naas*`/`Edge*` events route here via Kusto update policies + `bag_unpack`). 10 domain subtables total under MDATPAndroidDB.
- **22 of 30 Defender-vetted ICM queries** now mapped to specific daily-livesite-report sections — see Scully's new `android-icm-baseline-mapping/SKILL.md` and the section-index table at the top of `android-kusto-starter/SKILL.md`.
- **Version-regression detection pattern** for Android (analog of Windows v2.28.96 playbook) — see Doggett's new `android-version-regression-detection/SKILL.md` (confidence LOW; pairs Doggett+Scully on first use). Uses ECS feature-flag `ClientVersion`-targeting + per-version metric divergence.
- Decisions `scully-icm-baseline-adopted` + `doggett-android-telemetry-docs-ingested` merged to `decisions.md`, PROPOSED, pending Mulder ack. Clarification note appended to prior "GSA Kusto Catalog adopted" decision flagging the supersession.

## 2026-06-08T16:23Z — Cross-team notification: ICM v1 integration shipped + detector silence finding

**From:** Doggett, Scully, Reyes (orchestrated by Scribe)

**New skill:** `.squad/skills/icm-queue-ingest/SKILL.md` (confidence MEDIUM, promote to HIGH after second clean cycle). HarryPotter's `agency mcp icm` pattern ported for team 106961. Single source of truth `.squad/config.json :: icm.team_id`. Doggett owns doc maintenance; Scully executes per report cycle; Reyes owns template sections (On-Call + Active ICM Incidents + Patterns).

**v2 report shipped:** `daily-livesite-report-android-2026-06-06.md` at repo root. NAAS v1 preserved verbatim. Three new ICM sections live (On-Call roster, Active ICM counts/tables, Patterns). Effective real-incident = 0 (one TestICM-flagged Sev3 doesn't count). On-call primary `dileepkusuma`, backup `samirnen`.

**Findings for your review:**
1. **Detector silence is suspicious.** Zero system-detected ICMs on team 106961 while Scully's NAAS 7d pull shows 0.36% sustained tunnel failure (5× ramp). Either no Android-tagged detector exists on the queue or routing isn't hooking detector-emitted ICMs. Worth an ack from you both that this isn't a "false reassurance" artifact.
2. **Queue identity open question for Saloni.** `owningTeamId=106961` returns `owningTeamName="GSA  Client - XPlat"` (with double-space typo from ICM). Confirm 106961 is the Android queue vs a parent queue with an Android sub-queue. If sub-queue exists, entire ICM section is scoped to the wrong target.

**Decisions merged:** 6 inbox files (HP discovery, skill authored, NAAS 7d, v1 report, ICM first pull, v2 report) into `.squad/decisions.md`.

---

## 2026-06-10 — Team expansion: Frohike and Langly hired

Two new team members hired 2026-06-10: Frohike (Play Vitals Analyst) owns Google Play Console crash/ANR analysis, NAAS-filtered; Langly (Release Tracker) pulls current Play Store version of `com.microsoft.scmx` on every report cycle. Frohike replaces Scully's ad-hoc Play Vitals ownership and outputs to `.squad/agents/frohike/research/naas-crashes-{date}.md`. Langly surfaces as a one-line header in every daily/weekly report, anchoring crash data to shipping version. Daily report assembly (Reyes) now pulls from Scully (server) + Frohike (Play crashes) + Langly (current version) in parallel. ICM investigations also fan out to Frohike for client-side crash signature matching.

---

## 2026-06-10 — Architecture decision: daily report generator CLI

Authored `.squad/decisions/inbox/mulder-report-generator-architecture.md` as Doggett's implementation spec for cron-driven daily report generation. Key architectural calls and the trade-offs behind them:

**1. SectionResult + 4-status enum (GO/PARTIAL/SKIP/FAIL) as the producer contract.** Considered a simpler `(markdown, ok_bool)` tuple but rejected: PARTIAL is structurally different from FAIL (Skinner's CI ICM skip is *expected*, Scully timeout is *degraded*, Frohike auth-missing is *configuration*). The assembler's banner and the Contributors footer need to distinguish these, and `--validate` thresholds differ. Three-state would have collapsed SKIP and PARTIAL — wrong because SKIP is silent, PARTIAL is loud.

**2. Three-wave execution model (Langly → {Scully, Frohike, Skinner} parallel → Reyes) over a generic DAG.** A topo-sorted DAG would be more "correct" but the dependency shape is fixed and small. Encoding it as three explicit waves keeps `orchestrator.py` <100 lines, makes failure stories per-wave easy to reason about, and matches the 2026-06-10 "lead-with-Play-Store-version" decision verbatim (Langly first is a structural rule, not just an ordering). Trade-off: if we ever add a fifth producer that depends on Frohike (e.g. a Play Vitals trend differ), we add Wave 2.5, not a graph refactor. Acceptable.

**3. Concurrent.futures ThreadPoolExecutor over asyncio.** Producers will be implemented by four different agents over multiple weeks. Sync code is easier to standalone-run (constraint-critical for testability — Frohike must be able to `python -m tools.report_generator.sections.frohike_play_vitals` without spinning the whole orchestrator). I/O-bound work means GIL is not the bottleneck. The 10–15% latency win from asyncio doesn't justify the contract complexity or the harder debugging.

**4. ICM auth: option (c) graceful skip via env var.** Considered (a) hardcode-skip and (b) require SP workaround. Rejected (a) because hardcoding removes the future agency-CLI-SP path. Rejected (b) because `tools/icm/icm_collector.py` line 8–16 already documents that the SP path doesn't exist upstream — we cannot block daily reporting on something not in our control. (c) preserves optionality + matches the existing weekly-cadence framing pattern in the 06-10 report. Side benefit: the same env var lets local devs skip ICM during testing.

**5. Validation hook is its own module (`validators.py`), runs post-assembly, fails the workflow only in `--validate` mode.** The 9 invariants are partly structural (H1, Langly header, Exec Summary present) and partly defensive (5–30KB size band, no `/Users/` leakage, no Jinja `{TBD` markers). The size band is calibrated to the existing 4 reports (14.5KB–25.5KB → 5–30KB envelope). Splitting validators out means producers can call individual checks during dev without `--validate`'s exit-1 behavior.

**6. Fixed report shape — Reyes does NOT redesign.** Cross-section framing rules (the `.04xx` ring tag, `LIVE PROD` tag, NAAS-as-a-unit, per-version table primary) are carried in `metadata` dicts the assembler consumes, not invented per-cycle. This is explicit so the contract is closed to the 06-10 shape; any template change requires a new decision file. Trade-off: less expressive Reyes, but the alternative is template drift across cron runs, which destroys the "exec-readable at-a-glance" property Saloni wants.

**7. Four open questions for Saloni held back BEFORE Doggett implements.** Runner choice (self-hosted vs hosted) directly affects WIF feasibility and Kusto reachability — getting that wrong means a rewrite. SP ownership for Kusto is the long-pole blocker. Auto-commit policy interacts with Scribe's existing ownership. ICM cadence formalization is the smallest of the four but unblocks `config.py` constants. Listed explicitly with Mulder's lean for each so Saloni can ack/override fast.

Reviewer role discipline held: did not write Kusto/Python/ICM code. Doc is a spec for Doggett (orchestrator), Reyes (assembler), Frohike/Langly/Scully/Skinner (producers) to implement against in parallel.
