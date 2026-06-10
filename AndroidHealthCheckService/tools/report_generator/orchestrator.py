"""Wave executor — runs the four producers in Mulder's 3-wave model.

Wave 1 (serial):   Langly  → publishes ``live_play_version`` etc. into ctx.
Wave 2 (parallel): Scully + Frohike + Skinner via ThreadPoolExecutor(max=3).
Wave 3 (serial):   Reyes (assembler) — only producer whose failure aborts.

Fail-soft: a producer that raises or returns Status.FAIL is logged, recorded,
and execution continues. The report is always assembled and written (Mulder §7),
unless ``--dry-run`` is set or Reyes itself raises (AssemblyError → exit 1).
"""

from __future__ import annotations

import concurrent.futures
import importlib
import json
import logging
import shutil
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.report_generator import config
from tools.report_generator.contracts import (
    AssemblyError,
    SECTION_MODULES,
    Section,
    SectionResult,
    Status,
)

LOG = logging.getLogger(__name__)


# --- Producer invocation ----------------------------------------------------


def _invoke_producer(
    section: Section, date: str, ctx: dict[str, Any]
) -> SectionResult:
    """Import + call a section module's ``produce(date, ctx)``.

    The orchestrator is the *last-resort* backstop per Mulder §2 rule 2 —
    producers are supposed to catch their own exceptions. If one slips
    through, we wrap it into a FAIL SectionResult so the wave keeps moving.
    """
    log = ctx.get("log", LOG).getChild(section.value) if ctx.get("log") else LOG
    started = time.monotonic()
    module_path = SECTION_MODULES[section]
    try:
        mod = importlib.import_module(module_path)
        produce = getattr(mod, "produce")
        result = produce(date, ctx)
        # Duck-type: producers authored before contracts.py merged may carry
        # their own fallback SectionResult class. Accept anything with the
        # required attrs and re-hydrate into our canonical type.
        if not isinstance(result, SectionResult):
            required = ("section", "status", "markdown", "metadata", "errors")
            if not all(hasattr(result, a) for a in required):
                raise TypeError(
                    f"{module_path}.produce returned {type(result).__name__}, "
                    "missing SectionResult attrs"
                )
            status_val = getattr(result.status, "value", result.status)
            result = SectionResult(
                section=section,
                status=Status(str(status_val)),
                markdown=getattr(result, "markdown", "") or "",
                metadata=dict(getattr(result, "metadata", {}) or {}),
                denominators=dict(getattr(result, "denominators", {}) or {}),
                errors=list(getattr(result, "errors", []) or []),
                drop_path=getattr(result, "drop_path", None),
                elapsed_s=getattr(result, "elapsed_s", 0.0) or 0.0,
            )
        if not result.elapsed_s:
            result.elapsed_s = time.monotonic() - started
        return result
    except Exception as exc:  # last-resort backstop
        elapsed = time.monotonic() - started
        log.error("producer %s failed: %s", section.value, exc, exc_info=True)
        return SectionResult(
            section=section,
            status=Status.FAIL,
            markdown="",
            metadata={},
            errors=[f"{type(exc).__name__}: {exc}"],
            elapsed_s=elapsed,
        )


# --- Wave 2 parallel execution ----------------------------------------------


def _run_wave2(
    sections: list[Section],
    date: str,
    ctx: dict[str, Any],
    timeout: int,
) -> dict[Section, SectionResult]:
    results: dict[Section, SectionResult] = {}
    if not sections:
        return results

    log = ctx.get("log", LOG)
    workers = min(config.WAVE2_MAX_WORKERS, len(sections))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_section = {
            ex.submit(_invoke_producer, s, date, ctx): s for s in sections
        }
        for fut in concurrent.futures.as_completed(future_to_section):
            section = future_to_section[fut]
            try:
                results[section] = fut.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                log.error("producer %s exceeded %ds timeout", section.value, timeout)
                results[section] = SectionResult(
                    section=section,
                    status=Status.FAIL,
                    markdown="",
                    errors=[f"timeout after {timeout}s"],
                )
            except Exception as exc:  # belt-and-suspenders
                log.error("future for %s raised: %s", section.value, exc)
                results[section] = SectionResult(
                    section=section,
                    status=Status.FAIL,
                    markdown="",
                    errors=[f"{type(exc).__name__}: {exc}"],
                )
    return results


# --- Manifest ---------------------------------------------------------------


def _serialize_result(sr: SectionResult) -> dict[str, Any]:
    d = asdict(sr)
    # Enum → str
    d["section"] = sr.section.value if isinstance(sr.section, Section) else str(sr.section)
    d["status"] = sr.status.value if isinstance(sr.status, Status) else str(sr.status)
    return d


