# Routing

Route work to the right team member based on signals in the user's message.

## By Keyword

| Signal | Route to |
|--------|----------|
| scope, decision, architecture, plan, prioritize, review | Mulder |
| kusto, KQL, telemetry, query, AppInsights, Aria, anomaly, metrics, dashboard | Scully |
| Play Console, Play Vitals, Google crash report, ANR, NAAS crash, per-version crash | Frohike |
| Play Store version, latest Defender version, current release, what's live | Langly |
| Android, WD.Client.Android, repro, client code, crash repro, logcat, manifest, onboarding | Doggett |
| ICM, incident, escalation, on-call, sev, mitigation, livesite | Skinner |
| report, write-up, summary, Teams post, doc, weekly, executive | Reyes |
| log, decision history, what did we decide | Scribe (read decisions.md directly) |
| status, board, backlog, monitor, keep working | Ralph |

## By Task Type

| Task | Primary | Anticipatory |
|------|---------|--------------|
| Investigate new ICM incident | Skinner | Scully (server telemetry), Frohike (client crashes), Doggett (repro) |
| Write daily/weekly service health report | Reyes | Scully (server), Frohike (Play crashes), Langly (current version), Mulder (review) |
| New Kusto query for an issue | Scully | Doggett (interpret client signals) |
| Pull Google Play crash data for NAAS | Frohike | Langly (version context), Scully (server cross-ref) |
| Get latest Play Store Defender version | Langly | — |
| Diagnose Android client bug | Doggett | Scully (server telemetry), Frohike (Play crash signature) |
| Prioritize backlog | Mulder | Skinner (incident severity) |

## Defaults

- Multi-domain ("team, ...") → Mulder coordinates + 2-3 specialists
- Ambiguous → Mulder triages
- Server-telemetry-heavy → Scully leads
- Client-crash-heavy (Play Console) → Frohike leads
- Incident-driven → Skinner leads
- Every report cycle → Langly fires automatically for current Play Store version
