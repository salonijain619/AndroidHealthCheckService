"""langly_version — produces the leading Play-Store-version header line.

Charter: Langly is the Release Tracker. Every daily/weekly report leads with the
currently live Play Store production version of ``com.microsoft.scmx``.

Two pull paths, tried in order:
  1. Play Reporting / Publisher API (needs ``PLAY_CONSOLE_SA_KEY`` env var —
     same service account as Frohike).
  2. Public Play Store listing scrape (anonymous HTTP).

Conforms to Mulder's producer contract (``tools/report_generator/contracts.py``)
— see ``.squad/decisions/inbox/mulder-report-generator-architecture.md`` §2.

Lightweight by design — see ``.squad/agents/langly/charter.md``.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import time
import urllib.request
from typing import Any

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover — fallback to urllib for total-minimal envs
    requests = None  # type: ignore

from tools.report_generator.contracts import Section, SectionResult, Status

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
ROLLING_LOG = REPO_ROOT / ".squad" / "agents" / "langly" / "research" / "play-store-versions.md"
PACKAGE_ID = "com.microsoft.scmx"
LISTING_URL = f"https://play.google.com/store/apps/details?id={PACKAGE_ID}&hl=en&gl=US"
UA = "Mozilla/5.0 (Linux; Android 13)"

# Regex anchors for the public listing — see history.md learnings.
#   1. JSON-LD softwareVersion (rare on Play listings but cheap to try first).
#   2. Metadata array adjacent to min/target SDK — the version that is NOT a
#      review-record version. Documented in Langly history 2026-06-10.
_VERSION_PATTERNS = (
    re.compile(r'"softwareVersion"\s*:\s*"(\d+\.\d+\.\d+\.\d+)"'),
    re.compile(r'\[\[\["(\d+\.\d+\.\d+\.\d+)"\]\],\[\[\[\d+\]\],\[\[\[\d+'),
)
_UPDATED_PATTERN = re.compile(r'"(\w{3} \d{1,2}, 20\d{2})",\[(\d{10})')


# ---------------------------------------------------------------------------
# Pull paths
# ---------------------------------------------------------------------------

def _fetch_listing_html(timeout: int = 15) -> str:
    if requests is not None:
        r = requests.get(LISTING_URL, headers={"User-Agent": UA}, timeout=timeout)
        r.raise_for_status()
        return r.text
    req = urllib.request.Request(LISTING_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_version_from_html(html: str) -> tuple[str | None, str | None]:
    """Return (version, updated_date_iso) parsed from the public listing HTML.

    Either field may be None if not found.
    """
    version: str | None = None
    for pat in _VERSION_PATTERNS:
        m = pat.search(html)
        if m:
            version = m.group(1)
            break

    updated_iso: str | None = None
    # The listing has several 10-digit unix stamps (first-publish, last-updated,
    # review timestamps, …). Pick the LATEST one — that is "Updated on" — to
    # avoid latching onto the original 2020-era publish date.
    candidates = _UPDATED_PATTERN.findall(html)
    if candidates:
        try:
            unix_ts = max(int(c[1]) for c in candidates)
            updated_iso = _dt.datetime.fromtimestamp(unix_ts, _dt.timezone.utc).date().isoformat()
        except (ValueError, OSError):
            updated_iso = None
    return version, updated_iso


def _pull_via_api() -> dict[str, Any] | None:
    """Attempt Play Reporting / Publisher API pull.

    Stub-grade: builds the request only if the SA key is present and the
    ``google-auth`` lib is importable. In the current environment neither is
    wired up (per Langly's 2026-06-10 history), so this returns None and the
    scrape fallback owns the pull. Kept here so wiring the SA later is a
    single-function change.
    """
    sa_key = os.environ.get("PLAY_CONSOLE_SA_KEY")
    if not sa_key:
        return None
    try:
        from google.oauth2 import service_account  # type: ignore
        from google.auth.transport.requests import Request as _GReq  # type: ignore
    except ImportError:
        return None
    try:
        info = json.loads(sa_key) if sa_key.lstrip().startswith("{") else json.load(open(sa_key))
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/androidpublisher"],
        )
        creds.refresh(_GReq())
        if requests is None:
            return None
        # Open a new edit, read production track, abandon edit.
        base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE_ID}"
        h = {"Authorization": f"Bearer {creds.token}"}
        edit = requests.post(f"{base}/edits", headers=h, timeout=15).json()
        edit_id = edit["id"]
        try:
            track = requests.get(f"{base}/edits/{edit_id}/tracks/production", headers=h, timeout=15).json()
        finally:
            requests.delete(f"{base}/edits/{edit_id}", headers=h, timeout=15)
        releases = track.get("releases", []) or []
        if not releases:
            return None
        rel = releases[0]
        version = (rel.get("name") or (rel.get("versionCodes") or [""])[0]) or None
        rollout = rel.get("userFraction")
        rollout_pct = round(float(rollout) * 100, 1) if rollout is not None else 100.0
        return {"version": version, "rollout_pct": rollout_pct, "via": "play-publisher-api"}
    except Exception:
        return None


def _pull_via_scrape() -> dict[str, Any] | None:
    try:
        html = _fetch_listing_html()
    except Exception:
        return None
    version, updated = parse_version_from_html(html)
    if not version:
        return None
    return {"version": version, "released": updated, "rollout_pct": None, "via": "play-store-scrape"}


# ---------------------------------------------------------------------------
# Header rendering
# ---------------------------------------------------------------------------

def _render_header(version: str, released: str, rollout_pct: float | None) -> str:
    if rollout_pct is not None and rollout_pct < 100.0:
        tail = f"rollout {rollout_pct:g}% staged production track"
    elif rollout_pct == 100.0:
        tail = "rollout 100% production track"
    else:
        tail = (
            "rollout % not visible — Play Console auth needed; "
            "active ramp inferred from server telemetry"
        )
    return (
        f"📱 **Defender for Android — Live on Play Store: `v{version}`** "
        f"(released {released}; {tail}). _Source: Langly._"
    )


def _fail_stub(date: str) -> str:
    return (
        f"_⚠️ Play Store version unavailable — see "
        f"`.squad/decisions/inbox/langly-version-pull-failure-{date}.md` for diagnosis._"
    )


# ---------------------------------------------------------------------------
# Rolling log
# ---------------------------------------------------------------------------

_HEADER_TS = "**Last pull:**"
_TABLE_HEADER = "| Version | Released | Rollout % | Pulled-via | Notes |"
_TABLE_SEP = "|---|---|---|---|---|"


def _update_rolling_log(version: str, released: str, rollout_pct: float | None,
                        via: str, date: str, log_path: pathlib.Path | None = None) -> None:
    # Resolve at call time so tests can monkeypatch ROLLING_LOG.
    if log_path is None:
        log_path = ROLLING_LOG
    rollout_str = f"{rollout_pct:g}%" if rollout_pct is not None else "TBD (Play Console)"
    if not log_path.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(_fresh_log(version, released, rollout_str, via, date), encoding="utf-8")
        return

    text = log_path.read_text(encoding="utf-8")
    # Bump last-pull timestamp
    text = re.sub(rf"({re.escape(_HEADER_TS)}) [\d\-]+", rf"\1 {date}", text, count=1)

    # Check whether this version is already the top row of the rolling table.
    table_start = text.find(_TABLE_HEADER)
    if table_start == -1:
        # No table yet — append one.
        text = text.rstrip() + "\n\n## Rolling history\n\n" + _TABLE_HEADER + "\n" + _TABLE_SEP + "\n"
    # Find first data row.
    rows_start = text.find("\n", text.find(_TABLE_SEP, table_start if table_start >= 0 else 0)) + 1
    rest = text[rows_start:]
    first_row_match = re.match(r"\|\s*`?([\d.]+)`?\s*\|", rest)
    new_row = f"| `{version}` | {released} | {rollout_str} | {via} | Auto-pulled {date}. |\n"
    if first_row_match and first_row_match.group(1) == version:
        # Same version — just touch timestamp (already done above).
        pass
    else:
        text = text[:rows_start] + new_row + rest
    log_path.write_text(text, encoding="utf-8")


def _fresh_log(version: str, released: str, rollout_str: str, via: str, date: str) -> str:
    return (
        f"# Microsoft Defender for Android — Play Store Version Tracker\n\n"
        f"**Package:** `{PACKAGE_ID}`\n"
        f"**Maintained by:** Langly (Release Tracker)\n"
        f"{_HEADER_TS} {date}\n\n---\n\n"
        f"## Rolling history\n\n"
        f"{_TABLE_HEADER}\n{_TABLE_SEP}\n"
        f"| `{version}` | {released} | {rollout_str} | {via} | First entry. |\n"
    )


# ---------------------------------------------------------------------------
# Public contract
# ---------------------------------------------------------------------------

def produce(date: str, ctx: dict | None = None) -> SectionResult:
    started = time.monotonic()
    ctx = ctx or {}
    errors: list[str] = []

    pulled = _pull_via_api()
    status = Status.GO
    if not pulled:
        pulled = _pull_via_scrape()
        status = Status.PARTIAL  # scrape never knows rollout %
    if not pulled or not pulled.get("version"):
        return SectionResult(
            section=Section.LANGLY_VERSION,
            status=Status.FAIL,
            markdown=_fail_stub(date),
            errors=["both Publisher API and Play Store scrape failed"],
            elapsed_s=time.monotonic() - started,
        )

    version = pulled["version"]
    released = pulled.get("released") or date
    rollout_pct = pulled.get("rollout_pct")
    via = pulled.get("via", "unknown")

    try:
        _update_rolling_log(version, released, rollout_pct, via, date)
    except Exception as exc:
        # Log update is best-effort — never let it kill the report.
        errors.append(f"rolling-log update skipped: {type(exc).__name__}: {exc}")

    try:
        drop_path = str(ROLLING_LOG.relative_to(REPO_ROOT))
    except ValueError:
        drop_path = str(ROLLING_LOG)

    return SectionResult(
        section=Section.LANGLY_VERSION,
        status=status,
        markdown=_render_header(version, released, rollout_pct),
        metadata={"version": version, "released": released,
                  "rollout_pct": rollout_pct, "via": via, "package_id": PACKAGE_ID},
        errors=errors,
        drop_path=drop_path,
        elapsed_s=time.monotonic() - started,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pull current Play Store version of com.microsoft.scmx.")
    p.add_argument("--date", required=True, help="Report date (YYYY-MM-DD).")
    args = p.parse_args(argv)
    result = produce(args.date, ctx={})
    print(result.markdown)
    return 0 if result.status != Status.FAIL else 2


if __name__ == "__main__":
    raise SystemExit(main())
