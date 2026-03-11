---
name: bot
description: "Trading bot operator router. Usage: /bot list|summary|pending|status|balance|holdings|info <TICKER>|sync|restart"
user-invocable: false
disable-model-invocation: true
---

# Trading Bot Operator Router

The native `/bot` workspace command now owns Telegram slash-command routing.

Keep this skill non-invocable so it does not compete with the native command path.

The repo-managed router remains:

```bash
~/trading-bot/monorepo-staging/scripts/run_trading_bot_telegram_command.sh 'bot <raw args>'
```

The native command should invoke that router directly and return wrapper stdout only.