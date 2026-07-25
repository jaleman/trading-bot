#!/usr/bin/env bash
set -euo pipefail

# Runtime log rotation and off-machine backup.
#   rotate              - archive oversized human-readable logs (never the JSONL)
#   backup <dest-dir>   - copy runtime logs to an off-machine destination
#
# trades.jsonl is the source of truth the read model replays; it is never
# rotated. Rotated archives are never deleted -- they hold crash tracebacks
# that the JSONL does not.

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
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.persistence.log_maintenance "$@"
