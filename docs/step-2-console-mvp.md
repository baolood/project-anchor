# Project Anchor – Step 2 Console MVP

## Step 2 – Console Commands List (MVP)

### 目标

在不修改 Anchor 后端状态机（PENDING / PROCESSING / DONE / FAILED），
不引入任何新前端框架的前提下，完成 Console 的最小可用 Commands 列表页面（MVP），
用于验证前后端链路、Proxy 结构与 UI 基础可行性。

本阶段的目标不是功能完整，而是：

- 跑通
- 稳定
- 可演进

---

### 已完成内容

#### 一、后端（anchor-backend）

- 当前实现为占位接口，返回空数组 `[]`
- 仅用于 unblock Console 列表能力
- 不影响既有 `POST /commands`、worker 与状态机逻辑

验证方式：

```bash
curl -i http://127.0.0.1:8000/commands
