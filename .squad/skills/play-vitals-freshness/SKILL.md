# Play Vitals — Per-Metric Freshness Window (team-local skill note)

**Owner:** Frohike
**Created:** 2026-06-10
**Status:** Team-local extension of the canonical skill at
`WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`.
Promote upstream when that repo's workflow allows.

---

## The rule

Any call into `playdeveloperreporting.googleapis.com/v1beta1` that carries a
`timelineSpec` must clamp `endTime` to at most
`today - freshness_offset(metricSet)`. Asking for `endTime = today` returns
HTTP 400 INVALID_ARGUMENT:

```
'timeline_spec.end_date' field should be at most the current freshness <YYYY-MM-DD> 00:00
```

Each MetricSet has its own DAILY lag. Empirical floor on 2026-06-10:

| MetricSet | DAILY freshness offset (days) |
|---|---:|
| `crashRateMetricSet` | 1 |
| `anrRateMetricSet` | 1 |
| `errorCountMetricSet` | 1 |
| (unknown) | 2 (safe fallback) |

Other MetricSets (`slowStartRateMetricSet`, `excessiveWakeupRateMetricSet`,
`stuckBackgroundWakelockRateMetricSet`, `lmkRateMetricSet`) historically lag
1–3 days depending on Play infra weather. Always verify before trusting.

## How to read freshness live

Two options:

1. **Per-MetricSet GET (authoritative):** call `.get()` on the resource and
   read `freshnessInfo[].latestEndTime` for the granularity you intend to
   query. The discovery doc exposes one `.get()` per MetricSet under the same
   nested path used for `.query()`.
2. **MCP shortcut:** `mcp_google-play-r_get_metric_freshness()` returns a
   matrix of every MetricSet × granularity with its latest available date.
   Cheaper than calling `.get()` on each MetricSet individually.

Use the live value as `max(static_offset, today - latestEndTime)` — the
static offset is a floor, never a ceiling.

## Preserve window length when clamping

When `endTime` is shifted back by N days, shift `startTime` back by the same
N days. The daily report still gets a 7-day rolling window; it just ends
N days earlier than the calendar date the operator passed on the CLI. This
keeps `current_7d_window` and `prior_7d_window` comparable shapes.

## What to surface in the raw artifact

Whatever your `pull_all` (or equivalent) returns to downstream readers, embed
the per-metric offset used so consumers can tell whether they're looking at
`[today-7d, today-1d]` data or `[today-9d, today-3d]` data. In Frohike's
pipeline this lives in `raw["window"]["freshness_offset_days"]`.

## Implementation reference

Production code shipping this pattern (single chokepoint per call site):

- `tools/report_generator/sections/frohike_play_vitals.py`
  - `PlayVitalsClient._METRIC_FRESHNESS_OFFSET_DAYS` — the table
  - `_clamp_window_for_freshness(start, end, metric_set, today=None)` — helper
  - Applied inside `_rate_by_version`, `_rate_by_country`, `_error_counts`
- Tests asserting per-metric offset and window-length preservation:
  `tools/report_generator/sections/tests/test_frohike_play_vitals.py`

## Anti-patterns to avoid

- ❌ Hard-coding `endTime = report_date` from CLI input. Breaks the day the
  operator runs same-day as the report.
- ❌ One global offset across all MetricSets. Hides per-MetricSet drift; the
  next MetricSet to extend its lag silently corrupts the others' windows.
- ❌ Clamping `endTime` without shifting `startTime`. Quietly shrinks the
  reporting window and skews 7d/28d aggregates.
- ❌ Relying on `mcp_google-play-r_get_metric_freshness` alone without a
  static fallback. MCP outages and discovery-doc churn would take the section
  to FAIL with no useful data.
