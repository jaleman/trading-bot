# Scripts

This directory is reserved for repository automation scripts.

Examples:
- setup scripts
- validation scripts
- migration helpers
- packaging utilities

## Current Scripts

- `bootstrap_trading_bot.sh` — creates the app-local virtualenv and installs the staged app in editable mode
- `merge_openclaw_trading_job.py` — safely replaces only the trading-bot job inside an OpenClaw `jobs.json` file
- `prepare_openclaw_cutover_jobs.sh` — builds a staged candidate `jobs.json` for cutover review without modifying the live file
- `print_trading_bot_operator_summary.sh` — prints the latest staged operator-facing summary from the JSONL runtime artifact
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
