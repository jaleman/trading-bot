#!/usr/bin/env bash
set -euo pipefail

# Deploy the repository-managed ZeroClaw config to the live runtime.
#
# One-way by design: repo -> runtime. The deployed config is runtime state,
# this repo is the contract. Nothing here reads changes back, which is the
# decision recorded in todo.md and inherited from the OpenClaw contract.
#
# The live config is backed up before every write, because channel tokens are
# set directly on it via `zeroclaw config set` (masked input) and are NOT
# stored in the repo. If a sync would drop a secret, the backup is how you get
# it back -- and --check will warn before that happens.
#
# Usage:
#   sync_zeroclaw_config.sh            deploy config
#   sync_zeroclaw_config.sh --check    show the diff, change nothing
#   sync_zeroclaw_config.sh --with-cron  deploy config, then apply the daily scan

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONOREPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$MONOREPO_ROOT/.." && pwd)"
TEMPLATE="$MONOREPO_ROOT/zeroclaw/config/config.template.toml"
LIVE_CONFIG="${ZEROCLAW_CONFIG:-/opt/homebrew/var/zeroclaw/config.toml}"
BACKUP_DIR="$MONOREPO_ROOT/runtime/zeroclaw-backups"

MODE="deploy"
case "${1:-}" in
	--check) MODE="check" ;;
	--with-cron) MODE="with-cron" ;;
	"") ;;
	*) echo "Unknown option: $1" >&2; exit 2 ;;
esac

if [[ ! -f "$TEMPLATE" ]]; then
	echo "Missing config template: $TEMPLATE" >&2
	exit 1
fi

if ! command -v zeroclaw >/dev/null 2>&1; then
	echo "zeroclaw is not on PATH. Install with: brew install zeroclaw" >&2
	exit 1
fi

RENDERED="$(mktemp)"
trap 'rm -f "$RENDERED"' EXIT
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$TEMPLATE" > "$RENDERED"

if [[ "$MODE" == "check" ]]; then
	echo "Template renders for repo root: $REPO_ROOT"
	echo "Live config: $LIVE_CONFIG"
	echo
	if [[ -f "$LIVE_CONFIG" ]]; then
		diff -u "$LIVE_CONFIG" "$RENDERED" && echo "Live config already matches the repo."
	else
		echo "No live config yet; a deploy would create it."
	fi
	exit 0
fi

# Some config is runtime-only and must survive a redeploy:
#
#   channels.*     credentials -- ZeroClaw requires bot_token on a Telegram
#                  channel, so the section cannot exist in the repo at all
#   peer_groups.*  operator identity bindings written by
#                  `zeroclaw channel bind-telegram`
#
# Overwriting either would silently unpair the operator channel: the daemon
# keeps running, the bot simply stops answering. That is the same
# fails-quietly-and-nobody-notices shape that made this project dormant for
# three months, so these sections are carried across rather than replaced.
PRESERVE_PREFIXES="channels peer_groups"
if [[ -f "$LIVE_CONFIG" ]]; then
	PRESERVED="$(mktemp)"
	python3 - "$LIVE_CONFIG" "$PRESERVE_PREFIXES" > "$PRESERVED" <<'PYEOF'
import re, sys

text = open(sys.argv[1], encoding="utf-8").read()
prefixes = tuple(sys.argv[2].split())
out, keeping = [], False
for line in text.splitlines():
    header = re.match(r"\s*\[+([^\]]+)\]+\s*$", line)
    if header:
        keeping = header.group(1).startswith(prefixes)
    if keeping:
        out.append(line)
if out:
    print("\n# --- preserved from the live config (runtime-only: secrets, bindings) ---")
    print("\n".join(out))
PYEOF
	if [[ -s "$PRESERVED" ]]; then
		cat "$PRESERVED" >> "$RENDERED"
		echo "Preserved live [channels.*] configuration (contains credentials)."
	fi
	rm -f "$PRESERVED"
fi

if [[ -f "$LIVE_CONFIG" ]]; then
	mkdir -p "$BACKUP_DIR"
	BACKUP="$BACKUP_DIR/config-$(date +%Y%m%d-%H%M%S).toml"
	cp "$LIVE_CONFIG" "$BACKUP"
	echo "Backed up live config to $BACKUP"
fi

mkdir -p "$(dirname "$LIVE_CONFIG")"
cp "$RENDERED" "$LIVE_CONFIG"
echo "Deployed $TEMPLATE -> $LIVE_CONFIG"

if ! zeroclaw status >/dev/null 2>&1; then
	echo "WARNING: zeroclaw status reports a problem with the new config." >&2
	zeroclaw status 2>&1 | head -20 >&2
	exit 1
fi
echo "Config validates."

if [[ "$MODE" == "with-cron" ]]; then
	SCAN="$MONOREPO_ROOT/scripts/run_trading_bot_rehearsal.sh"
	echo
	echo "Applying the daily scan job (see zeroclaw/cron/trading-bot-daily-scan.md)"
	zeroclaw cron add '35 9 * * 1-5' "$SCAN" --agent tradingbot --tz America/Detroit
fi

echo
echo "Restart the daemon to pick up config changes: zeroclaw service restart"
