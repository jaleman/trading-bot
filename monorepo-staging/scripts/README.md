# Scripts

This directory is reserved for repository automation scripts.

Examples:
- setup scripts
- validation scripts
- migration helpers
- packaging utilities

## Current Scripts

- `bootstrap_trading_bot.sh` — creates the app-local virtualenv and installs the staged app in editable mode
- `print_trading_bot_balance.sh` — prints cash, holdings, portfolio value, and buying power for the broker account
- `print_trading_bot_holdings.sh` — prints the per-position holdings breakdown for the broker account
- `print_trading_bot_operator_summary.sh` — prints the latest staged operator-facing summary from the JSONL runtime artifact
- `print_trading_bot_pending_orders.sh` — prints broker-backed pending orders for operator status checks
- `print_trading_bot_runtime_status.sh` — prints a concise staged runtime status using artifacts plus broker context when available
- `print_trading_bot_stock_info.sh` — prints current market snapshot information for a single ticker
- `print_trading_bot_supported_commands.sh` — prints the supported Telegram/OpenClaw command surface
- `run_trading_bot_telegram_command.sh` — routes a raw Telegram operator-command line to the correct repo-managed wrapper
- `run_trading_bot_rehearsal.sh` — canonical supervised rehearsal command using local-only staged config and env files
- `run_trading_bot.sh` — canonical staged app run command
- `run_trading_bot_tests.sh` — canonical staged test command

## Python Resolution Order

The staged wrappers resolve Python in this order:

1. `PYTHON_BIN` environment override
2. app-local virtualenv at `apps/trading-bot/.venv`
3. otherwise fail fast with a bootstrap instruction

The wrappers are intentionally self-contained and no longer fall back to the legacy repo virtualenv.

## Rule

OpenClaw-facing staged commands should prefer these wrapper scripts over raw deep-path Python commands.

For Telegram operator commands specifically, prefer the native `/bot <subcommand>` workspace command and have it call `run_trading_bot_telegram_command.sh` as the single routing entrypoint instead of trying to execute tokens like `bot list` or `/List` directly in the shell.

The routed operator surface is: `/bot list`, `/bot summary`, `/bot pending`, `/bot status`, `/bot balance`, `/bot holdings`, `/bot info <TICKER>`, `/bot sync`, and `/bot restart`.

## OpenClaw Operational Overrides
