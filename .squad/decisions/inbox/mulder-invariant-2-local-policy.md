# Decision: Invariant-2 policy for local-runner v1

**By:** Mulder (Lead)
**Date:** 2026-06-10
**Status:** PROPOSED — ready for Reyes implementation
**Supersedes/depends-on:** `mulder-local-first-v1.md` (v1 architecture framing)
**Implementer:** **Reyes** (owns `tools/local-runner/`)
**Reviewer (final ack):** Saloni

---

## Context

First fire of `./tools/local-runner/run-daily.sh` on 2026-06-10:

| Producer | Status | Notes |
|---|---|---|
| Langly | PARTIAL | rollout-% needs Play Console (known) |
| Scully | SKIP | no local Kusto SP (deferred to v2 per v1 decision) |
| Skinner | **GO** | file-based ICM working — 2 active incidents (1× Sev25 RCE, 1× Sev3) pulled |
| Frohike | PARTIAL | env-var bug; Reyes fixing in parallel |
| Assembler | OK | 2481-byte report written |
| Validation | **FAIL** | `invariant-2: file size 2481 bytes outside [5000, 30000]` |

`set -euo pipefail` in `run-daily.sh` + CLI returning exit 1 on validation failure means the Teams post never fires. Same blocker that killed yesterday's CI run.

I read the 2481-byte report. It contains: H1, Langly version header (with rollout caveat), On-Call table (Primary `dileepkusuma` / Backup `samirnen`), **a real ICM table with an active Sev25 ITD RemoteCodeExecution incident on the GSA Client and a Sev3 customer-reported incident**, Contributors, and a Run Diagnostics matrix that surfaces exactly which producers degraded and why. **This is useful to post.** The on-call rotation + the Sev25 active ICM are signal Saloni and the on-call want today — withholding them because the byte-count floor was calibrated against a 4-section fully-healthy report is the wrong default.

---

## Decision

**Adopt Option C, scoped to local-runner only. CI stays strict.**

Concretely:

1. **`tools/local-runner/run-daily.sh` invokes the generator with `--no-fail-on-validation`.** The flag already exists in `tools/report_generator/cli.py` (added by Doggett during initial build). This is a one-line change. Validation still runs, `validation.json` still gets written into `tools/report_generator/runs/{date}/`, every failure still logs at ERROR level — but exit code is 0, so the Teams post proceeds.

2. **The runner shell script then echoes a banner whenever validation reported failures**, so Saloni sees in the terminal that the report shipped *degraded*. Example:
   ```
   ⚠️  Report posted to Teams BUT validation reported 1 failure(s).
       See: tools/report_generator/runs/2026-06-10/validation.json
   ```
   This preserves the "loud about degradation" property without blocking delivery.

3. **CI workflow is NOT changed.** GitHub Actions continues to call the CLI without `--no-fail-on-validation`, so a CI-mode regression that drops a section below the 5KB floor still fails the build. CI runs in the "fully healthy" world (all SPs wired), so the floor is appropriate there.

4. **The pre-existing failing unit test `test_validation_passes_on_2026_06_10_report`** is the same root cause. The test asserts the 06-10 report passes all 9 invariants, but the 06-10 report was generated in local-degraded mode (no Kusto SP, Frohike env-var bug). Fix: relax the regression-anchor test to assert "no failures OTHER than `invariant-2`" for this specific degraded sample. A second regression test using a synthetic fully-healthy report (≥5KB) keeps invariant-2 covered. This is a Reyes-owned fix in the same PR.

## Why C and not the alternatives

- **(A) Lower the floor to 2000.** Rejected. The 5KB floor exists precisely to detect "we lost a whole section to a real bug." Dropping it to 2000 silently masks future regressions that drop, say, the entire Skinner ICM table — and on a day when the ICM table is the *only* live data we have, losing it silently is the worst possible failure mode.
- **(B) Status-aware skip — invariant-2 ignored when sections are SKIP/PARTIAL with known reasons.** Right in spirit but wrong on cost. Requires plumbing `SectionResult` statuses + "known reason" allow-listing into `validation.py`, which currently reads only the written file. "Known reason" classification is fuzzy and will rot. Defer to v3 if we ever need finer-grained gating.
- **(C) Skip invariant-2 in local mode, keep it in CI.** Chosen. Minimum code (one shell flag + one banner + one test relaxation). Matches the v1 "local is degraded but real" framing — local-runner *is* the degraded path by design; gating it on full-healthy invariants is a category error. CI still enforces full-healthy. The `--no-fail-on-validation` infrastructure already exists; we just turn it on for local.
- **(D) Post first, validate after — validation becomes diagnostic, not a gate.** Conceptually the cleanest framing and what I'd do at v2 (validation as observability, not policy). But to implement *today* it requires reordering run-daily.sh and partially defeating the safety net (e.g., a malformed report with H1 missing also slips through). C achieves D's posting-as-success-criterion with a smaller blast radius: validation still runs *before* post, just doesn't gate it. We get the same shipped-anyway behavior with one less moving part.

## Symmetric framing

This matches my v1 architectural call that local-runner is the degraded path: no Kusto SP, no Play Console SA, file-based ICM. By construction the report will sometimes be small. Local validation must therefore be **diagnostic-loud, gate-soft**. CI is the inverse: full SPs, full data — therefore **gate-strict**.

## Implementation checklist (for Reyes)

- [ ] `tools/local-runner/run-daily.sh`: add `--no-fail-on-validation` to the `python -m tools.report_generator.cli` invocation in step 3/4.
- [ ] After the generator call, read `tools/report_generator/runs/{date}/validation.json`; if `passed: false`, print a `⚠️ Report posted DEGRADED` banner with the failure list and the validation.json path before the step 4/4 Teams post.
- [ ] `tests/test_validation.py::test_validation_passes_on_2026_06_10_report`: change the assertion to `failures == [] or all(f.startswith("invariant-2:") for f in failures)` and add a docstring explaining why (local-degraded sample). File a v2 backlog todo to add a fully-healthy fixture report and assert strict-pass against *that*.
- [ ] Verify by re-running `./tools/local-runner/run-daily.sh` against today's date: report posts to Teams (or webhook stub), validation.json on disk shows the failure, banner appears in the terminal, exit code is 0.
- [ ] Smoke: run `pytest tools/report_generator/tests/test_validation.py` — must be green.

## Out-of-scope (triage carry-over from Frohike PR #3)

- **CLI `--only` flag.** Frohike's workaround (calling section modules directly with `python -m tools.report_generator.sections.frohike_play_vitals`) works fine for the iterate-on-one-section dev loop. **File as v2 backlog** — nice-to-have ergonomics, not blocking. Will pick up alongside `--fail-fast` (exit code 2 is reserved for it per CLI docstring).
- **The pre-existing failing test** — covered in the implementation checklist above; same root cause as this decision.

## Asks

- **Saloni:** ack option C. If you'd rather have D ("post first, validate after as pure diagnostic") for cleaner semantics, say so before Reyes starts — it's still a small PR, just a slightly different shape.
- **Reyes:** implement per the checklist; flag any surprise in the validation.json shape.
