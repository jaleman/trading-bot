# Trading Bot App Contract
*Created March 8, 2026*

## Purpose

This document defines the first real contract for the rebuilt trading-bot app inside the staged monorepo.

It is the boundary between:
- the **OpenClaw runtime**, which invokes and supervises the app
- the **trading app**, which performs trading-domain work
- future **shared packages**, which should only exist after real reuse appears

## App Responsibilities

The trading-bot app owns:
- loading trading configuration
- resolving runtime paths
- fetching market data
- calculating indicators
- prefiltering candidate signals
- preparing trade decisions
- interacting with the broker layer
- recording structured run outcomes

## OpenClaw Responsibilities

OpenClaw owns:
- scheduling
- Telegram interaction
- agent behavior files
- operator-facing summaries
- confirmation boundaries for sensitive actions
- orchestration around when the app is called

## Preserved Behavior From Current System

The rebuilt app must preserve these behaviors from the live hybrid system:

1. **Signal gate before paid reasoning**
   - local prefilter first
   - paid model only when symbols are triggered

2. **Paper-trading broker flow**
   - account lookup
   - open-position lookup
   - paper order placement

3. **Indicator semantics**
   - 20-day moving average
   - 50-day moving average
   - RSI

4. **Observable run output**
   - each run should produce a structured summary that OpenClaw can summarize to the user

## Initial Runtime Contract

### Inputs
- strategy configuration file
- environment variables / secret references
- current runtime root for logs and state
- invocation context from OpenClaw or local CLI

### Outputs
- structured daily scan summary
- structured signal classification data
- structured trade decision data
- event log records

## Initial Module Boundaries

### `trading_bot.config_loader`
Loads and validates configuration.

### `trading_bot.runtime_paths`
Resolves app root, repo root, config paths, and runtime directories.

### `trading_bot.models`
Defines typed contracts for configuration and run outputs.

### `trading_bot.services.daily_scan`
Owns the application-level orchestration flow.

### `trading_bot.integrations.*`
Reserved for external-system adapters such as Alpaca, data providers, local model access, and decision-model access.

## Port Order

1. runtime path resolution
2. config loader
3. typed models/contracts
4. daily scan service
5. market-data adapter
6. local prefilter adapter
7. decision-model adapter
8. broker adapter
9. persistence / audit layer

## Current Status

- Contract established
- Package created and promoted to a staged production-candidate runtime
- Market-data and indicator adapter ported
- Ollama prefilter adapter ported
- Claude decision adapter ported
- Broker adapter ported
- Runtime logging helper ported
- Daily scan service can now load config, resolve runtime paths, and optionally fetch indicator snapshots, run the prefilter gate, request structured decisions, fetch broker context, and execute staged paper trades
- Initial guardrail enforcement added for Claude call limits, trade counts, position counts, and execution policy
- Initial unittest coverage added for core guardrail behavior
- Persistence design beyond runtime logs and daily guardrail counters is still pending

## Current Runtime Position

The staged app should now be treated as a **production-candidate runtime contract** for cutover planning.

That does **not** mean live production cutover has happened.
It means the staged runtime now reports itself as a production candidate while still preserving explicit safe-mode and staged-runtime boundaries.
