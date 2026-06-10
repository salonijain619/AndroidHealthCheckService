"""Contracts for the daily livesite report generator.

Public types every producer + the orchestrator + the assembler agree on.
Per Mulder's architecture decision
(``.squad/decisions/inbox/mulder-report-generator-architecture.md`` §2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Per-section status. Mulder §2."""

    GO = "GO"
    PARTIAL = "PARTIAL"
    SKIP = "SKIP"
    FAIL = "FAIL"


class Section(str, Enum):
    """Canonical section keys. Mulder §2.

    String values match the section *module* basename so the assembler can key
    its ``sections`` dict by enum value without extra translation.
    """

    LANGLY_VERSION = "langly_version"
    SCULLY_SERVER = "scully_server_telemetry"
    FROHIKE_PLAY_VITALS = "frohike_play_vitals"
    SKINNER_ICM = "skinner_icm"


@dataclass
class SectionResult:
    """A single producer's return value. Mulder §2."""

    section: Section
    status: Status
    markdown: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    denominators: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    drop_path: str | None = None
    elapsed_s: float = 0.0


# --- Custom exceptions ------------------------------------------------------


class ReportGeneratorError(RuntimeError):
    """Base class for all CLI/orchestrator errors."""


class ConfigError(ReportGeneratorError):
    """Bad CLI args or config (exit code 3)."""


class AssemblyError(ReportGeneratorError):
    """Reyes' assembler raised or the final file could not be written
    (exit code 1 — the only producer whose failure fails the whole run)."""


class ValidationFailure(ReportGeneratorError):
    """One or more validation invariants from Mulder §8 failed
    (exit code 1 in --validate mode)."""

    def __init__(self, failed: list[str]) -> None:
        super().__init__(
            f"Validation failed ({len(failed)} invariant(s)): " + "; ".join(failed)
        )
        self.failed = list(failed)


# Section module path lookup — used by orchestrator to dynamically import.
SECTION_MODULES: dict[Section, str] = {
    Section.LANGLY_VERSION: "tools.report_generator.sections.langly_version",
    Section.SCULLY_SERVER: "tools.report_generator.sections.scully_server_telemetry",
    Section.FROHIKE_PLAY_VITALS: "tools.report_generator.sections.frohike_play_vitals",
    Section.SKINNER_ICM: "tools.report_generator.sections.skinner_icm",
}
