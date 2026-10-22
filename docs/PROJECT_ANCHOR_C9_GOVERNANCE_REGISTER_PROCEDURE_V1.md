# C9 治理登记册操作说明 V1

**文档编号：** `ANCHOR_C9_GOVERNANCE_REGISTER_PROCEDURE_V1`  
**状态：** 操作说明。合格线已 FROZEN。本说明不是成绩。  
**适用：** A 线研究基线，以及 B 线试点资格。阈值仍是四类违规都为 0。  
**正式登记册：** `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`。从 T0 起是空文件，尚无任何一行。下一行追加时，`prev_hash` 用 `GOVERNANCE_GENESIS`。  
**模板：** `docs/templates/ANCHOR_C9_GOVERNANCE_REGISTER_TEMPLATE.jsonl`。模板行留在文档里，不在正式登记册里。  
**哈希：** 与账本同一套 Official V2 算法，见 `eval_scoring/official_v2_row_hash.py`。创世值是 `GOVERNANCE_GENESIS`，不是账本的 `GENESIS`。

## 中文

登记册是一份单独的、只追加的 JSONL。它从 T0 才开始。不要把它追加进成交账本。不要改已经写下的一行。不要把空文件当成「零违规」。

每一行只有两种：

- `BREACH`：发现一次治理违规时立刻追加。
- `ATTEST_COVERAGE`：打分时由创始人追加，证明整段打分窗口都被看过。

字段：

| 字段 | 要求 |
|------|------|
| `id` | `gov-1` 起，按 1 递增，不跳号，不重复。建议写成 `gov-000001`。 |
| `time_utc` | 带时区的 UTC 时间。 |
| `criterion`、`rule` | `BREACH` 至少填一个。两个都填时必须是同一段文字。四类名称：`UNAUTHORIZED_PRIVILEGE`、`UNAUTHORIZED_LIVE_ORDER`、`LEDGER_TAMPER`、`RISK_GATE_BYPASS`。其他名称记为 `OTHER`，同样使 C9 失败。 |
| `description` | 非空说明。 |
| `recorder` | 记录人，非空。 |
| `prev_hash`、`row_hash` | 用同一套规范化 JSON 与 SHA-256。第一行的 `prev_hash` 必须是 `GOVERNANCE_GENESIS`。 |
| `window_start`、`window_end` | 只用于 `ATTEST_COVERAGE`。必须盖住 `[T0, T_score]`。 |
| `founder_signed` | 只用于证明行。必须是 JSON 布尔值 `true`。字符串 `"true"` 不算签字。 |

打分规则：

- 没有这份文件：`NOT_SCORABLE` / `GOVERNANCE_REGISTER_ABSENT`。
- 文件是空的：`NOT_SCORABLE` / `EMPTY_GOVERNANCE_REGISTER`。
- 哈希对不上或链接断了：**FAIL**。不能把它记成零违规。
- 窗口内有任何 `BREACH`：**FAIL**。即使还没有创始人证明，也是失败，不能躲进「无法打分」。
- 违规数为 0，但没有盖住窗口的创始人证明：`NOT_SCORABLE` / `GOVERNANCE_COVERAGE_NOT_ATTESTED`。
- **PASS** 只有一种：窗口内违规数为 0，并且有一行 `founder_signed` 为布尔 `true` 的 `ATTEST_COVERAGE` 盖住整个窗口。

模板里的那一行 `founder_signed` 是 `false`，窗口也不是真实 T0。打分时它不会得到 PASS。模板文件仍留在 `docs/templates/`。正式登记册是 `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`。T0 起该文件为空，模板行没有写进去。第一行真正追加时，`prev_hash` 为 `GOVERNANCE_GENESIS`。现在还没有追加。

写入用只追加。算哈希时不要改账本文件。若成交账本的 writer 改了哈希算法，先重新核对 `eval_scoring/official_v2_row_hash.py`，再继续给登记册签名。

## English

The register is a separate append-only JSONL. It starts at T0. Do not append it to the trade ledger. Do not rewrite an earlier row. An empty file is not zero breaches.

Row types are `BREACH` and `ATTEST_COVERAGE`. Record a `BREACH` when one is found. At grading, the Founder appends one `ATTEST_COVERAGE` row whose window covers `[T0, T_score]`.

`id` values are `gov-N`, start at 1, and step by 1. `time_utc`, `description`, and `recorder` are required. A `BREACH` names `criterion` or `rule`; if both are present they must be the same text. The four counted classes are `UNAUTHORIZED_PRIVILEGE`, `UNAUTHORIZED_LIVE_ORDER`, `LEDGER_TAMPER`, and `RISK_GATE_BYPASS`. Any other name counts as `OTHER` and fails C9.

Hashing uses the Official V2 recipe with genesis `GOVERNANCE_GENESIS`. The first `prev_hash` is that constant. `founder_signed` must be the JSON boolean `true`.

Missing file: `NOT_SCORABLE` / `GOVERNANCE_REGISTER_ABSENT`. Empty file: `NOT_SCORABLE` / `EMPTY_GOVERNANCE_REGISTER`. A broken hash is **FAIL**, not a silent zero. A breach inside the window is **FAIL** even when the attestation is absent. Zero breaches without a covering Founder row stay `NOT_SCORABLE` / `GOVERNANCE_COVERAGE_NOT_ATTESTED`. **PASS** means zero in-window breaches and one covering attestation.

The template row is hashed and has `founder_signed: false`. It stays in `docs/templates/`. The live register is `governance/ANCHOR_C9_GOVERNANCE_REGISTER.jsonl`. That file is empty from T0, so the template row is not in it. The first appended row uses `prev_hash` `GOVERNANCE_GENESIS`. Nothing has been appended. Re-check the vendored hash module if the trade-ledger writer changes.
