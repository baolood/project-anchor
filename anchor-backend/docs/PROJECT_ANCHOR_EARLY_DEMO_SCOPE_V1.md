# PROJECT_ANCHOR_EARLY_DEMO_SCOPE_V1

## 1. 当前判断

Project Anchor 当前不能作为真实交易系统对外开放。  
但可以作为 Early Demo 对外展示纪律执行、风控检查、命令流和运维状态。

## 2. Early Demo 定位

Project Anchor Early Demo 是一个纪律执行与风险控制演示系统。  
它不是收益工具，不是自动交易托管系统，不接管用户资金。

## 3. 允许展示的内容

- /ops 状态
- /commands 命令流
- /checklist 负责人检查流程
- /recovery 当前恢复边界
- cloud_runtime_check_readonly.sh 的 PASS / FAIL 输出
- 模拟 order / quote / preview 的 DONE / FAILED 证据
- 端口已从 0.0.0.0 收口到 127.0.0.1 的云端安全证据
- backend health 返回 {"ok":true} 的运行证据

## 4. 禁止展示成真实能力的内容

- 不展示为真实自动交易系统
- 不展示为收益工具
- 不开放真实资金
- 不开放真实交易所 API key
- 不开放 Codex / Cursor 生产写权限
- 不承诺盈利
- 不给用户真实下单入口
- 不宣传“已经可托管交易”

## 5. 对外一句话版本

Project Anchor 是一个帮助交易者执行纪律、检查风险、减少情绪化操作的控制系统；当前 Early Demo 只展示流程和风控能力，不执行真实交易。

## 6. 下一步唯一外部动作

完成 Early Demo Scope 后，下一步只做一个只读演示入口或一页对外说明。  
不做真实交易上线。  
不接用户资金。  
不接真实 API key。

## 7. 验收标准

- 只新增本文档
- 不改 backend
- 不改 worker
- 不改 compose
- 不改 env
- 不改 nginx / UFW
- 明确允许展示范围
- 明确禁止真实交易承诺
- 明确下一步只读展示动作

## 8. 回滚方式

删除本文档即可回滚。
