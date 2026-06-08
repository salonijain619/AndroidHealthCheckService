"""Tests for tools/icm/icm_collector.py

Single-backend design (D-131-final, 2026-06-04): all ICM data flows through
`agency mcp icm` (Microsoft-internal stdio MCP server). The previous REST +
multi-backend tests were removed when those paths were removed.

Run from the repo root:
    python3 -m unittest tools.icm.tests.test_icm_collector -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.icm.icm_collector import (  # noqa: E402
    IcmCollectorError,
    IcmMcpClient,
    _extract_on_call,
    _parse_incidents,
    _resolve_agency_cmd,
    collect,
    fetch_incident,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ACTIVE_INCIDENT = {
    "id": "12345",
    "title": "Test active incident",
    "severity": 2,
    "status": "Active",
    "source": "System",
}

_MITIGATED_INCIDENT = {
    "id": "12344",
    "title": "Recently mitigated",
    "severity": 2,
    "status": "Mitigated",
    "source": "System",
}

_ONCALL_RESPONSE = {
    "shiftCurrentOnCalls": [
        {
            "currentOnCallContacts": [
                {"alias": "primaryalias", "name": "Primary Person"},
                {"alias": "backupalias", "name": "Backup Person"},
            ]
        }
    ],
}


def _mock_client_with_tools(call_responses):
    """Build a MagicMock IcmMcpClient that dispatches call_tool by name."""
    client = MagicMock(spec=IcmMcpClient)

    def fake_call_tool(name, arguments, timeout_s=60):
        if name in call_responses:
            return call_responses[name](arguments)
        return None

    client.call_tool.side_effect = fake_call_tool
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# agency CLI discovery
# ---------------------------------------------------------------------------


class TestResolveAgencyCmd(unittest.TestCase):
    def test_raises_when_agency_not_on_path(self):
        with patch("tools.icm.icm_collector.shutil.which", return_value=None), \
                patch.dict("os.environ", {"ICM_MCP_COMMAND": ""}, clear=False):
            with self.assertRaises(IcmCollectorError) as cm:
                _resolve_agency_cmd()
            self.assertIn("agency", str(cm.exception))

    def test_default_when_agency_present(self):
        with patch("tools.icm.icm_collector.shutil.which", return_value="/usr/bin/agency"), \
                patch.dict("os.environ", {"ICM_MCP_COMMAND": ""}, clear=False):
            cmd = _resolve_agency_cmd()
        self.assertEqual(cmd, ["agency", "mcp", "icm"])

    def test_env_override(self):
        with patch.dict("os.environ", {"ICM_MCP_COMMAND": "/opt/foo/agency,mcp,icm"}, clear=False):
            cmd = _resolve_agency_cmd()
        self.assertEqual(cmd, ["/opt/foo/agency", "mcp", "icm"])


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------


class TestParseIncidents(unittest.TestCase):
    def test_dict_with_items(self):
        self.assertEqual(_parse_incidents({"items": [1, 2]}), [1, 2])

    def test_dict_with_value(self):
        self.assertEqual(_parse_incidents({"value": [{"id": 1}]}), [{"id": 1}])

    def test_bare_list(self):
        self.assertEqual(_parse_incidents([{"id": 1}]), [{"id": 1}])

    def test_empty_or_unknown(self):
        self.assertEqual(_parse_incidents(None), [])
        self.assertEqual(_parse_incidents("nope"), [])
        self.assertEqual(_parse_incidents({}), [])


class TestExtractOnCall(unittest.TestCase):
    def test_primary_and_backup(self):
        result = _extract_on_call(_ONCALL_RESPONSE)
        self.assertEqual(result["primary"], {"alias": "primaryalias", "name": "Primary Person"})
        self.assertEqual(result["backup"], {"alias": "backupalias", "name": "Backup Person"})
        self.assertEqual(result["schedule_source"], "live")

    def test_empty(self):
        result = _extract_on_call({})
        self.assertIsNone(result["primary"])
        self.assertIsNone(result["backup"])
        self.assertIsNone(result["schedule_source"])

    def test_none(self):
        result = _extract_on_call(None)
        self.assertIsNone(result["primary"])


# ---------------------------------------------------------------------------
# collect() — live path with mocked client
# ---------------------------------------------------------------------------


class TestCollectLive(unittest.TestCase):
    def setUp(self):
        def search_handler(args):
            states = args["incidentAdvancedSearchRequest"]["states"]
            if "Active" in states:
                return {"items": [_ACTIVE_INCIDENT]}
            if "Mitigated" in states:
                return {"items": [_MITIGATED_INCIDENT]}
            return {"items": []}

        self._mock = _mock_client_with_tools({
            "search_incidents": search_handler,
            "get_on_call_schedule_by_team_id": lambda a: _ONCALL_RESPONSE,
            "get_ai_summary": lambda a: {"summary": f"AI summary for {a['incidentId']}"},
        })

    def test_collect_populates_envelope(self):
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=self._mock):
            result = collect(config={"icm": {"team_id": 106961, "lookback_days": 7}})
        self.assertEqual(result["source"], "live")
        self.assertEqual(len(result["active_icms"]), 1)
        self.assertEqual(len(result["mitigated_icms"]), 1)
        self.assertEqual(result["on_call"]["primary"]["alias"], "primaryalias")
        self.assertIn("12345", result["ai_summaries"])
        self.assertEqual(result["counts"]["active"], 1)
        self.assertEqual(result["oncall"]["primary"], "primaryalias")

    def test_collect_calls_tools_with_bare_names(self):
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=self._mock):
            collect(config={"icm": {"team_id": 106961, "lookback_days": 7}})
        call_names = [c.args[0] for c in self._mock.call_tool.call_args_list]
        # All names must be bare (no "ICMProd-" prefix).
        for name in call_names:
            self.assertFalse(name.startswith("ICMProd-"),
                             f"Tool name {name!r} must be bare; agency CLI does not use the prefix.")
        self.assertIn("search_incidents", call_names)
        self.assertIn("get_on_call_schedule_by_team_id", call_names)


# ---------------------------------------------------------------------------
# collect() — partial path when agency CLI is missing
# ---------------------------------------------------------------------------


class TestCollectPartial(unittest.TestCase):
    def test_partial_envelope_when_agency_missing(self):
        with patch(
            "tools.icm.icm_collector.IcmMcpClient",
            side_effect=IcmCollectorError("agency not found"),
        ):
            result = collect(config={"icm": {"team_id": 106961}})
        self.assertEqual(result["source"], "partial")
        self.assertEqual(result["active_icms"], [])
        self.assertIn("agency not found", result["warning"])
        self.assertEqual(result["oncall"]["primary"], "?")
        self.assertEqual(result["_meta"]["team_id"], 106961)

    def test_partial_when_search_tool_raises(self):
        def raising_search(args):
            raise RuntimeError("upstream timeout")

        mock_client = _mock_client_with_tools({
            "search_incidents": raising_search,
            "get_on_call_schedule_by_team_id": lambda a: _ONCALL_RESPONSE,
        })
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=mock_client):
            result = collect(config={"icm": {"team_id": 106961}})
        self.assertEqual(result["source"], "partial")
        self.assertTrue(any("search_incidents(active)" in e for e in result["_meta"]["errors"]))
        # On-call should still populate since its tool worked.
        self.assertEqual(result["on_call"]["primary"]["alias"], "primaryalias")


# ---------------------------------------------------------------------------
# fetch_incident()
# ---------------------------------------------------------------------------


class TestFetchIncident(unittest.TestCase):
    def test_fetch_incident_uses_bare_tool_names(self):
        mock_client = _mock_client_with_tools({
            "get_incident_details_by_id": lambda a: {"id": a["incidentId"], "title": "Test"},
            "get_incident_context": lambda a: {"discussionEntries": []},
        })
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=mock_client):
            result = fetch_incident(798182497)
        self.assertEqual(result["details"]["id"], 798182497)
        self.assertEqual(result["description_entries"], {"discussionEntries": []})
        call_names = [c.args[0] for c in mock_client.call_tool.call_args_list]
        self.assertEqual(call_names[0], "get_incident_details_by_id")
        self.assertFalse(any(n.startswith("ICMProd-") for n in call_names))

    def test_fetch_incident_tolerates_context_failure(self):
        def details(a):
            return {"id": a["incidentId"]}

        def context_fail(a):
            raise RuntimeError("context tool blew up")

        mock_client = _mock_client_with_tools({
            "get_incident_details_by_id": details,
            "get_incident_context": context_fail,
        })
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=mock_client):
            result = fetch_incident(123)
        self.assertEqual(result["details"]["id"], 123)
        self.assertEqual(result["description_entries"], {})


# ---------------------------------------------------------------------------
# D-138 regression — date-filter dropped active long-running ICMs
# ---------------------------------------------------------------------------


class TestSearchIncidentsQueryShape(unittest.TestCase):
    """Regression coverage for D-138.

    Prior to D-138 the Active and Mitigated `search_incidents` calls both
    applied `dateRange.createdAfter = now - lookback_days` which silently
    dropped still-open or recently-mitigated ICMs created more than 7 days
    ago (e.g. 798182497, 21000001038446, 21000000977796, 51000000966797).
    """

    def setUp(self):
        def search_handler(args):
            states = args["incidentAdvancedSearchRequest"]["states"]
            if "Active" in states:
                return {"items": [_ACTIVE_INCIDENT]}
            if "Mitigated" in states:
                return {"items": [_MITIGATED_INCIDENT]}
            return {"items": []}

        self._mock = _mock_client_with_tools({
            "search_incidents": search_handler,
            "get_on_call_schedule_by_team_id": lambda a: _ONCALL_RESPONSE,
            "get_ai_summary": lambda a: {"summary": "x"},
        })

    def _search_calls(self):
        return [
            c.args[1]["incidentAdvancedSearchRequest"]
            for c in self._mock.call_tool.call_args_list
            if c.args[0] == "search_incidents"
        ]

    def _active_request(self):
        for req in self._search_calls():
            if "Active" in req.get("states", []):
                return req
        self.fail("no Active search_incidents call recorded")

    def _mitigated_request(self):
        for req in self._search_calls():
            if req.get("states") == ["Mitigated"]:
                return req
        self.fail("no Mitigated search_incidents call recorded")

    def test_active_query_omits_date_range(self):
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=self._mock):
            collect(config={"icm": {"team_id": 106961, "lookback_days": 7}})
        req = self._active_request()
        self.assertNotIn(
            "dateRange", req,
            "Active/Mitigating search must not apply a createdAfter window "
            "— an open incident is in scope regardless of age (D-138).",
        )
        self.assertEqual(req["owningTeamId"], 106961)
        self.assertEqual(sorted(req["states"]), ["Active", "Mitigating"])

    def test_mitigated_query_omits_date_range(self):
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=self._mock):
            collect(config={"icm": {"team_id": 106961, "lookback_days": 7}})
        req = self._mitigated_request()
        self.assertNotIn(
            "dateRange", req,
            "Mitigated search must not apply createdAfter — recently mitigated "
            "ICMs may have been created long before the window (D-138).",
        )

    def test_mitigated_query_sorts_by_last_modified_desc(self):
        with patch("tools.icm.icm_collector.IcmMcpClient", return_value=self._mock):
            collect(config={"icm": {"team_id": 106961, "lookback_days": 7}})
        req = self._mitigated_request()
        self.assertIn("sortBy", req, "Mitigated search must sort to surface most-recent first")
        self.assertEqual(
            req["sortBy"],
            [{"field": "LastModifiedDate", "direction": "Descending"}],
            "Mitigated search must sort by LastModifiedDate Descending (D-138).",
        )


if __name__ == "__main__":
    unittest.main()
