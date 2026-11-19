#!/usr/bin/env bash
# Bridge tool for Claude Code ↔ Codex communication
# Usage:
#   bridge send-task   "<subject>" "<payload>"   → 创建任务发往 Codex
#   bridge check-inbox                          → 检查 inbox 中已完成的任务
#   bridge check-outbox                         → 检查 Codex 发来的新任务
#   bridge accept <task-id>                     → 标记任务为 accepted
#   bridge done   <task-id>  "<result>"         → 标记任务为 done 并填写结果
#   bridge reject <task-id>  "<reason>"         → 标记任务为 rejected
#   bridge archive <task-id>                    → 归档已完成任务
#   bridge list-inbox                           → 列出所有 inbox 任务
#   bridge list-outbox                          → 列出所有 outbox 任务
set -euo pipefail

# Primary bridge: project-local (Codex sandbox can write here)
BRIDGE_DIR="$(dirname "$0")"
# Fallback: global bridge (some Codex sessions may use this)
GLOBAL_BRIDGE="$HOME/.codex/bridge"
INBOX="$BRIDGE_DIR/inbox"
OUTBOX="$BRIDGE_DIR/outbox"
HISTORY="$BRIDGE_DIR/history"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

ensure_dirs() {
  mkdir -p "$INBOX" "$OUTBOX" "$HISTORY"
}

gen_uuid8() {
  # Generate 8-char hex from uuidgen or random
  if command -v uuidgen &>/dev/null; then
    uuidgen | tr -d '-' | cut -c1-8
  else
    echo "$(date +%s%N)$$" | md5sum | cut -c1-8 2>/dev/null || \
    printf '%08x' "$((RANDOM * RANDOM))"
  fi
}

# Write a task JSON to stdout
write_task() {
  local id="$1" from="$2" to="$3" type="$4" subject="$5" payload="$6"
  cat <<EOF
{
  "id": "$id",
  "from": "$from",
  "to": "$to",
  "type": "$type",
  "subject": "$subject",
  "payload": $(echo "$payload" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$payload\""),
  "context": {
    "project": "$(pwd)",
    "files": [],
    "selection": ""
  },
  "status": "pending",
  "result": null,
  "reply_to": null,
  "created_at": "$TIMESTAMP",
  "updated_at": "$TIMESTAMP"
}
EOF
}

# update task status and result
update_task() {
  local file="$1" status="$2" result="${3:-null}"
  local tmp="${file}.tmp"
  python3 -c "
import json, sys
with open('$file') as f:
    t = json.load(f)
t['status'] = '$status'
t['result'] = $result
t['updated_at'] = '$TIMESTAMP'
with open('$tmp', 'w') as f:
    json.dump(t, f, indent=2, ensure_ascii=False)
" 2>/dev/null && mv "$tmp" "$file"
  echo "Updated $file → $status"
}

# ── Commands ──

cmd_send_task() {
  ensure_dirs
  local subject="$1" payload="$2" id=$(gen_uuid8)
  local file="$INBOX/task-${id}.json"
  write_task "$id" "claude" "codex" "task" "$subject" "$payload" > "$file"
  echo "Task created: $file"
  echo "Run: codex exec \"请处理桥接任务 ~/.codex/bridge/inbox/task-${id}.json\""
}

cmd_check_inbox() {
  ensure_dirs
  echo "=== Inbox Tasks (Claude → Codex) ==="
  for f in "$INBOX"/task-*.json; do
    [ -f "$f" ] || { echo "No tasks in inbox."; break; }
    python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
print(f'{t[\"id\"]} | {t[\"status\"]:8s} | {t[\"subject\"]}')
" 2>/dev/null || echo "$(basename $f) | (unreadable)"
  done
}

cmd_check_outbox() {
  ensure_dirs
  echo "=== Outbox Tasks (Codex → Claude) ==="
  local found=false
  for f in "$OUTBOX"/task-*.json; do
    [ -f "$f" ] || { echo "No tasks in outbox."; break; }
    found=true
    python3 -c "
import json
with open('$f') as fh:
    t = json.load(fh)
print(f'{t[\"id\"]} | {t[\"status\"]:8s} | {t[\"subject\"]}')
print(f'  Payload: {t[\"payload\"][:200]}')
" 2>/dev/null
  done
}

cmd_accept() { ensure_dirs; update_task "$1" "accepted" "null"; }
cmd_done() { ensure_dirs; update_task "$1" "done" "\"$2\""; }
cmd_reject() { ensure_dirs; update_task "$1" "rejected" "\"$2\""; }

cmd_archive() {
  ensure_dirs
  local file="$1" base=$(basename "$file" .json)
  local dest="$HISTORY/${base}-$(date -u +"%Y%m%d%H%M%S").json"
  mv "$file" "$dest"
  echo "Archived → $(basename "$dest")"
}

cmd_list_inbox() {
  ensure_dirs
  ls -la "$INBOX"/task-*.json 2>/dev/null || echo "No inbox tasks."
}

cmd_list_outbox() {
  ensure_dirs
  ls -la "$OUTBOX"/task-*.json 2>/dev/null || echo "No outbox tasks."
}

cmd_read_task() {
  local file="$1"
  [ -f "$file" ] || { echo "File not found: $file"; exit 1; }
  python3 -c "
import json
with open('$file') as f:
    t = json.load(f)
print(json.dumps(t, indent=2, ensure_ascii=False))
"
}

# ── Main ──

case "${1:-help}" in
  send-task)       cmd_send_task "${2:-}" "${3:-}" ;;
  check-inbox)     cmd_check_inbox ;;
  check-outbox)    cmd_check_outbox ;;
  accept)          cmd_accept "$2" ;;
  done)            cmd_done "$2" "${3:-}" ;;
  reject)          cmd_reject "$2" "${3:-}" ;;
  archive)         cmd_archive "$2" ;;
  list-inbox)      cmd_list_inbox ;;
  list-outbox)     cmd_list_outbox ;;
  read)            cmd_read_task "$2" ;;
  *)
    echo "Usage: bridge <command> [args...]"
    echo "Commands: send-task, check-inbox, check-outbox, accept, done, reject, archive, list-inbox, list-outbox, read"
    ;;
esac
