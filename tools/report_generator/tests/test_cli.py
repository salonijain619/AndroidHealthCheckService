"""Tests for the CLI: arg parsing, exit codes, skip-sections, dry-run."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest import mock

import pytest

from tools.report_generator import cli, config, orchestrator
from tools.report_generator.contracts import Section, SectionResult, Status


def _ok(section: Section, md: str = "ok") -> SectionResult:
    return SectionResult(section=section, status=Status.GO, markdown=md)


def test_cli_bad_date_exits_3():
    rc = cli.main(["--date", "not-a-date"])
    assert rc == 3


def test_cli_unknown_skip_section_exits_3():
    rc = cli.main(["--date", "2026-06-10", "--skip-sections", "nope_not_a_section"])
    assert rc == 3


def test_cli_skip_sections_excludes_producers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config, "runs_dir",
        lambda date, repo_root=None: tmp_path / "runs" / date,
    )
    output = tmp_path / "out.md"
    called: list[Section] = []

    def _fake_invoke(section, date, ctx):
        called.append(section)
        return _ok(section, f"# {section.value}\n")

    with mock.patch.object(orchestrator, "_invoke_producer", side_effect=_fake_invoke):
        rc = cli.main(
            [
                "--date", "2026-06-10",
                "--output", str(output),
                "--skip-sections", "frohike_play_vitals,langly_version",
                "--dry-run",
            ]
        )

    assert rc == 0
    assert Section.LANGLY_VERSION not in called
    assert Section.FROHIKE_PLAY_VITALS not in called
    assert Section.SCULLY_SERVER in called


def test_cli_dry_run_does_not_write_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config, "runs_dir",
        lambda date, repo_root=None: tmp_path / "runs" / date,
    )
    output = tmp_path / "out.md"

    with mock.patch.object(
        orchestrator, "_invoke_producer",
        side_effect=lambda s, d, c: _ok(s, f"# {s.value}\n"),
    ):
        rc = cli.main(
            ["--date", "2026-06-10", "--output", str(output), "--dry-run"]
        )

    assert rc == 0
    assert not output.exists()
