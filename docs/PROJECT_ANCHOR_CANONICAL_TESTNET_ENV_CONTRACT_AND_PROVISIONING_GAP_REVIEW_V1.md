# Project Anchor Canonical Testnet Env Contract And Provisioning Gap Review V1

## Locked Baseline

- Current locked state: `PROJECT_ANCHOR_EXACTLY_ONE_BOUNDED_RUNTIME_ENABLEMENT_PREFLIGHT_FAILED_RUNTIME_DISABLED`
- Baseline HEAD reviewed: `6792b43 Merge pull request #294 from baolood/codex/project-anchor-runtime-enablement-execution-preflight-authorization-request-operator-fill`
- Observed preflight result: `PREFLIGHT_RESULT=FAIL`
- Observed failure reason: required canonical testnet credentials/env/config items are missing
- Scope: read-only repository contract review and documentation-only gap report
- Second preflight executed in this review: NO
- Credentials/env/config modified in this review: NO
- Secret values read or exposed in this review: NO
- Runtime enabled in this review: NO
- HTTP/network attempted in this review: NO

## Reviewed Contract Sources

- `anchor-backend/docker-compose.override.yml`
- `anchor-backend/app/actions/runner.py`
- `anchor-backend/app/executors/testnet_real_handoff_adapter.py`
- `anchor-backend/app/executors/testnet_order_executor.py`
- `scripts/local_testnet_runtime_check.sh`
- `docs/TESTNET_SECRETS_CUSTODY_V1.md`
- `docs/REAL_TESTNET_CREDENTIAL_HANDOFF_RULE_V1.md`
- `docs/REAL_TESTNET_FIRST_REAL_REQUEST_ENABLEMENT_CHECKLIST_V1.md`
- `docs/GO_LIVE_CHECKLIST.md`

No real secret values were read, printed, copied, hashed, or modified.

## Contract Summary

The canonical runtime contract is the `TESTNET_EXCHANGE_*` and `TESTNET_EXECUTOR_*` family injected into the runtime process environment. The first approved handoff model is runtime process environment only, fed from an approved secret store or operator-controlled runtime injection, never from repository files.

The canonical deployment/runtime provisioning location currently referenced by compose and runtime-check tooling is:

```text
/etc/project-anchor/testnet.env
```

That file path is outside the repository and must remain outside Git. Values must be provided by the operator or approved secret store, then injected into backend and worker runtime environment.

## Field Contract Results

| Field | Canonical loader/reference | Required or optional | Required condition | Expected non-secret shape | Secret | May be committed to Git | Current status | Remediation owner |
|---|---|---:|---|---|---:|---:|---|---|
| `TESTNET_EXCHANGE_BASE_URL` | `runner.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required | Required for canonical testnet host-safety preflight and runtime execution path | non-empty HTTPS testnet origin, expected allowlisted origin such as `https://demo-fapi.binance.com` | NO | NO as runtime config value; placeholder/example only | MISSING in failed preflight scope | OPERATOR |
| `TESTNET_EXCHANGE_API_KEY` | `runner.py`, `testnet_order_executor.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required | Required before credential-presence gate can pass for real testnet execution | non-empty opaque testnet API key; value must never be printed | YES | NO | MISSING in failed preflight scope | OPERATOR |
| `TESTNET_EXCHANGE_API_SECRET` | `runner.py`, `testnet_order_executor.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required | Required before credential-presence gate and real signing can proceed in later authorized execution | non-empty opaque testnet API secret; value must never be printed | YES | NO | MISSING in failed preflight scope | OPERATOR |
| `TESTNET_EXCHANGE_KEY_ID` | `runner.py`, `testnet_real_handoff_adapter.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required by boundary/preflight contract | Required by runner boundary preflight and review/audit surface; low-level real wire helper only requires key and secret | non-secret review identifier or suffix; not usable as a credential | NO | NO as runtime config value; safe suffix may be documented only if explicitly approved | MISSING in failed preflight scope | OPERATOR |
| `TESTNET_EXECUTOR_MODE` | `runner.py`, `testnet_real_handoff_adapter.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required for runtime execution decision | Required to choose `mock` vs `real`; for future bounded runtime preflight it must be explicitly `real`, while disabled/mock handoff posture expects `mock` | exact value `real` for authorized real runtime preflight/execution; exact value `mock` for safe credential-free handoff posture | NO | NO as runtime config value; placeholder/example only | MISSING in failed preflight scope | OPERATOR |
| `TESTNET_EXECUTOR_REAL_ENABLE` | `testnet_order_executor.py`, `testnet_real_handoff_adapter.py`, `docker-compose.override.yml`, `local_testnet_runtime_check.sh` | required for real wire | Required to permit real wire helper past `TESTNET_REAL_WIRE_DISABLED`; for future bounded runtime preflight it must be exactly `1`, while disabled/mock handoff posture expects `0` | exact string `1` for authorized real wire preflight/execution; exact string `0` for disabled/mock posture | NO | NO as runtime config value; placeholder/example only | MISSING in failed preflight scope | OPERATOR |

