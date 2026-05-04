# DOMAIN_COMMAND_VALIDATION_DEV_USAGE_V1.md

## 1. 目的

本文档用于固定 dev-only 路由 `/domain-command-validation-dev` 的最小运行说明，明确调用方式、正向示例、反向示例和预期返回结构。

本文档只描述当前 dev-only validation 链的使用方式，不修改任何业务代码，不扩展到主业务路由，不包含未来规划。

## 2. 路由地址

- `POST /domain-command-validation-dev`

## 3. 调用命令

```bash
curl -sS -X POST "http://127.0.0.1:8000/domain-command-validation-dev?command_type=quote" \
  -H "Content-Type: application/json" \
  -d '{"command_type":"quote","symbol":"BTCUSDT"}'
```

## 4. 正向示例

请求条件：

- `command_type=quote`
- `payload={"command_type":"quote","symbol":"BTCUSDT"}`

请求命令：

```bash
curl -sS -X POST "http://127.0.0.1:8000/domain-command-validation-dev?command_type=quote" \
  -H "Content-Type: application/json" \
  -d '{"command_type":"quote","symbol":"BTCUSDT"}'
```

预期结果：

- `summary.is_valid=true`
- `summary.error_codes=[]`
- `summary.validation.missing_required_fields=[]`
- `summary.validation.unexpected_fields=[]`

## 5. 反向示例

请求条件：

- `command_type=quote`
- `payload={"command_type":"quote"}`

请求命令：

```bash
curl -sS -X POST "http://127.0.0.1:8000/domain-command-validation-dev?command_type=quote" \
  -H "Content-Type: application/json" \
  -d '{"command_type":"quote"}'
```

预期结果：

- `summary.is_valid=false`
- `summary.error_codes` 包含 `MISSING_REQUIRED_FIELDS`
- `summary.validation.missing_required_fields` 包含 `symbol`

## 6. 返回结构说明

顶层固定键：

- `command_type`
- `payload`
- `summary`

`summary` 固定键：

- `command_type`
- `is_valid`
- `error_codes`
- `validation`

`validation` 固定键：

- `command_type`
- `is_valid_command_type`
- `missing_required_fields`
- `unexpected_fields`

## 7. 当前边界

- 当前仅为 dev-only validation 链。
- 当前尚未接入主业务 domain-commands 执行链。
- 当前不改变 worker、risk、ops、audit、release 或主业务路由逻辑。
- 当前不新增数据库结构，不引入执行链副作用。
