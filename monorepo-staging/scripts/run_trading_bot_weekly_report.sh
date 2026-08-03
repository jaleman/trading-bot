#!/usr/bin/env bash
set -uo pipefail

# Generates the weekly buy/sell/hold decision-rationale PDF and drops it in
# <repo-root>/reports/. Intended for the Saturday cron job -- see the
# "Companion job: weekly decision report" section in
# zeroclaw/cron/trading-bot-daily-scan.md.
#
# reportlab has no business in the trading runtime's venv (same reasoning as
# build_executive_summary.py), but a cron job can't interactively create a
# throwaway one and `pip install` over the network every run without that
# failure becoming silent. So this maintains its own small persistent venv,
# built once and reused -- network is only required the first time.
#
# Usage: run_trading_bot_weekly_report.sh [--dry-run]
#   --dry-run  print what would be sent to Telegram instead of sending it

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MONOREPO_ROOT/.." && pwd)"
APP_DIR="$MONOREPO_ROOT/apps/trading-bot"
ENV_FILE="$APP_DIR/.env"
REPORT_VENV="$MONOREPO_ROOT/.report-venv"
REPORTS_DIR="$REPO_ROOT/reports"

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

if [[ ! -x "$REPORT_VENV/bin/python" ]]; then
	python3 -m venv "$REPORT_VENV"
	"$REPORT_VENV/bin/pip" install --quiet reportlab
fi

RECIPIENT="${TRADING_BOT_TELEGRAM_RECIPIENT:-}"
if [[ -z "$RECIPIENT" && -f "$ENV_FILE" ]]; then
	RECIPIENT="$(grep -E '^TRADING_BOT_TELEGRAM_RECIPIENT=' "$ENV_FILE" 2>/dev/null \
		| head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs || true)"
fi

PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

DELIVERY_LOG="$MONOREPO_ROOT/runtime/trading-bot/logs/delivery.log"

record_delivery() {
	mkdir -p "$(dirname "$DELIVERY_LOG")" 2>/dev/null || true
	printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >>"$DELIVERY_LOG" 2>/dev/null || true
	echo "$1" >&2
}

notify() {
	local message="$1"
	if [[ "$DRY_RUN" == "1" ]]; then
		echo "--- would send to Telegram ---"
		echo "$message"
		echo "------------------------------"
		return 0
	fi
	if [[ -z "$RECIPIENT" ]]; then
		record_delivery "SKIPPED no TRADING_BOT_TELEGRAM_RECIPIENT configured"
		return 0
	fi
	if ! command -v zeroclaw >/dev/null 2>&1; then
		record_delivery "SKIPPED zeroclaw not on PATH (PATH=$PATH)"
		return 0
	fi
	local output
	if output="$(zeroclaw channel send "$message" \
		--channel-id telegram --recipient "$RECIPIENT" 2>&1)"; then
		record_delivery "SENT ok"
	else
		record_delivery "FAILED ${output//$'\n'/ }"
	fi
}

mkdir -p "$REPORTS_DIR"

STARTED="$(date '+%Y-%m-%d %H:%M:%S')"
BUILD_OUTPUT="$(cd "$REPORTS_DIR" && "$REPORT_VENV/bin/python" \
	"$SCRIPT_DIR/build_weekly_decision_report.py" --last-full-week 2>&1)"
BUILD_STATUS=$?

if [[ $BUILD_STATUS -ne 0 ]]; then
	DETAIL="$(printf '%s\n' "$BUILD_OUTPUT" | tail -12)"
	notify "$(printf 'trading-bot: WEEKLY REPORT FAILED\nstarted: %s\n\n%s' "$STARTED" "$DETAIL")"
	echo "$BUILD_OUTPUT"
	exit $BUILD_STATUS
fi

REPORT_NAME="$(printf '%s\n' "$BUILD_OUTPUT" | grep -oE '[^ /]*\.pdf' | tail -1)"
REPORT_FILE="${REPORT_NAME:+$REPORTS_DIR/$REPORT_NAME}"
notify "$(printf 'trading-bot: weekly decision report ready\n%s' "${REPORT_FILE:-$REPORTS_DIR}")"
echo "$BUILD_OUTPUT"
exit 0
