"""Tests for the Frohike Play Vitals section producer.

Run from the repo root:
    python -m pytest tools/report_generator/sections/tests/test_frohike_play_vitals.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.report_generator.contracts import Section, Status  # noqa: E402
from tools.report_generator.sections import frohike_play_vitals as fpv  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _empty_raw(date: str = "2026-06-10") -> Dict[str, Any]:
    """Empty but well-formed Play API response shape."""
    return {
        "date": date,
        "window": {
            "current_start": "2026-06-03",
            "current_end": "2026-06-10",
            "prior_start": "2026-05-27",
            "prior_end": "2026-06-03",
        },
        "freshness": {},
        "crash_rate_7d": {"rows": []},
        "crash_rate_prior_7d": {"rows": []},
        "anr_rate_7d": {"rows": []},
        "anr_rate_prior_7d": {"rows": []},
        "error_counts_by_issue_version": {"rows": []},
        "error_issues": {"errorIssues": []},
        "crash_rate_by_country": {"rows": []},
    }


def _row(dims: Dict[str, str], metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dimensions": [{"dimension": k, "stringValue": v} for k, v in dims.items()],
        "metrics": [{"metric": k, "decimalValue": v} for k, v in metrics.items()],
    }


def _populated_raw(date: str = "2026-06-10") -> Dict[str, Any]:
    """A realistic mini-dataset covering NAAS attribution, .04xx ring, and EU."""
    raw = _empty_raw(date)
    raw["error_issues"]["errorIssues"] = [
        {
            "name": "apps/com.microsoft.scmx/errorIssues/iss-vpn-1",
            "issueId": "iss-vpn-1",
            "type": "CRASH",
            "cause": "ForegroundServiceDidNotStartInTimeException",
            "location": "com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand",
            "sampleStackTrace": "android.app.RemoteServiceException...\nat VpnServiceOrchestrator.onStartCommand",
        },
        {
            "name": "apps/com.microsoft.scmx/errorIssues/iss-openvpn-1",
            "issueId": "iss-openvpn-1",
            "type": "APPLICATION_NOT_RESPONDING",
            "cause": "ANR slow main thread",
            "location": "com.microsoft.scmx.vpn.openvpn.BaseOpenVpnClient.initialize",
            "sampleStackTrace": "dlopen → BaseOpenVpnClient.initialize",
        },
        {
            "name": "apps/com.microsoft.scmx/errorIssues/iss-notnaas-1",
            "issueId": "iss-notnaas-1",
            "type": "CRASH",
            "cause": "NullPointerException",
            "location": "com.microsoft.scmx.dashboard.MainActivity.onCreate",
            "sampleStackTrace": "MainActivity.onCreate",
        },
    ]
    raw["error_counts_by_issue_version"]["rows"] = [
        _row({"reportType": "CRASH", "issueId": "iss-vpn-1", "versionCode": "900200122"},
             {"errorReportCount": 2878, "distinctUsers": 475}),
        _row({"reportType": "APPLICATION_NOT_RESPONDING", "issueId": "iss-openvpn-1", "versionCode": "900200122"},
             {"errorReportCount": 1244, "distinctUsers": 1202}),
        _row({"reportType": "CRASH", "issueId": "iss-vpn-1", "versionCode": "900300412"},
             {"errorReportCount": 95, "distinctUsers": 80}),
        _row({"reportType": "CRASH", "issueId": "iss-notnaas-1", "versionCode": "900200122"},
             {"errorReportCount": 99999, "distinctUsers": 99999}),  # excluded
    ]
    raw["crash_rate_7d"]["rows"] = [
        _row({"versionCode": "900200122"},
             {"userPerceivedCrashRate": 0.006025, "distinctUsers": 187000}),
    ]
    raw["anr_rate_7d"]["rows"] = [
        _row({"versionCode": "900200122"},
             {"userPerceivedAnrRate": 0.001908, "distinctUsers": 187000}),
    ]
    raw["crash_rate_prior_7d"]["rows"] = [
        _row({"versionCode": "900200122"},
             {"userPerceivedCrashRate": 0.005800, "distinctUsers": 184000}),
    ]
    raw["anr_rate_prior_7d"]["rows"] = [
        _row({"versionCode": "900200122"},
             {"userPerceivedAnrRate": 0.001800, "distinctUsers": 184000}),
    ]
    raw["crash_rate_by_country"]["rows"] = [
        _row({"countryCode": "DE"},
             {"userPerceivedCrashRate": 0.0325, "distinctUsers": 29000}),
        _row({"countryCode": "US"},
             {"userPerceivedCrashRate": 0.004, "distinctUsers": 100000}),
    ]
    return raw


class _FakeClient:
    def __init__(self, raw: Dict[str, Any]):
        self._raw = raw
        self.calls = 0

    def pull_all(self, date: str) -> Dict[str, Any]:
        self.calls += 1
        return self._raw


# ---------------------------------------------------------------------------
# 1. Required test: no creds → PARTIAL with onboarding stub
# ---------------------------------------------------------------------------


def test_produce_skip_when_no_creds(monkeypatch, tmp_path):
    """Spec required this test name. Implementation returns Status.PARTIAL
    (not SKIP) to conform with Mulder §4 ("auth not configured" → PARTIAL).
    The stub markdown and onboarding pointer are still asserted."""
    monkeypatch.delenv("PLAY_CONSOLE_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("REPORT_GENERATOR_SKIP_FROHIKE", raising=False)

    result = fpv.produce("2026-06-10", ctx={"drop_dir": tmp_path})
    assert result.section == Section.FROHIKE_PLAY_VITALS
    assert result.status == Status.PARTIAL  # per Mulder §4 ("auth not configured" → PARTIAL)
    assert "Play Vitals data unavailable" in result.markdown
    assert "PLAY_CONSOLE_SA_KEY" in result.markdown
    assert "frohike-play-vitals-onboarding" in result.markdown
    # Drop file is mandatory even on PARTIAL (Mulder §2 rule 4)
    drop = tmp_path / "naas-crashes-2026-06-10.md"
    assert drop.exists()
    assert "PARTIAL" in drop.read_text()


def test_produce_skip_when_env_var_set(monkeypatch, tmp_path):
    """Explicit SKIP path — `REPORT_GENERATOR_SKIP_FROHIKE=1` short-circuits."""
    monkeypatch.setenv("REPORT_GENERATOR_SKIP_FROHIKE", "1")
    result = fpv.produce("2026-06-10", ctx={"drop_dir": tmp_path})
    assert result.status == Status.SKIP
    assert "skipped" in result.markdown.lower()


# ---------------------------------------------------------------------------
# 2. Required test: NAAS attribution filter (include / exclude)
# ---------------------------------------------------------------------------


def test_naas_attribution_filter_include_vpn_orchestrator():
    """Issue with `VpnServiceOrchestrator` in location → included."""
    iss = {
        "cause": "ForegroundServiceDidNotStartInTimeException",
        "location": "com.microsoft.scmx.vpn.VpnServiceOrchestrator.onStartCommand",
    }
    assert fpv.is_naas_issue(iss) is True


def test_naas_attribution_filter_include_libnaas():
    """Native NAAS lib SIGSEGV → included."""
    iss = {
        "cause": "SIGSEGV",
        "location": "[base.apk!libnaas_native_vpn.so]",
    }
    assert fpv.is_naas_issue(iss) is True


def test_naas_attribution_filter_exclude_non_naas():
    """Non-NAAS dashboard crash → excluded."""
    iss = {
        "cause": "NullPointerException",
        "location": "com.microsoft.scmx.dashboard.MainActivity.onCreate",
    }
    assert fpv.is_naas_issue(iss) is False


def test_naas_attribution_filter_case_insensitive():
    iss = {"cause": "VPNSERVICEORCHESTRATOR died", "location": ""}
    assert fpv.is_naas_issue(iss) is True


def test_analyze_filters_non_naas_issues(tmp_path):
    """End-to-end: non-NAAS issue's errorReportCount is NOT in totals."""
    raw = _populated_raw()
    analysis = fpv.analyze(raw)
    # 2 NAAS issues (vpn + openvpn), 1 excluded
    assert len(analysis.naas_issues) == 2
    # Crashes from NAAS only: 2878 + 95 = 2973 (the 99999 non-NAAS row excluded)
    assert analysis.total_naas_crashes == 2878 + 95
    assert analysis.total_naas_anrs == 1244


