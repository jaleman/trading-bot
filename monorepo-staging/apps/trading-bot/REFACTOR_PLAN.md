# Trading Bot Refactor Plan
*Created March 9, 2026*

## Purpose

This document defines the planned refactor of the staged trading-bot app from a small watchlist + model-driven signal classifier into a broader market-scanning engine with deterministic strategy enforcement, local-model analysis, and optional premium-model escalation.

The plan intentionally does **not** preserve the current model-first decision path as a compatibility target.

## Why This Refactor Exists

The current staged runtime has three structural problems:

1. explicit strategy rules are partly duplicated in model prompts instead of being enforced only in code
2. the fixed 12-symbol watchlist is too narrow for real target discovery
3. Claude is being used for work that deterministic code or a local model should handle more cheaply and more reliably

## Target Outcome

The refactored app should behave like this:

1. Python scans a broader tradable universe and computes technical features deterministically.
2. Python applies deterministic entry, exit, and risk rules from the strategy config.
3. Ollama/Qwen performs cheap higher-level analysis on a shortlisted candidate set.
4. Claude is optional and only used for ambiguous or high-impact portfolio-level decisions.
5. OpenClaw remains the orchestration, scheduling, approval, and operator-summary layer.

## Core Design Decisions

### Deterministic Rules Stay In Code

The following must be enforced in Python rather than delegated to a model prompt:

- universe screening filters
- entry eligibility
- exit eligibility
- position sizing
- max positions
- max trades per day
- safe mode / execution policy
- buy and sell execution validation

### Qwen Becomes The Primary Analysis Layer

The local model should not decide whether a simple threshold is true.

The local model should instead help with:

- ranking already-qualified candidates
- identifying cleaner versus noisier setups
- comparing candidates across sectors
- producing operator-facing summaries
- determining whether a run is routine or should be escalated

### Claude Becomes Optional Escalation

Claude should not remain in the default daily path unless it proves incremental value.

Claude should only be called for situations such as:

- multiple strong candidates competing for limited position slots
- conflicting buy versus hold versus sell scenarios across the portfolio
- elevated concentration risk
- disagreement between deterministic scoring and local-model ranking
- periodic portfolio review when higher-quality reasoning is worth the cost

### OpenClaw Stays Above The Trading Logic

OpenClaw should orchestrate when the app runs and how results are delivered, not own core numeric trade logic.

OpenClaw responsibilities remain:

- scheduling
- Telegram operator interaction
- approval boundaries
- exception routing
- morning / intraday / end-of-day summaries

## Role Of strategy.local.json

`config/strategy.local.json` becomes the single source of truth for trading policy.

It should define:

- universe settings
- deterministic signal thresholds
- exit logic
- portfolio and risk limits
- model routing policy
- execution mode flags

It should **not** contain:

- API secrets
- scheduling policy
- OpenClaw-specific behavior
- duplicated prompt prose
- runtime state such as trade counters or open positions

## Target Architecture

### 1. Universe Builder

Replace the fixed watchlist-first model with a configurable universe.

Initial target capabilities:

- named universe preset or explicit symbol list
- include and exclude symbols
- minimum liquidity filters
- maximum shortlist size

Initial practical universe size should likely be between 50 and 150 liquid names, not the full market.

### 2. Deterministic Scanner

For each symbol, compute features and eligibility using code.

Expected initial features:

- current price
- 20-day MA
- 50-day MA
- RSI
- recent returns
- volatility or ATR
- optional volume/liquidity measures

The scanner should produce:

- eligible entry candidates
- eligible exit candidates
- ranked deterministic scores
- explicit rejection reasons

### 3. Local Analysis Layer

Feed only the shortlisted candidates into Ollama/Qwen.

Expected outputs:

- ranked candidate list
- short thesis for each candidate
- setup quality notes
- confidence score or escalation recommendation
- operator summary text

### 4. Execution Firewall

Before any broker call, Python must validate the final execution intents.

The firewall should enforce:

- safe mode
- paper trading enabled
- max positions
- max trades per day
- max position size
- no buy without valid cash / buying power context
- no sell without an existing position
- no invalid or duplicate actions for the same symbol in the same run

### 5. Broker Execution

Execution must support both buys and sells.

The current buy-only execution path is not sufficient for a complete strategy because exit logic cannot be treated as real policy until sell execution exists.

## Proposed Module Changes

### Keep And Expand

- `src/trading_bot/config_loader.py`
- `src/trading_bot/models.py`
- `src/trading_bot/runtime_paths.py`
- `src/trading_bot/services/daily_scan.py`
- `src/trading_bot/services/guardrails.py`
- `src/trading_bot/integrations/market_data.py`
- `src/trading_bot/integrations/broker.py`

### Repurpose

- `src/trading_bot/integrations/prefilter.py`
  - stop using it as a rule-checking prefilter
  - repurpose it into local analysis / ranking / summary support, or replace it with a new integration module

- `src/trading_bot/integrations/decision_model.py`
  - stop using it as the default daily threshold evaluator
  - redesign it as an optional portfolio-review escalation client

### Add

