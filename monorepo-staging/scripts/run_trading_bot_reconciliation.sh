#!/usr/bin/env bash
set -euo pipefail

# Reconcile the scan log against actual Alpaca fills.
#
# The bot records an order's status at submission (PENDING_NEW / ACCEPTED) and
# never revisits it, so on its own it cannot tell a filled order from a
# rejected one. Alpaca is the system of record for fills; this is the join
# between them. Read-only: it places no orders.
#
#   --json   machine-readable output

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
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.services.reconciliation "$@"
