# Team

## Project Context

**Project:** Android GSA Client Service Health Check
**User:** salonijain619 (Saloni)
**Created:** 2026-06-05
**Description:** Service health check and reporting for the GSA (Global Secure Access) Android client. Models after the Windows (`win_client_investigation_squad`) and Mac (`HarryPotter`) investigation squads. Pulls telemetry from server-side Kusto (NaasProd @ idsharedwus) and client-side AppInsights / Aria Kusto, tracks ICM incidents (team 106961), and produces service health reports for the IDNA GSA Livesite Teams channel.

**Key references:**
- Android client repo: https://microsoft.visualstudio.com/Windows%20Defender/_git/WD.Client.Android (GSA Android is integrated into Microsoft Defender for Android — repo also has existing agents/skills/plugins for telemetry, crashes, Kusto that we should examine and reuse)
- Android onboarding docs: https://learn.microsoft.com/en-us/entra/global-secure-access/how-to-install-android-client
- **Existing Android GSA Kusto dashboard:** https://dataexplorer.azure.com/dashboards/8a1fa78a-032c-4b91-ba3d-9c83c8e0dd98?p-_startTime=7days&p-_endTime=now&p-_osType=v-ANDROID&p-_trafficProfile=all&p-_tenantId=all (canonical starting point — mirror its panels/metrics into the daily livesite report)
- Windows squad: https://github.com/mogendel_microsoft/win_client_investigation_squad
- Mac squad: https://github.com/jainash_microsoft/HarryPotter
- ICM team: https://portal.microsofticm.com/imp/v3/administration/teamdashboard/details?id=106961
- Service health report template: IDNA GSA Livesite - Client Teams channel
- Server telemetry: idsharedwus / NaasProd (Kusto)
- Client telemetry: AppInsights (sub fb633419-6bb2-4a7e-8993-fd9456d19c4c) + kusto.aria.microsoft.com/f0eaa94222894be599b7cd0bc1e2ed6f

## Members

| Name | Role | Notes | Badge |
|------|------|-------|-------|
| Mulder | Lead | Scope, decisions, drives investigations, code review | 🏗️ Lead |
| Scully | Telemetry Analyst | Kusto/AppInsights queries, data analysis, anomaly detection | 📊 Data |
| Doggett | Android Engineer | WD.Client.Android codebase, repro, client-side diagnosis | 🔧 Backend |
| Skinner | ICM Liaison | Incident triage, ICM workflow, escalations, on-call | 🔒 Security |
| Reyes | Report Writer | Service health report assembly, Teams posts, docs | 📝 DevRel |
| Frohike | Play Vitals Analyst | Google Play Console crashes/ANRs, NAAS-filtered, per-Defender-version | 📊 Data |
| Langly | Release Tracker | Latest Play Store Defender version, every report | 🔧 Backend |
| Scribe | Session Logger | Memory, decisions, session logs | 📋 Scribe |
| Ralph | Work Monitor | Work queue, backlog, keep-alive | 🔄 Monitor |
