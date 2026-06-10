"""icm_collector.py — ICM incident + on-call collector via `agency mcp icm`.

Single-backend design (D-131-final, 2026-06-04).  All previously-attempted
auth paths (ICM REST API + az-CLI bearer, custom `icm-mcp-server` subprocess)
were removed after empirical testing showed:

  * Azure CLI's public app registration (04b07795-…) is not authorized for
    the ICM REST resource e416d988-… — `az login --scope` returns
    AADSTS650057. The upstream `InE.IcmAutomation.Copilot` uses a private
    app registration + interactive browser flow + an SSO token-exchange
    against https://prod.microsofticm.com/sso2/token that cannot be
    reproduced without that app registration's client_id.
  * No public `icm-mcp-server` binary exists; the upstream ICM MCP server
    is shipped inside the Microsoft-internal `agency` CLI and exposed via
    `agency mcp icm` (stdio JSON-RPC, registered in
    ~/.copilot/mcp-config.json as the "ICMProd" server).

The working path is to spawn ``agency mcp icm`` as a JSON-RPC subprocess
ourselves, following this sequence (per the working pattern discovered in
prior session ``afe1c520-03c6-4cad-8b2b-75cb34753060``):

  1. spawn ``agency mcp icm``
  2. ``initialize`` (wait up to 60s — Entra interactive auth on first run,
     cached after)
  3. ``notifications/initialized``
  4. ``tools/list`` — warm-up; the first real ``tools/call`` after init
     often races on "A new session can only be created by an initialize
     request" without this
  5. wait ``WARMUP_DELAY_S`` seconds, then ``tools/call``

Tool names are bare (e.g. ``get_incident_details_by_id``); the Copilot
runtime prefixes them with ``ICMProd-`` for namespacing but the agency CLI
subprocess does not.

Public entry points
-------------------
collect(config, timeout)        Called by generate_report.py; returns ICM envelope.
fetch_incident(icm_id)          Ad-hoc single-incident lookup.

See .squad/skills/icm-via-mcp/SKILL.md for the full tool catalog.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class IcmCollectorError(RuntimeError):
    """Raised for hard failures (agency CLI missing, JSON-RPC errors, timeouts)."""


# ---------------------------------------------------------------------------
# agency CLI discovery
# ---------------------------------------------------------------------------

_AGENCY_CMD = ["agency", "mcp", "icm"]

_INSTALL_HINT = (
    "`agency` CLI not found on PATH. "
    "Install the Microsoft-internal `agency` CLI (provides ICMProd MCP proxy via `agency mcp icm`). "
    "Override with ICM_MCP_COMMAND=/path/to/agency,mcp,icm if needed. "
    "See .squad/skills/icm-via-mcp/SKILL.md for full details."
)


def _resolve_agency_cmd() -> List[str]:
    explicit = os.environ.get("ICM_MCP_COMMAND", "").strip()
    if explicit:
        return [p.strip() for p in explicit.split(",") if p.strip()]
    if not shutil.which(_AGENCY_CMD[0]):
        raise IcmCollectorError(_INSTALL_HINT)
    return list(_AGENCY_CMD)


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 client over `agency mcp icm` stdio
# ---------------------------------------------------------------------------

_JSONRPC_ID_SEED = 1


class IcmMcpClient:
    """Long-lived JSON-RPC 2.0 client over `agency mcp icm` stdio.

    Use as a context manager::

        with IcmMcpClient() as client:
            result = client.call_tool("search_incidents", {...})

    Tool names are bare (e.g. ``get_incident_details_by_id``).

    Raises IcmCollectorError on startup if the ``agency`` CLI is not found
    or initialization fails / times out.
    """

    INITIALIZE_TIMEOUT_S = 60   # Entra auth challenge on cold cache
    WARMUP_DELAY_S = 6           # post-tools/list, before first tools/call
    DEFAULT_CALL_TIMEOUT_S = 60  # ICM upstream can be slow

    def __init__(
        self,
        command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        cmd = command or _resolve_agency_cmd()
        proc_env = dict(os.environ)
        if env:
            proc_env.update(env)
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env=proc_env,
        )
        self._seq = _JSONRPC_ID_SEED
        self._out_q: "queue.Queue[str]" = queue.Queue()
        self._stderr_buf: List[str] = []
        threading.Thread(target=self._stdout_reader, daemon=True).start()
        threading.Thread(target=self._stderr_reader, daemon=True).start()
        self._initialize()

    # ------------------------------------------------------------------
    # IO threads — agency emits chatty stderr; keep it off the JSON-RPC path
    # ------------------------------------------------------------------

    def _stdout_reader(self) -> None:
        assert self._proc.stdout is not None
        for raw in self._proc.stdout:
            try:
                self._out_q.put(raw.decode("utf-8", errors="replace").rstrip("\n"))
            except Exception:
                pass

    def _stderr_reader(self) -> None:
        assert self._proc.stderr is not None
        for raw in self._proc.stderr:
            try:
                s = raw.decode("utf-8", errors="replace").rstrip("\n")
                self._stderr_buf.append(s)
                if len(self._stderr_buf) > 200:
                    self._stderr_buf = self._stderr_buf[-200:]
            except Exception:
                pass

    # ------------------------------------------------------------------
    # JSON-RPC plumbing
    # ------------------------------------------------------------------

    def _send(self, obj: Dict[str, Any]) -> None:
        assert self._proc.stdin is not None
        line = (json.dumps(obj) + "\n").encode("utf-8")
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

    def _recv(self, timeout_s: float) -> Dict[str, Any]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                line = self._out_q.get(timeout=1.0)
            except queue.Empty:
                if self._proc.poll() is not None:
                    tail = "\n".join(self._stderr_buf[-20:])
                    raise IcmCollectorError(
                        f"`agency mcp icm` exited unexpectedly. stderr tail:\n{tail}"
                    )
                continue
            if not line.strip():
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        raise IcmCollectorError(
            f"Timed out after {timeout_s}s waiting for JSON-RPC response from `agency mcp icm`."
        )

    def _rpc(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        is_notification: bool = False,
        timeout_s: float = 30.0,
    ) -> Any:
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if is_notification:
            self._send(msg)
            return None
        req_id = self._seq
        self._seq += 1
        msg["id"] = req_id
        self._send(msg)
        while True:
            response = self._recv(timeout_s)
            if response.get("id") == req_id:
                break
        if "error" in response:
            raise IcmCollectorError(f"JSON-RPC error: {response['error']}")
        return response.get("result")

    def _initialize(self) -> None:
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ahcs-icm-collector", "version": "1.0"},
            },
            timeout_s=self.INITIALIZE_TIMEOUT_S,
        )
        self._rpc("notifications/initialized", {}, is_notification=True)
        time.sleep(1)
        try:
            self._rpc("tools/list", timeout_s=30)
        except IcmCollectorError:
            pass
        time.sleep(self.WARMUP_DELAY_S)

    # ------------------------------------------------------------------
    # Public call_tool
    # ------------------------------------------------------------------

    def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout_s: float = DEFAULT_CALL_TIMEOUT_S,
    ) -> Any:
        """Call an ICM MCP tool by bare name (no ICMProd- prefix).

        Returns the parsed JSON payload from the tool's first content block,
        or the raw result dict if there is no content array.
        """
        result = self._rpc(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout_s=timeout_s,
        )
        if isinstance(result, dict) and result.get("isError"):
            content = result.get("content") or []
            msg = content[0].get("text", "Unknown MCP tool error") if content else "Unknown MCP tool error"
            raise IcmCollectorError(f"ICM MCP tool error [{name}]: {msg}")
        if isinstance(result, dict):
            content = result.get("content") or []
            if content and isinstance(content[0], dict):
                raw = content[0].get("text", "")
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return raw
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __enter__(self) -> "IcmMcpClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._proc.poll() is None:
            try:
                assert self._proc.stdin is not None
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()


# ---------------------------------------------------------------------------
# Response-parsing helpers
# ---------------------------------------------------------------------------


def _parse_incidents(raw: Any) -> List[Dict[str, Any]]:
    """Extract the items list from a search_incidents response."""
    if isinstance(raw, dict):
        items = raw.get("items") or raw.get("value") or []
        return items if isinstance(items, list) else []
    if isinstance(raw, list):
        return raw
    return []


def _incident_state(item: Dict[str, Any]) -> str:
    return str(item.get("status") or item.get("state") or "").lower()


def _incident_sev(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("severity") or item.get("sev") or 99)
    except (TypeError, ValueError):
        return 99


def _extract_on_call(raw: Any) -> Dict[str, Any]:
    """Normalise a get_on_call_schedule_by_team_id response."""
    if not raw:
        return {"primary": None, "backup": None, "schedule_source": None}

    schedule = raw[0] if isinstance(raw, list) else raw

    contacts: List[Dict[str, Any]] = []
    shifts = schedule.get("shiftCurrentOnCalls") or []
    if shifts:
        contacts = (shifts[0] or {}).get("currentOnCallContacts") or []
    if not contacts:
        contacts = schedule.get("currentOnCallContacts") or []

    def _contact(idx: int) -> Optional[Dict[str, Any]]:
        if idx >= len(contacts):
            return None
        c = contacts[idx]
        alias = c.get("alias") or c.get("userAlias") or None
        name = c.get("name") or c.get("displayName") or alias
        return {"alias": alias, "name": name} if alias else None

    return {
        "primary": _contact(0),
        "backup": _contact(1),
        "schedule_source": "live",
    }


# ---------------------------------------------------------------------------
# Envelope builders
# ---------------------------------------------------------------------------


def _partial_envelope(
    team_id: int,
    team_name: str,
    lookback_days: int,
    fetched_at: str,
    errors: List[str],
) -> Dict[str, Any]:
    """Clean partial-result envelope when the agency CLI can't start."""
    error_str = "; ".join(errors)
    return {
        "active_icms": [],
        "mitigated_icms": [],
        "on_call": {"primary": None, "backup": None, "schedule_source": None},
        "ai_summaries": {},
        "source": "partial",
        "_meta": {
            "team_id": team_id,
            "team_name": team_name,
            "lookback_days": lookback_days,
            "fetched_at": fetched_at,
            "errors": errors,
            "row_counts": {"active": 0, "mitigated": 0, "ai_summaries": 0},
        },
        # Backward-compat keys for generate_report.normalize_icm()
        "warning": error_str,
        "active": [],
        "mitigated": [],
        "counts": {"active": 0, "mitigated": 0},
        "customer_created_active": [],
        "system_created_active": [],
        "mitigated_highlights": [],
        "patterns": [error_str] if errors else [],
        "oncall": {
            "primary": "?",
            "backup": "?",
            "team_id": str(team_id),
            "cached": True,
            "warning": error_str,
            "source": "partial",
        },
    }


