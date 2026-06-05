# Session: Catalog + Marketplace Ingest — 2026-06-05T12:40:00Z

**Cycle topic:** Adopt GSA Kusto catalog; inventory client-plugin marketplace.

## Spawned this cycle
- **scully** (general-purpose, background, claude-opus-4.7) — catalog ingest
- **doggett** (general-purpose, background, claude-opus-4.7) — marketplace inventory (excluding catalog)

## Unknowns closed (3 of 4)
1. **PKI source:** `naas-idsharedwus / NaasCloudPkiProd / EnrollCertificateOperationSummary` (time col `PreciseTimeStamp`). Routing UNBLOCKED; query body still owes schema introspection.
2. **App Insights component:** `wd-prod-android-client` under sub `fb633419-6bb2-4a7e-8993-fd9456d19c4c`. App Insights REST API (NOT a Kusto cluster URL — `azure-mcp-kusto` will not route).
3. **Android client-side pipeline:** **App Insights**, NOT Aria. Independently confirmed by Doggett via the `wd-prod-` prefix.

## Correction logged
- **Charter point #2 (Scully) was wrong.** Prior assumption: Aria `mnap_xplat_*` is the Android client-side pipeline. Reality (per catalog): those tables are Win/Mac primary; Android rides App Insights. Aria carries Android only opportunistically (`errorevent` via `App_Platform == 'Android'`). Charter needs a correction pass in a future cycle.

## New clusters discovered
- `naas-idsharedscus` (`https://idsharedscus.southcentralus.kusto.windows.net`) — hosts the full 37-table `NaasProd`. `naas-idsharedwus / NaasProd` is a **2-table mirror only** (Tunnel + Edge). Roxy / Talon / ControlTower / NaaSVPN* / CertMonitor cross-checks require SCUS hop.
- `androidgsa.eastus.kusto.windows.net / Metric` — Android perf rollups (`MemoryCPUUsage`, `UploadDownloadSpeed`) by AppVersion + day. Catalog-flagged unverified (DNS failed during catalog generation); needs live reachability check before promotion.

## Decisions filed (now merged to decisions.md)
- `scully-kusto-catalog-adopted.md` — adopt upstream catalog as canonical; local Android slice is derived.
- `doggett-marketplace-inventory.md` — 0 ADOPT, 2 REFERENCE, 0 SKIP for non-catalog marketplace skills.

Both PROPOSED, pending Mulder ack.

## Standing unknown (still open)
- **Crash signal for Android.** Watson is Win32; Android needs Play Console / Crashlytics path. Not closed this cycle.
