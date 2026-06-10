# Architecture: Daily Livesite Report Generator CLI

**By:** Mulder (Lead) · **Date:** 2026-06-10 · **Status:** PROPOSED → ready for Doggett to implement
**Consumers:** Doggett (orchestrator), Reyes (assembler), Frohike, Langly, Scully, Skinner (producers)
**Replaces:** the placeholder `Generate daily livesite report` step in `.github/workflows/daily-livesite-report.yml`

---

## 0. Goal (one sentence)

Produce, idempotently and non-interactively under GitHub Actions cron `0 14 * * 1-5`, the file
`daily-livesite-report-android-{YYYY-MM-DD}.md` at repo root, structurally identical to the
2026-06-10 manual report, with fail-soft per-section semantics so a single producer outage never
blocks the report.

---

## 1. CLI entry point & invocation contract

**Location:** `tools/report_generator/cli.py` — invoked as a module so package imports work:
`python -m tools.report_generator --date 2026-06-10` (with `__main__.py` re-exporting `cli.main`).

### Flags

| Flag | Type | Default | Purpose |
|---|---|---|---|
| `--date YYYY-MM-DD` | str | today UTC | Report date. Single source of truth threaded into every producer's `ctx`. |
| `--output PATH` | path | `daily-livesite-report-android-{date}.md` (repo root) | Final assembled markdown path. |
| `--runs-dir PATH` | path | `tools/report_generator/runs/{date}/` | Where per-section drops, raw JSON, and logs go. |
| `--skip-sections CSV` | str | `""` | Comma-separated section IDs to skip (e.g. `skinner_icm,frohike_play_vitals`). |
| `--only-sections CSV` | str | `""` | Inverse of `--skip-sections`; mutually exclusive. Useful for local dev. |
| `--dry-run` | flag | false | Run all producers, write drops, but DO NOT write the final assembled file. |
| `--validate` | flag | false | After assembly, run the §8 validation hook; nonzero exit if it fails. |
| `--no-validate` | flag | false | Skip §8 validation (CI default is to validate; this is for emergencies). |
| `--fail-fast` | flag | false | Override fail-soft and exit 2 on first producer FAIL. Off in CI. |
| `--log-level {DEBUG,INFO,WARN,ERROR}` | str | INFO | Stderr log level. |

### Exit codes

| Code | Meaning | Workflow reaction |
|---|---|---|
| 0 | Report assembled. May contain PARTIAL/SKIP sections (this is success per fail-soft). | Continue to Teams post + commit. |
| 1 | Assembly failed (Reyes raised, file not produced, validation failed in `--validate` mode). | Workflow fails; no Teams post. |
| 2 | `--fail-fast` tripped on a producer FAIL. | Workflow fails. |
| 3 | Invalid CLI args / config (bad date, mutually exclusive flags, missing config.json). | Workflow fails before any producer runs. |

### Workflow invocation (replaces the `Generate daily livesite report` step)

```yaml
- name: Generate daily livesite report
  env:
    PLAY_CONSOLE_SA_KEY: ${{ secrets.PLAY_CONSOLE_SA_KEY }}
    KUSTO_AAD_SP_CLIENT_ID: ${{ secrets.KUSTO_AAD_SP_CLIENT_ID }}
    KUSTO_AAD_SP_CLIENT_SECRET: ${{ secrets.KUSTO_AAD_SP_CLIENT_SECRET }}
    KUSTO_AAD_TENANT_ID: ${{ secrets.KUSTO_AAD_TENANT_ID }}
    REPORT_GENERATOR_SKIP_ICM: "1"   # see §4
  run: |
    python -m tools.report_generator \
      --date "${{ steps.date.outputs.date }}" \
      --validate
    echo "REPORT_FILE=daily-livesite-report-android-${{ steps.date.outputs.date }}.md" >> $GITHUB_ENV
```

### Idempotency

