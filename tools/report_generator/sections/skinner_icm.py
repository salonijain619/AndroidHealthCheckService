"""Skinner — ICM section (Wave 2, file-based per Mulder Track 3 Option B).

Source-of-truth flow:
  1. ``REPORT_GENERATOR_SKIP_ICM=1`` → explicit-skip hatch → Status.SKIP.
  2. ``.squad/agents/skinner/icm-latest.json`` present + mtime ≤ 48h →
     parse incidents + on-call, render markdown → Status.GO.
  3. JSON present but mtime > 48h → Status.PARTIAL with stale-data note.
  4. JSON missing → Status.PARTIAL with original "no CI auth" stub
     (carry-forward path).

The JSON is produced out-of-band by ``tools/icm/icm_collector.py`` (run via
``tools/icm/refresh-local.sh`` on Saloni's laptop) and committed to the repo
so CI never needs interactive ICM auth (Mulder plan §3 Option B + §4 hybrid).

On-call data is published into ``metadata['on_call']`` for the assembler to
hoist into the "📟 On-Call Today" table (Mulder plan §4 recommendation).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from tools.report_generator.contracts import Section, SectionResult, Status

LOG = logging.getLogger(__name__)

# Repo root: tools/report_generator/sections/skinner_icm.py → parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_INPUT = _REPO_ROOT / ".squad" / "agents" / "skinner" / "icm-latest.json"
_FRESHNESS_WINDOW_S = 48 * 3600  # 48 hours

_STUB_MARKDOWN_NO_FILE = (
    "_ICM data not refreshed in this run (CI auth limitation: "
    "`ICM_SP_CLIENT_ID` not set; `agency mcp icm` requires interactive Entra). "
    "Manual refresh path: `tools/icm/refresh-local.sh` (wraps "
    "`python -m tools.icm.icm_collector`). "
    "Last manual pull carried forward by Reyes from the most recent drop._"
)


def _format_stale(age_hours: float) -> str:
    return (
        f"_ICM data stale (>{int(age_hours)}h since last local pull) — "
        f"Saloni run `tools/icm/refresh-local.sh` to refresh "
        f"`.squad/agents/skinner/icm-latest.json`._"
    )


def _render_markdown(payload: dict[str, Any], pull_iso: str) -> str:
    active = payload.get("active_icms") or payload.get("active") or []
    mitigated = payload.get("mitigated_icms") or payload.get("mitigated") or []
    lines = ["## 📟 Active ICM Incidents", ""]
    lines.append(
        f"**Active:** {len(active)} · **Mitigated (7d):** {len(mitigated)} · "
        f"_Pulled: {pull_iso}_"
    )
    lines.append("")
    if active:
        lines.append("| ID | Sev | Title | Created | Type |")
        lines.append("|---|---|---|---|---|")
        for inc in active:
            iid = inc.get("id", "—")
            sev = inc.get("severity", "—")
            title = str(inc.get("title", "")).replace("|", "\\|")
            created = (inc.get("createdDate") or "")[:10]
            itype = inc.get("type", "—")
            lines.append(f"| {iid} | Sev{sev} | {title} | {created} | {itype} |")
    else:
        lines.append("_No active ICM incidents on team 106961 in this window._")
    return "\n".join(lines)


def _extract_on_call(payload: dict[str, Any]) -> dict[str, str | None]:
    oc = payload.get("on_call") or {}
    primary = (oc.get("primary") or {}).get("alias") if isinstance(oc.get("primary"), dict) else None
    backup = (oc.get("backup") or {}).get("alias") if isinstance(oc.get("backup"), dict) else None
    return {"primary": primary, "backup": backup}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def produce(date: str, ctx: dict) -> SectionResult:
    log = ctx.get("log", LOG)

    if os.environ.get("REPORT_GENERATOR_SKIP_ICM", "").strip():
        log.info("skinner_icm: REPORT_GENERATOR_SKIP_ICM set → SKIP")
        return SectionResult(
            section=Section.SKINNER_ICM,
            status=Status.SKIP,
            markdown="",
            metadata={"auth_path": "explicit-skip"},
            errors=["REPORT_GENERATOR_SKIP_ICM=1"],
        )

    input_path = Path(ctx.get("icm_input_file") or _DEFAULT_INPUT)

    if not input_path.exists():
        log.info("skinner_icm: %s missing → PARTIAL (carry-forward)", input_path)
        return SectionResult(
            section=Section.SKINNER_ICM,
            status=Status.PARTIAL,
            markdown=_STUB_MARKDOWN_NO_FILE,
            metadata={"auth_path": "file-missing", "input_path": str(input_path)},
            errors=[f"{input_path.name} not present; manual pull required"],
        )

    try:
        mtime = input_path.stat().st_mtime
        age_s = max(0.0, time.time() - mtime)
        payload = _load(input_path)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("skinner_icm: failed to read %s: %s", input_path, exc)
        return SectionResult(
            section=Section.SKINNER_ICM,
            status=Status.PARTIAL,
            markdown=_STUB_MARKDOWN_NO_FILE,
            metadata={"auth_path": "file-unreadable", "input_path": str(input_path)},
            errors=[f"failed to parse {input_path.name}: {exc}"],
        )

    pull_iso = (
        (payload.get("_meta") or {}).get("fetched_at")
        or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
    )
    on_call = _extract_on_call(payload)
    active_count = len(payload.get("active_icms") or payload.get("active") or [])
    mitigated_count = len(payload.get("mitigated_icms") or payload.get("mitigated") or [])
    common_meta = {
        "auth_path": "file-based",
        "input_path": str(input_path),
        "pull_date": pull_iso,
        "pull_age_hours": round(age_s / 3600, 1),
        "on_call": on_call,
        "active_count": active_count,
        "mitigated_count": mitigated_count,
    }

    if age_s > _FRESHNESS_WINDOW_S:
        age_h = age_s / 3600
        log.info(
            "skinner_icm: %s mtime %.1fh old (>48h) → PARTIAL stale",
            input_path,
            age_h,
        )
        stale_note = _format_stale(age_h)
        body = _render_markdown(payload, pull_iso)
        return SectionResult(
            section=Section.SKINNER_ICM,
            status=Status.PARTIAL,
            markdown=f"{stale_note}\n\n{body}",
            metadata=common_meta,
            errors=[f"icm-latest.json is {age_h:.1f}h old (>48h freshness gate)"],
        )

    log.info(
        "skinner_icm: %s fresh (%.1fh old) → GO (active=%d, mitigated=%d)",
        input_path,
        age_s / 3600,
        active_count,
        mitigated_count,
    )
    return SectionResult(
        section=Section.SKINNER_ICM,
        status=Status.GO,
        markdown=_render_markdown(payload, pull_iso),
        metadata=common_meta,
        errors=[],
    )


def _cli(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wrapper
    p = argparse.ArgumentParser(prog="tools.report_generator.sections.skinner_icm")
    p.add_argument("--date", default="2026-06-10")
    p.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help=f"Override default ICM JSON path (default: {_DEFAULT_INPUT}).",
    )
    args = p.parse_args(argv)
    ctx: dict[str, Any] = {}
    if args.input_file:
        ctx["icm_input_file"] = str(args.input_file)
    sr = produce(args.date, ctx)
    print(f"status={sr.status.value}")
    print(f"metadata={json.dumps(sr.metadata, indent=2)}")
    if sr.errors:
        print(f"errors={sr.errors}")
    print("---markdown---")
    print(sr.markdown)
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(_cli(sys.argv[1:]))
