# Decision: File-based ICM + on-call (Mulder plan Tracks 3+4 shipped)

**By:** Skinner (ICM Liaison) + Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** SHIPPED — PR #1 (`track3-track4-file-based-icm-oncall`)
**Closes:** Mulder plan §3 (Option B) and §4 (hybrid recommendation)

## What

Skinner's ICM producer and Reyes's on-call rendering both source from a single
JSON file committed in the repo: `.squad/agents/skinner/icm-latest.json`.
No CI auth required for either the ICM section or the On-Call Today table.

## Pattern

1. **Out-of-band pull (Saloni's laptop):** `tools/icm/refresh-local.sh` wraps
   `python -m tools.icm.icm_collector --team-id 106961` and writes the result
   to `.squad/agents/skinner/icm-latest.json`. Interactive Entra auth happens
   exactly once here, cached for ~24h.
2. **Commit + push:** Saloni commits the JSON. CI/local readers pick it up
   automatically.
3. **Skinner producer:** Loads the file, applies a 48h freshness gate:
   - `<= 48h` → Status.GO with full Active ICM table + on-call metadata.
   - `> 48h` → Status.PARTIAL with explicit stale callout.
   - Missing → Status.PARTIAL with carry-forward stub.
   - `REPORT_GENERATOR_SKIP_ICM=1` → Status.SKIP (explicit-skip hatch).
4. **Reyes assembler:** Resolves on-call via precedence chain:
   `ctx` → `sections['skinner_icm'].metadata['on_call']` → `.squad/config/on-call.yaml`
   (date-window) → `TBD`. The YAML is Saloni's hand-maintained fallback for
   OOF / mid-week rotation changes.

## Recommended cadence

- **JSON refresh:** 2-3x/week minimum (Mon / Wed / Fri). Cron/launchd preferred
  to avoid drift. ICM signal velocity on team 106961 is currently low
  (effective real-incident count = 0), so 48h is a comfortable gate.
- **YAML override:** Update only when (a) Saloni is OOF and won't refresh JSON,
  or (b) rotation changes mid-week without the ICM roster reflecting it yet.

## Files added/changed

- `tools/report_generator/sections/skinner_icm.py` — full rewrite, file-based.
- `tools/report_generator/assembler.py` — on-call precedence chain + YAML reader.
- `tools/report_generator/tests/test_assembler.py` — updated on-call test + new Skinner-metadata test.
- `.squad/config/on-call.yaml` — seed schedule (`TBD-update-me` sentinels).
- `tools/icm/refresh-local.sh` — Saloni's pull helper (executable).
- `.squad/agents/skinner/icm-latest.json` — seed snapshot of 06-08 pull.

## Verification

- Local dry-run: Skinner → GO, on-call → `dileepkusuma` / `samirnen`.
- `pytest tools/report_generator/` → 45 passed (1 pre-existing failure deselected: validation invariant-2 on prior 06-10 report, unrelated).

## Open follow-up (not in this PR)

The workflow currently hardcodes `REPORT_GENERATOR_SKIP_ICM: "1"` at
`.github/workflows/daily-livesite-report.yml:104`. To activate file-based ICM
in CI, drop that env var in a separate workflow-scoped PR. Kept out of this
PR because the workflow file requires GitHub Actions auth scope that the
current push token lacks.

## Track 3 Option A status

Still deferred per Mulder plan. File the ICM team 106961 SP request when daily
ICM refresh becomes necessary (currently 2-3x/week is sufficient).
