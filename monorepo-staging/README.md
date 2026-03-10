# Monorepo Staging
*Created March 8, 2026*

This directory began as a safe staging scaffold for the future multi-agent monorepo.

It is now the active managed runtime path for the live trading-bot OpenClaw job, even though the folder name still contains `staging`.

## Current Status

- controlled cutover completed on March 8, 2026
- live trading job enabled on March 8, 2026
- OpenClaw now runs the trading bot through the wrapper flow in this directory
- paper-trade execution was exercised successfully on March 9, 2026 with guardrails passing
- the current live phase is post-cutover validation under the monorepo-managed runtime
- the legacy root repo remains available as historical reference and fallback context

## Current Phase

This repo is no longer just a staging scaffold in practice.

The active process state is:

1. cutover complete
2. live scheduled wrapper path active
3. paper-trade validation underway
4. live-capital approval still pending a separate gate

## Current Intent

This monorepo is organized around a hybrid architecture:

1. **OpenClaw runtime layer**
   - orchestration
   - Telegram interface
   - scheduling
   - workspace behavior files
2. **App layer**
   - trading bot as the first app
   - future agents/apps added alongside it
3. **Shared packages layer**
   - common libraries extracted only when reuse is real
4. **Runtime layer**
   - logs, databases, caches, deployment snapshots, and other ignored state

## Live Execution Reality

The current live scheduled path is:

- OpenClaw cron job `trading-bot-daily-scan`
- execution wrapper: [scripts/run_trading_bot_rehearsal.sh](scripts/run_trading_bot_rehearsal.sh)
- summary wrapper: [scripts/print_trading_bot_operator_summary.sh](scripts/print_trading_bot_operator_summary.sh)
- deployed OpenClaw workspace files under `~/.openclaw/workspace/`

Despite the wrapper name, this path is now the live scheduled job contract.
The latest runtime artifacts show that paper-trade execution has already been exercised successfully through this managed path.

The legacy root repo still contains the original implementation sources:

- `~/trading-bot/main.py`
- `~/trading-bot/agents/`
- `~/trading-bot/monitoring/`
- `~/trading-bot/tools/`

Those files remain useful reference material, but they are no longer the intended scheduled execution path or Python-environment dependency for the monorepo runtime.

## Important Safety Rule

Operational changes should continue to use the wrapper-script contract, guardrail-aware runtime flow, and documented OpenClaw assets rather than ad hoc deep-path commands.

Live-capital trading remains out of scope until a separate explicit approval gate is defined.

## Repository Layout

- [docs/README.md](docs/README.md) — monorepo docs hub
- [docs/Migration.md](docs/Migration.md) — staged cutover and rollback plan
- [docs/Architecture.md](docs/Architecture.md) — current architecture and live runtime flow
- [openclaw/README.md](openclaw/README.md) — OpenClaw-managed runtime assets
- [apps/trading-bot/README.md](apps/trading-bot/README.md) — first app boundary
- [packages/README.md](packages/README.md) — shared code staging area
- [runtime/README.md](runtime/README.md) — ignored runtime state conventions and deployment artifacts
- [scripts/README.md](scripts/README.md) — repo automation scripts

## Relationship To Rebuild Docs

The authoritative rebuild reasoning still lives in:

- [../docs/rebuild/README.md](../docs/rebuild/README.md)
- [../docs/rebuild/RebuildPlan.md](../docs/rebuild/RebuildPlan.md)
- [../docs/rebuild/Operations.md](../docs/rebuild/Operations.md)
- [../docs/rebuild/MachineAudit.md](../docs/rebuild/MachineAudit.md)
- [../docs/rebuild/DriftRegister.md](../docs/rebuild/DriftRegister.md)

This monorepo directory is the implemented result of that plan's first production handoff.

## Canonical Commands

- Bootstrap app env: [scripts/bootstrap_trading_bot.sh](scripts/bootstrap_trading_bot.sh)
- Print latest operator summary: [scripts/print_trading_bot_operator_summary.sh](scripts/print_trading_bot_operator_summary.sh)
- Run supervised rehearsal: [scripts/run_trading_bot_rehearsal.sh](scripts/run_trading_bot_rehearsal.sh)
- Run app directly: [scripts/run_trading_bot.sh](scripts/run_trading_bot.sh)
- Run tests: [scripts/run_trading_bot_tests.sh](scripts/run_trading_bot_tests.sh)

## Recommended Reading

- [docs/Architecture.md](docs/Architecture.md)
- [openclaw/FINAL_REVIEW.md](openclaw/FINAL_REVIEW.md)
- [openclaw/CUTOVER_RUNBOOK.md](openclaw/CUTOVER_RUNBOOK.md)
