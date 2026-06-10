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

## 2026-06-10T17:43+05:30 — Track 3+4 shipped: on-call wiring (PR #1)

Paired with Skinner; Reyes owned the assembler + YAML fallback. Branch `track3-track4-file-based-icm-oncall`.

### Learnings
- **On-call precedence chain (assembler `_resolve_oncall`):**
  1. `ctx['oncall_primary']` / `ctx['oncall_backup']` (explicit override from orchestrator).
  2. `sections['skinner_icm'].metadata['on_call'] = {primary, backup}` — Skinner publishes this when it loads `.squad/agents/skinner/icm-latest.json`.
  3. `.squad/config/on-call.yaml` — `schedule[].{from, to, primary, backup}`; pick the entry whose `from <= date <= to`.
  4. Literal `TBD`.
- **YAML reader is PyYAML-optional.** Ships an inline minimal parser for the documented shape so the assembler stays import-clean if PyYAML isn't on the runner. PyYAML used when present.
- **JSON shape consumed (from icm_collector):** Skinner publishes only the on-call sub-shape into metadata, but full payload also has `active_icms` / `mitigated_icms` / `_meta.fetched_at` (used as `pull_date`).
- **Freshness gate is Skinner's, not Reyes's.** Skinner returns PARTIAL with stale note if > 48h; assembler still gets `metadata['on_call']` populated and uses it. So an aging JSON keeps the on-call current as long as the rotation didn't change.
- **Fallback YAML location:** `.squad/config/on-call.yaml`. Reyes reads, Saloni hand-maintains for OOF / mid-week rotation changes.
- **Test invariant updated:** old `test_oncall_falls_back_to_TBD_when_missing` now asserts `TBD-update-me` (the YAML seed). New companion test exercises the Skinner-metadata path explicitly.