* Running twice on the same `--date` produces byte-identical output **only if** upstream data is
  identical. The CLI does not cache results between runs; instead, each producer is responsible
  for re-fetching. The point of "idempotent" here is **safe to re-run** (no destructive side
  effects, no duplicate commits beyond git's own dedup), not "deterministic across time".
* The output file is **overwritten** on each run. If `daily-livesite-report-android-{date}.md`
  already exists, the CLI replaces it. (Git's `--cached --quiet` check in the workflow already
  no-ops a commit when nothing changed.)
* `tools/report_generator/runs/{date}/` is overwritten on each run (per-date dir is wiped at
  start, then re-populated). Doggett: implement as `shutil.rmtree(..., ignore_errors=True)`
  followed by `mkdir(parents=True, exist_ok=True)`.

---

## 2. Section-producer contract

Every producer module exposes exactly one public function:

```python
def produce(date: str, ctx: dict) -> SectionResult: ...
```

### `SectionResult` (in `contracts.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Status(str, Enum):
    GO = "GO"           # full data, ready to publish
    PARTIAL = "PARTIAL" # produced output but data is incomplete (e.g. ICM unauth, page_size capped)
    SKIP = "SKIP"       # producer deliberately skipped (--skip-sections, env flag, no-op date)
    FAIL = "FAIL"       # producer raised or returned no usable markdown

class Section(str, Enum):
    LANGLY_VERSION         = "langly_version"
    SCULLY_SERVER          = "scully_server_telemetry"
    FROHIKE_PLAY_VITALS    = "frohike_play_vitals"
    SKINNER_ICM            = "skinner_icm"

@dataclass
class SectionResult:
    section: Section
    status: Status
    markdown: str                       # the rendered section body (may include H2/H3). Empty on SKIP/FAIL.
    metadata: dict[str, Any] = field(default_factory=dict)  # cross-section facts (e.g. live_play_version)
    denominators: dict[str, Any] = field(default_factory=dict)  # for the assembler's framing rules
    errors: list[str] = field(default_factory=list)         # human-readable; surfaced in report footer
    drop_path: str | None = None        # path to the producer's own drop file
    elapsed_s: float = 0.0
```

### `ctx` dict (passed in)

```python
{
    "date": "2026-06-10",               # canonical report date (UTC)
    "runs_dir": Path("tools/report_generator/runs/2026-06-10/"),
    "config": <config.py module>,       # paths, thresholds, constants
    "prior_results": {                  # results of producers that already ran (see §5 ordering)
        Section.LANGLY_VERSION: SectionResult(...),
        ...
    },
    "log": <logging.Logger>,            # child logger named after the section
}
```

Producers consume `prior_results` to enforce cross-section framing rules — e.g. Frohike's table
flags rows where `version == ctx["prior_results"][LANGLY_VERSION].metadata["live_play_version"]`
as ✅ LIVE PROD, and rows where `version` matches the `.04xx` pattern as 🔴 INTERNAL RING.

### Producer contract rules (Doggett, enforce these in tests)

1. **Pure-ish:** Producers MUST NOT mutate the filesystem outside `ctx["runs_dir"]` and their own
   `.squad/agents/{name}/research/` drop file (existing convention — keep it).
2. **Fail-soft:** Producers MUST catch their own exceptions and return `Status.FAIL` with errors
   populated. They MUST NOT raise out. The orchestrator only catches as a last-resort backstop.
3. **Standalone-runnable:** Each producer module ships its own `__main__` block so
   `python -m tools.report_generator.sections.frohike_play_vitals --date 2026-06-10` works.
   This is non-negotiable — it's how Frohike/Langly/Scully test their own work without spinning
   the orchestrator.
4. **Drop file is mandatory:** Every producer (regardless of GO/PARTIAL) writes
   `.squad/agents/{name}/research/{drop-template}-{date}.md`. On FAIL, the producer still writes
   a stub drop noting the failure — this is the human-debuggable record.
5. **Markdown shape:** Producers return rendered markdown for **their section only** (no H1, no
   report-level scaffolding). The assembler stitches sections under H2/H3 in the order defined by
   the template.
6. **Timeouts:** Each producer must honor `ctx["config"].SECTION_TIMEOUT_S` (default 300s per
   section). If exceeded, the orchestrator cancels and records FAIL — this is the one place
   the orchestrator force-terminates a producer.

---

## 3. Module layout — CONFIRMED with minor adjustments

```
tools/report_generator/
  __init__.py
  __main__.py                          # re-exports cli.main so `python -m tools.report_generator` works
  cli.py                               # arg parse, orchestration entry, exit-code mapping
  contracts.py                         # SectionResult, Section, Status, exceptions
  config.py                            # paths, thresholds, NAAS_PREDICATE_TERMS, .04xx pattern, version regex
  orchestrator.py                      # NEW — wave/dependency execution; cli.py stays thin
  assembler.py                         # Reyes — final markdown assembly + cross-section framing
  validators.py                        # NEW — §8 validation hook (Doggett owns; Mulder reviews)
  sections/
    __init__.py
    langly_version.py                  # Langly
    scully_server_telemetry.py         # Scully
    frohike_play_vitals.py             # Frohike
    skinner_icm.py                     # Skinner (PARTIAL in CI per §4)
  runs/                                # gitignored — see §6
  tests/                               # producer contract tests (per producer + assembler smoke)
```

### Revisions vs. the proposed layout in the task

1. **Added `orchestrator.py`** — separates "run waves, collect results, handle timeouts" from
   "parse args, set up logging, map to exit code". Keeps `cli.py` <150 lines and lets Doggett
   unit-test orchestration without arg-parse plumbing.
2. **Added `__main__.py`** — single-line file. Lets us drop the `cli.py` suffix from invocations
   in CI.
3. **Added `validators.py`** — §8 deserves its own module (header + summary + table + size checks
   are non-trivial regex/AST work).
4. **`runs/` is gitignored.** The drop files under `.squad/agents/{name}/research/` are the
   committed artifacts; `runs/` is ephemeral build output.

Everything else from the task's proposed layout stands.

---

## 4. Non-interactive auth strategy

**Decision: (c) graceful skip via env var for ICM in CI today; (b) WIF + service principal as a
follow-up issue for Kusto/Play Console.** Justification + per-producer secrets below.

### Why (c) for ICM and not (a) or (b)

* `tools/icm/icm_collector.py` is explicit (line 8–16): the only working backend is `agency mcp
  icm` over interactive Entra. The CLI's app registration is private and a service-principal
  workaround was already attempted and abandoned (per the file's own D-131-final note).
* (a) "skip ICM in CI" is functionally what we want, but hardcoding the skip removes the ability
  for a future agency-CLI service-principal path to flip on — bad design.
* (b) "require WIF + SP as a follow-up" is correct for Kusto and Play, but for ICM the SP path
  doesn't exist upstream — we cannot block daily reporting on something not in our control.
* (c) `REPORT_GENERATOR_SKIP_ICM=1` env var → `skinner_icm.produce()` short-circuits with
  `Status.PARTIAL`, markdown = "ICM data not refreshed in this run (CI auth limitation). Last
  manual pull: {date_of_last_drop}." This matches the existing 06-10 report's "weekly cadence /
  no movement in 24h" framing — minimal narrative disruption.

### Follow-up issues (Saloni to file or delegate)

1. **WIF + service principal for Kusto** — `wdgvsoprod.westus.kusto.windows.net`. Needs a SP with
   `Database Viewer` on `NaasProd`. Owner: TBD (see §10 open question 2).
2. **Play Console service account JSON key** — `PLAY_CONSOLE_SA_KEY` as a single base64-encoded
   secret. Owner: Frohike to spec; Saloni to grant. The Play Developer API supports SA auth
   natively, so this is the easy one.
3. **ICM SP path** — track upstream `InE.IcmAutomation` for any non-interactive flow; until
   then, ICM section runs weekly via Scully's manual cadence (already established in
   `.squad/decisions.md` 2026-06-10 entry).

### Required GitHub Action secrets (declare these in workflow `env:`)

| Secret | Used by | Required? | Skip behavior if missing |
|---|---|---|---|
| `PLAY_CONSOLE_SA_KEY` | Frohike, Langly | YES for both | Producer returns PARTIAL with "auth not configured" error; assembler renders skeleton. |
| `KUSTO_AAD_SP_CLIENT_ID` | Scully | YES | Producer returns PARTIAL; carries forward prior-day Scully drop with explicit "reused" framing. |
| `KUSTO_AAD_SP_CLIENT_SECRET` | Scully | YES | Same as above. |
| `KUSTO_AAD_TENANT_ID` | Scully | YES | Same as above. |
| `REPORT_GENERATOR_SKIP_ICM` | Skinner | optional, default `1` in CI | When `1`, Skinner returns PARTIAL immediately (no auth attempted). |
| `MOBILE_LIVESITE_TEAMS_WEBHOOK` | workflow only (not the CLI) | already specced in workflow | unchanged. |

The CLI never reads these directly — each producer reads only the env vars it needs. Document
them in `tools/report_generator/README.md` (Doggett to create after Mulder review).

---

## 5. Execution order & dependency graph — CONFIRMED with concrete waves

**Wave model (3 waves, mixed serial/parallel):**

```
Wave 1 (serial):  Langly  →  publishes live_play_version, release_date, rollout_caveat
                            into ctx["prior_results"][LANGLY_VERSION].metadata.

Wave 2 (parallel, concurrent.futures.ThreadPoolExecutor, max_workers=3):
                  Scully  ┐
                  Frohike ┤  read Langly's metadata to apply framing rules
                  Skinner ┘  (SKIP in CI per §4 — runs instantly)

Wave 3 (serial):  Reyes (assembler)  →  consumes all four SectionResults +
                                       cross-section metadata; writes final .md.
```

### Why these waves (not pure dependency-graph)

* Langly **must** finish first — every other producer consults `live_play_version` for framing.
  This is a hard ordering constraint from the 2026-06-10 "lead-with-Play-Store-version"
  decision in `.squad/decisions.md`. ~5 second producer; cheap to serialize.
* Scully + Frohike + Skinner have **no inter-dependencies** in Wave 2. ThreadPoolExecutor (not
  ProcessPoolExecutor) is fine because all three are I/O-bound (HTTP/Kusto), not CPU-bound, and
  threads share the imported config module cleanly.
* Reyes is the only Wave 3 producer; runs serial; consumes everything.

### Concurrency choice — confirmed: `concurrent.futures.ThreadPoolExecutor`

* Stdlib only (constraint).
* I/O-bound work (HTTP + Kusto query + Play Developer API) — GIL is not a blocker.
* Easy per-future timeout via `future.result(timeout=SECTION_TIMEOUT_S)`.
* Easy fail-soft — exceptions are captured in the future and reported, not raised through.

### Anti-decision: do not use `asyncio`

* Producers will be implemented by four different agents over multiple cycles. Sync code is
  easier to standalone-run (constraint) and to debug. The marginal latency win of asyncio
  doesn't justify the contract complexity.

---

## 6. Output file convention — CONFIRMED

| Path | Contents | Committed? |
|---|---|---|
| `daily-livesite-report-android-{date}.md` (repo root) | Final assembled report. **Exact filename the workflow expects.** | YES — Teams post + git commit in workflow. |
| `tools/report_generator/runs/{date}/` | Per-section JSON dumps, raw API responses, orchestrator log, per-producer stderr captures. | NO — gitignored. Ephemeral. |
| `tools/report_generator/runs/{date}/manifest.json` | Map of `Section → SectionResult` (as JSON), elapsed times, error lists. | NO — but inspectable in workflow logs on failure. |
| `.squad/agents/{name}/research/{drop-template}-{date}.md` | Producer's own drop file (existing convention). | YES — committed by Scribe / squad workflow, NOT this CLI. |

### Add to `.gitignore`

```
tools/report_generator/runs/
```

(Doggett: confirm or migrate to existing `.gitignore` pattern.)

---

## 7. Failure semantics — precise

**Principle: the report ALWAYS produces.** A single missing section never blocks Wave 3.

### Per-producer failure handling (the orchestrator's perspective)

| Producer fails | Wave 2 effect | Wave 3 (Reyes) effect | Final report |
|---|---|---|---|
| Langly FAIL | Wave 2 still runs; producers get `live_play_version = None` in ctx | Reyes renders header as `📱 Defender for Android — Live on Play Store: ⚠️ version pull failed ({date}). _Source: Langly._` and continues. | Published; header degraded; banner in Exec Summary noting Langly failure. |
| Scully FAIL | Independent of others | Reyes renders Scully's section header + a "⚠️ Server-side telemetry unavailable today. Last successful pull: {date_of_last_drop}." + carries forward the prior `.squad/agents/scully/research/naas-7d-report-data-*.md` (most recent) with explicit "reused" framing. | Published with PARTIAL Scully. |
| Frohike FAIL | Independent of others | Same pattern: Frohike's H2 section + "⚠️ Play Vitals pull failed: {first error}." Per-version table omitted; downstream cross-domain correlation section notes "Frohike data unavailable for this cycle." | Published with PARTIAL Frohike. |
| Skinner PARTIAL (CI-expected) | Independent | Reyes renders ICM section with "_ICM data not refreshed (CI auth limitation). Last pull: {date}._" — exact pattern from 06-10 report. | Published; ICM PARTIAL marked as expected, not failure. |
| Reyes FAIL | n/a | n/a | Exit code 1; no file written; workflow fails. **This is the only producer whose failure fails the whole run.** |

### Banner conventions (Reyes implements; Mulder pre-approves)

* **Status banner above Exec Summary** if ANY section is PARTIAL/FAIL:
  `> ⚠️ **Generated with degraded inputs:** Scully (FAIL), Skinner (PARTIAL — CI). See Contributors footer for details.`
* **Contributors footer** lists per-producer status with one-line error excerpt.

### Producer-level retries

* HTTP producers (Langly, Frohike) MUST implement: 3 retries, exponential backoff (1s/2s/4s),
  retry only on 5xx and connection errors. Spec in `contracts.py` as a `retry()` helper or
  documented expectation — Doggett's call.
* Kusto producer (Scully): single retry on transient `429`/`503`; no retry on auth failure.
* No retries on the CLI/orchestrator level — retries are a producer concern.

---

## 8. Validation hook (`--validate`)

Implemented in `validators.py`. Runs against the assembled file AFTER Reyes writes. On failure
in `--validate` mode, exit code 1 (workflow fails). In non-validate mode, prints warnings to
stderr and exits 0.

### Asserted invariants

1. **File exists** at `--output` path.
2. **File size between 5,000 and 30,000 bytes.** (The 06-10 manual report is 25,489 bytes; 06-09
   is 19,428 bytes; 06-05 is 14,495 bytes. 5–30KB band accommodates both partial-section days
   and full-fusion days.) Outside the band → fail.
3. **Required H1 present:** matches `^# .*[Dd]aily [Ll]ivesite [Rr]eport`.
4. **Langly version header present:** matches `📱 \*\*Defender for Android — Live on Play Store`
   within the first 5 non-empty lines. **This is the hard structural rule from the 2026-06-10
   "lead-with-Play-Store-version" decision.**
5. **Executive Summary heading present:** matches `^## Executive Summary`.
6. **At least one metric table present:** at least one markdown table (regex `^\|.*\|.*\|$` on
   3+ consecutive lines) inside an H2 named "Key Metrics" or starting with "📊"/"### Server-side"
   /"### Client-side".
7. **Contributors footer present:** `^## Contributors` near EOF.
8. **No raw Jinja/format-string leakage:** no occurrences of `{date}`, `{TBD`, `{{`, `}}` in the
   final markdown.
9. **No /Users/ paths leaked:** grep for `/Users/` → fail. (Constraint: no hardcoded
   `/Users/salonijain`.)

Validation results are written to `tools/report_generator/runs/{date}/validation.json` for
post-run inspection.

---

## 9. Backwards compatibility — the format is fixed

**Reyes does NOT redesign.** The 2026-06-10 report (`daily-livesite-report-android-2026-06-10.md`)
is the visual template, with 06-09 as the "shape stability" reference. The contract above is
specifically designed so Reyes can produce output that LOOKS like 06-10:

* Each producer returns markdown for its section in the **shape** of the 06-10 corresponding
  section. The assembler stitches in this fixed order:

```
# 📋 GSA Android Daily Livesite Report — {Weekday Mon DD, YYYY}
{Langly header line — H1-adjacent, NOT H2}
{Scope blockquote}
{Headline reframe blockquote}
## 📟 On-Call Today      ← from Skinner (or carried forward in CI)
## Executive Summary     ← assembled by Reyes from each producer's "exec_summary_bullets" metadata
## Key Metrics
  ### Server-side ...    ← Scully
  ### Client-side ...    ← Frohike
## 🆕 NAAS Client Stability (Google Play Vitals)   ← Frohike (full body)
## 🔍 Top Insights       ← Reyes (merges producers' insights metadata)
## 🔥 Cross-Domain Correlation   ← Reyes (depends on Scully + Frohike metadata)
## ICM Snapshot          ← Skinner
## Contributors          ← Reyes auto-generates from SectionResults
```

* **Metadata-passing for cross-section framing:** Each producer's `metadata` dict contributes
  named keys the assembler knows about. Documented in `contracts.py` as a typed dict (Doggett:
  use `TypedDict`):
  * `langly_version.metadata`: `live_play_version`, `release_date`, `rollout_caveat`
  * `scully_server.metadata`: `headline_findings: list[dict]`, `top_insights: list[dict]`,
    `denominators: dict`, `pull_window: tuple[str,str]`
  * `frohike_play_vitals.metadata`: `headline_findings`, `top_insights`, `per_version_table`,
    `naas_event_counts`, `subsystem_breakdown`
  * `skinner_icm.metadata`: `oncall_primary`, `oncall_backup`, `bucket_counts`, `pull_date`

* **Framing rules carried into the assembler** (from `.squad/decisions.md`):
  1. `.04xx` ring versions (regex `^\d+\.\d+\.\d+\.04\d{2}$` or last-segment `04xx`) → tag
     🔴 **(.04xx INTERNAL RING)** and downgrade severity.
  2. Versions matching `live_play_version` → tag ✅ **LIVE PROD**.
  3. NAAS Play Vitals output is **always** NAAS-as-a-unit, never Defender-filtered-to-NAAS.
  4. Per-Defender-version table is **primary**, not appendix.

Reyes does NOT introduce new sections without an updated decision file. The contract is closed
to the 06-10 shape until a new template decision lands.

---

## 10. Open questions for Saloni (BEFORE Doggett implements)

1. **Runner: GitHub-hosted `ubuntu-latest` (current workflow) vs Microsoft self-hosted?**
   Self-hosted is preferable for (a) Kusto network reachability to `wdgvsoprod.westus.kusto.windows.net`
   (corp endpoint — may not be reachable from `ubuntu-latest`'s IP range), and (b) easier WIF
   federation with the corp AAD tenant. Hosted is simpler to bootstrap. Mulder's lean:
   **self-hosted**, but need Saloni's call because it affects who owns the runner pool.

2. **WIF / Kusto SP onboarding — who owns provisioning?**
   Creating an Entra SP + granting `Database Viewer` on `NaasProd` requires someone with subscription
   `fb633419-6bb2-4a7e-8993-fd9456d19c4c` admin. Is that Saloni, or do we file a request through
   the GSA team? Blocks Scully producer running in CI; without it, every cron run is PARTIAL on
   server telemetry.

3. **Auto-commit policy:** the workflow's `Commit report to repository` step currently auto-pushes
   from `github-actions[bot]`. The 2026-06-10 Doggett decision entry flags this as "TODO: confirm
   whether auto-commit is desired or if manual commit (via Scribe) is preferred." This affects
   the CLI's idempotency story — if Scribe owns commits, the CLI should NOT touch `git`. Mulder's
   lean: **Scribe owns commits**, CLI never invokes git. Confirm.

4. **ICM weekly-cadence formalization:** is "weekly Skinner pull, daily CI carries-forward with
   timestamp" the official cadence? It's been the de-facto pattern for 3 reports running. If yes,
   we lock it into `config.py` (e.g. `ICM_REFRESH_DAY = "MON"`); if no, we need the SP workaround
   prioritized. Mulder's lean: **formalize as weekly Monday refresh**, document in next cycle's
   decision merge.

---

## Acceptance criteria for Doggett's implementation PR

* `python -m tools.report_generator --date 2026-06-10 --dry-run` runs locally with mocked
  producers and writes a manifest.
* All four producer modules have a `__main__` stub that exits 0 with stub output (real fetchers
  land in subsequent PRs by Frohike/Langly/Scully/Skinner).
* `validators.py` runs against the existing `daily-livesite-report-android-2026-06-10.md` and
  passes all 9 invariants. (This is the regression bar — if the template passes validation, the
  CLI's output for the same date must too.)
* Exit-code matrix from §1 has unit tests.
* No `/Users/` paths in any committed file. All paths repo-relative via `pathlib.Path(__file__)`
  resolution or repo-root detection.
* GitHub Actions workflow updated to invoke per §1, with the four secrets declared (even if
  unset — graceful skip is tested).

---

## Mulder's review checkpoints (before this merges past `inbox/`)

1. Reyes ack: assembler shape + metadata contract is implementable from §9.
2. Frohike ack: §2 contract + §4 secret + drop-file path matches their existing workflow.
3. Langly ack: §5 Wave 1 serialization + §9 metadata keys are sufficient.
4. Scully ack: §4 SP-auth path is acceptable as the CI plan; §7 carry-forward semantics on FAIL
   are correct.
5. Doggett ack: implementable in one PR cycle; flag any §10 question blocking implementation.
