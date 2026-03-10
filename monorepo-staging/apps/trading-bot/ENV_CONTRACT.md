# Trading Bot Environment Contract
*Created March 8, 2026*

## Purpose

This document defines the staged environment and config contract for the monorepo trading-bot runtime.

It describes:
- which local files must exist
- which environment variables are required
- how config and env file resolution works
- what OpenClaw should assume during staged rehearsal and future cutover

## Required Local Files

### 1. Local env file
- path: `apps/trading-bot/.env`
- source template: [.env.example](.env.example)
- commit policy: **do not commit**

### 2. Local strategy file
- path: `apps/trading-bot/config/strategy.local.json`
- source template: [config/strategy.example.json](config/strategy.example.json)
- commit policy: **do not commit**

## Required Environment Variables

The staged runtime requires these variables when using real integrations:

- `ANTHROPIC_API_KEY`
- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

## Resolution Rules

### Environment resolution
The staged runtime resolves environment input in this order:

1. `--env-file <path>` passed to the CLI
2. default local file at `apps/trading-bot/.env` if present
3. already-existing process environment variables

### Strategy config resolution
The staged runtime resolves strategy config in this order:

1. `--config <path>` passed to the CLI
2. default local file at `apps/trading-bot/config/strategy.local.json` if present
3. fallback tracked file at [config/strategy.example.json](config/strategy.example.json)

## Canonical Runtime Commands

### Supervised rehearsal
Use:
- [../../scripts/run_trading_bot_rehearsal.sh](../../scripts/run_trading_bot_rehearsal.sh)

This wrapper requires both:
- `apps/trading-bot/.env`
- `apps/trading-bot/config/strategy.local.json`

### Generic staged runtime invocation
Use:
- [../../scripts/run_trading_bot.sh](../../scripts/run_trading_bot.sh)

This wrapper can still be driven explicitly with `--config` and `--env-file` overrides.

## Safe-Mode Contract

During staged rehearsal and pre-cutover validation:
- `safe_mode` should remain `true`
- `paper_trade_execution_enabled` should remain `false` unless explicitly testing a different migration step
- successful runs must still state that production cutover has not occurred

## OpenClaw Expectations

OpenClaw should assume:
- the staged runtime is a production candidate, not live production
- secrets are sourced from the staged app env file or inherited environment
- the Telegram destination remains owned by the live OpenClaw cron container file and is preserved during cron merge preparation

## Non-Goals

This document does **not**:
- store secrets
- authorize live deployment
- change the live OpenClaw runtime

## Current Status

- env contract documented
- staged rehearsal contract documented
- OpenClaw cutover to the monorepo runtime completed on March 8, 2026
- this contract now governs the live scheduled wrapper path used by OpenClaw
- paper-trade execution was exercised successfully on March 9, 2026 with guardrails passing
- live-capital deployment still requires a separate explicit approval gate
