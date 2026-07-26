#!/usr/bin/env bash
set -uo pipefail

# The complete daily flow: scan, then report the outcome to Telegram.
#
# This is what the scheduler runs. Deliberately a plain shell script with no
# agent in the path: `zeroclaw channel send` delivers "without starting the
# full agent loop" (verified 2026-07-25 -- 1s, zero trace events), so neither
# execution nor reporting depends on a model interpreting instructions.
#
# The previous design failed exactly there. Its scheduled payload was prose
# addressed to an LLM ("run the scan, then send that summary to Telegram")
# with best-effort delivery, so when it stopped on 2026-04-24 nothing said so
# for three months.
#
# A failing scan reports the failure. Silence is never the success signal.
#
# This script PLACES PAPER ORDERS. The scan is invoked with
# --execute-paper-trades, without which `daily_scan` runs every analysis stage
# and then returns with an empty `order_results` -- the execution branch, the
# trade-limit guardrail, the position-size check and the execution-intent
# firewall all sit behind that flag. Until 2026-07-26 this script omitted it,
# so the scheduled job would have decided to sell and never sold, while still
# reporting a healthy scan every morning.
#
# Usage: run_trading_bot_daily.sh [--dry-run]
#   --dry-run  scan only: places no orders and sends nothing, printing the
#              summary that would have been delivered

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$MONOREPO_ROOT/apps/trading-bot"
ENV_FILE="$APP_DIR/.env"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# Telegram user/chat id. Read from the environment or the gitignored .env
# rather than committed. Grepped, not sourced -- .env also holds broker and
# API credentials that have no business in this shell.
RECIPIENT="${TRADING_BOT_TELEGRAM_RECIPIENT:-}"
if [[ -z "$RECIPIENT" && -f "$ENV_FILE" ]]; then
	RECIPIENT="$(grep -E '^TRADING_BOT_TELEGRAM_RECIPIENT=' "$ENV_FILE" 2>/dev/null \
		| head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs || true)"
fi

notify() {
	local message="$1"
	if [[ "$DRY_RUN" == "1" ]]; then
		echo "--- would send to Telegram ---"
		echo "$message"
		echo "------------------------------"
		return 0
	fi
	if [[ -z "$RECIPIENT" ]]; then
		echo "No TRADING_BOT_TELEGRAM_RECIPIENT configured; skipping delivery." >&2
		return 0
	fi
	if ! command -v zeroclaw >/dev/null 2>&1; then
		echo "zeroclaw not on PATH; skipping delivery." >&2
		return 0
	fi
	# Delivery failure must not mask the scan result, so this never aborts.
	zeroclaw channel send "$message" \
		--channel-id telegram --recipient "$RECIPIENT" >/dev/null 2>&1 \
		|| echo "WARNING: Telegram delivery failed." >&2
}

STARTED="$(date '+%Y-%m-%d %H:%M:%S')"
if [[ "$DRY_RUN" == "1" ]]; then
	# --dry-run suppresses execution as well as delivery. A flag by that name
	# that still placed real orders would be a trap worth avoiding.
	SCAN_OUTPUT="$("$SCRIPT_DIR/run_trading_bot_rehearsal.sh" 2>&1)"
	SCAN_STATUS=$?
else
	SCAN_OUTPUT="$("$SCRIPT_DIR/run_trading_bot_rehearsal.sh" --execute-paper-trades 2>&1)"
	SCAN_STATUS=$?
fi

if [[ $SCAN_STATUS -ne 0 ]]; then
	# Last few lines carry the traceback tail; the full record is in trades.log.
	DETAIL="$(printf '%s\n' "$SCAN_OUTPUT" | tail -12)"
	notify "$(printf 'trading-bot: SCAN FAILED\nstarted: %s\nexit code: %s\n\n%s' \
		"$STARTED" "$SCAN_STATUS" "$DETAIL")"
	echo "$SCAN_OUTPUT"
	exit $SCAN_STATUS
fi

SUMMARY="$("$SCRIPT_DIR/print_trading_bot_operator_summary.sh" 2>&1)" || SUMMARY=""
if [[ -z "${SUMMARY// }" ]]; then
	SUMMARY="Scan completed but produced no operator summary."
fi

notify "$(printf 'trading-bot: daily scan\n%s\n\n%s' "$STARTED" "$SUMMARY")"
echo "$SCAN_OUTPUT"
exit 0
