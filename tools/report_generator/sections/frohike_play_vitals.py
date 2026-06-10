"""frohike_play_vitals — Frohike's NAAS-as-a-unit Play Vitals section producer.

Owns the "Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)" section
of the daily livesite report. Pulls Google Play Developer Reporting API,
filters/attributes to NAAS, and emits both:

  1. The report-section markdown (`SectionResult.markdown`).
  2. A full research drop at `.squad/agents/frohike/research/naas-crashes-{date}.md`.

Conforms to Mulder's report-generator architecture
(``.squad/decisions/inbox/mulder-report-generator-architecture.md``):
  * Uses `SectionResult`/`Section`/`Status` from `tools.report_generator.contracts`.
  * Fail-soft — never raises. Returns Status.FAIL/PARTIAL with errors populated.
  * Standalone-runnable: `python -m tools.report_generator.sections.frohike_play_vitals --date YYYY-MM-DD`.
  * Reads `ctx["prior_results"][Section.LANGLY_VERSION].metadata` for cross-section
    framing (✅ LIVE PROD tag on Langly's live_play_version row).
  * Drop file is mandatory — written on every status, including FAIL.
  * HTTP retries: 3 attempts with exponential backoff on 5xx + connection errors.

Framing rules (HARD, per Frohike's charter):
  * NAAS-as-a-unit, never Defender-filtered-to-NAAS.
  * Per-Defender-version table is the PRIMARY deliverable.
  * Denominator basis MUST be stated explicitly in metadata.
  * No fabricated "NAAS-only rate" — Play does not publish a NAAS-session
    denominator. We surface NAAS event *counts* with whole-app rate as
    context, and stamp `denominator_basis = "whole_app_sessions"`.

Env vars (either satisfies auth):
  PLAY_CONSOLE_SA_KEY              — JSON contents OR filesystem path of SA key
  GOOGLE_APPLICATION_CREDENTIALS   — filesystem path to SA key JSON
  REPORT_GENERATOR_SKIP_FROHIKE    — when "1", return Status.SKIP immediately
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.report_generator.contracts import Section, SectionResult, Status


# ---------------------------------------------------------------------------
# Constants — NAAS attribution + Play API shape
# ---------------------------------------------------------------------------

PACKAGE_NAME = "com.microsoft.scmx"

# Issue-cluster-level predicate. We lower-case `(cause || ' ' || location)` for
# each issue returned by `errorIssues.search` and accept any substring match.
# Mirrors the predicate Frohike's prior drops have used since 2026-06-10.
NAAS_ATTRIBUTION_TOKENS: Tuple[str, ...] = (
    "vpnserviceorchestrator",
    "com.microsoft.scmx.vpn",
    "com.microsoft.intune.vpn",
    "features.consumer.vpn",
    "features.naas",
    "baseopenvpnclient",
    "openvpn",
    "libnaas",
    "naas",
    "tunnel",
    "vpn",
)

# Repo root: sections → report_generator → tools → repo
REPO_ROOT = Path(__file__).resolve().parents[3]
DROP_DIR = REPO_ROOT / ".squad" / "agents" / "frohike" / "research"

GOOGLE_CRASH_THRESHOLD_PCT = 1.09
GOOGLE_ANR_THRESHOLD_PCT = 0.47

EU_COUNTRIES: frozenset = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
    "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
    "RO", "SK", "SI", "ES", "SE",
})

# HTTP retry policy (Mulder §7)
RETRY_ATTEMPTS = 3
RETRY_BACKOFFS_S = (1.0, 2.0, 4.0)

_log = logging.getLogger("frohike_play_vitals")


# ---------------------------------------------------------------------------
# Public contract — produce()
# ---------------------------------------------------------------------------


def produce(date: str, ctx: Optional[Dict[str, Any]] = None) -> SectionResult:
    """Produce Frohike's daily-report section for `date` (YYYY-MM-DD).

    Args:
        date: Report date (e.g. "2026-06-10"). The 7d window is
            `date - 7d ..= date - 1d`; rate freshness lags Play 1–2 days.
        ctx: Orchestrator-provided context. Recognized keys:
            - `prior_results` (dict[Section, SectionResult]): Langly's result
              is consulted for `live_play_version` framing.
            - `runs_dir` (Path): per-run scratch dir for raw API JSON.
            - `client` (test seam): pre-built `PlayVitalsClient`-like object
              with `pull_all(date) -> dict`.
            - `drop_dir` (Path, test seam): override the research drop dir.
            - `log` (logging.Logger).
    """
    started = time.monotonic()
    ctx = ctx or {}
    log = ctx.get("log") or _log
    errors: List[str] = []
    drop_dir = Path(ctx.get("drop_dir", DROP_DIR))

    # ---- 0. Deliberate skip (env-var override) ----------------------------
    if os.environ.get("REPORT_GENERATOR_SKIP_FROHIKE", "").strip() == "1":
        return _skip_result(
            date=date,
            reason="REPORT_GENERATOR_SKIP_FROHIKE=1",
            drop_dir=drop_dir,
            started=started,
        )

    # ---- 1. Auth resolution ------------------------------------------------
    client = ctx.get("client")
    if client is None:
        auth = _resolve_credentials()
        if auth.status == "missing":
            return _partial_no_creds(date=date, drop_dir=drop_dir, started=started)
        try:
            client = PlayVitalsClient(package_name=PACKAGE_NAME, sa_key_path=auth.sa_key_path)
        except Exception as exc:  # pragma: no cover — exercised in real CI only
            errors.append(f"client_init_failed: {exc!r}")
            return _fail_result(
                date=date,
                reason=f"Play Reporting API client init failed: `{exc.__class__.__name__}`.",
                errors=errors,
                drop_dir=drop_dir,
                started=started,
                tb=traceback.format_exc(),
            )

    # ---- 2. Data pull (fail-soft) -----------------------------------------
    try:
        raw = client.pull_all(date)
    except Exception as exc:
        errors.append(f"pull_all_failed: {exc!r}")
        log.warning("Play Vitals pull failed for %s: %r", date, exc)
        return _fail_result(
            date=date,
            reason=f"Play Reporting API pull failed: `{exc.__class__.__name__}`.",
            errors=errors,
            drop_dir=drop_dir,
            started=started,
            tb=traceback.format_exc(),
        )

    # ---- 3. Transform: NAAS attribution + per-version aggregation ---------
    try:
        analysis = analyze(raw)
    except Exception as exc:
        errors.append(f"analyze_failed: {exc!r}")
        return _fail_result(
            date=date,
            reason=f"NAAS attribution / analysis failed: `{exc.__class__.__name__}`.",
            errors=errors,
            drop_dir=drop_dir,
            started=started,
            tb=traceback.format_exc(),
        )

    # ---- 4. Cross-section framing from Langly (Mulder §2) -----------------
    live_play_version = _live_version_from_ctx(ctx)
    section_md = render_section_markdown(date, analysis, live_play_version=live_play_version)
    drop_md = render_drop_file_markdown(date, analysis, raw, live_play_version=live_play_version)
    drop_path = _write_drop_file(drop_dir, date, drop_md)

    # Optional: dump raw JSON into runs_dir for inspection.
    runs_dir = ctx.get("runs_dir")
    if runs_dir:
        try:
            Path(runs_dir).mkdir(parents=True, exist_ok=True)
            (Path(runs_dir) / "frohike_raw.json").write_text(
                json.dumps(raw, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:  # never fatal
            log.debug("runs_dir dump skipped: %r", exc)

    status = _grade(analysis, errors)
    return SectionResult(
        section=Section.FROHIKE_PLAY_VITALS,
        status=status,
        markdown=section_md,
        metadata={
            "naas_crash_rate_pct": analysis.app_crash_rate_pct,
            "naas_anr_rate_pct": analysis.app_anr_rate_pct,
            "naas_crash_count": analysis.total_naas_crashes,
            "naas_anr_count": analysis.total_naas_anrs,
            "naas_issue_count": len(analysis.naas_issues),
            "germany_crash_pct": analysis.germany_pct,
            "eu_aggregate_pct": analysis.eu_aggregate_pct,
        },
        denominators={
            "denominator_basis": analysis.denominator_basis,
            "app_session_basis": "all com.microsoft.scmx Android sessions in 7d window",
            "naas_session_basis": "not exposed by Play — see Scully TunnelServerOperationEvents",
        },
        errors=errors,
        drop_path=str(drop_path),
        elapsed_s=round(time.monotonic() - started, 3),
    )


# ---------------------------------------------------------------------------
# Auth resolution
# ---------------------------------------------------------------------------


@dataclass
class _AuthState:
    status: str  # "ok" | "missing"
    sa_key_path: Optional[str] = None
    _tempfile_handle: Optional[Any] = None  # keep handle alive


def _resolve_credentials() -> _AuthState:
    """Resolve service-account creds from env. PLAY_CONSOLE_SA_KEY wins.

    PLAY_CONSOLE_SA_KEY may carry either:
      - raw JSON contents of the key (preferred for GitHub Actions secrets)
      - a filesystem path (treated the same as GOOGLE_APPLICATION_CREDENTIALS)
    """
    raw = os.environ.get("PLAY_CONSOLE_SA_KEY", "").strip()
    if raw:
        if raw.lstrip().startswith("{"):
            tf = tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False, prefix="play-sa-"
            )
            tf.write(raw)
            tf.flush()
            tf.close()
            return _AuthState(status="ok", sa_key_path=tf.name, _tempfile_handle=tf)
        if Path(raw).is_file():
            return _AuthState(status="ok", sa_key_path=raw)

    gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if gac and Path(gac).is_file():
        return _AuthState(status="ok", sa_key_path=gac)

    return _AuthState(status="missing")


# ---------------------------------------------------------------------------
# Play Reporting API client (thin wrapper around google-api-python-client)
# ---------------------------------------------------------------------------


class PlayVitalsClient:
    """Wrapper around `playdeveloperreporting.googleapis.com` v1beta1.

    Pulls the artifacts Frohike's drops have used since 2026-06-10:
      1. freshness (anomalies)
      2. crashRate 7d + prior 7d by versionCode (trend)
      3. anrRate 7d + prior 7d by versionCode (trend)
      4. errorCount 7d by reportType+issueId+versionCode (NAAS counts × ver)
      5. errorIssues:search top-N (cluster cause/location for NAAS predicate)
      6. crashRate 7d by countryCode (EU corroboration)
    """

    BASE = "https://playdeveloperreporting.googleapis.com/v1beta1"
    SCOPE = "https://www.googleapis.com/auth/playdeveloperreporting"

    def __init__(self, package_name: str, sa_key_path: str):
        self.package_name = package_name
        self.app_name = f"apps/{package_name}"
        self._sa_key_path = sa_key_path
        self._service = None

    def _build(self):
        if self._service is not None:
            return self._service
        # Lazy import — PARTIAL-no-creds path doesn't require these libs.
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        creds = service_account.Credentials.from_service_account_file(
            self._sa_key_path, scopes=[self.SCOPE]
        )
        self._service = build(
            "playdeveloperreporting", "v1beta1",
            credentials=creds, cache_discovery=False,
        )
        return self._service

    def pull_all(self, date: str) -> Dict[str, Any]:
        end = _parse_date(date)
        start = end - timedelta(days=7)
        prior_end = start
        prior_start = end - timedelta(days=14)
        svc = self._build()

        return {
            "date": date,
            "window": {
                "current_start": start.isoformat(),
                "current_end": end.isoformat(),
                "prior_start": prior_start.isoformat(),
                "prior_end": prior_end.isoformat(),
            },
            "freshness": _with_retry(lambda: self._freshness(svc)),
            "crash_rate_7d": _with_retry(lambda: self._rate_by_version(svc, "crashRateMetricSet", start, end)),
            "crash_rate_prior_7d": _with_retry(lambda: self._rate_by_version(svc, "crashRateMetricSet", prior_start, prior_end)),
            "anr_rate_7d": _with_retry(lambda: self._rate_by_version(svc, "anrRateMetricSet", start, end)),
            "anr_rate_prior_7d": _with_retry(lambda: self._rate_by_version(svc, "anrRateMetricSet", prior_start, prior_end)),
            "error_counts_by_issue_version": _with_retry(lambda: self._error_counts(svc, start, end)),
            "error_issues": _with_retry(lambda: self._search_error_issues(svc)),
            "crash_rate_by_country": _with_retry(lambda: self._rate_by_country(svc, "crashRateMetricSet", start, end)),
        }

    def _freshness(self, svc) -> Dict[str, Any]:
        try:
            return svc.anomalies().list(parent=self.app_name).execute()
        except Exception as exc:
            return {"_error": repr(exc)}

    # Map from the API resource-name segment (used in `name=apps/{app}/<seg>`)
    # to the chain of accessors on the v1beta1 discovery doc. The discovery
    # builder lowercases the first segment and nests `errorCountMetricSet`
    # under `vitals().errors().counts()` (not a flat `vitals().errorCountMetricSet()`).
    _METRIC_RESOURCE_PATH: Dict[str, Tuple[str, ...]] = {
        "crashRateMetricSet": ("vitals", "crashrate"),
        "anrRateMetricSet": ("vitals", "anrrate"),
        "errorCountMetricSet": ("vitals", "errors", "counts"),
    }

    def _metric_resource(self, svc, metric_set: str):
        try:
            path = self._METRIC_RESOURCE_PATH[metric_set]
        except KeyError as exc:
            raise ValueError(f"Unknown metric set: {metric_set!r}") from exc
        node = svc
        for accessor in path:
            node = getattr(node, accessor)()
        return node

    def _rate_by_version(self, svc, metric_set: str, start: date_cls, end: date_cls) -> Dict[str, Any]:
        metric = "userPerceivedCrashRate" if metric_set == "crashRateMetricSet" else "userPerceivedAnrRate"
        body = {
            "timelineSpec": {
                "aggregationPeriod": "DAILY",
                "startTime": _date_to_api_dt(start),
                "endTime": _date_to_api_dt(end),
            },
            "dimensions": ["versionCode"],
            "metrics": [metric, "distinctUsers"],
            "pageSize": 1000,
        }
        return self._metric_resource(svc, metric_set).query(
            name=f"{self.app_name}/{metric_set}", body=body,
        ).execute()

    def _rate_by_country(self, svc, metric_set: str, start: date_cls, end: date_cls) -> Dict[str, Any]:
        body = {
            "timelineSpec": {
                "aggregationPeriod": "DAILY",
                "startTime": _date_to_api_dt(start),
                "endTime": _date_to_api_dt(end),
            },
            "dimensions": ["countryCode"],
            "metrics": ["userPerceivedCrashRate", "distinctUsers"],
            "pageSize": 1000,
        }
        return self._metric_resource(svc, metric_set).query(
            name=f"{self.app_name}/{metric_set}", body=body,
        ).execute()

    def _error_counts(self, svc, start: date_cls, end: date_cls) -> Dict[str, Any]:
        body = {
            "timelineSpec": {
                "aggregationPeriod": "FULL_RANGE",
                "startTime": _date_to_api_dt(start),
                "endTime": _date_to_api_dt(end),
            },
            "dimensions": ["reportType", "issueId", "versionCode"],
            "metrics": ["errorReportCount", "distinctUsers"],
            "pageSize": 1000,
        }
        return self._metric_resource(svc, "errorCountMetricSet").query(
            name=f"{self.app_name}/errorCountMetricSet", body=body,
        ).execute()

    def _search_error_issues(self, svc, page_count: int = 6) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        token: Optional[str] = None
        for _ in range(page_count):
            params = {
                "parent": self.app_name,
                "pageSize": 25,
                "orderBy": "errorReportCount desc",
            }
            if token:
                params["pageToken"] = token
            resp = svc.vitals().errors().issues().search(**params).execute()
            rows.extend(resp.get("errorIssues", []))
            token = resp.get("nextPageToken")
            if not token:
                break
        return {"errorIssues": rows, "count": len(rows)}


def _with_retry(fn):
    """3 attempts with exponential backoff (Mulder §7). Retries on 5xx /
    transient network errors only. Auth / 4xx errors fail fast."""
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == RETRY_ATTEMPTS - 1:
                raise
            time.sleep(RETRY_BACKOFFS_S[attempt])
    if last_exc:  # pragma: no cover
        raise last_exc
    return None


def _is_retryable(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    if any(s in name for s in ("timeout", "connection", "socket", "transport")):
        return True
    status = getattr(exc, "status_code", None)
    if status is None and hasattr(exc, "resp"):
        resp = getattr(exc, "resp", None)
        if isinstance(resp, dict):
            status = resp.get("status")
    try:
        if status and int(status) >= 500:
            return True
    except (TypeError, ValueError):
        pass
    return False


# ---------------------------------------------------------------------------
# Transform / analysis
# ---------------------------------------------------------------------------


@dataclass
class _VersionRow:
    version_code: str
    naas_crashes: int = 0
    naas_anrs: int = 0
    app_crash_pct: Optional[float] = None
    app_anr_pct: Optional[float] = None
    users: Optional[int] = None
    is_ring_04xx: bool = False
    notes: str = ""


@dataclass
class _CountryRow:
    country_code: str
    app_crash_pct: float
    users: int


@dataclass
class _Analysis:
    naas_issues: List[Dict[str, Any]]
    total_naas_crashes: int
    total_naas_anrs: int
    affected_users_upper_bound: int
    app_crash_rate_pct: float
    app_anr_rate_pct: float
    app_crash_rate_prior_pct: float
    app_anr_rate_prior_pct: float
    per_version: List[_VersionRow]
    countries: List[_CountryRow]
    eu_aggregate_pct: float
    non_eu_aggregate_pct: float
    germany_pct: Optional[float]
    top_crashes: List[Dict[str, Any]]
    top_anrs: List[Dict[str, Any]]
    denominator_basis: str
    window: Dict[str, str]


def analyze(raw: Dict[str, Any]) -> _Analysis:
    """Pure transform: raw API responses → NAAS-attributed analysis."""
    window = raw.get("window", {})

    issues = raw.get("error_issues", {}).get("errorIssues", [])
    naas_issues = [iss for iss in issues if is_naas_issue(iss)]
    naas_issue_ids = {_issue_id(iss) for iss in naas_issues}
    naas_issue_ids.discard("")
    issue_type_by_id = {_issue_id(iss): _normalize_issue_type(iss) for iss in naas_issues if _issue_id(iss)}

    per_version: Dict[str, _VersionRow] = {}
    rows = raw.get("error_counts_by_issue_version", {}).get("rows", [])
    total_crashes = 0
    total_anrs = 0
    affected_users_ub = 0
    naas_issue_count_map: Dict[str, Dict[str, int]] = {}

    for row in rows:
        dims = _flatten_dims(row.get("dimensions", []))
        iid = dims.get("issueId")
        vcode = dims.get("versionCode")
        rtype = dims.get("reportType", "").upper()
        if iid not in naas_issue_ids:
            continue
        count = _metric_val(row, "errorReportCount")
        users = _metric_val(row, "distinctUsers")

        bucket = naas_issue_count_map.setdefault(iid, {"crashes": 0, "anrs": 0, "users": 0})
        if rtype == "CRASH":
            total_crashes += count
            bucket["crashes"] += count
        elif rtype in ("APPLICATION_NOT_RESPONDING", "ANR"):
            total_anrs += count
            bucket["anrs"] += count
        bucket["users"] += users
        affected_users_ub += users

        vrow = per_version.setdefault(vcode, _VersionRow(version_code=vcode))
        if rtype == "CRASH":
            vrow.naas_crashes += count
        elif rtype in ("APPLICATION_NOT_RESPONDING", "ANR"):
            vrow.naas_anrs += count

    crash_rates_7d = _aggregate_rate_by_version(raw.get("crash_rate_7d", {}), metric="userPerceivedCrashRate")
    anr_rates_7d = _aggregate_rate_by_version(raw.get("anr_rate_7d", {}), metric="userPerceivedAnrRate")
    for vcode, (rate, users) in crash_rates_7d.items():
        vrow = per_version.setdefault(vcode, _VersionRow(version_code=vcode))
        vrow.app_crash_pct = rate
        vrow.users = users
    for vcode, (rate, _users) in anr_rates_7d.items():
        vrow = per_version.setdefault(vcode, _VersionRow(version_code=vcode))
        vrow.app_anr_pct = rate

    app_crash = _user_weighted_app_rate(raw.get("crash_rate_7d", {}), "userPerceivedCrashRate")
    app_anr = _user_weighted_app_rate(raw.get("anr_rate_7d", {}), "userPerceivedAnrRate")
    app_crash_prior = _user_weighted_app_rate(raw.get("crash_rate_prior_7d", {}), "userPerceivedCrashRate")
    app_anr_prior = _user_weighted_app_rate(raw.get("anr_rate_prior_7d", {}), "userPerceivedAnrRate")

    for vrow in per_version.values():
        vrow.is_ring_04xx = is_04xx_ring(vrow.version_code)

    per_version_sorted = sorted(
        per_version.values(),
        key=lambda r: (r.naas_crashes + r.naas_anrs),
        reverse=True,
    )
    # Suppress rows with <5 NAAS events (per Frohike's prior drop convention)
    per_version_sorted = [r for r in per_version_sorted if (r.naas_crashes + r.naas_anrs) >= 5]

    top_crashes, top_anrs = _split_top_naas(naas_issues, naas_issue_count_map, issue_type_by_id)

    countries = _country_rows(raw.get("crash_rate_by_country", {}))
    eu_pct, non_eu_pct, germany_pct = _eu_aggregate(countries)

    return _Analysis(
        naas_issues=naas_issues,
        total_naas_crashes=total_crashes,
        total_naas_anrs=total_anrs,
        affected_users_upper_bound=affected_users_ub,
        app_crash_rate_pct=app_crash,
        app_anr_rate_pct=app_anr,
        app_crash_rate_prior_pct=app_crash_prior,
        app_anr_rate_prior_pct=app_anr_prior,
        per_version=per_version_sorted,
        countries=countries,
        eu_aggregate_pct=eu_pct,
        non_eu_aggregate_pct=non_eu_pct,
        germany_pct=germany_pct,
        top_crashes=top_crashes,
        top_anrs=top_anrs,
        denominator_basis="whole_app_sessions",
        window=window,
    )


# ---------------------------------------------------------------------------
# NAAS attribution helpers (public for tests)
# ---------------------------------------------------------------------------


def is_naas_issue(issue: Dict[str, Any]) -> bool:
    """Apply the NAAS attribution predicate to an issue cluster."""
    cause = (issue.get("cause") or "").lower()
    location = (issue.get("location") or "").lower()
    blob = f"{cause} {location}"
    return any(tok in blob for tok in NAAS_ATTRIBUTION_TOKENS)


def is_04xx_ring(version_code: str) -> bool:
    """`.04xx` ring detector. Version codes embed the build suffix:
    `1.0.9003.0401` → `900300412` (arm64 ABI suffix `2`)."""
    if not version_code or len(version_code) < 6 or not version_code.isdigit():
        return False
    suffix = version_code[-4:-1]  # strip ABI digit, take next 3
    return suffix.startswith("04")


def _normalize_issue_type(issue: Dict[str, Any]) -> str:
    t = (issue.get("type") or "").upper()
    if t in ("APPLICATION_NOT_RESPONDING", "ANR"):
        return "ANR"
    if t == "CRASH":
        return "CRASH"
    return t or "UNKNOWN"


def _issue_id(issue: Dict[str, Any]) -> str:
    name = issue.get("name", "")
    if "/" in name:
        return name.rsplit("/", 1)[-1]
    return issue.get("issueId", "")


# ---------------------------------------------------------------------------
# Numeric aggregation helpers
# ---------------------------------------------------------------------------


def _flatten_dims(dims: List[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for d in dims:
        key = d.get("dimension") or d.get("name")
        val = d.get("stringValue") or d.get("int64Value") or d.get("value") or ""
        if key:
            out[key] = str(val)
    return out


def _metric_val(row: Dict[str, Any], metric_name: str) -> int:
    for m in row.get("metrics", []):
        if m.get("metric") == metric_name or m.get("name") == metric_name:
            for k in ("decimalValue", "int64Value", "doubleValue", "value"):
                if k in m:
                    v = m[k]
                    if isinstance(v, dict):
                        v = v.get("value", 0)
                    try:
                        return int(float(v))
                    except (TypeError, ValueError):
                        return 0
    return 0


def _metric_float(row: Dict[str, Any], metric_name: str) -> float:
    for m in row.get("metrics", []):
        if m.get("metric") == metric_name or m.get("name") == metric_name:
            for k in ("doubleValue", "decimalValue", "value"):
                if k in m:
                    v = m[k]
                    if isinstance(v, dict):
                        v = v.get("value", 0)
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return 0.0
    return 0.0


def _aggregate_rate_by_version(payload: Dict[str, Any], metric: str) -> Dict[str, Tuple[float, int]]:
    acc: Dict[str, List[Tuple[float, int]]] = {}
    for row in payload.get("rows", []):
        dims = _flatten_dims(row.get("dimensions", []))
        vcode = dims.get("versionCode")
        if not vcode:
            continue
        rate = _metric_float(row, metric)
        users = _metric_val(row, "distinctUsers")
        acc.setdefault(vcode, []).append((rate, users))
    out: Dict[str, Tuple[float, int]] = {}
    for vcode, samples in acc.items():
        total_users = sum(u for _, u in samples) or 1
        weighted = sum(r * u for r, u in samples) / total_users
        peak = max(u for _, u in samples)
        out[vcode] = (weighted * 100, peak)
    return out


def _user_weighted_app_rate(payload: Dict[str, Any], metric: str) -> float:
    total_rate_users = 0.0
    total_users = 0
    for row in payload.get("rows", []):
        rate = _metric_float(row, metric)
        users = _metric_val(row, "distinctUsers")
        total_rate_users += rate * users
        total_users += users
    if total_users == 0:
        return 0.0
    return (total_rate_users / total_users) * 100


def _country_rows(payload: Dict[str, Any]) -> List[_CountryRow]:
    by_country: Dict[str, List[Tuple[float, int]]] = {}
    for row in payload.get("rows", []):
        dims = _flatten_dims(row.get("dimensions", []))
        cc = dims.get("countryCode")
        if not cc:
            continue
        rate = _metric_float(row, "userPerceivedCrashRate")
        users = _metric_val(row, "distinctUsers")
        by_country.setdefault(cc, []).append((rate, users))
    rows: List[_CountryRow] = []
    for cc, samples in by_country.items():
        total_users = sum(u for _, u in samples) or 1
        weighted = sum(r * u for r, u in samples) / total_users
        peak = max(u for _, u in samples)
        rows.append(_CountryRow(country_code=cc, app_crash_pct=weighted * 100, users=peak))
    rows.sort(key=lambda r: r.app_crash_pct, reverse=True)
    return rows


def _eu_aggregate(countries: List[_CountryRow]) -> Tuple[float, float, Optional[float]]:
    eu_w, eu_u, non_w, non_u = 0.0, 0, 0.0, 0
    germany: Optional[float] = None
    for c in countries:
        if c.country_code == "DE":
            germany = c.app_crash_pct
        if c.country_code in EU_COUNTRIES:
            eu_w += c.app_crash_pct * c.users
            eu_u += c.users
        else:
            non_w += c.app_crash_pct * c.users
            non_u += c.users
    eu_pct = (eu_w / eu_u) if eu_u else 0.0
    non_pct = (non_w / non_u) if non_u else 0.0
    return eu_pct, non_pct, germany


def _split_top_naas(
    naas_issues: List[Dict[str, Any]],
    counts: Dict[str, Dict[str, int]],
    issue_type: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    enriched: List[Dict[str, Any]] = []
    for iss in naas_issues:
        iid = _issue_id(iss)
        c = counts.get(iid, {"crashes": 0, "anrs": 0, "users": 0})
        enriched.append({
            "issue_id": iid,
            "type": issue_type.get(iid, _normalize_issue_type(iss)),
            "cause": iss.get("cause") or "",
            "location": iss.get("location") or "",
            "sample_stack": iss.get("sampleStackTrace") or iss.get("sampleErrorReport", ""),
            "report_count_7d": c["crashes"] + c["anrs"],
            "distinct_users": c["users"],
        })
    crashes = sorted([e for e in enriched if e["type"] == "CRASH"],
                     key=lambda e: e["report_count_7d"], reverse=True)[:5]
    anrs = sorted([e for e in enriched if e["type"] == "ANR"],
                  key=lambda e: e["report_count_7d"], reverse=True)[:5]
    return crashes, anrs


# ---------------------------------------------------------------------------
# Cross-section ctx parsing
# ---------------------------------------------------------------------------


def _live_version_from_ctx(ctx: Dict[str, Any]) -> Optional[str]:
    """Read Langly's published live Play Store version from ctx."""
    pr = ctx.get("prior_results") or {}
    if not pr:
        return None
    res: Any = None
    for k in (Section.LANGLY_VERSION, "langly_version", Section.LANGLY_VERSION.value):
        if k in pr:
            res = pr[k]
            break
    if res is None:
        return None
    md = getattr(res, "metadata", None) or getattr(res, "data", None)
    if not md:
        return None
    return md.get("live_play_version") or md.get("version")


