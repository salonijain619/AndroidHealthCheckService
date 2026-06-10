# GSA Client Marketplace — Plugin & Skill Inventory

**Author:** Doggett (Android Engineer)
**Date:** 2026-06-05
**Source clone:** `/Users/salonijain/workspace/Identity-gsa-client-marketplace/`
**Upstream:** `https://msazure.visualstudio.com/One/_git/Identity-gsa-client-marketplace` (`gsa-client-plugins`)
**Sister marketplace (cross-cutting):** `https://msazure.visualstudio.com/One/_git/Identity-GSA-Marketplace` (`gsa-plugins`)
**Status:** Inventory complete for everything except `gsa-kusto-catalog` (owned by Scully this cycle).

---

## 1. Marketplace contract (what the README + AGENTS.md establish)

- **Two-tier model.** This repo is the **client sub-system** marketplace. Anything client-codebase-, client-telemetry-, client-packaging-, or on-device-debugging-specific lives here. Cross-cutting tooling (PR review, git, planning, server-side Kusto, livesite bootstrapping) lives in `gsa-plugins`.
- **Plugin layout (reference: `gsa-client-telemetry-toolkit`):**
  ```
  plugins/<plugin>/
  ├── .claude-plugin/plugin.json     # name, version, description, maintainers
  ├── README.md                      # human docs
  ├── skills/<skill>/SKILL.md        # agent instructions (KNOW/DO/CHECK + Rationalizations + Red Flags)
  └── (optional) commands/, TESTING.md
  ```
- **SKILL.md required sections:** `## KNOW`, `## DO` (numbered `### Step N — Title`), `## CHECK` (`- [ ]` evidence), `## Common Rationalizations` (≥3), `## Red Flags` (≥3). **Body < 500 lines.** Frontmatter `description` ≤ 250 chars. Long reference data → `references/` sibling files or a wiki page fetched at runtime, never inlined.
- **MCP-first / no installers.** Plugins should NOT ship per-plugin installers. Configure shared MCP servers (`ICMProd`, `ADOProd`, `AzureMCP`, `workiq`, `kusto`) via `/mcp-setup` from `gsa-plugins`. If a plugin must mutate user files, it must be idempotent + take timestamped backups + bail safely + ship `TESTING.md`.
- **Catalog reuse rule.** GSA NaaS Kusto routing (clusters/databases/tables/aliases) lives in `gsa-kusto-catalog/catalog.json`. Other skills should depend on it instead of redefining cluster URLs.
- **Validation gates.** `/test-skill` (format) and `review-skill` (content) from `gsa-plugins` are run before PR review.
- **Install UX:**
  ```
  /plugin marketplace add <repo-url>
  /plugin install <plugin>@gsa-client-plugins
  ```

## 2. Skill inventory (this cycle)

`gsa-kusto-catalog` is intentionally excluded — Scully owns the catalog read this cycle.

| # | Skill path (relative to `plugins/gsa-client-telemetry-toolkit/skills/`) | Purpose | Tools / agents | Android-relevance | Verdict |
|---|---|---|---|---|---|
| 1 | `gsa-client-telemetry-toolkit/SKILL.md` | KNOW/DO/CHECK conventions for running GSA / NaaS KQL through the Kusto MCP — Aria (Win/Mac/Android/iOS) + ADX server clusters. Encodes routing rules, identity rules (Client_Id vs DeviceInfo_Id, ban on UserInfo_Id), Aria platform filtering, time-column conventions, alias resolution, Graph reverse-lookup recipe. | `kusto-list_tables`, `kusto-get_table_schema`, `kusto-execute_query`, `Bash`, `Read`, `Edit`, `Create`, `ADOProd-wiki_get_page_content` | **HIGH (8/10)** — explicitly names `android-appinsights / wd-prod-android-client` as the Android client telemetry home (NOT Aria), and codifies `App_Platform == 'Android'` as the Aria-side filter when Android signals show up there. Identity rules apply to Android sessions identically. | **REFERENCE** |
| 2 | `setup-prereqs/SKILL.md` | Bootstrap checklist: Node.js, `kusto-mcp-server`, MCP registration, `az login`, per-cluster scopes (`kusto.aria.microsoft.com`, `idsharedwus.kusto.windows.net`), `gsa-plugins` marketplace, `mcp-setup`, optional `bluebird` code-search MCP. | `Bash`, `Read` | **MEDIUM (5/10)** — platform-agnostic, but every Android squad member who wants to run the toolkit has to walk this exact list. Cleanest single document for new-member onboarding. | **REFERENCE** |

> Skill #3 in the marketplace — `gsa-kusto-catalog/` (catalog.json + catalog-semantics.json + SKILL.md) — is being inventoried in parallel by Scully and is the largest reuse target overall. Cross-reference: `.squad/agents/scully/research/` (Scully's parallel artifact this cycle).

### Per-skill verdicts in detail

