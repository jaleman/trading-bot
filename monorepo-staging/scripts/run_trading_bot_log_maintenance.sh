#!/usr/bin/env bash
set -euo pipefail

# Runtime log rotation and off-machine backup.
#   rotate              - archive oversized human-readable logs (never the JSONL)
#   backup [dest-dir]   - copy runtime logs to an off-machine destination;
#                         defaults to TRADING_BOT_BACKUP_DEST from the
#                         environment or the gitignored .env
#
# trades.jsonl is the source of truth the read model replays; it is never
# rotated. Rotated archives are never deleted -- they hold crash tracebacks
# that the JSONL does not.
#
# The destination is resolved here rather than passed on the command line
# because the scheduler does not tokenise like a shell: the Google Drive path
# contains a space ("My Drive"), and ZeroClaw split it into two arguments --
# with or without quotes -- so the scheduled backup failed every run. Keeping
# the path out of the cron command removes that class of failure entirely.

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

# `backup` with no destination resolves one from the environment or .env.
# Grepped, not sourced -- .env also holds broker and API credentials that have
# no business in this shell.
if [[ "${1:-}" == "backup" && $# -eq 1 ]]; then
	DEST="${TRADING_BOT_BACKUP_DEST:-}"
	ENV_FILE="$APP_DIR/.env"
	if [[ -z "$DEST" && -f "$ENV_FILE" ]]; then
		DEST="$(grep -E '^TRADING_BOT_BACKUP_DEST=' "$ENV_FILE" 2>/dev/null \
			| head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)"
	fi
	if [[ -z "$DEST" ]]; then
		echo "No backup destination given and TRADING_BOT_BACKUP_DEST is not set." >&2
		echo "Pass one explicitly, or set it in $ENV_FILE." >&2
		exit 1
	fi
	set -- backup "$DEST"
fi

export PYTHONPATH="$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$APP_DIR"
exec "$RESOLVED_PYTHON_BIN" -m trading_bot.persistence.log_maintenance "$@"
