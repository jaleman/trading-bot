---
name: bot
description: "Trading bot operator router. Usage: /bot list|summary|pending|status|balance|holdings|info <TICKER>"
user-invocable: true
disable-model-invocation: false
---

# Trading Bot Operator Router

Routes operator requests to the repo-managed wrapper script and returns its
output verbatim.

```bash
/Users/labanlaro/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot <raw args>'
```

## Rules

- Pass the operator's arguments through unchanged. This is a deterministic
  router, not a conversation: `bot balance` runs the balance wrapper.
- Return the wrapper's stdout **verbatim**. Do not summarise, reformat, or
  round numbers — balances and positions are reported exactly as the broker
  states them.
- Never improvise an answer from memory or from raw logs when a wrapper
  exists. If the wrapper fails, report the failure text rather than guessing.
- With no arguments, run `bot list` to show the supported surface.

## Why this differs from the OpenClaw version

Under OpenClaw this skill was deliberately **disabled**
(`user-invocable: false`, `disable-model-invocation: true`) because a native
TypeScript command plugin owned `/bot` routing and the skill would have
competed with it.

ZeroClaw has no such plugin, so the skill becomes the router itself and is
enabled. The 56-line plugin it replaces did nothing but shell out to the same
wrapper script and return stdout, so no behaviour is lost.
