#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="ai-daemon"
PYTHON_BIN="$ROOT_DIR/venv/bin/python"
DAEMON_ENTRY="core/daemon.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "❌ Virtual environment not found. Run ./scripts/install.sh first." >&2
  exit 1
fi

case "$OSTYPE" in
  linux-gnu*)
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    sudo tee "$SERVICE_FILE" >/dev/null <<SERVICE
[Unit]
Description=AI System Daemon
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$ROOT_DIR
Environment=PATH=$ROOT_DIR/venv/bin
ExecStart=$PYTHON_BIN $ROOT_DIR/$DAEMON_ENTRY
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo "✅ Linux service installed. Start with: sudo systemctl start $SERVICE_NAME"
    ;;
  darwin*)
    PLIST="$HOME/Library/LaunchAgents/com.${USER}.${SERVICE_NAME}.plist"
    cat <<PLIST > "$PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.${USER}.${SERVICE_NAME}</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$ROOT_DIR/$DAEMON_ENTRY</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$ROOT_DIR/logs/daemon.log</string>
  <key>StandardErrorPath</key>
  <string>$ROOT_DIR/logs/daemon.error.log</string>
</dict>
</plist>
PLIST

    launchctl load "$PLIST"
    echo "✅ macOS service installed and started"
    ;;
  *)
    echo "⚠️ Unsupported OS for automated deployment." >&2
    exit 1
    ;;
 esac
