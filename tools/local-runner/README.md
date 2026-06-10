# Local runner — daily livesite report (v1)

## What this does

Builds the daily AHCS livesite report end-to-end on Saloni's Mac and POSTs it
to the Teams "Livesite — Mobile Client" channel via a Power Automate webhook.
v1 is **manual trigger only**: one command, one log file, one HTTP 202. The
launchd plist for automated daily runs ships alongside but is **not installed**
until Phase 1.5 below.

## One-time setup

1. **Store the Teams webhook URL in Keychain** (the URL itself never lands on
   disk or in any log — paste it directly into this command):

   ```bash
   security add-generic-password -a "$USER" -s ahcs-livesite-webhook -w '<paste webhook URL>'
   ```

   Update later with `-U`:
   ```bash
   security add-generic-password -U -a "$USER" -s ahcs-livesite-webhook -w '<new URL>'
   ```

2. **Confirm the Play Console SA JSON** is at the default location and
   readable only by you:

   ```bash
   ls -l /Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json
   chmod 600  /Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json
   ```

   (Override the path by exporting `PLAY_CONSOLE_SA_KEY=/some/other/path.json`.)

3. **Azure CLI login to the corp tenant:**

   ```bash
   az login --tenant 72f988bf-86f1-41af-91ab-2d7cd011db47
   az account show --query user.name -o tsv   # should print your alias
   ```

4. **ICM cache** — make sure the local refresh works at least once:

   ```bash
   bash tools/icm/refresh-local.sh
   ls -l .squad/agents/skinner/icm-latest.json
   ```

5. **Python deps** — activate the project venv (whichever you use) and verify:

   ```bash
   python -c 'import googleapiclient' && echo OK
   ```

   If missing: `pip install -r tools/report_generator/requirements.txt`.

6. **jq** is required for safe JSON escaping of the report payload:
   `brew install jq`.

## Daily use

```bash
./tools/local-runner/run-daily.sh                 # today (UTC date)
./tools/local-runner/run-daily.sh --date 2026-06-10  # explicit date
```

What happens:

1. `preflight.sh` runs four checks (az login, SA JSON, ICM cache age, Keychain
   webhook entry, python deps). Any hard failure → abort, nothing posted.
2. Webhook URL is loaded into `AHCS_TEAMS_WEBHOOK_URL` from Keychain.
3. `python -m tools.report_generator.cli --date <date>` writes the report to
   `daily-livesite-report-android-<date>.md` at the repo root (overwrites if
   re-run — idempotent).
4. The markdown is POSTed to the Teams webhook. Expected response is HTTP
   202; anything else aborts non-zero.
5. Everything tees to `~/Library/Logs/ahcs-livesite/run-<UTC-timestamp>.log`.

**Re-running** the same `--date` is safe for the on-disk artifacts (generator
overwrites its own outputs) but **will repost** to the Teams channel —
intentional for v1.

## Phase 1.5: enable launchd (optional automation)

When you're tired of typing the command:

```bash
# Copy the plist to the user LaunchAgents dir.
cp tools/local-runner/com.microsoft.ahcs.livesite.plist ~/Library/LaunchAgents/

# Load it (the -w flag makes it persist across reboots).
launchctl load -w ~/Library/LaunchAgents/com.microsoft.ahcs.livesite.plist

# Verify it's registered.
launchctl list | grep ahcs
```

Schedule is **daily at 09:30 IST**. Note that launchd does **not** wake the
laptop from sleep — if the lid is closed at 09:30 IST the run is silently
skipped and you re-run manually. Inspect logs at:

```
~/Library/Logs/ahcs-livesite/launchd.out.log
~/Library/Logs/ahcs-livesite/launchd.err.log
~/Library/Logs/ahcs-livesite/run-*.log
```

## Troubleshooting

| Symptom                                              | Fix                                                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `preflight: az login not active`                     | `az login --tenant 72f988bf-86f1-41af-91ab-2d7cd011db47`                                         |
| `Play Console SA JSON not found`                     | Place the file at the default path or export `PLAY_CONSOLE_SA_KEY=/path/to.json`                 |
| `ICM cache aging (Nh old)` (warn)                    | `bash tools/icm/refresh-local.sh` — non-blocking but freshen soon                                |
| `ICM cache stale (>48h)` (hard fail)                 | `bash tools/icm/refresh-local.sh` — required to proceed                                          |
| `Teams webhook URL not found in Keychain`            | Run the `security add-generic-password ...` command in §One-time setup                           |
| `googleapiclient not importable`                     | Activate the project venv, then `pip install -r tools/report_generator/requirements.txt`         |
| `jq is required`                                     | `brew install jq`                                                                                |
| `Teams webhook returned HTTP 4xx/5xx`                | Check the response body in the log; webhook URL may have been rotated — re-add via `-U`          |
| Generator exits non-zero                             | Inspect the log file; rerun manually with `--verbose` (pass directly to the Python CLI) to debug |

## Uninstall

```bash
# Stop and unregister the launchd job (if installed).
launchctl unload -w ~/Library/LaunchAgents/com.microsoft.ahcs.livesite.plist
rm ~/Library/LaunchAgents/com.microsoft.ahcs.livesite.plist

# Remove the webhook from Keychain.
security delete-generic-password -s ahcs-livesite-webhook
```

The runner itself is just files in `tools/local-runner/` — delete the
directory to fully uninstall.
