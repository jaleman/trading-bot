#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAW_COMMAND="$(printf '%s' "$*" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

if [[ -z "$RAW_COMMAND" ]]; then
	echo "Usage: $0 </bot list|/bot summary|/bot pending|/bot status|/bot balance|/bot holdings|/bot info TICKER|/bot sync|/bot restart|bot list|bot summary|bot pending|bot status|bot balance|bot holdings|bot info TICKER|bot sync|bot restart>" >&2
	exit 1
fi

COMMAND_TOKEN="$RAW_COMMAND"
COMMAND_ARG=""

if [[ "$RAW_COMMAND" =~ ^/[Bb][Oo][Tt]([[:space:]]+.*)?$ ]]; then
	RAW_COMMAND="bot${RAW_COMMAND:4}"
fi

if [[ "$RAW_COMMAND" =~ ^([Ll][Ii][Ss][Tt]|[Ss][Uu][Mm][Mm][Aa][Rr][Yy]|[Pp][Ee][Nn][Dd][Ii][Nn][Gg]|[Ss][Tt][Aa][Tt][Uu][Ss]|[Bb][Aa][Ll][Aa][Nn][Cc][Ee]|[Hh][Oo][Ll][Dd][Ii][Nn][Gg][Ss]|[Ii][Nn][Ff][Oo]|[Ss][Yy][Nn][Cc]|[Rr][Ee][Ss][Tt][Aa][Rr][Tt])([[:space:]]+.*)?$ ]]; then
	RAW_COMMAND="bot $RAW_COMMAND"
fi

if [[ "$RAW_COMMAND" =~ ^[Bb][Oo][Tt][[:space:]]+ ]]; then
	COMMAND_TOKEN="bot"
	COMMAND_ARG="$(printf '%s' "${RAW_COMMAND#${RAW_COMMAND%%[[:space:]]*}}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
fi

if [[ "$COMMAND_TOKEN" != "bot" && "$RAW_COMMAND" == *[[:space:]]* ]]; then
	COMMAND_TOKEN="${RAW_COMMAND%%[[:space:]]*}"
	COMMAND_ARG="$(printf '%s' "${RAW_COMMAND#"$COMMAND_TOKEN"}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
fi

NORMALIZED_TOKEN="$(printf '%s' "$COMMAND_TOKEN" | tr '[:upper:]' '[:lower:]')"

if [[ "$NORMALIZED_TOKEN" == "bot" ]]; then
	SUBCOMMAND_TOKEN="$COMMAND_ARG"
	SUBCOMMAND_ARG=""
	if [[ -z "$SUBCOMMAND_TOKEN" ]]; then
		echo "Usage: bot <list|summary|pending|status|balance|holdings|info TICKER|sync|restart>" >&2
		exit 1
	fi
	if [[ "$SUBCOMMAND_TOKEN" == *[[:space:]]* ]]; then
		SUBCOMMAND_ARG="$(printf '%s' "${SUBCOMMAND_TOKEN#${SUBCOMMAND_TOKEN%%[[:space:]]*}}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
		SUBCOMMAND_TOKEN="${SUBCOMMAND_TOKEN%%[[:space:]]*}"
	fi
	NORMALIZED_TOKEN="bot:$(printf '%s' "$SUBCOMMAND_TOKEN" | tr '[:upper:]' '[:lower:]')"
	COMMAND_ARG="$SUBCOMMAND_ARG"
fi

case "$NORMALIZED_TOKEN" in
	bot:list|!list|/list)
		exec "$SCRIPT_DIR/print_trading_bot_supported_commands.sh"
		;;
	bot:summary|/summary)
		exec "$SCRIPT_DIR/print_trading_bot_operator_summary.sh"
		;;
	bot:pending|/pending)
		exec "$SCRIPT_DIR/print_trading_bot_pending_orders.sh"
		;;
	bot:status|/status)
		exec "$SCRIPT_DIR/print_trading_bot_runtime_status.sh"
		;;
	bot:balance|/balance)
		exec "$SCRIPT_DIR/print_trading_bot_balance.sh"
		;;
	bot:holdings|/holdings)
		exec "$SCRIPT_DIR/print_trading_bot_holdings.sh"
		;;
	bot:info|/info)
		if [[ -z "$COMMAND_ARG" ]]; then
			echo "Usage: bot info <TICKER>" >&2
			exit 1
		fi
		exec "$SCRIPT_DIR/print_trading_bot_stock_info.sh" "$COMMAND_ARG"
		;;
	bot:sync|/sync)
		exec "$SCRIPT_DIR/sync_openclaw_workspace.sh"
		;;
	bot:restart|/restart)
		exec "$SCRIPT_DIR/restart_openclaw_gateway.sh"
		;;
	*)
		echo "Unsupported command. Available commands: /bot list | /bot summary | /bot pending | /bot status | /bot balance | /bot holdings | /bot info <TICKER> | /bot sync | /bot restart"
		exit 0
		;;
esac