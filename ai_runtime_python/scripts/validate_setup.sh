#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$ROOT_DIR/venv/bin/python"

printf "\n🔍 Validating AI Daemon setup...\n\n"

if [[ -x "$VENV_BIN" ]]; then
  PY_CMD="$VENV_BIN"
else
  PY_CMD="python3"
fi

if "$PY_CMD" -c "import aiohttp, yaml, asyncio, aiosqlite, psutil" >/dev/null 2>&1; then
  echo "✅ Python dependencies available"
else
  echo "❌ Missing python dependencies. Run ./scripts/install.sh" >&2
  exit 1
fi

missing=0
for file in config/system.yaml config/services.yaml; do
  if [[ -f "$ROOT_DIR/$file" ]]; then
    echo "✅ $file present"
  else
    echo "❌ $file missing"
    missing=1
  fi
done

if [[ $missing -ne 0 ]]; then
  echo "❌ Required configuration files missing" >&2
  exit 1
fi

"$PY_CMD" - <<'PY'
import asyncio
from datetime import datetime
from core.memory import ExperienceDB

async def main():
    db = ExperienceDB('knowledge/experience.db')
    await db.log_metrics({
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_percent': 0,
        'memory_percent': 0,
        'disk_percent': 0
    })
    trends = await db.analyze_trends('cpu_percent', window_hours=1)
    await db.close()
    print('✅ Database operational (trend sample:', trends or 'n/a', ')')

asyncio.run(main())
PY

if pgrep -f "core/daemon.py" >/dev/null 2>&1; then
  echo "✅ Daemon process detected"
else
  echo "ℹ️  Daemon process not running"
fi

echo "\nValidation complete!"
