# Scripts

This directory is reserved for repository automation scripts.

Examples:
- setup scripts
- validation scripts
- migration helpers
- packaging utilities

## Current Scripts

Updated 2026-07-26. Eight scripts were missing from this list, including all
three that are now on a schedule.

**Scheduled — these run unattended.** See
`zeroclaw/cron/trading-bot-daily-scan.md`.

- `run_trading_bot_daily.sh` — **the scheduled daily flow (09:45 weekdays)**: runs the scan *with paper-trade execution* and reports the outcome to Telegram. Failures report themselves and exit non-zero. `--dry-run` scans without executing or sending
- `run_trading_bot_log_maintenance.sh` — `rotate`, or `backup [dest]` (10:15 weekdays); with no destination it resolves `TRADING_BOT_BACKUP_DEST` from `.env`
- `run_trading_bot_watchdog.sh` — staleness watchdog (11:00 weekdays); counts missed *trading weekdays* since the last scan

**Run and rehearse**

- `run_trading_bot.sh` — canonical staged app run command
- `run_trading_bot_rehearsal.sh` — full analysis path using local-only staged config and env files. Places no orders unless `--execute-paper-trades` is passed, which it forwards. Note `--rehearsal` is not a dry-run flag; it just enables every scan stage
- `run_trading_bot_tests.sh` — canonical staged test command
- `bootstrap_trading_bot.sh` — creates the app-local virtualenv and installs the staged app in editable mode

**Operator queries**

- `print_trading_bot_balance.sh` — prints cash, holdings, portfolio value, and buying power for the broker account
- `print_trading_bot_holdings.sh` — prints the per-position holdings breakdown for the broker account
- `print_trading_bot_operator_summary.sh` — prints the latest staged operator-facing summary from the JSONL runtime artifact
- `print_trading_bot_pending_orders.sh` — prints broker-backed pending orders for operator status checks
- `print_trading_bot_runtime_status.sh` — prints a concise staged runtime status using artifacts plus broker context when available
- `print_trading_bot_stock_info.sh` — prints current market snapshot information for a single ticker
- `print_trading_bot_supported_commands.sh` — prints the supported Telegram operator-command surface
- `run_trading_bot_telegram_command.sh` — routes a raw Telegram operator-command line to the correct repo-managed wrapper
- `run_trading_bot_operator_poller.sh` — deterministic `/bot` command poller, deny-by-default, no agent in the path
- `install_operator_poller_service.sh` — installs the poller as a user service

**Analysis and reporting**

- `run_trading_bot_reconciliation.sh` — read-only; compares the bot's order record against Alpaca, computes FIFO realised P/L and the consecutive-loss run. Places no orders
- `run_trading_bot_read_model.sh` — `rebuild`, `metrics`, or `query` against the derived SQLite projection of `trades.jsonl`
- `build_executive_summary.py` — generates the shareable executive-summary PDF. Needs `reportlab`, which is deliberately **not** in the app venv; see the module docstring, and refresh its `LIVE` figures before regenerating

**Deployment**

- `sync_zeroclaw_config.sh` — one-way deploy of the repo-managed ZeroClaw config to the live runtime, backing up the live config first. `--check` verifies they match; `--with-cron` also applies the daily scan job

## Python Resolution Order

The staged wrappers resolve Python in this order:

1. `PYTHON_BIN` environment override
2. app-local virtualenv at `apps/trading-bot/.venv`
3. otherwise fail fast with a bootstrap instruction

The wrappers are intentionally self-contained and no longer fall back to the legacy repo virtualenv.

## Rule

Harness-facing staged commands should prefer these wrapper scripts over raw deep-path Python commands.

For Telegram operator commands specifically, prefer `/bot <subcommand>` and have it call `run_trading_bot_telegram_command.sh` as the single routing entrypoint instead of trying to execute tokens like `bot list` or `/List` directly in the shell.

The routed operator surface is: `/bot list`, `/bot summary`, `/bot pending`, `/bot status`, `/bot balance`, `/bot holdings`, and `/bot info <TICKER>`, plus plain-text and capitalised aliases. Verify with `print_trading_bot_supported_commands.sh`, which is the authority.

`/bot sync` and `/bot restart` were **removed** in commit 98f51da and are no longer routed; this list named them until 2026-07-26.
