#!/usr/bin/env bash
# Refresh .squad/agents/skinner/icm-latest.json from the live ICM API.
# Run on Saloni's laptop (interactive Entra auth required by `agency mcp icm`).
# Wrap in cron/launchd for 2-3x/week cadence — see Mulder plan §3 Option B.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT=".squad/agents/skinner/icm-latest.json"
python -m tools.icm.icm_collector --team-id 106961 > "$OUT"
echo "✅ ICM refreshed → $OUT at $(date -u +%FT%TZ)"
