# Skill: icm-queue-ingest (Android GSA, team 106961)

**Owner (skill maintenance):** Doggett
**Owner (per-run execution):** Scully
**Created:** 2026-06-06
**Adopted from:** HarryPotter squad (Mac, team 115956), discovery date 2026-06-06
**Confidence:** MEDIUM — pattern is fully load-bearing and regression-tested upstream by HP (D-138 test suite), but our first live run against team `106961` lands today; mark HIGH only after one clean unattended cycle.

> Full lineage + rationale: `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/agents/doggett/research/harrypotter-icm-port-plan.md`. **Do not duplicate that doc here** — this skill is the operational summary; the discovery is the audit trail.

---

## What this skill is

The **one canonical pattern** for pulling ICM team-queue data into the daily Android GSA livesite report. It fronts ICMProd via the Microsoft-internal `agency` CLI's stdio MCP proxy (`agency mcp icm`), drives a small JSON-RPC handshake from a Python subprocess, and projects the result into two report sections (`📟 On-Call Today` and `🚨 Active ICM Incidents`). If a future agent asks *"how do I get ICM data into our report?"* — they land here first and stop searching.

## When to use it

- Writing the **daily Android GSA livesite report** (every run includes a fresh ICM pass).
- **On-call check** — confirming primary/backup for the day from authoritative ICM schedule.
- **Live incident triage** — re-running mid-day to refresh active-incident counts and AI summaries.
- **Investigating a telemetry anomaly** that may have a corresponding ICM (use ICM list to confirm/deny customer-visibility, age, ownership).
- **Cross-team routing-rot checks** — opportunistically searching neighbor queues (Mac `115956`, Windows `95422`) for misrouted Android-tagged incidents.

Do **not** use this skill for: incident *creation*, incident *updates* / mitigation posts, or paging operations. It is read-only ingest.

---

## KNOW

### Auth & pre-reqs

**One-time (Saloni only):**

1. Install confirmed at `/Users/salonijain/.config/agency/CurrentVersion/agency` — the Microsoft-internal `agency` CLI.
2. Run `agency mcp icm` interactively **once** to complete the Entra browser auth flow:
   - App registration: `aebc6443-996d-45c2-90f0-388ff96faa56`
   - Scope: `mcp.tools`
   - Backend after auth: `https://icm-mcp-prod.azure-api.net/v1/` → ICMProd
3. Confirm Saloni's corp identity has **read access on ICM team `106961`** ("GSA Client - Android"). Without it, `search_incidents` returns silently empty.

**Recurring (every run):**

- Token auto-refreshed from the AzureAuth cache — **no per-run user prompt**.
- Corp VPN reachable to `icm-mcp-prod.azure-api.net`.
- Python 3.11+ on PATH.

