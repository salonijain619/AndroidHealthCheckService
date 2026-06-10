"""Skinner — ICM section (Wave 2, graceful-skip strategy per Mulder §4).

Interactive-auth-blocked in CI:
  * If ``ICM_SP_CLIENT_ID`` env var is absent → return PARTIAL with a stub
    paragraph noting the auth gap and pointing operators at the manual path
    (``tools/icm/icm_collector.py``).
  * If present → log "TODO: wire SP" and still return PARTIAL until the SP
    integration is wired upstream (tracked in Mulder §4 follow-up issue 3).

This is the right call per Mulder's graceful-skip strategy — the report
ALWAYS produces, ICM section just degrades gracefully in unattended runs.
"""

from __future__ import annotations

import logging
import os

from tools.report_generator.contracts import Section, SectionResult, Status

LOG = logging.getLogger(__name__)

_STUB_MARKDOWN_NO_SP = (
    "_ICM data not refreshed in this run (CI auth limitation: "
    "`ICM_SP_CLIENT_ID` not set; `agency mcp icm` requires interactive Entra). "
    "Manual refresh path: `python -m tools.icm.icm_collector` — see "
    "`tools/icm/icm_collector.py` (D-131-final, 2026-06-04). "
    "Last manual pull carried forward by Reyes from the most recent drop._"
)

_STUB_MARKDOWN_TODO_SP = (
    "_ICM service-principal path detected (`ICM_SP_CLIENT_ID` set) but "
    "non-interactive ICM auth is not yet wired upstream "
    "(tracked in `.squad/decisions/inbox/mulder-report-generator-architecture.md` "
    "§4 follow-up 3). Falling back to PARTIAL — last manual pull carried forward._"
)


def produce(date: str, ctx: dict) -> SectionResult:
    log = ctx.get("log", LOG)
    if os.environ.get("ICM_SP_CLIENT_ID", "").strip():
        log.info("skinner_icm: ICM_SP_CLIENT_ID present — TODO: wire SP")
        markdown = _STUB_MARKDOWN_TODO_SP
        errors = ["ICM SP auth path not implemented (Mulder §4 follow-up 3)"]
    else:
        log.info("skinner_icm: ICM_SP_CLIENT_ID absent — graceful skip per Mulder §4")
        markdown = _STUB_MARKDOWN_NO_SP
        errors = ["ICM_SP_CLIENT_ID not set; agency CLI interactive auth unavailable in CI"]

    return SectionResult(
        section=Section.SKINNER_ICM,
        status=Status.PARTIAL,
        markdown=markdown,
        metadata={"auth_path": "skip-ci"},
        errors=errors,
    )


if __name__ == "__main__":  # pragma: no cover
    import sys
    print(produce(date="2026-06-10", ctx={}))
    sys.exit(0)
