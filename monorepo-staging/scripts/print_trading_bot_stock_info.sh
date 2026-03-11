#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/trading-bot"
APP_VENV_PYTHON="$APP_DIR/.venv/bin/python"

if [[ -n "${PYTHON_BIN:-}" ]]; then
	RESOLVED_PYTHON_BIN="$PYTHON_BIN"
elif [[ -x "$APP_VENV_PYTHON" ]]; then
	RESOLVED_PYTHON_BIN="$APP_VENV_PYTHON"
else
	echo "Missing app-local Python environment: $APP_VENV_PYTHON" >&2
	echo "Run $REPO_ROOT/scripts/bootstrap_trading_bot.sh before printing stock info." >&2
	exit 1
fi

if [[ $# -lt 1 ]]; then
	echo "Usage: $0 <TICKER>" >&2
	exit 1
fi

export PYTHONPATH="$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$APP_DIR"
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.operator_commands info "$@"