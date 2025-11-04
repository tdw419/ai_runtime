#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/venv"

printf "\n🚀 Setting up AI System Daemon...\n\n"

python3 -c "import sys; assert sys.version_info >= (3, 8), 'Python 3.8+ required'"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install psutil aiohttp pyyaml aiosqlite

mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/knowledge"

python - <<'PY'
from core.memory import ExperienceDB

ExperienceDB('knowledge/experience.db')
print('✅ Database initialized')
PY

cat <<MSG
✅ AI Daemon setup complete!
📁 Edit config files in: $ROOT_DIR/config/
💡 Start with: ./scripts/start.sh
MSG