#### Skill 1 — `gsa-client-telemetry-toolkit` → **REFERENCE (do not copy)**

- **Why REFERENCE, not ADOPT:** This skill is a *consumer* of `gsa-kusto-catalog/catalog.json` via the relative path `../gsa-kusto-catalog/`. Copying the SKILL.md alone into `.squad/skills/` would break that path and lose the routing data underneath. It also references seven IdentityWiki pages at runtime via `ADOProd-wiki_get_page_content`, which we don't have wired up in this squad's MCP set.
- **What we use it for:** authoritative source on (a) Android client telemetry lives in App Insights `wd-prod-android-client`, NOT Aria; (b) Aria's `App_Platform` filter is required when an Android signal does land there; (c) `Client_Id` vs `DeviceInfo_Id` joining/dcounting rules; (d) `UserInfo_Id` is access-restricted and returns 400 — never use it. Cite the file path from this clone in our daily report and in Scully's KQL skill.
- **Action:** add a one-line pointer entry in `.squad/skills/android-kusto-starter/SKILL.md` ("for cross-platform routing/identity rules see `Identity-gsa-client-marketplace/plugins/gsa-client-telemetry-toolkit/skills/gsa-client-telemetry-toolkit/SKILL.md`"). Do not duplicate prose.

#### Skill 2 — `setup-prereqs` → **REFERENCE (link, don't fork)**

- **Why REFERENCE:** It already exists upstream, gets maintained by the toolkit owner, and prescribes the canonical bootstrap. Forking it into `.squad/skills/` invites drift. The squad's only on-ramp need is "tell me how to get the Kusto MCP working for Android queries", which this skill answers verbatim.
- **Action:** in our top-level `.squad/README.md` (or wherever onboarding currently lives), link to this SKILL.md path as the "first-time setup" reference. Do not author our own bootstrap doc.

## 3. Android-specific signals harvested

Direct, citable findings about how the GSA Android client integrates with Defender / surfaces in telemetry — derived purely from the marketplace clone (no WD.Client.Android repo access required):

1. **Android telemetry pipeline differs from Win/Mac.** The toolkit's routing cheat-sheet (SKILL.md line 96) says: `Android client behavior → cluster=android-appinsights, database=wd-prod-android-client, NOT Aria`. This is the strongest signal yet that the GSA Android module emits through Defender's existing **App Insights** pipeline, not Aria/1DS. The `wd-prod-android-client` database name maps directly onto the WD (Windows Defender) brand — confirms Saloni's "GSA is a module inside Defender for Android" framing.
2. **iOS analog points to the same pattern.** `iOS client behavior → cluster=ios-mdatp, database=MDATPiOSDB` (`customEvents`). Both mobile platforms use Defender-owned App Insights, while desktop (Win/Mac) uses the GSA-owned Aria pipeline. The asymmetry is structural, not accidental — GSA's mobile telemetry is hosted by Defender's mobile telemetry stack.
3. **Identity rules are pan-platform.** `Client_Id` (rotates on Entra repair/rejoin, can be empty for broken-auth devices) and `DeviceInfo_Id` (stable hardware-derived) apply identically to Android sessions. `UserInfo_Id` is access-restricted in Aria — never use it for joins.
4. **Aria fallback for Android.** When Android signals do appear in shared Aria tables (e.g., `mnap_xplat_telemetry*`), the platform filter is `App_Platform == 'Android'` (string literal, exact case). Aria's database GUID is `f0eaa94222894be599b7cd0bc1e2ed6f` (prod) — already in our context, now corroborated.
5. **Graph reverse-lookup recipe.** `Client_Id → owner` via Graph `/users/{upn}/ownedDevices` with `operatingSystem` mapping to `App_Platform` — works for Android (`Android` → `Android`). Useful when Skinner needs to attach a user to a device from a single Client_Id captured in a crash trace.
6. **What the marketplace does NOT contain.** No Defender-Android crash reporter wiring, no `*Telemetry*` helper class names, no checked-in KQL for Android specifically (the catalog ships *aliases*, not raw queries scoped to Android). No mention of Doze/battery-optimization, foreground-service notification health, OEM mix, work-profile vs personal split. **All of those still require WD.Client.Android repo access.**

## 4. Marketplace conventions Squad should mirror

