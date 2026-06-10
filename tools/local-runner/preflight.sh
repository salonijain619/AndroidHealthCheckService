#!/usr/bin/env bash
# preflight.sh — fail-fast environment checks for the local livesite runner.
#
# Exit codes:
#   0  all checks pass (✅)
#   1  hard failure — caller must abort
#
# macOS bash 3.2 compatible: no associative arrays, no `mapfile`.

set -uo pipefail

# Resolve repo root from this script's location (tools/local-runner/preflight.sh → repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SA_DEFAULT_PATH="/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json"
ICM_CACHE="${REPO_ROOT}/.squad/agents/skinner/icm-latest.json"
KEYCHAIN_SERVICE="ahcs-livesite-webhook"
CORP_TENANT_ID="72f988bf-86f1-41af-91ab-2d7cd011db47"

# Resolve credential env vars in this shell. Idempotent and silent on the
# happy path. When preflight is invoked from run-daily.sh the parent has
# already sourced this; sourcing it again here keeps preflight usable as a
# standalone debugging tool (`bash tools/local-runner/preflight.sh`).
# shellcheck source=_resolve_credentials.sh
. "${SCRIPT_DIR}/_resolve_credentials.sh"

FAIL=0
GREEN="$(printf '\033[32m')"
YELLOW="$(printf '\033[33m')"
RED="$(printf '\033[31m')"
RESET="$(printf '\033[0m')"

pass() { printf "%s✅ %s%s\n" "$GREEN" "$1" "$RESET"; }
warn() { printf "%s⚠️  %s%s\n" "$YELLOW" "$1" "$RESET"; }
fail() { printf "%s❌ %s%s\n" "$RED" "$1" "$RESET"; FAIL=1; }

echo "── preflight: AHCS livesite runner ──"
echo "repo: ${REPO_ROOT}"
echo

# 1) az login active.
AZ_USER=""
if command -v az >/dev/null 2>&1; then
  AZ_USER="$(az account show --query user.name -o tsv 2>/dev/null || true)"
fi
if [ -n "$AZ_USER" ]; then
  pass "az login active as: ${AZ_USER}"
else
  fail "az login not active. Fix:"
  printf "    az login --tenant %s\n" "$CORP_TENANT_ID"
fi

# 2) Play Console SA key. (Resolution lives in _resolve_credentials.sh which
#    has already been sourced above; here we only verify.)
if [ -n "${PLAY_CONSOLE_SA_KEY:-}" ] && [ -r "${PLAY_CONSOLE_SA_KEY}" ]; then
  if [ "${PLAY_CONSOLE_SA_KEY}" = "$SA_DEFAULT_PATH" ]; then
    pass "PLAY_CONSOLE_SA_KEY resolved to default: ${PLAY_CONSOLE_SA_KEY}"
  else
    pass "PLAY_CONSOLE_SA_KEY set and readable: ${PLAY_CONSOLE_SA_KEY}"
  fi
elif [ -n "${PLAY_CONSOLE_SA_KEY:-}" ]; then
  fail "PLAY_CONSOLE_SA_KEY set but not readable: ${PLAY_CONSOLE_SA_KEY}"
  printf "    chmod 600 \"\$PLAY_CONSOLE_SA_KEY\"\n"
else
  fail "Play Console SA JSON not found. Fix one of:"
  printf "    export PLAY_CONSOLE_SA_KEY=/path/to/google-play-sa.json\n"
  printf "    # or place file at: %s\n" "$SA_DEFAULT_PATH"
  printf "    # then: chmod 600 \"\$PLAY_CONSOLE_SA_KEY\"\n"
fi

# 3) ICM cache freshness (warn >24h, fail >48h).
if [ -r "$ICM_CACHE" ]; then
  # macOS stat: -f %m → mtime epoch seconds.
  MTIME="$(stat -f %m "$ICM_CACHE" 2>/dev/null || echo 0)"
  NOW="$(date +%s)"
  AGE_S=$(( NOW - MTIME ))
  AGE_H=$(( AGE_S / 3600 ))
  if [ "$AGE_S" -le 0 ]; then
    warn "ICM cache mtime in the future; treating as fresh"
    pass "ICM cache present: ${ICM_CACHE}"
  elif [ "$AGE_H" -lt 24 ]; then
    pass "ICM cache fresh (${AGE_H}h old): ${ICM_CACHE}"
  elif [ "$AGE_H" -lt 48 ]; then
    warn "ICM cache aging (${AGE_H}h old). Refresh soon:"
    printf "    bash %s/tools/icm/refresh-local.sh\n" "$REPO_ROOT"
  else
    fail "ICM cache stale (${AGE_H}h old > 48h). Refresh now:"
    printf "    bash %s/tools/icm/refresh-local.sh\n" "$REPO_ROOT"
  fi
else
  fail "ICM cache missing: ${ICM_CACHE}"
  printf "    bash %s/tools/icm/refresh-local.sh\n" "$REPO_ROOT"
fi

# 4) Webhook URL retrievable from Keychain.
if security find-generic-password -s "$KEYCHAIN_SERVICE" -w >/dev/null 2>&1; then
  pass "Teams webhook URL present in Keychain (service: ${KEYCHAIN_SERVICE})"
else
  fail "Teams webhook URL not found in Keychain. One-time setup:"
  printf "    security add-generic-password -a \"\$USER\" -s %s -w '<paste webhook URL>'\n" "$KEYCHAIN_SERVICE"
fi

# 5) Python deps: googleapiclient importable (venv-activated or system).
PY_BIN="${PYTHON:-python3}"
if "$PY_BIN" -c 'import googleapiclient' >/dev/null 2>&1; then
  pass "python deps: googleapiclient importable (${PY_BIN})"
else
  fail "googleapiclient not importable by '${PY_BIN}'. Fix:"
  printf "    source .venv-local/bin/activate   # or your venv\n"
  printf "    pip install -r tools/report_generator/requirements.txt\n"
fi

echo
if [ "$FAIL" -ne 0 ]; then
  printf "%spreflight: FAILED — fix items above and re-run.%s\n" "$RED" "$RESET"
  exit 1
fi
printf "%spreflight: all checks passed ✅%s\n" "$GREEN" "$RESET"
exit 0
