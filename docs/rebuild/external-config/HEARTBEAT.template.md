# HEARTBEAT.md — Sanitized Trading Bot Checks

## Trading Bot Checks

Run these checks 1–2x per day during market hours.

### 1. Check for new activity
```bash
tail -30 ~/trading-bot/logs/trades.log
```
- Notify the user if a BUY or SELL entry appears.
- Notify the user immediately if an ERROR appears.
- If the latest run says there were no signals, stay quiet.

### 2. Check open positions if a trade was made recently
```bash
cd ~/trading-bot && source .venv/bin/activate && python -c "from tools.alpaca_tools import get_open_positions; print(get_open_positions())"
```

## Verified Notes

- The live OpenClaw workspace contains a dedicated trading-bot heartbeat file.
- The heartbeat logic is centered on checking `~/trading-bot/logs/trades.log`.
- This file should be treated as part of the real runtime behavior, not just documentation.