## Required Determinations

1. `TESTNET_EXCHANGE_KEY_ID` is truly required by the active boundary/preflight contract, because `runner.py` requires key id together with API key and API secret before credential-presence gate passes. It is not required by the low-level real wire helper, which only checks key and secret before signing, but the active boundary should still require it for auditability and review.
2. `TESTNET_EXECUTOR_MODE` and `TESTNET_EXECUTOR_REAL_ENABLE` are not required to keep the runtime disabled. They are required only for the future explicitly authorized bounded real runtime preflight/execution posture. While runtime remains disabled or credential-free handoff is being reviewed, the safe posture remains `mock` and `0`.
3. The canonical provisioning location is `/etc/project-anchor/testnet.env`, injected into backend and worker via compose/runtime environment. Repository `.env` files are not approved as the canonical first handoff model.
4. The failed preflight did not check the canonical runtime source. It checked the current process/repository env-like scope and therefore correctly reported missing items for that scope, but it did not prove `/etc/project-anchor/testnet.env` or container runtime env is missing.
5. A contract mismatch was found: the one-time preflight presence check used an incomplete environment source compared with the canonical contract. The missing result is valid for the checked scope, but remediation must target the canonical runtime injection path.
6. No item is caused by a source-code requirement defect in this review. The gap is provisioning and preflight-source alignment, not runtime code enablement.

## Safe Operator Provisioning Sequence

Use placeholders only in docs and chat. Do not paste real values.

1. Confirm a separate provisioning authorization exists before writing any runtime env/config.
2. Prepare the approved out-of-repository target:

```text
/etc/project-anchor/testnet.env
```

3. Populate only through an operator-controlled secure channel or approved secret store materialization. The expected placeholder shape is:

```text
TESTNET_EXCHANGE_BASE_URL=<testnet_https_origin>
TESTNET_EXCHANGE_API_KEY=<secret:testnet_api_key>
TESTNET_EXCHANGE_API_SECRET=<secret:testnet_api_secret>
TESTNET_EXCHANGE_KEY_ID=<non_secret_key_identifier_or_suffix>
TESTNET_EXECUTOR_MODE=real
TESTNET_EXECUTOR_REAL_ENABLE=1
```

4. Ensure the file remains outside Git and is not copied into repository docs, shell history, screenshots, or terminal transcript.
5. Restart only the intended runtime components after a separate authorization exists.
6. Request a fresh, separate authorization before running another bounded preflight.

## Secret-Safe Verification Command

The existing command that can verify presence/shape without printing values is:

```bash
bash scripts/local_testnet_runtime_check.sh
```

This command is not authorized in this review because it can start docker services and perform local HTTP health/ops checks. A dry-run help/contract review is safe, but a real execution requires separate authorization.

The secret-safe runtime env check embedded in that script reports only states such as `PRESENT`, `MISSING`, `EMPTY`, `REAL`, and `ONE`, not raw values.

## Required Authorizations Before Continuing

- Fresh separate authorization before provisioning `/etc/project-anchor/testnet.env`: YES
- Fresh separate authorization before restarting runtime components: YES
- Fresh separate authorization before rerunning bounded preflight: YES
- Fresh separate authorization before runtime path enablement: YES
- Fresh separate authorization before canary: YES
- Fresh separate authorization before any external request: YES

## Locked Boundary

- preflight execution count remains exactly one
- second preflight authorized: NO
- second preflight executed: NO
- credentials/env/config modification authorized: NO
- credentials/env/config modified: NO
- secret values disclosed: NO
- runtime path enabled: NO
- signing enabled: NO
- HTTP/network attempted: NO
- external request sent: NO
- canary executed: NO
- go-live/live trading: NO-GO

ENV_CONTRACT_REVIEW_RESULT=PASS
CANONICAL_PROVISIONING_LOCATION_IDENTIFIED=YES
MISSING_ITEMS_CONFIRMED=YES
CONTRACT_MISMATCH_FOUND=YES
OPERATOR_SECRET_PROVISIONING_REQUIRED=YES
SECOND_PREFLIGHT_AUTHORIZATION_REQUIRED=YES
NEXT_SAFE_STATE=READY_FOR_CANONICAL_TESTNET_ENV_PROVISIONING_AUTHORIZATION_REQUEST_PREP
RUNTIME_REMAINS_DISABLED=YES
