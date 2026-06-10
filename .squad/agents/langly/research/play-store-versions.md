# Microsoft Defender for Android — Play Store Version Tracker

**Package:** `com.microsoft.scmx`
**Maintained by:** Langly (Release Tracker)
**Last pull:** 2026-06-10

---

## 🟢 Current Live Version (Play Store production track)

| Field | Value |
|---|---|
| **Version** | `1.0.9002.0102` |
| **Release / "Updated on" date** | 2026-06-10 |
| **Rollout state** | Unknown from public listing — Play Console auth required to read staged-rollout %. Inferred to be **actively rolling** (Scully telemetry shows this cohort growing 13.3K → 20.2K devices, +51% week-over-week — consistent with a live ramp, not 100% saturation). |
| **Active rings (visible publicly)** | Production: `1.0.9002.0102`. Closed/internal rings NOT visible on the public listing — only inferable from server-side telemetry (Scully sees `1.0.9002.0402`, `1.0.9003.0401`, `1.0.9002.0202` cohorts; `.04xx` suffix consistently small + concentrated → almost certainly internal/closed-test ring). |
| **Public-listing version code (arm64)** | Inferred `900200122` per skill convention (last 3 digits = ABI+min-API; arm64 ends in `2`). Awaiting Play Console confirmation. |

### Source & confidence

- **Primary attempted:** Google Play Reporting MCP (`mcp_google-play-r_get_release_filter_options`) — **NOT REACHED**. The `google-play-vitals` skill exists at `…/WD.Client.Android-icm-copilot/.github/skills/google-play-vitals/SKILL.md` and defines the right tool, but the underlying `google-play-reporting-server` MCP is not registered in Langly's current toolset.
- **Fallback used:** Anonymous fetch of `https://play.google.com/store/apps/details?id=com.microsoft.scmx&hl=en&gl=US` (HTTP 200, 1.26 MB). Version `1.0.9002.0102` is the only version string carried in the page's metadata block (adjacent to the `Jun 10, 2026` / unix `1781068472` "Updated on" timestamp). Other version strings on the page (`1.0.8921.0101`, `1.0.8913.0101`, `1.0.8905.0106`, etc.) appear only inside user-review records and represent the version each reviewer was running — **not** the current published build.
- **Confidence:** High on version identity + release date. Low on rollout % and ring composition (those need Play Console auth).

---

## 🚨 Cross-reference flags for today's report

1. **Scully's "+131% fail-rate" anchor `1.0.9003.0401` is NOT the live production build.**
   - Live production: `1.0.9002.0102` (build 9002, `.0102` mainstream suffix).
   - Scully's bad cohort: `1.0.9003.0401` (build 9003, `.0401` suffix) — only 1,003 devices, concentrated in 2 tenants, consistent with an **internal/closed-test ring**, not general-availability.
   - **Implication:** General Play Store users are *not yet* exposed to the `.04xx` regression. The `.04xx` ring is a forward-looking risk if it graduates to production. Doggett's open question — "what is `.04xx`?" — gets a partial answer from Langly: it is not on the public production track.

2. **The mainstream production build (`1.0.9002.0102`) is also degrading.**
   - Scully: `9002.0102` fail-rate rose ~21% week-over-week (still in the 0.33–0.35% band, well below `.04xx`'s 0.626%).
   - Because `9002.0102` is what real Play Store users get, this milder degradation is the one with end-user blast radius today.

3. **No newer build than `1.0.9002.0102` has shipped to production since Scully's 2026-06-09 pull** → crash data is current, not stale.

---

## One-line header for Reyes (2026-06-10 daily report)

```
📱 Defender for Android — Live on Play Store: v1.0.9002.0102 (released 2026-06-10, rollout % not visible — Play Console auth needed; active ramp inferred from +51% device growth in Scully telemetry)
```

---

## Rolling history

| Version | Released | Rollout % | Pulled-via | Notes |
|---|---|---|---|---|
| `1.0.9002.0102` | 2026-06-10 | TBD (Play Console) | play-store-scrape | First Langly pull. Mainstream `.0102` suffix. Coincides with active ramp per Scully (+51% device growth WoW). Mild fail-rate uptick (~+21%, still ~0.33%). |

*(Older versions visible in Play Store review records — `1.0.8921.0101`, `1.0.8913.0101`, `1.0.8905.0106` — are historical and not added here; they will be backfilled if/when Play Console release-history endpoint becomes reachable.)*