# ---------------------------------------------------------------------------
# 3. Required test: markdown shape matches the 2026-06-10 report template
# ---------------------------------------------------------------------------


def test_markdown_shape_matches_06_10_template(tmp_path):
    raw = _populated_raw()
    analysis = fpv.analyze(raw)
    md = fpv.render_section_markdown("2026-06-10", analysis)

    # Section header (matches the daily report's H3 exactly in shape)
    assert "### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit," in md

    # Headline table header (4 columns) — per 06-10 line 52
    assert "| Metric | Value | Denominator | Readout |" in md

    # Per-Defender-version PRIMARY table — per 06-10 line 81; 7-column shape
    assert "### Per-Defender-version NAAS table (PRIMARY)" in md
    assert fpv.SECTION_TABLE_HEADER in md
    # Column count = 7 columns (8 pipes including the leading + trailing)
    assert fpv.SECTION_TABLE_HEADER.count("|") == fpv.SECTION_TABLE_COLUMN_COUNT + 1

    # Top NAAS crashes / ANRs sub-tables
    assert "### Top NAAS crashes" in md
    assert "### Top NAAS ANRs" in md

    # Country / EU breakdown block
    assert "### Affected users / regions" in md
    assert "Germany" in md  # populated raw has DE row

    # Denominator framing rule blockquote (HARD per charter)
    assert "Denominator framing rule" in md
    assert "NOT NAAS-only" in md


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_is_04xx_ring_detection():
    assert fpv.is_04xx_ring("900300412") is True   # 1.0.9003.0401
    assert fpv.is_04xx_ring("892100412") is True
    assert fpv.is_04xx_ring("900200122") is False  # 1.0.9002.0102 — production
    assert fpv.is_04xx_ring("") is False
    assert fpv.is_04xx_ring("abc") is False


