# Architecture Overview

## Current Status

As of March 10, 2026, the repository has moved beyond an initial scaffold.

The live trading-bot path is now a hybrid of:

1. **OpenClaw as the outer runtime**
	- scheduling
	- isolated session execution
	- Telegram delivery
	- operator workspace behavior files under `~/.openclaw/workspace/`
	- native `/bot` operator command registration from `~/.openclaw/workspace/.openclaw/extensions/`
2. **The monorepo-managed trading bot implementation**
	- wrapper-script based execution from `~/trading-bot/monorepo-staging/`
	- Python package under `apps/trading-bot/`
	- runtime artifacts under `runtime/trading-bot/`

Despite the folder name `monorepo-staging`, this path is now the active managed runtime path for the scheduled trading job.

## Live Execution Contract

The live OpenClaw job `trading-bot-daily-scan` is scheduled for:

- `35 9 * * 1-5`
- timezone `America/Detroit`

Its current live payload is wrapper-based:

1. run `~/trading-bot/monorepo-staging/scripts/run_trading_bot_rehearsal.sh`
2. then run `~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh`
3. send that summary to Telegram via OpenClaw delivery

This means OpenClaw owns job orchestration and delivery, while the monorepo app owns trading-bot execution behavior and operator summary generation.

For Telegram operator commands, the live path is also wrapper-based:

1. the deployed native `/bot` workspace command receives the operator request
2. that command invokes `~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh`
3. the router dispatches the appropriate repo-managed wrapper and returns stdout to Telegram

For operator chat and general Telegram questions, the live OpenClaw default model is now `ollama/qwen2.5:7b`.

> **Deprecated (2026-07-25).** The statement above described the March 2026
> deployment and is no longer accurate. OpenClaw is not installed on the
> current host (no `~/.openclaw/`, no scheduled job), and `qwen2.5:7b` is not
> installed in Ollama — the only local model present is `gemma4:e4b-mlx`.
> The operator-chat model is deliberately *not* being repointed, because the
> agent-harness decision (OpenClaw vs. a lighter alternative) is still open;
> see the Phase 3 entry in `todo.md`. Note this is the operator-chat role,
> which is separate from the trading app's local-analysis model.

Claude remains part of the overall system, but only as an explicitly retained provider for trading-bot decision paths and possible escalation scenarios rather than the default operator conversation path.

## System Layers

### 1. OpenClaw runtime layer

Owned by live files under `~/.openclaw/` and staged sources under `openclaw/`.

Responsibilities:
- schedule and wake behavior
- isolated session targeting
- Telegram delivery target and mode
- workspace behavior and operator instructions
- native `/bot` command registration and deterministic operator command routing
- top-level runtime identity for the bot session
- default operator chat model routing via local Ollama/qwen *(deprecated
  2026-07-25: `qwen2.5:7b` is no longer installed; see the deprecation note
  in the operator-chat section above)*

Key staged sources:
- `openclaw/workspace/AGENTS.md`
- `openclaw/workspace/BOOTSTRAP.md`
- `openclaw/workspace/HEARTBEAT.md`
- `openclaw/workspace/IDENTITY.md`
- `openclaw/workspace/MIGRATION.md`
- `openclaw/workspace/SOUL.md`
- `openclaw/workspace/TOOLS.md`
- `openclaw/workspace/USER.md`
- `openclaw/workspace/.openclaw/extensions/bot-command/`
- `openclaw/cron/trading-bot-daily-scan.template.json`

### 2. Script and entrypoint layer

The script layer is the stable execution boundary between OpenClaw and the Python package.

Current canonical scripts:
- `scripts/bootstrap_trading_bot.sh`
- `scripts/print_trading_bot_balance.sh`
- `scripts/print_trading_bot_holdings.sh`
- `scripts/run_trading_bot.sh`
- `scripts/run_trading_bot_rehearsal.sh`
- `scripts/run_trading_bot_tests.sh`
- `scripts/print_trading_bot_operator_summary.sh`
- `scripts/print_trading_bot_pending_orders.sh`
- `scripts/print_trading_bot_runtime_status.sh`
- `scripts/print_trading_bot_stock_info.sh`
- `scripts/print_trading_bot_supported_commands.sh`
- `scripts/run_trading_bot_telegram_command.sh`
- `scripts/run_trading_bot_daily.sh` — scheduled flow: scan, then report
- `scripts/run_trading_bot_operator_poller.sh` — deterministic /bot poller
- `scripts/install_operator_poller_service.sh` — launchd install for the poller
- `scripts/run_trading_bot_reconciliation.sh` — scan log vs broker fills
- `scripts/run_trading_bot_read_model.sh` — derived SQLite projection
- `scripts/run_trading_bot_log_maintenance.sh` — rotation and off-machine backup
- `scripts/sync_zeroclaw_config.sh` — deploy repo-managed ZeroClaw config

Why this layer exists:
- avoids fragile deep-path Python commands in cron payloads
- centralizes Python resolution behavior
- centralizes env/config loading expectations
- provides a stable operator contract for post-run summaries