# ---------------------------------------------------------------------------
# Markdown renderers — report section + drop file
# ---------------------------------------------------------------------------


SECTION_TABLE_HEADER = (
    "| Defender version | NAAS Crashes | NAAS ANRs | App CR% (7d) | App ANR% (7d) | Users 7d | Notes |"
)
SECTION_TABLE_SEP = "|---|---:|---:|---:|---:|---:|---|"

# Number of columns in the per-version table; tested against the 06-10 shape.
SECTION_TABLE_COLUMN_COUNT = 7


def render_section_markdown(
    date: str,
    a: _Analysis,
    live_play_version: Optional[str] = None,
) -> str:
    """Render the daily-report section. Shape matches 2026-06-10 template."""
    w = a.window
    rate_window = f"{w.get('current_start', '?')} → {w.get('current_end', '?')}"

    lines: List[str] = []
    lines.append(
        f"### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit, 7d `{rate_window}`)"
    )
    lines.append("")

    # --- Headline table
    lines.append("| Metric | Value | Denominator | Readout |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| NAAS crash reports (7d in-window) | **{a.total_naas_crashes:,}** | "
        f"Sum of `errorReportCount` over {len(a.naas_issues)} NAAS-attributed issue clusters | "
        f"{len(a.naas_issues)} NAAS issues identified |"
    )
    lines.append(
        f"| NAAS ANR reports (7d in-window) | **{a.total_naas_anrs:,}** | Same | "
        f"ANR long-tail concentrated in OpenVPN init |"
    )
    lines.append(
        f"| Affected users (upper bound) | **{a.affected_users_upper_bound:,}** | "
        f"Sum of `distinctUsers` across {len(a.naas_issues)} NAAS issues (NOT cross-issue deduped) | "
        f"True unique-user count is lower |"
    )
    crash_emoji = "✅" if a.app_crash_rate_pct < GOOGLE_CRASH_THRESHOLD_PCT else "🔴"
    anr_emoji = "✅" if a.app_anr_rate_pct < GOOGLE_ANR_THRESHOLD_PCT else "🔴"
    lines.append(
        f"| **App user-perceived crash rate (whole-app, 7d, user-weighted)** | "
        f"**{a.app_crash_rate_pct:.4f}%** | All `com.microsoft.scmx` Android sessions in window | "
        f"{crash_emoji} {'Below' if a.app_crash_rate_pct < GOOGLE_CRASH_THRESHOLD_PCT else 'Over'} "
        f"Google bad-behavior threshold {GOOGLE_CRASH_THRESHOLD_PCT}% |"
    )
    lines.append(
        f"| **App user-perceived ANR rate (whole-app, 7d, user-weighted)** | "
        f"**{a.app_anr_rate_pct:.4f}%** | Same | "
        f"{anr_emoji} {'Below' if a.app_anr_rate_pct < GOOGLE_ANR_THRESHOLD_PCT else 'Over'} "
        f"Google bad-behavior threshold {GOOGLE_ANR_THRESHOLD_PCT}% |"
    )
    d_crash = a.app_crash_rate_pct - a.app_crash_rate_prior_pct
    d_anr = a.app_anr_rate_pct - a.app_anr_rate_prior_pct
    rel_crash = (d_crash / a.app_crash_rate_prior_pct * 100) if a.app_crash_rate_prior_pct else 0.0
    rel_anr = (d_anr / a.app_anr_rate_prior_pct * 100) if a.app_anr_rate_prior_pct else 0.0
    lines.append(
        f"| Δ crash rate vs prior 7d | **{a.app_crash_rate_pct:.4f}% vs {a.app_crash_rate_prior_pct:.4f}%** "
        f"({d_crash:+.3f}pp / {rel_crash:+.1f}% rel) | App-level | "
        f"{'⬆️ Uptick' if d_crash > 0 else '⬇️ Down'} |"
    )
    lines.append(
        f"| Δ ANR rate vs prior 7d | **{a.app_anr_rate_pct:.4f}% vs {a.app_anr_rate_prior_pct:.4f}%** "
        f"({d_anr:+.3f}pp / {rel_anr:+.1f}% rel) | App-level | "
        f"{'⬆️ Uptick' if d_anr > 0 else '⬇️ Down'} |"
    )
    lines.append(
        "| Tenant attribution | **Not derivable from Play** | — | "
        "Play Vitals exposes no tenant cut — use Scully for tenant slicing |"
    )
    lines.append("")
    lines.append(
        "> **Denominator framing rule:** \"NAAS crash/ANR\" are **counts**, not rates. "
        "Play does not publish a NAAS-using-session denominator; only Scully's "
        "`TunnelServerOperationEvents` carries it. The two user-perceived rates above are "
        "app-wide, NOT NAAS-only."
    )
    lines.append("")

    # --- Per-version PRIMARY table
    lines.append("### Per-Defender-version NAAS table (PRIMARY)")
    lines.append("")
    lines.append(SECTION_TABLE_HEADER)
    lines.append(SECTION_TABLE_SEP)
    for r in a.per_version:
        label = _format_version_label(
            r.version_code, ring=r.is_ring_04xx, live=live_play_version,
        )
        cr = "n/a — sub-threshold" if r.app_crash_pct is None else f"{r.app_crash_pct:.4f}%"
        ar = "n/a" if r.app_anr_pct is None else f"{r.app_anr_pct:.4f}%"
        users = f"{r.users:,}" if r.users else "<500"
        lines.append(
            f"| {label} | {r.naas_crashes:,} | {r.naas_anrs:,} | {cr} | {ar} | {users} | {r.notes} |"
        )
    lines.append("")

    # --- Top NAAS crashes (top 3)
    lines.append("### Top NAAS crashes (top 3; full root-cause depth in Frohike's drop)")
    lines.append("")
    lines.append("| # | Cluster cause / location | 7d reports | Affected users | Root-cause hypothesis |")
    lines.append("|---:|---|---:|---:|---|")
    for i, c in enumerate(a.top_crashes[:3], 1):
        cause = (c["cause"] or "?")[:80]
        loc = (c["location"] or "?")[:80]
        lines.append(
            f"| {i} | `{cause}` / `{loc}` | **{c['report_count_7d']:,}** | "
            f"{c['distinct_users']:,} | See drop file (`{c['issue_id'][:10]}…`) |"
        )
    lines.append("")

    # --- Top NAAS ANRs (top 3)
    lines.append("### Top NAAS ANRs (top 3; full table in Frohike's drop)")
    lines.append("")
    lines.append("| # | Cluster cause / location | 7d reports | Affected users | Root-cause hypothesis |")
    lines.append("|---:|---|---:|---:|---|")
    for i, c in enumerate(a.top_anrs[:3], 1):
        cause = (c["cause"] or "?")[:80]
        loc = (c["location"] or "?")[:80]
        lines.append(
            f"| {i} | `{cause}` / `{loc}` | **{c['report_count_7d']:,}** | "
            f"{c['distinct_users']:,} | See drop file (`{c['issue_id'][:10]}…`) |"
        )
    lines.append("")

    # --- Country breakdown for EU corroboration
    lines.append("### Affected users / regions")
    lines.append("")
    lines.append(
        f"- **Affected NAAS users (upper bound):** {a.affected_users_upper_bound:,} over 7d "
        f"(across {len(a.naas_issues)} NAAS issues, not deduplicated cross-issue)."
    )
    if a.germany_pct is not None:
        de_emoji = "🔴" if a.germany_pct > GOOGLE_CRASH_THRESHOLD_PCT else "🟡"
        de_verb = "OVER" if a.germany_pct > GOOGLE_CRASH_THRESHOLD_PCT else "below"
        lines.append(
            f"- **{de_emoji} Germany whole-app crash rate: {a.germany_pct:.4f}%** — "
            f"{de_verb} Google's {GOOGLE_CRASH_THRESHOLD_PCT}% Play Console bad-behavior threshold."
        )
    if a.eu_aggregate_pct and a.non_eu_aggregate_pct:
        ratio = a.eu_aggregate_pct / a.non_eu_aggregate_pct if a.non_eu_aggregate_pct else 0
        lines.append(
            f"- **EU aggregate (whole-app, 7d, user-weighted): {a.eu_aggregate_pct:.3f}% vs "
            f"non-EU {a.non_eu_aggregate_pct:.3f}% — {ratio:.1f}× lift.**"
        )
    lines.append(
        "- Caveat: country-level rates are whole-app, NOT NAAS-only. EU correlation with "
        "Scully's NAAS server-side EU intensification is **same-shape** but Play cannot prove "
        "NAAS-attribution at country level — Scully NAAS-tenant-by-region cut still owed."
    )
    lines.append("")
    return "\n".join(lines)


