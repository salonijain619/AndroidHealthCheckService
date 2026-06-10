# reyes — Learnings

## Project Context
Android GSA Client Service Health Check. Telemetry: server-side NAAS (Kusto), client-side AppInsights + Aria Kusto. Report: daily livesite → Teams IDNA GSA channel.

## Key Learnings (Consolidated)

**Report assembly evolution (v1→v4):**
- v1 (06-05): NAAS-only daily from Scully's 7d data, skeleton template established.
- v2 (06-06): Added live ICM roster + Active ICM section.
- v3 (06-09): Fresh NAAS refresh; headline P2 promoted to P2→P1 trend; Microsoft 1P hypothesis falsified; .04xx ring + EU regions escalated.
- v4 (06-10): 3-source fusion (Scully server + Frohike Play Vitals + Langly Play Store version). Langly header leads; Server↔Client correlation table added; .04xx demoted to P3 ring-risk (not live); EU crash-rate finding promoted.

**Assembly invariants (enforced by assembler.py):**
1. Langly version header immediately under H1, before Exec Summary.
2. Section order closed: H1 → Langly → Scope → Reframe (optional) → On-Call → Exec Summary → Key Metrics (Scully/Frohike subsections) → ICM → Contributors → Run Diagnostics.
3. Server↔Client subsections in Key Metrics are PEERS (separate denominators, never merged).
4. Run Diagnostics always at bottom for Saloni's triage.
5. No new sections without decision file.

