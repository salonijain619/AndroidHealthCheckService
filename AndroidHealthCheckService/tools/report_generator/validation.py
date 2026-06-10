"""Post-write validation of the assembled daily livesite report.

Implements the 9 invariants from Mulder's architecture decision §8.
Returns a list of human-readable failure strings; callers decide whether
to abort.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from tools.report_generator import config

LOG = logging.getLogger(__name__)


# Regex toolkit ---------------------------------------------------------------

_RE_H1 = re.compile(r"^# .*[Dd]aily [Ll]ivesite [Rr]eport", re.MULTILINE)
_RE_LANGLY_HEADER = re.compile(r"📱 \*\*Defender for Android — Live on Play Store")
_RE_EXEC_SUMMARY = re.compile(r"^## Executive Summary", re.MULTILINE)
_RE_CONTRIBUTORS = re.compile(r"^## Contributors", re.MULTILINE)
_RE_TABLE_ROW = re.compile(r"^\|.*\|.*\|\s*$")


def _has_metric_table(text: str) -> bool:
    """Invariant 6 — at least one markdown table of >=3 consecutive rows."""
    streak = 0
    for line in text.splitlines():
        if _RE_TABLE_ROW.match(line):
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 0
    return False


def _langly_header_in_top(text: str, n: int = 5) -> bool:
    """Invariant 4 — Langly version header in first ``n`` non-empty lines."""
    non_empty = [ln for ln in text.splitlines() if ln.strip()]
    return any(_RE_LANGLY_HEADER.search(ln) for ln in non_empty[:n])


def validate_report(path: Path | str) -> list[str]:
    """Run the 9 invariants. Return a list of failure strings (empty on pass)."""
    p = Path(path)
    failures: list[str] = []

    # 1. File exists.
    if not p.exists():
        return [f"invariant-1: file does not exist at {p}"]

    raw = p.read_bytes()

    # 2. File size in band.
    size = len(raw)
    if size < config.REPORT_MIN_BYTES or size > config.REPORT_MAX_BYTES:
        failures.append(
            f"invariant-2: file size {size} bytes outside "
            f"[{config.REPORT_MIN_BYTES}, {config.REPORT_MAX_BYTES}]"
        )

    text = raw.decode("utf-8", errors="replace")

    # 3. H1 present.
    if not _RE_H1.search(text):
        failures.append("invariant-3: missing daily livesite report H1")

    # 4. Langly version header near top.
    if not _langly_header_in_top(text):
        failures.append(
            "invariant-4: missing '📱 **Defender for Android — Live on Play Store' "
            "in first 5 non-empty lines"
        )

    # 5. Executive Summary heading present.
    if not _RE_EXEC_SUMMARY.search(text):
        failures.append("invariant-5: missing '## Executive Summary' heading")

    # 6. At least one metric table.
    if not _has_metric_table(text):
        failures.append("invariant-6: no markdown table of >=3 consecutive rows found")

    # 7. Contributors footer present.
    if not _RE_CONTRIBUTORS.search(text):
        failures.append("invariant-7: missing '## Contributors' footer")

    # 8 + 9. No forbidden substrings.
    for needle in config.FORBIDDEN_SUBSTRINGS:
        if needle in text:
            failures.append(
                f"invariant-8/9: forbidden substring {needle!r} present in report"
            )

    return failures


def write_validation_report(failures: list[str], runs_dir: Path) -> Path:
    """Persist a ``validation.json`` next to the per-date runs dir for triage."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    out = runs_dir / "validation.json"
    payload = {
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out
