# PROJECT_ANCHOR_READONLY_DEMO_ENTRY_TASKCARD_V1

## 1. 任务结论

本任务卡用于约束下一轮“只读演示入口”实现。

当前只允许先定义实现边界，不允许直接进入页面实现。

目标是确保 Early Demo 的展示入口只读、可验收、可回滚，不引入真实交易、真实资金、真实 API key、生产写操作或自动化执行能力。

---

## 2. 只允许改哪个仓库

只允许改：

- `anchor-console`

不允许改：

- `anchor-backend`
- `local_box`
- 云主机文件
- nginx
- UFW
- Docker / compose
- env / secrets
- 数据库
- worker
- risk
- migrations

---

## 3. 只允许改哪些文件

下一轮实现时，只允许新增或修改前端只读展示文件。

建议允许范围：

- `anchor-console/app/demo/page.tsx`

如必须增加导航入口，最多允许改：

- `anchor-console/app/page.tsx`

禁止修改：

- `anchor-console/app/api/**`
- `anchor-console/config/**`
- `anchor-console/package.json`
- `anchor-console/next.config.ts`
- `anchor-backend/**`
- 任何部署、环境、代理、后端、worker、risk 文件

---

## 4. 只读页面展示哪些内容

只读演示入口页面只展示：

- Project Anchor Early Demo 定位
- 当前不是自动交易系统
- 当前不接资金、不接真实 API key、不承诺收益
- 演示顺序：
  - `/ops`
  - `/commands`
  - `/checklist`
  - `/recovery`
- 只读健康检查概念：
  - `cloud_runtime_check_readonly.sh`
  - `SYSTEM_NORMAL / SYSTEM_NOT_NORMAL`
- 当前云端安全证据：
  - backend / postgres / redis 端口收口到 `127.0.0.1`
  - backend health 可返回 `{"ok":true}`
- 下一步用户访谈目标：
  - 找 3–5 个真实 crypto 交易者看 20 分钟演示

---

## 5. 禁止新增哪些按钮

禁止新增任何会产生写操作或误导真实交易能力的按钮：

- 禁止“开始交易”
- 禁止“连接交易所”
- 禁止“绑定 API Key”
- 禁止“自动执行”
- 禁止“真实下单”
- 禁止“同步账户”
- 禁止“部署”
- 禁止“重启服务”
- 禁止“修改配置”
- 禁止“开启 Codex / Cursor 自动操作”

允许的按钮仅限：

- 跳转 `/ops`
- 跳转 `/commands`
- 跳转 `/checklist`
- 跳转 `/recovery`
- 复制只读检查命令说明
- 返回首页

---

## 6. 禁止调用哪些写接口

下一轮实现严禁调用任何写接口。

禁止调用：

- `POST /commands`
- `POST /domain-commands/*`
- `POST /ops/kill-switch`
- `POST /ops/*`
- 任何 create / update / delete / retry / execute / cancel 类接口
- 任何会改变 backend、worker、risk、compose、env、数据库状态的接口

允许：

- 静态页面
- 纯文案
- 纯链接
- 不触发后端写操作的只读说明

---

## 7. 实现验收标准

下一轮实现完成后必须满足：

- 只改允许文件
- 不改 backend
- 不改 worker
- 不改 API proxy
- 不改 compose / env / nginx / UFW
- 不新增真实交易按钮
- 不新增 API key 输入框
- 不新增任何写接口调用
- 页面明确写出：
  - Early Demo 不执行真实交易
  - 不接用户资金
  - 不承诺收益
  - 只展示纪律执行、风控检查、命令流和运维状态
- 页面能在本地 Next dev 打开
- 页面可见 `/ops`、`/commands`、`/checklist`、`/recovery` 入口

---

## 8. 回滚方式

如果下一轮实现未提交：

```bash
cd /Users/baolood/Projects/project-anchor/anchor-console
git checkout -- app/page.tsx
rm -rf app/demo
git status --short
```

如果下一轮实现已经提交：

```bash
cd /Users/baolood/Projects/project-anchor/anchor-console
git revert HEAD
```

如果父仓库只记录 submodule 指针变化：

```bash
cd /Users/baolood/Projects/project-anchor
git checkout -- anchor-console
git status --short
```

---

## 9. 本任务卡验收标准

本轮只新增本文档。

验收标准：

- 只新增 `anchor-backend/docs/PROJECT_ANCHOR_READONLY_DEMO_ENTRY_TASKCARD_V1.md`
- 不改 frontend
- 不改 backend
- 不改 worker
- 不改 deploy / compose / env / nginx / UFW
- 明确允许仓库
- 明确允许文件
- 明确页面展示内容
- 明确禁止按钮
- 明确禁止写接口
- 明确实现验收
- 明确回滚方式

Final: 本文档通过后，下一轮才允许进入只读演示入口页面实现。
