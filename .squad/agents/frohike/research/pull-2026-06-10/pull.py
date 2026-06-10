#!/usr/bin/env python3
"""Frohike 2026-06-10 NAAS-filtered Play Vitals pull (7d, 2026-06-03..2026-06-10)."""
import json, os, sys
from pathlib import Path

SRV = Path("/Users/salonijain/workspace/android/WD.Client.Android/WD.Mobile.XPlat.Infra/mcp/google-play-reporting-server")
sys.path.insert(0, str(SRV))
os.environ.setdefault("GOOGLE_PLAY_PACKAGE_NAME", "com.microsoft.scmx")

from src.auth import GooglePlayAuth
from src.reporting_client import ReportingClient

OUT = Path("/Users/salonijain/workspace/AndroidHealthCheckService/.squad/agents/frohike/research/pull-2026-06-10")

def dump(name, obj):
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(obj, indent=2, default=str))
    print(f"  wrote {p.name} ({p.stat().st_size} bytes)")

auth = GooglePlayAuth()
c = ReportingClient(auth)

print("== freshness ==")
dump("freshness", c.get_all_freshness())

print("== release_filter_options ==")
dump("release_filter_options", c.get_release_filter_options())

print("== crash_rate 7d by versionCode ==")
dump("crash_rate_7d_by_version", c.query_metrics("crashRate", days=7, dimensions=["versionCode"]))

print("== anr_rate 7d by versionCode ==")
dump("anr_rate_7d_by_version", c.query_metrics("anrRate", days=7, dimensions=["versionCode"]))

print("== crash_rate 14d (trend) ==")
dump("crash_rate_14d_by_version", c.query_metrics("crashRate", days=14, dimensions=["versionCode"]))

print("== anr_rate 14d (trend) ==")
dump("anr_rate_14d_by_version", c.query_metrics("anrRate", days=14, dimensions=["versionCode"]))

print("== error_counts 7d by reportType+versionCode ==")
dump("error_counts_7d_by_version", c.query_metrics("errorCount", days=7, dimensions=["reportType","versionCode"], page_size=1000))

print("== error_counts 7d by reportType+issueId ==")
dump("error_counts_7d_by_issue", c.query_metrics("errorCount", days=7, dimensions=["reportType","issueId"], page_size=1000))

print("== error_counts 7d by reportType+issueId+versionCode ==")
dump("error_counts_7d_by_issue_version", c.query_metrics("errorCount", days=7, dimensions=["reportType","issueId","versionCode"], page_size=1000))

print("== error_counts 7d by reportType+countryCode ==")
dump("error_counts_7d_by_country", c.query_metrics("errorCount", days=7, dimensions=["reportType","countryCode"], page_size=1000))

print("== search_error_issues ==")
issues=[]; tok=None
for i in range(4):
    resp = c.search_error_issues(order_by="errorReportCount desc", page_size=25, page_token=tok)
    issues.extend(resp.get("errorIssues", []))
    tok = resp.get("nextPageToken")
    if not tok: break
dump("search_error_issues", {"errorIssues": issues, "count": len(issues)})

print("DONE")
