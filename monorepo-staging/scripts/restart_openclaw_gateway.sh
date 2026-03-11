#!/usr/bin/env bash
set -euo pipefail

usage() {
	echo "Usage: $0 [--dry-run]" >&2
}

DRY_RUN=0
if [[ $# -gt 1 ]]; then
	usage
	exit 1
fi

if [[ $# -eq 1 ]]; then
	if [[ "$1" == "--dry-run" ]]; then
		DRY_RUN=1
	else
		usage
		exit 1
	fi
fi

if [[ -n "${OPENCLAW_GATEWAY_RESTART_CMD:-}" ]]; then
	RESTART_COMMAND="$OPENCLAW_GATEWAY_RESTART_CMD"
else
	if ! command -v openclaw >/dev/null 2>&1; then
		echo "Missing openclaw CLI in PATH. Set OPENCLAW_GATEWAY_RESTART_CMD to the correct restart command for this machine." >&2
		exit 1
	fi
	RESTART_COMMAND="openclaw gateway restart"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
	echo "Would run: $RESTART_COMMAND"
	exit 0
fi

sh -lc "$RESTART_COMMAND"
echo "OpenClaw gateway restart command completed."