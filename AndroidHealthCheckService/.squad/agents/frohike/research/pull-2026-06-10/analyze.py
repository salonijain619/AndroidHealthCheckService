#!/usr/bin/env python3
"""Frohike analysis — produces aggregates for the 2026-06-10 NAAS report."""
import json, sys, re
from collections import defaultdict
from pathlib import Path

D = Path("/Users/salonijain/workspace/AndroidHealthCheckService/.squad/agents/frohike/research/pull-2026-06-10")

NAAS_PATTERNS = [
    "vpnserviceorchestrator", "com.microsoft.scmx.vpn", "com.microsoft.intune.vpn",
    "features.consumer.vpn", "features.naas", "baseopenvpnclient", "openvpn",
    "libnaas", "naas", "tunnel", "vpn"
]

def is_naas(*texts):
    blob = " ".join(t for t in texts if t).lower()
    return any(p in blob for p in NAAS_PATTERNS)

# ---- 1. Build NAAS issue ID set from issue inventory ----
issues = json.load(open(D/"search_error_issues.json"))["errorIssues"]
print(f"Total issues fetched: {len(issues)}")

naas_issue_ids = set()
issue_meta = {}  # id -> dict
for i in issues:
    # API returns 'name' = apps/.../errorIssues/{id}
    name = i.get("name","")
    iid = name.split("/")[-1] if name else ""
    cause = i.get("cause","")
    loc = i.get("location","")
    typ = i.get("type","")  # CRASH / ANR
    cnt = int(i.get("errorReportCount", 0))
    last = i.get("lastErrorReportTime",{})
    first = i.get("firstErrorReportTime",{})
    affected_versions = i.get("sampleErrorReports", [])
    issue_meta[iid] = {
        "cause": cause, "location": loc, "type": typ,
        "cnt": cnt, "naas": is_naas(cause, loc),
        "last": last, "first": first,
        "distinctUsersPercent": i.get("distinctUsersPercent"),
        "name": name,
    }
    if is_naas(cause, loc):
        naas_issue_ids.add(iid)

print(f"NAAS issue IDs: {len(naas_issue_ids)}")
naas_crash = [i for i,m in issue_meta.items() if m["naas"] and m["type"]=="CRASH"]
naas_anr   = [i for i,m in issue_meta.items() if m["naas"] and m["type"]=="ANR"]
print(f"  NAAS crash issues: {len(naas_crash)}, NAAS ANR issues: {len(naas_anr)}")

# ---- 2. error_counts_7d_by_issue (in window) — totals per issue, plus identify NAAS sums ----
def parse_rows(path):
    """Returns list of (dims_dict, metrics_dict, date_str)."""
    j = json.load(open(path))
    out = []
    for r in j.get("rows",[]):
        st = r.get("startTime",{})
        date_str = f"{st.get('year'):04d}-{st.get('month'):02d}-{st.get('day'):02d}" if st else ""
        dims = {d["dimension"]:d.get("stringValue") or d.get("int64Value") or d.get("valueLabel") for d in r.get("dimensions",[])}
        # Capture numerics properly
        for d in r.get("dimensions",[]):
            for k in ("stringValue","int64Value","valueLabel"):
                if k in d and d[k] is not None:
                    dims[d["dimension"]] = d[k]
                    break
        mets = {}
        for m in r.get("metrics",[]):
            name = m["metric"]
            val = m.get("decimalValue",{}).get("value") if "decimalValue" in m else None
            if val is None:
                val = m.get("doubleValue") or m.get("int64Value")
            try:
                val = float(val) if val is not None else 0.0
            except: val = 0.0
            mets[name] = val
        out.append((dims, mets, date_str))
    return out

ec_by_issue = parse_rows(D/"error_counts_7d_by_issue.json")
print(f"\nerror_counts_7d_by_issue rows: {len(ec_by_issue)}")
# Distinct dates in window
dates = sorted(set(r[2] for r in ec_by_issue))
print(f"  Date range: {dates[0]} .. {dates[-1]}  ({len(dates)} days)")

# Sum per-issue across window
issue_totals = defaultdict(lambda: {"CRASH":{"cnt":0,"users":0}, "ANR":{"cnt":0,"users":0}, "UNKNOWN":{"cnt":0,"users":0}})
for dims, mets, _ in ec_by_issue:
    iid = dims.get("issueId","?")
    rt = dims.get("reportType","UNKNOWN")
    issue_totals[iid][rt]["cnt"] += mets.get("errorReportCount",0)
    issue_totals[iid][rt]["users"] += mets.get("distinctUsers",0)