def test_produce_end_to_end_with_fake_client(tmp_path):
    """Full produce() path with mocked client; status=GO; metadata populated."""
    raw = _populated_raw()
    client = _FakeClient(raw)
    result = fpv.produce(
        "2026-06-10",
        ctx={"client": client, "drop_dir": tmp_path},
    )
    assert result.section == Section.FROHIKE_PLAY_VITALS
    assert result.status == Status.GO
    assert result.metadata["naas_crash_count"] == 2878 + 95
    assert result.metadata["naas_anr_count"] == 1244
    assert result.metadata["naas_issue_count"] == 2
    assert result.denominators["denominator_basis"] == "whole_app_sessions"
    assert client.calls == 1

    # Drop file written + idempotent (re-run replaces, no double-append)
    drop_path = Path(result.drop_path)
    assert drop_path.exists()
    first_size = drop_path.stat().st_size
    result2 = fpv.produce(
        "2026-06-10",
        ctx={"client": _FakeClient(raw), "drop_dir": tmp_path},
    )
    second_size = Path(result2.drop_path).stat().st_size
    assert first_size == second_size, "drop file should overwrite, not append"


def test_produce_fail_soft_on_client_exception(tmp_path):
    """A pulling exception is captured → Status.FAIL, no propagation."""
    class _BoomClient:
        def pull_all(self, date):
            raise RuntimeError("simulated 503")

    result = fpv.produce(
        "2026-06-10",
        ctx={"client": _BoomClient(), "drop_dir": tmp_path},
    )
    assert result.status == Status.FAIL
    assert any("pull_all_failed" in e for e in result.errors)
    # Drop stub written even on FAIL (Mulder §2 rule 4)
    assert Path(result.drop_path).exists()
    assert "FAILED" in Path(result.drop_path).read_text()


