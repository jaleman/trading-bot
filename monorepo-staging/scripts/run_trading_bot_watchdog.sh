#!/usr/bin/env bash
set -euo pipefail

# Alert when the daily scan has NOT run.
#
# Runs as its own scheduled job, separate from the scan. A watchdog inside the
# thing it watches cannot report that thing stopping -- which is exactly what
# happened between 2026-04-24 and 2026-07-25: the scan stopped, and because a
# stopped scan writes no logs and raises no errors, absence was
# indistinguishable from a quiet market.
#
#   --check-only   report without sending (exit 1 if stale)

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
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.services.watchdog "$@"