- `src/trading_bot/services/universe.py`
  - builds the scan universe from config

- `src/trading_bot/services/strategy_engine.py`
  - deterministic entry / exit evaluation and scoring

- `src/trading_bot/services/model_router.py`
  - decides whether local-only analysis is sufficient or whether Claude escalation is warranted

- `src/trading_bot/services/execution_firewall.py`
  - validates final execution intents before broker calls

### Extend

- `src/trading_bot/services/trade_execution.py`
  - support validated buy and sell execution

## Config Refactor Direction

The strategy schema should move from a small fixed watchlist contract to a broader policy contract.

Representative sections:

- `universe`
- `entry`
- `exit`
- `risk`
- `execution_controls`
- `model_routing`
- `models`

Representative example fields:

- `universe.preset`
- `universe.include_symbols`
- `universe.exclude_symbols`
- `universe.shortlist_size`
- `entry.ma_crossover.short`
- `entry.ma_crossover.long`
- `entry.rsi_threshold`
- `entry.min_rsi`
- `entry.min_recent_return_5d`
- `entry.min_recent_return_20d`
- `entry.min_distance_to_ma_20_pct`
- `entry.min_distance_to_ma_50_pct`
- `risk.max_positions`
- `risk.max_trades_per_day`
- `risk.max_position_size_pct`
- `model_routing.local_analysis_enabled`
- `model_routing.claude_escalation_enabled`
- `model_routing.max_candidates_for_local_analysis`
- `model_routing.escalate_when_slots_remaining_lte`

## Refactor Phases

### Phase 1: Config And Contracts

Goal:
Define the new strategy schema and update typed models to match.

Deliverables:

- updated `strategy.example.json`
- updated local strategy contract
- updated `models.py`
- clear separation between strategy policy and runtime state

### Phase 2: Deterministic Strategy Engine

Goal:
Make code the owner of entry, exit, and scoring logic.

Deliverables:

- new deterministic strategy engine service
- deterministic candidate scoring
- explicit rejection reasons for non-qualifying symbols
- unit tests for entry and exit evaluation

### Phase 3: Broader Universe Scanning

Goal:
Replace the fixed 12-name scan with a configurable universe and shortlist pipeline.

Deliverables:

- universe builder service
- liquidity-aware symbol set handling
- shortlist generation
- CLI / summary support for broader scans

### Phase 4: Local Analysis Layer

Goal:
Promote Ollama/Qwen into a meaningful analysis role after deterministic screening.

Deliverables:

- local ranking / analysis integration
- structured analysis outputs
- escalation recommendation contract
- operator-summary improvements

### Phase 5: Execution Firewall And Sell Support

Goal:
Make execution complete and safe for both entry and exit actions.

Deliverables:

- explicit execution-intent validation
- buy and sell execution support
- no-action / blocked-action reasons in scan summary
- expanded guardrail and execution tests

### Phase 6: Optional Claude Escalation

Goal:
Reintroduce Claude only where stronger portfolio-level reasoning may materially improve outcomes.

Deliverables:

- redesigned escalation client
- explicit escalation policy in config
- structured escalation inputs and outputs
- tests covering no-escalation and escalation branches

### Phase 7: OpenClaw Job Realignment

Goal:
Align OpenClaw scheduling and summaries with the new engine lifecycle.

Deliverables:

- overnight scan job design
- pre-market refresh job design
- market-open execution-check job design
- updated operator-facing summaries

## Recommended Execution Order

Implement in this order:

1. config contract update
2. deterministic strategy engine
3. universe builder
4. local analysis layer
5. execution firewall and sell support
6. Claude escalation redesign
7. OpenClaw job and summary updates

This order keeps the new architecture coherent by building deterministic ownership first and model routing second.

## Testing Strategy

At minimum, add or update tests for:

- deterministic entry qualification
- deterministic exit qualification
- universe construction from config
- shortlist generation
- local analysis routing decisions
- execution blocking behavior
- sell execution behavior
- end-to-end daily scan summaries without Claude
- optional escalation paths when Claude is enabled

## First Implementation Slice

The first implementation slice should be:

1. redesign the config contract
2. add the deterministic strategy engine
3. wire `daily_scan` to use deterministic candidates as the primary decision source
4. keep local-model participation limited to summary and ranking until deterministic behavior is stable

This slice creates the foundation for the rest of the refactor without spending time polishing the old model-first flow.

## Explicit Non-Goals

Do not spend time on these until the core engine exists:

- preserving the current prompt wording
- maintaining exact behavior parity with the existing 12-symbol model-driven flow
- expanding Claude usage before local analysis and deterministic screening are working well
- broad live-trading enablement before sell-side execution and execution validation exist

## Success Criteria

The refactor should be considered successful when:

1. strategy policy lives only in config + deterministic Python logic
2. the app scans a broader configurable universe instead of a fixed tiny watchlist
3. Qwen/Ollama adds value through ranking and analysis rather than threshold checking
4. buy and sell actions are both supported through validated execution
5. Claude is optional, not structurally required for daily operation
6. OpenClaw cleanly supervises and summarizes the app without owning trading logic