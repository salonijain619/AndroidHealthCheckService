# Routing

Route work to the right team member based on signals in the user's message.

## By Keyword

| Signal | Route to |
|--------|----------|
| scope, decision, architecture, plan, prioritize, review | Mulder |
| kusto, KQL, telemetry, query, AppInsights, Aria, anomaly, metrics, dashboard | Scully |
| Android, WD.Client.Android, repro, client code, crash, logcat, manifest, onboarding | Doggett |
| ICM, incident, escalation, on-call, sev, mitigation, livesite | Skinner |
| report, write-up, summary, Teams post, doc, weekly, executive | Reyes |
| log, decision history, what did we decide | Scribe (read decisions.md directly) |
| status, board, backlog, monitor, keep working | Ralph |

## By Task Type

| Task | Primary | Anticipatory |
|------|---------|--------------|
| Investigate new ICM incident | Skinner | Scully (pull telemetry), Doggett (client repro) |
| Write weekly service health report | Reyes | Scully (data), Mulder (review) |
| New Kusto query for an issue | Scully | Doggett (interpret client signals) |
| Diagnose Android client bug | Doggett | Scully (telemetry context) |
| Prioritize backlog | Mulder | Skinner (incident severity) |

## Defaults

- Multi-domain ("team, ...") → Mulder coordinates + 2-3 specialists
- Ambiguous → Mulder triages
- Telemetry-heavy → Scully leads
- Incident-driven → Skinner leads
