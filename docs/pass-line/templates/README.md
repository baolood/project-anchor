# C9 incident register template

`C9_INCIDENT_REGISTER.jsonl` is an empty append-only template.

It is not the live scoring register. That file is `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`, and this package does not append to it.

`eval_scoring` does not read this template. An empty file is not a zero-incident score and not a Founder attestation. Do not start `ATTEST_ZERO` rows from here.