def _build_envelope(
    active_items: List[Dict[str, Any]],
    mitigated_items: List[Dict[str, Any]],
    on_call: Dict[str, Any],
    ai_summaries: Dict[str, str],
    source: str,
    resolved_team_id: int,
    team_name: str,
    lookback_days: int,
    fetched_at: str,
    errors: List[str],
) -> Dict[str, Any]:
    customer_created = [i for i in active_items if str(i.get("source", "")).lower().startswith("customer")]
    system_created = [i for i in active_items if i not in customer_created]
    oncall_primary = (on_call.get("primary") or {}).get("alias") or "?"
    oncall_backup = (on_call.get("backup") or {}).get("alias") or "?"

    return {
        "active_icms": active_items,
        "mitigated_icms": mitigated_items,
        "on_call": on_call,
        "ai_summaries": ai_summaries,
        "source": source,
        "_meta": {
            "team_id": resolved_team_id,
            "team_name": team_name,
            "lookback_days": lookback_days,
            "fetched_at": fetched_at,
            "errors": errors,
            "row_counts": {
                "active": len(active_items),
                "mitigated": len(mitigated_items),
                "ai_summaries": len(ai_summaries),
            },
        },
        # Backward-compat keys for generate_report.py
        "warning": "; ".join(errors) if errors else "",
        "active": active_items,
        "mitigated": mitigated_items,
        "counts": {"active": len(active_items), "mitigated": len(mitigated_items)},
        "customer_created_active": customer_created,
        "system_created_active": system_created,
        "mitigated_highlights": mitigated_items[:5],
        "patterns": [],
        "oncall": {
            "primary": oncall_primary,
            "backup": oncall_backup,
            "team_id": str(resolved_team_id),
            "cached": False,
            "warning": "; ".join(errors) if errors else "",
            "source": source,
        },
    }


