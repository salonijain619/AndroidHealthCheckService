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
