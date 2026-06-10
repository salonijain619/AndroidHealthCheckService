# reyes — Learnings

## Project Context
Android GSA Client Service Health Check. Telemetry: server-side NAAS (Kusto), client-side AppInsights + Aria Kusto. Report: daily livesite → Teams IDNA GSA channel.

## Key Learnings (Consolidated)

**Report assembly evolution (v1→v4):**
- v1 (06-05): NAAS-only daily from Scully's 7d data, skeleton template established.
- v2 (06-06): Added live ICM roster + Active ICM section.
- v3 (06-09): Fresh NAAS refresh; headline P2 promoted to P2→P1 trend; Microsoft 1P hypothesis falsified; .04xx ring + EU regions escalated.
- v4 (06-10): 3-source fusion (Scully server + Frohike Play Vitals + Langly Play Store version). Langly header leads; Server↔Client correlation table added; .04xx demoted to P3 ring-risk (not live); EU crash-rate finding promoted.

**Assembly invariants (enforced by assembler.py):**
1. Langly version header immediately under H1, before Exec Summary.
2. Section order closed: H1 → Langly → Scope → Reframe (optional) → On-Call → Exec Summary → Key Metrics (Scully/Frohike subsections) → ICM → Contributors → Run Diagnostics.
3. Server↔Client subsections in Key Metrics are PEERS (separate denominators, never merged).
4. Run Diagnostics always at bottom for Saloni's triage.
5. No new sections without decision file.

**Exec-summary bullet logic:** Render order (langly, scully, frohike, skinner). For each: take `metadata['exec_bullet']` if present, else omit (don't invent). Degrade to sentinel ⚠️ if SKIP/FAIL.

**Teams re-fire pattern (06-10T17:37):** Payload `{"text":"<markdown>"}` (json.dumps escaping), urllib.request POST, Content-Type: application/json. HTTP 202 = success.

**Gotchas:** Date format `%-d` (GNU) fails on Windows → fallback chain `%-d` → `%#d` → manual strip. Langly header if FAILed → degraded line (not omit). ICM PARTIAL → canonical phrasing verbatim for continuity.
