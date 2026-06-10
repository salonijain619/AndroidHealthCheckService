# v2 backlog: synthetic fully-healthy fixture + strict-pass validation test

**By:** Reyes (Report Writer)
**Date:** 2026-06-10
**Status:** BACKLOG (v2)
**Spawned from:** `mulder-invariant-2-local-policy.md` (Option C implementation)
**Owner (when picked up):** Reyes

---

## Context

Mulder's Option C (implemented 2026-06-10) relaxes
`test_validation_passes_on_2026_06_10_report` to tolerate `invariant-2:`
failures on the shipped 06-10 sample, because that report is a
local-degraded artifact (no Kusto SP, Frohike PARTIAL, file-based ICM).

This means the `[5000, 30000]` byte-floor invariant is currently NOT
covered by any green test against a real-shaped report. If the assembler
regresses and starts emitting 800-byte reports, this test alone won't
catch it.

CI exercises invariant-2 strictly via `cli.py` exit code, but that's an
integration path, not a unit assertion on validators.

## Backlog item

Add to `tools/report_generator/tests/fixtures/`:

- `fully-healthy-report.md` — synthetic markdown that satisfies all 9
  invariants. Hand-authored to ≥5KB, ≤30KB. Models a "Wave-2 fully
  green" output: Langly PASS, Scully GO, Frohike GO, Skinner GO,
  assembler clean. Realistic per-section sizes (Scully ≥1.5KB,
  Frohike ≥1.5KB, ICM table ≥0.5KB).

Add to `tools/report_generator/tests/test_validation.py`:

- `test_validation_strict_pass_on_fully_healthy_fixture` —
  `assert validate_report(FIXTURE) == []`. Non-tolerant. This is the
  test that proves invariant-2 (and every other invariant) actually
  enforces what we think it does.

## Why not now

Hand-authoring a 5KB markdown fixture that passes all 9 invariants
needs ~30 min of careful drafting (every section header, the version
header rule, server↔client framing, run-diagnostics table, exec-bullet
positions). Not blocking today's runner; Mulder's relaxation is
sufficient interim coverage. Pick up when next touching `validation.py`
or fixture-related work, or when invariant-2 changes.

## Acceptance

- [ ] `fully-healthy-report.md` fixture committed, ≥5KB.
- [ ] New strict-pass test green.
- [ ] Existing 06-10 tolerant test stays green (unchanged).
- [ ] Both tests run in same `pytest tools/report_generator/tests/test_validation.py` invocation.
