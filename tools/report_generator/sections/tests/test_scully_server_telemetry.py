"""Tests for tools/report_generator/sections/scully_server_telemetry.py

Run from the repo root:
    python -m pytest tools/report_generator/sections/tests/test_scully_server_telemetry.py -v
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.report_generator.sections import scully_server_telemetry as scully  # noqa: E402

DATE = "2026-06-10"


# --- helpers ------------------------------------------------------------------


@pytest.fixture
def isolated_drop_dir(tmp_path, monkeypatch):
    """Redirect the producer's drop / onboarding paths into tmp."""
    monkeypatch.setattr(scully, "DROP_DIR", tmp_path / "drops")
    monkeypatch.setattr(
        scully, "ONBOARDING_DOC", tmp_path / "scully-kusto-sp-onboarding.md"
    )
    (tmp_path / "drops").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _clear_auth_env(monkeypatch):
    for k in (
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_FEDERATED_TOKEN_FILE",
        "KUSTO_AAD_TENANT_ID",
        "KUSTO_AAD_SP_CLIENT_ID",
        "KUSTO_AAD_SP_CLIENT_SECRET",
    ):
        monkeypatch.delenv(k, raising=False)


def _canned_raw():
    """Mock Kusto-row payload shaped like real responses."""
    end = datetime.strptime(DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    daily = []
    for i, pct in enumerate([0.360, 0.367, 0.359, 0.354, 0.416, 0.431, 0.447]):
        day = end - timedelta(days=7 - i)
        daily.append(
            {
                "TIMESTAMP": day,
                "Devices": 22000,
                "Tenants": 1100,
                "Events": 21_000_000,
                "Failures": int(21_000_000 * pct / 100),
                "FailPct": pct,
            }
        )
    return {
        "fleet_totals": [
            {
                "ActiveDevices": 27744,
                "ActiveTenants": 1254,
                "TotalEvents": 131_874_839,
                "Failures": 507_643,
            }
        ],
        "daily_trend": daily,
        "regions": [
            {
                "Region": "germanywestcentral",
                "Total": 4_675_247,
                "Failures": 32_726,
                "Devices": 1925,
                "Tenants": 207,
                "FailPct": 0.700,
            },
            {
                "Region": "SwedenCentral",
                "Total": 5_196_296,
                "Failures": 13_099,
                "Devices": 1348,
                "Tenants": 111,
                "FailPct": 0.252,
            },
        ],
        "client_versions": [
            {
                "ClientVersion": "1.0.8921.0101",
                "Devices": 21352,
                "Tenants": 1092,
                "Events": 61_640_489,
                "Failures": 217_856,
                "FailPct": 0.353,
            },
            {
                "ClientVersion": "1.0.9002.0102",
                "Devices": 20174,
                "Tenants": 1054,
                "Events": 49_761_167,
                "Failures": 163_433,
                "FailPct": 0.328,
            },
            {
                "ClientVersion": "1.0.9003.0401",
                "Devices": 1003,
                "Tenants": 2,
                "Events": 4_600_055,
                "Failures": 28_814,
                "FailPct": 0.626,
            },
        ],
        "aps_get": [
            {
                "Total": 268_878_188,
                "Devices": 818_000,
                "Tenants": 24_092,
                "Successes": 268_867_194,
            }
        ],
        "aps_ack": [
            {"Total": 267_231_292, "Successes": 267_230_479, "AuthFails": 813}
        ],
        "pki": [
            {
                "ResultStatus": "InProgress",
                "OperationName": "CreateEnrollmentJob",
                "HttpResponseStatusCode": "201",
                "Events": 603_811,
            },
            {
                "ResultStatus": "Completed",
                "OperationName": "GetEnrollmentJobStatus",
                "HttpResponseStatusCode": "200",
                "Events": 102_171,
            },
            {
                "ResultStatus": "Failed",
                "OperationName": "GetEnrollmentJobStatus",
                "HttpResponseStatusCode": "500",
                "Events": 2,
            },
        ],
        "latency_probe": [],  # ghost-column still ghost
    }


def _runner_factory(raw):
    """Build a `_query_runner` lambda that maps db+query → canned rows."""
    qid_for = {kql: qid for qid, (_, kql) in scully._build_queries(DATE).items()}

    def runner(_client, _db, query):
        qid = qid_for.get(query)
        if qid is None:
            raise AssertionError(f"unexpected query: {query[:60]!r}")
        return raw.get(qid, [])

    return runner


# --- 1. SKIP when no auth env vars --------------------------------------------


def test_skip_when_no_auth(monkeypatch, isolated_drop_dir):
    _clear_auth_env(monkeypatch)
    # No cached drop, no auth.
    result = scully.produce(DATE, ctx={"date": DATE})
    assert result.status == scully.Status.SKIP
    assert "Server telemetry unavailable" in result.markdown
    assert "scully-kusto-sp-onboarding" in result.markdown
    assert result.metadata.get("reason") == "no_kusto_auth"
    # Onboarding doc dropped for Saloni.
    assert isolated_drop_dir.joinpath("scully-kusto-sp-onboarding.md").exists()


# --- 2. Markdown shape — 9 metric rows (10 incl. header) ----------------------


def test_markdown_matches_table_shape(monkeypatch, isolated_drop_dir):
    _clear_auth_env(monkeypatch)
    raw = _canned_raw()
    result = scully.produce(
        DATE,
        ctx={"date": DATE, "live_version": "1.0.9002.0102"},
        _kusto_factory=lambda: object(),  # bypass auth
        _query_runner=_runner_factory(raw),
    )
    assert result.status == scully.Status.GO, result.errors

    md = result.markdown
    # Header line + separator + 9 metric rows = 11 pipe-prefixed lines
    table_lines = [ln for ln in md.splitlines() if ln.startswith("|")]
    assert len(table_lines) == 11, f"expected 11 table lines, got {len(table_lines)}"

    # Each of the 06-10 metric labels is present
    expected_labels = [
        "Active Android Devices",
        "Active Android Tenants",
        "Fleet Tunnel Events",
        "Tunnel Health",
        "APS Get-Settings Availability",
        "APS Settings-Ack Success",
        "PKI Cert Enrollment Health",
        "Android Client Version Distribution",
        "Tunnel Latency p50/p95/p99",
    ]
    for lbl in expected_labels:
        assert lbl in md, f"missing metric row: {lbl}"

    # Trend conventions preserved
    assert "⬆️" in md
    assert "✅" in md
    assert "➡️" in md
    assert "🔴 Unfixed" in md  # ghost-column caveat

    # Metadata sanity
    assert result.metadata["tunnel_fail_rate_pct_7d"] == 0.385
    assert result.metadata["tunnel_fail_rate_peak_value_pct"] == 0.447
    assert result.metadata["tunnel_fail_rate_peak_day"] == "2026-06-09"  # last day
    assert result.metadata["eu_intensification_top_country"] == "germanywestcentral"
    assert result.metadata["internal_ring_anchor_version"] == "1.0.9003.0401"
    assert "exec_bullet" in result.metadata


# --- 3. Cache reuse within max-age --------------------------------------------


def test_cache_reuse_within_max_age(monkeypatch, isolated_drop_dir):
    _clear_auth_env(monkeypatch)
    # First call seeds the cache (auth bypassed via fake factory).
    raw = _canned_raw()
    first = scully.produce(
        DATE,
        ctx={"date": DATE, "live_version": "1.0.9002.0102"},
        _kusto_factory=lambda: object(),
        _query_runner=_runner_factory(raw),
    )
    assert first.status == scully.Status.GO
    drop = isolated_drop_dir / "drops" / f"server-telemetry-{DATE}.md"
    assert drop.exists()
    # Force the drop's mtime to be 1 hour ago (well within default 6h).
    one_hour_ago = time.time() - 3600
    os.utime(drop, (one_hour_ago, one_hour_ago))

    # Second call — no kusto factory, no auth env. Must still GO via cache.
    def _should_not_run():
        raise AssertionError("Kusto factory must not be called on a cache hit")

    second = scully.produce(
        DATE,
        ctx={"date": DATE, "live_version": "1.0.9002.0102"},
        max_age_hours=6,
        _kusto_factory=_should_not_run,
    )
    assert second.status == scully.Status.GO
    assert second.metadata.get("reused_from_cache") is True
    assert "germanywestcentral" in second.metadata.get(
        "eu_intensification_top_country", ""
    )

    # And expiring the cache forces a re-pull (SKIP because no auth).
    expired = time.time() - 7 * 3600
    os.utime(drop, (expired, expired))
    third = scully.produce(
        DATE,
        ctx={"date": DATE},
        max_age_hours=6,
    )
    assert third.status == scully.Status.SKIP


# --- 4. ctx['live_version'] drives the .04xx reframe --------------------------


def test_internal_ring_callout_uses_ctx_live_version(monkeypatch, isolated_drop_dir):
    _clear_auth_env(monkeypatch)
    raw = _canned_raw()
    result = scully.produce(
        DATE,
        ctx={"date": DATE, "live_version": "1.0.9002.0102"},
        _kusto_factory=lambda: object(),
        _query_runner=_runner_factory(raw),
    )
    md = result.markdown
    # `.04xx` is framed as internal ring, NOT as live customer track.
    assert "Internal `.04xx` ring `1.0.9003.0401`" in md
    assert "pre-production, NOT live customer track per Langly" in md
    # The live prod label points at 9002.0102 specifically (not at .04xx).
    assert "Live prod `1.0.9002.0102`" in md
    # Metadata mirrors the framing.
    assert result.metadata["production_version"] == "1.0.9002.0102"
    assert result.metadata["internal_ring_anchor_version"] == "1.0.9003.0401"
