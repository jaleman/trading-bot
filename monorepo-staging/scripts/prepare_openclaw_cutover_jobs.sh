#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LIVE_JOBS="/Users/labanlaro/.openclaw/cron/jobs.json"
TEMPLATE="$REPO_ROOT/openclaw/cron/trading-bot-daily-scan.template.json"
STAMP="${1:-$(date +%Y%m%d-%H%M%S)}"
OUTPUT_DIR="$REPO_ROOT/runtime/cutover-rehearsal/$STAMP"
OUTPUT_FILE="$OUTPUT_DIR/jobs.candidate.json"
APP_VENV_PYTHON="$REPO_ROOT/apps/trading-bot/.venv/bin/python"

if [[ -n "${PYTHON_BIN:-}" ]]; then
	RESOLVED_PYTHON_BIN="$PYTHON_BIN"
elif [[ -x "$APP_VENV_PYTHON" ]]; then
	RESOLVED_PYTHON_BIN="$APP_VENV_PYTHON"
else
	echo "Missing app-local Python environment: $APP_VENV_PYTHON" >&2
	echo "Run $REPO_ROOT/scripts/bootstrap_trading_bot.sh before preparing candidate jobs." >&2
	exit 1
fi

mkdir -p "$OUTPUT_DIR"

"$RESOLVED_PYTHON_BIN" "$SCRIPT_DIR/merge_openclaw_trading_job.py" \
	--target "$LIVE_JOBS" \
	--template "$TEMPLATE" \
	--output "$OUTPUT_FILE"

echo "Candidate jobs file written to: $OUTPUT_FILE"