#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/trading-bot"
ENV_FILE="$APP_DIR/.env"
STRATEGY_FILE="$APP_DIR/config/strategy.local.json"
RUNNER="$SCRIPT_DIR/run_trading_bot.sh"

if [[ ! -f "$ENV_FILE" ]]; then
	echo "Missing staged env file: $ENV_FILE" >&2
	echo "Create it from $APP_DIR/.env.example before running the rehearsal." >&2
	exit 1
fi

if [[ ! -f "$STRATEGY_FILE" ]]; then
	echo "Missing staged strategy file: $STRATEGY_FILE" >&2
	echo "Create it from $APP_DIR/config/strategy.example.json before running the rehearsal." >&2
	exit 1
fi

exec "$RUNNER" \
	--config "$STRATEGY_FILE" \
	--env-file "$ENV_FILE" \
	--rehearsal \
	"$@"
