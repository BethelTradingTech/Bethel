# Bethel Security & Compliance Operations

This runbook covers operational evidence only. It does not grant trading authority and must not modify MT5 EA execution.

## Automated daily controls

1. `bethel-sanctions-refresh` refreshes the active sanctions dataset at 02:00 UTC.
2. `bethel-security-compliance-check` runs at 02:30 UTC and fails if API health, production readiness, Native KYC availability, or the active sanctions dataset is not healthy.
3. Render job history is retained as operational evidence. Failed jobs require investigation before production readiness is represented as healthy.

## Monthly backup verification

- Confirm the production PostgreSQL recovery/backup feature is active in the hosting control plane.
- Record the latest recoverable timestamp.
- At least quarterly, restore into a non-production database and verify application-readable data.
- Never restore a production backup over the live database as a test.
- Record date, operator, result, and corrective action if a restore fails.

## Quarterly access review

Review GitHub collaborators, Render members, production admin/super-admin accounts, API/service credentials, and obsolete integrations. Remove access that is no longer required. Rotate credentials if exposure is suspected; never place secret values in evidence logs.

## Security evidence record

Retain: daily compliance job status, sanctions refresh status, CI security status, backup/restore verification, access review date, connector replay-protection test result, and incident/corrective-action references.

## Incident rule

A failed readiness or compliance check is a fail-closed operational signal. Investigate the failed dependency; do not bypass readiness controls merely to obtain a green status.

## Reporting language

Reports must distinguish implemented controls from regulatory approval. Production readiness is technical evidence and must not be described as a licence, certification, regulator endorsement, or guarantee of security.
