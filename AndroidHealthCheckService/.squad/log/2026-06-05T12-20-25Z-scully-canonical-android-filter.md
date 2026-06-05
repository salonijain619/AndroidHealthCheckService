# Session Log — 2026-06-05T12:20:25Z — scully-canonical-android-filter

**Topic:** Canonical Android KQL filter confirmation
**Agent:** Scully

## Summary
Scully executed verbatim panel KQL from the production Android GSA dashboard against `idsharedwus / NaasProd / TunnelServerOperationEvents`. Result: 8 distinct active Android tenants (7d). Established canonical filter `DeviceOs has_cs 'ANDROID'` and Android-specific `ClientVersion` format `1.0.NNNN.NNNN`.

## Artifacts
- Decision merged: canonical Android filter (PROPOSED, pending Mulder ack)
- Skill updated: `.squad/skills/android-kusto-starter/SKILL.md` (7 queries, confidence bumps)
- Research updated: `.squad/agents/scully/research/dashboard-analysis.md` (Ground Truth section)

## Open items
- Mulder ack
- Saloni: 37-version allowlist auto-curated or manual?