# NAAS totals over 7d window
naas_crash_total = sum(issue_totals[iid]["CRASH"]["cnt"] for iid in naas_issue_ids)
naas_anr_total = sum(issue_totals[iid]["ANR"]["cnt"] for iid in naas_issue_ids)
naas_crash_users_upper = sum(issue_totals[iid]["CRASH"]["users"] for iid in naas_issue_ids)
naas_anr_users_upper = sum(issue_totals[iid]["ANR"]["users"] for iid in naas_issue_ids)
print(f"\n=== NAAS 7d in-window (errorCount metric, dates {dates[0]}..{dates[-1]}) ===")
print(f"  NAAS crash reports: {int(naas_crash_total)}")
print(f"  NAAS ANR reports:   {int(naas_anr_total)}")
print(f"  NAAS crash users (upper, not dedup): {int(naas_crash_users_upper)}")
print(f"  NAAS ANR users (upper, not dedup):   {int(naas_anr_users_upper)}")

# All-cluster totals (for share)
all_crash_total = sum(d["CRASH"]["cnt"] for d in issue_totals.values())
all_anr_total = sum(d["ANR"]["cnt"] for d in issue_totals.values())
print(f"  All com.microsoft.scmx crash reports: {int(all_crash_total)} (NAAS share {100*naas_crash_total/max(1,all_crash_total):.1f}%)")
print(f"  All com.microsoft.scmx ANR reports:   {int(all_anr_total)} (NAAS share {100*naas_anr_total/max(1,all_anr_total):.1f}%)")

# ---- 3. Per-version NAAS counts via error_counts_7d_by_issue_version ----
ec_by_iv = parse_rows(D/"error_counts_7d_by_issue_version.json")
print(f"\nerror_counts_7d_by_issue_version rows: {len(ec_by_iv)}")
ver_naas = defaultdict(lambda: {"CRASH":0.0, "ANR":0.0, "users_proxy":0.0})
for dims, mets, _ in ec_by_iv:
    iid = dims.get("issueId","?")
    if iid not in naas_issue_ids: continue
    vc = str(dims.get("versionCode","?"))
    rt = dims.get("reportType","UNKNOWN")
    if rt in ("CRASH","ANR"):
        ver_naas[vc][rt] += mets.get("errorReportCount",0)
        ver_naas[vc]["users_proxy"] += mets.get("distinctUsers",0)

# ---- 4. App-level crash/ANR rates 7d & 14d (for trend & per-version baseline) ----
def collapse_rates(rows, metric_keys, dim="versionCode"):
    """Sum/avg the user-perceived weighted rates across rows; return per-version aggregate over window."""
    bucket = defaultdict(lambda: {"days":0, "sum_rate":0.0, "sum_userweighted":0.0, "users":0.0,
                                  "max_rate":0.0, "min_rate":1e9})
    by_version = defaultdict(list)
    for dims, mets, dstr in rows:
        v = str(dims.get(dim,"?"))
        by_version[v].append((dstr, mets))
    return by_version

cr7 = collapse_rates(parse_rows(D/"crash_rate_7d_by_version.json"), [])
ar7 = collapse_rates(parse_rows(D/"anr_rate_7d_by_version.json"), [])
cr14 = collapse_rates(parse_rows(D/"crash_rate_14d_by_version.json"), [])
ar14 = collapse_rates(parse_rows(D/"anr_rate_14d_by_version.json"), [])

def avg_metric(per_version_dict, version, key):
    rows = per_version_dict.get(version, [])
    vals = [m.get(key,0.0) for _, m in rows if m.get(key,0.0) > 0]
    return sum(vals)/len(vals) if vals else 0.0

def sum_users(per_version_dict, version):
    rows = per_version_dict.get(version, [])
    return sum(m.get("distinctUsers",0.0) for _, m in rows)

# Headline: roll up across all versions (weighted by distinctUsers) for whole-app user-perceived rate
def app_weighted_rate(per_version_dict, key):
    """Weighted avg using user-day denominators per row."""
    num, den = 0.0, 0.0
    for v, rows in per_version_dict.items():
        for _, m in rows:
            users = m.get("distinctUsers",0.0)
            rate = m.get(key,0.0)
            num += rate * users
            den += users
    return (num/den) if den else 0.0

app_uperc_crash_7d = app_weighted_rate(cr7, "userPerceivedCrashRate")
app_uperc_anr_7d = app_weighted_rate(ar7, "userPerceivedAnrRate")
print(f"\n=== App-level (com.microsoft.scmx) user-perceived rates, 7d ===")
print(f"  user-perceived crash rate (user-weighted across versions): {app_uperc_crash_7d*100:.4f}%")
print(f"  user-perceived ANR rate (user-weighted across versions):   {app_uperc_anr_7d*100:.4f}%")

