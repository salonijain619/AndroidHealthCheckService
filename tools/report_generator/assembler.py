"""Reyes — final report assembler (Wave 3).

Consumes the SectionResult objects produced by Wave 1 (Langly) and Wave 2
(Scully, Frohike, Skinner) and stitches them into the canonical daily livesite
report markdown — visually equivalent to
``daily-livesite-report-android-2026-06-10.md``.

This module is deliberately data-forward and template-stable:
  * It does NOT invent numbers — every metric line comes from a producer.
  * It does NOT redesign the report shape — the 06-10 manual report is the
    visual contract.
  * If a producer fails or skips, the section is rendered as a clear stub so
    the report still ships (per Mulder's §7 fail-soft semantics).

Imports are defensive: in the steady-state, ``SectionResult`` / ``Status``
live in ``tools.report_generator.contracts`` (Doggett's module). While that
file is being built in parallel, the assembler ships its own local
fallback so it remains standalone-runnable and unit-testable.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "0.1.0"

# --- Contract import (defensive) -------------------------------------------------

try:  # pragma: no cover - exercised only once contracts.py lands
    from tools.report_generator.contracts import (  # type: ignore
        Section as _SectionEnum,
        SectionResult as _SectionResult,
        Status as _Status,
    )

    Status = _Status
    SectionResult = _SectionResult
    Section = _SectionEnum
except Exception:  # contracts.py not yet present — provide a local mirror

    class Status(str, Enum):
        GO = "GO"
        PARTIAL = "PARTIAL"
        SKIP = "SKIP"
        FAIL = "FAIL"

    class Section(str, Enum):
        LANGLY_VERSION = "langly_version"
        SCULLY_SERVER = "scully_server_telemetry"
        FROHIKE_PLAY_VITALS = "frohike_play_vitals"
        SKINNER_ICM = "skinner_icm"

    @dataclass
    class SectionResult:  # type: ignore[no-redef]
        section: Any
        status: Status
        markdown: str = ""
        metadata: dict[str, Any] = field(default_factory=dict)
        denominators: dict[str, Any] = field(default_factory=dict)
        errors: list[str] = field(default_factory=list)
        drop_path: str | None = None
        elapsed_s: float = 0.0


# --- Section key canonicalisation ------------------------------------------------
#
# Mulder's spec uses ``scully_server_telemetry`` but the task brief abbreviated
# it to ``scully_server``. Accept both so producers and the orchestrator can
# converge without renaming churn.

_SCULLY_KEYS = ("scully_server_telemetry", "scully_server")
_SECTION_DISPLAY = {
    "langly_version": "Langly version",
    "scully_server_telemetry": "Scully server telemetry",
    "scully_server": "Scully server telemetry",
    "frohike_play_vitals": "Frohike Play Vitals",
    "skinner_icm": "Skinner ICM",
}
_SECTION_EMOJI = {
    "langly_version": "📱",
    "scully_server_telemetry": "🛰️",
    "scully_server": "🛰️",
    "frohike_play_vitals": "📲",
    "skinner_icm": "📟",
}

# Render order for exec-summary bullets and run-diagnostics rows
_ORDER = (
    "langly_version",
    "scully_server_telemetry",
    "frohike_play_vitals",
    "skinner_icm",
)


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _repo_relative(path_str: str) -> str:
    """Strip the repo root prefix so paths in the report stay portable.
    Falls back to the original string if `path_str` is already relative or
    lives outside the repo."""
    if not path_str:
        return path_str
    try:
        p = Path(path_str)
        if p.is_absolute():
            try:
                return p.relative_to(_REPO_ROOT).as_posix()
            except ValueError:
                return p.name
        return path_str
    except Exception:
        return path_str


def _get(sections: dict[str, Any], *keys: str) -> SectionResult | None:
    for k in keys:
        if k in sections and sections[k] is not None:
            return sections[k]
    return None


def _status_of(sr: SectionResult | None) -> Status:
    if sr is None:
        return Status.SKIP
    s = sr.status
    if isinstance(s, str):
        try:
            return Status(s)
        except ValueError:
            return Status.FAIL
    return s


def _display_name(key: str) -> str:
    return _SECTION_DISPLAY.get(key, key)


# --- Date header ----------------------------------------------------------------


def format_date_header(date: str) -> str:
    """Return e.g. ``Wed Jun 10, 2026`` from ``2026-06-10``.

    Uses ``%-d`` on POSIX, falls back to ``%d`` with a manual zero-strip on
    platforms (Windows) that do not honour the GNU extension.
    """
    dt = datetime.strptime(date, "%Y-%m-%d")
    try:
        return dt.strftime("%a %b %-d, %Y")
    except (ValueError, TypeError):  # Windows
        # %#d is the Windows equivalent; fall back to manual strip if even that fails.
        try:
            return dt.strftime("%a %b %#d, %Y")
        except (ValueError, TypeError):
            base = dt.strftime("%a %b %d, %Y")
            # Strip the leading zero from the day portion only.
            parts = base.split(" ")
            if len(parts) == 4 and parts[2].endswith(",") and parts[2].startswith("0"):
                parts[2] = parts[2][1:]
            return " ".join(parts)


# --- Block builders -------------------------------------------------------------


_ONCALL_YAML_PATH = _REPO_ROOT / ".squad" / "config" / "on-call.yaml"


def _oncall_from_skinner(sections: dict[str, SectionResult]) -> tuple[str | None, str | None]:
    """Pull on-call aliases from Skinner's section metadata (preferred source).

    Skinner's producer publishes ``metadata['on_call'] = {'primary': alias,
    'backup': alias}`` when it loads `.squad/agents/skinner/icm-latest.json`
    (Mulder plan §4 hybrid recommendation).
    """
    skinner = _get(sections, "skinner_icm")
    if skinner is None or not skinner.metadata:
        return None, None
    on_call = skinner.metadata.get("on_call") or {}
    if not isinstance(on_call, dict):
        return None, None
    return on_call.get("primary"), on_call.get("backup")


def _oncall_from_yaml(date: str) -> tuple[str | None, str | None]:
    """Fallback: read manual rotation from ``.squad/config/on-call.yaml``.

    Picks the schedule entry whose ``from <= date <= to`` window contains the
    report date. Returns (None, None) if the file is missing, unparseable, or
    no matching entry. Tolerates PyYAML being absent — falls back to a minimal
    inline parser for the simple schema we ship.
    """
    if not _ONCALL_YAML_PATH.exists():
        return None, None
    try:
        text = _ONCALL_YAML_PATH.read_text(encoding="utf-8")
    except OSError:
        return None, None
    data: Any = None
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
    except ImportError:
        data = _parse_oncall_yaml_minimal(text)
    except Exception:  # noqa: BLE001 — best-effort
        return None, None
    if not isinstance(data, dict):
        return None, None
    schedule = data.get("schedule") or []
    if not isinstance(schedule, list):
        return None, None
    for entry in schedule:
        if not isinstance(entry, dict):
            continue
        frm = str(entry.get("from") or "")
        to = str(entry.get("to") or "")
        if frm and to and frm <= date <= to:
            primary = entry.get("primary")
            backup = entry.get("backup")
            primary = str(primary) if primary is not None else None
            backup = str(backup) if backup is not None else None
            return primary, backup
    return None, None


def _parse_oncall_yaml_minimal(text: str) -> dict[str, Any]:
    """Tiny YAML subset reader for the on-call.yaml shape we ship.

    Handles only the documented schema:
        schedule:
          - from: YYYY-MM-DD
            to: YYYY-MM-DD
            primary: alias
            backup: alias

    PyYAML is the supported path; this is a no-dependency fallback.
    """
    schedule: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_schedule = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            in_schedule = line.strip() == "schedule:"
            current = None
            continue
        if not in_schedule:
            continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current is not None:
                schedule.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None or ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        current[key.strip()] = val.strip().strip('"').strip("'")
    if current:
        schedule.append(current)
    return {"schedule": schedule}


def _resolve_oncall(
    ctx: dict, sections: dict[str, SectionResult], date: str
) -> tuple[str, str]:
    """Resolve the on-call (primary, backup) tuple per Mulder §4 hybrid.

    Precedence: explicit ctx override → Skinner JSON metadata →
    `.squad/config/on-call.yaml` → "TBD" sentinel.
    """
    primary = ctx.get("oncall_primary")
    backup = ctx.get("oncall_backup")
    if not primary or not backup:
        sp, sb = _oncall_from_skinner(sections)
        primary = primary or sp
        backup = backup or sb
    if not primary or not backup:
        yp, yb = _oncall_from_yaml(date)
        primary = primary or yp
        backup = backup or yb
    return (primary or "TBD"), (backup or "TBD")


def _oncall_block(
    ctx: dict,
    sections: dict[str, SectionResult] | None = None,
    date: str | None = None,
) -> str:
    primary, backup = _resolve_oncall(ctx, sections or {}, date or "")
    return (
        "## 📟 On-Call Today\n\n"
        "| Role | Engineer |\n"
        "|---|---|\n"
        f"| 🔴 Primary | {primary} |\n"
        f"| 🟡 Backup | {backup} |"
    )


def _scope_block(ctx: dict, date: str) -> str | None:
    scope = ctx.get("scope_callout")
    if not scope:
        return None
    scope = scope.strip()
    # If the caller already wrote a blockquote, pass it through; otherwise wrap.
    if scope.startswith(">"):
        return scope
    return f"> **Scope ({date}):** {scope}"


def _reframe_block(ctx: dict) -> str | None:
    rf = ctx.get("reframe_callout")
    if not rf:
        return None
    rf = rf.strip()
    if rf.startswith(">"):
        return rf
    return f"> **Headline reframe:** {rf}"


def _exec_summary(sections: dict[str, SectionResult]) -> str:
    lines = ["## Executive Summary", ""]
    emitted = 0
    for key in _ORDER:
        if key == "scully_server_telemetry":
            sr = _get(sections, *_SCULLY_KEYS)
        else:
            sr = _get(sections, key)
        status = _status_of(sr)
        if status in (Status.SKIP, Status.FAIL):
            lines.append(
                f"_⚠️ {_display_name(key)} unavailable this run — see logs._"
            )
            lines.append("")
            emitted += 1
            continue
        bullet = (sr.metadata or {}).get("exec_bullet") if sr else None
        if not bullet:
            continue
        bullet = bullet.strip()
        # Producers may already include an emoji + bold lead; if not, prepend
        # the section emoji so the visual cadence of 06-10 is preserved.
        if not bullet.startswith(_SECTION_EMOJI.get(key, "")) and not bullet[:2].strip().startswith(
            ("🔄", "🌍", "🟠", "🟡", "🔴", "🟢", "🔬", "⬆️", "⬇️", "✅", "⚠️", "❌", "🚨", "📱", "📊", "🆕")
        ):
            bullet = f"{_SECTION_EMOJI.get(key, '•')} {bullet}"
        lines.append(bullet)
        lines.append("")
        emitted += 1
    if emitted == 0:
        lines.append("_No section produced an executive bullet this run._")
        lines.append("")
    return "\n".join(lines).rstrip()


def _section_stub(key: str, sr: SectionResult | None, date: str) -> str:
    status = _status_of(sr)
    name = _display_name(key)
    if status == Status.FAIL:
        errs = ""
        if sr and sr.errors:
            errs = f" First error: `{sr.errors[0]}`."
        return (
            f"> ⚠️ **{name} failed to render this run.**{errs} "
            f"See `tools/report_generator/runs/{date}/errors.log` for details."
        )
    if status == Status.SKIP:
        return f"> ⏭️ **{name} skipped this run** (per orchestrator flags or env config)."
    if status == Status.PARTIAL:
        note = ""
        if sr and sr.errors:
            note = f" Note: {sr.errors[0]}"
        return (
            f"> ⚠️ **{name} returned partial data this run.**{note}"
        )
    return ""


def _key_metrics(sections: dict[str, SectionResult], date: str) -> str:
    out = ["## Key Metrics", ""]
    scully = _get(sections, *_SCULLY_KEYS)
    frohike = _get(sections, "frohike_play_vitals")

    # Server-side / Scully
    s_status = _status_of(scully)
    if s_status in (Status.GO, Status.PARTIAL) and scully and scully.markdown.strip():
        md = scully.markdown.strip()
        if not md.lstrip().startswith("###"):
            out.append("### Server-side (Scully, NAAS telemetry)")
            out.append("")
        out.append(md)
        if s_status == Status.PARTIAL:
            note = scully.errors[0] if scully.errors else "data incomplete"
            out.append("")
            out.append(f"> ⚠️ _Scully ran PARTIAL: {note}_")
    else:
        out.append("### Server-side (Scully, NAAS telemetry)")
        out.append("")
        out.append(_section_stub("scully_server_telemetry", scully, date))
    out.append("")

    # Client-side / Frohike (Play Vitals)
    f_status = _status_of(frohike)
    if f_status in (Status.GO, Status.PARTIAL) and frohike and frohike.markdown.strip():
        md = frohike.markdown.strip()
        if not md.lstrip().startswith("###") and not md.lstrip().startswith("## 🆕"):
            out.append("### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)")
            out.append("")
        out.append(md)
        if f_status == Status.PARTIAL:
            note = frohike.errors[0] if frohike.errors else "data incomplete"
            out.append("")
            out.append(f"> ⚠️ _Frohike ran PARTIAL: {note}_")
    else:
        out.append("### Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)")
        out.append("")
        out.append(_section_stub("frohike_play_vitals", frohike, date))
    return "\n".join(out).rstrip()


def _icm_section(sections: dict[str, SectionResult], date: str) -> str:
    skinner = _get(sections, "skinner_icm")
    status = _status_of(skinner)
    if status == Status.GO and skinner and skinner.markdown.strip():
        md = skinner.markdown.strip()
        if not md.lstrip().startswith("## "):
            return "## ICM Snapshot\n\n" + md
        return md
    if status == Status.PARTIAL:
        md = (skinner.markdown or "").strip() if skinner else ""
        header = "## ICM Snapshot"
        meta = skinner.metadata if skinner else {}
        last_pull = meta.get("pull_date") if isinstance(meta, dict) else None
        gap_note = (
            f"_ICM data not refreshed in this run (CI auth limitation). "
            f"Last manual pull: {last_pull or 'see Skinner drop'}._"
        )
        return f"{header}\n\n{gap_note}" + (f"\n\n{md}" if md else "")
    if status == Status.SKIP:
        return (
            "## ICM Snapshot\n\n"
            "_ICM data not refreshed in this run (skipped by orchestrator / env flag). "
            "Last successful pull is the most recent file under `.squad/agents/skinner/research/`._"
        )
    # FAIL
    return "## ICM Snapshot\n\n" + _section_stub("skinner_icm", skinner, date)


def _langly_header(sections: dict[str, SectionResult], date: str) -> str:
    langly = _get(sections, "langly_version")
    status = _status_of(langly)
    if status in (Status.GO, Status.PARTIAL) and langly and langly.markdown.strip():
        return langly.markdown.strip()
    # Degraded fallback per Mulder §7
    return (
        f"📱 **Defender for Android — Live on Play Store: ⚠️ version pull failed "
        f"({date}).** _Source: Langly._"
    )


def _run_diagnostics(
    sections: dict[str, SectionResult], date: str, started_at: datetime
) -> str:
    status_emoji = {
        Status.GO: "✅ GO",
        Status.PARTIAL: "⚠️ PARTIAL",
        Status.SKIP: "⏭️ SKIP",
        Status.FAIL: "❌ FAIL",
    }
    rows = ["## Run Diagnostics", "", "| Section | Status | Notes |", "|---|---|---|"]
    for key in _ORDER:
        if key == "scully_server_telemetry":
            sr = _get(sections, *_SCULLY_KEYS)
        else:
            sr = _get(sections, key)
        status = _status_of(sr)
        notes_bits: list[str] = []
        if sr and sr.metadata:
            for k in ("live_play_version", "pull_window", "pull_date"):
                v = sr.metadata.get(k)
                if v:
                    notes_bits.append(f"{k}={v}")
        if sr and sr.errors:
            notes_bits.append(f"err={sr.errors[0]}")
        if sr is None:
            notes_bits.append("no result returned")
        notes = "; ".join(notes_bits) or "—"
        # Markdown table cells must not contain unescaped pipes.
        notes = notes.replace("|", "\\|")
        rows.append(f"| {_display_name(key)} | {status_emoji[status]} | {notes} |")
    rows.append("")
    rows.append(
        f"**Report run:** {started_at.strftime('%Y-%m-%dT%H:%M:%SZ')} (UTC) · "
        f"**Generator version:** {GENERATOR_VERSION} · **Report date:** {date}"
    )
    return "\n".join(rows)


def _contributors(sections: dict[str, SectionResult]) -> str:
    lines = ["## Contributors", ""]
    contrib_map = {
        "langly_version": "**Langly** — Play Store version tracker.",
        "scully_server_telemetry": "**Scully** — server-side NAAS telemetry.",
        "frohike_play_vitals": "**Frohike** — Google Play Vitals (NAAS-as-a-unit).",
        "skinner_icm": "**Skinner** — ICM snapshot.",
    }
    for key in _ORDER:
        if key == "scully_server_telemetry":
            sr = _get(sections, *_SCULLY_KEYS)
        else:
            sr = _get(sections, key)
        status = _status_of(sr)
        suffix = ""
        if sr and sr.drop_path:
            suffix = f" See `{_repo_relative(sr.drop_path)}`."
        lines.append(f"- {contrib_map[key]} _Status: {status.value}._{suffix}")
    lines.append("- **Reyes** — daily report assembly.")
    return "\n".join(lines)


# --- Top-level assemble() -------------------------------------------------------


def assemble(date: str, sections: dict[str, SectionResult], ctx: dict | None = None) -> str:
    """Assemble the full daily livesite report markdown.

    Args:
        date: ``YYYY-MM-DD`` report date (UTC).
        sections: mapping of section key (per Mulder §2) to ``SectionResult``.
        ctx: optional context dict. Recognised keys:
            * ``oncall_primary``, ``oncall_backup`` — On-Call Today table values.
            * ``scope_callout`` — body of the Scope blockquote (string).
            * ``reframe_callout`` — body of the Headline reframe blockquote.
              Omitted entirely when absent.
            * ``started_at`` — ``datetime`` for the run-diagnostics footer
              (defaults to ``datetime.now(timezone.utc)``).

    Returns:
        The full report markdown, ready to write to disk.
    """
    ctx = ctx or {}
    started_at = ctx.get("started_at") or datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    parts: list[str] = []

    # 1. H1
    parts.append(f"# 📋 GSA Android Daily Livesite Report — {format_date_header(date)}")
    parts.append("")

    # 2. Langly version header (immediately under H1)
    parts.append(_langly_header(sections, date))
    parts.append("")

    # 3. Scope callout (optional)
    scope = _scope_block(ctx, date)
    if scope:
        parts.append(scope)
        parts.append("")

    # 4. Headline reframe (optional — omit if not set per spec)
    reframe = _reframe_block(ctx)
    if reframe:
        parts.append(reframe)
        parts.append("")

    # 5. On-Call Today
    parts.append(_oncall_block(ctx, sections, date))
    parts.append("")
    parts.append("---")
    parts.append("")

    # 6. Executive Summary
    parts.append(_exec_summary(sections))
    parts.append("")
    parts.append("---")
    parts.append("")

    # 7. Key Metrics (Scully + Frohike side-by-side)
    parts.append(_key_metrics(sections, date))
    parts.append("")
    parts.append("---")
    parts.append("")

    # 8. ICM Snapshot
    parts.append(_icm_section(sections, date))
    parts.append("")
    parts.append("---")
    parts.append("")

    # 9. Contributors
    parts.append(_contributors(sections))
    parts.append("")
    parts.append("---")
    parts.append("")

    # 10. Run Diagnostics (the at-a-glance triage table for Saloni)
    parts.append(_run_diagnostics(sections, date, started_at))
    parts.append("")

    return "\n".join(parts)


# --- CLI (optional re-assemble from cached SectionResult JSONs) -----------------


def _load_section_from_json(path: Path) -> tuple[str, SectionResult]:
    raw = json.loads(path.read_text())
    key = raw.get("section") or path.stem
    if isinstance(key, dict):
        key = key.get("value") or key.get("name") or path.stem
    status_val = raw.get("status", "FAIL")
    try:
        status = Status(status_val if isinstance(status_val, str) else status_val.get("value", "FAIL"))
    except (ValueError, AttributeError):
        status = Status.FAIL
    sr = SectionResult(
        section=key,
        status=status,
        markdown=raw.get("markdown", "") or "",
        metadata=raw.get("metadata", {}) or {},
        denominators=raw.get("denominators", {}) or {},
        errors=raw.get("errors", []) or [],
        drop_path=raw.get("drop_path"),
        elapsed_s=float(raw.get("elapsed_s", 0.0) or 0.0),
    )
    return str(key), sr


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tools.report_generator.assembler")
    p.add_argument("--date", required=True, help="Report date YYYY-MM-DD")
    p.add_argument(
        "--from-runs-dir",
        type=Path,
        required=True,
        help="Directory containing cached SectionResult JSONs from a prior orchestrator run.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: daily-livesite-report-android-{date}.md at cwd).",
    )
    args = p.parse_args(argv)

    runs_dir: Path = args.from_runs_dir
    if not runs_dir.exists():
        print(f"runs-dir not found: {runs_dir}", file=sys.stderr)
        return 3

    sections: dict[str, SectionResult] = {}
    for jp in sorted(runs_dir.glob("*.json")):
        if jp.name == "manifest.json":
            continue
        try:
            key, sr = _load_section_from_json(jp)
            sections[key] = sr
        except Exception as e:  # noqa: BLE001 — best-effort load
            print(f"skipping {jp.name}: {e}", file=sys.stderr)

    ctx_path = runs_dir / "ctx.json"
    ctx: dict[str, Any] = {}
    if ctx_path.exists():
        try:
            ctx = json.loads(ctx_path.read_text())
        except Exception:  # noqa: BLE001
            ctx = {}

    md = assemble(args.date, sections, ctx)
    output = args.output or Path(f"daily-livesite-report-android-{args.date}.md")
    output.write_text(md)
    print(f"wrote {output} ({len(md.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
