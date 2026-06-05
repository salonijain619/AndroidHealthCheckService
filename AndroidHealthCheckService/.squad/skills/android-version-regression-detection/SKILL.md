---
name: android-version-regression-detection
description: Detect a regression introduced in a specific Android GSA client version (the Android analog of the Windows v2.28.96 playbook). Combines ClientVersion pivoting, the ECS feature-flag rollout model, and the customEvents → subtable → aggregated-table pipeline to localize a regression to a (version, flag, code-path) triple. Load when an error/crash/availability metric spikes for a single ClientVersion or after a phased Defender-for-Android rollout.
confidence: low
---

## KNOW

### Background
- **Windows precedent:** v2.28.96 of the Windows GSA client shipped a regression that surfaced as a specific error-code spike for clients reporting that ClientVersion. The fix pattern was: (1) identify the version, (2) find what *changed* (flag flip or new code path gated by an existing flag), (3) roll back the flag or stop the rollout, (4) ship a patched version.
- **Android telemetry foundation** (see `.squad/agents/doggett/research/android-telemetry-model.md`):
  - Every Android telemetry row carries `ClientVersion` in the 4-segment `1.0.NNNN.NNNN` format (verified by Scully against `TunnelServerOperationEvents`).
  - Raw events land in `customEvents` in `MDATPAndroidDB` on cluster `mdatpandroidcluster.westus2.kusto.windows.net` and fan out into 10 domain subtables.
  - GSA tunnel events live in `TelemetryVPNAndWebProtection` (`Vpn*`, `Tunnel*`, `Naas*`, `Edge*`); auth in `TelemetryAuth` (`MSAL*`, `Token*`, `SignIn*`, `PRT*`); flag evaluations in `TelemetryConfiguration` (`ECS*`, `Config*`, `Feature*`).
- **Feature-flag rollout model on Android:** ECS (`EcsManager.isFeatureEnabled("Feature/Name", default)`) — audience predicates include `user type, enrollment, android version, device, tenant` (`agent-docs/FeatureFlags.md` line 11). A flag can be rolled out **per Android client version**, which is what makes a version regression possible without any code change in the suspect version.
- **On-device caching pattern:** Feature managers cache flag evaluations in `AtomicBoolean` and subscribe to `HANDLER_MSG_ECS_CONFIG_REFRESH` to invalidate. A flag rolled out *after* a device installed Vx.Y.A.B will only take effect after the next ECS refresh — so a regression can show up *days* after a version's release.

### Prerequisites
- Read access to `mdatpandroidcluster.westus2.kusto.windows.net / MDATPAndroidDB` (via `azure-mcp-kusto`).
- Familiarity with the Android telemetry model doc (`.squad/agents/doggett/research/android-telemetry-model.md`).
- Knowledge of canonical filters: `| where DeviceOs has_cs 'ANDROID'` (case-sensitive) on server-side tables; `bag_unpack` patterns on raw `customEvents`.

### Constraints
- **No WD.Client.Android source access yet.** This skill operates from telemetry only. Once VSTS access lands, augment with codebase grep for the suspect flag's call sites + `git blame`.
- **CONFIDENCE: low.** This pattern is **derived**, not validated against a real Android regression. The Windows precedent + Android FeatureFlags doc + ClientVersion availability make it plausible, but the first real run should be paired with Scully and treated as a hypothesis test.
- Aggregated tables in the `"dashboard"` folder may already cover some of these dimensions — check `.show tables | where Folder == "dashboard"` before building ad-hoc queries.

## DO

### Step 1 — Establish the baseline ClientVersion distribution

Pull the active-version mix for the trailing 7 days, weighted by event volume. The "suspect" version is the one where a metric diverges from peers.

```kql
TelemetryVPNAndWebProtection      // or whichever subtable matches the symptom
| where timestamp > ago(7d)
| summarize Events = count(), Devices = dcount(MachineId) by ClientVersion
| order by Events desc
```

