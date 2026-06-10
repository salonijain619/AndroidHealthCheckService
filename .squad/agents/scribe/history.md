# scribe — Learnings

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

### 2026-06-10 — Largest fan-out to date: 6-agent report-generator build

**What:** Saloni requested Coordinator to fan out six agents (Mulder → Frohike+Langly → Doggett+Reyes+Scully) to design and implement the daily report-generator CLI in a single day.

**Wave pattern proved robust:** Serial-first (Mulder architecture) → parallel horizontal (Wave 2 producers) → serial assembly (Reyes) allowed dependency isolation and per-wave error handling. Fail-soft semantics (PARTIAL/SKIP vs FAIL) prevent cascade.

**Inbox consolidation pattern:** Mulder, Frohike, and Scully each dropped a decision into `.squad/decisions/inbox/` at end of day. Scribe merged all three into `.squad/decisions.md` under a dated section, deleted inbox files via `git rm`, and created a parallel orchestration log. This pattern scales well for multi-agent fan-outs (no manual conflict resolution, single source of truth maintained).

**Orchestrator/Assembler separation principle:** Mulder's split between orchestrator.py (wave scheduling, timeouts, per-producer error capture) and assembler.py (cross-section framing rules, final markdown) makes each module testable and likely reusable for other report types (weekly report, monthly digest, ad-hoc investigations). Establishes a producers-orchestrator-assembler (POA) pattern for future report-like work.

**Open questions deferred well:** Four design questions (runner choice, SP ownership, auto-commit, ICM cadence) were captured in Mulder's spec without blocking the build. Scribe surfaced them in orchestration log next-actions for Saloni. Allows parallelism without stalling on unknowns.

**Next application:** When quarterly or weekly reports are commissioned, reuse POA pattern and inbox-consolidation workflow. Likely candidates: weekly mobile health summary (reuse Langly+Frohike+Scully producers, different assembler template) and monthly compliance report (different producers, same orchestration layer).