def render_drop_file_markdown(
    date: str,
    a: _Analysis,
    raw: Dict[str, Any],
    live_play_version: Optional[str] = None,
) -> str:
    w = a.window
    lines: List[str] = []
    lines.append(
        f"# NAAS Android Client Stability — {w.get('current_start', '?')} → {w.get('current_end', '?')}"
    )
    lines.append(
        "**Author:** Frohike (Play Vitals Analyst), automated via "
        "`tools/report_generator/sections/frohike_play_vitals.py`"
    )
    lines.append("**Source:** Google Play Developer Reporting API v1beta1 (service-account auth)")
    lines.append(f"**Package:** `{PACKAGE_NAME}`")
    if live_play_version:
        lines.append(f"**Live Play Store version (per Langly):** `{live_play_version}`")
    lines.append("**NAAS attribution predicate (issue-cluster level):**")
    lines.append("```text")
    lines.append("NAAS predicate: lower(cause || ' ' || location) contains any of")
    lines.append("  " + ", ".join(NAAS_ATTRIBUTION_TOKENS))
    lines.append(f"→ {len(a.naas_issues)} NAAS issues identified")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Headline + Per-Version Table (mirrors report section)")
    lines.append("")
    lines.append(render_section_markdown(date, a, live_play_version=live_play_version))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Top NAAS issues — full detail")
    lines.append("")
    for kind, lst in (("Crashes", a.top_crashes), ("ANRs", a.top_anrs)):
        lines.append(f"### {kind}")
        lines.append("")
        for i, c in enumerate(lst, 1):
            lines.append(f"#### {i}. `{c['issue_id']}`")
            lines.append(f"- **Cause:** `{c['cause']}`")
            lines.append(f"- **Location:** `{c['location']}`")
            lines.append(f"- **7d reports:** {c['report_count_7d']:,}")
            lines.append(f"- **Affected users (issue-local):** {c['distinct_users']:,}")
            stack = c.get("sample_stack", "")
            if stack:
                lines.append("- **Sample stack:**")
                lines.append("```")
                lines.append(str(stack)[:2000])
                lines.append("```")
            lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Country breakdown (whole-app rate, top 25)")
    lines.append("")
    lines.append("| Country | App CR% (7d) | Users 7d |")
    lines.append("|---|---:|---:|")
    for c in a.countries[:25]:
        lines.append(f"| {c.country_code} | {c.app_crash_pct:.4f}% | {c.users:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Raw API payload manifest")
    lines.append("")
    for k, v in raw.items():
        size = len(v) if isinstance(v, (list, dict, str)) else "?"
        lines.append(f"- `{k}` (size: {size})")
    lines.append("")
    return "\n".join(lines)


