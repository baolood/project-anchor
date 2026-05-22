# Testnet secrets custody V1

**Status:** custody plan only - no credential values, no implementation, no testnet execution, no live trading approval.

**Owner:** **baolood** (Security / Operations lead, interim).

**Date:** 2026-05-22

**Pairs with:**

- `docs/TESTNET_COMMAND_CONTRACT_V1.md`
- `docs/TESTNET_READINESS_GAP_REVIEW_V1.md`
- `docs/SECRETS_AND_ROTATION.md`
- `docs/PERMISSION_AUDIT.md`
- `docs/BACKUP_AND_RECOVERY.md`

## 1. Decision

Testnet credentials may be planned, but must not be added to git or wired into runtime until custody, least privilege, rotation, and no-plaintext evidence are in place.

This document authorizes only the handling model for future testnet credentials. It does not authorize live credentials or real-money trading.

## 2. Secret inventory row

Add this row to the release evidence bundle before any testnet key is used. Do not paste actual values.

| Secret ID | Description | Storage target | Owner role | Rotation interval |
|-----------|-------------|----------------|------------|-------------------|
| `SEC-TESTNET-EXCHANGE` | Exchange testnet API key + secret for testnet-only order execution | `<TBD secret manager or local OS keychain>` | Security owner | 30 days during testnet, immediately on suspected exposure |

Rules:

- The value must never appear in git, screenshots, terminal transcripts, issue text, or docs.
- The storage target must be outside the repository.
- The storage target must support deletion / rotation.
- If a temporary local store is used before a proper secret manager exists, record the local-only path in private operator notes, not in git.

## 3. Minimum permissions

The testnet key must be created with the smallest possible scope:

| Permission | Required | Rule |
|------------|----------|------|
| Testnet environment only | yes | Key must not work against live endpoints |
| Trade/order permission | yes, testnet only | Required only for testnet order smoke |
| Read account/order status | yes, testnet only | Needed to verify testnet response |
| Withdrawal | no | Must be disabled |
| Transfer / funding | no | Must be disabled |
| Margin / leverage | no by default | Requires separate review if ever needed |
| IP allowlist | recommended | Prefer restricting to the stage host or known operator IP |

If the exchange UI cannot disable withdrawal or live access for a key, do not use that key for Project Anchor.

## 4. Environment variables

Future runtime wiring may use these names, but this document does not create or require them:

```text
TESTNET_EXCHANGE_API_KEY
TESTNET_EXCHANGE_API_SECRET
TESTNET_EXCHANGE_BASE_URL
TESTNET_EXCHANGE_KEY_ID
```

Rules:

- `TESTNET_EXCHANGE_BASE_URL` must point to a testnet hostname.
- No `LIVE_*`, `PROD_*`, or generic `EXCHANGE_API_KEY` variable may be used for testnet smoke.
- `.env`, `.env.local`, shell history, and logs must be treated as sensitive if they ever contain a value.
- Environment variable names may be documented; values must not be documented.

## 5. No-plaintext scan

Before any testnet smoke that uses credentials, run a no-plaintext scan from the parent repo.

Minimum parent scan:

```bash
git grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|secret[_-]?key\s*=|api[_-]?key\s*=|api[_-]?secret\s*=' -- ':!docs/' ':!RELEASE_NOTES.md' || true
```

Also run equivalent scans in:

```text
anchor-backend
anchor-console
```

Acceptance:

- Any hit outside obvious placeholder examples is a P1 until rotated and purged.
- A clean scan does not prove secrets are safe; it only proves no obvious plaintext was found in git-tracked content.
- Do not commit scan output if it contains sensitive values.

## 6. Rotation procedure

Rotate `SEC-TESTNET-EXCHANGE`:

1. Create a new testnet-only key with the permissions in §3.
2. Store it in the approved storage target.
3. Update runtime configuration outside git.
4. Restart only the component that needs the key.
5. Run no-plaintext scan.
6. Run a testnet health/auth smoke when one exists.
7. Revoke the old testnet key.
8. Record timestamp, operator, key id suffix only, and smoke result.

Do not rotate by editing repository files with real values.

## 7. Exposure response

If a testnet key is suspected exposed:

1. Revoke the key immediately.
2. Remove any leaked local file or transcript.
3. Search git history and working trees for the exposed value.
4. Create a new key only after the storage path is fixed.
5. Record the incident as testnet credential exposure.

Even though testnet has no funds, treat exposure as a rehearsal for production incident handling.

## 8. Runtime guardrails before use

Before an executor is allowed to read testnet credentials:

- `execution_mode` must be exactly `testnet`.
- Base URL must be a recognized testnet URL.
- Key id must correspond to `SEC-TESTNET-EXCHANGE`.
- Kill switch must be checked before any external call.
- Command must already pass risk policy.
- Worker must emit command events visible at `/commands/[id]`.

If any guardrail fails, command must end as `FAILED` with an explicit reason and no external order request.

## 9. Evidence bundle for first use

The first accepted testnet credential use must record:

```text
[Testnet Secrets Custody Evidence]
date:
operator:
secret id: SEC-TESTNET-EXCHANGE
storage target: <name only, no values>
key id suffix: <last 4 chars only, if safe>
withdrawal disabled: PASS/FAIL
live endpoint disabled or impossible: PASS/FAIL
testnet base URL: <hostname only>
parent no-plaintext scan: PASS/FAIL
anchor-backend no-plaintext scan: PASS/FAIL
anchor-console no-plaintext scan: PASS/FAIL
rotation path documented: PASS/FAIL
kill switch precondition documented: PASS/FAIL
live trading: NO-GO
```

## 10. What not to do

- Do not commit API keys, API secrets, `.env` files, screenshots, or terminal output with values.
- Do not use a live exchange key as a "temporary" testnet key.
- Do not create a key with withdrawal permission.
- Do not use generic environment variable names that could point at live endpoints.
- Do not bypass risk or kill switch to prove connectivity.
- Do not close `docs/GO_LIVE_CHECKLIST.md` §5 G4 from this document alone.

## 11. Acceptance for this custody plan

```text
testnet secret id defined: PASS
storage target remains value-free: PASS
least privilege defined: PASS
withdrawal disabled required: PASS
no-plaintext scan defined: PASS
rotation procedure defined: PASS
exposure response defined: PASS
runtime guardrails defined: PASS
no credentials added: PASS
no backend changed: PASS
no worker changed: PASS
no risk changed: PASS
live trading: NO-GO
```

## 12. Next single task

Recommended next task:

```text
Testnet Executor Stub V1
```

Scope:

- code may be needed, but no external API call
- prove worker boundary and eventing
- reject `execution_mode=live`
- no API key value
- no real order
- no live endpoint
