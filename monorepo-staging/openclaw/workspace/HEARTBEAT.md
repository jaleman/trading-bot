# HEARTBEAT.md

## Active Runtime Checks

Use this heartbeat for the active monorepo trading runtime.

Do not interpret successful paper-trade checks as live-capital approval.

### 1. Check runtime activity
```bash
~/trading-bot/monorepo-staging/scripts/print_trading_bot_operator_summary.sh
```
- If the app has not been run, stay quiet.
- If the app reports an error, notify the user.
- If the summary wrapper returns output, use that exact stdout for any operator-facing summary.
- Do not wrap the stdout in headings, bullet lists, or extra explanation.

### 1a. Optional raw log inspection
```bash
tail -30 ~/trading-bot/monorepo-staging/runtime/trading-bot/logs/trades.log
```

### 1b. Optional broker-state check when order status matters
```bash
~/trading-bot/monorepo-staging/scripts/print_trading_bot_pending_orders.sh
```

Use this only when the operator asks whether submitted buys are pending, accepted, or filled.

### 2. Check guardrail state
```bash
cat ~/trading-bot/monorepo-staging/runtime/trading-bot/guardrail-state.json 2>/dev/null || echo "No guardrail state yet"
```

### 3. Optional validation check
```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot_tests.sh
```

## When to Notify

**Notify when:**
- tests fail
- runtime logs show errors
- guardrails block execution
- the runtime submits paper-trade orders
- broker state contradicts the latest summary artifact

**Stay quiet when:**
- the app has not been run
- there is no new runtime activity
- there is no operator-facing change worth reporting