**Exec-summary bullet logic:** Render order (langly, scully, frohike, skinner). For each: take `metadata['exec_bullet']` if present, else omit (don't invent). Degrade to sentinel ⚠️ if SKIP/FAIL.

**Teams re-fire pattern (06-10T17:37):** Payload `{"text":"<markdown>"}` (json.dumps escaping), urllib.request POST, Content-Type: application/json. HTTP 202 = success.

**Gotchas:** Date format `%-d` (GNU) fails on Windows → fallback chain `%-d` → `%#d` → manual strip. Langly header if FAILed → degraded line (not omit). ICM PARTIAL → canonical phrasing verbatim for continuity.

## 2026-06-10T17:43+05:30 — Track 3+4 shipped: on-call wiring (PR #1)

Paired with Skinner; Reyes owned the assembler + YAML fallback. Branch `track3-track4-file-based-icm-oncall`.

### Learnings
- **On-call precedence chain (assembler `_resolve_oncall`):**
  1. `ctx['oncall_primary']` / `ctx['oncall_backup']` (explicit override from orchestrator).
  2. `sections['skinner_icm'].metadata['on_call'] = {primary, backup}` — Skinner publishes this when it loads `.squad/agents/skinner/icm-latest.json`.
  3. `.squad/config/on-call.yaml` — `schedule[].{from, to, primary, backup}`; pick the entry whose `from <= date <= to`.
  4. Literal `TBD`.
- **YAML reader is PyYAML-optional.** Ships an inline minimal parser for the documented shape so the assembler stays import-clean if PyYAML isn't on the runner. PyYAML used when present.
- **JSON shape consumed (from icm_collector):** Skinner publishes only the on-call sub-shape into metadata, but full payload also has `active_icms` / `mitigated_icms` / `_meta.fetched_at` (used as `pull_date`).
- **Freshness gate is Skinner's, not Reyes's.** Skinner returns PARTIAL with stale note if > 48h; assembler still gets `metadata['on_call']` populated and uses it. So an aging JSON keeps the on-call current as long as the rotation didn't change.
- **Fallback YAML location:** `.squad/config/on-call.yaml`. Reyes reads, Saloni hand-maintains for OOF / mid-week rotation changes.
- **Test invariant updated:** old `test_oncall_falls_back_to_TBD_when_missing` now asserts `TBD-update-me` (the YAML seed). New companion test exercises the Skinner-metadata path explicitly.
**Structural changes vs v2:**
1. **Headline severity promoted.** Anchor insight moved from 🟡 P2 to 🟠 **P2-trending-P1** per Scully's direction (6/05=0.354% → 6/06=0.416% → 6/07=0.431% → 6/08=0.447%, single +0.55pp day from 1% threshold). Added a stand-alone bullet to Exec Summary calling this out as a "second step up, not stabilization" — distinct framing from v1/v2's "5× ramp / sustained plateau" language.
2. **Cross-domain candidate REMOVED.** v1/v2 candidate #1 ("Microsoft 1P dogfood rollout driving regression") explicitly **struck through and labeled FALSIFIED** in the Cross-Domain section, with Scully's S6b non-1P probe cited as the falsifying evidence (non-1P fail-rate 0.49–0.60%, HIGHER than global). First time a v3 had to retract a prior-cycle hypothesis publicly — used strikethrough + bold "FALSIFIED today" to make the retraction unambiguous.
3. **New top single-version anchor swapped in.** v1 had flagged `.0102` ring; v3 promotes `1.0.9003.0401` (`.04xx` flavor) to Top Insight #2 — devices +55%, fail-rate +131%, concentrated in 2 tenants. Doggett task: "identify what `.04xx` actually is."
4. **EU regional cluster promoted to its own Top Insight (#4).** Multiple EU regions accelerating in lockstep (germanywestcentral +67%, NorthEurope +61%, SwedenCentral +114%, WestEurope +53%) — v1/v2 had buried this under Insight #2 (Private Access); v3 separates because the ServiceType-uniform-degradation finding now makes "Private Access path" too narrow a frame.
5. **NEW Insight #5: PROFILE_UNDEFINED widening.** Device count +41% (245→345) outpacing event count +10% — reframed from "low-volume race condition" (v1) to "client config/onboarding bug suspect" (v3). Severity 🟡 P3/watch.
6. **Data Quality recurring row escalated.** Created a dedicated "Recurring DQ Row" table inside Data Quality Notes with status `🔴 OPEN 4d, no upstream fix` and explicit "Recommended Action: file schema/normalization ticket" for both ghost columns and region casing. Previously buried as prose bullets in v1/v2.
7. **Detector silence escalated to 3-pull pattern.** ICM Patterns + Cross-Domain both call out "3 consecutive pulls with zero auto-ICMs against a 6× ramp" — v2 had 1 pull as a data point; v3 has structural pattern.
8. **Contributors footer extended** to list v3 deliverables (Scully's fresh NAAS + S6b probe; Reyes's v3 assembly with hypothesis retraction).

**Asymmetric freshness framing:** NAAS is fresh today (06-09 run), ICM is 1 day old (06-08, no movement). Explicitly labeled both windows in the `> v3 note:` and on the ICM section header.

### 2026-06-10 — Team expansion: Report now pulls from Scully + Frohike + Langly in parallel

Daily report assembly (Reyes) now pulls from three parallel sources: Scully (server-side NAAS telemetry), Frohike (Google Play Console crash/ANR analysis, NAAS-filtered), and Langly (current Play Store version of `com.microsoft.scmx`). Lead every daily/weekly report with Langly's one-line Play Store version header to anchor crash/ANR data to the currently shipping Defender version. Frohike replaces Scully's ad-hoc Play Vitals ownership and outputs `.squad/agents/frohike/research/naas-crashes-{date}.md`. ICM investigations also fan out to Frohike for client-side crash signature matching. Framing rule: all Play Vitals output MUST be NAAS-as-a-unit, never Defender-filtered-to-NAAS.

### 2026-06-10T12:45+05:30 — First 3-source daily assembled (Scully + Frohike + Langly fusion)

Assembled `daily-livesite-report-android-2026-06-10.md` (25,082 bytes) — first daily that fuses three parallel research sources. Pattern crystallized:

**3-source assembly pattern:**
1. **Langly's Play Store version header goes FIRST** (right under the title, above Executive Summary). It is the anchor that contextualizes every per-version number downstream. Without it, server-side and client-side version cohorts cannot be classified as "live customer" vs "internal ring."
2. **Scully (server-side NAAS) + Frohike (client-side Play Vitals) are PEERS, not nested.** Key Metrics now has TWO labeled subsections ("Server-side / Scully" and "Client-side / Frohike") — never merge their denominators. Server denominator = NAAS sessions; client denominator = whole-app `com.microsoft.scmx` installs. The "Denominator framing rule" callout is mandatory.
3. **Frohike gets its own top-level section** ("NAAS Client Stability (Google Play Vitals)") placed AFTER Key Metrics and BEFORE Top Insights. Per-version table is PRIMARY; top crashes/ANRs are top-3 with hypothesis (NOT all 8); subsystem breakdown is the closer.
4. **Cross-Domain section gets a new "Server↔Client per-version alignment" table.** First time we can show same-shape corroboration on a per-version axis. The .04xx ring (server +131% fail-rate ⟷ client 33.7% native SIGSEGV concentration ⟷ Langly "not on prod track") was the cleanest dual-signal example to date.

**Narrative reframes that came out of the 3-source fusion (would NOT have been possible with Scully alone):**
- **`.04xx` ring DEMOTED** from yesterday's top P2 anchor to forward-looking P3 ring-promotion risk. Langly's "live prod = 9002.0102, not 9003.0401" is the trigger; Frohike's "all 4 .04xx SKUs are sub-privacy-threshold install base, crash-only with 0 ANR" is the corroboration. Made explicit in Exec Summary lead-in.
- **EU finding PROMOTED** to top P2 cross-domain anchor. Frohike independently surfaced Germany 3.25% whole-app crash rate (over Google's 1.09% Play Console bad-behavior threshold) — same region cluster Scully sees server-side. Added new framing: "Play Store visibility/ranking risk, independent of NAAS attribution."
- **Server↔client correlation strongest at `libnaas_native_vpn.so` SIGSEGV** (Frohike Top-Crash #3, 33.7% .04xx). Cleanest code-localized evidence the ring-promotion risk is real.

**Structural rules that survived from v3 (06-09) into this report:**
- On-Call kept as compact 2-row table (no metadata prose).
- ICM reused at prior freshness with explicit "live as of X, no movement" header + weekly-cadence footnote.
- Microsoft 1P falsified hypothesis kept with strikethrough for retraction visibility.
- Detector silence pattern (3+ pulls, zero auto-ICMs) escalated each cycle.

**Removed per Saloni's approved 06-09 template:** Patterns section, Data Completeness Notes, Data Quality Notes tail. Did NOT re-introduce.

**Sizing:** Target was 18–22KB; landed at 25KB. The new "NAAS Client Stability" section is ~7KB on its own (per-version table + 2 top-N tables + subsystem breakdown). Acceptable on a first-fusion daily; can trim subsystem breakdown to prose next cycle if Saloni wants the bound enforced.

**Decision worth promoting:** Lead every future daily/weekly with Langly's one-line Play Store version header. Filed to `.squad/decisions/inbox/reyes-play-store-version-header-first.md`.

2026-06-10: Assembled v4 daily livesite report (25,489 bytes) integrating Frohike Play Vitals + Langly version data. Led with `.04xx` reframe + Germany 3.25% EU cross-domain finding. Proposed version-line header convention (decision filed).

### 2026-06-10T14:46+05:30 — Wave-3 assembler shipped (`tools/report_generator/assembler.py`)

Implemented Mulder's Wave-3 module per the architecture decision in `.squad/decisions/inbox/mulder-report-generator-architecture.md`. 8/8 tests passing.

## Learnings

**Assembly invariants (the rules the assembler enforces, lifted from the 06-10 manual report):**

1. **Langly version header sits immediately under H1, not under an H2.** This is the §8.4 validator invariant and Saloni's lead-with-Play-Store-version decision (2026-06-10 in `.squad/decisions.md`). The assembler emits it as the very first non-H1 block; if Langly FAILed, it falls back to a clearly-degraded line rather than omitting (per Mulder §7).
2. **Section order is closed.** H1 → Langly header → Scope → (optional Reframe) → On-Call → Exec Summary → Key Metrics (Scully then Frohike, in that order) → ICM → Contributors → Run Diagnostics. **Reyes does NOT introduce new sections without a new decision file.**
3. **Server-vs-client framing is mandatory.** Key Metrics has two labeled subsections ("Server-side / Scully" and "Client-side / Frohike"). Never merge their denominators. The assembler tolerates a producer including its own `###` header (passes through) or omitting one (assembler injects the canonical header).
4. **`scully_server_telemetry` vs `scully_server` alias.** Mulder's spec uses the long form; the task brief abbreviated. The assembler accepts both via `_SCULLY_KEYS` so producers and the orchestrator can converge without churn.
5. **Run Diagnostics table is at the very bottom.** Saloni triages failed runs from this single table — it must always render, regardless of section health.

**Exec-summary bullet selection rule:**

- Iterate `_ORDER = (langly, scully, frohike, skinner)` — fixed render order, matches the 06-10 narrative cadence (anchor first, server ramp, client cross-domain, structural/ICM).
- For each section: take `metadata['exec_bullet']` if present. If absent, **silently omit** — do not fabricate. This is the "DO NOT invent data" rule operationalised.
- If status is SKIP or FAIL: replace the bullet with `_⚠️ {section_name} unavailable this run — see logs._` (sentinel line for visibility without blocking the report).
- Prepend the section emoji ONLY if the producer didn't already lead with an emoji — preserves producers' tone (Scully's 🟠, Frohike's 🌍) while back-filling Langly's 📱 when omitted.

**Date format gotcha — captured in `format_date_header()`:**

- `%-d` is a GNU/POSIX extension. Doggett's Ubuntu CI runs it fine; Windows dev boxes do not.
- Three-tier fallback: `%-d` → `%#d` (Windows) → `%d` with manual leading-zero strip. The test `test_date_header_formatting` covers both two-digit (`Jun 10`) and one-digit (`Jun 5`) cases.

**Voice/tone notes from re-reading 06-10 (the things the assembler must NOT break):**

- **Data-forward, blunt, no hedging.** Exec bullets lead with the number, not the framing. The assembler doesn't add prose — it just stitches.
- **Emoji as severity grammar.** 🟠 = P2, 🟡 = P3, 🔴 = structural/blocking, ✅ / ⚠️ / ❌ for status. The Run Diagnostics table uses the same vocabulary so triage is consistent with the body.
- **Side-by-side server↔client framing.** The two Key Metrics subsections are PEERS — never nested. The assembler enforces this by always emitting both subsection headers in order, even when one section is degraded.
- **Stubs are explicit, not blank.** Per Mulder §7: a FAILed section becomes a blockquote pointing to `tools/report_generator/runs/{date}/errors.log`. A SKIPped section becomes a `⏭️` blockquote. ICM PARTIAL gets the canonical "_ICM data not refreshed in this run (CI auth limitation). Last manual pull: {date}._" phrasing — verbatim continuity with the 06-10 manual report so Saloni sees the same shape whether ICM ran or didn't.

**Defensive-imports pattern (worth keeping):** `contracts.py` is Doggett's file and was not yet in tree when this landed. The assembler does `try: from tools.report_generator.contracts import …` then falls back to a local `dataclass` mirror. This made my module standalone-testable; when Doggett ships contracts.py, the import flips automatically and the tests stay green because they import `SectionResult`/`Status` from the assembler (which re-exports whichever source won).

**Test-fixture sizing lesson:** First test run failed the 5KB floor because my fixture markdown was unrealistically thin (~3.7KB total). Real producers ship per-section tables of 1–7KB. Bumped Scully fixture to the 9-row metrics table from 06-10 and Frohike to the 7-row metrics table + 4-row per-version table. Now naturally lands ~7KB, well inside the 5–30KB validator band. **Takeaway:** test fixtures should approximate real producer output size, not just shape — otherwise the size invariant test is meaningless.

## 2026-06-10T19:00+05:30 — Local-runner kit for v1 (manual daily report)

Branch: `reyes-local-runner` off `master`. Task B in Mulder's local-first-v1 design.

### Shipped (`tools/local-runner/`)
- `preflight.sh` — fail-fast checks: az login, Play SA JSON (env or default path), ICM cache age (warn >24h, fail >48h), Keychain webhook entry (`security -s ahcs-livesite-webhook`), `googleapiclient` import. Green ✅ summary on pass; actionable fix-it lines on each failure.
- `_load_webhook.sh` — tiny sourced helper; exports `AHCS_TEAMS_WEBHOOK_URL` from Keychain. Never echoes the URL.
- `run-daily.sh` — entry point. `--date YYYY-MM-DD` flag (defaults to today UTC). Runs preflight → loads webhook → invokes `python -m tools.report_generator.cli` → POSTs `{"text": <md>}` via `jq -Rs` + `curl`, expects HTTP 202. Tees to `~/Library/Logs/ahcs-livesite/run-<UTC>.log`. Idempotent on re-run (generator overwrites; we repost).
- `com.microsoft.ahcs.livesite.plist` — launchd scaffold for 09:30 IST daily. **Not installed in v1.** Top-of-file XML comment block warns against installing until Phase 1.5.
- `README.md` — one-time setup, daily use, Phase 1.5 launchd enablement, troubleshooting matrix, uninstall.

### Learnings / decisions made along the way
- **Env var name**: Saloni's spec said `AHCS_TEAMS_WEBHOOK_URL`; Mulder's design said `WEBHOOK_URL`. Used `AHCS_TEAMS_WEBHOOK_URL` (Saloni's spec wins, more specific name).
- **Schedule**: 09:30 IST = 04:00 UTC. Used local-time `StartCalendarInterval{Hour:9,Minute:30}` since Saloni's laptop is on IST — launchd uses local TZ.
- **Webhook secrecy invariant**: URL is loaded into env var only; never printed in logs; not in any committed file. `_load_webhook.sh` writes the error to stderr without echoing the URL.
- **bash 3.2 compat**: no associative arrays, no `mapfile`, no `&>` redirection inside `tee` pipeline — used `exec > >(tee -a) 2>&1` which works on 3.2.
- **Report path**: not parsed from CLI stdout (fragile); computed deterministically as `daily-livesite-report-android-${date}.md` at repo root, matching `tools/report_generator/config.py:REPORT_FILENAME_TEMPLATE`.
- **jq dependency**: required for safe JSON escaping (markdown can contain backticks, quotes, newlines). Documented `brew install jq` in README + troubleshooting.

### Preflight dry-run on Saloni's box (2026-06-10)
- ✅ az login active as salonijain@microsoft.com
- ✅ PLAY_CONSOLE_SA_KEY resolved to default path
- ❌ ICM cache missing (Saloni needs `bash tools/icm/refresh-local.sh`)
- ❌ Webhook not in Keychain (Saloni needs one-time `security add-generic-password ...`)
- ❌ `googleapiclient` not importable in plain `python3` (Saloni needs venv activated)

All three failures are expected one-time setup items — captured in PR description.

### Did NOT touch (per coordination)
- `tools/report_generator/sections/frohike_play_vitals.py` (Frohike's parallel branch)
- `.github/workflows/daily-livesite-report.yml` (CI stays inert per Mulder §3)
- Any generator/assembler Python

### 2026-06-10T18:40+05:30 — Bug: PLAY_CONSOLE_SA_KEY not propagating from preflight to generator (PR #4)

Saloni's first end-to-end `./tools/local-runner/run-daily.sh` showed preflight green ("PLAY_CONSOLE_SA_KEY resolved to default: …/google-play-sa.json") but Frohike still returned PARTIAL with "PLAY_CONSOLE_SA_KEY and GOOGLE_APPLICATION_CREDENTIALS both unset". Branch `reyes-fix-sa-key-export`, PR #4.

## Learnings

- **Subprocess `export` does not propagate to parent.** `preflight.sh` was invoked as `bash "${SCRIPT_DIR}/preflight.sh"` from `run-daily.sh`, so its `export PLAY_CONSOLE_SA_KEY=…` fallback only affected the preflight subprocess. The parent shell's environment was unchanged, and the Python generator the parent later spawned saw the var as unset. This is a classic POSIX shell pitfall — env mutation only flows down, never up.
- **Fix pattern: extract env-resolution into a sourceable file.** Created `tools/local-runner/_resolve_credentials.sh` modelled on the existing `_load_webhook.sh`. `run-daily.sh` sources it BEFORE invoking preflight so the export happens in the parent shell. `preflight.sh` also sources it (idempotent, silent) so it stays usable as a standalone debugging entrypoint.
- **Design split codified: "preflight verifies, parent shell does env setup."** Anything in the local-runner kit that needs to be visible to the Python generator (or any sibling child process) MUST be exported in run-daily.sh's shell, never inside preflight. Preflight is now strictly verification — it reads env state and reports pass/fail/fixit, never mutates anything that needs to outlive its own process.
- **Same pattern would apply if we ever default-resolve `GOOGLE_APPLICATION_CREDENTIALS`, `AZURE_SUBSCRIPTION_ID`, etc.** Add the resolution to `_resolve_credentials.sh` (single sourced file, ordered before preflight) — do not be tempted to put it in preflight just because preflight is "where checks live."
- **Verification:** After fix, runner reached Play Developer Reporting with authenticated credentials (HTTP 400 on `crashRateMetricSet:query` for end_date=2026-06-10 vs freshness 2026-06-09 — a data-window bug, not auth). The "both unset" message is gone. Invariant-2 size failure remains for Mulder.

### 2026-06-10T18:42+05:30 — Invariant-2 local policy shipped (Mulder Option C)

Branch `reyes-invariant-2-local-policy`. Implemented Mulder's
`mulder-invariant-2-local-policy.md` Option C: local-runner skips
invariant-2 gating, CI stays strict. Three changes: `--no-fail-on-validation`
flag in `run-daily.sh`, post-generator banner that reads
`validation.json` and prints a `⚠️ Report posted DEGRADED` block when
`passed: false`, and the `test_validation_passes_on_2026_06_10_report`
relaxation to tolerate `invariant-2:` failures specifically. End-to-end
verified: report posted to Teams (HTTP 202), pytest 4/4 green.

## Learnings

- **"Diagnostic-loud, gate-soft" is the right local-runner posture.** The
  one-line `--no-fail-on-validation` flag plus a stderr-loud banner gives
  Saloni everything she needs (the report shipped, validation still ran,
  failures are surfaced in the terminal AND on disk in validation.json)
  without making the runner abort on a calibration-mismatch like the
  06-10 5KB floor. CI's posture is the inverse — gate-strict, because CI
  runs in the "fully healthy" world by construction. Encoding the
  asymmetry as a single CLI flag (no code-fork between local/CI paths)
  keeps both behaviors honest.

- **Banner placement matters more than banner content.** Mulder's spec
  said "before the Teams post," and that's load-bearing: if you print
  the banner after curl, a curl failure (or even just `set -e` killing
  the script on HTTP 5xx) buries the degradation signal under whatever
  error follows. Printing before the POST means Saloni sees "shipped
  degraded, here's why" even if the very next step blows up.

- **Always sanity-check banner code paths even when validation passes
  on the live run.** Today's runner happened to land at 5735 bytes
  (Frohike's freshness-window fix from a sibling branch pushed us over
  the floor), so the banner naturally didn't fire end-to-end. Instead
  of declaring victory, swap in a synthesized `validation.json` with
  `passed: false` and exec just the banner block — five seconds of
  shell, catches typos in the jq expressions or the conditional. Don't
  trust untested error paths.

- **Test-relaxation pattern: "tolerate ONLY this specific failure,
  catch everything else."** The temptation with a sample that has a
  known-bad invariant is to write `assert True` or skip the test. The
  pattern that survives review is
  `assert failures == [] or all(f.startswith("invariant-N:") for f in failures)`
  — it keeps the regression surface intact for the other 8 invariants
  while tolerating the one we're explicitly allowing. Docstring MUST
  cite the decision doc and the backlog item that restores full coverage,
  otherwise the relaxation rots into "all invariants are optional."

- **`git stash pop` after `git checkout -b` brings unrelated working-tree
  modifications onto the new branch.** Caught this when the post-checkout
  status showed `frohike_play_vitals.py` and other sibling-branch edits
  alongside my real changes. Lesson: when stashing across branch creation,
  use `git add -- <only-my-files>` followed by `git commit -- <only-my-files>`,
  never `git commit -a`. Verified the commit contains only the three
  files in Mulder's checklist + the decision/backlog drops + this
  history append.
