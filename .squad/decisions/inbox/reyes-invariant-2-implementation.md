# Decision drop: Invariant-2 local policy — IMPLEMENTED

**By:** Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** SHIPPED
**Implements:** `.squad/decisions/inbox/mulder-invariant-2-local-policy.md` (Option C)
**Branch:** `reyes-invariant-2-local-policy`

---

## What landed

Per Mulder's checklist, three surgical changes:

1. **`tools/local-runner/run-daily.sh`** — added `--no-fail-on-validation`
   to the `python -m tools.report_generator.cli` invocation in step 3/4.
   Validation still runs; exit code stays 0 on failure so Teams post
   proceeds. Inline comment in the script points at Mulder's decision doc.

2. **`tools/local-runner/run-daily.sh`** — after the generator call, the
   runner reads `tools/report_generator/runs/{date}/validation.json` and,
   if `passed: false`, prints the canonical degraded banner BEFORE the
   Teams post (so it's not buried by a downstream curl failure):
   ```
   ⚠️  Report posted to Teams BUT validation reported N failure(s).
       See: tools/report_generator/runs/2026-06-10/validation.json
         - <each failure>
   ```
   Banner code path verified with synthesized failing validation.json.

3. **`tools/report_generator/tests/test_validation.py`** —
   `test_validation_passes_on_2026_06_10_report` assertion relaxed to:
   ```python
   assert failures == [] or all(f.startswith("invariant-2:") for f in failures)
   ```
   Docstring rewritten to explain the local-degraded-sample rationale and
   point at the v2 backlog item.

## Did NOT touch

- `.github/workflows/daily-livesite-report.yml` — CI stays strict per
  Mulder's framing (gate-strict CI, gate-soft local).
- `tools/report_generator/cli.py` — `--no-fail-on-validation` already
  existed (Doggett's earlier work); no change needed.
- `validators.py` — no shape change to `validation.json`; the banner
  reads the existing `{passed, failure_count, failures[]}` schema.

## Verification

- `pytest tools/report_generator/tests/test_validation.py` — 4/4 green.
- `./tools/local-runner/run-daily.sh --date 2026-06-10` end-to-end:
  preflight ✅, generator ran, report 5735 bytes (today actually passed
  all 9 invariants because Frohike's latest fix kept the report above
  5KB), Teams post returned **HTTP 202**, exit code 0. Banner code path
  verified separately by injecting a synthetic failing validation.json
  and exec'ing the banner block — output matched Mulder's spec line for
  line.

## Spawned backlog

- `.squad/decisions/inbox/reyes-v2-fully-healthy-fixture.md` — v2 work
  item to add a synthetic fully-healthy ≥5KB fixture and a strict-pass
  validation test against it, restoring full invariant-2 unit coverage
  that the 06-10 relaxation gave up.
