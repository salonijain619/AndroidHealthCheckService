# Kusto Service Principal Onboarding — Scully

**Owner:** Saloni · **Status:** PENDING

Scully's server-telemetry producer needs a non-interactive Entra service principal to query `idsharedwus.westus.kusto.windows.net / NaasProd` from CI.

## What to provision

1. **Tenant ID** — the Microsoft corp tenant (confirm GUID).
2. **Service Principal creation** (`az ad sp create-for-rbac`):

   ```bash
   az ad sp create-for-rbac \
       --name gsa-android-scully-naas-reader \
       --years 1 \
       --skip-assignment
   ```

   Capture `appId`, `password`, `tenant`.

3. **Role assignment on NaasProd DB** (Viewer):

   ```bash
   az kusto database-principal-assignment create \
       --cluster-name idsharedwus --resource-group <rg> \
       --database-name NaasProd \
       --principal-assignment-name scully-reader \
       --principal-id <appId> --principal-type App \
       --role Viewer
   ```

   Repeat for `NaasAgentServicesApsProd` and `NaasCloudPkiProd`.

4. **GitHub Actions secrets** (per Mulder §4):
   - `KUSTO_AAD_TENANT_ID`
   - `KUSTO_AAD_SP_CLIENT_ID`
   - `KUSTO_AAD_SP_CLIENT_SECRET`

Until wired, the producer returns `Status.SKIP` with a stub — the daily report still ships, but the server-side section is empty.
