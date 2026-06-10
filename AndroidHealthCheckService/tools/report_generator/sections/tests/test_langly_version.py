"""Tests for langly_version section producer."""
from __future__ import annotations

import pathlib

from tools.report_generator.contracts import Section, Status
from tools.report_generator.sections import langly_version as lv


FIXTURE_HTML = """
<html><head><title>Microsoft Defender</title></head><body>
<script>some js blob ... ,"Jun 10, 2026",[1781068472,0]],...
[[["1.0.9002.0102"]],[[[36]],[[[30,"11"]]]]] ...
[[["1.0.8921.0101"]]] in a review record block much later ...
</script></body></html>
"""


def test_scrape_fallback_parses_version():
    version, released = lv.parse_version_from_html(FIXTURE_HTML)
    assert version == "1.0.9002.0102"
    assert released == "2026-06-10"  # unix 1781068472 → 2026-06-10 UTC


def test_header_format_matches_template():
    header = lv._render_header("1.0.9002.0102", "2026-06-10", None)
    assert header.startswith("📱 **Defender for Android — Live on Play Store: `v1.0.9002.0102`**")
    assert "(released 2026-06-10;" in header
    assert "rollout % not visible" in header
    assert header.endswith("_Source: Langly._")


def test_header_format_with_rollout_pct():
    header = lv._render_header("1.0.9002.0102", "2026-06-10", 35.0)
    assert "rollout 35% staged production track" in header

    header_full = lv._render_header("1.0.9002.0102", "2026-06-10", 100.0)
    assert "rollout 100% production track" in header_full


def test_fail_returns_stub_not_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(lv, "_pull_via_api", lambda: None)
    monkeypatch.setattr(lv, "_pull_via_scrape", lambda: None)
    monkeypatch.setattr(lv, "ROLLING_LOG", tmp_path / "log.md")
    result = lv.produce("2026-06-10", ctx={})
    assert result.status == Status.FAIL
    assert result.section == Section.LANGLY_VERSION
    assert "Play Store version unavailable" in result.markdown
    assert "langly-version-pull-failure-2026-06-10.md" in result.markdown


def test_produce_partial_via_scrape(monkeypatch, tmp_path):
    monkeypatch.setattr(lv, "_pull_via_api", lambda: None)
    monkeypatch.setattr(lv, "_fetch_listing_html", lambda timeout=15: FIXTURE_HTML)
    log_path = tmp_path / "log.md"
    monkeypatch.setattr(lv, "ROLLING_LOG", log_path)
    result = lv.produce("2026-06-10", ctx={})
    assert result.status == Status.PARTIAL
    assert result.section == Section.LANGLY_VERSION
    assert result.metadata["version"] == "1.0.9002.0102"
    assert result.metadata["via"] == "play-store-scrape"
    assert log_path.exists()
    assert "1.0.9002.0102" in log_path.read_text()


def test_rolling_log_same_version_only_touches_timestamp(monkeypatch, tmp_path):
    log = tmp_path / "log.md"
    monkeypatch.setattr(lv, "ROLLING_LOG", log)
    lv._update_rolling_log("1.0.9002.0102", "2026-06-10", None, "play-store-scrape", "2026-06-10")
    body1 = log.read_text()
    lv._update_rolling_log("1.0.9002.0102", "2026-06-10", None, "play-store-scrape", "2026-06-11")
    body2 = log.read_text()
    # Exactly one row for this version
    assert body2.count("| `1.0.9002.0102` |") == 1
    assert "**Last pull:** 2026-06-11" in body2
    assert body1 != body2


def test_rolling_log_new_version_prepends_row(monkeypatch, tmp_path):
    log = tmp_path / "log.md"
    monkeypatch.setattr(lv, "ROLLING_LOG", log)
    lv._update_rolling_log("1.0.9002.0102", "2026-06-10", None, "play-store-scrape", "2026-06-10")
    lv._update_rolling_log("1.0.9100.0102", "2026-06-12", 25.0, "play-publisher-api", "2026-06-12")
    body = log.read_text()
    assert body.count("| `1.0.9100.0102` |") == 1
    assert body.count("| `1.0.9002.0102` |") == 1
    # New row appears above the older one.
    assert body.index("1.0.9100.0102") < body.index("1.0.9002.0102")
    assert "25%" in body