def _format_version_label(
    version_code: str,
    ring: bool = False,
    live: Optional[str] = None,
) -> str:
    """Convert `900200122` → `1.0.9002.0102` and tag rings / live prod.

    Version-code layout (per canonical google-play-vitals SKILL.md):
      MMMM XYZW A   (9 digits)
      ^^^^      = build major (e.g. 9002)
           XYZW = build minor in encoded order
                ^ = ABI digit (2 = arm64)
    Label minor is decoded as `X Z Y W` (swap positions 1 and 2):
      870300112 → body 87030011 → major 8703, enc 0011 → minor 0101 → 1.0.8703.0101
      860200122 → body 86020012 → major 8602, enc 0012 → minor 0102 → 1.0.8602.0102
      900300412 → body 90030041 → major 9003, enc 0041 → minor 0401 → 1.0.9003.0401
    """
    label = version_code
    try:
        if version_code.isdigit() and len(version_code) == 9:
            body = version_code[:-1]  # strip ABI digit
            major = body[:4]
            enc = body[4:]            # 4 digits, encoded minor
            minor = enc[0] + enc[2] + enc[1] + enc[3]
            label = f"1.0.{major}.{minor}"
    except Exception:
        label = version_code

    is_live = live is not None and (label == live or version_code == live)

    if is_live and ring:
        return f"🔴 `{label}` **(.04xx INTERNAL RING)** ⚠️ also flagged live?"
    if is_live:
        return f"`{label}` ✅ **LIVE PROD**"
    if ring:
        return f"🔴 `{label}` **(.04xx INTERNAL RING)**"
    return f"`{label}`"


