#!/usr/bin/env bash
set -euo pipefail

# Install the /bot poller as a launchd user service so it survives reboots and
# restarts if it dies.
#
# Also disables ZeroClaw's Telegram channel, which is required rather than
# optional: two processes cannot poll one bot token, and they would silently
# steal each other's messages. Outbound delivery still works -- `zeroclaw
# channel send` sends with the channel disabled (verified 2026-07-25).
#
#   install_operator_poller_service.sh            install and start
#   install_operator_poller_service.sh --uninstall stop and remove

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LABEL="com.trading-bot.operator-poller"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$MONOREPO_ROOT/runtime/trading-bot/logs"

if [[ "${1:-}" == "--uninstall" ]]; then
	launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
	rm -f "$PLIST"
	echo "Uninstalled $LABEL"
	exit 0
fi

if ! grep -qE '^TELEGRAM_BOT_TOKEN=.+' "$MONOREPO_ROOT/apps/trading-bot/.env" 2>/dev/null; then
	echo "TELEGRAM_BOT_TOKEN is not set in apps/trading-bot/.env" >&2
	echo "Add it (from @BotFather) before installing the service." >&2
	exit 1
fi

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>$LABEL</string>
	<key>ProgramArguments</key>
	<array>
		<string>$MONOREPO_ROOT/scripts/run_trading_bot_operator_poller.sh</string>
	</array>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<true/>
	<key>StandardOutPath</key>
	<string>$LOG_DIR/operator-poller.log</string>
	<key>StandardErrorPath</key>
	<string>$LOG_DIR/operator-poller.log</string>
	<key>ProcessType</key>
	<string>Background</string>
</dict>
</plist>
PLIST_EOF

echo "Wrote $PLIST"

if command -v zeroclaw >/dev/null 2>&1; then
	echo "Disabling ZeroClaw's Telegram channel (required: one poller per token)"
	zeroclaw config set channels.telegram.default.enabled false >/dev/null 2>&1 || true
	zeroclaw service restart >/dev/null 2>&1 || true
fi

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
sleep 2

if launchctl list | grep -q "$LABEL"; then
	echo "Started $LABEL"
	echo "Logs: $LOG_DIR/operator-poller.log"
else
	echo "Service did not start; check $LOG_DIR/operator-poller.log" >&2
	exit 1
fi