### 3. Trading bot app layer

The app lives in `apps/trading-bot/` and is the first monorepo app.

Primary app assets:
- `apps/trading-bot/pyproject.toml`
- `apps/trading-bot/.env.example`
- `apps/trading-bot/APP_CONTRACT.md`
- `apps/trading-bot/ENV_CONTRACT.md`
- `apps/trading-bot/config/strategy.example.json`
- local operator file: `apps/trading-bot/config/strategy.local.json`

Python package root:
- `apps/trading-bot/src/trading_bot/`

Current module boundaries:

#### Core app modules
- `trading_bot.cli` — package entrypoint
- `trading_bot.models` — typed data contracts
- `trading_bot.runtime_paths` — monorepo path resolution
- `trading_bot.config_loader` — strategy config loading
- `trading_bot.env_loader` — env loading
- `trading_bot.operator_commands` — operator-facing command formatting and command-line entrypoints
- `trading_bot.operator_summary` — operator-facing summary generation from runtime artifacts

#### Service layer
- `trading_bot.services.daily_scan` — main orchestration flow
- `trading_bot.services.decision_context` — decision payload shaping
- `trading_bot.services.guardrails` — guardrail evaluation
- `trading_bot.services.safety` — runtime safety semantics
- `trading_bot.services.trade_execution` — order-execution coordination

#### Integration layer
- `trading_bot.integrations.market_data` — Alpaca market data and indicator snapshots
- `trading_bot.integrations.prefilter` — Ollama-based signal filtering
- `trading_bot.integrations.decision_model` — Claude decision adapter
- `trading_bot.integrations.broker` — Alpaca broker adapter

#### Persistence layer
- `trading_bot.persistence.trade_log` — text and JSONL runtime logging
- `trading_bot.persistence.guardrail_state` — persisted daily counters and enforcement state

### 4. Runtime state layer

Runtime state is kept under `runtime/` and ignored from version control except for documentation and selected rehearsal artifacts.

Important active paths:
- `runtime/trading-bot/logs/trades.log`
- `runtime/trading-bot/logs/trades.jsonl`
- `runtime/trading-bot/guardrail-state.json`

Operational snapshots created during deployment work:
- `runtime/rollback-rehearsal/20260308-161833/`
- `runtime/cutover-rehearsal/20260308-chron-merge/`
- `runtime/cutover-execution/20260308-165207/`
- `runtime/go-live-execution/20260308-165905/`

### 5. Legacy repo layer

The legacy root-level implementation still exists and remains useful as historical reference and fallback context:
- `main.py`
- `agents/`
- `monitoring/`
- `tools/`
- `config/`

However, it is no longer the intended scheduled execution path for the live OpenClaw trading job.

## Runtime Flow

The current end-to-end execution model is:

1. OpenClaw cron triggers `trading-bot-daily-scan`
2. OpenClaw opens an isolated session using the deployed workspace files
3. The payload runs `scripts/run_trading_bot_rehearsal.sh`
4. The wrapper resolves Python and local config/env inputs
5. `trading_bot.cli` enters the app runtime
6. `trading_bot.services.daily_scan` orchestrates:
	- config loading
	- account and positions lookup
	- market indicator snapshot collection
	- Ollama prefilter pass
	- Claude decision pass only when triggered symbols exist
	- guardrail evaluation
	- execution-policy checks
	- trade logging and summary persistence
7. OpenClaw then runs `scripts/print_trading_bot_operator_summary.sh`
8. The generated operator summary is delivered to Telegram

The current operator-command model is:

1. Telegram sends an exact operator command such as `/bot summary` or `/bot holdings`
2. OpenClaw resolves that request through the deployed native `/bot` workspace command
3. the native command invokes `scripts/run_trading_bot_telegram_command.sh`
4. the router normalizes the command and dispatches the correct wrapper
5. the wrapper calls `trading_bot.operator_commands` or the relevant operational helper script
6. wrapper stdout is returned to Telegram without freeform reinterpretation

## Safety Model

The current live path is intentionally conservative.

Safety characteristics:
- safe mode semantics remain explicit in operator output
- Claude calls are guarded by daily counters
- trade count and position limits are enforced
- execution policy is mediated by guardrail checks
- exact Telegram operator commands are routed deterministically rather than interpreted as open-ended chat prompts
- operator messaging is generated from structured summary artifacts rather than improvised from raw logs

This architecture was chosen to preserve proven behavior while reducing ambiguity during operations.

## Repository Layout Summary

### OpenClaw-facing assets
- `openclaw/`

### App implementation
- `apps/trading-bot/`

### Shared code staging area
- `packages/`

### Runtime state and deployment artifacts
- `runtime/`

### Operator and automation scripts
- `scripts/`

### Planning and migration docs
- `docs/`

## Design Rule

Model the system as a real hybrid runtime:

- OpenClaw is the operator-facing orchestrator
- the monorepo trading-bot package is the execution engine
- wrapper scripts are the stable integration seam
- runtime artifacts are first-class operational outputs

Do not collapse these concerns back into a single-script mental model.
