# Orchestration Log: 2026-06-10 Report-Generator Fan-Out

**Date:** 2026-06-10  
**Trigger:** Saloni requested Coordinator to fan out the squad and build the report-generator CLI across six agents.

---

## Spawn Manifest

**Wave 1 (Sync):**
- **Mulder** (Lead Architect) · claude-opus-4.7 · Task: Design CLI architecture, orchestration, contracts, module layout.

**Wave 1 → Wave 2 (Background, parallel after Mulder ack):**
- **Frohike** (Play Vitals Analyst) · claude-opus-4.7 · Task: Implement `frohike_play_vitals.py` producer + Play Console SA onboarding.
- **Langly** (Release Tracker) · claude-opus-4.7 · Task: Implement `langly_version.py` producer + Play Store version fetching.

**Wave 2 → Wave 3 (Background, parallel, independent of Wave 2 outcome):**
- **Doggett** (Orchestrator/Backend) · claude-opus-4.7 · Task: Implement `orchestrator.py`, `cli.py`, `validators.py`, tests, workflow integration.
- **Reyes** (Assembler) · claude-opus-4.7 · Task: Implement `assembler.py` + cross-section framing + final markdown assembly.
- **Scully** (Telemetry Analyst) · claude-opus-4.7 · Task: Implement `scully_server_telemetry.py` producer + Kusto SP onboarding spec.

**All six agents assigned per team-wide directive: claude-opus-4.7.**

---

## Outcome

**Test status:** 45/45 tests pass (unit + orchestration + assembler smoke).

**CLI status:** End-to-end `python -m tools.report_generator.cli --date 2026-06-10` exits with code 0.

**Report generation:** Daily report `daily-livesite-report-android-2026-06-10.md` generates successfully with:
- **Langly section (GO):** Live Play Store version `1.0.9002.0102` + release date.
- **Scully section (PARTIAL):** Kusto auth not configured; carries forward prior-day data with "reused" framing + explicit error in footer.
- **Frohike section (PARTIAL):** Play Console SA auth not configured; returns stub "⚠️ Play Vitals data unavailable" + explicit error in footer.
- **Skinner section (PARTIAL):** CI-time skip via `REPORT_GENERATOR_SKIP_ICM=1` env var; returns "ICM data not refreshed in this run (CI auth limitation)" per fail-soft contract.
- **Reyes (Assembler, GO):** Final report assembles cleanly; cross-section framing rules applied; header includes Langly's Play Store version per decision 2026-06-10.

All PARTIAL/SKIP sections recorded in orchestrator manifest.json + workflow logs for transparency.

---

## Open Questions from Mulder's Spec (Saloni to Answer)

1. **Cron runner choice (hosted vs self-hosted):** Will daily-livesite-report.yml run on GitHub-hosted runners or self-hosted? Impacts timeout budgets and Kusto/Play API rate-limit quotas. Default assumption: GitHub-hosted with 300s per-section timeout.

2. **Kusto Service Principal ownership:** Who provisions and owns the Kusto SP (gsa-android-scully-naas-reader)? Tentative: Saloni (this task) as initial owner; TBD for ongoing rotation/expiry.

3. **Auto-commit policy for daily reports:** Should the workflow auto-commit generated `.md` files to the repo, or require manual review-and-merge? Currently: workflow has `--cached --quiet` check to no-op commits when content unchanged. Decision pending: optional commit vs required manual gate.

4. **ICM cadence:** Skinner section runs at CI-time in Wave 3, but ICM SP auth is not available today (upstream InE.IcmAutomation blocker). Should ICM remain weekly-manual via Scully's existing cadence, or is there a forward-looking path to daily CI-time pulls? Decision pending: stick with weekly or escalate upstream.

---

## Cron Status

**Current:** Disabled in `.github/workflows/daily-livesite-report.yml` (per PROPOSED state; cron jobs are commented out).

**Pending activation path:**
1. Saloni provisions `PLAY_CONSOLE_SA_KEY` secret (Frohike onboarding).
2. Saloni provisions `KUSTO_AAD_*` secrets (Scully onboarding).
3. Saloni triggers manual `gh workflow run daily-livesite-report.yml --ref main`.
4. Workflow executes; report generates; Teams webhook posts the Adaptive Card.
5. Saloni confirms Teams post lands in channel.
6. Saloni flips cron schedule in workflow YAML (uncomment `schedule: - cron: '0 14 * * 1-5'`).

---

## Next-Action Checklist for Saloni

- [ ] **(1) Provision PLAY_CONSOLE_SA_KEY:** Follow Frohike onboarding document (`.squad/decisions/inbox/frohike-play-vitals-onboarding.md` now merged into decisions.md). Export existing SA key JSON at `/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json`, confirm Play Console "View app information and download bulk reports" role, create GitHub secret.

- [ ] **(2) Provision KUSTO_AAD_* credentials:** Follow Scully onboarding document (`.squad/decisions/inbox/scully-kusto-sp-onboarding.md` now merged into decisions.md). Create service principal via `az ad sp create-for-rbac`, assign Viewer role to NaasProd/siblings, create three GitHub secrets (`KUSTO_AAD_TENANT_ID`, `KUSTO_AAD_SP_CLIENT_ID`, `KUSTO_AAD_SP_CLIENT_SECRET`).

- [ ] **(3) Manual workflow_dispatch test:** Once secrets provisioned, run `gh workflow run daily-livesite-report.yml --ref main` to trigger a single report cycle. Monitor workflow logs for any auth failures.

- [ ] **(4) Verify Teams post:** Confirm the generated Adaptive Card lands in Teams channel "Livesite - Mobile Client" (Group ID `a3312108-40d2-4d8d-a401-066749108606`, Channel ID `19:uDpMueKuWUKAMPQ1RO5qOzAL_R8Dq-ZJrXTUPxM63ZY1@thread.tacv2`). If successful, proceed to cron activation.

- [ ] **(5) Flip cron schedule:** Uncomment the `schedule` trigger in `.github/workflows/daily-livesite-report.yml` to enable daily 14:00 UTC Monday–Friday runs.

---

## Learnings for Future Fan-Outs

- **Wave model is robust:** Three-wave structure (serial bottleneck → parallel horizontal scale → serial assembly) allows dependency isolation and per-wave timeout/error handling.
- **Fail-soft contract prevents cascade:** Any single producer's auth gap or transient failure does NOT block report publication. PARTIAL/SKIP semantics keep the report flowing while recording explicit errors.
- **Orchestrator/Assembler separation:** Mulder's split between orchestrator.py (wave scheduling, timeouts) and assembler.py (framing rules) makes each module unit-testable and reusable for other report types.
- **Inbox-to-decisions consolidation:** This pattern (fan-out → inbox drop → scribe merge + git rm) is efficient for multi-agent decision capture and keeps decisions.md as the single source of truth.