# ---------------------------------------------------------------------------
# Drop file write + grading + outcome helpers
# ---------------------------------------------------------------------------


def _write_drop_file(drop_dir: Path, date: str, content: str) -> Path:
    drop_dir.mkdir(parents=True, exist_ok=True)
    target = drop_dir / f"naas-crashes-{date}.md"
    # Idempotent overwrite — re-run for same date replaces, does not append.
    target.write_text(content, encoding="utf-8")
    return target


def _grade(a: _Analysis, errors: List[str]) -> Status:
    if errors:
        return Status.PARTIAL
    if not a.naas_issues:
        return Status.PARTIAL
    return Status.GO


def _partial_no_creds(date: str, drop_dir: Path, started: float) -> SectionResult:
    stub_md = (
        "### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)\n\n"
        "_⚠️ Play Vitals data unavailable — `PLAY_CONSOLE_SA_KEY` secret not configured. "
        "See `.squad/decisions/inbox/frohike-play-vitals-onboarding.md`._\n"
    )
    try:
        _write_drop_file(
            drop_dir, date,
            f"# NAAS Crashes — {date}\n\n"
            "**PARTIAL — no Play Console credentials available in this environment.**\n\n"
            "Set `PLAY_CONSOLE_SA_KEY` (JSON contents or path) or "
            "`GOOGLE_APPLICATION_CREDENTIALS` (path) to unblock.\n\n"
            "See `.squad/decisions/inbox/frohike-play-vitals-onboarding.md` for provisioning steps.\n",
        )
    except Exception:
        pass
    return SectionResult(
        section=Section.FROHIKE_PLAY_VITALS,
        status=Status.PARTIAL,
        markdown=stub_md,
        metadata={"skip_reason": "no_play_console_credentials"},
        denominators={"denominator_basis": "n/a — no credentials"},
        errors=["PLAY_CONSOLE_SA_KEY and GOOGLE_APPLICATION_CREDENTIALS both unset"],
        drop_path=str(drop_dir / f"naas-crashes-{date}.md"),
        elapsed_s=round(time.monotonic() - started, 3),
    )


