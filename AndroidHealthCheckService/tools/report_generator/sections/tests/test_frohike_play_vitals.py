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
