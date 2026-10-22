# Official pass line V1.1 freeze record

**Document ID:** `ANCHOR_OFFICIAL_PASS_LINE_V1_1_FREEZE_RECORD`  
**Status:** freeze record for commit A. This file does not change the sign-off page.  
**Live trading:** NO-GO. This record does not authorize orders, a Pilot, or a deploy.

| Field | Value |
|-------|--------|
| T0 (Asia/Shanghai) | `2026-10-22T20:27:21+08:00` |
| `T0_FROZEN` | `YES` |
| T_alloc | blank (no new allocation rule) |
| Founder name | baolood herid |
| Signature | Founder chat confirmation 2026-10-22 20:24 Asia/Shanghai via Grok Bot |
| R0 seed | blank. The scorer does not require a seed. The expected random-direction book remains the binding comparison. |
| Sign-off page | `docs/PROJECT_ANCHOR_OFFICIAL_EVALUATION_PASS_LINE_V1_1_SIGN_OFF.md` |
| Sign-off page SHA-256 (file bytes in commit A) | `8a31095dc854d5fe95fd481ec8673df2cee2c40afcfc0361ab52b5852d94287f` |
| Commit A SHA | `92141c19b57667861818850732b23ecf07d0fb5e` |
| Bundle `affl_v2/engine.py` SHA-256 | `299569516edda10e6464246457a5d3e6149ac56900fac04be90fd5fbcef1d1c8` |
| r2.2 candidate `engine.py` SHA-256 | `cd40e5a4186dd3314450388b91a30f06176d97040236a111f5a2093de3506e45` |

Commit A is the freeze. Its author time and committer time are T0. The four hash functions in those two `engine.py` files are byte-identical. Genesis for the trade ledger is `GENESIS`. Re-check `eval_scoring/official_v2_row_hash.py` if the writer changes.

The C9 register is `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`. It is empty. Nothing has been appended. The first appended row's `prev_hash` is `GOVERNANCE_GENESIS`. The template row stays in `docs/templates/ANCHOR_C9_GOVERNANCE_REGISTER_TEMPLATE.jsonl` and is not in the live register.

Thresholds are the V1 R2 thresholds. They were not changed in commit A or in this record.
