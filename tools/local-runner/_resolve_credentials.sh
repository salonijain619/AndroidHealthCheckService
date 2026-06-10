#!/usr/bin/env bash
# _resolve_credentials.sh — source this from run-daily.sh (and preflight.sh).
#
# Resolves credential env vars in the CURRENT shell so they propagate to any
# child process (preflight checks, the Python report generator, etc.).
#
# Why a sourceable file: preflight.sh runs as a subprocess of run-daily.sh,
# so an `export` inside preflight does not reach the parent. Anything that
# needs to be visible to `python -m tools.report_generator.cli` must be
# exported by the parent shell. Same pattern as _load_webhook.sh.
#
# Currently resolves:
#   PLAY_CONSOLE_SA_KEY — if unset/empty, fall back to the canonical local
#                         path if it exists and is readable. Otherwise leave
#                         unset and let preflight.sh report it as a fix-it.
#
# Idempotent: safe to source multiple times. Never overwrites a value the
# user explicitly set. Silent on the happy path — output is preflight's job.

_ahcs_sa_default_path="/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json"

if [ -z "${PLAY_CONSOLE_SA_KEY:-}" ] && [ -r "$_ahcs_sa_default_path" ]; then
  export PLAY_CONSOLE_SA_KEY="$_ahcs_sa_default_path"
fi

unset _ahcs_sa_default_path
