# Trading Platform Rebuild Plan
*Last updated: March 8, 2026*

## Objective

Recreate the trading application inside a new monorepo that treats **OpenClaw as the primary runtime**, while rebuilding the Python trading engine as a clean internal component.

This repository is not being treated as the long-term platform root. Instead, it is the current reference source for:
- proven trading-engine behavior
- current code structure
- runtime log evidence
- known documentation drift

## Rebuild Posture

### Chosen approach
**Hybrid rebuild**

That means:
- rebuild the platform cleanly in a new monorepo
- port forward only the small set of behaviors that are proven and useful
- avoid in-place refactoring of the current repo as the main strategy

### Why not incremental refactor
- OpenClaw runtime/config is external to this repository
- docs and code diverge materially
- configuration authority is split across docs, JSON, and hardcoded constants
- current imports and relative paths are not a scalable base for a multi-agent platform

## System Model

The rebuilt system should clearly separate three layers:

### 1. OpenClaw runtime layer
Owns:
- orchestration
- Telegram interface
- schedule execution
- operator confirmation policy
- agent prompt/boundary files

### 2. Trading engine layer
Owns:
- market-data retrieval
- indicator computation
- signal prefilter logic
- decision preparation
- broker actions
- persistence and logging

### 3. Mac Mini operations layer
Owns:
- installed runtimes and services
- service startup and shutdown
- launch agents / cron / scheduler ownership
- secret storage locations
- incident recovery actions

## Proven Behaviors To Preserve

These are the minimum behaviors that should survive the rebuild.

### Behavior 1: prefilter before paid model call
Current flow in [../main.py](../main.py):
1. Run Ollama-based prefilter
2. Log watching/summary output
3. Only call Claude if symbols are triggered

This behavior is also visible in [../logs/trades.log](../logs/trades.log).

### Behavior 2: indicator calculations
Current logic in [../tools/data_tools.py](../tools/data_tools.py):
- fetch daily bars from Alpaca market data
- compute 20-day moving average
- compute 50-day moving average
- compute RSI

### Behavior 3: paper trading wrapper
Current logic in [../tools/alpaca_tools.py](../tools/alpaca_tools.py):
- get account balance
- get open positions
- place Alpaca paper orders
- fetch trade history

### Behavior 4: structured decision contract
Current expected decision format in [../agents/trader_agent.py](../agents/trader_agent.py):
- symbol
- action
- reason
- qty

### Behavior 5: trade/event logging
Current log behavior in [../agents/trader_agent.py](../agents/trader_agent.py) writes to `logs/trades.log`.

## What Should Be Rebuilt Cleanly

### Configuration system
Do not carry forward the current split authority between:
- [../config/strategy.json](../config/strategy.json)
- hardcoded strategy values in [../agents/trader_agent.py](../agents/trader_agent.py)
- hardcoded model/watchlist values in [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)

### Risk controls
Rebuild and actually enforce:
- daily trade limits
- daily Claude call limits
- position sizing checks
- stop loss behavior
- profit target behavior
- paper-to-live gate logic

### Persistence
Rebuild persistence intentionally instead of relying only on flat log appends.

### OpenClaw integration boundary
Document and manage the OpenClaw runtime assets as first-class external dependencies with sanitized in-repo references.

## Target Monorepo Concept

The future monorepo should include:
- shared top-level docs for platform operations
- an app folder for the trading capability
- a place for future agents/apps
- sanitized external-config references
- clear ownership boundaries between runtime and app code

## Phases

### Phase 1 — Baseline capture
- freeze current repo as evidence
- document plan, operations, audit, and drift
- audit live OpenClaw and Mac Mini environment

### Phase 2 — New monorepo scaffold
- create new repo structure
- add docs hub and runtime ownership docs
- define trading app boundary
- add config and external-config conventions

### Phase 3 — Clean trading engine rebuild
- rebuild config loading
- rebuild signal flow
- rebuild broker integration layer
- rebuild persistence/logging
- rebuild guardrails and testability

### Phase 4 — OpenClaw reintegration
- wire the rebuilt trading engine into OpenClaw
- recreate prompts/policies/templates
- preserve bot identity and schedule timing

### Phase 5 — Cutover
- validate paper-trading workflow
- validate scheduled execution
- validate OpenClaw command behavior
- perform big-bang replace only after acceptance checks pass

## Cutover Rules

The rebuild is not ready to replace the current setup until all of the following are true:
- OpenClaw external config has been audited and documented
- preserved behaviors are reproduced in the new system
- schedule timing is confirmed
- paper-trading workflow is confirmed
- guardrails are implemented, not just documented
- rollback steps are documented

## Known Blockers

- actual OpenClaw config is not in this repo
- actual Telegram pairing and policy state is not in this repo
- scheduler ownership is described in docs but not captured in repo artifacts
- some runtime claims in docs may be aspirational rather than verified

## Current Status

- strategy chosen
- rebuild docs created
- external runtime audit pending
- new monorepo pending
- no cutover work started

## Next Action

Populate [MachineAudit.md](MachineAudit.md) with real on-host findings from the Mac Mini and use those findings to refine [Operations.md](Operations.md).