def _skip_result(date: str, reason: str, drop_dir: Path, started: float) -> SectionResult:
    md = (
        "### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)\n\n"
        f"_⏭️ Frohike section skipped this run ({reason})._\n"
    )
    try:
        _write_drop_file(
            drop_dir, date,
            f"# NAAS Crashes — {date}\n\n**SKIPPED.** Reason: `{reason}`.\n",
        )
    except Exception:
        pass
    return SectionResult(
        section=Section.FROHIKE_PLAY_VITALS,
        status=Status.SKIP,
        markdown=md,
        metadata={"skip_reason": reason},
        denominators={"denominator_basis": "n/a — skipped"},
        errors=[],
        drop_path=str(drop_dir / f"naas-crashes-{date}.md"),
        elapsed_s=round(time.monotonic() - started, 3),
    )


def _fail_result(
    date: str, reason: str, errors: List[str],
    drop_dir: Path, started: float, tb: str = "",
) -> SectionResult:
    md = (
        "### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)\n\n"
        f"_🔴 Play Vitals data unavailable — {reason}_\n"
    )
    try:
        _write_drop_file(
            drop_dir, date,
            f"# NAAS Crashes — {date}\n\n**FAILED.** {reason}\n\n"
            f"Errors:\n```\n{json.dumps(errors, indent=2)}\n```\n\n"
            + (f"Traceback:\n```\n{tb}\n```\n" if tb else ""),
        )
    except Exception:
        pass
    return SectionResult(
        section=Section.FROHIKE_PLAY_VITALS,
        status=Status.FAIL,
        markdown=md,
        metadata={"failure_reason": reason},
        denominators={"denominator_basis": "n/a — pull failed"},
        errors=errors,
        drop_path=str(drop_dir / f"naas-crashes-{date}.md"),
        elapsed_s=round(time.monotonic() - started, 3),
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _parse_date(s: str) -> date_cls:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _date_to_api_dt(d: date_cls) -> Dict[str, int]:
    return {"year": d.year, "month": d.month, "day": d.day}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frohike_play_vitals",
        description="Produce the Frohike NAAS-as-a-unit Play Vitals section.",
    )
    parser.add_argument(
        "--date", required=True,
        help="Report date (YYYY-MM-DD). 7d analysis window is date-7d ..= date-1d.",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=("DEBUG", "INFO", "WARN", "ERROR"),
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    result = produce(args.date)
    sys.stdout.write(result.markdown)
    sys.stdout.write("\n")
    sys.stderr.write(
        f"[frohike_play_vitals] status={result.status.value} "
        f"errors={len(result.errors)} "
        f"naas_crashes={result.metadata.get('naas_crash_count', 'n/a')} "
        f"naas_anrs={result.metadata.get('naas_anr_count', 'n/a')} "
        f"drop={result.drop_path}\n"
    )
    return 0 if result.status != Status.FAIL else 2


if __name__ == "__main__":
    raise SystemExit(main())