**Dead paths — do NOT re-attempt (HP proved all three don't work):**

- ICM REST API with an `az account get-access-token` bearer (wrong audience; 401).
- Standalone `icm-mcp-server` binary (does not exist as a shippable; only the `agency mcp` subcommand fronts it).
- `agency tool <name>` style invocation (no such surface — must use `agency mcp icm` stdio).

### The mechanism (how it actually works)

The collector spawns `agency mcp icm` as a `subprocess.Popen` child and drives **JSON-RPC 2.0 over stdio**. The handshake is empirically required to be **exactly five steps**:

1. `initialize` — 60s timeout (covers cold-cache browser auth; warm cache returns in ~1s).
2. `notifications/initialized`.
3. `tools/list` — warm-up call.
4. **`time.sleep(WARMUP_DELAY_S)` where `WARMUP_DELAY_S = 6`.** **LOAD-BEARING.** Without it the next `tools/call` races on the upstream error `"A new session can only be created by an initialize request"`. Do not shorten.
5. `tools/call` — the real request, 60s timeout.

**Per-run tool sequence (bare tool names — no `ICMProd-` prefix because we're driving the MCP outside the Copilot runtime):**

| # | Tool | Inputs | Purpose |
|---|---|---|---|
| 1 | `search_incidents` | `teamIds=[106961]`, `states=["Active","Mitigating"]`, `top=50`, `sortBy=[Severity Asc, CreatedDate Desc]`, **no `dateRange`** | Active incidents (both customer- and system-created) |
| 2 | `search_incidents` | `teamIds=[106961]`, `states=["Mitigated"]`, `top=50`, `sortBy=[LastModifiedDate Desc]`, **no `dateRange`** | Recently-mitigated highlights |
| 3 | `get_on_call_schedule_by_team_id` | `teamId=106961` | Primary + Backup for the report header |
| 4 | `get_ai_summary` (optional, per active Sev≤2 ICM) | `incidentId=<id>` | Narrative input for `Patterns:` bullets |

Other 20 tools in the MCP catalog (`get_team_by_id`, `get_incident_context`, `get_mitigation_hints`, `get_similar_incidents`, `get_incident_history`, etc.) are documented in HP's `icm-via-mcp/SKILL.md` for future use but are **not used by our v2 collector**.

### Single source of truth for the team id

`team_id` lives in **`.squad/config.json :: icm.team_id`** (canonical: `106961`). The collector resolves it in this override order:

```
CLI flag --team-id  >  env AHCS_ICM_TEAM_ID  >  .squad/config.json:icm.team_id  >  default (106961)
```

**Never hardcode `106961`** in scripts, templates, narrative, or downstream skills. Same discipline HP enforced in D-117/D-118 for their `115956`.

### D-138: the `dateRange` regression — do not re-introduce

HP earlier versions applied `dateRange.createdAfter = now - 7d` to the Active search and **silently dropped long-running open ICMs created >7d ago** (a Sev3 open for 14 days disappeared from the report). Fix, enforced by the ported regression suite:

- **No `dateRange` on the Active search.** Rely on `states=["Active","Mitigating"]` + `top=50` + `sortBy=[Severity Asc, CreatedDate Desc]`.
- **No `dateRange` on the Mitigated search.** Rely on `states=["Mitigated"]` + `top=50` + `sortBy=[LastModifiedDate Desc]`.
- The `tests/test_icm_collector.py::TestSearchIncidentsQueryShape` cases will fail loudly if a `dateRange` key reappears in the request payload.

### Files (after Scully's port lands)

| Artifact | Path |
|---|---|
| Collector | `/Users/salonijain/workspace/AndroidHealthCheckService/tools/icm/icm_collector.py` |
| Test suite | `/Users/salonijain/workspace/AndroidHealthCheckService/tools/icm/tests/` |
| Per-run raw output | `/Users/salonijain/workspace/AndroidHealthCheckService/tools/icm/runs/icm-run-YYYY-MM-DD.json` |
| Report data drop (for Reyes) | `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/agents/scully/research/icm-team-106961-data-YYYY-MM-DD.md` |
| Config knob | `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/config.json` key `icm.team_id` |

### Report sections this skill populates

In `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/templates/daily-livesite-report.md`:

1. **`📟 On-Call Today`** (header) — Primary + Backup as `display_name (alias)`; schedule footnote `ICM Team 106961 (GSA Client - Android)` with portal link.
2. **`🚨 Active ICM Incidents`** (body) — top-line counts strip (Active / Mitigated / Resolved-3d) + severity rollup line + **three tables**:
   - `👤 Customer-Created Active` — filter active set by `source startswith "customer"`.
   - `🤖 System-Created Active` — complement set (LiveSite / Deployment / etc.).
   - `🟡 Mitigated Highlights` — top 5 by `LastModifiedDate Desc`.
3. **`Patterns:`** narrative bullets (3–6 lines) — owned by Skinner once live: Sev-mix call-outs, `[TestICM]` flags, system-detector silence interpretation, cross-team routing red flags, aging Sev3/4 with no acknowledgement, on-call rotation oddities.

Column shape (all tables): `ICM ID | Sev | Age | Title | Status` (or `… | Mitigated` for the mitigated table). Severity prefix emoji: 🔴 Sev0/1, 🟠 Sev2, 🟡 Sev3, ⚪ Sev4, 🧪 TestICM-tagged. Portal link template: `https://portal.microsofticm.com/imp/v3/incidents/details/<id>/home`.

### Run cadence

- **One-shot per report run** (currently daily, manual via `python3 tools/icm/icm_collector.py --team-id 106961`).
- Future automation: GitHub Actions weekday cron, or local `launchd` plist — mirrors HP's `.github/workflows/daily-report.yml` and `scheduler/launchd/com.harrypotter.dailyreport.plist`. Not committed yet.

---

## DO

### Step 1 — Confirm pre-reqs

```bash
# agency on PATH (or known absolute)?
ls /Users/salonijain/.config/agency/CurrentVersion/agency

# Entra token still warm? (returns ~1s if cached; opens a browser if cold)
agency mcp icm <<< ''   # interactive smoke; Ctrl-C after handshake completes
```

If `agency` is not on the subprocess's PATH at run time, the collector prepends `/Users/salonijain/.config/agency/CurrentVersion/` to the spawned env's `PATH` (see `_resolve_agency_cmd` in the collector).

### Step 2 — Run the collector

```bash
cd /Users/salonijain/workspace/AndroidHealthCheckService
python3 tools/icm/icm_collector.py --team-id 106961 --timeout 60 \
  > tools/icm/runs/icm-run-$(date +%F).json
```

Override hierarchy:

```bash
# CLI flag wins
python3 tools/icm/icm_collector.py --team-id 115956   # spot-check Mac queue

# Env var beats config
AHCS_ICM_TEAM_ID=95422 python3 tools/icm/icm_collector.py   # spot-check Windows queue
```

### Step 3 — Hand the envelope to Reyes

The collector emits a single JSON envelope:

```
{
  "source": "live" | "partial",
  "team_id": 106961,
  "team_name": "GSA Client - Android",
  "oncall": { "primary": {...}, "secondary": {...}, "warning"?: "...", "cached"?: bool },
  "active_icms":     [ {id, title, severity, age, url, status, source}, ... ],
  "mitigated_icms":  [ {id, title, severity, age, url, mitigated_at}, ... ],
  "counts": { "active": N, "mitigated": N, "resolved_3d": N, "by_sev": {...} },
  "_meta": { "errors": [...], "tool_calls": N, "duration_ms": N }
}
```

Reyes consumes this directly. v2 = paste-rendered; v3+ = Jinja2 template fed by a small `render_report.py` (TBD, not in this skill's scope).

### Step 4 — On `source: "partial"`, render the cache banner

If `_meta.errors` is non-empty, the template must render this above the affected tables:

```markdown
> ⚠️ ICM data partial this run — `<first error string>`. Counts below may be incomplete.
```

`collect()` **never raises** — the partial envelope is the contract. Don't add try/except around it in the report-assembly layer.

---

## CHECK

- [ ] `team_id` came from config (or explicit CLI/env override), **never** a hardcoded `106961` literal in a script or template.
- [ ] Handshake retained the 5-step shape including the **6-second sleep** between `tools/list` and the first `tools/call`.
- [ ] **Neither** `search_incidents` call carries a `dateRange.createdAfter` field (D-138 regression).
- [ ] Active search uses `states=["Active","Mitigating"]`; Mitigated search uses `states=["Mitigated"]` + `sortBy=[LastModifiedDate Desc]`.
- [ ] If new ICMs unexpectedly missing, cross-checked against the portal at `https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961` before declaring "quiet day".
- [ ] AI-summary calls only fired for active **Sev ≤ 2.5 + CRIs** (upstream restriction — collector silently skips Sev3/4).
- [ ] Test suite under `tools/icm/tests/` passes — especially `TestSearchIncidentsQueryShape`.

---

## Known failure modes & remediation

| Symptom | Likely cause | Fix |
|---|---|---|
| Handshake hangs on `initialize` past 60s | Cold Entra cache; browser tab opened but not completed | Saloni completes the browser auth; subsequent runs warm |
| Upstream error `"A new session can only be created by an initialize request"` on first `tools/call` | `WARMUP_DELAY_S` reduced below 6s | Restore `WARMUP_DELAY_S = 6` |
| Empty `active_icms` but portal shows incidents | Either (a) D-138 regression re-introduced (`dateRange` slipped back into the payload), or (b) Saloni lost read on team 106961 | (a) Run the test suite — `TestSearchIncidentsQueryShape` will fail loudly. (b) Re-request team membership |
| `403`/`unauthorized` from MCP | Token expired AND silent refresh failed | Re-run `agency mcp icm` interactively to redo browser flow |
| `agency: command not found` in subprocess | Collector spawned with stripped PATH | Verify `_resolve_agency_cmd` prepends `/Users/salonijain/.config/agency/CurrentVersion/` to env PATH |
| `source: "partial"` with `_meta.errors: ["...VPN..."]` | Off corp network | Reconnect VPN; rerun |
| `oncall.primary == "?"` and `oncall.warning` set | `get_on_call_schedule_by_team_id` returned empty (schedule misconfigured for that day) | Render the warning banner verbatim; surface to Saloni for ICM-side schedule fix |
| Sev3/Sev4 active ICMs have no AI summary | **Expected.** Upstream restricts `get_ai_summary` to Sev ≤ 2.5 + CRIs | No action — collector silently skips by design |

---

## Common rationalizations

| Excuse | Rebuttal |
|---|---|
| "Let me query ICM via the REST API + an `az account get-access-token` bearer — fewer moving parts." | HP tried; wrong audience, returns 401. Three dead-end auth paths are recorded in `/Users/salonijain/workspace/HarryPotter/.squad/skills/icm-via-mcp/SKILL.md` § History so this exact attempt isn't repeated. Use `agency mcp icm`. |
| "The 6-second sleep is ugly — let me drop it to 1s." | It's load-bearing. Upstream MCP racing on `initialize` → `tools/call` is the symptom. Do not shorten without writing a regression test that survives 100 cold runs. |
| "I'll just add `dateRange.createdAfter=now-7d` to keep the active list small." | That's the D-138 regression. Long-running open ICMs created >7d ago will silently vanish from the report. Use `top=50` + `sortBy=Severity Asc` for size control instead. |
| "Hardcoding `106961` in the template once is fine — it never changes." | Same logic gave HP a 2-PR refactor when their team id moved environments. Read from `.squad/config.json :: icm.team_id`. Always. |
| "AI summaries are slow (~2s each) — let me skip them entirely." | They're the primary input for Skinner's `Patterns:` bullets when a real Sev2 lands. Keep ON by default; the upstream Sev-cutoff already keeps the call count tiny. |
| "The 24-tool catalog is overkill — let me trim the doc to the 4 we use." | The other 20 are the v3 expansion surface (e.g., `get_similar_incidents` for cross-incident pattern detection). HP keeps them documented for exactly that reason. Leave the reference in the upstream skill. |

---

## Red flags

- A new helper or script references `teamId=106961` as a literal — should always be `config["icm"]["team_id"]` or the env override.
- A diff to `icm_collector.py` adds a `"dateRange"` key under either `search_incidents` payload — instant block, run D-138 suite.
- Handshake step ordering changed, or `WARMUP_DELAY_S` lowered — instant block.
- A report run shows `"oncall": {"primary": "?", ...}` with **no** `warning` field — collector swallowed an error; check `_meta.errors`.
- Someone adds ICMProd to `~/.copilot/mcp-config.json` "for consistency" — irrelevant for our Python-subprocess path and changes the tool names to the `ICMProd-` prefixed form inside the Copilot CLI runtime. Don't conflate the two invocation contexts.
- Active count drops to zero on a day the portal shows incidents — D-138 regression first suspect; ACL loss second.
- New code path calls `search_incidents` with `dateRange` "just for the mitigated highlights" — same regression class, same block.

---

## Citations (HP source — audit lineage here)

- **HP collector (port source):** `/Users/salonijain/workspace/HarryPotter/livesite/scripts/icm_collector.py`
- **HP test suite (port source, includes D-138 regression cases):** `/Users/salonijain/workspace/HarryPotter/livesite/scripts/tests/test_icm_collector.py`
- **HP skill (24-tool catalog, dead-path history, recipes — reference doc, do not duplicate):** `/Users/salonijain/workspace/HarryPotter/.squad/skills/icm-via-mcp/SKILL.md`
- **HP narrative-pattern skill (for Skinner's `Patterns:` bullets):** `/Users/salonijain/workspace/HarryPotter/.squad/skills/mac-active-icm/SKILL.md`
- **HP template blocks ported into our `.squad/templates/daily-livesite-report.md`:** `/Users/salonijain/workspace/HarryPotter/livesite/templates/daily-report.md.j2` lines 15–28 (on-call) + 601–653 (Active ICMs)
- **Our discovery doc (full A–F rationale):** `/Users/salonijain/workspace/AndroidHealthCheckService/.squad/agents/doggett/research/harrypotter-icm-port-plan.md`
- **ICM portal (team dashboard):** `https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961`

---

## Evolution / open follow-ups

- **Programmatic ICM ↔ telemetry cross-reference.** Currently narrative only (Skinner interprets, no code joins `active_icms[].title` against KQL anomalies). HP doesn't do it either. Candidate for v3 if the manual pass keeps surfacing the same correlations.
- **Automate the daily run.** GitHub Actions weekday cron, or local `launchd` plist. Pattern is HP-proven; we don't yet have a CI runner committed.
- **Expand from 4 tools to the full 24.** Specific candidates: `get_similar_incidents` (auto-link the new ICM to historical near-misses), `get_incident_history` (timeline reconstruction for post-mortems), `get_team_by_id` (auto-verify the team name + ACL on every run instead of trusting config).
- **Cross-team routing-rot check.** Add an opportunistic `search_incidents` against `[115956, 95422]` filtered for "android"-mentioning titles — catches misrouted Android incidents in Mac/Windows queues. Cheap (~1s extra). Awaiting Saloni's green-light to include in v2.
- **`cache/icm-last-good.json` persistence.** HP's skill doc references it; HP's collector doesn't actually implement it. v3 work item if we want the report to render last-good data during VPN outages instead of just the partial banner.
- **First-run confidence bump.** Promote this skill to HIGH after one clean unattended cycle against team `106961`.
