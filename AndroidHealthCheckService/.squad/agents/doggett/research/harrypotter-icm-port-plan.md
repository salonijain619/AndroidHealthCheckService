# HarryPotter ICM Integration — Discovery + Port Plan

- **Source repo:** `/Users/salonijain/workspace/HarryPotter` (cloned 2026-06-06)
- **Target squad:** AndroidHealthCheckService
- **ICM target queue:** `106961` (Saloni's GSA Android queue — `https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961`)
- **Discovery date:** 2026-06-06
- **Read-only discovery — no ICM API calls made this pass.**

---

## A. How Mac Gets ICM Data

**One backend, decisively.** Per HP's `D-131-final` (memorialized in `/Users/salonijain/workspace/HarryPotter/.squad/skills/icm-via-mcp/SKILL.md` and the docstring of `/Users/salonijain/workspace/HarryPotter/livesite/scripts/icm_collector.py`), all ICM data flows through **`agency mcp icm`** — the Microsoft-internal `agency` CLI's stdio MCP proxy, which fronts `https://icm-mcp-prod.azure-api.net/v1/` → ICMProd. That same MCP server is also (separately) registered in Copilot's `~/.copilot/mcp-config.json` under the name `ICMProd`; when called from inside the Copilot CLI session, tool names get the `ICMProd-` prefix; when driven from a Python subprocess they are bare (`search_incidents`, `get_on_call_schedule_by_team_id`, etc.).

**Auth.** Interactive **Entra browser flow** on first run only (private app reg `aebc6443-996d-45c2-90f0-388ff96faa56`, scope `mcp.tools`), token cached by AzureAuth thereafter — so subsequent runs are unattended. Cold-cache UX = `agency mcp icm` opens a browser tab; warm-cache = ~1s init. **No env-var secret, no PAT, no Azure CLI bearer** — HP tried three alternative auth paths (REST + `az` token, hypothetical standalone `icm-mcp-server`, `agency tool` subcommand) and recorded all three as dead ends in `icm-via-mcp/SKILL.md` § History.

**Mechanics.** `livesite/scripts/icm_collector.py` is the only Python entry point. It `subprocess.Popen`s `agency mcp icm`, drives JSON-RPC 2.0 over stdio, and follows an empirically-required 5-step handshake:
1. `initialize` (60s timeout for browser auth)
2. `notifications/initialized`
3. `tools/list` (warm-up)
4. **Sleep `WARMUP_DELAY_S = 6` seconds** — without this the next `tools/call` races on `"A new session can only be created by an initialize request"`
5. `tools/call` (real request, 60s timeout)

Refresh cadence = **one-shot per report run**, kicked off by `livesite/scripts/generate_report.py` calling `icm_collector.collect(config, timeout=60)` once per scheduled `make report-deliver` cycle. Scheduler is either GitHub Actions weekday 06:00 UTC (`.github/workflows/daily-report.yml`) or local launchd 09:00 (`scheduler/launchd/com.harrypotter.dailyreport.plist`).

**Endpoints actually hit (bare tool names):**
- `search_incidents` (two calls per run — Active+Mitigating; Mitigated)
- `get_on_call_schedule_by_team_id` (single call)
- `get_ai_summary` (per active ICM, optional)

**Config knob.** `icm.team_id` in `.squad/squad.yml` (HP value: `115956`), with env override `HP_ICM_TEAM_ID` and CLI flag `--team-id`. The agency CLI invocation itself can be overridden with env `ICM_MCP_COMMAND=/path/to/agency,mcp,icm` (comma-separated).

---

## B. Fields & Sections Mac Surfaces

Template: `/Users/salonijain/workspace/HarryPotter/livesite/templates/daily-report.md.j2`. Two sections drive off ICM data:

**1. Header — `📟 On-Call Today`** (lines 15-28)
- 🔴 Primary: `display_name (alias)`
- 🟡 Backup:  `display_name (alias)`
- Schedule footnote: `ICM Team <team_id> (<team_name>)`
- Cache/warning banner if `oncall.cached` or `oncall.warning` set.

**2. Body — `🚨 Active ICM Incidents`** (lines 601-653)
Top-line counts strip: `🔴 Active: N  |  🟡 Mitigated: N  |  🟢 Resolved (3d): N` + optional `Severity:` rollup line. Then three tables:

| Sub-section | Columns | Source |
|---|---|---|
| `👤 Customer-Created Active` | `ICM ID • Sev • Age • Title • Status` | `search_incidents` states=`Active,Mitigating`, filtered by `source startswith "customer"` |
| `🤖 System-Created Active` | same | same call, complement set (LiveSite / Deployment / etc.) |
| `🟡 Mitigated Highlights` | `ICM ID • Sev • Age • Title • Mitigated` | `search_incidents` states=`Mitigated`, sorted `LastModifiedDate Descending`, top 5 |

Plus a `**Patterns:**` bullet list — plain-English narrative (3-6 lines) produced by Severus per `mac-active-icm/SKILL.md` Step 6: Sev mix call-outs, `[TestICM]` flags, system-detector silence interpretation, cross-team routing red flags, aging Sev3/4 with no acknowledgement, on-call rotation oddities.

**Per-incident projection** (`mac-active-icm/SKILL.md` Step 2): `{id, title, severity ("Sev<N>"), age ("Nd (created YYYY-MM-DD)"), url=https://portal.microsofticm.com/imp/v3/incidents/details/<id>/home, status}`.

**Severity discipline.** Sev enum is `[0,1,2,3,4,25]`. AI-summary tools (`get_ai_summary`, `get_mitigation_hints`, `get_similar_incidents`, `get_incident_context`) are restricted by upstream to **Sev ≤ 2.5 + CRIs only** — collector silently skips for Sev3/4.

**Cross-reference to telemetry findings:** *not done programmatically*. HP keeps the cross-reference in Rita Skeeter's narrative pass + Severus's `Patterns:` bullets. There is no code path that joins `active_icms[].title` against KQL anomalies. Worth noting but not a blocker for us.

**Failure-degrade contract.** `collect()` never raises. If `agency` is missing or Entra times out it returns `source:"partial"` with `_meta.errors:[...]`, populated `oncall.primary="?"`, `warning=...` — and Rita's template renders a yellow banner instead of an empty section.

**D-138 lesson (worth porting verbatim):** earlier HP versions applied `dateRange.createdAfter = now - 7d` to the Active search and silently dropped long-running open ICMs created >7d ago. Fix = **no `dateRange` on Active or Mitigated searches**; rely on `states` + `top:50` + `sortBy LastModifiedDate Desc`. There are regression tests in `livesite/scripts/tests/test_icm_collector.py::TestSearchIncidentsQueryShape` we should mirror.

---

## C. Reusable vs HP-Specific

### Reusable nearly verbatim (port as-is, change literals only)

| Asset | HP path | Notes |
|---|---|---|
| **Auth pattern + JSON-RPC client** | `livesite/scripts/icm_collector.py` lines 1-290 (`IcmMcpClient`, `_resolve_agency_cmd`, error type) | Zero HP-isms — pure mechanics of driving `agency mcp icm`. |
| **Response parsers** | `icm_collector.py` lines 297-344 (`_parse_incidents`, `_extract_on_call`, `_incident_state`, `_incident_sev`) | Generic. |
| **Envelope builders** | `icm_collector.py` lines 351-447 (`_partial_envelope`, `_build_envelope`) | Generic — only `team_name` default string is HP-flavored. |
| **`collect()` orchestration** | `icm_collector.py` lines 455-590 | The 3-call sequence (active / mitigated / on-call / optional AI summaries) is queue-agnostic. |
| **Test suite** | `livesite/scripts/tests/test_icm_collector.py` | All 12 tests are HP-neutral except the `team_id=115956` literal. |
| **MCP tool catalog reference** | `.squad/skills/icm-via-mcp/SKILL.md` (24 tools, recipes, failure modes, history-of-dead-paths) | Should be ported wholesale into our `.squad/skills/` so future spawns don't re-derive. |
| **Template section blocks** | `daily-report.md.j2` lines 15-28 (on-call) + 601-653 (Active ICMs) | Drop into Reyes's report template as new sections. |
| **D-138 query-shape regression tests** | same test file | Port the discipline to prevent us re-introducing the bug. |

### HP-specific (must substitute on port)

| What | HP value | Our value |
|---|---|---|
| ICM team id | `115956` | **`106961`** |
| Team display name | `GSA Client - MacOS` | `GSA Client - Android` (Saloni to confirm exact ICM display) |
| Cross-team check ids | `[95422]` (Windows triage) | `[95422]` is plausibly still useful (Windows squad); maybe also Mac `115956`. Saloni to confirm. |
| Persona/charter wrapper | `Severus Snape` / `icm-oncall-warden` | Either new agent **Skinner-ICM** or extension of existing `skinner` charter — see Section D. |
| ICM portal deep-link template | `…/details/<id>/home` | Same — portal URL is global. |
| Scheduler triggers | GH Actions cron + launchd plist | We don't yet have a CI runner; manual `python -m … icm_collector` per report cycle is fine for v2. |

### HP pre-reqs they assume

- **Microsoft-internal `agency` CLI installed.** ✅ Already present in Saloni's env at `/Users/salonijain/.config/agency/CurrentVersion/agency`.
- **Python 3.11+** with `pyyaml` (already in our environment).
- **First-run interactive browser** to complete Entra auth (Saloni one-time action).
- **VPN / corp network** reachable to `icm-mcp-prod.azure-api.net` (Saloni's normal posture).
- ICMProd MCP **NOT required** to be registered in `~/.copilot/mcp-config.json` for the Python collector path — that registration is only for Copilot's runtime convenience. Saloni's current `~/.copilot/mcp-config.json` does NOT have ICMProd; we don't need to add it.

---

## D. Concrete Port Plan

### Topology decision

**Port as a new skill + extend Scully (data) + extend Reyes (template).** Do NOT spin up a new agent. Rationale:

- HP has 11 agents and dedicated Severus because their squad fans out wide. Our squad has 7 and `skinner` already owns "incident process" per his charter. Adding a 9th is overhead for one collector + one template block.
- The work cleanly splits across existing roles: **Scully** runs the collector (it's just another telemetry/data fetch in her wheelhouse), **Doggett** owns the skill doc (architecture/auth/MCP knowledge, which is my charter), **Reyes** owns the template section, **Skinner** owns the narrative `Patterns:` bullets when there's a live incident worth interpreting.

### Step-by-step

| # | Action | Path | Owner |
|---|---|---|---|
| 1 | **Create `.squad/skills/icm-queue-ingest/SKILL.md`** by copy+adapt of HP's `icm-via-mcp/SKILL.md`. Substitute `115956 → 106961`, `GSA Client - MacOS → GSA Client - Android`. Keep the 24-tool catalog, handshake sequence, failure-mode table, and history-of-dead-paths verbatim — future-you will need them. | `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/skills/icm-queue-ingest/SKILL.md` | Doggett (this drop is the input; Scribe will commit) |
| 2 | **Port the collector script.** Copy `/Users/salonijain/workspace/HarryPotter/livesite/scripts/icm_collector.py` → `/Users/salonijain/workspace/AndroidHealthCheckService/tools/icm_collector.py`. Change default team_id `115956 → 106961` (line ~472), default `team_name → "GSA Client - Android"` (line ~474). Keep `D-138` no-`dateRange` logic. Keep `WARMUP_DELAY_S=6`. | `tools/icm_collector.py` (new top-level `tools/` dir — we don't have a `livesite/` package yet) | Scully (executes once Saloni green-lights auth) |
| 3 | **Port tests.** Copy `livesite/scripts/tests/test_icm_collector.py` → `tools/tests/test_icm_collector.py`. Substitute `115956 → 106961` in fixtures and assertions. | `tools/tests/test_icm_collector.py` | Scully |
| 4 | **Wire a config knob.** Add to whatever our squad config equivalent is (or introduce minimal `.squad/config.json` key): `icm.team_id: 106961`, `icm.team_name: "GSA Client - Android"`, `icm.cross_team_ids: [115956, 95422]` (Mac + Windows for routing-rot check), `icm.active_states: ["Active","Mitigating","Correlating"]`, `icm.lookback_days: 7`. | `.squad/config.json` (extend) | Doggett (proposes), Scribe (commits) |
| 5 | **Extend Reyes's report template** with two new sections: replace current placeholder `📟 On-Call Today` (which says "TBD") with HP's table block; insert a new top-level section `## 🚨 Active ICM Incidents` after `## 🔍 Top 5 Insights` and before `## 🔥 Cross-Domain Correlation Analysis`, mirroring HP's three-table layout (customer / system / mitigated highlights + Patterns bullets). | `.squad/templates/daily-livesite-report.md` (or wherever Reyes's template lives — check her agent dir) | Reyes |
| 6 | **One-shot smoke test by Saloni.** Run `python3 tools/icm_collector.py --team-id 106961 --timeout 60` interactively to complete the Entra browser flow; token will then be cached for unattended runs. | terminal | Saloni |
| 7 | **Bake into report cycle.** Reyes's report-assembly invocation calls `icm_collector.collect(config={"icm":{"team_id":106961}})` and pipes the envelope into the Jinja2 template (we'll add a tiny `render_report.py` later if/when we move to templated rendering — for v2 Reyes can paste the rendered tables manually). | new tools/render integration | Reyes + Scully |
| 8 | **Charter touch-ups.** Add one paragraph to `.squad/agents/skinner/charter.md` ("owns ICM narrative interpretation when active incidents land in v2+ reports") and `.squad/agents/scully/charter.md` ("runs `tools/icm_collector.collect()` as part of standard data pass"). | charters | Skinner / Scully (each amends own) |

### What plugs into queue `106961`

A single config key — **`icm.team_id: 106961`** — read at runtime by `collect()` (line ~470). Override hierarchy (mirrors HP): CLI flag `--team-id` → env `HP_ICM_TEAM_ID` (rename to `AHCS_ICM_TEAM_ID` for us) → config file → default. The team_id literal **must not be hardcoded anywhere downstream** (template, skill, Reyes's narrative) — same discipline as HP's D-117/D-118.

### Auth pre-reqs Saloni must satisfy before v2 runs

1. **Run `agency mcp icm` once interactively** to complete the Entra browser auth. Token caches in AzureAuth — subsequent runs unattended. Saloni already has `agency` installed; this is a 30-second action.
2. **Verify ACL on team `106961`.** Saloni's Entra identity must be a member of the team (or have read-on-team) to see incidents via the MCP. The `get_team_by_id` call will surface auth issues immediately.
3. **VPN / corp network** when running (`icm-mcp-prod.azure-api.net` is corp-fronted).

No other secret/PAT/webhook required for the **ingest** path. (Delivery to Teams is a separate question we're not solving in this pass.)

---

## E. v2 Report Section Markdown Template

Drop these into the next Android report as drop-in replacements / additions. Counts/IDs are placeholders Scully will fill at run time.

### Replace current `📟 On-Call Today` (which is `TBD`)

```markdown
## 📟 On-Call Today

| Role | Engineer |
|---|---|
| 🔴 **Primary** | {{ oncall_primary.display_name }} ({{ oncall_primary.alias }}) |
| 🟡 **Backup**  | {{ oncall_secondary.display_name }} ({{ oncall_secondary.alias }}) |

_Schedule:_ ICM Team **106961** (GSA Client - Android) —
[portal](https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961)

> ⚠️ If `oncall.warning` set: render banner verbatim (e.g. "ICM data served from cache (age: 4h)").
```

### New section — insert after `🔍 Top 5 Insights`, before `🔥 Cross-Domain Correlation Analysis`

```markdown
## 🚨 Active ICM Incidents

🔴 **Active: {{ icm_active_count }}** &nbsp;|&nbsp; 🟡 **Mitigated (7d): {{ icm_mitigated_count }}** &nbsp;|&nbsp; 🟢 **Resolved (3d): {{ icm_resolved_3d_count }}**

**Severity:** Sev0: 0 · Sev1: 0 · Sev2: {{n}} · Sev3: {{n}} · Sev4: {{n}}

### 👤 Customer-Created Active ({{ count }})

| ICM ID | Sev | Age | Title | Status |
|---|---|---|---|---|
| [798182497](https://portal.microsofticm.com/imp/v3/incidents/details/798182497/home) | Sev3 | 12d (created 2026-05-25) | <truncate title to 80 chars> | Active |
| — | — | — | _No customer-created active ICMs_ | — |

### 🤖 System-Created Active ({{ count }})

| ICM ID | Sev | Age | Title | Status |
|---|---|---|---|---|
| — | — | — | _No system-created active ICMs_ | — |

### 🟡 Mitigated Highlights (top 5 by LastModifiedDate)

| ICM ID | Sev | Age | Title | Mitigated |
|---|---|---|---|---|
| — | — | — | _No mitigated highlights in the lookback window_ | — |

**Patterns:**

- Plain-English bullet (3-6). Examples:
  - "Quiet 7d on team 106961 — N active, all Sev≥3, no customer-reported."
  - "Active Sev2 #<id> aging Nd without acknowledgement — primary should triage today."
  - "Zero system-detected (LiveSite/Deployment) ICMs this week — telemetry-driven detectors silent; weigh against KPI deltas before declaring 'healthy'."
  - "ICM #<id> tagged `[TestICM]` by <alias>, recommend cleanup."
  - "Mac-tagged incident found under team 95422 — routing rot, flag to Mulder."

> Per D-138 (port from HP): the Active and Mitigated `search_incidents` calls do **not** apply `dateRange.createdAfter`. Open or recently-mitigated long-running ICMs created >7d ago must still surface.
```

**Sort order (per `mac-active-icm/SKILL.md` Step 2):** Active tables sort by `Severity Ascending` then `CreatedDate Descending` (lowest sev number = most severe first, then newest). Mitigated table sorts by `LastModifiedDate Descending`. Cap each table at `top:50`; truncate display to first 10, with a "... and N more" footer if needed.

**Severity color rendering (markdown-safe):** prefix the Sev cell with the emoji: `🔴 Sev0/Sev1`, `🟠 Sev2`, `🟡 Sev3`, `⚪ Sev4`, `🧪 TestICM` (surface, do not filter).

**Cache-degrade banner** (above any table whose source is `partial`):
```markdown
> ⚠️ ICM data partial this run — `<error string from _meta.errors>`. Counts below may be incomplete.
```

---

## F. Open questions / blockers for Saloni

1. **Entra interactive auth for `agency mcp icm`.** Has Saloni already completed it in a prior session, or is the first `agency mcp icm` invocation still pending? If pending, this is the only manual step before our first run.
2. **Team membership on `106961`.** Confirm Saloni's corp identity has read on team `106961` in ICMProd. If not, `get_team_by_id`/`search_incidents` will return empty silently.
3. **Cross-team routing list.** HP checks `[95422]` (Windows triage). For us, candidates are `95422` (Windows) and `115956` (Mac, HP's team). Worth checking both for "Android-tagged" misrouting? Saloni call.
4. **Lookback window for "Mitigated Highlights".** HP uses 7d; our scope-lock is also 7d. Confirm 7d is right for v2.
5. **Should AI-summary calls be on by default?** HP fires `get_ai_summary` for active Sev≤2.5 ICMs. Slow (~2s each) but high-value narrative input. Default ON for us?
6. **Where does `tools/icm_collector.py` ultimately live?** We don't have a `livesite/` package skeleton yet. Proposal: top-level `tools/` for v2; promote to a proper `androidlivesite/scripts/` package when we mirror HP's full template-rendering flow in v3.
7. **Do we want the cross-team routing-rot check in v2, or defer to v3?** It's one extra MCP call per cross-team id. Cheap. Recommend ON.
8. **Caching policy on `_meta.errors` paths.** HP renders cache-age banners but doesn't actually persist a `cache/icm-last-good.json` in the checked-in collector — the cache key is referenced in skill doc but not implemented in `icm_collector.py`. Likely intended for v3. We can skip in v2 and rely on the `partial` banner.
9. **Confirm portal URL pattern matches Android.** HP uses `https://portal.microsofticm.com/imp/v3/incidents/details/<id>/home`. Same domain should work for all team queues, but worth a one-click confirm on a real `106961` incident.
