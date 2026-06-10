"""Repo-relative paths, filename patterns, and validation thresholds.

All paths resolve against the repo root, discovered via
``Path(__file__).resolve().parents[2]``. No hardcoded ``/Users/`` paths.
"""

from __future__ import annotations

from pathlib import Path

# Repo root: tools/report_generator/config.py → parents[2] is repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

# Report filename pattern (Mulder §6).
REPORT_FILENAME_TEMPLATE = "daily-livesite-report-android-{date}.md"


def report_path(date: str, repo_root: Path | None = None) -> Path:
    """Absolute path to the final assembled report for ``date``."""
    root = repo_root or REPO_ROOT
    return root / REPORT_FILENAME_TEMPLATE.format(date=date)


def runs_dir(date: str, repo_root: Path | None = None) -> Path:
    """Per-date ephemeral runs directory (gitignored — Mulder §6)."""
    root = repo_root or REPO_ROOT
    return root / "tools" / "report_generator" / "runs" / date


# --- Validation thresholds (Mulder §8 invariants) ---------------------------

REPORT_MIN_BYTES = 5_000
REPORT_MAX_BYTES = 30_000

# Section execution timeout (Mulder §2 rule 6).
SECTION_TIMEOUT_S = 300

# Wave 2 parallelism (Mulder §5).
WAVE2_MAX_WORKERS = 3

# Forbidden substrings — invariant 8 (no template leakage) and invariant 9
# (no /Users/ paths).
FORBIDDEN_SUBSTRINGS = (
    "{date}",
    "{TBD",
    "{{",
    "}}",
    "/Users/",
)
