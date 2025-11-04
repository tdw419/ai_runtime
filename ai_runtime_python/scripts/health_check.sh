#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$ROOT_DIR/logs/daemon.log"
VENV_BIN="$ROOT_DIR/venv/bin/python"

printf "\n🩺 AI Daemon Health Check\n"

if pgrep -f "core/daemon.py" > /dev/null; then
  echo "✅ Daemon process is running"
else
  echo "❌ Daemon process not found"
fi

if [[ -f "$LOG_FILE" ]]; then
  echo "\nRecent log entries:"
  tail -n 20 "$LOG_FILE"
else
  echo "\nℹ️  Log file not found at $LOG_FILE"
fi

echo "\nPython environment:"
if [[ -x "$VENV_BIN" ]]; then
  "$VENV_BIN" -c "import sys; print('Python', sys.version)"
else
  python3 -c "import sys; print('Python', sys.version)"
fi
