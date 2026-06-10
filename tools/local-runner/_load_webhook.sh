#!/usr/bin/env bash
# _load_webhook.sh — source this from run-daily.sh.
# Exports AHCS_TEAMS_WEBHOOK_URL from the macOS Keychain.
# Never echoes, logs, or prints the URL.

_ahcs_kc_service="ahcs-livesite-webhook"
AHCS_TEAMS_WEBHOOK_URL="$(security find-generic-password -s "$_ahcs_kc_service" -w 2>/dev/null || true)"
if [ -z "${AHCS_TEAMS_WEBHOOK_URL:-}" ]; then
  echo "ERROR: webhook URL not found in Keychain (service=${_ahcs_kc_service})." >&2
  echo "  Add it once: security add-generic-password -a \"\$USER\" -s ${_ahcs_kc_service} -w '<paste webhook URL>'" >&2
  unset _ahcs_kc_service
  return 1 2>/dev/null || exit 1
fi
export AHCS_TEAMS_WEBHOOK_URL
unset _ahcs_kc_service
