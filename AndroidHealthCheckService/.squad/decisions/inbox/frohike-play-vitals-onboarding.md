# Frohike — Play Vitals onboarding / SA provisioning

**By:** Frohike (Play Vitals Analyst)
**Date:** 2026-06-10
**Status:** PROPOSED — needs Saloni action to unblock CI

## What

Wire `tools/report_generator/sections/frohike_play_vitals.py` into CI by
provisioning a Google Cloud service account with read access to the
Play Developer Reporting API for `com.microsoft.scmx`.

## Why

The producer is implemented, fail-soft, and unit-tested, but in CI today it
returns `Status.PARTIAL` with the stub markdown because neither
`PLAY_CONSOLE_SA_KEY` nor `GOOGLE_APPLICATION_CREDENTIALS` is set. Until
the SA is granted access, every daily report runs degraded for Frohike's
section.

Locally (Saloni's workstation) the existing service-account JSON at
`/Users/salonijain/workspace/android/WD.Client.Android/google-play-sa.json`
works for manual pulls (this is the SA Frohike's prior 2026-06-10 drop used).
That same SA can be reused for CI provided it is granted the right Play
Console role, then exported as a base64-encoded secret.

## What Saloni needs to provision

1. **Confirm or create the service account** with at least the Play Console
   "View app information and download bulk reports" role for `com.microsoft.scmx`.
   Existing SA candidate: the one whose key lives at the local path above.
   Tenant: Microsoft Defender for Android publisher account.
2. **Export the SA key JSON** (the full Google-issued `.json` file).
3. **Add a GitHub Actions secret** named `PLAY_CONSOLE_SA_KEY` containing
   the *raw JSON contents* of the key (not base64 — Frohike's producer
   detects JSON-vs-path automatically; the workflow can paste the key body
   directly into the secret).
4. **Workflow already declares it:** Mulder's architecture §1 sample
   `Generate daily livesite report` step lists
   `PLAY_CONSOLE_SA_KEY: ${{ secrets.PLAY_CONSOLE_SA_KEY }}` in `env:`.
   Once Doggett's workflow lands, nothing further is needed in the YAML.

## Local-developer note

For pre-commit smoke tests, devs can either:
- Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json` in their shell, or
- Set `PLAY_CONSOLE_SA_KEY="$(cat /path/to/sa.json)"`.

Both are picked up automatically by `frohike_play_vitals._resolve_credentials()`.

## Skip path (already supported)

While the SA is being provisioned, daily reports continue to publish — the
Frohike section degrades to the documented stub:

> _⚠️ Play Vitals data unavailable — `PLAY_CONSOLE_SA_KEY` secret not
> configured. See `.squad/decisions/inbox/frohike-play-vitals-onboarding.md`._

…and `Status.PARTIAL` is recorded in the orchestrator manifest (per Mulder §4).

## Asks

- **Saloni:** create the GitHub secret + confirm SA has Play Console read scope.
- **Doggett (workflow owner):** confirm the `PLAY_CONSOLE_SA_KEY` env passes
  through to `python -m tools.report_generator` (already specced — just verify
  when the workflow lands).
- **Mulder:** ack the PARTIAL-not-SKIP framing for "auth missing" (matches
  Mulder §4 table; the spec brief originally said SKIP — resolved in Frohike's
  test file with a comment).

## Acceptance criteria

After provisioning, a fresh CI run should show:
```
[frohike_play_vitals] status=GO errors=0 naas_crashes=<n> naas_anrs=<n> drop=.squad/agents/frohike/research/naas-crashes-<date>.md
```
and the report's "Client-side (Frohike, Google Play Vitals, NAAS-as-a-unit)"
section should populate with live data, not the stub.
