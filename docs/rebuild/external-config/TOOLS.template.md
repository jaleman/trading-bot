# TOOLS.md — Sanitized Trading Bot Notes

## Trading Bot

The trading bot lives at `~/trading-bot/`. It runs inside a Python virtual environment.

**Always activate the venv before running any bot command:**
```bash
cd ~/trading-bot && source .venv/bin/activate
```

## Run Commands

| What | Command |
|------|---------|
| Full daily scan | `cd ~/trading-bot && source .venv/bin/activate && python main.py` |
| Check today's log | `cat ~/trading-bot/logs/trades.log` |
| Check last 20 log lines | `tail -20 ~/trading-bot/logs/trades.log` |

## Verified Notes

- OpenClaw cron currently executes `python main.py` from the repo root.
- The log file path `~/trading-bot/logs/trades.log` is actively used by OpenClaw.
- The workspace guidance currently contains drift that must be corrected during rebuild.

## Known Drift To Fix In Rebuild

- References to `~/trading-bot/config/.env` do not match the current repo layout.
- References to `~/trading-bot/database/trades.db` do not match the visible implementation.
- Some helper commands assume async wrappers around functions that are currently synchronous.
- Some instructions reference `crontab -l`, but scheduling is actually owned by OpenClaw cron.