# ---------------------------------------------------------------------------
# Public collect() entry point
# ---------------------------------------------------------------------------


def collect(
    config: Optional[Dict[str, Any]] = None,
    team_id: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Collect ICM incident and on-call state for the Android (AHCS) team.

    Returns the ICM envelope consumed by generate_report.py.  Hard failures
    (agency CLI missing, Entra auth timeout) return source="partial" with a
    friendly error message rather than raising, so the report still renders.
    """
    config = config or {}
    icm_cfg = config.get("icm", {})
    resolved_team_id = int(
        team_id
        or icm_cfg.get("team_id")
        or os.getenv("AHCS_ICM_TEAM_ID")
        or 106961
    )
    team_name: str = str(icm_cfg.get("team_name") or "GSA Client - Android")
    lookback_days = int(icm_cfg.get("lookback_days") or 7)
    fetched_at = datetime.now(timezone.utc).isoformat()
    # NOTE: ``lookback_days`` is retained in the envelope for telemetry, but
    # is no longer used as a createdAfter filter on the search_incidents
    # calls below — see D-138.

    errors: List[str] = []
    active_items: List[Dict[str, Any]] = []
    mitigated_items: List[Dict[str, Any]] = []
    on_call: Dict[str, Any] = {"primary": None, "backup": None, "schedule_source": None}
    ai_summaries: Dict[str, str] = {}
    source = "live"

    try:
        client = IcmMcpClient()
    except IcmCollectorError as exc:
        return _partial_envelope(
            team_id=resolved_team_id,
            team_name=team_name,
            lookback_days=lookback_days,
            fetched_at=fetched_at,
            errors=[str(exc)],
        )

    with client:
        # 1. Active incidents (Active + Mitigating)
        #
        # D-138: no dateRange. An open incident is in scope regardless of how
        # long ago it was created — applying createdAfter here previously
        # dropped still-active long-running ICMs (e.g. 798182497, 21000000977796).
        # `top: 50` already caps the result set.
        try:
            raw_active = client.call_tool(
                "search_incidents",
                {
                    "incidentAdvancedSearchRequest": {
                        "owningTeamId": resolved_team_id,
                        "states": ["Active", "Mitigating"],
                        "top": 50,
                    }
                },
                timeout_s=timeout,
            )
            active_items = _parse_incidents(raw_active)
        except Exception as exc:
            errors.append(f"search_incidents(active): {exc}")
            source = "partial"

        # 2. Recently-mitigated incidents
        #
        # D-138: drop createdAfter (upstream API supports only createdAfter /
        # createdBefore, not modifiedAfter — so a recently-mitigated incident
        # created months ago would be filtered out). Instead sort by
        # LastModifiedDate Descending so "Mitigated Highlights" surfaces the
        # most recently mitigated ICMs regardless of creation date.
        try:
            raw_mitigated = client.call_tool(
                "search_incidents",
                {
                    "incidentAdvancedSearchRequest": {
                        "owningTeamId": resolved_team_id,
                        "states": ["Mitigated"],
                        "sortBy": [
                            {"field": "LastModifiedDate", "direction": "Descending"}
                        ],
                        "top": 50,
                    }
                },
                timeout_s=timeout,
            )
            mitigated_items = _parse_incidents(raw_mitigated)
        except Exception as exc:
            errors.append(f"search_incidents(mitigated): {exc}")
            source = "partial"

        # 3. On-call schedule
        try:
            raw_oncall = client.call_tool(
                "get_on_call_schedule_by_team_id",
                {"teamIds": [resolved_team_id]},
                timeout_s=timeout,
            )
            on_call = _extract_on_call(raw_oncall)
        except Exception as exc:
            errors.append(f"get_on_call_schedule_by_team_id: {exc}")
            source = "partial"

        # 4. AI summaries — only for Active/Mitigating or high-sev (≤2)
        for item in active_items:
            if _incident_state(item) not in {"active", "mitigating"} and _incident_sev(item) > 2:
                continue
            inc_id = str(item.get("id") or item.get("incidentId") or "")
            if not inc_id:
                continue
            try:
                raw_summary = client.call_tool(
                    "get_ai_summary",
                    {"incidentId": inc_id},
                    timeout_s=timeout,
                )
                if isinstance(raw_summary, dict):
                    text = raw_summary.get("summary") or raw_summary.get("text") or str(raw_summary)
                else:
                    text = str(raw_summary)
                ai_summaries[inc_id] = text
            except Exception as exc:
                errors.append(f"get_ai_summary({inc_id}): {exc}")
                source = "partial"

    return _build_envelope(
        active_items=active_items,
        mitigated_items=mitigated_items,
        on_call=on_call,
        ai_summaries=ai_summaries,
        source=source,
        resolved_team_id=resolved_team_id,
        team_name=team_name,
        lookback_days=lookback_days,
        fetched_at=fetched_at,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Ad-hoc single-incident fetch
# ---------------------------------------------------------------------------


def fetch_incident(icm_id: Union[int, str]) -> Dict[str, Any]:
    """Fetch a single ICM incident by ID for ad-hoc lookups.

    Returns ``{"details": ..., "description_entries": ...}``.
    Raises IcmCollectorError on failure.
    """
    with IcmMcpClient() as client:
        details = client.call_tool(
            "get_incident_details_by_id",
            {"incidentId": int(icm_id)},
        )
        try:
            context = client.call_tool(
                "get_incident_context",
                {"incidentId": str(icm_id)},
            )
        except Exception:
            context = {}
        return {"details": details or {}, "description_entries": context}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _load_config(config_path: str) -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect Android ICM and on-call data via `agency mcp icm` (D-131-final)."
    )
    parser.add_argument("--config", default=".squad/config.json")
    parser.add_argument("--team-id", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    print(
        json.dumps(
            collect(config=_load_config(args.config), team_id=args.team_id, timeout=args.timeout),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