Record the top 5–10 versions and their event/device counts. Confirm with `.squad/skills/android-kusto-starter/SKILL.md` that `ClientVersion` format is `1.0.NNNN.NNNN` and the case-sensitive `DeviceOs` filter is unnecessary inside `MDATPAndroidDB` subtables (those are Android-only by construction; the filter applies on shared/server-side tables only).

### Step 2 — Compute the metric divergence per version

For whichever metric is alerting (auth-failure rate, tunnel-start-failure rate, crash rate, etc.), compute the per-version time series and rank versions by deviation from the cohort median.

```kql
let cohort_start = ago(14d);
let suspect_metric = (T:(*)) {
    T
    | extend IsFailure = name in ("VpnClientStartFailed", "TunnelStartFailure", "NaasConnectionFailed")
    | summarize Total = count(), Failures = countif(IsFailure) by ClientVersion, day = bin(timestamp, 1d)
    | extend FailureRate = todouble(Failures) / Total
};
TelemetryVPNAndWebProtection
| where timestamp > cohort_start
| invoke suspect_metric()
| summarize Median = percentile(FailureRate, 50), Suspect = percentile(FailureRate, 95) by ClientVersion
| extend Divergence = Suspect - Median
| order by Divergence desc
```

The top row is the **suspect version**. Capture: `Vsuspect` (the version), `Vbaseline` (the immediately prior version), and the event-name set driving the divergence.

### Step 3 — Diff the ECS flag-evaluation surface between versions

Pull the set of flags that evaluated for `Vsuspect` vs `Vbaseline`. A flag that newly evaluates `true` (or newly evaluates *at all*) in `Vsuspect` is the prime suspect.

```kql
let Vsuspect = "1.0.NNNN.BBB";
let Vbaseline = "1.0.NNNN.AAA";
TelemetryConfiguration
| where timestamp > ago(14d)
| where name in ("FeatureEvaluated", "ECSConfigRefresh", "ConfigUpdated")  // verify exact names via `customEvents | where name has 'Feature' | distinct name`
| extend FeatureName = tostring(EventProperty.FeatureName),
         Value = tostring(EventProperty.Value)
| where ClientVersion in (Vsuspect, Vbaseline)
| summarize EvalCount = count(),
            TrueCount = countif(Value == "true"),
            FalseCount = countif(Value == "false")
          by ClientVersion, FeatureName
| evaluate pivot(ClientVersion, sum(TrueCount), FeatureName)
// Inspect rows where TrueCount differs significantly between the two columns
```

If the exact event/property names differ, fall back to `customEvents | where name has "Feature" or name has "ECS" | take 10 | evaluate bag_unpack(EventProperty)` to discover the real schema first.

### Step 4 — Correlate the suspect flag with the failure spike

For each candidate flag from Step 3, segment the failure rate by flag-evaluation outcome within `Vsuspect`. If failure rate is concentrated in the `flag == true` cohort, you have the regression.

```kql
let Vsuspect = "1.0.NNNN.BBB";
let SuspectFlag = "NetworkProtection/SomeNewFlag";
// 1. Devices that evaluated the flag in the last 7d
let FlagState = TelemetryConfiguration
    | where timestamp > ago(7d)
    | where ClientVersion == Vsuspect
    | where tostring(EventProperty.FeatureName) == SuspectFlag
    | summarize arg_max(timestamp, *) by MachineId
    | project MachineId, FlagValue = tostring(EventProperty.Value);
// 2. Failure events for the same devices/version
TelemetryVPNAndWebProtection
| where timestamp > ago(7d)
| where ClientVersion == Vsuspect
| where name in ("VpnClientStartFailed", "TunnelStartFailure", "NaasConnectionFailed")
| join kind=inner FlagState on MachineId
| summarize FailureCount = count() by FlagValue
```

If `FlagValue == "true"` carries the bulk of failures → the flag is the regression vector. If it splits evenly → the regression is **version-intrinsic** (a code change shipped in `Vsuspect`), not flag-gated.

