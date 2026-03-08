# Operations Runbook (Rebuild Staging)
*Last updated: March 8, 2026*

## Purpose

This document records the system architecture and operational ownership model for the rebuild effort.

It is intentionally split between:
- **confirmed facts** — directly evidenced in this repository
- **inferred facts** — plausible from docs/logs/code but not externally verified
- **unknowns** — items that require direct inspection on the Mac Mini or inside the OpenClaw environment

## Architecture Boundary

### OpenClaw runtime layer
**Role:** primary runtime and orchestration layer

Expected responsibilities:
- Telegram interface
- command routing
- scheduled execution
- agent prompt/policy files
- confirmation boundaries for sensitive actions

**Status:** confirmed by live audit

Verified responsibilities:
- OpenClaw runs as launchd service `ai.openclaw.gateway`
- OpenClaw cron owns the scheduled trading scan
- OpenClaw workspace files exist and contain trading-bot operational instructions
- OpenClaw delivers cron summaries to Telegram

### Trading engine layer
**Role:** executable trading logic component

Confirmed responsibilities from this repo:
- run a daily trading cycle via [../main.py](../main.py)
- perform prefiltering via [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- perform Claude-based trade decisions via [../agents/trader_agent.py](../agents/trader_agent.py)
- fetch market data and indicators via [../tools/data_tools.py](../tools/data_tools.py)
- perform Alpaca paper trading via [../tools/alpaca_tools.py](../tools/alpaca_tools.py)
- append trade/event logs via [../logs/trades.log](../logs/trades.log)

### Mac Mini operations layer
**Role:** host environment

Expected responsibilities:
- run Python environment and dependencies
- run local Ollama service
- run OpenClaw background service
- store secrets and agent config files
- own scheduler/service management

**Status:** confirmed in part by live audit

## Confirmed Facts

### Repository/runtime facts
- A local Python virtual environment exists in `.venv/`
- This repo has executable Python code for a trading workflow
- That code has produced log output in [../logs/trades.log](../logs/trades.log)
- Alpaca trading client is configured for paper trading in [../tools/alpaca_tools.py](../tools/alpaca_tools.py)
- Ollama is expected at `http://localhost:11434/api/generate` in [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- Anthropic is called directly from [../agents/trader_agent.py](../agents/trader_agent.py)

### Live host facts
- macOS version confirmed: `26.3` (`25D125`)
- Python confirmed: `/opt/homebrew/bin/python3` → `3.14.3`
- Node confirmed: `/opt/homebrew/opt/node@22/bin/node` → `22.22.0`
- Homebrew confirmed: `5.0.16`
- Ollama confirmed: `/opt/homebrew/bin/ollama` → `0.17.5`
- Installed Ollama model confirmed: `qwen2.5:7b`
- OpenClaw confirmed: `/opt/homebrew/bin/openclaw` → `2026.3.1`
- Root `.env` exists in the repo; `config/.env` does not

### Live OpenClaw facts
- Main config exists at `~/.openclaw/openclaw.json`
- Auth profile exists at `~/.openclaw/agents/main/agent/auth-profiles.json`
- Cron config exists at `~/.openclaw/cron/jobs.json`
- Workspace exists at `~/.openclaw/workspace/`
- Workspace files include `AGENTS.md`, `BOOTSTRAP.md`, `HEARTBEAT.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, and `USER.md`
- Telegram channel is enabled in OpenClaw config

### Live scheduler facts
- The daily scan is scheduled by OpenClaw cron, not system crontab
- Confirmed job id: `trading-bot-daily-scan`
- Confirmed schedule: `35 9 * * 1-5`
- Confirmed timezone: `America/Detroit`
- Confirmed payload runs the repo directly with `cd ~/trading-bot && source .venv/bin/activate && python main.py`
- Confirmed cron post-step reads `~/trading-bot/logs/trades.log` and sends a Telegram summary

### Current code ownership inside repo
- [../main.py](../main.py) orchestrates the high-level run
- [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py) owns prefilter logic
- [../agents/trader_agent.py](../agents/trader_agent.py) owns trader decision calls and trade logging
- [../tools/alpaca_tools.py](../tools/alpaca_tools.py) owns broker access wrappers
- [../tools/data_tools.py](../tools/data_tools.py) owns market-data and indicator logic

## Inferred Facts

- Telegram interaction is routed through OpenClaw rather than custom Python bot code in this repo
- OpenClaw heartbeats likely monitor trade outcomes during market hours via `HEARTBEAT.md`
- OpenClaw workspace instructions are treated as the live operator-facing interface for this system

## Unknowns Requiring Audit

### OpenClaw
- exact Telegram pairing policy value and effective behavior
- exact gateway/session modes after safe review of `openclaw.json`
- whether any additional hidden skills/tools outside the workspace files affect trading-bot operation
- whether any other OpenClaw sessions or agents also interact with the trading bot

### Mac Mini
- actual startup behavior after reboot
- full secret sourcing rules for OpenClaw-triggered Python runs
- whether additional launch agents or login items participate in the trading workflow

### Trading runtime
- whether external OpenClaw workspace instructions supersede parts of the Python implementation or simply wrap them
- whether documented security guardrails are enforced outside this repo

## External File Inventory (Expected)

These are expected to exist outside the repo and should later be represented with sanitized templates.

### OpenClaw-related
- `~/.openclaw/openclaw.json`
- `~/.openclaw/agents/main/agent/auth-profiles.json`
- `~/.openclaw/cron/jobs.json`
- OpenClaw workspace files such as `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`, `AGENTS.md`, and `BOOTSTRAP.md`

### Project/runtime-related
- ignored live `.env` file(s)
- launchd entries for `ai.openclaw.gateway` and `homebrew.mxcl.ollama`
- Ollama service configuration

## Startup / Shutdown Ownership

### Likely startup flow
1. Mac Mini boots
2. OpenClaw service starts
3. Ollama service starts
4. OpenClaw can execute or schedule trading actions
5. trading engine performs scan/trade flow when invoked

**Status:** mostly confirmed, except reboot persistence behavior still needs explicit validation

### Likely emergency stop ownership
- OpenClaw service stop
- Ollama service stop
- any directly running Python trading process stop

**Status:** ownership confirmed at a high level; stop/restart commands still need live validation

## Operational Rules For Rebuild

- Treat OpenClaw as an external runtime dependency until audited
- Do not copy secret-bearing external files into the repo
- Store only sanitized structures and field descriptions in-repo
- Separate platform docs from app-specific strategy docs
- Mark each fact as confirmed, inferred, or unknown until verified

## Runtime Interpretation

The live architecture is now clearer:
- OpenClaw is the outer runtime and scheduler
- OpenClaw directly invokes the Python trading code in this repo
- OpenClaw workspace files provide operator-facing instructions and heartbeat behavior around the repo
- Therefore, the current system is a **hybrid architecture**, not “OpenClaw only” and not “repo only”

## Next Action

Create sanitized external-config templates for the discovered OpenClaw files and update the rebuild plan so the future monorepo treats OpenClaw workspace assets as first-class managed artifacts.
