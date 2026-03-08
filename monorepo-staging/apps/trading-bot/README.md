# Trading Bot App

This is the future home of the trading bot inside the monorepo.

## Current App Contract

See [APP_CONTRACT.md](APP_CONTRACT.md) for the first defined boundary for this app.
See [ENV_CONTRACT.md](ENV_CONTRACT.md) for the staged env/config contract.

## Scope

This app should eventually contain:
- the trading engine code
- app-specific config
- app-specific docs
- tests

## Current Live Reference

The legacy implementation still exists at the current repo root:
- `~/trading-bot/main.py`
- `~/trading-bot/agents/`
- `~/trading-bot/monitoring/`
- `~/trading-bot/tools/`

Those files are now historical reference material, not the intended runtime dependency for the monorepo-managed app.

## Rebuild Goal

Rebuild the trading engine cleanly here, while preserving the proven behavior:
- prefilter first
- paid LLM only on triggered signals
- Alpaca paper trading
- structured trade logging

## Current Runtime Package

- package metadata: [pyproject.toml](pyproject.toml)
- example env file: [.env.example](.env.example)
- example config file: [config/strategy.example.json](config/strategy.example.json)
- package root: [src/trading_bot](src/trading_bot)
- intended local virtualenv path: `.venv/`

This app is now being treated as a **staged production candidate**, not just a scaffold.

## Local Setup Direction

The preferred setup path for this staged app is via [../../scripts/bootstrap_trading_bot.sh](../../scripts/bootstrap_trading_bot.sh), which creates `.venv/` locally inside this app and installs the package in editable mode.

For supervised rehearsal work:
- create `.env` from [.env.example](.env.example)
- create `config/strategy.local.json` from [config/strategy.example.json](config/strategy.example.json)
- keep `safe_mode` enabled until cutover approval exists
- run [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh)

## CLI Reference

### Python entrypoint

The app entrypoint is `trading_bot.cli` in [src/trading_bot/cli.py](src/trading_bot/cli.py).

It runs the staged scan orchestration and supports these primary flags:

- `--config` — path to the strategy config file
- `--env-file` — path to the env file
- `--include-market-data` — fetch indicator snapshots
- `--include-prefilter` — run the Ollama prefilter layer
- `--include-decisions` — run the Claude decision layer
- `--include-broker-context` — fetch account and position context
- `--execute-paper-trades` — allow paper-trade execution, still subject to guardrails
- `--rehearsal` — turn on the supervised rehearsal path
- `--write-logs` / `--no-write-logs` — force or suppress runtime log writes for a single invocation

### Wrapper commands

- [../../scripts/run_trading_bot.sh](../../scripts/run_trading_bot.sh)
	- canonical wrapper for running `trading_bot.cli`
	- resolves Python from app-local `.venv` or an explicit `PYTHON_BIN` override
	- fails fast if the app-local environment has not been bootstrapped

- [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh)
	- validates that local `.env` and `config/strategy.local.json` exist
	- runs the app with `--rehearsal`
	- this is the current live scheduled wrapper path

- [../../scripts/print_trading_bot_operator_summary.sh](../../scripts/print_trading_bot_operator_summary.sh)
	- prints the latest operator-facing summary from structured runtime artifacts
	- intended for post-run Telegram delivery through OpenClaw

- [../../scripts/run_trading_bot_tests.sh](../../scripts/run_trading_bot_tests.sh)
	- runs the staged unittest suite

- [../../scripts/bootstrap_trading_bot.sh](../../scripts/bootstrap_trading_bot.sh)
	- creates the app-local virtualenv and installs the package in editable mode

### OpenClaw job helpers

- [../../scripts/prepare_openclaw_cutover_jobs.sh](../../scripts/prepare_openclaw_cutover_jobs.sh)
	- creates a candidate merged OpenClaw `jobs.json` for review

- [../../scripts/merge_openclaw_trading_job.py](../../scripts/merge_openclaw_trading_job.py)
	- safely replaces only the `trading-bot-daily-scan` job definition in an OpenClaw jobs file

## Telegram Operator Examples

Telegram is currently treated as a plain-language operator interface rather than a slash-command interface.

Useful operator requests include:

- `Run a scan now`
	- runs the live wrapper flow through [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh)

- `Show the latest trading bot summary`
	- prints the latest operator-facing summary via [../../scripts/print_trading_bot_operator_summary.sh](../../scripts/print_trading_bot_operator_summary.sh)

- `Run the trading bot tests`
	- runs [../../scripts/run_trading_bot_tests.sh](../../scripts/run_trading_bot_tests.sh)

- `Show the current guardrail state`
	- reads the persisted runtime state from `runtime/trading-bot/guardrail-state.json`

- `Show the last 30 lines of the trading log`
	- reads the most recent lines from `runtime/trading-bot/logs/trades.log`

- `Bootstrap the trading bot app`
	- runs [../../scripts/bootstrap_trading_bot.sh](../../scripts/bootstrap_trading_bot.sh)
	- intended for setup or repair, not normal daily operation

- `Prepare a candidate OpenClaw jobs file`
	- runs [../../scripts/prepare_openclaw_cutover_jobs.sh](../../scripts/prepare_openclaw_cutover_jobs.sh)
	- intended for change management, not routine operation

You can also ask for behavior-oriented runs such as:

- `Run the trading bot with market data`
- `Run the trading bot with broker context`
- `Run the trading bot in rehearsal mode`
- `Run the trading bot without writing logs`

Sensitive configuration or trading-policy changes should still be treated as high-friction requests that require confirmation rather than immediate execution.

## Initial Implementation Modules

- `trading_bot.models` — typed contracts
- `trading_bot.runtime_paths` — path resolution
- `trading_bot.config_loader` — config loading
- `trading_bot.services.daily_scan` — staged production-candidate orchestration
- `trading_bot.integrations.market_data` — monorepo-native Alpaca market-data and indicator adapter
- `trading_bot.integrations.prefilter` — monorepo-native Ollama prefilter adapter
- `trading_bot.integrations.decision_model` — monorepo-native Claude decision adapter
- `trading_bot.integrations.broker` — monorepo-native Alpaca broker adapter
- `trading_bot.persistence.trade_log` — monorepo-native runtime logging helper
- `trading_bot.persistence.guardrail_state` — persisted daily counters for guardrail enforcement
- `trading_bot.services.guardrails` — execution guardrail evaluation
- `trading_bot.cli` — app entrypoint

## Current Ported Behavior

- configuration loading from `config/strategy.example.json`
- runtime path resolution for monorepo layout
- typed scan-summary contract
- Sonnet 4.6 is the only Claude model referenced by the staged app config; local monitoring stays on `qwen2.5:7b`
- safe market-data adapter ported from the current repo's indicator logic
- safe Ollama prefilter adapter ported from the current repo's signal-classification logic
- safe Claude decision adapter ported from the current repo's decision contract
- safe Alpaca broker adapter ported from the current repo's paper-trading helpers
- monorepo-native runtime log path and trade-log helper
- initial guardrail enforcement for Claude calls, trade count, position count, and execution policy
- initial unittest coverage for guardrails and staged scan blocking behavior

The market-data, prefilter, decision, broker, and logging layers now exist, and the staged app has been promoted to a production-candidate runtime contract. Safe mode remains the default protection until cutover approval exists.
