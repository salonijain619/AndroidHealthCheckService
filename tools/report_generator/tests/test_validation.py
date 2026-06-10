"""Tests for the §8 validation invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.report_generator import config, validation


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_validation_catches_missing_header(tmp_path: Path):
    bad = tmp_path / "bad.md"
    # Right size, has Exec Summary + Contributors + table — but missing H1.
    body = (
        "Not a daily livesite header.\n\n"
        "📱 **Defender for Android — Live on Play Store: `v0`**\n\n"
        "## Executive Summary\n\nstuff\n\n"
        "| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |\n\n"
        "## Contributors\n\nme\n"
    )
    # Pad to satisfy size invariant.
    body += "filler line.\n" * 500
    bad.write_text(body, encoding="utf-8")
    failures = validation.validate_report(bad)
    codes = " ".join(failures)
    assert "invariant-3" in codes


def test_validation_catches_forbidden_substring(tmp_path: Path):
    bad = tmp_path / "bad.md"
    body = (
        "# Daily Livesite Report — leaked\n\n"
        "📱 **Defender for Android — Live on Play Store: `v0`**\n\n"
        "## Executive Summary\n\nthe date is {date}.\n\n"
        "| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |\n\n"
        "## Contributors\n\nme\n"
    )
    body += "filler line.\n" * 500
    bad.write_text(body, encoding="utf-8")
    failures = validation.validate_report(bad)
    assert any("invariant-8/9" in f for f in failures)


def test_validation_passes_on_2026_06_10_report():
    """Regression anchor: the existing 06-10 manual report must pass all 9
    invariants — if validation rejects it, validation is wrong."""
    p = REPO_ROOT / "daily-livesite-report-android-2026-06-10.md"
    assert p.exists(), f"regression anchor missing: {p}"
    failures = validation.validate_report(p)
    assert failures == [], (
        f"06-10 report failed validation — fix invariants, not the report: {failures}"
    )


def test_validation_writes_validation_json(tmp_path: Path):
    failures = ["invariant-1: missing"]
    out = validation.write_validation_report(failures, tmp_path / "runs")
    assert out.exists()
    import json
    payload = json.loads(out.read_text())
    assert payload["passed"] is False
    assert payload["failure_count"] == 1
