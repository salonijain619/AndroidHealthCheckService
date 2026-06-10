"""Tests for the orchestrator's wave model + fail-soft semantics."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest import mock

import pytest

from tools.report_generator import config, orchestrator
from tools.report_generator.contracts import Section, SectionResult, Status


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "daily-livesite-report-android-2026-06-10.md"


def _ok(section: Section, md: str = "ok") -> SectionResult:
    return SectionResult(section=section, status=Status.GO, markdown=md)


def _fail(section: Section, msg: str = "boom") -> SectionResult:
    return SectionResult(
        section=section, status=Status.FAIL, markdown="", errors=[msg]
    )


def test_orchestrator_continues_on_section_failure(tmp_output, monkeypatch):
    """A producer that raises must NOT abort the run — other producers and
    the assembler still execute, and the report still gets written
    (Mulder §7 fail-soft)."""

    # Redirect runs_dir to tmp.
    monkeypatch.setattr(
        config, "runs_dir",
        lambda date, repo_root=None: tmp_output.parent / "runs" / date,
    )

    def _fake_invoke(section, date, ctx):
        if section is Section.FROHIKE_PLAY_VITALS:
            raise RuntimeError("simulated producer crash")
        return _ok(section, f"# {section.value}\n\n| a | b | c |\n|---|---|---|\n| 1 | 2 | 3 |\n")

    with mock.patch.object(orchestrator, "_invoke_producer", side_effect=_fake_invoke):
        result = orchestrator.run(
            date="2026-06-10",
            output_path=tmp_output,
            skip_sections=set(),
            dry_run=False,
            log=logging.getLogger("test"),
        )

    assert result["wrote_output"] is True
    assert tmp_output.exists()

    results = result["results"]
    # Frohike was simulated to crash via direct raise — but our mock raises
    # directly, bypassing the real _invoke_producer's backstop. So Wave 2's
    # future.result() will raise and orchestrator records FAIL.
    assert results[Section.FROHIKE_PLAY_VITALS].status is Status.FAIL
    # Other producers still ran.
    assert results[Section.LANGLY_VERSION].status is Status.GO
    assert results[Section.SCULLY_SERVER].status is Status.GO
    assert results[Section.SKINNER_ICM].status is Status.GO


def test_orchestrator_dry_run_does_not_write(tmp_output, monkeypatch):
    monkeypatch.setattr(
        config, "runs_dir",
        lambda date, repo_root=None: tmp_output.parent / "runs" / date,
    )
    with mock.patch.object(
        orchestrator, "_invoke_producer",
        side_effect=lambda s, d, c: _ok(s, f"# {s.value}\n"),
    ):
        result = orchestrator.run(
            date="2026-06-10",
            output_path=tmp_output,
            skip_sections=set(),
            dry_run=True,
            log=logging.getLogger("test"),
        )
    assert result["wrote_output"] is False
    assert not tmp_output.exists()
    # manifest is still written.
    assert result["manifest_path"].exists()


def test_orchestrator_skip_excludes_producers(tmp_output, monkeypatch):
    monkeypatch.setattr(
        config, "runs_dir",
        lambda date, repo_root=None: tmp_output.parent / "runs" / date,
    )
    called: list[Section] = []

    def _fake_invoke(section, date, ctx):
        called.append(section)
        return _ok(section, f"# {section.value}\n")

    with mock.patch.object(orchestrator, "_invoke_producer", side_effect=_fake_invoke):
        result = orchestrator.run(
            date="2026-06-10",
            output_path=tmp_output,
            skip_sections={Section.LANGLY_VERSION, Section.FROHIKE_PLAY_VITALS},
            dry_run=True,
            log=logging.getLogger("test"),
        )

    assert Section.LANGLY_VERSION not in called
    assert Section.FROHIKE_PLAY_VITALS not in called
    assert Section.SCULLY_SERVER in called
    assert Section.SKINNER_ICM in called
    assert result["results"][Section.LANGLY_VERSION].status is Status.SKIP
    assert result["results"][Section.FROHIKE_PLAY_VITALS].status is Status.SKIP
