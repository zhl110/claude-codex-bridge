# Bridge Protocol — Claude Code ↔ Codex

让 Claude Code 与 Codex CLI 通过共享文件目录协作的轻量协议。无需服务、无需网络、无需第三方依赖——一个文件夹就是一条桥。

## 目录结构

```
claude-codex-bridge/          ← 仓库根即桥接根目录
├── PROTOCOL.md               本协议定义
├── task-schema.json          任务 JSON Schema
├── bridge.sh                 Claude Code 端桥接工具脚本
├── inbox/                    Claude 写入任务 → Codex 读取执行（运行时自动创建）
├── outbox/                   Codex 写入任务 → Claude 读取执行（运行时自动创建）
├── history/                  已完成任务归档（运行时自动创建）
├── skill/SKILL.md            Claude Code skill 版操作规程
└── computer-use/             另一套桥：Claude 驱动 + 本地视觉模型操控 Windows 桌面
```

## 任务生命周期

```
pending → accepted → running → done
                            ↘ rejected
```

## 任务 JSON 结构

```json
{
  "id": "uuid",
  "from": "claude|codex",
  "to":   "claude|codex",
  "type": "task|review|question|handoff|notify",
  "subject": "一句话描述",
  "payload": "详细指令或问题",
  "context": {
    "project": "项目路径",
    "files": ["相关文件路径"],
    "selection": "选中代码片段"
  },
  "status": "pending",
  "result": null,
  "reply_to": "关联任务id（回复时填写）",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## 工作流示例

### Claude 派任务给 Codex

1. Claude 写入 `inbox/task-{id}.json`，状态 `pending`
2. Claude 执行 `codex exec "处理桥接任务 inbox/task-{id}.json"`
3. Codex 更新状态 → `accepted` → `running` → `done`，填写 result
4. Claude 读取结果，决定下一步

### Codex 向 Claude 提问

1. Codex 写入 `outbox/task-{id}.json`，状态 `pending`
2. Claude 检测到新任务（用户通知或轮询）
3. Claude 更新状态 → `accepted` → `running` → `done`，填写 result
4. Codex 读取 Claude 的回复

## 状态流转规则

- 接收方看到 `pending` 任务后，先改为 `accepted`
- 开始执行时改为 `running`
- 完成后改为 `done`，填写 `result` 字段
- 无法执行时改为 `rejected`，在 `result` 中说明原因

## 命名规范

- 任务文件：`task-{uuid前8位}.json`
- 归档文件：`history/task-{uuid前8位}-{完成时间戳}.json`
