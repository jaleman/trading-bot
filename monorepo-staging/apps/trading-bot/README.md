# Trading Bot App

This directory contains the monorepo-managed Python trading engine used by the live OpenClaw scheduled path.

## Start Here

- [../../README.md](../../README.md) — current repo status, phase, and canonical commands
- [APP_CONTRACT.md](APP_CONTRACT.md) — app ownership and runtime contract
- [ENV_CONTRACT.md](ENV_CONTRACT.md) — env/config contract for the wrapper-based runtime
- [REFACTOR_PLAN.md](REFACTOR_PLAN.md) — forward-looking design work and remaining structural cleanup

## Scope

This app owns:

- trading configuration loading
- runtime path resolution
- deterministic strategy evaluation
- local analysis and optional Claude escalation
- broker integration and guarded paper-trade execution
- structured runtime artifacts, summaries, and tests

OpenClaw owns scheduling, Telegram delivery, workspace behavior files, and top-level operator orchestration.

## Current Position

The app is no longer just a scaffold.

- it is part of the active live scheduled path under `monorepo-staging/`
- wrapper scripts are the supported execution boundary
- paper-trade execution has already been exercised successfully under guardrail enforcement
- live-capital trading is still out of scope pending a separate approval gate

## Key Files

- [pyproject.toml](pyproject.toml) — package metadata and dependencies
- [.env.example](.env.example) — local env template
- [config/strategy.example.json](config/strategy.example.json) — tracked strategy template
- [src/trading_bot](src/trading_bot) — package source
- [tests](tests) — staged unittest coverage

## Quickstart

1. Bootstrap the app environment with [../../scripts/bootstrap_trading_bot.sh](../../scripts/bootstrap_trading_bot.sh)
2. Create `.env` from [.env.example](.env.example)
3. Create `config/strategy.local.json` from [config/strategy.example.json](config/strategy.example.json)
4. Run the supervised wrapper with [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh)

The preferred local runtime files are:

- `apps/trading-bot/.env`
- `apps/trading-bot/config/strategy.local.json`

## Canonical Commands

- [../../scripts/bootstrap_trading_bot.sh](../../scripts/bootstrap_trading_bot.sh) — create `.venv/` and install the package in editable mode
- [../../scripts/run_trading_bot.sh](../../scripts/run_trading_bot.sh) — canonical wrapper for direct app execution
- [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh) — validated wrapper used by the live scheduled job
- [../../scripts/print_trading_bot_operator_summary.sh](../../scripts/print_trading_bot_operator_summary.sh) — print the latest operator summary from runtime artifacts
- [../../scripts/run_trading_bot_tests.sh](../../scripts/run_trading_bot_tests.sh) — run the staged unittest suite

## CLI Entry Point

The package entry point is [src/trading_bot/cli.py](src/trading_bot/cli.py).

Primary flags:

- `--config`
- `--env-file`
- `--include-market-data`
- `--include-local-analysis`
- `--include-claude-review`
- `--include-broker-context`
- `--execute-paper-trades`
- `--rehearsal`
- `--write-logs` / `--no-write-logs`

For deeper behavior and module ownership, use [APP_CONTRACT.md](APP_CONTRACT.md) rather than expanding this README into a second contract document.