# Trend: split 14d into earlier 7d vs latest 7d
def split_trend(per_version_dict_14d, key):
    """Returns (prior_7d_rate, latest_7d_rate) user-weighted."""
    sd = sorted({d for v, rows in per_version_dict_14d.items() for d, _ in rows})
    if len(sd) < 8: return None, None
    cutoff = sd[len(sd)//2]
    def w(date_pred):
        num, den = 0.0, 0.0
        for v, rows in per_version_dict_14d.items():
            for d, m in rows:
                if not date_pred(d): continue
                users = m.get("distinctUsers",0.0)
                num += m.get(key,0.0) * users; den += users
        return (num/den) if den else 0.0
    earlier = w(lambda d: d < cutoff)
    later = w(lambda d: d >= cutoff)
    return earlier, later

prior_crash, latest_crash = split_trend(cr14, "userPerceivedCrashRate")
prior_anr, latest_anr = split_trend(ar14, "userPerceivedAnrRate")
print(f"\n=== 14d trend ===")
print(f"  user-perceived crash rate prior 7d: {prior_crash*100:.4f}%  latest 7d: {latest_crash*100:.4f}%  delta {(latest_crash-prior_crash)*100:+.4f} pp")
print(f"  user-perceived ANR rate prior 7d:   {prior_anr*100:.4f}%  latest 7d: {latest_anr*100:.4f}%  delta {(latest_anr-prior_anr)*100:+.4f} pp")

# ---- 5. Per-version table ----
# version_code -> Defender version mapping (just last 8 digits -> 1.0.NNNN.NNNN, arm64 ends in 2; we'll show raw code + label)
def vcode_to_label(vc):
    # 900300112 -> 1.0.9003.0101 (arm64=2 → "01")
    if len(vc) != 9: return vc
    a, b, c = vc[1:5], vc[5:8], vc[8]
    abi = {"1":"v7a","2":"arm64","3":"x86","4":"x86_64"}.get(c, c)
    last4 = b[:2] + b[2:]
    # major.minor.NNNN.MMMM where digits 1-4 = NNNN, digits 5-7+abi-suffix layout = MMMM
    # observed: 900300412 → 1.0.9003.0401. So: digits 1-4 → "9003", digits 5-7 → "041" + arm64 ("2") → reconstruct 04 0 1 → "0401"
    # Pattern: V{NNNN}{MMM}{abi}, where MMM = MM + "01" omitted. Use known map for clarity.
    known = {
        "900300112":"1.0.9003.0101","900300122":"1.0.9003.0102",
        "900300212":"1.0.9003.0201","900300412":"1.0.9003.0401",
        "900300312":"1.0.9003.0301","900200122":"1.0.9002.0102",
        "892100112":"1.0.8921.0101","891300112":"1.0.8913.0101",
        "892100111":"1.0.8921.0101","890600132":"1.0.8906.0103",
        "880500132":"1.0.8805.0103","891800122":"1.0.8918.0102",
        "881400111":"1.0.8814.0101","890500192":"1.0.8905.0190",
        "870300112":"1.0.8703.0101","741300112":"1.0.7413.0101",
        "781100112":"1.0.7811.0101","742700112":"1.0.7427.0101",
        "612200322":"1.0.6122.0302",
    }
    return known.get(vc, f"{vc}(unknown)")

print("\n=== NAAS Per-Defender-Version table (7d, errorCount metric) ===")
# Need per-version user-perceived crash/ANR rate from app-level rate queries (NOT NAAS-only — denominator is sessions on that version)
print(f"{'VersionCode':<11} {'Label':<24} {'NAAS-Crash':>10} {'NAAS-ANR':>9} {'AppCrashRate':>13} {'AppANRRate':>11} {'DistinctUsers_proxy':>20}")
ring_04xx = []
all_rows = []
for vc in sorted(ver_naas.keys(), key=lambda v: ver_naas[v]["CRASH"]+ver_naas[v]["ANR"]*0.3, reverse=True):
    nc = int(ver_naas[vc]["CRASH"])
    na = int(ver_naas[vc]["ANR"])
    label = vcode_to_label(vc)
    # App crash/anr rate for this version: avg over 7d window
    app_cr = avg_metric(cr7, vc, "userPerceivedCrashRate") * 100
    app_ar = avg_metric(ar7, vc, "userPerceivedAnrRate") * 100
    users_proxy = int(ver_naas[vc]["users_proxy"])
    is_04xx = ".0401" in label or ".0402" in label or ".0403" in label or ".0404" in label or ".0405" in label or vc.endswith("04xx") or "0401" in vc[-4:] or "0402" in vc[-4:] or "0403" in vc[-4:] or "0404" in vc[-4:] or "0405" in vc[-4:]
    # Better: check if 3rd-to-5th digits of full vc indicate 04xx ring (vc[5:7]=='04')
    is_04xx = vc[5:7] == "04"
    mark = "🔴" if is_04xx else "  "
    if is_04xx: ring_04xx.append(vc)
    all_rows.append((vc, label, nc, na, app_cr, app_ar, users_proxy, is_04xx))
    print(f"{mark}{vc:<11} {label:<24} {nc:>10} {na:>9} {app_cr:>12.4f}% {app_ar:>10.4f}% {users_proxy:>20}")

# Save for report writer
out = {
    "window_dates": dates,
    "freshness": {"crashRate_DAILY":"2026-06-08","anrRate_DAILY":"2026-06-08","errorCount_DAILY":"2026-06-09"},
    "naas_issue_count": len(naas_issue_ids),
    "naas_crash_total_reports": int(naas_crash_total),
    "naas_anr_total_reports": int(naas_anr_total),
    "naas_crash_users_upper": int(naas_crash_users_upper),
    "naas_anr_users_upper": int(naas_anr_users_upper),
    "app_uperc_crash_7d_pct": app_uperc_crash_7d*100,
    "app_uperc_anr_7d_pct": app_uperc_anr_7d*100,
    "trend_crash_prior_pct": prior_crash*100 if prior_crash else None,
    "trend_crash_latest_pct": latest_crash*100 if latest_crash else None,
    "trend_anr_prior_pct": prior_anr*100 if prior_anr else None,
    "trend_anr_latest_pct": latest_anr*100 if latest_anr else None,
    "all_crash_reports_in_window": int(all_crash_total),
    "all_anr_reports_in_window": int(all_anr_total),
    "ring_04xx_codes": ring_04xx,
    "per_version_rows": [
        {"vc":vc,"label":lbl,"naas_crash":nc,"naas_anr":na,"app_crash_pct":cr,"app_anr_pct":ar,"users_proxy":up,"is_04xx":x}
        for (vc,lbl,nc,na,cr,ar,up,x) in all_rows
    ],
}
(D/"aggregates.json").write_text(json.dumps(out, indent=2))
print(f"\nWrote aggregates.json")

# ---- 6. Top NAAS crash & ANR issues with depth ----
print("\n=== Top 10 NAAS crash issues by 7d count ===")
naas_crash_sorted = sorted(naas_crash, key=lambda i: issue_totals[i]["CRASH"]["cnt"], reverse=True)[:10]
for iid in naas_crash_sorted:
    m = issue_meta[iid]
    cnt = int(issue_totals[iid]["CRASH"]["cnt"])
    users = int(issue_totals[iid]["CRASH"]["users"])
    print(f"  {iid[:16]}.. cnt={cnt:<6} users={users:<6} cause={(m['cause'] or '')[:60]} loc={(m['location'] or '')[:40]}")

print("\n=== Top 10 NAAS ANR issues by 7d count ===")
naas_anr_sorted = sorted(naas_anr, key=lambda i: issue_totals[i]["ANR"]["cnt"], reverse=True)[:10]
for iid in naas_anr_sorted:
    m = issue_meta[iid]
    cnt = int(issue_totals[iid]["ANR"]["cnt"])
    users = int(issue_totals[iid]["ANR"]["users"])
    print(f"  {iid[:16]}.. cnt={cnt:<6} users={users:<6} cause={(m['cause'] or '')[:60]} loc={(m['location'] or '')[:40]}")

# Save IDs for the report writer
(D/"top_issues.json").write_text(json.dumps({
    "naas_crash_top10": [{"id":i,"cnt":int(issue_totals[i]["CRASH"]["cnt"]),"users":int(issue_totals[i]["CRASH"]["users"]),
                          "cause":issue_meta[i]["cause"],"location":issue_meta[i]["location"]} for i in naas_crash_sorted],
    "naas_anr_top10": [{"id":i,"cnt":int(issue_totals[i]["ANR"]["cnt"]),"users":int(issue_totals[i]["ANR"]["users"]),
                        "cause":issue_meta[i]["cause"],"location":issue_meta[i]["location"]} for i in naas_anr_sorted],
}, indent=2))
print("\nWrote top_issues.json")
