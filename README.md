# Claude ↔ Codex Bridge

让 Claude Code 与 Codex CLI 通过**共享文件目录**协作的轻量协议，外加一套**本地视觉模型驱动的 Windows 桌面操控桥**。

零服务、零网络依赖、零第三方框架——一个文件夹就是一条桥。

> 起源：作者在用 Orca 这类多 Agent 编排平台之前，需要让 Claude Code（规划）和 Codex CLI（执行）互相派活。文件桥接是最简单可靠的办法：一方写 JSON 任务进 `inbox/`，另一方读走、执行、写回结果。

## 两套工具

### 1. 任务桥协议（`PROTOCOL.md` + `bridge.sh`）

Claude Code 与 Codex 双向派活的文件协议：

```
Claude ──写任务──▶ inbox/ ──▶ Codex 读取执行 ──写结果──▶ 同一文件
Codex ──写任务──▶ outbox/ ──▶ Claude 读取执行 ──写结果──▶ 同一文件
```

- 任务 = 一个 JSON 文件（schema 见 `task-schema.json`），字段含发送方、类型（task/review/question/handoff/notify）、详细指令、状态
- 状态机：`pending → accepted → running → done / rejected`，先认领再动手，避免双方抢同一任务
- `bridge.sh` 封装常用操作：`send-task` / `check-inbox` / `check-outbox` / `accept` / `done` / `reject` / `archive`
- 已完成任务移入 `history/` 归档，链路可追

**快速开始**：

```bash
# 克隆后，仓库根就是桥接根目录（bridge.sh 以自身位置定位）
cd claude-codex-bridge

# Claude 侧创建任务发给 Codex
./bridge.sh send-task "识别这张图" "请读取 C:/path/to/img.jpg 并描述内容"

# 触发 Codex 执行
codex exec "处理桥接任务 inbox/task-xxxx.json"

# 查看任务状态
./bridge.sh check-inbox
```

配合 Claude Code skill 使用：把 `skill/SKILL.md` 复制到 `~/.claude/skills/bridge-protocol/`，Agent 就会按规程派活、接活、归档。

### 2. Computer Use 桌面操控桥（`computer-use/`）

让 Claude Code 像真人一样操控 Windows 桌面：

- **Claude Code** = 大脑（决策）
- **本地 Ollama 视觉模型**（minicpm-v）= 眼睛（描述画面）
- **bridge.py** = 手（截图、点击、输入、滚动）

```bash
python computer-use/bridge.py describe   # 截图 + 视觉模型描述画面
python computer-use/bridge.py click 500 300
python computer-use/bridge.py type "hello"
```

支持 describe / click / type / key / scroll / drag / wait 等原子动作，详见 [`computer-use/bridge_usage.md`](computer-use/bridge_usage.md)。另有 `cu.py`：截图 → 视觉模型 → 动作 → 验证的自动循环版。

**依赖**：Python 3.8+、`pillow`、`pywin32`、`pywinauto`、[Ollama](https://ollama.com)（`ollama pull minicpm-v:8b`）。

## 目录结构

```
claude-codex-bridge/
├── PROTOCOL.md          任务桥协议定义
├── task-schema.json     任务 JSON Schema
├── bridge.sh            Claude Code 端桥接工具脚本（bash）
├── skill/SKILL.md       Claude Code skill 版操作规程
├── computer-use/        桌面操控桥（bridge.py 主程序 / cu.py 自动循环 / 使用指南）
├── inbox/  outbox/  history/   运行时自动创建，已在 .gitignore 排除
└── README.md
```

## 适用场景与限制

**适合**：同一台机器上 Claude Code + Codex CLI 协作；不想跑常驻服务；需要任务留痕可审计。

**不适合**：跨机器协作（文件在同一磁盘）；实时对话式交互（任务粒度是异步的）。如果你在用 Orca 这类多 Agent 编排平台，它内置的 worker 编排是更强的替代方案——本项目的价值在于零依赖、五分钟上手。

## 设计原则

1. **文件即真相**：任务状态、结果全在 JSON 文件里，`git` 可审计
2. **先认领再执行**：`pending → accepted` 防止双 Agent 抢任务
3. **payload 自包含**：执行方没有派活方的会话上下文，路径、约束、验收标准必须写全
4. **归档才算闭环**：文件进入 `history/` 任务才真正结束

## License

[MIT](LICENSE)
