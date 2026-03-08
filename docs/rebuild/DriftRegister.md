# Drift Register
*Last updated: March 8, 2026*

## Purpose

This file tracks the differences between:
- current code in this repo
- current documentation in this repo
- assumed live OpenClaw/Mac Mini runtime behavior

The goal is to prevent undocumented assumptions from leaking into the rebuild.

## Severity Guide

- **High** — affects architecture, runtime ownership, safety, or cutover confidence
- **Medium** — affects maintainability or configuration clarity
- **Low** — wording, naming, or cleanup issue

## Known Drift Items

### 1. OpenClaw ownership is documented, but runtime config is not present
- **Severity:** High
- **Code reality:** this repo contains direct Python logic for trading flow and direct Anthropic calls
- **Docs reality:** OpenClaw is described as the orchestration platform handling Telegram and Claude connectivity
- **Audit update:** live audit confirmed OpenClaw is installed and directly schedules `cd ~/trading-bot && source .venv/bin/activate && python main.py`
- **Gap:** runtime assets are real, external, and operationally important, but still not captured in-repo
- **References:** [../TradingBotPlan.md](../TradingBotPlan.md), [../Security.md](../Security.md), [../agents/trader_agent.py](../agents/trader_agent.py)

### 2. Python code is clearly executable, but docs imply a broader platform than the repo shows
- **Severity:** High
- **Code reality:** [../main.py](../main.py) and related modules implement a real scan/decision flow
- **Evidence:** log entries in [../logs/trades.log](../logs/trades.log)
- **Audit update:** OpenClaw cron and workspace files confirm the repo is part of the live runtime, not just dead/generated output
- **Gap:** repo still does not show the full production boundary even though it is directly executed by OpenClaw

### 3. `strategy.json` is not the real runtime authority
- **Severity:** High
- **Code reality:** strategy values are hardcoded in [../agents/trader_agent.py](../agents/trader_agent.py)
- **Docs reality:** [../config/strategy.json](../config/strategy.json) is described as the configuration authority
- **Gap:** config-driven behavior is not actually wired through runtime

### 4. Model selection drifts between config and code
- **Severity:** High
- **Code reality:** Claude model is hardcoded in [../agents/trader_agent.py](../agents/trader_agent.py); Ollama model is hardcoded in [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- **Docs/config reality:** model selections are described in [../config/strategy.json](../config/strategy.json) and [../TradingBotPlan.md](../TradingBotPlan.md)
- **Gap:** no single source of truth

### 5. Watchlist ownership drifts between config and code
- **Severity:** Medium
- **Code reality:** watchlist is hardcoded in [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- **Docs/config reality:** watchlist appears in [../config/strategy.json](../config/strategy.json)
- **Gap:** duplicated settings increase drift risk

### 6. Security controls are documented but not fully evident in code
- **Severity:** High
- **Docs reality:** [../Security.md](../Security.md) describes trade limits, Claude call limits, and config protections
- **Code reality:** visible runtime code does not clearly enforce all of these controls
- **Gap:** rebuild must treat these as requirements to implement, not facts already satisfied

### 7. SQLite persistence is documented but not implemented in visible code
- **Severity:** Medium
- **Docs reality:** [../TradingBotPlan.md](../TradingBotPlan.md) describes `database/trades.db`
- **Code reality:** no SQLite usage was identified in current Python files
- **Gap:** persistence design must be explicitly rebuilt

### 8. `.env` documentation and repo layout are inconsistent
- **Severity:** Medium
- **Docs reality:** docs describe config-managed secret locations in different ways
- **Repo reality:** a root-level `.env` exists and is ignored by git
- **Audit update:** OpenClaw workspace `TOOLS.md` still tells the agent secrets live at `~/trading-bot/config/.env`, but `config/.env` does not exist
- **Gap:** secrets contract must be clarified in the rebuild

### 9. Relative-path runtime assumptions are fragile
- **Severity:** Medium
- **Code reality:** logging uses relative path `logs/trades.log`; imports rely on repo-root behavior and `sys.path` patches
- **Audit update:** the live cron payload explicitly `cd`s into `~/trading-bot` before running `python main.py`, which hides these path assumptions in production
- **Gap:** monorepo rebuild must use explicit package imports and resolved runtime paths

### 10. OpenClaw workspace instructions drift from the repo implementation
- **Severity:** High
- **OpenClaw reality:** `~/.openclaw/workspace/TOOLS.md` and `HEARTBEAT.md` are active operational guidance for the live agent
- **Drift examples:**
	- references `~/trading-bot/config/.env`, which does not exist
	- references `~/trading-bot/database/trades.db`, which is documented but not implemented in visible code
	- uses `asyncio.run(...)` around functions that are currently synchronous in the repo
	- tells the operator to check `crontab -l`, but scheduling is actually owned by OpenClaw cron
- **Gap:** the live agent instructions and the repo code/docs are not aligned

### 11. Scheduler ownership is misdescribed in operator guidance
- **Severity:** Medium
- **Docs/workspace reality:** some instructions imply system cron is relevant
- **Audit reality:** `crontab -l` is empty; scheduling is defined in `~/.openclaw/cron/jobs.json`
- **Gap:** rebuild docs and operational templates must treat OpenClaw cron as the actual scheduler of record

## Rebuild Handling Rules

For each drift item, decide one of the following during rebuild:
- **Preserve** — existing behavior is correct and should be kept
- **Rebuild** — current behavior is unsafe, unclear, or incomplete
- **Audit first** — external runtime must be checked before deciding

## Current Default Decisions

- OpenClaw ownership boundary — **Preserve and document**
- Trading engine proven behavior — **Preserve**
- Config system — **Rebuild**
- Guardrails — **Rebuild**
- Persistence layer — **Rebuild**
- Secrets contract — **Audit first**
- Scheduler ownership — **Preserve and document**

## Next Action

Use the live audit findings to update OpenClaw workspace templates and ensure the rebuild treats OpenClaw cron, workspace files, and repo-root execution as explicit parts of the current system contract.
