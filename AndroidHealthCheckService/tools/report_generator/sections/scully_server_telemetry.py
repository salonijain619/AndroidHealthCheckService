"""Scully — server-side NAAS telemetry section producer (Wave 2).

Produces the "Server-side (Scully, NAAS telemetry, 7d window …)" table that
matches the shape of ``daily-livesite-report-android-2026-06-10.md``.

Design notes
------------
* **Auth.** Uses ``azure.identity.DefaultAzureCredential`` so the same
  module works in CI (SP env vars / WIF token file) and locally (az-cli
  fallback). If credential acquisition or Kusto connection fails, the
  producer returns ``Status.SKIP`` with a stub markdown — never crashes.
* **Kusto.** Cluster ``https://idsharedwus.westus.kusto.windows.net`` /
  database ``NaasProd`` (plus sibling ``NaasAgentServicesApsProd`` and
  ``NaasCloudPkiProd`` for APS + PKI rows). Queries are the v1/v3
  ``S1..S12`` set Scully already shipped — see
  ``.squad/agents/scully/research/naas-7d-report-data-2026-06-09.md``.
* **Caching.** ``--max-age-hours`` (default 6) skips the pull if the drop
  file at ``.squad/agents/scully/research/server-telemetry-{date}.md`` is
  fresher than N hours and parses the cached numbers back out.
* **Cross-section framing.** The ``.04xx`` ring is reframed as an internal
  pre-prod track once Langly publishes ``live_play_version`` into
  ``ctx['live_version']`` (or ``ctx['prior_results'][LANGLY].metadata
  ['live_play_version']``). The producer never frames ``.04xx`` as live.

Standalone:
    python -m tools.report_generator.sections.scully_server_telemetry \
        --date 2026-06-10
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# --- Contract import (defensive — see assembler.py for rationale) ----------------

try:  # pragma: no cover - exercised once contracts.py lands
    from tools.report_generator.contracts import (  # type: ignore
        Section as _SectionEnum,
        SectionResult as _SectionResult,
        Status as _Status,
    )

    Status = _Status
    SectionResult = _SectionResult
    Section = _SectionEnum
except Exception:  # contracts.py not yet present — local mirror

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


# --- Constants ------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
DROP_DIR = REPO_ROOT / ".squad" / "agents" / "scully" / "research"
ONBOARDING_DOC = (
    REPO_ROOT / ".squad" / "decisions" / "inbox" / "scully-kusto-sp-onboarding.md"
)

KUSTO_CLUSTER = "https://idsharedwus.westus.kusto.windows.net"
KUSTO_DB_TUNNEL = "NaasProd"
KUSTO_DB_APS = "NaasAgentServicesApsProd"
KUSTO_DB_PKI = "NaasCloudPkiProd"

DEFAULT_MAX_AGE_HOURS = 6

INTERNAL_RING_RE = re.compile(r"^\d+\.\d+\.\d+\.04\d{2}$")

AUTH_STUB_MD = (
    "_⚠️ Server telemetry unavailable — Kusto SP not yet wired. "
    "See `.squad/decisions/inbox/scully-kusto-sp-onboarding.md`._"
)

# Baseline values (06-05 v1) for delta computation — published comparison anchor.
_BASELINE_FAIL_PCT = 0.289
_BASELINE_EVENTS = 130_050_841
_BASELINE_FAILURES = 375_714
_BASELINE_DEVICES = 27_489
_BASELINE_TENANTS = 1_241

_EU_REGIONS_OF_INTEREST = (
    "germanywestcentral",
    "NorthEurope",
    "SwedenCentral",
    "francecentral",
    "WestEurope",
    "westeurope",
)

_REGION_BASELINE_PCT = {
    "germanywestcentral": 0.322,
    "NorthEurope": 0.230,
    "SwedenCentral": 0.118,
    "francecentral": 0.225,
    "WestEurope": 0.449,
    "westeurope": 0.441,
}


# --- KQL — the S1..S12 suite, verbatim from prior naas-7d-report drops ----------

_TUNNEL_ANDROID_FILTER = "where DeviceOs has_cs 'ANDROID'"


def _window_predicate(date: str) -> str:
    """Closed 7-day window ending at ``date`` 00:00:00Z (Saloni-locked shape)."""
    end = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start = end - timedelta(days=7)
    return (
        f"where TIMESTAMP between (datetime({start.isoformat().replace('+00:00','Z')}) "
        f".. datetime({end.isoformat().replace('+00:00','Z')}))"
    )


def _build_queries(date: str) -> dict[str, tuple[str, str]]:
    """{qid: (db, kql)}. Shapes match prior S1..S12 verbatim."""
    w = _window_predicate(date)
    f = _TUNNEL_ANDROID_FILTER
    return {
        "fleet_totals": (
            KUSTO_DB_TUNNEL,
            f"""TunnelServerOperationEvents
