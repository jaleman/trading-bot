# HEARTBEAT.md

## Staged Monorepo Checks

Use this heartbeat only for rebuild validation work, not for the current live production trading bot.

Do not interpret successful staged checks as cutover approval.

### 1. Check staged runtime activity
```bash
~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh
```
- If the staged app has not been run, stay quiet.
- If the staged app reports an error, notify the user.
- If the staged app remains in staged safe mode, do not imply that live trades occurred.

### 1a. Optional raw log inspection
```bash
tail -30 ~/trading-bot/monorepo-staging/runtime/trading-bot/logs/trades.log
```

### 2. Check staged guardrail state
```bash
cat ~/trading-bot/monorepo-staging/runtime/trading-bot/guardrail-state.json 2>/dev/null || echo "No staged guardrail state yet"
```

### 3. Optional validation check
```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh
```

## When to Notify

**Notify when:**
- staged tests fail
- staged runtime logs show errors
- staged runtime unexpectedly attempts execution outside expected safe-mode behavior
- staged operator summary reports blocked guardrails or unexpected execution

**Stay quiet when:**
- the staged app has not been run
- there is no new staged activity
- the staged app remains in expected production-candidate safe-mode behavior
