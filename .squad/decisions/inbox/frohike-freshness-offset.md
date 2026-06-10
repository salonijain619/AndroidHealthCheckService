# Decision: Per-metric freshness offset for Play Reporting v1beta1 timeline queries

**By:** Frohike (Play Vitals Analyst)
**Date:** 2026-06-10
**Status:** PROPOSED — pending Mulder ack

## What

Every `timelineSpec`-bearing call into `playdeveloperreporting.googleapis.com/v1beta1`
MUST clamp `endTime` to at most `today - freshness_offset(metricSet)` and shift
`startTime` back by the same delta to preserve the window length. The offset is
per-MetricSet (different MetricSets materialize on different lags) and lives in
a small constant table inside `PlayVitalsClient` so it can be raised individually
without touching call sites.

Initial table (from empirical 2026-06-10 freshness):

| MetricSet | DAILY offset (days) |
|---|---:|
| `crashRateMetricSet` | 1 |
| `anrRateMetricSet` | 1 |
| `errorCountMetricSet` | 1 |
| (unknown / fallback) | 2 |

Unknown MetricSets fall back to **2 days** — a safe upper bound that matches the
worst-case lag we've observed across DAILY MetricSets in v1beta1.

## Why

Without clamping, the section pipeline produces HTTP 400 INVALID_ARGUMENT
("'timeline_spec.end_date' field should be at most the current freshness
2026-06-09 00:00") whenever the operator runs `--date $(today)` — which is the
default in the daily report pipeline. Yesterday's run worked only by accident
because the pipeline launched after Play had materialized that day's timeline.

This is a structural contract of the Play Reporting API, not a one-off bug:
every future MetricSet we wire in (slow-start, wakeup, LMK, etc.) has its own
freshness lag. A central, per-metric clamp is the only way to keep
section call sites freshness-blind.

## Operational rules

1. **Single chokepoint:** All `timelineSpec` query bodies in
   `frohike_play_vitals.py` go through `_clamp_window_for_freshness(start, end, metric_set)`
   before being sent. New MetricSets added to `_METRIC_RESOURCE_PATH` must also
   be added to `_METRIC_FRESHNESS_OFFSET_DAYS`.
2. **Window length is preserved:** Clamping shifts `start` back by the same
   number of days `end` was shifted. The 7-day rolling window stays 7 days
   long, just ending earlier.
3. **Surfaced in raw output:** The `pull_all()` response's `window` dict now
   carries `freshness_offset_days` per MetricSet so downstream consumers can
   tell whether the data they're looking at ends on `today-1` or `today-3`.
4. **Static offsets are a floor, not a ceiling:** If a MetricSet's
   live `freshnessInfo` advertises a longer lag (Play outage, infra change),
   future work should call `.get()` on the MetricSet and use
   `max(static_offset, today - latestEndTime)`. Out of scope for this fix.

## Risks

- **Stale data drift:** A 1-day clamp means the daily report's "current" window
  ends one day before the report date. The Δ-vs-prior-7d comparison is now
  `[today-8d, today-1d]` vs `[today-15d, today-8d]`, not
  `[today-7d, today]` vs `[today-14d, today-7d]`. Operationally fine — Play
  data is already aggregated end-of-day so the latest day is rarely
  representative anyway — but worth calling out in the narrative if Reyes
  ever wants to claim "as of today" precision.
- **MetricSets with longer lag will silently fall back to the 2-day default.**
  If we wire in `slowStartRateMetricSet` (T-2) without updating the table, the
  fallback handles it but we lose the explicit signal. Mitigation: PR template
  reminder.

## Not deciding

- Whether to fetch live `freshnessInfo` per request. Static offsets ship now;
  live freshness is a follow-up if we see drift.
- Whether `errorCountMetricSet` should use a 0-day offset to maximize recency.
  Conservative 1-day floor for now; revisit if narrative needs the extra day.

## Asks

- **Mulder:** ack the per-metric-offset pattern so future MetricSets follow it
  without re-litigating.
- **Reyes:** no action required — section continues to expose markdown
  identical in shape to the 06-10 template; only the underlying window is
  shifted one day earlier.