- **`.squad/skills/<name>/SKILL.md` should adopt the same five-section structure** (KNOW / DO / CHECK / Common Rationalizations / Red Flags) the GSA marketplace standardized on. Body < 500 lines, frontmatter description ≤ 250 chars. Our existing `android-kusto-starter` SKILL should be retrofitted to this shape on the next pass.
- **No installers in skills.** Anything that needs to mutate `~/.copilot/mcp-config.json` defers to `mcp-setup@gsa-plugins`. We should adopt the same posture so we don't ship a per-squad installer.
- **Catalog-as-data, not prose.** Long reference content (per-event field tables, error-code dictionaries, OEM mix, panel-to-query mappings) goes in `references/*.json` next to SKILL.md, not inline. Scully's dashboard panel mapping is a candidate for this treatment.
- **Wiki-fetched references for very long-lived content.** The toolkit puts seven reference docs (Cluster Routing, Identity Rules, MCP Failure Triage, Per-Event Fields, Mac State Vocabulary, Auth Event Taxonomy, Codebase Correlation) on IdentityWiki and fetches them on demand. If our daily-report assembly grows long auxiliary references, this is the pattern.
- **Two-tier routing guide.** When deciding where a future Squad asset lives — internal to this squad vs. proposed upstream into `gsa-client-plugins` — apply the marketplace's own scope test: "is this client-codebase / client-telemetry / on-device specific?" If yes, it could be promoted; if no, it stays in the squad.

## 5. Integration plan

| Squad asset | Action | Justification |
|---|---|---|
| `.squad/skills/android-kusto-starter/SKILL.md` | **Update** to (a) link to `gsa-client-telemetry-toolkit/SKILL.md` for routing/identity/Aria rules; (b) add a `## KNOW` callout that Android client telemetry actually lives in `android-appinsights / wd-prod-android-client` (App Insights), and our existing 7 NaasProd-server-side queries are *complementary* to — not replacements for — the App Insights data. Retrofit to KNOW/DO/CHECK/Rationalizations/Red Flags shape on the next dedicated pass. | Closes the highest-value gap from the marketplace inventory without any copy. |
| `.squad/agents/scully/charter.md` | **Update** Scully's responsibilities to explicitly include "consume `gsa-kusto-catalog/catalog.json` as routing source-of-truth for any cross-cluster question; flag when our queries diverge from a catalog alias." (Coordinate with whoever owns Scully's charter file.) | Mirrors the marketplace's catalog-reuse rule and prevents drift from the canonical alias library. |
| `.squad/agents/doggett/charter.md` | **Update** to reference `gsa-client-telemetry-toolkit` SKILL as the canonical place to check for cross-platform identity rules and the App Insights routing for Android client telemetry. | Anchors my own charter to a maintained upstream rather than restating the rules locally. |
| `.squad/agents/skinner/charter.md` (Severity classifier) | **Update** to call out that Android crash/error telemetry is reachable via App Insights `wd-prod-android-client` (not Aria) — affects how Skinner sources signals. | Same App Insights signal, owned by the engineer who classifies severity from that data. |
| `.squad/skills/<setup>` | **Do not create.** Link to `setup-prereqs/SKILL.md` from `.squad/README.md` instead. | Avoids forking a maintained doc. |
| `.squad/skills/gsa-client-telemetry-toolkit/SKILL.md` | **Do not create / do not copy.** Reference by absolute path. | Toolkit depends on a sibling catalog and seven wiki pages we don't have. |

## 6. Open questions still requiring WD.Client.Android repo access

These are unchanged by the marketplace inventory — they remain blocked behind the VSTS auth wall and will be picked up when access is granted:

1. The Android telemetry helper class name(s) inside the Defender-for-Android codebase (`*Telemetry*`, `*Logger*`, `*EventNames*`).
2. Whether App Insights `wd-prod-android-client` is fed by **OneDS / 1DS** SDK on device, by App Insights direct, or by a custom Defender uploader. (The marketplace identifies the destination cluster, not the on-device emitter.)
3. The crash-reporter implementation (Crashlytics / AppCenter / OneDS / in-house Defender uploader) and its event taxonomy.
4. Any pre-existing `.squad/`, `.copilot/`, `agents/`, `skills/`, or `plugins/` directories inside WD.Client.Android — the marketplace does not enumerate them, only references them at the *Identity* layer (`Identity-ZTNA-NaaS-Agent` is the GSA *agent* repo, not WD.Client.Android).
5. Whether KQL / Workbook JSON specific to Android is checked into WD.Client.Android (the marketplace catalog does not surface raw Android KQL, only aliases).
6. The Android `EventName` constants used by the GSA module — needed to map error codes (505, APS `SuccessSettingsNotFound`, etc.) to client emit sites.
7. Defender for Android's Android-version / API-level / OEM-mix dashboards (if any), to see whether our seven proposed report fields (Doze kill rate, foreground-service notification health, work-profile split, etc.) overlap with existing Defender telemetry.

## 7. Recommended adoption count (summary)

| Verdict | Count | Skills |
|---|---|---|
| ADOPT (copy into `.squad/skills/`) | **0** | — |
| REFERENCE (link by path, don't copy) | **2** | `gsa-client-telemetry-toolkit`, `setup-prereqs` |
| SKIP (not Android-relevant) | **0** | — |

**Net:** zero copies, two references, two charter updates, one starter-skill update, one onboarding-readme link. No bulk-copy this run — proposing the plan for Mulder's ack.
