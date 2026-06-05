# Session Log — 2026-06-05T12:55:00Z — ICM baseline + Android telemetry docs ingest

## Headline
**Both Scully and Doggett INDEPENDENTLY converged on `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` as the canonical Android client telemetry cluster.** Two independent paths (Scully via `IcmBaselineQueries.md`, Doggett via `agent-docs/Telemetry.md`) → confidence on the supersession is HIGH. This corrects the prior "Android client = App Insights `wd-prod-android-client` REST only" assumption from the catalog-ingest cycle; AI is now a cross-check, ADX is operationally preferred and Kusto-queryable via `azure-mcp-kusto`.

## Cycle outcomes
- **Scully:** ingested 30 Defender-for-Android ICM baseline queries; 22 map directly to report sections. New skill `android-icm-baseline-mapping` (medium). `android-kusto-starter` restructured (Part 1 server / Part 2 client; ICM queries → HIGH confidence).
- **Doggett:** ingested 8 `agent-docs/` files; closed 4 of 13 open questions outright (5 partial / 4 still blocked on VSTS). New reference doc `android-telemetry-model.md`. New skill `android-version-regression-detection` (low; pairs with Scully on first use). ECS feature-flag targeting by `ClientVersion` enables Android analog of Windows v2.28.96-style regression detection.
- **Architecture map (now stable):** 3-layer ADX pipeline `customEvents` (raw, JSON props) → 10 domain subtables (Kusto update policies + `bag_unpack`) → aggregated tables (Azure Function `KustoQueryFunc`, hourly modulo-scheduled). GSA lives in `TelemetryVPNAndWebProtection`.

## Decisions merged
- `scully-icm-baseline-adopted.md` — ICM queries adopted as canonical client-side starting point.
- `doggett-android-telemetry-docs-ingested.md` — Defender docs ingested; pipeline + emitter model documented.
Both PROPOSED, pending Mulder ack. Clarification note appended to the prior "GSA Kusto Catalog adopted" decision flagging the partial supersession.

## Cross-agent
Mulder, Reyes, Skinner histories updated with: MDATPAndroidDB correction, GSA→TelemetryVPNAndWebProtection routing, 22 ICM-vetted queries mapped, version-regression skill availability.

## History summarization
- Doggett history was 21,534 bytes — over the 15,360 gate. Summarized this pass; full content moved to `agents/doggett/history-archive.md`.
- Scully (14,409) under gate; no summarization.

## Open dependencies
- Mulder ack on both new decisions.
- Saloni: confirm `azure-mcp-kusto` can authenticate against `mdatpandroidcluster.westus2.kusto.windows.net`.
- Saloni: unblock VSTS read on WD.Client.Android (all 4 still-blocked discovery questions reduce to this).
