---
name: bridge-protocol
description: Claude↔Codex 文件桥接协议的完整操作规程——桥接目录布局、任务 JSON 结构与状态流转、派活/接活/归档流程。当需要让 Codex 干执行类活（跑代码、终端操作、识别图片、批量处理文件），或需要处理 Codex 写进 outbox 的任务时使用。
---

# Claude ↔ Codex 桥接协议

## 何时用这个 Skill

- 需要 Codex 执行：跑代码、终端操作、识别图片、批量处理文件
- 需要处理 Codex 写进 `outbox/` 的任务（可配 SessionStart hook 在会话开始自动提醒 pending 任务）
- 需要查任务 JSON 该怎么写、状态怎么流转、做完怎么归档

## 桥接根目录

本 skill 假定桥接根目录为 `<BRIDGE_DIR>`（clone [claude-codex-bridge](https://github.com/zhl110/claude-codex-bridge) 的位置）。`bridge.sh` 以自身所在目录为桥接根，`inbox/`、`outbox/`、`history/` 运行时自动创建。

| 路径 | 用途 | 谁写 |
|---|---|---|
| `inbox/` | Claude 写入的任务 → Codex 读取执行 | Claude |
| `outbox/` | Codex 写入的任务 → Claude 读取执行 | Codex |
| `history/` | 已完成任务归档 | 双方 |
| `PROTOCOL.md` | 协议原文定义 | — |
| `task-schema.json` | 任务 JSON Schema | — |
| `bridge.sh` | Claude Code 端桥接工具脚本 | — |

---

## 任务 JSON 结构

Schema：`task-schema.json`（JSON Schema draft 2020-12）。
必填字段：`id` / `from` / `to` / `type` / `subject` / `payload` / `status` / `created_at`

```json
{
  "id": "uuid-v4",
  "from": "claude",
  "to": "codex",
  "type": "task",
  "subject": "一句话描述（≤200 字符）",
  "payload": "详细指令：做什么、在哪做、验收标准是什么",
  "context": {
    "project": "/path/to/project",
    "files": ["相关文件路径"],
    "selection": "选中的代码片段"
  },
  "status": "pending",
  "result": null,
  "reply_to": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### 字段约束（schema 原文，取值别自创）

| 字段 | 取值 |
|---|---|
| `id` | string，UUID v4 |
| `from` / `to` | 枚举 `claude` \| `codex` |
| `type` | 枚举 `task` \| `review` \| `question` \| `handoff` \| `notify` |
| `subject` | string，**最长 200 字符** |
| `payload` | string |
| `context` | 可选 object：`project`(string) / `files`(string[]) / `selection`(string) |
| `status` | 枚举 `pending` \| `accepted` \| `running` \| `done` \| `rejected` |
| `result` / `reply_to` | string |
| `created_at` / `updated_at` | ISO8601 date-time |

---

## 状态流转

```
pending → accepted → running → done
                        ↘ rejected
```

- 看到 `pending` → 立刻改 `accepted`（**先认领再动手**，避免双方抢同一个任务）
- 动手执行前 → `running`
- 完成 → `done`，同时填 `result`
- 做不了 → `rejected`，在 `result` 里写清原因

---

## 三类动作

### A. Claude 派活给 Codex

1. 写 `inbox/task-{id前8位}.json`，`from: "claude"`、`to: "codex"`、`status: "pending"`
   （或直接 `./bridge.sh send-task "<subject>" "<payload>"`）
2. 触发执行：`codex exec "处理桥接任务 inbox/task-{id前8位}.json"`
3. Codex 更新状态 → `accepted` → `running` → `done`，填写 `result`
4. Claude 读取 `result`，决定下一步

### B. 处理 outbox 里的活（Codex 派给 Claude）

1. 扫 `outbox/*.json` 找 `status: "pending"`（或 `./bridge.sh check-outbox`）
2. 改 `accepted` → 开始执行前改 `running`
3. 执行任务
4. 改 `done` + 填 `result`；无法执行改 `rejected` + 说明原因

### C. 归档

任务完成后把文件移入 `history/`（或 `./bridge.sh archive <任务文件路径>`）：

```
history/task-{id前8位}-{完成时间戳}.json
```

---

## 命名规范

- 任务文件：`task-{uuid前8位}.json`
- 归档文件：`history/task-{uuid前8位}-{完成时间戳}.json`

---

## 注意事项

- **先改状态再干活**：`pending → accepted` 不能省，否则双方可能同时执行同一任务
- **`payload` 要写完整**：执行类活（代码、终端）Codex 没有当前会话的上下文，路径、约束、验收标准必须在 payload 里写清
- **`rejected` 必填原因**：填进 `result`，不能只改状态就了事
- **归档才算闭环**：文件出现在 `history/` 里，任务才真正结束
- **回复要串起来**：回复类任务填 `reply_to` 指向原任务 id，保持链路可追

---

## 自查命令

```bash
# 查有没有 Codex 派来的活
grep -l '"status": *"pending"' <BRIDGE_DIR>/outbox/*.json

# 或用 bridge.sh
<BRIDGE_DIR>/bridge.sh check-outbox
```
