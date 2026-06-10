#!/usr/bin/env bash
# run-daily.sh — manual one-command driver for the daily livesite report.
#
# v1 = manual trigger. Saloni runs this from her laptop; on success the
# generated markdown is POSTed to the Teams Power Automate webhook
# (URL lives in macOS Keychain — never on disk, never logged).
#
# Usage:
#   ./tools/local-runner/run-daily.sh                # today (UTC)
#   ./tools/local-runner/run-daily.sh --date 2026-06-10
#
# Re-running for the same date is safe: the generator overwrites its own
# outputs and we just re-POST the same markdown.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# --- Args -------------------------------------------------------------------
REPORT_DATE="$(date -u +%Y-%m-%d)"
while [ $# -gt 0 ]; do
  case "$1" in
    --date)
      REPORT_DATE="${2:?--date requires YYYY-MM-DD}"
      shift 2
      ;;
    --date=*)
      REPORT_DATE="${1#--date=}"
      shift
      ;;
    -h|--help)
      sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

# Sanity-check date shape (YYYY-MM-DD).
case "$REPORT_DATE" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) echo "ERROR: --date must be YYYY-MM-DD (got: $REPORT_DATE)" >&2; exit 2 ;;
esac

# --- Logging ---------------------------------------------------------------
LOG_DIR="${HOME}/Library/Logs/ahcs-livesite"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/run-$(date -u +%Y%m%dT%H%M%SZ).log"

# Mirror all stdout+stderr to the log file from this point on.
exec > >(tee -a "$LOG_FILE") 2>&1

log() { printf "[%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

log "── AHCS daily livesite runner ──"
log "repo:        ${REPO_ROOT}"
log "report date: ${REPORT_DATE}"
log "log file:    ${LOG_FILE}"

# --- Resolve credential env vars in THIS shell -----------------------------
# Must happen before preflight so the child preflight process sees the same
# resolved values, and (critically) before we exec the Python generator —
# subprocess exports inside preflight.sh do not propagate back up here.
# shellcheck source=_resolve_credentials.sh
. "${SCRIPT_DIR}/_resolve_credentials.sh"

# --- Preflight -------------------------------------------------------------
log "step 1/4: preflight"
if ! bash "${SCRIPT_DIR}/preflight.sh"; then
  log "preflight FAILED — aborting."
  exit 1
fi

# --- Webhook ---------------------------------------------------------------
log "step 2/4: loading webhook URL from Keychain"
# shellcheck source=_load_webhook.sh
. "${SCRIPT_DIR}/_load_webhook.sh"
# Re-export so the variable is in scope after sourcing.
export AHCS_TEAMS_WEBHOOK_URL

# --- Generator -------------------------------------------------------------
log "step 3/4: running report generator for ${REPORT_DATE}"
cd "$REPO_ROOT"

PY_BIN="${PYTHON:-python3}"
# --no-fail-on-validation: local-runner is the degraded path by design
# (no Kusto SP, sometimes no Play Console SA, file-based ICM). Validation
# still runs and writes validation.json, but exit code stays 0 so the
# Teams post proceeds. CI remains strict (no flag in the workflow).
# See: .squad/decisions/inbox/mulder-invariant-2-local-policy.md
"$PY_BIN" -m tools.report_generator.cli --date "$REPORT_DATE" --no-fail-on-validation

REPORT_PATH="${REPO_ROOT}/daily-livesite-report-android-${REPORT_DATE}.md"
if [ ! -s "$REPORT_PATH" ]; then
  log "ERROR: expected report not produced at: ${REPORT_PATH}"
  exit 1
fi
log "report written: ${REPORT_PATH} ($(wc -c < "$REPORT_PATH" | tr -d ' ') bytes)"

# --- Validation banner (degraded but shipping) -----------------------------
# Read validation.json written by the generator. If passed=false, print a
# loud banner so Saloni sees the report shipped *degraded* even though we're
# about to post it. Banner appears BEFORE the Teams post, not after, so a
# subsequent curl failure can't bury it.
VALIDATION_JSON="${REPO_ROOT}/tools/report_generator/runs/${REPORT_DATE}/validation.json"
if [ -f "$VALIDATION_JSON" ]; then
  if command -v jq >/dev/null 2>&1; then
    V_PASSED="$(jq -r '.passed' "$VALIDATION_JSON" 2>/dev/null || echo "unknown")"
    if [ "$V_PASSED" = "false" ]; then
      V_COUNT="$(jq -r '.failure_count' "$VALIDATION_JSON" 2>/dev/null || echo "?")"
      echo ""
      echo "⚠️  Report posted to Teams BUT validation reported ${V_COUNT} failure(s)."
      echo "    See: tools/report_generator/runs/${REPORT_DATE}/validation.json"
      jq -r '.failures[] | "      - " + .' "$VALIDATION_JSON" 2>/dev/null || true
      echo ""
    fi
  else
    log "WARN: jq missing — cannot parse ${VALIDATION_JSON} for banner."
  fi
else
  log "WARN: no validation.json at ${VALIDATION_JSON} — generator did not write one?"
fi

# --- Post to Teams ---------------------------------------------------------
log "step 4/4: posting to Teams webhook"
if ! command -v jq >/dev/null 2>&1; then
  log "ERROR: jq is required for safe JSON escaping. Install: brew install jq"
  exit 1
fi

# Build {"text": "<markdown>"} via jq -Rs so embedded quotes/backticks/newlines
# are escaped safely. The webhook URL is passed to curl via --url-file-like
# stdin? No — curl needs it as an arg; we pass it as the last positional arg
# without ever echoing it.
HTTP_STATUS_FILE="${LOG_DIR}/.curl-status.$$"
RESP_BODY_FILE="${LOG_DIR}/.curl-body.$$"
trap 'rm -f "$HTTP_STATUS_FILE" "$RESP_BODY_FILE"' EXIT

set +e
jq -Rs '{text: .}' < "$REPORT_PATH" \
  | curl -sS -X POST \
      -H 'Content-Type: application/json' \
      --data-binary @- \
      -o "$RESP_BODY_FILE" \
      -w '%{http_code}' \
      "$AHCS_TEAMS_WEBHOOK_URL" > "$HTTP_STATUS_FILE"
CURL_RC=$?
set -e

HTTP_STATUS="$(cat "$HTTP_STATUS_FILE" 2>/dev/null || echo "000")"

if [ "$CURL_RC" -ne 0 ]; then
  log "ERROR: curl failed (rc=${CURL_RC}). Response body:"
  cat "$RESP_BODY_FILE" >&2 || true
  exit 1
fi

if [ "$HTTP_STATUS" != "202" ]; then
  log "ERROR: Teams webhook returned HTTP ${HTTP_STATUS} (expected 202). Body:"
  cat "$RESP_BODY_FILE" >&2 || true
  exit 1
fi

log "✅ Teams post OK (HTTP ${HTTP_STATUS})"
log "✅ done. report=${REPORT_PATH} log=${LOG_FILE}"
exit 0
