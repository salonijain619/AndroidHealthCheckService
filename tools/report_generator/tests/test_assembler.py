"""Tests for Reyes' Wave-3 assembler.

These tests use the local-fallback ``SectionResult``/``Status`` exposed by
``assembler.py``. When Doggett's ``contracts.py`` lands, the assembler will
prefer those symbols and the tests will keep passing because the assembler
re-exports them by name.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tools.report_generator.assembler import (
    SectionResult,
    Status,
    assemble,
    format_date_header,
)

DATE = "2026-06-10"


def _ctx() -> dict:
    return {
        "oncall_primary": "dileepkusuma",
        "oncall_backup": "samirnen",
        "scope_callout": (
            "First daily that fuses three parallel sources — "
            "Scully (server-side NAAS telemetry), Frohike (Google Play "
            "Vitals, NAAS-as-a-unit), and Langly (Play Store production "
            "version tracker)."
        ),
        "reframe_callout": (
            "Langly confirmed live production is `1.0.9002.0102` — "
            "the `.04xx` ring is internal/closed-test, not the production track."
        ),
        "started_at": datetime(2026, 6, 10, 14, 46, 0, tzinfo=timezone.utc),
    }


def _langly_go() -> SectionResult:
    md = (
        "📱 **Defender for Android — Live on Play Store: `v1.0.9002.0102`** "
        "(released 2026-06-10; rollout % not visible — Play Console auth "
        "needed; active ramp inferred from +51% device growth WoW). "
        "_Source: Langly._"
    )
    return SectionResult(
        section="langly_version",
        status=Status.GO,
        markdown=md,
        metadata={
            "live_play_version": "v1.0.9002.0102",
            "release_date": "2026-06-10",
            "exec_bullet": (
                "📱 **Live Play Store production = `1.0.9002.0102`.** "
                "All per-version framing in this report is anchored to this build."
            ),
        },
        drop_path=".squad/agents/langly/research/play-store-versions.md",
    )


def _scully_go() -> SectionResult:
    md = (
        "### Server-side (Scully, NAAS telemetry, 7d window "
        "`2026-06-02 → 2026-06-09`, reused)\n\n"
        "| Metric | Value | Trend |\n"
        "|---|---|---|\n"
        "| Active Android Devices (7d distinct, server-observed) | **27,744** | "
        "➡️ +0.9% (flat) |\n"
        "| Active Android Tenants (7d distinct) | **1,254** | ➡️ +1.0% (flat) |\n"
        "| Fleet Tunnel Events (7d) | **131,874,839** — 131,367,196 success / "
        "**507,643 failure** | ⬆️ Events +1.4%, **failures +35.1%** — pure "
        "quality degradation |\n"
        "| Tunnel Health (server-side success) | **99.615%** (7d fail-rate "
        "**0.385%**) | ⬆️ +33% (0.289 → 0.385); daily peak **0.447% on 6/08** |\n"
        "| APS Get-Settings Availability (7d) | **99.996%** (268.9M events / "
        "818K devices / 24,092 tenants) | ✅ Healthy, flat |\n"
        "| APS Settings-Ack Success (7d) | **99.99970%** (267.2M / 267.2M; 813 "
        "auth fails) | ✅ Healthy, flat |\n"
        "| PKI Cert Enrollment Health (7d) | ✅ **5 errors / 707,887 events = "
        "0.0007%** (1,326+ tenants); new low-volume failure class: 2× HTTP 500 "
        "`Failed/GetEnrollmentJobStatus` | ➡️ Flat; new watch item |\n"
        "| Android Client Version Distribution (server-side) | **Live prod "
        "`1.0.9002.0102`: 0.33–0.35% band (~+21%, mild).** Mainstream `.01xx` "
        "(8921.0101, 8913.0101) similar band. **Internal `.04xx` ring "
        "`1.0.9003.0401`: 0.626% (+131%, 1,003 devices / 2 tenants)** — "
        "pre-production, NOT live customer track per Langly. Long-tail "
        "pre-`8900` builds 0.87–2.67%. | ⬆️ `.04xx` regression confined to "
        "internal ring; live prod track milder |\n"
        "| Tunnel Latency p50/p95/p99 | TBD — `LatencyMs` ghost-column on "
        "`TunnelServerOperationEvents` (SEM0100) | 🔴 Unfixed 4d |\n"
    )
    return SectionResult(
        section="scully_server_telemetry",
        status=Status.GO,
        markdown=md,
        metadata={
            "pull_window": "2026-06-02..2026-06-09",
            "exec_bullet": (
                "🟠 **Server-side ramp still climbing — 7d fail-rate 0.289% → "
                "0.385% (+33%), daily peak 0.447% on 6/08.** Failures +35% on "
                "+1.4% traffic = pure quality degradation."
            ),
        },
        drop_path=".squad/agents/scully/research/naas-7d-report-data-2026-06-09.md",
    )


def _frohike_go() -> SectionResult:
    md = (
        "### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit, "
        "7d `2026-06-02 → 2026-06-08` rates / `2026-06-03 → 2026-06-09` counts)\n\n"
        "| Metric | Value | Denominator | Readout |\n"
        "|---|---|---|---|\n"
        "| NAAS crash reports (7d in-window) | **4,898** | Sum of "
        "`errorReportCount` over 17 NAAS-attributed issue clusters | 17 NAAS "
        "issues identified out of top-150 by lifetime |\n"
        "| NAAS ANR reports (7d in-window) | **4,413** | Same | ANR long-tail "
        "concentrated in OpenVPN init |\n"
        "| Affected users (upper bound) | **5,125** | Sum of `distinctUsers` "
        "across 17 NAAS issues (NOT cross-issue deduped) | True unique-user "
        "count is lower |\n"
        "| App user-perceived crash rate (whole-app, 7d, user-weighted) | "
        "**0.7045%** | All `com.microsoft.scmx` Android sessions in window | "
        "✅ Below Google bad-behavior threshold 1.09% |\n"
        "| App user-perceived ANR rate (whole-app, 7d, user-weighted) | "
        "**0.2619%** | Same | ✅ Below Google bad-behavior threshold 0.47% |\n"
        "| Δ crash rate vs prior 7d | **0.7045% vs 0.6783%** (+0.026pp / "
        "+3.9% rel) | App-level | ➡️ Slight uptick, within noise |\n"
        "| Tenant attribution | **Not derivable from Play** | — | Play Vitals "
        "exposes no tenant cut — use Scully for tenant slicing |\n\n"
        "## 🆕 NAAS Client Stability (Google Play Vitals)\n\n"
        "_Frohike's first daily — NAAS-attributed via cluster-level predicate "
        "match against top-150 issues by `errorReportCount`. 17 NAAS issues "
        "identified (4 CRASH, 13 ANR)._\n\n"
        "### Per-Defender-version NAAS table (PRIMARY)\n\n"
        "| Defender version | NAAS Crashes | NAAS ANRs | App CR% (7d) | "
        "App ANR% (7d) | Users 7d | Notes |\n"
        "|---|---:|---:|---:|---:|---:|---|\n"
        "| `1.0.9002.0102` ✅ **LIVE PROD** | **2,878** | **1,822** | 0.6025% "
        "| 0.1908% | 187,000 | Dominant absolute volume on arm64. |\n"
        "| `1.0.8921.0101` | 1,468 | 1,733 | 0.8770% | 0.2318% | 261,000 | "
        "Largest install base; highest CR% in the live cohort. |\n"
        "| `1.0.8913.0101` | 201 | 266 | 0.6091% | 0.3144% | 34,000 | "
        "Long-tail still active. |\n"
        "| 🔴 `1.0.9003.0401` **(.04xx INTERNAL RING)** | **95** | 0 | n/a — "
        "Play withholds (sub-threshold install base) | n/a | <500 | "
        "**27 of these 95 are `libnaas_native_vpn.so` SIGSEGVs.** |\n\n"
        "**Top-2-version concentration:** `1.0.9002.0102` + `1.0.8921.0101` "
        "carry **89% of NAAS crashes (4,346/4,898)** and **80% of NAAS ANRs "
        "(3,555/4,413)**. Any NAAS-class regression should be assessed "
        "against these two SKUs first.\n"
    )
    return SectionResult(
        section="frohike_play_vitals",
        status=Status.GO,
        markdown=md,
        metadata={
            "exec_bullet": (
                "🌍 **EU regional degradation cross-domain CORROBORATED — "
                "Germany 3.25% on 29K users, over Google's 1.09% Play Console "
                "bad-behavior threshold.**"
            ),
        },
        drop_path=".squad/agents/frohike/research/naas-crashes-2026-06-10.md",
    )


def _skinner_partial() -> SectionResult:
    md = (
        "| Bucket | Count | Notes |\n"
        "|---|---|---|\n"
        "| 🔴 Active + Mitigating | 1 | Sev3 #810723164 (TestICM, unack'd 5+ days) |\n"
        "| **Effective real-incident count** | **0** | After TestICM filter |\n"
    )
    return SectionResult(
        section="skinner_icm",
        status=Status.PARTIAL,
        markdown=md,
        metadata={
            "pull_date": "2026-06-08",
            "exec_bullet": (
                "🔴 **Detector silence pattern still stands — 3+ pulls, zero "
                "auto-ICMs against a 6× server-side ramp.**"
            ),
        },
        errors=["ICM auth not configured in CI; reusing 2026-06-08 manual pull."],
        drop_path=".squad/agents/skinner/research/icm-team-106961-data-2026-06-08.md",
    )


def _all_go() -> dict[str, SectionResult]:
    return {
        "langly_version": _langly_go(),
        "scully_server_telemetry": _scully_go(),
        "frohike_play_vitals": _frohike_go(),
        "skinner_icm": _skinner_partial(),
    }


# ---------------------------------------------------------------------------


def test_date_header_formatting():
    assert format_date_header("2026-06-10") == "Wed Jun 10, 2026"
    # Single-digit day must NOT be zero-padded
    assert format_date_header("2026-06-05") == "Fri Jun 5, 2026"


def test_assemble_full_report_shape():
    md = assemble(DATE, _all_go(), _ctx())

    # H1 with the canonical date format
    assert md.startswith("# 📋 GSA Android Daily Livesite Report — Wed Jun 10, 2026")

    # Langly header sits immediately under H1 (within first ~5 non-empty lines)
    head = [ln for ln in md.splitlines()[:8] if ln.strip()]
    assert any("Defender for Android — Live on Play Store" in ln for ln in head), head

    # Scope + reframe callouts both present
    assert "> **Scope (2026-06-10):**" in md
    assert "> **Headline reframe:**" in md

    # On-Call table
    assert "## 📟 On-Call Today" in md
    assert "| 🔴 Primary | dileepkusuma |" in md
    assert "| 🟡 Backup | samirnen |" in md

    # Required H2 sections present in canonical order
    assert "## Executive Summary" in md
    assert "## Key Metrics" in md
    assert "### Server-side (Scully" in md
    assert "### Client-side (Frohike" in md or "## 🆕 NAAS Client Stability" in md
    assert "## ICM Snapshot" in md
    assert "## Contributors" in md
    assert "## Run Diagnostics" in md

    # Every producer's exec bullet was surfaced
    for snippet in (
        "Live Play Store production = `1.0.9002.0102`",
        "Server-side ramp still climbing",
        "EU regional degradation cross-domain CORROBORATED",
        "Detector silence pattern still stands",
    ):
        assert snippet in md

    # Producer markdown bodies stitched in
    assert "**27,744**" in md  # Scully metric
    assert "**4,898**" in md   # Frohike metric

    # Run diagnostics table has a row per section
    assert "| Langly version |" in md
    assert "| Scully server telemetry |" in md
    assert "| Frohike Play Vitals |" in md
    assert "| Skinner ICM |" in md
    assert "✅ GO" in md and "⚠️ PARTIAL" in md

    # Footer run metadata
    assert "Report run:** 2026-06-10T14:46:00Z" in md
    assert "Generator version:" in md

    # Hard size floor per spec / validator §8.2
    assert len(md.encode("utf-8")) >= 5_000, len(md.encode("utf-8"))


def test_assemble_section_skip_renders_stub():
    sections = _all_go()
    sections["frohike_play_vitals"] = SectionResult(
        section="frohike_play_vitals",
        status=Status.SKIP,
        markdown="",
        metadata={},
    )
    md = assemble(DATE, sections, _ctx())

    # Exec summary stub line for the skipped section
    assert "_⚠️ Frohike Play Vitals unavailable this run — see logs._" in md
    # Key Metrics renders a skip stub instead of a broken table
    assert "Frohike Play Vitals skipped this run" in md
    # Diagnostics reflects SKIP
    assert "⏭️ SKIP" in md
    # Report still ships — no exception and meaningful size
    assert len(md.encode("utf-8")) >= 3_000


def test_assemble_section_fail_renders_stub_with_errors():
    sections = _all_go()
    sections["scully_server_telemetry"] = SectionResult(
        section="scully_server_telemetry",
        status=Status.FAIL,
        markdown="",
        errors=["Kusto SP auth: AADSTS700016 application not found in tenant"],
    )
    md = assemble(DATE, sections, _ctx())

    # Exec summary stub
    assert "_⚠️ Scully server telemetry unavailable this run — see logs._" in md
    # Key Metrics stub mentions the error file
    assert "Scully server telemetry failed to render" in md
    assert (
        "tools/report_generator/runs/2026-06-10/errors.log" in md
    )
    # Diagnostics reflects FAIL + carries the error excerpt
    assert "❌ FAIL" in md
    assert "AADSTS700016" in md
    # Other sections still rendered fully
    assert "**4,898**" in md
    assert "## Contributors" in md


def test_assembled_report_size_within_validation_bounds():
    md = assemble(DATE, _all_go(), _ctx())
    n = len(md.encode("utf-8"))
    assert 5_000 <= n <= 30_000, f"size out of band: {n}"


def test_reframe_callout_omitted_when_absent():
    ctx = _ctx()
    ctx.pop("reframe_callout")
    md = assemble(DATE, _all_go(), ctx)
    assert "Headline reframe" not in md


def test_oncall_falls_back_to_TBD_when_missing():
    """When Skinner has no on_call metadata and ctx has no override, the
    on-call resolver falls through to .squad/config/on-call.yaml. The shipped
    seed entry for 2026-06-10 carries `TBD-update-me` sentinels for both
    roles, so that's what should render."""
    md = assemble(DATE, _all_go(), {"started_at": datetime(2026, 6, 10, tzinfo=timezone.utc)})
    assert "| 🔴 Primary | TBD-update-me |" in md
    assert "| 🟡 Backup | TBD-update-me |" in md


def test_oncall_resolves_from_skinner_metadata():
    """Skinner JSON-derived on-call metadata is hoisted into the table when
    ctx doesn't override it (Mulder plan §4 hybrid)."""
    sections = _all_go()
    skinner = sections["skinner_icm"]
    skinner.status = Status.GO
    skinner.metadata = dict(skinner.metadata or {})
    skinner.metadata["on_call"] = {"primary": "dileepkusuma", "backup": "samirnen"}
    md = assemble(
        DATE, sections, {"started_at": datetime(2026, 6, 10, tzinfo=timezone.utc)}
    )
    assert "| 🔴 Primary | dileepkusuma |" in md
    assert "| 🟡 Backup | samirnen |" in md


def test_alias_scully_server_key_accepted():
    sections = _all_go()
    sections["scully_server"] = sections.pop("scully_server_telemetry")
    md = assemble(DATE, sections, _ctx())
    assert "**27,744**" in md
    assert "| Scully server telemetry | ✅ GO" in md


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