def test_live_prod_tag_uses_langly_metadata(tmp_path):
    """When Langly's prior_result names live_play_version, that row gets ✅ LIVE PROD."""
    raw = _populated_raw()
    analysis = fpv.analyze(raw)

    class _LanglyRes:
        metadata = {"live_play_version": "1.0.9002.0102"}

    md = fpv.render_section_markdown(
        "2026-06-10", analysis, live_play_version="1.0.9002.0102"
    )
    assert "✅ **LIVE PROD**" in md
    # The .04xx row also remains tagged as INTERNAL RING
    assert ".04xx INTERNAL RING" in md

    # And the full produce() path picks it up from ctx.prior_results
    result = fpv.produce(
        "2026-06-10",
        ctx={
            "client": _FakeClient(raw),
            "drop_dir": tmp_path,
            "prior_results": {Section.LANGLY_VERSION: _LanglyRes()},
        },
    )
    assert "✅ **LIVE PROD**" in result.markdown


def test_resolve_credentials_reads_json_env(monkeypatch):
    """PLAY_CONSOLE_SA_KEY with JSON contents → writes a tempfile and returns ok."""
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setenv("PLAY_CONSOLE_SA_KEY", '{"type":"service_account","client_email":"x@y.iam"}')
    auth = fpv._resolve_credentials()
    assert auth.status == "ok"
    assert auth.sa_key_path is not None
    assert Path(auth.sa_key_path).is_file()
    assert "service_account" in Path(auth.sa_key_path).read_text()


