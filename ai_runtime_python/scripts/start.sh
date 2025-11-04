#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "❌ Virtual environment not found. Run ./scripts/install.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

exec python -m core.daemon