def _write_manifest(
    runs_dir: Path,
    date: str,
    results: dict[Section, SectionResult],
    started_at: datetime,
    elapsed_s: float,
    dry_run: bool,
) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = runs_dir / "manifest.json"
    payload = {
        "date": date,
        "started_at": started_at.isoformat(),
        "elapsed_s": round(elapsed_s, 3),
        "dry_run": dry_run,
        "sections": {
            s.value: _serialize_result(sr) for s, sr in results.items()
        },
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


# --- Orchestrator entry point -----------------------------------------------


def run(
    date: str,
    output_path: Path,
    skip_sections: set[Section] | None = None,
    dry_run: bool = False,
    log: logging.Logger | None = None,
) -> dict[str, Any]:
    """Execute the 3 waves. Returns a dict with results + manifest path.

    Raises ``AssemblyError`` only if Reyes itself fails or the output file
    cannot be written (the single hard-fail per Mulder §7).
    """
    log = log or LOG
    skip = set(skip_sections or [])
    started_at = datetime.now(timezone.utc)
    started_mono = time.monotonic()

    runs = config.runs_dir(date)
    shutil.rmtree(runs, ignore_errors=True)
    runs.mkdir(parents=True, exist_ok=True)
    log.info("runs dir: %s", runs)

    ctx: dict[str, Any] = {
        "date": date,
        "runs_dir": runs,
        "config": config,
        "prior_results": {},
        "log": log,
    }

    results: dict[Section, SectionResult] = {}

    # Wave 1 — Langly (serial).
    if Section.LANGLY_VERSION not in skip:
        log.info("wave 1: langly_version (serial)")
        sr = _invoke_producer(Section.LANGLY_VERSION, date, ctx)
        results[Section.LANGLY_VERSION] = sr
        ctx["prior_results"][Section.LANGLY_VERSION] = sr
        log.info(
            "  langly_version → %s (%.2fs)", sr.status.value, sr.elapsed_s
        )
    else:
        log.info("wave 1: langly_version SKIPPED via --skip-sections")
        results[Section.LANGLY_VERSION] = SectionResult(
            section=Section.LANGLY_VERSION,
            status=Status.SKIP,
            markdown="",
            errors=["skipped via --skip-sections"],
        )
        ctx["prior_results"][Section.LANGLY_VERSION] = results[Section.LANGLY_VERSION]

    # Wave 2 — Scully + Frohike + Skinner (parallel).
    wave2_targets = [
        s
        for s in (
            Section.SCULLY_SERVER,
            Section.FROHIKE_PLAY_VITALS,
            Section.SKINNER_ICM,
        )
        if s not in skip
    ]
    wave2_skipped = [
        s
        for s in (
            Section.SCULLY_SERVER,
            Section.FROHIKE_PLAY_VITALS,
            Section.SKINNER_ICM,
        )
        if s in skip
    ]
    log.info(
        "wave 2: %s (parallel, max_workers=%d)",
        [s.value for s in wave2_targets],
        min(config.WAVE2_MAX_WORKERS, max(1, len(wave2_targets))),
    )
    wave2_results = _run_wave2(
        wave2_targets, date, ctx, timeout=config.SECTION_TIMEOUT_S
    )
    for s, sr in wave2_results.items():
        results[s] = sr
        ctx["prior_results"][s] = sr
        log.info("  %s → %s (%.2fs)", s.value, sr.status.value, sr.elapsed_s)
    for s in wave2_skipped:
        results[s] = SectionResult(
            section=s,
            status=Status.SKIP,
            markdown="",
            errors=["skipped via --skip-sections"],
        )
        ctx["prior_results"][s] = results[s]
        log.info("  %s → SKIP (--skip-sections)", s.value)

    # Wave 3 — Reyes (assembler). Hard-fails on raise.
    log.info("wave 3: assembler (serial)")
    sections_for_assembler: dict[str, SectionResult] = {
        s.value: sr for s, sr in results.items()
    }
    try:
        from tools.report_generator import assembler  # local import — Reyes' file
        markdown = assembler.assemble(date, sections_for_assembler, ctx)
    except Exception as exc:
        log.error("assembler raised: %s\n%s", exc, traceback.format_exc())
        raise AssemblyError(f"assembler failed: {exc}") from exc

    if dry_run:
        log.info("--dry-run: NOT writing %s (would be %d bytes)",
                 output_path, len(markdown.encode("utf-8")))
        wrote = False
    else:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")
            log.info("wrote report → %s (%d bytes)",
                     output_path, output_path.stat().st_size)
            wrote = True
        except OSError as exc:
            raise AssemblyError(
                f"failed to write report to {output_path}: {exc}"
            ) from exc

    elapsed = time.monotonic() - started_mono
    manifest = _write_manifest(runs, date, results, started_at, elapsed, dry_run)
    log.info("manifest → %s (total elapsed %.2fs)", manifest, elapsed)

    return {
        "results": results,
        "manifest_path": manifest,
        "markdown": markdown,
        "wrote_output": wrote,
        "output_path": output_path,
        "elapsed_s": elapsed,
    }
