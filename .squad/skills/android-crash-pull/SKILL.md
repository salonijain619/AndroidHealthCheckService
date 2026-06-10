# Android crash pull pointer — updated 2026-06-10 (Frohike)

Confidence: **HIGH** — verified end-to-end against Google Play Vitals on 2026-06-10 with the canonical google-play-vitals skill. Pattern below produces the daily NAAS Client Stability section.

## Canonical source
- Canonical Android crash / ANR source: `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md`.
- Package: `com.microsoft.scmx`.
- Preferred invocation: when MCP `mcp_google-play-r_*` tools are exposed, use them. When they are not (default in current Copilot CLI), use the direct-API fallback below.

## Auth + direct-API fallback (verified working 2026-06-10)
1. **Env:** `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` must point to the service-account JSON. Verified path: `/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json`.
2. **Python:** USE the MCP server's venv — it has `googleapiclient`/`google-oauth2` installed; system python does not. Path: `/Users/salonijain/workspace/android/WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server/.venv/bin/python`.
3. **Wrapper:** import `src.auth.GooglePlayAuth` and `src.reporting_client.ReportingClient` from `WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server` (prepend to `sys.path`), set `GOOGLE_PLAY_PACKAGE_NAME=com.microsoft.scmx`, instantiate, call.

```python
import sys, os
sys.path.insert(0, '/Users/salonijain/workspace/android/WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server')
os.environ.setdefault('GOOGLE_PLAY_PACKAGE_NAME','com.microsoft.scmx')
from src.auth import GooglePlayAuth
from src.reporting_client import ReportingClient
c = ReportingClient(GooglePlayAuth())
svc = c._auth.get_service()   # raw googleapiclient service for arbitrary bodies
```

## NAAS filter pattern (issue-cluster level)
Pull top issues (`errorIssues:search`, order by `errorReportCount desc`, page 6× of 25 = 150). For each issue, apply the NAAS predicate over `cause || ' ' || location`:

```text
NAAS predicate (case-insensitive contains any):
  vpnserviceorchestrator | com.microsoft.scmx.vpn | com.microsoft.intune.vpn
  features.consumer.vpn  | features.naas | baseopenvpnclient | openvpn
  libnaas | naas | tunnel | vpn
```

Verified output on 2026-06-10 pull: 17 NAAS issues (4 CRASH, 13 APPLICATION_NOT_RESPONDING) out of top-150 by lifetime count.

## Per-NAAS-issue 7d totals (the right way — verified 2026-06-10)
**Don't try to paginate `errorCount × issueId` unfiltered** — issue cardinality is in the tens of thousands. Instead, **one filtered query per NAAS issue**:

```python
body = {
  'timelineSpec':{'aggregationPeriod':'FULL_RANGE',
                  'startTime':{'year':2026,'month':6,'day':3},
                  'endTime':{'year':2026,'month':6,'day':9}},
  'dimensions':['reportType','versionCode'],     # add deviceBrand / apiLevel as needed
  'metrics':['errorReportCount','distinctUsers'],
  'pageSize': 1000,
  'filter': f'issueId = "{iid}"',
}
svc.vitals().errors().counts().query(name='apps/com.microsoft.scmx/errorCountMetricSet', body=body).execute()
```
Returns <20 rows per issue (per-version split). 17 NAAS issues = ~17 fast calls. Stays inside the 7,200/day quota with massive headroom.

## App-level rates (whole `com.microsoft.scmx`, NOT NAAS-only)
```python
# crashRate / anrRate support: DAILY + HOURLY (NO FULL_RANGE).
# Dimensions: versionCode, countryCode, apiLevel, deviceBrand/Model/Type/Ram/Soc/Cpu/Gpu/Vulkan/Gl/Screen, osBuild.
# Default ReportingClient.query_metrics has max_pages=3 hard-coded — paginate manually for full coverage.
body = {'timelineSpec':{'aggregationPeriod':'DAILY','startTime':...,'endTime':...},
        'dimensions':['versionCode'],
        'metrics':['userPerceivedCrashRate','distinctUsers'],
        'pageSize':1000}
svc.vitals().crashrate().query(name='apps/com.microsoft.scmx/crashRateMetricSet', body=body).execute()
```
User-weight-average rates locally for 7d aggregate (rate × distinctUsers / Σ distinctUsers).

## NAAS-as-a-unit framing rule (HARD)
- Play has **no NAAS-only crash rate**. Numerator (NAAS event counts) is derivable; denominator (NAAS-using sessions) is not. Always state denominator explicitly.
- For headline rates, publish the whole-app user-perceived rate with explicit "denominator = all com.microsoft.scmx users" caveat.
- For NAAS event volume, publish counts with affected-users upper bound (sum of per-issue `distinctUsers`, NOT deduplicated).
- For per-version concentration, the per-Defender-version NAAS table is the PRIMARY artifact, not an appendix.

## Known gotchas
| Gotcha | Workaround |
|---|---|
| `countryCode` not valid on `errorCountMetricSet` | Use `crashRate` / `anrRate` for country cuts; accept that those are whole-app, not NAAS-only. |
| `crashRate`/`anrRate` reject `FULL_RANGE` | Use DAILY + local user-weight-average. |
| `ReportingClient.query_metrics` caps at 3 pages | Bypass via `_auth.get_service()` and your own pagination loop. |
| ANR issue `type` is `APPLICATION_NOT_RESPONDING` (full string) | Don't filter for `"ANR"`. |
| `.04xx` ring versions return no Play rate | Sub-threshold install base — Play withholds. Use Scully's server-side rate. |
| `distinctUsers` summed across issues ≠ unique users | It's an upper bound. Label "affected users (upper bound, not deduplicated)". |

## Supplementary fallback (NOT canonical)
The prior AppEvents / CrashReported KQL path is **not canonical** for user-perceived Android crashes. Use only as a supplementary raw-exit signal:

```kql
AppEvents
| where Name in ('AppExitInfoReported','CrashReported')
| extend p=parse_json(Properties)
| where tostring(p.Description) has '.vpn.VpnServiceOrchestrator'
   or tostring(p.StackTrace) has 'VpnServiceOrchestrator'
   or tostring(p.StackTrace) has 'com.microsoft.scmx.vpn'
```
Do not ship AppEvents numbers as Play crash/ANR rates.

## Worked example
See `.squad/agents/frohike/research/pull-2026-06-10/pull.py` and `naas-crashes-2026-06-10.md` for a complete end-to-end run of this pattern.
