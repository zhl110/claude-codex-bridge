# Computer Use Bridge 使用指南

## 概述

`bridge.py` 让 Claude Code 能像真人一样操控你的电脑桌面。
- **Claude Code** = 大脑（决策）
- **minicpm-v:8b** = 眼睛（描述画面）
- **bridge.py** = 手（执行动作）

## 文件位置

- 主程序：`computer-use/bridge.py`
- 截图输出：`computer-use/_bridge_screen.jpg`（每次覆盖）
- 依赖：`pillow`, `pywin32`, `pywinauto`
- 前置：Ollama 运行中，`minicpm-v:8b` 已拉取（`ollama pull minicpm-v:8b`）

## 所有命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `python bridge.py describe` | 截图+视觉模型描述画面 | Claude 获取屏幕信息 |
| `python bridge.py screen` | 仅截图 | 快速保存画面 |
| `python bridge.py resolution` | 获取分辨率 | 确认屏幕尺寸 |
| `python bridge.py click X Y` | 左键点击 | `click 500 300` |
| `python bridge.py rclick X Y` | 右键点击 | `rclick 500 300` |
| `python bridge.py dclick X Y` | 双击 | `dclick 200 150` |
| `python bridge.py move X Y` | 移动光标（不点击） | `move 800 400` |
| `python bridge.py drag X1 Y1 X2 Y2` | 鼠标拖拽 | `drag 100 100 500 500` |
| `python bridge.py type "文字"` | 剪贴板粘贴输入 | `type "hello world"` |
| `python bridge.py key "按键"` | 发送按键 | `key "{ENTER}"` / `key "^c"` |
| `python bridge.py scroll N` | 滚轮（正=上，负=下） | `scroll 3` / `scroll -5` |
| `python bridge.py wait N` | 等待 N 秒 | `wait 1.5` |

## 快捷键语法（key 命令）

| 语法 | 含义 |
|------|------|
| `^c` | Ctrl+C |
| `^v` | Ctrl+V |
| `%{F4}` | Alt+F4 |
| `{ENTER}` | 回车 |
| `{TAB}` | Tab |
| `{ESC}` | Escape |
| `{F5}` | F5 |
| `{VK_F5}` | 虚拟键码 F5 |

## 标准工作流

```
1. describe     → Claude 看到画面描述
2. 分析         → Claude 决定下一步动作
3. click/type   → 执行动作
4. wait 0.5     → 等待 UI 响应
5. describe     → 验证结果
6. 循环直到完成
```

## 注意事项

- 首次 `describe` 可能慢（模型冷加载），后续 2-5 秒
- 视觉模型给出的坐标是近似值，偏差可能 ±50-100 像素，需要验证循环纠正
- `type` 走剪贴板粘贴，支持中文，但某些安全输入框可能拦截
- 所有错误输出到 stderr 以 JSON 格式，exit code 1

## 快速启动

```bash
# 1. 确认 Ollama 在跑
ollama list

# 2. 确认能截图
python computer-use/bridge.py screen

# 3. 确认视觉模型能描述
python computer-use/bridge.py describe
```

三个都通过 → 随时可用。