def test_resolve_credentials_reads_path_env(monkeypatch, tmp_path):
    key_file = tmp_path / "sa.json"
    key_file.write_text("{}")
    monkeypatch.delenv("PLAY_CONSOLE_SA_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key_file))
    auth = fpv._resolve_credentials()
    assert auth.status == "ok"
    assert auth.sa_key_path == str(key_file)


def test_resolve_credentials_missing(monkeypatch):
    monkeypatch.delenv("PLAY_CONSOLE_SA_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    assert fpv._resolve_credentials().status == "missing"


# ---------------------------------------------------------------------------
# _metric_resource — discovery doc shape (v1beta1 Play Developer Reporting)
# ---------------------------------------------------------------------------
#
# The v1beta1 discovery doc exposes metric sets nested under `vitals()`, with
# the resource name segment lowercased. errorCountMetricSet lives one level
# deeper (`vitals().errors().counts()`), NOT as a flat sibling. The original
# implementation called `svc.vitals().crashRateMetricSet()`, which raised
# AttributeError on the real service object. These tests would have caught
# that bug and now lock in the correct dispatch.


def _fake_service():
    """Build a chainable mock matching the real v1beta1 discovery shape."""
    from unittest.mock import MagicMock

    svc = MagicMock(name="service")
    vitals = MagicMock(name="vitals")
    svc.vitals.return_value = vitals

    crashrate_res = MagicMock(name="crashrate_resource")
    anrrate_res = MagicMock(name="anrrate_resource")
    errors = MagicMock(name="errors")
    counts_res = MagicMock(name="counts_resource")

    vitals.crashrate.return_value = crashrate_res
    vitals.anrrate.return_value = anrrate_res
    vitals.errors.return_value = errors
    errors.counts.return_value = counts_res

    return svc, {
        "crashRateMetricSet": crashrate_res,
        "anrRateMetricSet": anrrate_res,
        "errorCountMetricSet": counts_res,
    }


@pytest.mark.parametrize(
    "metric_set",
    ["crashRateMetricSet", "anrRateMetricSet", "errorCountMetricSet"],
)
def test_metric_resource_returns_correct_resource(metric_set):
    svc, expected = _fake_service()
    client = fpv.PlayVitalsClient(package_name="com.microsoft.scmx", sa_key_path="/dev/null")
    assert client._metric_resource(svc, metric_set) is expected[metric_set]


def test_metric_resource_rejects_unknown_metric_set():
    svc, _ = _fake_service()
    client = fpv.PlayVitalsClient(package_name="com.microsoft.scmx", sa_key_path="/dev/null")
    with pytest.raises(ValueError, match="Unknown metric set"):
        client._metric_resource(svc, "bogusMetricSet")


def test_metric_resource_uses_lowercase_discovery_accessors_not_camelcase():
    """Regression guard: the prior bug was `svc.vitals().crashRateMetricSet()`,
    which AttributeErrors on the real service. The fix must NOT call any
    camelCase metric-set accessor on `vitals()`."""
    from unittest.mock import MagicMock

    svc = MagicMock(name="service")

    # Simulate the real discovery doc: vitals() exposes only the lowercase
    # accessors. Any camelCase access raises AttributeError.
    class StrictVitals:
        def __init__(self):
            self.crashrate = MagicMock(return_value=MagicMock(name="crashrate_res"))
            self.anrrate = MagicMock(return_value=MagicMock(name="anrrate_res"))
            errors = MagicMock(name="errors")
            errors.counts = MagicMock(return_value=MagicMock(name="counts_res"))
            self.errors = MagicMock(return_value=errors)

        def __getattr__(self, name):  # pragma: no cover - only hit on bug
            raise AttributeError(f"'Resource' object has no attribute '{name}'")

    svc.vitals.return_value = StrictVitals()
    client = fpv.PlayVitalsClient(package_name="com.microsoft.scmx", sa_key_path="/dev/null")

    for ms in ("crashRateMetricSet", "anrRateMetricSet", "errorCountMetricSet"):
        # Must not raise:
        client._metric_resource(svc, ms)


# ---------------------------------------------------------------------------
# Freshness-window clamp (regression: HTTP 400 from pipeline on 2026-06-10
# because Play crashRateMetricSet DAILY freshness was 2026-06-09 and the
# section was asking for endTime=2026-06-10). See PR titled
# "frohike: shift Play Vitals timeline back by per-metric freshness offset".
# ---------------------------------------------------------------------------

from datetime import date as _date  # noqa: E402


@pytest.mark.parametrize("metric_set", [
    "crashRateMetricSet",
    "anrRateMetricSet",
    "errorCountMetricSet",
])
def test_freshness_offset_is_applied_per_metric(metric_set):
    """Every supported MetricSet must declare a positive DAILY offset so
    `endTime` always lands at most `today - offset_days` (Play rejects
    later end dates with HTTP 400 INVALID_ARGUMENT)."""
    offset = fpv._freshness_offset_days(metric_set)
    assert offset >= 1, (
        f"{metric_set} must declare a DAILY freshness offset ≥ 1 day; "
        f"got {offset}. Play Reporting v1beta1 returns HTTP 400 when "
        f"timeline_spec.end_date is later than the metric's freshness."
    )


def test_clamp_window_shifts_end_back_to_freshness_boundary():
    """Requested end=today must be clamped to today - offset and start must
    shift by the same delta so the window length is preserved."""
    today = _date(2026, 6, 10)
    # Caller asks for the same 7d window the section computes by default.
    start = _date(2026, 6, 3)
    end = _date(2026, 6, 10)

    new_start, new_end = fpv._clamp_window_for_freshness(
        start, end, "crashRateMetricSet", today=today,
    )

    assert new_end == _date(2026, 6, 9), (
        "crashRateMetricSet has a 1-day freshness offset; end must be "
        "clamped to 2026-06-09 when today is 2026-06-10."
    )
    assert (new_end - new_start).days == (end - start).days, (
        "Window length must be preserved after clamping."
    )
    assert new_start == _date(2026, 6, 2)


def test_clamp_window_is_noop_when_end_already_safe():
    """If the caller passed an end date that already sits inside the
    freshness boundary, do not shift the window."""
    today = _date(2026, 6, 10)
    start = _date(2026, 6, 1)
    end = _date(2026, 6, 8)  # well inside today-1

    new_start, new_end = fpv._clamp_window_for_freshness(
        start, end, "crashRateMetricSet", today=today,
    )

    assert (new_start, new_end) == (start, end)


@pytest.mark.parametrize("metric_set,expected_end", [
    ("crashRateMetricSet", _date(2026, 6, 9)),
    ("anrRateMetricSet", _date(2026, 6, 9)),
    ("errorCountMetricSet", _date(2026, 6, 9)),
])
def test_clamp_window_uses_per_metric_offset(metric_set, expected_end):
    """The clamp helper must dispatch on metric_set so we can raise an
    individual MetricSet's offset later (e.g. if Google extends the lag for
    one MetricSet only) without rewriting any call sites."""
    today = _date(2026, 6, 10)
    start = _date(2026, 6, 3)
    end = _date(2026, 6, 10)

    _, new_end = fpv._clamp_window_for_freshness(
        start, end, metric_set, today=today,
    )
    assert new_end == expected_end
