# Mac Mini / OpenClaw Machine Audit
*Last updated: March 8, 2026*

## Purpose

This document is the audit worksheet for reconstructing the real live environment on the Mac Mini.

It should be updated with:
- what is **confirmed**
- what is **inferred**
- what is still **unknown**
- what command, file, or observation was used as evidence

## Current Audit Status

**Status:** initial live audit completed on March 8, 2026

## Verified Host Findings

### Host baseline
- **macOS:** 26.3 (`BuildVersion 25D125`)
- **User:** `labanlaro`
- **Home:** `/Users/labanlaro`
- **Shell:** `/bin/zsh`

### Installed toolchain
- **Python:** `/opt/homebrew/bin/python3` → `Python 3.14.3`
- **Node:** `/opt/homebrew/opt/node@22/bin/node` → `v22.22.0`
- **Homebrew:** `/opt/homebrew/bin/brew` → `Homebrew 5.0.16`

### Ollama
- **Binary:** `/opt/homebrew/bin/ollama`
- **Version:** `0.17.5`
- **Installed model confirmed:** `qwen2.5:7b`
- **Service status:** running via Homebrew service
- **Launch label observed:** `homebrew.mxcl.ollama`

### OpenClaw
- **Binary:** `/opt/homebrew/bin/openclaw`
- **Version:** `2026.3.1`
- **Main config path confirmed:** `~/.openclaw/openclaw.json`
- **Auth profile path confirmed:** `~/.openclaw/agents/main/agent/auth-profiles.json`
- **Cron config path confirmed:** `~/.openclaw/cron/jobs.json`
- **Workspace path confirmed:** `~/.openclaw/workspace/`
- **Workspace files confirmed:** `AGENTS.md`, `BOOTSTRAP.md`, `HEARTBEAT.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md`
- **Launch label observed:** `ai.openclaw.gateway`

### Scheduler / execution path
- OpenClaw owns the daily trading schedule
- No system crontab entries were present
- Confirmed job in `~/.openclaw/cron/jobs.json`:
	- **job id:** `trading-bot-daily-scan`
	- **schedule:** `35 9 * * 1-5`
	- **timezone:** `America/Detroit`
	- **payload behavior:** changes into `~/trading-bot`, activates `.venv`, runs `python main.py`, then reads the bot log and sends a Telegram summary

### Telegram / channel state
- Telegram channel is enabled in `~/.openclaw/openclaw.json`
- `dmPolicy` exists in config, but the value was intentionally redacted during audit capture
- `~/.openclaw/telegram/` exists
- `update-offset-default.json` exists
- `paired-users.json` was **not** present at the audited path

### Current repo/runtime assumptions confirmed
- The live automation targets the repo root `~/trading-bot`
- Root `.env` exists in this repo
- `config/.env` does **not** exist in this repo
- `.gitignore` ignores `.env`, `.venv/`, `logs/`, and `database/`

## Confirmed From This Repo

- Dedicated Mac Mini deployment is described in [../TradingBotPlan.md](../TradingBotPlan.md)
- A local Python environment exists for this repo
- Alpaca paper trading is used in [../tools/alpaca_tools.py](../tools/alpaca_tools.py)
- Anthropic access is used in [../agents/trader_agent.py](../agents/trader_agent.py)
- Ollama localhost access is used in [../monitoring/ollama_monitor.py](../monitoring/ollama_monitor.py)
- Trading cycle log evidence exists in [../logs/trades.log](../logs/trades.log)

## Confirmed From Live Audit

- OpenClaw is installed and running as a launchd-managed service
- Ollama is installed and running as a Homebrew-managed service
- A weekday scheduler exists and is owned by OpenClaw cron, not system crontab
- OpenClaw directly invokes this repository with `cd ~/trading-bot && source .venv/bin/activate && python main.py`
- OpenClaw is configured with Telegram enabled
- OpenClaw workspace instructions explicitly reference this trading bot and its runtime commands

## Inferred But Still Unverified

- The Telegram bot is actively paired to at least one intended user, even though a `paired-users.json` file was not found at the audited path
- The delivery target in the cron job corresponds to the intended operator account
- OpenClaw heartbeats are actively used for bot follow-up checks, not merely defined in docs
- The gateway/auth/session settings in `openclaw.json` match the intended security posture described in [../Security.md](../Security.md)

## Unknowns To Verify On Host

### Installed software
- whether any additional OpenClaw-related binaries or plugins are installed outside the visible footprint

### External config and runtime state
- exact `dmPolicy`, `dmScope`, gateway mode, bind mode, and auth mode values after safe review
- whether additional OpenClaw workspace state affects command routing beyond the visible markdown files
- whether the cron delivery target maps to a single operator or multiple recipients
- exact live environment variable source for OpenClaw-triggered Python runs

### Service status
- whether any Python trading process is long-running or only invoked per scheduled / on-demand turn
- whether OpenClaw restarts cleanly across reboots in practice

## Audit Checklist

### A. Host baseline
- [x] Confirm macOS version
- [x] Confirm current user and home directory assumptions
- [x] Confirm Python version used for this project
- [x] Confirm Node version
- [x] Confirm Homebrew presence

### B. Python project runtime
- [ ] Confirm venv path and interpreter
- [ ] Confirm required packages installed
- [ ] Confirm where live `.env` is loaded from for OpenClaw-triggered runs
- [x] Confirm whether repo root is the live execution directory

### C. OpenClaw
- [x] Confirm OpenClaw installation
- [x] Confirm OpenClaw version
- [x] Confirm config file path
- [x] Confirm auth profile path
- [x] Confirm agent workspace path
- [x] Confirm presence of `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`
- [x] Confirm Telegram integration state
- [ ] Confirm pairing policy

### D. Scheduling / services
- [x] Confirm how daily scan is scheduled
- [x] Confirm launchd plist names/paths
- [x] Confirm cron usage, if any
- [ ] Confirm reboot persistence behavior

### E. Ollama
- [x] Confirm service status
- [x] Confirm installed models
- [x] Confirm model actually used by live trading flow

### F. Recovery / controls
- [ ] Confirm emergency stop procedure actually works
- [ ] Confirm restart procedure actually works
- [x] Confirm log locations
- [ ] Confirm incident logging expectations

## Evidence Log Template

Use entries like this when performing the audit:

### Example entry
- **Item:** OpenClaw config path
- **Status:** confirmed
- **Date:** 2026-03-08
- **Evidence:** observed file at `...`
- **Notes:** redacted template should be created under `docs/rebuild/external-config/`

## Evidence Highlights

- OpenClaw cron job explicitly runs `cd ~/trading-bot && source .venv/bin/activate && python main.py`
- OpenClaw workspace `TOOLS.md` explicitly documents trading-bot commands, logs, and strategy references
- OpenClaw workspace `HEARTBEAT.md` explicitly checks `~/trading-bot/logs/trades.log`
- `crontab -l` returned no jobs, confirming the scheduler is not system cron

## Immediate Next Action

Safely inspect and template the discovered OpenClaw config and workspace files in `docs/rebuild/external-config/`, then verify any remaining unknowns around Telegram pairing policy, gateway settings, and reboot persistence.
