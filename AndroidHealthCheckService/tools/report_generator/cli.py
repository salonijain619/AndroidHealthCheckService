"""CLI entry point for the daily livesite report generator.

Invoked as: ``python -m tools.report_generator.cli --date YYYY-MM-DD``
(or via the package ``__main__`` shim: ``python -m tools.report_generator``).

Exit codes (Mulder §1):
  0 — report assembled (PARTIAL/SKIP sections are still success per fail-soft).
  1 — assembly failed, file not written, or validation failed.
  2 — reserved for --fail-fast (not yet wired).
  3 — invalid CLI args / config (bad date, mutually exclusive flags).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from tools.report_generator import config, orchestrator, validation
from tools.report_generator.contracts import (
    AssemblyError,
    ConfigError,
    Section,
)

LOG = logging.getLogger("report_generator")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def _parse_date(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError as exc:
        raise ConfigError(f"--date {s!r} is not YYYY-MM-DD: {exc}") from exc
    return s


def _parse_skip_sections(csv: str) -> set[Section]:
    if not csv:
        return set()
    out: set[Section] = set()
    valid = {s.value for s in Section}
    for raw in csv.split(","):
        token = raw.strip()
        if not token:
            continue
        if token not in valid:
            raise ConfigError(
                f"--skip-sections: unknown section {token!r}; "
                f"valid: {sorted(valid)}"
            )
        out.add(Section(token))
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="report_generator",
        description="Assemble the daily Android livesite report (Mulder §1).",
    )
    p.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="Report date YYYY-MM-DD (default: today UTC).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: repo-root/daily-livesite-report-android-{date}.md).",
    )
    p.add_argument(
        "--skip-sections",
        default="",
        help="Comma-separated section IDs to skip "
        "(e.g. langly_version,frohike_play_vitals).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run producers + assembler but do NOT write the final file.",
    )
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Skip producers; just run §8 validation against --output.",
    )
    p.add_argument(
        "--no-fail-on-validation",
        action="store_true",
        help="Log validation failures but still exit 0.",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="DEBUG-level logging.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        date = _parse_date(args.date)
        skip = _parse_skip_sections(args.skip_sections)
    except ConfigError as exc:
        LOG.error("config error: %s", exc)
        return 3

    output_path: Path = args.output or config.report_path(date)
    LOG.info("date=%s output=%s skip=%s dry_run=%s",
             date, output_path, sorted(s.value for s in skip), args.dry_run)

    # --validate-only short-circuit.
    if args.validate_only:
        failures = validation.validate_report(output_path)
        if failures:
            for f in failures:
                LOG.error("validation: %s", f)
            return 0 if args.no_fail_on_validation else 1
        LOG.info("validation: all 9 invariants passed for %s", output_path)
        return 0

    # Full run.
    try:
        result = orchestrator.run(
            date=date,
            output_path=output_path,
            skip_sections=skip,
            dry_run=args.dry_run,
            log=LOG,
        )
    except AssemblyError as exc:
        LOG.error("assembly failed: %s", exc)
        return 1
    except Exception as exc:  # pragma: no cover - belt-and-suspenders
        LOG.exception("unexpected orchestrator failure: %s", exc)
        return 1

    # Validate the written file (skip in dry-run; nothing to validate).
    if not args.dry_run and result["wrote_output"]:
        failures = validation.validate_report(output_path)
        try:
            validation.write_validation_report(failures, config.runs_dir(date))
        except OSError as exc:  # non-fatal
            LOG.warning("could not write validation.json: %s", exc)
        if failures:
            for f in failures:
                LOG.error("validation: %s", f)
            if not args.no_fail_on_validation:
                return 1
        else:
            LOG.info("validation: all 9 invariants passed.")

    LOG.info("done (%.2fs total)", result["elapsed_s"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
