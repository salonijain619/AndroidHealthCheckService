# 📋 GSA Daily Livesite Report — {day} {month} {date}, {year}

## 📟 On-Call Today
🔴 **Primary**    {primary_oncall_name} ({primary_oncall_handle})  
🟡 **Backup**     {backup_oncall_name} ({backup_oncall_handle})

---

## Executive Summary

{critical_issue_1_emoji} **{critical_issue_1_severity}:** {critical_issue_1_title} — {critical_issue_1_blast_radius_and_context}

{critical_issue_2_emoji} **{critical_issue_2_severity}:** {critical_issue_2_title} — {critical_issue_2_blast_radius_and_context}

{status_emoji} **Fleet Status:** {fleet_health_summary} — {fleet_metric_trend}

{additional_insight_emoji} **{additional_insight_title}:** {additional_insight_detail}

---

## Key Metrics

| Metric | Value | Trend |
|--------|-------|-------|
| Active Android Clients (weekday) | {TBD — pending Scully telemetry} | {TBD} |
| Fleet Errors (7d) | {TBD — pending Scully telemetry} | {TBD} |
| APS Availability | {TBD — pending Scully telemetry} | {TBD} |
| PKI Health | {TBD — pending Scully telemetry} | {TBD} |
| Tunnel Health | {TBD — pending Scully telemetry} | {TBD} |
| Android Client Version Distribution Health | {TBD — pending Scully telemetry} | {TBD} |
| Business Growth (7d) | {TBD — pending Scully telemetry} | {TBD} |

**Data Completeness Notes:**  
*{TBD — Scully: note if telemetry is still ingesting, any schema drift, or query timeout issues}*

---

## 🔍 Top 5 Insights

| # | Severity | Insight Title | Blast Radius | Action / Owner |
|---|----------|---------------|-------------|-----------------|
| 1 | {TBD — pending Skinner} | {insight_1_title} | {insight_1_blast_radius} | {insight_1_action} |
| 2 | {TBD — pending Skinner} | {insight_2_title} | {insight_2_blast_radius} | {insight_2_action} |
| 3 | {TBD — pending Skinner} | {insight_3_title} | {insight_3_blast_radius} | {insight_3_action} |
| 4 | {TBD — pending Skinner} | {insight_4_title} | {insight_4_blast_radius} | {insight_4_action} |
| 5 | {TBD — pending Skinner} | {insight_5_title} | {insight_5_blast_radius} | {insight_5_action} |

---

## 🔥 Cross-Domain Correlation Analysis

**Primary Correlation Chain:** {primary_chain_title}  
*Example: Android client v{X.Y.Z} auth regression → APS policy delivery → notification channel failures*

**Timeline:**
{TBD — pending Doggett: hour-by-hour spike narrative linking telemetry events across auth, policy, and client-side subsystems}

**Evidence:**
{TBD — pending Doggett: supporting telemetry counts, error rate ratios, and cross-domain signal alignment}

**Validation Steps:**
{TBD — pending Doggett: list of hypotheses to confirm (e.g., "v{X.Y.Z} auth failures precede policy fetch errors by <5 min", "tray icon errors spike in same cohort")}

---

## 📊 Data Quality Notes

- **Telemetry Source:** Kusto (NaasProd @ idsharedwus), AppInsights (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c), Aria Kusto (f0eaa94222894be599b7cd0bc1e2ed6f)
- **Open Questions:**
  - {TBD: Should we track Play Store vs. sideload/MAM channel adoption separately?}
  - {TBD: Android OS version split health tracking — baseline expectations?}
  - {TBD: Device model/OEM error variance — reportable signal or noise?}
- **Caveats:** {TBD — Scully: any schema drift, missing partitions, or ingest delays}

---

## Contributors

Mulder, Scully, Doggett, Skinner

**Timestamp:** {date} ({full_date_string})  
**Report Assembled By:** Reyes (Report Writer)
