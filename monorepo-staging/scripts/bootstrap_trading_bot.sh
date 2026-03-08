#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/trading-bot"
VENV_DIR="$APP_DIR/.venv"
BASE_PYTHON="${BOOTSTRAP_PYTHON:-$(command -v python3)}"

if [[ ! -x "$BASE_PYTHON" ]]; then
	echo "Unable to find a usable python3 interpreter for bootstrap." >&2
	exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
	echo "Creating virtualenv at $VENV_DIR"
	"$BASE_PYTHON" -m venv "$VENV_DIR"
else
	echo "Reusing existing virtualenv at $VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -e "$APP_DIR"

echo "Bootstrap complete."
echo "Run the staged app with: $REPO_ROOT/scripts/run_trading_bot.sh"
echo "Run the staged tests with: $REPO_ROOT/scripts/run_trading_bot_tests.sh"
