# Langly — History

## Day-1 Context

**Project:** Android GSA Client Service Health Check
**User:** Saloni (salonijain619)
**Hired:** 2026-06-10

**What the squad does:** Service health monitoring and reporting for the GSA (Global Secure Access) Android client, which ships as the NAAS subsystem inside Microsoft Defender for Android.

**Why Langly exists:** Microsoft Defender for Android ships frequently. Without a current-version anchor, the report doesn't tell readers whether crash data reflects the latest release or stale builds. Langly's one job is to surface "what's live on Play Store right now" on every report cycle so Frohike's crash data and Scully's telemetry can be interpreted in context.

**Key collaborators:**
- **Frohike** — needs the current Play Store version to interpret per-version crash tables.
- **Reyes** — consumes Langly's one-line header at the top of every daily report.
- **Scully** — cross-references current Play version against server-side `ClientVersion` distributions.

**Package:** `com.microsoft.scmx`

## Learnings

(populated as Langly works)

---

### 2026-06-10 — First pull

**How I reached Play Store today**
- Tried canonical skill first: `…/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md` documents `mcp_google-play-r_get_release_filter_options()` as the authoritative way to get production version codes. The MCP server (`google-play-reporting-server`) is **NOT registered in my toolset** — calling it is not possible from Langly today. Action item for Saloni: wire up the `google-play-reporting-server` MCP so future pulls can read rollout % and ring composition (the public listing does not expose those).
- Fallback that worked: anonymous `curl` of `https://play.google.com/store/apps/details?id=com.microsoft.scmx&hl=en&gl=US` with a Mozilla UA. HTTP 200, ~1.26 MB HTML. No auth needed, no rate-limit hit.

**Response shape (Play Store public listing)**
- Page is a single JS-embedded blob, not clean JSON. Useful anchors:
  - Current published version sits in a small metadata array adjacent to the `Updated on` unix timestamp. Pattern: `[[["<version>"]],[[[<minSdk>]],[[[<targetSdk>,"<displaySdkLabel>"]]]]]`. Today: `[[["1.0.9002.0102"]],[[[36]],[[[30,"11"]]]]]` next to unix `1781068472` (= 2026-06-09 23:14 UTC ≈ "Jun 10, 2026" in US locale).
  - All other version strings on the page (`1.0.8921.0101`, `1.0.8913.0101`, …) appear ONLY inside the user-reviews array — they are the version each reviewer ran, NOT the current published build. Trap to avoid: don't just `grep -o` for the highest version string; anchor to the metadata block.
- Public listing exposes: version string, min SDK, target SDK, "Updated on" date. Does NOT expose: rollout %, ring/track composition, staged-rollout status, version code (only the human-readable version). Those are Play Console–only.

**Today's result**
- Live: `1.0.9002.0102`, updated 2026-06-10. Mainstream `.0102` suffix. Active ramp inferred (Scully shows +51% device growth WoW for this cohort).
- Cross-ref: Scully's "biggest mover" `1.0.9003.0401` (+131% fail-rate) is NOT on the public production track. It's a small (1,003 devices, 2 tenants) `.04xx`-suffix cohort — almost certainly an internal/closed-test ring. End-user blast radius from `.04xx` is currently zero on Play Store production. Dropped a decision note for the team.

**Next-pull shortcut**
- One-liner that reliably extracts current version + date from the public listing (works as of 2026-06-10):
  ```
  curl -sS -A "Mozilla/5.0 (Linux; Android 13)" "https://play.google.com/store/apps/details?id=com.microsoft.scmx&hl=en&gl=US" \
    | python3 -c "import sys,re,json,datetime as dt; h=sys.stdin.read();\
ver=re.search(r'\[\[\[\"(\d+\.\d+\.\d+\.\d+)\"\]\],\[\[\[\d+\]\],\[\[\[\d+', h);\
ts=re.search(r'\"(\w{3} \d{1,2}, 20\d{2})\",\[(\d{10})', h);\
print('version', ver.group(1) if ver else 'NOT FOUND');\
print('updated', ts.group(1) if ts else 'NOT FOUND', '(unix', ts.group(2) if ts else '-', ')')"
  ```