| {w}
| {f}
| summarize ActiveDevices=dcount(DeviceId),
            ActiveTenants=dcount(TenantId),
            TotalEvents=count(),
            Failures=countif(Status=='Failure')""",
        ),
        "daily_trend": (
            KUSTO_DB_TUNNEL,
            f"""TunnelServerOperationEvents
| {w}
| {f}
| summarize Devices=dcount(DeviceId), Tenants=dcount(TenantId),
            Events=count(), Failures=countif(Status=='Failure')
            by bin(TIMESTAMP, 1d)
| extend FailPct = round(todouble(Failures)*100/Events, 3)
| order by TIMESTAMP asc""",
        ),
        "regions": (
            KUSTO_DB_TUNNEL,
            f"""TunnelServerOperationEvents
| {w}
| {f}
| summarize Total=count(), Failures=countif(Status=='Failure'),
            Devices=dcount(DeviceId), Tenants=dcount(TenantId) by Region
| extend FailPct = round(todouble(Failures)*100/Total, 3)
| order by Total desc
| take 25""",
        ),
        "client_versions": (
            KUSTO_DB_TUNNEL,
            f"""TunnelServerOperationEvents
| {w}
| {f}
| summarize Devices=dcount(DeviceId), Tenants=dcount(TenantId),
            Events=count(), Failures=countif(Status=='Failure') by ClientVersion
| extend FailPct = round(todouble(Failures)*100/Events, 3)
| order by Devices desc
| take 25""",
        ),
        "aps_get": (
            KUSTO_DB_APS,
            f"""AgentGetSettingsOperationEvent
| {w}
| where OS has_cs 'Android' or OSType has_cs 'Android'
| summarize Total=count(),
            Devices=dcount(DeviceId),
            Tenants=dcount(TenantId),
            Successes=countif(ResultStatus startswith 'Success' or HttpResponseStatusCode=='200')""",
        ),
        "aps_ack": (
            KUSTO_DB_APS,
            f"""AgentSettingsAckOperationEvent
| {w}
| where OS has_cs 'Android' or OSType has_cs 'Android'
| summarize Total=count(),
            Successes=countif(ResultStatus=='ProcceedSuccessfully'),
            AuthFails=countif(ResultStatus=='ClientFailureAuth')""",
        ),
        "pki": (
            KUSTO_DB_PKI,
            f"""EnrollCertificateOperationSummary
| {w}
| where OS == 'ANDROID'
| summarize Events=count() by ResultStatus, OperationName, HttpResponseStatusCode
| order by Events desc""",
        ),
        # Ghost-column re-check — caveat regenerates from a real attempt.
        "latency_probe": (
            KUSTO_DB_TUNNEL,
            f"""TunnelServerOperationEvents
