# Rebuild Documentation Index
*Last updated: March 8, 2026*

## Purpose

This folder is the temporary source of truth for rebuilding the trading bot into a new monorepo while preserving what is currently known about the live system.

The current repository contains useful executable trading logic and evidence of runtime behavior, but it does **not** contain the full OpenClaw runtime configuration. Because of that, the rebuild effort must track three layers separately:

1. **OpenClaw runtime layer** — orchestration, Telegram interface, scheduling, and agent policy
2. **Trading engine layer** — Python trading workflow, broker integration, indicator logic, and decision flow
3. **Mac Mini operations layer** — installed software, services, secrets locations, launch behavior, and recovery procedures

## Current Rebuild Position

### Approved direction
- Rebuild into a **new monorepo**, not by expanding this repo in place
- Keep **OpenClaw as the first-class runtime/orchestrator**
- Treat this repository as a **reference implementation and evidence source**
- Preserve the current bot identity, paper-trading behavior, and schedule timing during cutover
- Use a **big-bang replace** only after the new system is validated

### What is already known
- Python trading logic in this repo has run and produced real log output in [logs/trades.log](../logs/trades.log)
- OpenClaw is documented as the outer platform, but its actual configuration is external to this repo
- Current docs and current code drift in several places and cannot be treated as one authoritative source
- Initial host audit confirms OpenClaw is installed and directly schedules this repo with `cd ~/trading-bot && source .venv/bin/activate && python main.py`
- Initial host audit confirms the live OpenClaw workspace exists under `~/.openclaw/workspace/` with `SOUL.md`, `TOOLS.md`, and `HEARTBEAT.md`
- Initial host audit confirms Ollama is installed locally and running with `qwen2.5:7b`
- Initial non-live monorepo scaffold created at [../../monorepo-staging/README.md](../../monorepo-staging/README.md)
- Initial trading app contract and Python package skeleton created at [../../monorepo-staging/apps/trading-bot/APP_CONTRACT.md](../../monorepo-staging/apps/trading-bot/APP_CONTRACT.md)
- Initial market-data and indicator adapter ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/market_data.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/market_data.py)
- Initial Ollama prefilter adapter ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/prefilter.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/prefilter.py)
- Initial Claude decision adapter ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/decision_model.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/decision_model.py)
- Initial Alpaca broker adapter ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/broker.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/integrations/broker.py)
- Initial runtime logging helper ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/persistence/trade_log.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/persistence/trade_log.py)
- Initial guardrail state and enforcement layer ported into [../../monorepo-staging/apps/trading-bot/src/trading_bot/services/guardrails.py](../../monorepo-staging/apps/trading-bot/src/trading_bot/services/guardrails.py)
- Initial staged unittest coverage added under [../../monorepo-staging/apps/trading-bot/tests/README.md](../../monorepo-staging/apps/trading-bot/tests/README.md)
- Initial staged OpenClaw runtime wiring added under [../../monorepo-staging/openclaw/README.md](../../monorepo-staging/openclaw/README.md)

## Document Map

- [RebuildPlan.md](RebuildPlan.md) — approved rebuild strategy, phases, cutover rules, and preserved behaviors
- [Operations.md](Operations.md) — architecture boundaries, runtime ownership, external file locations, startup/shutdown responsibilities
- [MachineAudit.md](MachineAudit.md) — confirmed facts, inferred facts, unknowns, and on-host verification checklist
- [DriftRegister.md](DriftRegister.md) — gaps and contradictions between code, docs, and assumed runtime behavior
- [external-config/README.md](external-config/README.md) — notes for sanitized templates of external OpenClaw/macOS assets
- [../../monorepo-staging/README.md](../../monorepo-staging/README.md) — staged future monorepo structure

## Source Evidence Inside This Repo

Primary evidence used for this rebuild set:
- [main.py](../main.py)
- [agents/trader_agent.py](../agents/trader_agent.py)
- [monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- [tools/alpaca_tools.py](../tools/alpaca_tools.py)
- [tools/data_tools.py](../tools/data_tools.py)
- [config/strategy.json](../config/strategy.json)
- [logs/trades.log](../logs/trades.log)
- [docs/TradingBotPlan.md](../TradingBotPlan.md)
- [docs/Security.md](../Security.md)

## Legacy Docs

These existing documents remain useful as reference material but should not be treated as the sole source of truth for the rebuild:
- [../TradingBotPlan.md](../TradingBotPlan.md)
- [../Security.md](../Security.md)

## Immediate Next Step

Use the staged monorepo to begin Phase 2 of the rebuild:
1. define the first real app contract inside [../../monorepo-staging/apps/trading-bot/README.md](../../monorepo-staging/apps/trading-bot/README.md)
2. promote verified OpenClaw runtime artifacts into the staged `openclaw/` area
3. decide what code should be ported first from the current repo into the staged app package
4. create the first monorepo-native configuration and entrypoint conventions

## Status

- Rebuild documentation staging area created
- Strategy selected: hybrid rebuild with OpenClaw-first architecture
- Initial external runtime audit completed
- Initial non-live monorepo scaffold created
- Initial trading-bot app contract and package skeleton created
- Initial monorepo-native market-data adapter created
- Initial monorepo-native prefilter adapter created
- Initial monorepo-native decision-model adapter created
- Initial monorepo-native broker adapter created
- Initial monorepo-native runtime logging helper created
- Initial monorepo-native guardrail enforcement created
- Initial staged guardrail tests passing
- Initial monorepo-native OpenClaw workspace and cron templates created
