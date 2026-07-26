#!/usr/bin/env bash
set -euo pipefail

# Deterministic /bot Telegram poller. No model in the path.
#
# Requires TELEGRAM_BOT_TOKEN in apps/trading-bot/.env -- ZeroClaw stores the
# token encrypted and will not reveal it, so the poller needs its own copy.
#
# ZeroClaw's Telegram channel must be DISABLED while this runs. Two processes
# cannot poll one bot token; Telegram hands each update to whichever asks
# first, so they would steal messages from each other. Outbound delivery is
# unaffected: `zeroclaw channel send` works with the channel disabled.
#
#   zeroclaw config set channels.telegram.default.enabled false
#
#   --once   single poll cycle, for testing

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
	echo "Run $REPO_ROOT/scripts/bootstrap_trading_bot.sh first." >&2
	exit 1
fi

export PYTHONPATH="$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$APP_DIR"
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.services.operator_poller "$@"