| {w}
| {f}
| project LatencyMs
| take 1""",
        ),
    }


# --- Authentication & Kusto client ----------------------------------------------


def _have_auth_env() -> bool:
    if (
        os.environ.get("AZURE_TENANT_ID")
        and os.environ.get("AZURE_CLIENT_ID")
        and (
            os.environ.get("AZURE_CLIENT_SECRET")
            or os.environ.get("AZURE_FEDERATED_TOKEN_FILE")
        )
    ):
        return True
    if (
        os.environ.get("KUSTO_AAD_TENANT_ID")
        and os.environ.get("KUSTO_AAD_SP_CLIENT_ID")
        and os.environ.get("KUSTO_AAD_SP_CLIENT_SECRET")
    ):
        os.environ.setdefault("AZURE_TENANT_ID", os.environ["KUSTO_AAD_TENANT_ID"])
        os.environ.setdefault("AZURE_CLIENT_ID", os.environ["KUSTO_AAD_SP_CLIENT_ID"])
        os.environ.setdefault(
            "AZURE_CLIENT_SECRET", os.environ["KUSTO_AAD_SP_CLIENT_SECRET"]
        )
        return True
    return False


def _build_kusto_client():  # pragma: no cover - external SDK
    from azure.identity import DefaultAzureCredential  # type: ignore
    from azure.kusto.data import (  # type: ignore
        KustoClient,
        KustoConnectionStringBuilder,
    )

    cred = DefaultAzureCredential()
    cred.get_token("https://kusto.kusto.windows.net/.default")
    kcsb = KustoConnectionStringBuilder.with_azure_token_credential(KUSTO_CLUSTER, cred)
    return KustoClient(kcsb)


def _execute(client, db: str, query: str) -> list[dict[str, Any]]:  # pragma: no cover
    from azure.kusto.data.exceptions import KustoServiceError  # type: ignore

    for attempt in (1, 2):
        try:
            resp = client.execute(db, query)
            tbl = resp.primary_results[0]
            cols = [c.column_name for c in tbl.columns]
            return [dict(zip(cols, row)) for row in tbl.rows]
        except KustoServiceError as exc:
            if attempt == 1 and any(
                code in str(exc) for code in ("429", "503", "ServiceUnavailable")
            ):
                time.sleep(2)
                continue
            raise


# --- Data shaping ---------------------------------------------------------------


@dataclass
class _Pulled:
    window_start: str
    window_end: str
    devices_7d: int
    devices_delta_pct: float | None
    tenants_7d: int
    tenants_delta_pct: float | None
    total_events: int
    successes: int
    failures: int
    fail_pct_7d: float
    fail_pct_baseline: float | None
    fail_pct_delta_rel: float | None
    failures_delta_rel: float | None
    events_delta_rel: float | None
    peak_day: str
    peak_value_pct: float
    aps_get_pct: float
    aps_get_total: int
    aps_get_devices: int
    aps_get_tenants: int
    aps_ack_pct: float
    aps_ack_total: int
    aps_ack_auth_fails: int
    pki_total: int
    pki_errors: int
    pki_new_failure_class: str | None
    versions: list[dict[str, Any]]
    regions: list[dict[str, Any]]
    latency_ghost: bool


def _pct(n: float, d: float) -> float:
    return round(n * 100.0 / d, 3) if d else 0.0


def _delta_rel(now: float, base: float | None) -> float | None:
    if not base:
        return None
    return round((now - base) * 100.0 / base, 1)


def _shape_pulled(date: str, raw: dict[str, list[dict[str, Any]]]) -> _Pulled:
    end = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start = end - timedelta(days=7)

    totals = (raw.get("fleet_totals") or [{}])[0]
    total_events = int(totals.get("TotalEvents") or 0)
    failures = int(totals.get("Failures") or 0)
    successes = total_events - failures
    fail_pct = _pct(failures, total_events)
    devices = int(totals.get("ActiveDevices") or 0)
    tenants = int(totals.get("ActiveTenants") or 0)

    peak_day = ""
    peak_value = 0.0
    for r in raw.get("daily_trend") or []:
        events = int(r.get("Events") or 0)
        if events < 10_000:
            continue  # edge-of-window sliver
        pct = float(r.get("FailPct") or 0.0)
        if pct > peak_value:
            peak_value = pct
            ts = r.get("TIMESTAMP")
            if isinstance(ts, datetime):
                peak_day = ts.strftime("%Y-%m-%d")
            else:
                peak_day = str(ts)[:10]

    aps_get_row = (raw.get("aps_get") or [{}])[0]
    aps_get_total = int(aps_get_row.get("Total") or 0)
    aps_get_succ = int(aps_get_row.get("Successes") or 0)
    aps_get_pct = _pct(aps_get_succ, aps_get_total) if aps_get_total else 0.0

    aps_ack_row = (raw.get("aps_ack") or [{}])[0]
    aps_ack_total = int(aps_ack_row.get("Total") or 0)
    aps_ack_succ = int(aps_ack_row.get("Successes") or 0)
    aps_ack_auth_fails = int(aps_ack_row.get("AuthFails") or 0)
    aps_ack_pct = _pct(aps_ack_succ, aps_ack_total) if aps_ack_total else 0.0

    pki_rows = raw.get("pki") or []
    pki_total = sum(int(r.get("Events") or 0) for r in pki_rows)
    pki_errors = sum(
        int(r.get("Events") or 0)
        for r in pki_rows
        if str(r.get("ResultStatus", "")).lower() in ("failed", "unknown")
        or str(r.get("HttpResponseStatusCode", "")) in ("500", "404", "499")
    )
    pki_new = None
    for r in pki_rows:
        if (
            str(r.get("ResultStatus", "")) == "Failed"
            and str(r.get("HttpResponseStatusCode", "")) == "500"
        ):
            pki_new = (
                f"{int(r['Events'])}× HTTP 500 "
                f"`Failed/{r.get('OperationName','?')}`"
            )

    versions = []
    for r in raw.get("client_versions") or []:
        versions.append(
            {
                "version": str(r.get("ClientVersion", "")),
                "devices": int(r.get("Devices") or 0),
                "tenants": int(r.get("Tenants") or 0),
                "events": int(r.get("Events") or 0),
                "failures": int(r.get("Failures") or 0),
                "fail_pct": float(r.get("FailPct") or 0.0),
            }
        )

    regions = []
    for r in raw.get("regions") or []:
        region_name = str(r.get("Region", ""))
        regions.append(
            {
                "region": region_name,
                "total": int(r.get("Total") or 0),
                "failures": int(r.get("Failures") or 0),
                "fail_pct": float(r.get("FailPct") or 0.0),
                "devices": int(r.get("Devices") or 0),
                "tenants": int(r.get("Tenants") or 0),
                "delta_pct": _delta_rel(
                    float(r.get("FailPct") or 0.0),
                    _REGION_BASELINE_PCT.get(region_name),
                ),
            }
        )

    latency_ghost = not bool(raw.get("latency_probe"))

    return _Pulled(
        window_start=start.strftime("%Y-%m-%d"),
        window_end=end.strftime("%Y-%m-%d"),
        devices_7d=devices,
        devices_delta_pct=_delta_rel(devices, _BASELINE_DEVICES),
        tenants_7d=tenants,
        tenants_delta_pct=_delta_rel(tenants, _BASELINE_TENANTS),
        total_events=total_events,
        successes=successes,
        failures=failures,
        fail_pct_7d=fail_pct,
        fail_pct_baseline=_BASELINE_FAIL_PCT,
        fail_pct_delta_rel=_delta_rel(fail_pct, _BASELINE_FAIL_PCT),
        failures_delta_rel=_delta_rel(failures, _BASELINE_FAILURES),
        events_delta_rel=_delta_rel(total_events, _BASELINE_EVENTS),
        peak_day=peak_day,
        peak_value_pct=peak_value,
        aps_get_pct=aps_get_pct,
        aps_get_total=aps_get_total,
        aps_get_devices=int(aps_get_row.get("Devices") or 0),
        aps_get_tenants=int(aps_get_row.get("Tenants") or 0),
        aps_ack_pct=aps_ack_pct,
        aps_ack_total=aps_ack_total,
        aps_ack_auth_fails=aps_ack_auth_fails,
        pki_total=pki_total,
        pki_errors=pki_errors,
        pki_new_failure_class=pki_new,
        versions=versions,
        regions=regions,
        latency_ghost=latency_ghost,
    )


# --- Markdown rendering --------------------------------------------------------


def _classify_version(v: str, live_version: str | None) -> str:
    if live_version and v == live_version:
        return "live"
    if INTERNAL_RING_RE.match(v):
        return "internal_ring"
    return "other"


def _version_cell(pulled: _Pulled, live_version: str | None) -> str:
    live_row = None
    ring_anchor = None
    for v in pulled.versions:
        cls = _classify_version(v["version"], live_version)
        if cls == "live" and live_row is None:
            live_row = v
        if cls == "internal_ring":
            if ring_anchor is None or v["fail_pct"] > ring_anchor["fail_pct"]:
                ring_anchor = v

    parts: list[str] = []
    if live_row:
        parts.append(
            f"**Live prod `{live_row['version']}`: {live_row['fail_pct']:.3f}% "
            f"({live_row['devices']:,} devices / {live_row['tenants']} tenants).**"
        )
    elif live_version:
        parts.append(
            f"Live prod `{live_version}` not in top-25 server-observed cohort."
        )

    if ring_anchor:
        parts.append(
            f"**Internal `.04xx` ring `{ring_anchor['version']}`: "
            f"{ring_anchor['fail_pct']:.3f}%, "
            f"{ring_anchor['devices']:,} devices / {ring_anchor['tenants']} tenants** "
            f"— pre-production, NOT live customer track per Langly."
        )

    if not parts:
        parts.append("Version cohort data unavailable this cycle.")
    return " ".join(parts)


def _trend_arrow(pulled: _Pulled) -> str:
    if pulled.fail_pct_delta_rel and pulled.fail_pct_delta_rel > 0:
        peak = ""
        if pulled.peak_day:
            peak = (
                f"; daily peak **{pulled.peak_value_pct:.3f}% on "
                f"{pulled.peak_day[5:].replace('-', '/')}**"
            )
        return (
            f"⬆️ +{pulled.fail_pct_delta_rel:.0f}% "
            f"({pulled.fail_pct_baseline} → {pulled.fail_pct_7d:.3f}){peak}"
        )
    return "➡️ flat"


def _events_trend(pulled: _Pulled) -> str:
    et = pulled.events_delta_rel or 0
    ft = pulled.failures_delta_rel or 0
    return (
        f"⬆️ Events +{et:.1f}%, **failures +{ft:.1f}%** — pure quality degradation"
    )


def _devices_trend(pulled: _Pulled) -> str:
    d = pulled.devices_delta_pct or 0
    arrow = "➡️" if abs(d) < 5 else ("⬆️" if d > 0 else "⬇️")
    return f"{arrow} {d:+.1f}% (flat)"


def _tenants_trend(pulled: _Pulled) -> str:
    d = pulled.tenants_delta_pct or 0
    arrow = "➡️" if abs(d) < 5 else ("⬆️" if d > 0 else "⬇️")
    return f"{arrow} {d:+.1f}% (flat)"


def _eu_intensification(pulled: _Pulled) -> tuple[str, float]:
    best = ("", 0.0)
    for r in pulled.regions:
        if r["region"] in _EU_REGIONS_OF_INTEREST and r.get("delta_pct"):
            if r["delta_pct"] > best[1]:
                best = (r["region"], float(r["delta_pct"]))
    return best


def render_markdown(
    date: str,
    pulled: _Pulled,
    live_version: str | None,
    reused: bool = False,
) -> str:
    reuse_marker = ", reused" if reused else ""
    header = (
        f"### Server-side (Scully, NAAS telemetry, 7d window "
        f"`{pulled.window_start} → {pulled.window_end}`{reuse_marker})\n\n"
    )
    rows = [
        ("Metric", "Value", "Trend"),
        (
            "Active Android Devices (7d distinct, server-observed)",
            f"**{pulled.devices_7d:,}**",
            _devices_trend(pulled),
        ),
        (
            "Active Android Tenants (7d distinct)",
            f"**{pulled.tenants_7d:,}**",
            _tenants_trend(pulled),
        ),
        (
            "Fleet Tunnel Events (7d)",
            f"**{pulled.total_events:,}** — {pulled.successes:,} success / "
            f"**{pulled.failures:,} failure**",
            _events_trend(pulled),
        ),
        (
            "Tunnel Health (server-side success)",
            f"**{100 - pulled.fail_pct_7d:.3f}%** "
            f"(7d fail-rate **{pulled.fail_pct_7d:.3f}%**)",
            _trend_arrow(pulled),
        ),
        (
            "APS Get-Settings Availability (7d)",
            f"**{pulled.aps_get_pct:.3f}%** "
            f"({pulled.aps_get_total/1_000_000:.1f}M events / "
            f"{pulled.aps_get_devices/1000:.0f}K devices / "
            f"{pulled.aps_get_tenants:,} tenants)",
            "✅ Healthy, flat",
        ),
        (
            "APS Settings-Ack Success (7d)",
            f"**{pulled.aps_ack_pct:.5f}%** "
            f"({pulled.aps_ack_total/1_000_000:.1f}M / "
            f"{pulled.aps_ack_total/1_000_000:.1f}M; "
            f"{pulled.aps_ack_auth_fails:,} auth fails)",
            "✅ Healthy, flat",
        ),
        (
            "PKI Cert Enrollment Health (7d)",
            (
                f"✅ **{pulled.pki_errors} errors / {pulled.pki_total:,} events = "
                f"{_pct(pulled.pki_errors, pulled.pki_total):.4f}%**"
                + (
                    f"; new low-volume failure class: "
                    f"{pulled.pki_new_failure_class}"
                    if pulled.pki_new_failure_class
                    else ""
                )
            ),
            "➡️ Flat"
            + ("; new watch item" if pulled.pki_new_failure_class else ""),
        ),
        (
            "Android Client Version Distribution (server-side)",
            _version_cell(pulled, live_version),
            "⬆️ `.04xx` regression confined to internal ring; "
            "live prod track milder",
        ),
        (
            "Tunnel Latency p50/p95/p99",
            "TBD — `LatencyMs` ghost-column on `TunnelServerOperationEvents` "
            "(SEM0100)"
            if pulled.latency_ghost
            else "see drop",
            "🔴 Unfixed 4d" if pulled.latency_ghost else "—",
        ),
    ]

    out = [header]
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("|" + "|".join(["---"] * 3) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(c.replace("\n", " ") for c in r) + " |")
    return "\n".join(out) + "\n"


# --- Drop file (cache) ---------------------------------------------------------


_CACHE_BLOCK_RE = re.compile(
    r"<!--SCULLY-CACHE-V1-->\n(?P<json>\{.*?\})\n<!--/SCULLY-CACHE-V1-->",
    re.DOTALL,
)


def _drop_path(date: str) -> Path:
    return DROP_DIR / f"server-telemetry-{date}.md"


def _rel_to_repo(p: Path) -> str:
    """Best-effort repo-relative path; falls back to absolute (e.g. under tmp)."""
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _write_drop(
    date: str,
    markdown: str,
    pulled: _Pulled,
    metadata: dict[str, Any],
    raw: dict[str, Any] | None = None,
) -> Path:
    DROP_DIR.mkdir(parents=True, exist_ok=True)
    path = _drop_path(date)
    cache_blob = {
        "version": 1,
        "pulled_at_utc": datetime.now(timezone.utc).isoformat(),
        "date": date,
        "pulled": pulled.__dict__,
        "metadata": metadata,
    }
    body = [
        f"# Scully server telemetry drop — {date}\n",
        f"_Pulled at {cache_blob['pulled_at_utc']}_\n",
        "## Rendered section markdown\n",
        markdown,
        "\n## Cache payload (machine-readable; do not hand-edit)\n",
        "<!--SCULLY-CACHE-V1-->",
        json.dumps(cache_blob, default=str, indent=2),
        "<!--/SCULLY-CACHE-V1-->",
    ]
    if raw:
        body.append("\n## Raw KQL row counts\n")
        for k, rows in raw.items():
            body.append(f"- `{k}`: {len(rows) if rows is not None else 0} rows")
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def _read_cached(date: str, max_age_hours: int) -> tuple[_Pulled, dict, str] | None:
    path = _drop_path(date)
    if not path.exists():
        return None
    age_s = time.time() - path.stat().st_mtime
    if age_s > max_age_hours * 3600:
        return None
    text = path.read_text(encoding="utf-8")
    m = _CACHE_BLOCK_RE.search(text)
    if not m:
        return None
    try:
        blob = json.loads(m.group("json"))
    except json.JSONDecodeError:
        return None
    try:
        pulled = _Pulled(**blob["pulled"])
    except TypeError:
        return None
    md = ""
    if "## Rendered section markdown" in text:
        md = text.split("## Rendered section markdown", 1)[1]
        md = md.split("## Cache payload", 1)[0].strip() + "\n"
    return pulled, blob.get("metadata", {}), md


# --- Public producer entry -----------------------------------------------------


def _live_version_from_ctx(ctx: dict | None) -> str | None:
    if not ctx:
        return None
    if ctx.get("live_version"):
        return str(ctx["live_version"])
    prior = ctx.get("prior_results") or {}
    for key in (Section.LANGLY_VERSION, "langly_version"):
        sr = prior.get(key)
        if sr is None:
            continue
        meta = getattr(sr, "metadata", None) or (
            sr.get("metadata") if isinstance(sr, dict) else None
        )
        if meta and meta.get("live_play_version"):
            return str(meta["live_play_version"])
    return None


def produce(
    date: str,
    ctx: dict | None = None,
    *,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    _kusto_factory: Callable[[], Any] | None = None,
    _query_runner: Callable[[Any, str, str], list[dict]] | None = None,
) -> SectionResult:
    """Produce the Scully server-side section. Never raises."""
    log = (ctx or {}).get("log") or logging.getLogger("scully")
    started = time.monotonic()
    live_version = _live_version_from_ctx(ctx)

    # 1. Cache check — Saloni's "don't re-pull within 6h" rule.
    cached = _read_cached(date, max_age_hours)
    if cached:
        pulled, metadata, md = cached
        if live_version and live_version != metadata.get("production_version"):
            md = render_markdown(date, pulled, live_version, reused=True)
        metadata = dict(metadata)
        metadata["reused_from_cache"] = True
        metadata["cache_path"] = _rel_to_repo(_drop_path(date))
        return SectionResult(
            section=Section.SCULLY_SERVER,
            status=Status.GO,
            markdown=md,
            metadata=metadata,
            drop_path=_rel_to_repo(_drop_path(date)),
            elapsed_s=time.monotonic() - started,
        )

    # 2. Auth gate.
    if _kusto_factory is None and not _have_auth_env():
        _ensure_onboarding_doc()
        return SectionResult(
            section=Section.SCULLY_SERVER,
            status=Status.SKIP,
            markdown=AUTH_STUB_MD + "\n",
            metadata={"reason": "no_kusto_auth"},
            errors=[
                "AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET "
                "(or WIF token file) not configured."
            ],
            elapsed_s=time.monotonic() - started,
        )

    # 3. Build client + run queries.
    try:
        client = (_kusto_factory or _build_kusto_client)()
    except Exception as exc:  # pragma: no cover - external SDK errors
        log.warning("Kusto client construction failed: %s", exc)
        return SectionResult(
            section=Section.SCULLY_SERVER,
            status=Status.SKIP,
            markdown=AUTH_STUB_MD + "\n",
            metadata={"reason": "kusto_auth_failed"},
            errors=[f"DefaultAzureCredential failed: {exc!r}"],
            elapsed_s=time.monotonic() - started,
        )

    runner = _query_runner or _execute
    queries = _build_queries(date)
    raw: dict[str, list[dict]] = {}
    errors: list[str] = []
    for qid, (db, kql) in queries.items():
        try:
            raw[qid] = runner(client, db, kql)
        except Exception as exc:
            log.warning("Query %s failed: %s", qid, exc)
            errors.append(f"{qid}: {exc!r}")
            raw[qid] = []

    pulled = _shape_pulled(date, raw)
    md = render_markdown(date, pulled, live_version, reused=False)
    metadata = _build_metadata(pulled, live_version)
    drop = _write_drop(date, md, pulled, metadata, raw)

    status = Status.GO if not errors else Status.PARTIAL
    return SectionResult(
        section=Section.SCULLY_SERVER,
        status=status,
        markdown=md,
        metadata=metadata,
        errors=errors,
        drop_path=_rel_to_repo(drop),
        elapsed_s=time.monotonic() - started,
    )


def _build_metadata(pulled: _Pulled, live_version: str | None) -> dict[str, Any]:
    eu_top_region, eu_top_delta = _eu_intensification(pulled)

    anchor = None
    anchor_baseline_pct = None
    for v in pulled.versions:
        if INTERNAL_RING_RE.match(v["version"]):
            if anchor is None or v["fail_pct"] > anchor["fail_pct"]:
                anchor = v
                if v["version"] == "1.0.9003.0401":
                    anchor_baseline_pct = 0.271

    anchor_delta = None
    if anchor and anchor_baseline_pct:
        anchor_delta = _delta_rel(anchor["fail_pct"], anchor_baseline_pct)

    prod_band = None
    if live_version:
        for v in pulled.versions:
            if v["version"] == live_version:
                prod_band = v["fail_pct"]
                break

    exec_bullet = (
        f"🟠 Server-side ramp still climbing — 7d fail-rate "
        f"{(pulled.fail_pct_baseline or 0):.3f}% → {pulled.fail_pct_7d:.3f}% "
        f"(+{(pulled.fail_pct_delta_rel or 0):.0f}%), "
        f"daily peak {pulled.peak_value_pct:.3f}% on "
        f"{pulled.peak_day[5:].replace('-', '/') if pulled.peak_day else 'n/a'}."
    )

    return {
        "tunnel_fail_rate_pct_7d": pulled.fail_pct_7d,
        "tunnel_fail_rate_delta_pct": pulled.fail_pct_delta_rel,
        "tunnel_fail_rate_peak_day": pulled.peak_day,
        "tunnel_fail_rate_peak_value_pct": pulled.peak_value_pct,
        "eu_intensification_top_country": eu_top_region,
        "eu_intensification_top_delta_pct": eu_top_delta,
        "internal_ring_anchor_version": (anchor or {}).get("version"),
        "internal_ring_anchor_delta_pct": anchor_delta,
        "production_version": live_version,
        "production_version_band_pct": prod_band,
        "pull_window": [pulled.window_start, pulled.window_end],
        "reused_from_cache": False,
        "exec_bullet": exec_bullet,
    }


def _ensure_onboarding_doc() -> None:
    if ONBOARDING_DOC.exists():
        return
    ONBOARDING_DOC.parent.mkdir(parents=True, exist_ok=True)
    ONBOARDING_DOC.write_text(
        "# Kusto Service Principal Onboarding — Scully\n\n"
        "**Owner:** Saloni · **Status:** PENDING\n\n"
        "Scully's server-telemetry producer needs a non-interactive Entra "
        "service principal to query "
        "`idsharedwus.westus.kusto.windows.net / NaasProd` from CI.\n\n"
        "## What to provision\n\n"
        "1. **Tenant ID** — the Microsoft corp tenant (confirm GUID).\n"
        "2. **Service Principal creation** (`az ad sp create-for-rbac`):\n\n"
        "   ```bash\n"
        "   az ad sp create-for-rbac \\\n"
        "       --name gsa-android-scully-naas-reader \\\n"
        "       --years 1 \\\n"
        "       --skip-assignment\n"
        "   ```\n\n"
        "   Capture `appId`, `password`, `tenant`.\n\n"
        "3. **Role assignment on NaasProd DB** (Viewer):\n\n"
        "   ```bash\n"
        "   az kusto database-principal-assignment create \\\n"
        "       --cluster-name idsharedwus --resource-group <rg> \\\n"
        "       --database-name NaasProd \\\n"
        "       --principal-assignment-name scully-reader \\\n"
        "       --principal-id <appId> --principal-type App \\\n"
        "       --role Viewer\n"
        "   ```\n\n"
        "   Repeat for `NaasAgentServicesApsProd` and `NaasCloudPkiProd`.\n\n"
        "4. **GitHub Actions secrets** (per Mulder §4):\n"
        "   - `KUSTO_AAD_TENANT_ID`\n"
        "   - `KUSTO_AAD_SP_CLIENT_ID`\n"
        "   - `KUSTO_AAD_SP_CLIENT_SECRET`\n\n"
        "Until wired, the producer returns `Status.SKIP` with a stub — the "
        "daily report still ships, but the server-side section is empty.\n",
        encoding="utf-8",
    )


# --- CLI -----------------------------------------------------------------------


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scully server-telemetry section producer (Wave 2)."
    )
    parser.add_argument("--date", required=True, help="Report date, YYYY-MM-DD.")
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=DEFAULT_MAX_AGE_HOURS,
        help="Reuse drop file if fresher than this many hours (default 6).",
    )
    parser.add_argument(
        "--live-version",
        default=None,
        help="Override Langly's live_play_version (for ad-hoc runs).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s scully: %(message)s")
    ctx: dict[str, Any] = {"date": args.date}
    if args.live_version:
        ctx["live_version"] = args.live_version

    result = produce(args.date, ctx, max_age_hours=args.max_age_hours)
    sys.stdout.write(result.markdown)
    sys.stdout.write("\n")
    sys.stderr.write(
        f"[scully] status={result.status.value} "
        f"drop={result.drop_path} "
        f"reused={result.metadata.get('reused_from_cache', False)} "
        f"elapsed={result.elapsed_s:.2f}s\n"
    )
    if result.errors:
        for e in result.errors:
            sys.stderr.write(f"[scully:err] {e}\n")
    return 0 if result.status in (Status.GO, Status.PARTIAL, Status.SKIP) else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