- If that pattern breaks (Google reshuffles the JS blob), fall back to: pull all `\d+\.\d+\.\d+\.\d+` matches, ignore any that occur >1MB into the file (those are review-block versions), keep the one that appears with the smallest byte-offset near the "Updated on" anchor.

2026-06-10: First Play Store version pull. Live production = `1.0.9002.0102` (updated 2026-06-10). Reframed `.04xx` (1.0.9003.0401) as INTERNAL ring, not live customer pain. Used Play Store public listing fallback (google-play-reporting-server MCP not wired).

### 2026-06-10 — Section producer landed (`tools/report_generator/sections/langly_version.py`)

**Scrape-path HTML landmarks (the parser relies on two regex anchors)**
- **Version anchor (primary):** `\[\[\["(\d+\.\d+\.\d+\.\d+)"\]\],\[\[\[\d+\]\],\[\[\[\d+` — the production-version string sits inside a small metadata array immediately adjacent to the min-SDK / target-SDK / display-SDK tuple. This is the ONLY place on the page where the *current published* version lives. Every other 4-segment version on the page is inside a user-review record (the version that reviewer was running) and must be ignored.
- **Version anchor (cheap pre-try):** JSON-LD `"softwareVersion": "X.Y.Z.W"`. Currently absent from the listing in 2026-06 but cheap to try first; if Google ever adds it back, we win for free.
- **Released-date anchor:** `"(Mon DD, YYYY)",[<10-digit unix>,…` — but the listing carries SEVERAL 10-digit unix stamps (first-publish 2020, last-update, per-review timestamps). I take `max()` across all matches so we always land on the most recent — the "Updated on" date. First implementation took `.search()` (first match) and produced `2020-08-17` against today's live page. Fixed.

**Fragility notes**
- Both anchors are content-DOM-free regexes against a JS blob Google reshuffles freely. Expect breakage on a 6–12 month horizon. When it breaks: pull the live HTML, locate the human-displayed version string in the rendered page, then `grep -c` candidate regexes against the raw HTML to find an anchor pattern that uniquely identifies the current-version slot (not the review-record slots).
- The scrape path can NEVER read rollout %, ring composition, or version code. Those require Play Console / Publisher API auth. Today `produce()` returns status `PARTIAL` (not `GO`) whenever scrape is the path used, so downstream consumers can flag the missing rollout %.
- Default-arg pitfall caught in tests: do NOT default a function parameter to a module-level path constant — it's captured at def time and breaks monkeypatching. Resolve at call time instead.

**Producer-contract anticipatory call**
- Module defines its own local `SectionResult` dataclass (markdown / status / data). When Mulder lands `.squad/decisions/inbox/mulder-report-generator-architecture.md`, swap the import in one line and delete the local dataclass.

**Idempotency model**
- Rolling-log update touches `**Last pull:**` timestamp every run; only prepends a new history row when the version string actually changed vs the top of the table. Verified by running CLI twice for `--date 2026-06-10` and confirming the table row count did not grow.

**CLI smoke (2026-06-10):** `python -m tools.report_generator.sections.langly_version --date 2026-06-10` returns status PARTIAL (scrape path; Publisher API not wired) and prints the exact 06-10 report header line for `v1.0.9002.0102`. No creds-needed decision file was written — scrape alone keeps Langly's contract alive, so wiring Publisher API is a *quality improvement* (gives us rollout %), not a blocker.

**Mulder contract integration (same day, after first pass)**
- Discovered `tools/report_generator/contracts.py` already in place — Mulder's architecture decision had landed in parallel. Swapped the local stub `SectionResult` for the canonical one in two edits: (1) `from tools.report_generator.contracts import Section, SectionResult, Status`, (2) `produce()` now returns the full canonical shape with `section=Section.LANGLY_VERSION`, enum `Status`, `metadata=` (renamed from local `data=`), `errors=[]`, `drop_path=`, `elapsed_s=`. Orchestrator's duck-type adapter would have accepted the stub but the explicit shape is cleaner and survives `isinstance` checks. All 45 tests across the four sibling sections still pass.
