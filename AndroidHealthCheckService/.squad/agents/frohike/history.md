# Frohike — History

## Day-1 Context

**Project:** Android GSA Client Service Health Check
**User:** Saloni (salonijain619)
**Hired:** 2026-06-10

**What the squad does:** Service health monitoring and reporting for the GSA (Global Secure Access) Android client, which ships as the NAAS subsystem inside Microsoft Defender for Android. The squad pulls telemetry, tracks ICM incidents (team 106961), and produces daily/weekly service health reports.

**Why Frohike exists:** Saloni needed a dedicated owner for Google Play Console crash data, framed strictly as NAAS-only (not Defender-general). The squad iterated on crash reporting 4 times before this role was created — the lesson was: NAAS-as-a-unit framing is non-negotiable, and Play Vitals must be the source of truth over AppEvents.

**Key collaborators:**
- **Scully** — server-side NAAS telemetry (NaasProd Kusto). Cross-reference her `.04xx` ring findings against client crash data.
- **Reyes** — assembles the final daily report. Frohike's drop feeds Reyes's "Google Crash Report" / "NAAS Client Stability" section.
- **Langly** — provides current Play Store Defender version so Frohike knows what's live vs what's seeing crashes.

**Canonical skill:** `/Users/salonijain/workspace/android/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md` — read this first on every pull.

**Prior crash drops (pre-Frohike, Scully-authored):**
- `.squad/agents/scully/research/naas-crashes-2026-06-09.md` — 4-iteration deep dive that established the per-Defender-version table format and `.04xx` ring over-index finding (13–14× client crash concentration corroborating server-side anchor)

## Learnings

(populated as Frohike works)