### Step 5 — Identify the mitigation path

| Pattern | Mitigation |
|---|---|
| Flag-gated regression (Step 4 shows concentration in `true` cohort) | Roll the flag back through ECS (no client update needed). Coordinate with Defender ECS owner. |
| Version-intrinsic regression (Step 4 shows uniform distribution) | Halt the Play Store / MAM rollout of `Vsuspect`; ship `Vsuspect+1` with the fix. |
| Audience-specific (only certain `EnrollmentType`, `Persona`, or `TenantIdPII` cohorts impacted) | Narrow the ECS audience predicate to exclude the affected cohort; ship a longer-term fix later. |

### Step 6 — File the finding

Write to `.squad/agents/doggett/research/regression-<YYYY-MM-DD>-<vX.Y.A.B>.md`:
- `Vsuspect`, `Vbaseline`, suspect-flag name (if any).
- Event-name set + failure-rate divergence numbers.
- Mitigation recommendation.
- Cite the KQL queries used.

Open a decision in `.squad/decisions/inbox/` if mitigation requires cross-team coordination.

## CHECK

- [ ] Confirmed the suspect ClientVersion via per-version metric divergence (Step 2), not just gut feel from a release-notes diff.
- [ ] Verified the exact event-name + property-name strings via `customEvents | ... | bag_unpack(EventProperty) | take N` before relying on them in production queries (Steps 3 + 4).
- [ ] Tested whether the regression is flag-gated (Step 4) — concentration in `flag == true` cohort is the smoking gun.
- [ ] Documented the suspect flag's name and the ECS audience predicate that targeted `Vsuspect` (record source: Defender ECS team or `Identity-gsa-client-marketplace` Kusto catalog if it surfaces flag metadata).
- [ ] Mitigation path proposed matches the regression class (flag rollback vs version rollback vs audience narrowing).
- [ ] Finding filed under `.squad/agents/doggett/research/regression-...md`; decision opened if cross-team action required.
- [ ] Paired with Scully on at least one cross-check (they own the Kusto catalog + dashboard mapping; second opinion catches false positives).

## Common Rationalizations

| Rationalization | Rebuttal |
|---|---|
| "The error rate spike correlates with `Vsuspect` release time, that's enough." | Time correlation ≠ causation. A coincident ECS rollout or backend change can fake a version regression. Run Step 4 to disambiguate. |
| "We don't need to verify event/property names — the doc probably says X." | The 10-subtable doc lists ~632 events but property names are dynamic (`bag_unpack`). Always confirm via `take N` against live data before assuming. |
| "The flag was rolled out to 100% before `Vsuspect` shipped, so it can't be the cause." | An older flag can still trigger a regression *in `Vsuspect`* if `Vsuspect` introduced a new code path gated by that flag. Check `git blame` once VSTS access lands. |
| "Just roll back the Play Store release — fastest fix." | Play Store rollback can take 24–72h and doesn't unwind MAM-deployed installs. A flag rollback (if applicable) takes minutes and reaches all enrolled devices on next ECS refresh. Prefer flag rollback when possible. |
| "ClientVersion is in every row, so I can pivot on it freely." | True on `MDATPAndroidDB` subtables. On server-side tables (`NaasProd / TunnelServerOperationEvents`), apply `| where DeviceOs has_cs 'ANDROID'` first or you'll mix Windows/Mac/iOS rows. |

## Red Flags

- Diagnosing a "version regression" without ever running Step 2 (per-version divergence query) — you are guessing.
- Citing a flag as the cause without Step 4's `flag == true` concentration check.
- Recommending a Play Store rollback as first-line mitigation when the regression is flag-gated.
- Skipping the `bag_unpack` schema-confirmation step and writing queries against assumed property names — silent zero-row failures.
- Operating without pairing with Scully — single-agent regression calls have been wrong before (see Scully's earlier App Insights routing correction).
- Filing the finding without recording `Vbaseline` (the comparison anchor) — makes the finding non-reproducible.
